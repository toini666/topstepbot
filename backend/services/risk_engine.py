"""
Risk Engine - Hierarchical Settings Management & Trade Validation

Validation Flow (Per Account):
1. check_market_hours()            → Is market open? (Mon-Fri 00:00-22:00)
2. check_blocked_periods()         → Global blocked periods
3. check_account_enabled()         → Is account trading ON?
4. check_strategy_enabled()        → Is strategy active on account?
5. check_session_allowed()         → Is current session allowed for strategy?
6. check_open_position()           → No duplicate positions on this account
7. check_cross_account_direction() → No opposing positions on other accounts
"""

import json
from datetime import datetime, timezone, time
from typing import Optional, Tuple, List, Dict, Any
import pytz
from sqlalchemy.orm import Session

from backend.database import (
    Setting, Trade, TradeStatus, 
    AccountSettings, AccountStrategyConfig, 
    TradingSession, Strategy
)

# Brussels Timezone for all time calculations
BRUSSELS_TZ = pytz.timezone("Europe/Brussels")


class RiskEngine:
    """Manages hierarchical settings and trade validation."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # =========================================================================
    # GLOBAL SETTINGS
    # =========================================================================
    
    def get_global_settings(self) -> Dict[str, Any]:
        """Load all global settings from database."""
        settings = {}
        
        # Blocked periods enabled
        bp_enabled = self._get_setting("blocked_periods_enabled", "true")
        settings["blocked_periods_enabled"] = bp_enabled.lower() == "true"
        
        # Blocked periods (JSON)
        bp_json = self._get_setting("blocked_periods", "[]")
        try:
            settings["blocked_periods"] = json.loads(bp_json)
        except Exception:
            settings["blocked_periods"] = []
        
        # Auto flatten
        settings["auto_flatten_enabled"] = self._get_setting("auto_flatten_enabled", "false").lower() == "true"
        settings["auto_flatten_time"] = self._get_setting("auto_flatten_time", "21:55")
        
        # Market hours
        settings["market_open_time"] = self._get_setting("market_open_time", "00:00")
        settings["market_close_time"] = self._get_setting("market_close_time", "22:00")
        
        # Trading days (default: Mon-Fri)
        td_json = self._get_setting("trading_days", '["MON","TUE","WED","THU","FRI"]')
        try:
            settings["trading_days"] = json.loads(td_json)
        except Exception:
            settings["trading_days"] = ["MON", "TUE", "WED", "THU", "FRI"]
        
        # Configurable risk rules
        settings["enforce_single_position_per_asset"] = self._get_setting("enforce_single_position_per_asset", "true").lower() == "true"
        settings["block_cross_account_opposite"] = self._get_setting("block_cross_account_opposite", "true").lower() == "true"
        
        return settings
    
    def _get_setting(self, key: str, default: str = "") -> str:
        """Get a single setting value."""
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        return setting.value if setting else default
    
    def _set_setting(self, key: str, value: str):
        """Set a setting value."""
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = value
        else:
            self.db.add(Setting(key=key, value=value))
        self.db.commit()
    
    # =========================================================================
    # TRADING SESSIONS
    # =========================================================================
    
    def get_trading_sessions(self) -> List[TradingSession]:
        """Get all configured trading sessions."""
        return self.db.query(TradingSession).all()
    
    def get_current_session(self) -> Optional[str]:
        """Returns the name of the current active session, or None if outside all sessions."""
        now_bru = datetime.now(BRUSSELS_TZ).time()
        
        sessions = self.get_trading_sessions()
        for session in sessions:
            if not session.is_active:
                continue
                
            try:
                start_h, start_m = map(int, session.start_time.split(':'))
                end_h, end_m = map(int, session.end_time.split(':'))
                t_start = time(start_h, start_m)
                t_end = time(end_h, end_m)
                
                # Handle midnight crossing
                if t_start > t_end:
                    if now_bru >= t_start or now_bru <= t_end:
                        return session.name
                else:
                    if t_start <= now_bru <= t_end:
                        return session.name
            except Exception as e:
                print(f"Session parse error for {session.name}: {e}")
                continue
        
        return None
    
    # =========================================================================
    # ACCOUNT SETTINGS
    # =========================================================================
    
    def get_account_settings(self, account_id: int) -> Optional[AccountSettings]:
        """Get settings for a specific account."""
        return self.db.query(AccountSettings).filter(
            AccountSettings.account_id == account_id
        ).first()
    
    def ensure_account_settings(self, account_id: int, account_name: str = None) -> AccountSettings:
        """Get or create account settings with defaults."""
        settings = self.get_account_settings(account_id)
        if not settings:
            settings = AccountSettings(
                account_id=account_id,
                account_name=account_name,
                trading_enabled=False,  # Default: PAUSED for safety
                risk_per_trade=200.0
            )
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        elif account_name and not settings.account_name:
            # Update account_name if it was missing
            settings.account_name = account_name
            self.db.commit()
        return settings
    
    # =========================================================================
    # STRATEGY CONFIG (Per Account)
    # =========================================================================
    
    def get_strategy_config(self, account_id: int, strategy_tv_id: str) -> Optional[AccountStrategyConfig]:
        """Get strategy configuration for a specific account."""
        strategy = self.db.query(Strategy).filter(Strategy.tv_id == strategy_tv_id).first()
        if not strategy:
            return None
        
        return self.db.query(AccountStrategyConfig).filter(
            AccountStrategyConfig.account_id == account_id,
            AccountStrategyConfig.strategy_id == strategy.id
        ).first()
    
    def get_strategy_by_tv_id(self, tv_id: str) -> Optional[Strategy]:
        """Get strategy template by TradingView ID."""
        return self.db.query(Strategy).filter(Strategy.tv_id == tv_id).first()
    
    # =========================================================================
    # VALIDATION CHECKS
    # =========================================================================
    
    def check_market_hours(self) -> Tuple[bool, str]:
        """
        Check if market is open (within configured hours and on allowed days).
        Returns (allowed, reason).
        """
        now_bru = datetime.now(BRUSSELS_TZ)
        now_time = now_bru.time()
        
        # Get settings
        settings = self.get_global_settings()
        
        # Day of week check (replaces hardcoded weekend check)
        day_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        current_day = day_names[now_bru.weekday()]
        enabled_days = settings.get("trading_days", ["MON", "TUE", "WED", "THU", "FRI"])
        
        if current_day not in enabled_days:
            day_full = now_bru.strftime("%A")
            return False, f"Trading disabled on {day_full}"
        
        # Market hours check
        try:
            open_h, open_m = map(int, settings["market_open_time"].split(':'))
            close_h, close_m = map(int, settings["market_close_time"].split(':'))
            market_open = time(open_h, open_m)
            market_close = time(close_h, close_m)
            
            if now_time < market_open:
                return False, f"Market Closed (Before {settings['market_open_time']})"
            if now_time >= market_close:
                return False, f"Market Closed (After {settings['market_close_time']})"
        except Exception as e:
            print(f"Market hours parse error: {e}")
            # Default: closed after 22:00
            if now_time >= time(22, 0):
                return False, "Market Closed (> 22:00)"
        
        return True, "OK"
    
    def check_blocked_periods(self) -> Tuple[bool, str]:
        """
        Check if current time is in a blocked period.
        Returns (allowed, reason).
        """
        settings = self.get_global_settings()
        
        if not settings.get("blocked_periods_enabled", True):
            return True, "OK"
        
        now_bru = datetime.now(BRUSSELS_TZ).time()
        
        for block in settings.get("blocked_periods", []):
            # Respect the 'enabled' flag added recently
            if not block.get("enabled", True):
                continue
                
            try:
                start_h, start_m = map(int, block["start"].split(':'))
                end_h, end_m = map(int, block["end"].split(':'))
                t_start = time(start_h, start_m)
                t_end = time(end_h, end_m)
                
                # Handle midnight crossing
                if t_start > t_end:
                    if now_bru >= t_start or now_bru <= t_end:
                        return False, f"Blocked Time ({block['start']}-{block['end']})"
                else:
                    if t_start <= now_bru <= t_end:
                        return False, f"Blocked Time ({block['start']}-{block['end']})"
            except Exception as e:
                print(f"Block parse error: {e}")
                continue
        
        return True, "OK"
    
    def check_account_enabled(self, account_id: int) -> Tuple[bool, str]:
        """
        Check if account has trading enabled.
        Returns (allowed, reason).
        """
        settings = self.get_account_settings(account_id)
        if not settings:
            # No settings = not configured = reject
            return False, f"Account {account_id} not configured"
        
        if not settings.trading_enabled:
            return False, f"Trading disabled for account {account_id}"
        
        return True, "OK"
    
    def check_strategy_enabled(self, account_id: int, strategy_tv_id: str) -> Tuple[bool, str]:
        """
        Check if strategy is configured and enabled for this account.
        Returns (allowed, reason).
        """
        config = self.get_strategy_config(account_id, strategy_tv_id)
        if not config:
            return False, f"Strategy '{strategy_tv_id}' not configured for account {account_id}"
        
        if not config.enabled:
            return False, f"Strategy '{strategy_tv_id}' disabled for account {account_id}"
        
        return True, "OK"
    
    def check_session_allowed(self, account_id: int, strategy_tv_id: str) -> Tuple[bool, str]:
        """
        Check if current trading session is allowed for this strategy.
        Returns (allowed, reason).
        """
        current_session = self.get_current_session()
        config = self.get_strategy_config(account_id, strategy_tv_id)
        
        if not current_session:
            # Outside all sessions - check if allowed for this strategy
            if config and config.allow_outside_sessions:
                return True, "OK (outside sessions - allowed)"
            return False, "Outside trading sessions"
        
        if not config:
            return False, f"Strategy not configured"
        
        allowed_sessions = [s.strip().upper() for s in config.allowed_sessions.split(',')]
        
        if current_session.upper() not in allowed_sessions:
            return False, f"Session {current_session} not allowed (enabled: {', '.join(allowed_sessions)})"
        
        return True, "OK"
    
    async def check_open_position(self, account_id: int, ticker: str, topstep_client) -> Tuple[bool, str]:
        """
        Check if there's already an open position for this ticker on this account.
        Returns (allowed, reason).
        """
        # Check if this rule is enabled
        settings = self.get_global_settings()
        if not settings.get("enforce_single_position_per_asset", True):
            return True, "OK (multiple positions allowed)"
        
        try:
            positions = await topstep_client.get_open_positions(account_id)
            
            # Normalize ticker (e.g. MNQ1! -> MNQ)
            clean_ticker = ticker.replace("1!", "").replace("2!", "")
            
            for pos in positions:
                contract_name = pos.get('contractId', '')
                if clean_ticker.upper() in contract_name.upper():
                    return False, f"Position already open for {ticker} on account {account_id}"
            
            return True, "OK"
        except Exception as e:
            return False, f"Failed to check positions: {e}"
    
    async def check_cross_account_direction(
        self, 
        ticker: str, 
        direction: str,  # BUY or SELL
        exclude_account_id: int,
        topstep_client
    ) -> Tuple[bool, str]:
        """
        Check if any other account has an opposing position on this ticker.
        This prevents long/short conflicts across accounts.
        Returns (allowed, reason).
        """
        # Check if this rule is enabled
        settings = self.get_global_settings()
        if not settings.get("block_cross_account_opposite", True):
            return True, "OK (cross-account check disabled)"
        
        try:
            # Get all accounts we know about
            all_accounts = self.db.query(AccountSettings).all()
            clean_ticker = ticker.replace("1!", "").replace("2!", "").upper()
            
            # Determine our side (1=Long, 2=Short in TopStep API)
            our_side = 1 if direction.upper() in ["BUY", "LONG"] else 2
            
            for account in all_accounts:
                if account.account_id == exclude_account_id:
                    continue
                
                positions = await topstep_client.get_open_positions(account.account_id)
                for pos in positions:
                    contract_name = pos.get('contractId', '').upper()
                    if clean_ticker in contract_name:
                        pos_side = pos.get('type', 0)  # 1=Long, 2=Short
                        
                        # Check for opposing direction
                        if pos_side != our_side and pos_side in [1, 2]:
                            side_name = "LONG" if pos_side == 1 else "SHORT"
                            return False, f"Conflicting {side_name} position on {ticker} in account {account.account_id}"
            
            return True, "OK"
        except Exception as e:
            return False, f"Failed to check cross-account positions: {e}"
    
    async def check_contract_limit(
        self, 
        account_id: int, 
        ticker: str, 
        quantity: int,
        topstep_client
    ) -> Tuple[bool, str]:
        """
        Check if opening this position would exceed account's contract limit.
        Uses micro_equivalent from TickerMap (1 for micro, 10 for mini).
        Returns (allowed, reason).
        """
        from backend.database import TickerMap
        
        try:
            # Get account settings for max_contracts
            account_settings = self.get_account_settings(account_id)
            if not account_settings:
                return False, f"Account {account_id} not configured"
            
            max_contracts = account_settings.max_contracts or 50
            
            # Get current open positions
            positions = await topstep_client.get_open_positions(account_id)
            
            # Calculate current usage in micro-equivalent
            current_usage = 0
            for pos in positions:
                pos_contract_id = pos.get('contractId', '')
                pos_size = pos.get('size', 0)
                
                # Find micro_equivalent from TickerMap
                ticker_map = self.db.query(TickerMap).filter(
                    TickerMap.ts_contract_id == pos_contract_id
                ).first()
                
                micro_eq = ticker_map.micro_equivalent if ticker_map else 1
                current_usage += pos_size * micro_eq
            
            # Calculate new position micro-equivalent
            clean_ticker = ticker.replace("1!", "").replace("2!", "")
            new_ticker_map = self.db.query(TickerMap).filter(
                TickerMap.tv_ticker == ticker
            ).first()
            
            new_micro_eq = new_ticker_map.micro_equivalent if new_ticker_map else 1
            new_usage = quantity * new_micro_eq
            
            # Check if would exceed limit
            total_usage = current_usage + new_usage
            if total_usage > max_contracts:
                return False, f"Contract limit exceeded: {current_usage} + {new_usage} = {total_usage} > {max_contracts} max"
            
            return True, f"OK ({total_usage}/{max_contracts} after trade)"
        except Exception as e:
            return False, f"Failed to check contract limit: {e}"
    
    # =========================================================================
    # POSITION SIZING
    # =========================================================================
    
    def calculate_position_size(
        self, 
        entry_price: float, 
        sl_price: float, 
        risk_amount: float, 
        tick_size: float, 
        tick_value: float
    ) -> int:
        """
        Calculate lot size based on risk amount and stop distance.
        Risk Per Contract = (Distance / Tick_Size) * Tick_Value
        """
        stop_distance = abs(entry_price - sl_price)
        if stop_distance == 0 or tick_size == 0:
            return 0
        
        ticks_at_risk = stop_distance / tick_size
        risk_per_contract = ticks_at_risk * tick_value
        
        if risk_per_contract == 0:
            return 0
        
        qty = int(risk_amount // risk_per_contract)
        return max(1, qty) if qty > 0 else 0
    
    def get_risk_amount(self, account_id: int, strategy_tv_id: str) -> float:
        """
        Calculate effective risk amount for a trade.
        Risk = Account Base Risk * Strategy Risk Factor
        """
        account_settings = self.get_account_settings(account_id)
        base_risk = account_settings.risk_per_trade if account_settings else 200.0
        
        config = self.get_strategy_config(account_id, strategy_tv_id)
        factor = config.risk_factor if config else 1.0
        
        return base_risk * factor
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    def log(self, message: str, level: str = "INFO"):
        """Add a log entry to database."""
        from backend.database import Log
        self.db.add(Log(level=level, message=message))
        self.db.commit()
