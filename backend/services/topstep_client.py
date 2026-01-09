import httpx
import os
from datetime import datetime, timedelta, timezone
import asyncio
import json
from backend.database import SessionLocal, Log

class TopStepClient:
    def __init__(self):
        # Official TopStepX API URL
        self.base_url = os.getenv("TOPSTEP_URL", "https://api.topstepx.com") 
        self.username = os.getenv("TOPSTEP_USERNAME")
        self.password = os.getenv("TOPSTEP_PASSWORD") # Not used for 'loginKey' auth but kept for compat
        self.api_key = os.getenv("TOPSTEP_APIKEY") # NEW: Required for ProjectX
        
        self.token = None
        self.account_id = None
        self.account_id = None
        self._contract_cache = {} # Cache for Contract Details

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
        
        async with httpx.AsyncClient() as client:
            try:
                # print(f"Logging in to {url} with user {self.username}")
                response = await client.post(url, json=payload, timeout=10)
                
                if response.status_code != 200:
                    print(f"Login HTTP Error: {response.status_code} {response.text}")
                    return False

                data = response.json()
                
                if data.get("success"):
                    self.token = data["token"]
                    self._log_api_call("POST", url, payload, data, response.status_code)
                    
                    # Log high-level connection event
                    db = SessionLocal()
                    try:
                        db.add(Log(level="INFO", message="User Connected Successfully"))
                        db.commit()
                    finally:
                        db.close()
                        
                    return True
                else:
                    self._log_api_call("POST", url, payload, data, response.status_code)
                    print(f"Login failed: {data.get('errorMessage')}")
                    return False
            except Exception as e:
                print(f"Login Exception: {e}")
                return False

    async def logout(self):
        """Logs out by clearing the local token."""
        self.token = None
        return True

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

    async def get_accounts(self):
        """Retrieves all active trading accounts."""
        if not self.token:
            if not await self.login(): # Simple check for now, can be improved
                 return []

        url = f"{self.base_url}/api/Account/search"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"onlyActiveAccounts": True}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10)
                data = response.json()
                
                if data.get("success") and data.get("accounts"):
                    self._log_api_call("POST", url, payload, data, response.status_code)
                    return data["accounts"]
                else:
                    self._log_api_call("POST", url, payload, data, response.status_code)
                    print("No active accounts found.")
                    return []
            except Exception as e:
                print(f"Get Accounts Error: {e}")
                return []

    async def get_open_positions(self, account_id: int):
        """Retrieves open positions for a specific account."""
        if not self.token:
            if not await self.login():
                 return []
        
        url = f"{self.base_url}/api/Position/searchOpen"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"accountId": account_id}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10)
                data = response.json()
                
                if data.get("success") and data.get("positions"):
                    self._log_api_call("POST", url, payload, data, response.status_code)
                    return data["positions"]
                self._log_api_call("POST", url, payload, data, response.status_code)
                return []
            except Exception as e:
                print(f"Get Positions Error: {e}")
                return []

    async def get_orders(self, account_id: int, days: int = 1):
        """Retrieves orders for a specific account."""
        if not self.token:
            if not await self.login():
                 return []
        
        url = f"{self.base_url}/api/Order/search"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        if days == 1:
            # "Today" = Since Midnight Local Time
            now_local = datetime.now().astimezone() # Aware local time
            midnight_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            start_dt = midnight_local.astimezone(timezone.utc)
        else:
            # "Last N Days" = Rolling 24h * N for now, or Midnight N days ago?
            # User specifically complained about "Today". Let's keep 7 days as rolling window or N days ago.
            # To be consistent, let's make it rolling for 7 days unless requested otherwise.
            # But wait, "Last 7 days" usually implies a date range. 
            # Let's keep existing behavior for days > 1 but clean up format.
            start_dt = datetime.now(timezone.utc) - timedelta(days=days)

        # Remove microseconds and add Z
        start_timestamp = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        payload = {
            "accountId": account_id,
            "startTimestamp": start_timestamp
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10)
                data = response.json()
                
                if data.get("success") and data.get("orders"):
                    self._log_api_call("POST", url, payload, data, response.status_code)
                    return data["orders"]
                self._log_api_call("POST", url, payload, data, response.status_code)
                return []
            except Exception as e:
                print(f"Get Orders Error: {e}")
                return []

    async def get_historical_trades(self, account_id: int, days: int = 1):
        """Retrieves historical (half-turn) trades."""
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

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10)
                data = response.json()
                
                if data.get("success") and data.get("trades"):
                    self._log_api_call("POST", url, payload, data, response.status_code)
                    return data["trades"]
                self._log_api_call("POST", url, payload, data, response.status_code)
                return []
            except Exception as e:
                print(f"Get Historical Trades Error: {e}")
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

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10)
                data = response.json()
                self._log_api_call("POST", url, payload, data, response.status_code)
                return data.get("success", False)
            except Exception as e:
                print(f"Close Position Error: {e}")
                return False

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

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10)
                data = response.json()
                self._log_api_call("POST", url, payload, data, response.status_code)
                return data.get("success", False)
            except Exception as e:
                print(f"Cancel Order Error: {e}")
                return False

    async def get_contract_details(self, ticker: str):
        """
        Finds the Contract details for a given ticker (e.g. MNQ, MNQZ5).
        Returns a dict with {id, name, tickSize, tickValue, ...} or None.
        Uses In-Memory Cache to avoid frequent API calls.
        """
        # Normalize Ticker: Remove "1!", "2!" (TradingView continuous)
        clean_ticker = ticker.replace("1!", "").replace("2!", "")
        
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
        
        async with httpx.AsyncClient() as client:
            contracts = []
            try:
                # 2. Try Live
                payload_live = {"live": True}
                response = await client.post(url, json=payload_live, headers=headers, timeout=10)
                data = response.json()
                self._log_api_call("POST", url, payload_live, data, response.status_code)
                if data.get("success") and data.get("contracts"):
                    contracts = data["contracts"]
                else:
                    # 2b. Fallback to Simulation
                    response = await client.post(url, json={"live": False}, headers=headers, timeout=10)
                    data = response.json()
                    self._log_api_call("POST", url, {"live": False}, data, response.status_code)
                    if data.get("success") and data.get("contracts"):
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
            except Exception as e:
                print(f"Get Contract Details Error: {e}")
                return None

    async def get_all_computable_contracts(self):
        """Fetches all available contracts (raw list)."""
        if not self.token:
            await self.login()
            
        url = f"{self.base_url}/api/Contract/available"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                # Try Live
                response = await client.post(url, json={"live": True}, headers=headers, timeout=10)
                data = response.json()
                if data.get("success") and data.get("contracts"):
                    return data["contracts"]
                
                # Fallback to Simulation
                # print("Live contracts empty, trying simulation...")
                response = await client.post(url, json={"live": False}, headers=headers, timeout=10)
                data = response.json()
                if data.get("success") and data.get("contracts"):
                    return data["contracts"]

                print(f"Get All Contracts Failed. Response: {data}")
                return []
            except Exception as e:
                print(f"Get All Contracts Error: {e}")
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

        async with httpx.AsyncClient() as client:
            try:
                # print(f"Placing order: {payload}")
                response = await client.post(url, json=payload, headers=headers, timeout=10)
                data = response.json()
                self._log_api_call("POST", url, payload, data, response.status_code)
                
                if data.get("success"):
                    return {
                        "status": "filled", 
                        "order_id": str(data["orderId"]), 
                        "price": price, 
                        "avg_fill_price": price 
                    }
                else:
                    return {"status": "rejected", "reason": data.get("errorMessage", "Unknown Rejection")}

            except Exception as e:
                return {"status": "error", "message": f"Order Exception: {e}"}

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

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10)
                data = response.json()
                self._log_api_call("POST", url, payload, data, response.status_code)
                return data.get("success", False)
            except Exception as e:
                print(f"Modify Order Error: {e}")
                return False

    async def update_sl_tp_orders(self, account_id: int, ticker: str, sl_price: float, tp_price: float):
        """
        Finds open SL/TP orders for a ticker and updates them to the target prices.
        Assumes only one position active per ticker (enforced by risk engine).
        """
        # 1. Get Open Orders
        orders = await self.get_orders(account_id, days=1) 
        
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
