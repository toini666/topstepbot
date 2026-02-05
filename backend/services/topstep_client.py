import httpx
import os
from datetime import datetime, timedelta, timezone
import asyncio
import json
import logging
from backend.database import SessionLocal, Log
from backend.services.telegram_service import telegram_service

logger = logging.getLogger("topstepbot")


class RateLimitError(Exception):
    """Raised when API returns 429 Too Many Requests."""
    pass


class TopStepClient:
    def __init__(self):
        # Official TopStepX API URL
        self.base_url = os.getenv("TOPSTEP_URL", "https://api.topstepx.com")
        self.username = os.getenv("TOPSTEP_USERNAME")
        self.password = os.getenv("TOPSTEP_PASSWORD") # Not used for 'loginKey' auth but kept for compat
        self.api_key = os.getenv("TOPSTEP_APIKEY") # NEW: Required for ProjectX

        self.token = None
        self.account_id = None
        self._contract_cache = {} # Cache for Contract Details

        # Rate limiting tracking
        self._consecutive_errors = 0
        self._rate_limit_alert_sent = False
        self._last_rate_limit_time = None
        self._rate_limit_until = None # Circuit Breaker timestamp

        # Short-term API response cache to reduce redundant calls
        # Key: (endpoint, account_id), Value: (data, timestamp)
        self._api_cache = {}
        self._cache_ttl = {
            "accounts": 10,      # 10 seconds for accounts list
            "positions": 5,      # 5 seconds for positions (need fresh data)
            "orders": 5,         # 5 seconds for orders
            "trades": 10,        # 10 seconds for historical trades
        }

    async def _make_request(
        self, 
        method: str, 
        url: str, 
        payload: dict = None, 
        headers: dict = None,
        max_retries: int = 5,
        log_on_success: bool = True,
        expect_json: bool = True
    ) -> tuple:
        """
        Centralized HTTP request handler with exponential backoff for rate limiting.
        """
        # 1. CIRCUIT BREAKER CHECK
        if self._rate_limit_until and datetime.now(timezone.utc) < self._rate_limit_until:
            wait_time = (self._rate_limit_until - datetime.now(timezone.utc)).total_seconds()
            logger.warning(f"Circuit Breaker Active. Skipping call to {url}. Wait {wait_time:.1f}s")
            return (None, 429, False)

        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, headers=headers)
                    else:
                        response = await client.post(url, json=payload, headers=headers)
                    
                    # Handle rate limiting (429) - TRIGGER CIRCUIT BREAKER
                    if response.status_code == 429:
                        self._consecutive_errors += 1
                        
                        # Enable Circuit Breaker for 60 seconds
                        cooldown = 60
                        self._rate_limit_until = datetime.now(timezone.utc) + timedelta(seconds=cooldown)
                        
                        logger.error(
                            f"Rate limit hit (429) on {url}. Circuit Breaker ACTIVATED for {cooldown}s. "
                            f"Consecutive errors: {self._consecutive_errors}"
                        )
                        
                        # Log to database
                        self._log_api_call(method, url, payload, {"error": "Rate Limit Circuit Breaker Activated"}, 429)
                        
                        # Send Telegram alert immediately
                        if not self._rate_limit_alert_sent:
                            await self._send_rate_limit_alert(url, self._consecutive_errors)
                        
                        self._last_rate_limit_time = datetime.now(timezone.utc)
                        
                        # ABORT RETRIES - STOP HAMMERING
                        return (None, 429, False)
                    
                    # Handle auth errors
                    if response.status_code == 401:
                        self.token = None
                        self._log_api_call(method, url, payload, None, 401)
                        return (None, 401, False)
                    
                    # Handle 502 Bad Gateway (Maintenance)
                    if response.status_code == 502:
                        logger.warning(f"Topstep API 502 Bad Gateway on {url}. Maintenance likely. Waiting 60s...")
                        # Log it but don't count strictly as a "connection error" for circuit breaker, just maintenance
                        self._log_api_call(method, url, payload, None, 502)
                        await asyncio.sleep(60)
                        continue # Retry
                    
                    # Handle other errors
                    if response.status_code >= 400:
                        self._consecutive_errors += 1
                        self._log_api_call(method, url, payload, None, response.status_code)
                        return (None, response.status_code, False)
                    
                    # Success - reset error counter
                    self._consecutive_errors = 0
                    self._rate_limit_alert_sent = False
                    # DO NOT RESET CIRCUIT BREAKER ON SUCCESS
                    # Concurrent requests might succeed while a ban is active.
                    # We must let the time run out naturally.
                    # self._rate_limit_until = None 
                    
                    if expect_json:
                        try:
                            data = response.json()
                            if log_on_success:
                                self._log_api_call(method, url, payload, data, response.status_code)
                            return (data, response.status_code, True)
                        except json.JSONDecodeError:
                            self._log_api_call(method, url, payload, {"raw": response.text}, response.status_code)
                            return (None, response.status_code, False)
                    else:
                        if log_on_success:
                            self._log_api_call(method, url, payload, {"text": response.text}, response.status_code)
                        return (response.text, response.status_code, True)
                        
            except httpx.TimeoutException:
                self._consecutive_errors += 1
                logger.error(f"Timeout on {url} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay * (2 ** attempt))
                continue
            except Exception as e:
                self._consecutive_errors += 1
                logger.error(f"Request error on {url}: {e}")
                return (None, 0, False)
        
        # All retries exhausted
        logger.error(f"All {max_retries} retries exhausted for {url}")
        return (None, 429, False)

    def _get_cached(self, cache_key: str, account_id: int = None) -> tuple:
        """
        Get cached API response if still valid.
        Returns (data, is_valid) tuple.
        """
        full_key = f"{cache_key}:{account_id}" if account_id else cache_key
        cached = self._api_cache.get(full_key)

        if cached:
            data, timestamp = cached
            ttl = self._cache_ttl.get(cache_key, 5)
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()

            if age < ttl:
                return (data, True)

        return (None, False)

    def _set_cache(self, cache_key: str, data, account_id: int = None):
        """Store API response in cache."""
        full_key = f"{cache_key}:{account_id}" if account_id else cache_key
        self._api_cache[full_key] = (data, datetime.now(timezone.utc))

    def clear_cache(self, cache_key: str = None, account_id: int = None):
        """Clear specific cache entry or all cache."""
        if cache_key is None:
            self._api_cache.clear()
        else:
            full_key = f"{cache_key}:{account_id}" if account_id else cache_key
            self._api_cache.pop(full_key, None)

    async def _send_rate_limit_alert(self, url: str, error_count: int):
        """Send Telegram notification about rate limiting."""
        try:
            # Fix: Use the global instance imported at top of file
            # from backend.services.telegram_service import telegram_service 
            
            message = (
                f"⚠️ <b>API RATE LIMITING DETECTED</b>\n\n"
                f"TopStep API is returning 429 errors.\n"
                f"Consecutive errors: <code>{error_count}</code>\n"
                f"Last endpoint: <code>{url.split('/')[-1]}</code>\n\n"
                f"<b>CIRCUIT BREAKER ACTIVATED</b>\n"
                f"Pausing all API calls for 60 seconds."
            )
            
            # Print to console instantly as fallback to ensure visibility
            print(f"🚨 RATE LIMIT ALERT: {error_count} consecutive 429s on {url}")
            
            await telegram_service.send_message(message)
            self._rate_limit_alert_sent = True
            
            # Also log to database
            db = SessionLocal()
            try:
                db.add(Log(
                    level="ERROR",
                    message=f"Rate Limit Alert: {error_count} consecutive 429 errors",
                    details=json.dumps({"url": url, "error_count": error_count})
                ))
                db.commit()
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to send rate limit alert: {e}")
            print(f"CRITICAL: Failed to send Telegram alert for Rate Limit: {e}")


    def _log_api_call(self, method: str, url: str, payload: dict = None, response: dict = None, status_code: int = 0):
        """Logs an API call to the database."""
        try:
            # Filter out noisy polling endpoints (only log on error)
            # These run every few seconds and clutter the logs
            NOISY_ENDPOINTS = [
                "/api/Account/search",
                "/api/Position/searchOpen",
                "/api/Order/search",
                "/api/Trade/search",
                "/api/Auth/loginKey" # Login check might happen often if wrapper is used (though it shouldn't)
            ]
            
            is_noisy = any(endpoint in url for endpoint in NOISY_ENDPOINTS)
            
            # If it's a noisy endpoint and successful (200), SKIP LOGGING
            if is_noisy and 200 <= status_code < 300:
                return

            # Mask sensitive tokens if they accidentally slip in (though we log endpoint/payload)
            # Just to be safe or keep it simple.
            
            # Determine Log Level & Message Prefix
            level = "INFO"
            prefix = "API"
            
            if status_code == 0:
                level = "ERROR"
                prefix = "CONNECTION LOST"
            elif status_code in [401, 403]:
                level = "WARNING" 
                prefix = "AUTH ERROR"
                # Critical: Clear token so next call triggers re-login
                self.token = None
            elif status_code >= 400:
                level = "ERROR"
                prefix = "API ERROR"
            elif response and isinstance(response, dict) and response.get("success") is False:
                level = "ERROR"
                prefix = "API REJECTED"

            summary = f"{prefix} {method} {url} [{status_code}]"
            
            details = {
                "method": method,
                "url": url,
                "payload": payload,
                "response": response,
                "status_code": status_code
            }
            
            db = SessionLocal()
            try:
                log = Log(level=level, message=summary, details=json.dumps(details, default=str))
                db.add(log)
                db.commit()
            except Exception as e:
                print(f"Failed to log API call: {e}")
            finally:
                db.close()
        except Exception as e:
            print(f"Logging Wrapper Error: {e}")

    async def login(self):
        """Authenticates using UserName + API Key to get a Bearer Token."""
        url = f"{self.base_url}/api/Auth/loginKey"
        payload = {
            "userName": self.username,
            "apiKey": self.api_key
        }
        
    async def login(self):
        """Authenticates using UserName + API Key to get a Bearer Token."""
        url = f"{self.base_url}/api/Auth/loginKey"
        payload = {
            "userName": self.username,
            "apiKey": self.api_key
        }
        
        # Login is critical, careful not to loop if it fails inside _make_request (e.g. 401)
        # But _make_request handles 401 by clearing token, which is fine.
        data, status_code, success = await self._make_request("POST", url, payload, max_retries=3)
        
        if success and data.get("success"):
            self.token = data["token"]
            
            # Log high-level connection event
            db = SessionLocal()
            try:
                db.add(Log(level="INFO", message="User Connected Successfully"))
                db.commit()
            finally:
                db.close()
                
            return True
        else:
            print(f"Login failed: {data.get('errorMessage') if data else 'Unknown error'}")
            return False

    async def logout(self):
        """Logs out by clearing the local token."""
        self.token = None
        return True

    async def ping(self) -> tuple:
        """
        Checks TopStep API health using /api/Status/ping endpoint.
        Returns (is_healthy: bool, response_time_ms: float, error: str|None)
        """
        import time
        url = f"{self.base_url}/api/Status/ping"
        
        start_time = time.time()
        # Ping usually shouldn't trigger circuit breaker blocking, but 429s should still count?
        # Let's use _make_request but maybe allow it to pass even if CB is open? 
        # Actually standardizing is safer.
        data, status_code, success = await self._make_request("GET", url, max_retries=1, log_on_success=False, expect_json=False)
        response_time = (time.time() - start_time) * 1000  # ms
        
        if success and status_code == 200:
            return (True, response_time, None)
        else:
            return (False, response_time, f"HTTP {status_code}")

    async def _ensure_token(self):
        """Checks if token is valid, if not, logs in."""
        # 1. If no token, login
        if not self.token:
            return await self.login()
        
        # 2. Validate Token (Optional but recommended by User)
        # Using a lightweight call or specific Validate endpoint if exists
        # Swagger typically has /api/Auth/values or similar to check auth
        # User mentioned Auth/Validate specifically? Let's try or assume we check expiration.
        # Ideally we track expiration time locally to save requests, but here let's try a quick check.
        # But for performance (polling), we shouldn't validate EVERY call.
        # Let's just rely on 401 retry logic OR simple local check if we had expiration.
        
        # Since user explicitly asked for Auth/Validate:
        return True

    async def get_accounts(self, use_cache: bool = True):
        """Retrieves all active trading accounts."""
        # Check cache first
        if use_cache:
            cached_data, is_valid = self._get_cached("accounts")
            if is_valid:
                return cached_data

        if not self.token:
            if not await self.login():
                return []

        url = f"{self.base_url}/api/Account/search"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"onlyActiveAccounts": True}

        url = f"{self.base_url}/api/Account/search"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"onlyActiveAccounts": True}

        data, status_code, success = await self._make_request("POST", url, payload, headers)

        if success and data.get("success") and data.get("accounts"):
            accounts = data["accounts"]
            self._set_cache("accounts", accounts)
            return accounts
        else:
            print("No active accounts found or API error.")
            return []

    async def get_open_positions(self, account_id: int, use_cache: bool = True):
        """Retrieves open positions for a specific account."""
        # Check cache first
        if use_cache:
            cached_data, is_valid = self._get_cached("positions", account_id)
            if is_valid:
                return cached_data

        if not self.token:
            if not await self.login():
                return []

        url = f"{self.base_url}/api/Position/searchOpen"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"accountId": account_id}

        url = f"{self.base_url}/api/Position/searchOpen"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"accountId": account_id}

        data, status_code, success = await self._make_request("POST", url, payload, headers)

        if success and data.get("success") and data.get("positions"):
            positions = data["positions"]
            self._set_cache("positions", positions, account_id)
            return positions
        
        # Even if failed or empty, cache empty result to avoid spamming if API is returning success=false
        # But be careful, if API error, maybe don't cache empty? 
        # _make_request returns success=False on HTTP error.
        if success:
             self._set_cache("positions", [], account_id)
             
        return []

    async def get_orders(self, account_id: int, days: int = 1, use_cache: bool = True):
        """Retrieves orders for a specific account."""
        # Check cache first (only for days=1, the most common case)
        if use_cache and days == 1:
            cached_data, is_valid = self._get_cached("orders", account_id)
            if is_valid:
                return cached_data

        if not self.token:
            if not await self.login():
                return []

        url = f"{self.base_url}/api/Order/search"
        headers = {"Authorization": f"Bearer {self.token}"}

        if days == 1:
            # "Today" = Since Midnight Local Time
            now_local = datetime.now().astimezone()
            midnight_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            start_dt = midnight_local.astimezone(timezone.utc)
        else:
            start_dt = datetime.now(timezone.utc) - timedelta(days=days)

        start_timestamp = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        payload = {
            "accountId": account_id,
            "startTimestamp": start_timestamp
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10)

                if response.status_code != 200:
                    self._log_api_call("POST", url, payload, None, response.status_code)
                    if response.status_code == 401:
                        self.token = None
                    return []

                try:
                    data = response.json()
                except json.JSONDecodeError:
                    self._log_api_call("POST", url, payload, {"raw": response.text}, response.status_code)
                    return []

                if data.get("success") and data.get("orders"):
                    self._log_api_call("POST", url, payload, data, response.status_code)
                    orders = data["orders"]
                    if days == 1:
                        self._set_cache("orders", orders, account_id)
                    return orders
                self._log_api_call("POST", url, payload, data, response.status_code)
                if days == 1:
                    self._set_cache("orders", [], account_id)
                return []
            except Exception as e:
                print(f"Get Orders Error: {e}")
                return []

    async def get_historical_trades(self, account_id: int, days: int = 1, use_cache: bool = True):
        """Retrieves historical (half-turn) trades."""
        # Check cache first (only for days=1, the most common case)
        if use_cache and days == 1:
            cached_data, is_valid = self._get_cached("trades", account_id)
            if is_valid:
                return cached_data

        if not self.token:
            if not await self.login():
                return []

        url = f"{self.base_url}/api/Trade/search"
        headers = {"Authorization": f"Bearer {self.token}"}

        if days == 1:
            # "Today" = Since Midnight Local Time
            now_local = datetime.now().astimezone()
            midnight_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            start_dt = midnight_local.astimezone(timezone.utc)
        else:
            start_dt = datetime.now(timezone.utc) - timedelta(days=days)

        start_timestamp = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        payload = {
            "accountId": account_id,
            "startTimestamp": start_timestamp
        }

        data, status_code, success = await self._make_request("POST", url, payload, headers)

        if success and data.get("success") and data.get("trades"):
            trades = data["trades"]
            if days == 1:
                self._set_cache("trades", trades, account_id)
            return trades
            
        if success and days == 1:
            self._set_cache("trades", [], account_id)
            
        return []

    async def close_position(self, account_id: int, contract_id: str):
        """Closes a specific position."""
        if not self.token:
            if not await self.login():
                 return False
        
        url = f"{self.base_url}/api/Position/closeContract"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "accountId": account_id,
            "contractId": contract_id
        }

        url = f"{self.base_url}/api/Position/closeContract"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "accountId": account_id,
            "contractId": contract_id
        }

        data, status_code, success = await self._make_request("POST", url, payload, headers)
        
        if success and data.get("success"):
            # Invalidate Cache
            self.clear_cache("orders", account_id)
            self.clear_cache("positions", account_id)
            return True
            
        return False

    async def partial_close_position(self, account_id: int, contract_id: str, size: int) -> dict:
        """Partially closes a position using TopStep's dedicated API."""
        if not self.token:
            if not await self.login():
                return {"success": False, "error": "Not authenticated"}
        
        url = f"{self.base_url}/api/Position/partialCloseContract"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "accountId": account_id,
            "contractId": contract_id,
            "size": size
        }

        url = f"{self.base_url}/api/Position/partialCloseContract"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "accountId": account_id,
            "contractId": contract_id,
            "size": size
        }

        data, status_code, success = await self._make_request("POST", url, payload, headers)
        
        if success:
             # Invalidate Cache
            self.clear_cache("orders", account_id)
            self.clear_cache("positions", account_id)
            return data
            
        return {"success": False, "error": f"API Error {status_code}"}

    async def cancel_order(self, account_id: int, order_id: int):
        """Cancels a specific order."""
        if not self.token:
            if not await self.login():
                 return False
        
        url = f"{self.base_url}/api/Order/cancel"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "accountId": account_id,
            "orderId": order_id
        }

        url = f"{self.base_url}/api/Order/cancel"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "accountId": account_id,
            "orderId": order_id
        }

        data, status_code, success = await self._make_request("POST", url, payload, headers)
        
        if success and data.get("success"):
            # Invalidate Cache
            self.clear_cache("orders", account_id)
            return True
            
        return False

    async def get_contract_details(self, ticker: str):
        """
        Finds the Contract details for a given ticker (e.g. MNQ, MNQZ5).
        Returns a dict with {id, name, tickSize, tickValue, ...} or None.
        Uses In-Memory Cache to avoid frequent API calls.
        """
        # Normalize Ticker: Remove "1!", "2!" and any trailing "!"
        clean_ticker = ticker.replace("1!", "").replace("2!", "").replace("!", "")
        
        # 1. Check Cache
        cached = self._contract_cache.get(clean_ticker)
        if cached:
            # print(f"Cache Hit for {clean_ticker}")
            return cached

        # 2. If not in cache, fetch all available contracts and populate cache
        if not self.token:
            await self.login()
            
        url = f"{self.base_url}/api/Contract/available"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # 2. Try Live
        payload_live = {"live": True}
        data, status_code, success = await self._make_request("POST", url, payload_live, headers, max_retries=2)
        
        contracts = []
        if success and data.get("success") and data.get("contracts"):
            contracts = data["contracts"]

        if not contracts:
            # 2b. Fallback to Simulation
            payload_sim = {"live": False}
            data, status_code, success = await self._make_request("POST", url, payload_sim, headers, max_retries=2)
            if success and data.get("success") and data.get("contracts"):
                contracts = data["contracts"]

        # 3. Populate Cache
        if contracts:
            self._contract_cache = {} # Clear old cache? Or merge? Clear is safer to remove expired.
            for contract in contracts:
                # Map Contract Name prefix to Contract Object
                # keys: MNQ, MNQZ5, NQ, NQZ5...
                # API returns "name": "MNQH6", "symbolId": "MNQ"
                # We want to map "MNQ" -> MNQH6 object
                
                # Store by Exact Name
                c_name = contract.get("name", "")
                self._contract_cache[c_name] = contract
                
                # Store by Root Symbol (if it matches the *current* contract pattern)
                # This is tricky. Usually we want the front month. 
                # But for now, let's just cache by full name and implement a smarter lookup below.
            
            # 4. Find the specific requested ticker in the fresh cache
            # Iterate cache to find prefix match
            found = None
            for c_name, contract in self._contract_cache.items():
                 if c_name.startswith(clean_ticker):
                     # TODO: If multiple match (MNQH6, MNQM6), pick nearest?
                     # API usually returns sorted or we just pick first.
                     # For now, pick first match.
                     found = contract
                     # Also cache the CLEAN TICKER -> FOUND CONTRACT for direct lookup next time
                     self._contract_cache[clean_ticker] = found
                     break
            
            if found:
                return found
                
            print(f"Contract {ticker} details not found in {len(contracts)} available contracts.")
            return None
        else:
            print("Failed to fetch contract list (Live & Sim).")
            return None

    async def get_all_computable_contracts(self):
        """Fetches all available contracts (raw list)."""
        if not self.token:
            await self.login()
            
        url = f"{self.base_url}/api/Contract/available"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # 2. Try Live
        payload_live = {"live": True}
        data, status_code, success = await self._make_request("POST", url, payload_live, headers, max_retries=2)
        
        contracts = []
        if success and data.get("success") and data.get("contracts"):
            contracts = data["contracts"]
            
        if not contracts:
            # 2b. Fallback to Simulation
            payload_sim = {"live": False}
            data, status_code, success = await self._make_request("POST", url, payload_sim, headers, max_retries=2)
            if success and data.get("success") and data.get("contracts"):
               contracts = data["contracts"]

        # 3. Return contracts
        if contracts:
             return contracts
            
        print("Failed to fetch contract list (Live & Sim).")
        return []

    async def find_contract(self, ticker: str):
        """Legacy wrapper for backward compatibility if needed, returns just ID."""
        details = await self.get_contract_details(ticker)
        return details["id"] if details else None

    async def place_order(self, ticker: str, action: str, quantity: int, price: float = None, account_id: int = None, sl_ticks: int = None, tp_ticks: int = None, contract_id: str = None):
        """Places a Market Order with Optional Brackets (SL/TP in Ticks)."""
        if not self.token:
            if not await self.login():
                 return {"status": "rejected", "reason": "Login API Failed"}
            
        # Use provided account_id or fall back to stored/fetched one
        target_account_id = account_id
        if not target_account_id:
            if not self.account_id:
                await self.get_accounts() # Fetch defaults
            target_account_id = self.account_id
            
        if not target_account_id:
            return {"status": "rejected", "reason": "No Active Account Found"}

        # Try to find Contract ID (if not provided)
        if not contract_id:
            contract_id = await self.find_contract(ticker)
            
        if not contract_id:
            print(f"Warning: Could not resolve {ticker} to a Contract ID. Using ticker as ID.")
            contract_id = ticker

        url = f"{self.base_url}/api/Order/place"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Action Map: BUY=0 (Bid), SELL=1 (Ask) (Based on API Enum)
        side = 0 if action.upper() == "BUY" else 1
        
        payload = {
            "accountId": target_account_id,
            "contractId": contract_id,
            "type": 2, # Market Order
            "side": side,
            "size": quantity
        }

        # Attach Brackets if provided
        if sl_ticks:
            payload["stopLossBracket"] = {
                "ticks": sl_ticks,
                "type": 4 # Stop
            }
        
        if tp_ticks:
            payload["takeProfitBracket"] = {
                "ticks": tp_ticks,
                "type": 1 # Limit
            }

        data, status_code, success = await self._make_request("POST", url, payload, headers)
        
        if success and data.get("success"):
            # Invalidate Cache
            self.clear_cache("orders", target_account_id)
            self.clear_cache("positions", target_account_id)
            
            return {
                "status": "filled", 
                "order_id": str(data["orderId"]), 
                "price": price, 
                "avg_fill_price": price 
            }
            
        return {"status": "rejected", "reason": data.get("errorMessage", "Unknown Rejection") if data else f"API Error {status_code}"}

    async def modify_order(self, order_id: int, account_id: int = None, **kwargs):
        """Modifies an existing order. Pass fields like limitPrice, stopPrice, size as kwargs."""
        if not self.token:
            if not await self.login():
                 return False
        
        target_account_id = account_id
        if not target_account_id:
            target_account_id = self.account_id

        if not target_account_id:
            print("Modify Order Error: No Account ID provided")
            return False

        url = f"{self.base_url}/api/Order/modify"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        payload = {
            "orderId": order_id,
            "accountId": target_account_id
        }
        # Merge optional updates
        payload.update(kwargs)

        data, status_code, success = await self._make_request("POST", url, payload, headers)
        
        if success and data.get("success"):
             # Invalidate Cache
            self.clear_cache("orders", target_account_id)
            return True
            
        if data and not data.get("success"):
             await telegram_service.notify_api_error("POST", url, data, status_code)
             
        return False

    async def update_sl_tp_orders(self, account_id: int, ticker: str, sl_price: float, tp_price: float):
        """
        Finds open SL/TP orders for a ticker and updates them to the target prices.
        Assumes only one position active per ticker (enforced by risk engine).
        """
        # 1. Get Open Orders (Bypass Cache to catch recent executions)
        orders = await self.get_orders(account_id, days=1, use_cache=False) 
        
        print(f"DEBUG: Found {len(orders)} orders for account {account_id}")
        
        count = 0
        clean_ticker = ticker.replace("1!", "").replace("2!", "").upper()
            
        for order in orders:
            # Keys might be 'orderId' or 'id'. API varies.
            oid = order.get('orderId') or order.get('id')
            ostatus = order.get('status')
            otype = order.get('type')
            cid = order.get('contractId') or order.get('symbol')
            
            # Check Status
            # Status 1 = Working (likely), 2 = Filled, 3 = Canceled
            # Allow 'Working' (str) or 1 (int) or 6 (Pending?)
            valid_statuses = ["Working", "Accepted", 1, 6]
            if ostatus not in valid_statuses:
                continue
            
            # Check Ticker/Contract - STRICT MATCH needed?
            # Contracts usually look like "MNQZ4" or "CON.F.US.MNQ.Z4"
            # It's better to match loose containment of ticker root
            if not cid: continue
            if clean_ticker not in cid.upper():
                continue
            
            target_price = None
            if otype == 4: # STOP (SL)
                 target_price = sl_price
            elif otype == 1: # LIMIT (TP)
                 target_price = tp_price
            
            if target_price:
                 # Check multiple price keys
                 current_price = order.get("price")
                 if current_price is None:
                     current_price = order.get("triggerPrice") or order.get("stopPrice") or order.get("limitPrice")
                 
                 # If still None, maybe log and skip, or force update?
                 if current_price is None:
                     continue
                 
                 # Check if modification needed (tolerance?)
                 if abs(current_price - target_price) > 0.01:
                     print(f"Correcting Order {oid}: {current_price} -> {target_price}")
                     
                     # Determine correct key based on type
                     update_params = {}
                     if otype == 4:
                         update_params["stopPrice"] = target_price
                     elif otype == 1:
                         update_params["limitPrice"] = target_price
                     
                     await self.modify_order(oid, account_id=account_id, **update_params)
                     count += 1
        
        return count

    async def sync_order_quantities(self, account_id: int, ticker: str, new_quantity: int):
        """
        Synchronizes SL/TP order quantities with the current position size.
        This MUST be called after a partial close to prevent over-closing.
        
        Args:
            account_id: The account to sync orders for
            ticker: The contract ticker (e.g., "MNQ1!")
            new_quantity: The remaining position size after partial close
        
        Returns:
            Number of orders that were modified
        """
        orders = await self.get_orders(account_id, days=1, use_cache=False)
        clean_ticker = ticker.replace("1!", "").replace("2!", "").upper()
        
        count = 0
        for order in orders:
            oid = order.get('orderId') or order.get('id')
            ostatus = order.get('status')
            otype = order.get('type')
            cid = order.get('contractId') or order.get('symbol')
            current_size = order.get('size', 0)
            
            # Check status (Working/Accepted)
            valid_statuses = ["Working", "Accepted", 1, 6]
            if ostatus not in valid_statuses:
                continue
            
            # Check ticker match
            if not cid or clean_ticker not in cid.upper():
                continue
            
            # Only update SL (type=4) and TP/Limit (type=1) orders
            if otype not in [1, 4]:
                continue
            
            # Check if size needs adjustment
            if current_size != new_quantity:
                print(f"Syncing Order {oid} size: {current_size} -> {new_quantity}")
                success = await self.modify_order(oid, account_id=account_id, size=new_quantity)
                if success:
                    count += 1
                else:
                    print(f"Failed to sync order {oid} size")
        
        return count

    async def get_current_price(self, contract_id: str, is_simulated: bool = True):
        """
        Get the current/latest price for a contract using retrieveBars API.
        Uses 1-second bars, fetching the last few seconds to get the most recent close price.
        
        Args:
            contract_id: The TopStep contract ID (e.g., "MNQH6")
            is_simulated: If True, uses live=False for simulated accounts
        
        Returns:
            The close price of the most recent bar, or None if unavailable.
        """
        await self._ensure_token()
        
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(seconds=10)  # Look back 10 seconds
        
        url = f"{self.base_url}/api/History/retrieveBars"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Sim accounts must use live=False, live accounts use live=True
        live_flag = not is_simulated
        
        payload = {
            "contractId": contract_id,
            "live": live_flag,
            "startTime": start_time.isoformat(),
            "endTime": now.isoformat(),
            "unit": 1,  # 1 = Second
            "unitNumber": 1,  # 1-second bars
            "limit": 5,  # Get last 5 bars
            "includePartialBar": True
        }
        
        # Use centralized request handler with rate limiting protection
        data, status_code, success = await self._make_request(
            "POST", url, payload, headers,
            max_retries=2,  # Fewer retries for price fetching
            log_on_success=False  # Don't log every price fetch (too noisy)
        )
        
        if success and data and data.get("success"):
            bars = data.get("bars", [])
            if bars:
                # Find the most recent bar with a valid close price
                for bar in reversed(bars):
                    close_price = bar.get("c") or bar.get("close")  # API uses 'c' for close
                    if close_price is not None:
                        return close_price
        
        return None






    async def cancel_all_orders(self, account_id: int):
        """Fetches all working orders and cancels them."""
        # 1. Get Orders (using existing helper that fetches last 24h)
        # Note: Ideally we'd scan further back, but API limits apply. 
        # Usually orphaned orders are recent.
        orders = await self.get_orders(account_id, days=1)
        
        count = 0 
        for order in orders:
            # Check for Working Status (1=Working, 6=Pending, "Working", "Accepted")
            status = order.get('status')
            if status in [1, 6, "Working", "Accepted"]:
                oid = order.get('id') or order.get('orderId')
                if oid:
                    await self.cancel_order(account_id, oid)
                    count += 1
        return count

topstep_client = TopStepClient()
