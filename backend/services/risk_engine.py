import json
from datetime import datetime, timezone, time
import pytz
from sqlalchemy.orm import Session
from backend.database import Setting, Trade, TradeStatus
from backend.schemas import RiskSettings, TimeBlock

# Define Brussels Timezone
BRUSSELS_TZ = pytz.timezone("Europe/Brussels")

class RiskEngine:
    def __init__(self, db: Session):
        self.db = db
        self.settings = self._load_settings()

    def _load_settings(self) -> RiskSettings:
        # 1. Master Switch
        switch_setting = self.db.query(Setting).filter(Setting.key == "master_switch").first()
        enabled = True
        if switch_setting and switch_setting.value == "OFF":
            enabled = False
            
        # 2. Risk Amount ($)
        risk_amt_setting = self.db.query(Setting).filter(Setting.key == "risk_amount").first()
        risk_amt = float(risk_amt_setting.value) if risk_amt_setting else 200.0
        
        # 3. Blocked Periods Enabled
        bp_enabled_setting = self.db.query(Setting).filter(Setting.key == "blocked_periods_enabled").first()
        bp_enabled = True
        if bp_enabled_setting and bp_enabled_setting.value == "false":
            bp_enabled = False

        # 4. Blocked Periods (JSON)
        blocked_setting = self.db.query(Setting).filter(Setting.key == "blocked_periods").first()
        blocked = [
            TimeBlock(start="08:55", end="09:15"),
            TimeBlock(start="15:25", end="15:45"),
            TimeBlock(start="21:30", end="00:15")
        ]
        
        if blocked_setting:
            try:
                data = json.loads(blocked_setting.value)
                blocked = [TimeBlock(**b) for b in data]
            except Exception as e:
                print(f"Error parsing blocked_periods: {e}")

        # 5. Auto Flatten Settings
        af_enabled_setting = self.db.query(Setting).filter(Setting.key == "auto_flatten_enabled").first()
        af_enabled = False
        if af_enabled_setting and af_enabled_setting.value == "true":
            af_enabled = True

        af_time_setting = self.db.query(Setting).filter(Setting.key == "auto_flatten_time").first()
        af_time = af_time_setting.value if af_time_setting else "21:55"
                
        return RiskSettings(
            trading_enabled=enabled,
            risk_per_trade=risk_amt,
            blocked_periods_enabled=bp_enabled,
            blocked_periods=blocked,
            auto_flatten_enabled=af_enabled,
            auto_flatten_time=af_time
        )

    def check_global_switch(self) -> tuple[bool, str]:
        if not self.settings.trading_enabled:
             return False, "Trading Disabled by Master Switch"
        return True, "OK"

    async def check_open_position(self, account_id: int, ticker: str, topstep_client) -> tuple[bool, str]:
        """
        Ensures no open position exists for this ticker.
        Requires TopStepClient instance to fetch positions.
        """
        try:
            positions = await topstep_client.get_open_positions(account_id)
            
            # Normalize Ticker (e.g. MNQ1! -> MNQ)
            clean_ticker = ticker.replace("1!", "").replace("2!", "")

            # print(f"Checking Positions for {ticker} (clean: {clean_ticker}) in {len(positions)} open positions.")
            
            for pos in positions:
                contract_name = pos.get('contractId', '') # e.g. "CON.F.US.MNQ.H26" or "MNQH6"
                
                # Check for substring match (e.g. MNQ in CON.F.US.MNQ.H26)
                # Case insensitive check
                if clean_ticker.upper() in contract_name.upper():
                    # print(f"MATCH: {clean_ticker} found in {contract_name}")
                    return False, f"Position already open for {ticker} ({contract_name})"
                    
            return True, "OK"
        except Exception as e:
             return False, f"Failed to check positions: {e}"

    def check_time_filters(self) -> tuple[bool, str]:
        """
        Returns True if trading is ALLOWED.
        Checks against configurable blocked periods.
        """
        now_bru_dt = datetime.now(BRUSSELS_TZ)
        now_bru = now_bru_dt.time()
        
        # 0. Weekend Block (Sat=5, Sun=6) - MANDATORY CHECK
        if now_bru_dt.weekday() >= 5:
             day_name = now_bru_dt.strftime("%A")
             return False, f"Market Closed (Weekend: {day_name})"

        # 1. Daily Market Closed Block (22:00 - 00:00) - MANDATORY
        # User confirmed market closed from 22:00 to midnight
        if now_bru >= time(22, 0):
             return False, "Market Closed (Daily: > 22:00)"

        # Feature Toggle Check
        if not self.settings.blocked_periods_enabled:
            return True, "OK"
        
        for block in self.settings.blocked_periods:
            try:
                # Parse strings "HH:MM" to time objects
                start_h, start_m = map(int, block.start.split(':'))
                end_h, end_m = map(int, block.end.split(':'))
                t_start = time(start_h, start_m)
                t_end = time(end_h, end_m)
                
                # Check if block crosses midnight (e.g. 21:30 to 00:15)
                if t_start > t_end:
                    # Block is [Start -> Midnight] OR [Midnight -> End]
                    if now_bru >= t_start or now_bru <= t_end:
                         return False, f"Blocked Time ({block.start}-{block.end})"
                else:
                    # Standard block within one day
                    if t_start <= now_bru <= t_end:
                        return False, f"Blocked Time ({block.start}-{block.end})"
                        
            except Exception as e:
                print(f"Time Filter Error parsing block {block}: {e}")
                continue
                
        return True, "OK"

    def calculate_position_size(self, entry_price: float, sl_price: float, risk_amount: float, tick_size: float, tick_value: float) -> int:
        """
        Calc lots based on risk amount using exact Contract Specifications.
        Risk Per Contract = (Distance / Tick_Size) * Tick_Value.
        """
        stop_distance = abs(entry_price - sl_price)
        if stop_distance == 0 or tick_size == 0:
            return 0
        
        # Calculate Risk Per Contract
        ticks_at_risk = stop_distance / tick_size
        risk_per_contract = ticks_at_risk * tick_value
        
        if risk_per_contract == 0:
            return 0
            
        qty = int(risk_amount // risk_per_contract)
        
        return max(1, qty) # Always return at least 1 if valid, or handle 0

    def log(self, message: str, level: str = "INFO"):
        """Adds a log entry."""
        # Logs are typically handled by DB now, this might be legacy or for internal class usage?
        # Preserving interface but effectively this class uses return values for logic.
        pass

    async def check_auto_flatten(self):
        """
        Checks if the current time matches the auto-flatten schedule.
        If matched (within 1-minute window), it closes all positions.
        """
        if not self.settings.auto_flatten_enabled or not self.settings.auto_flatten_time:
            return

        now_bru = datetime.now(BRUSSELS_TZ).strftime("%H:%M")
        
        # Check simple equality. Since the job runs every minute, this should hit.
        # Ideally we might checking if we are PAST the time but haven't run today, 
        # but stateless minute-check is simple and accepted for this MVP.
        if now_bru == self.settings.auto_flatten_time:
            print(f"⏰ Auto-Flatten Time Reached ({now_bru}). Flattening Account...")
            
            # Find selected account
            # Note: RiskEngine normally doesn't hold topstep_client instance, 
            # we need to import it or pass it. 
            # But main.py calls this. RiskEngine logic usually is pure or checks state.
            # However this method is distinct: it performs action. 
            # We will import topstep_client here to break circular deps if any.
            from backend.services.topstep_client import topstep_client
            from backend.database import Setting, Log
            
            # Get Account
            acct_setting = self.db.query(Setting).filter(Setting.key == "selected_account_id").first()
            if not acct_setting:
                print("Auto-Flatten Skipped: No Account Selected")
                return
            
            account_id = int(acct_setting.value)
            
            # Flatten
            try:
                # 1. Close Positions
                # We reuse the logic from dashboard.flatten_account_endpoint partially or calls API directly
                # Implementation: Close all positions.
                positions = await topstep_client.get_open_positions(account_id)
                if positions:
                    for pos in positions:
                        await topstep_client.close_position(account_id, pos['contractId'])
                    
                    self.db.add(Log(level="WARNING", message=f"AUTO-FLATTEN Triggered: Closed {len(positions)} positions."))
                    
                # 2. Cancel Orders
                orders = await topstep_client.get_orders(account_id, days=1)
                for order in orders:
                    if str(order.get('status')).upper() in ["WORKING", "ACCEPTED", "1", "6"]:
                         await topstep_client.cancel_order(account_id, order.get('id') or order.get('orderId'))
                
                self.db.add(Log(level="WARNING", message="AUTO-FLATTEN: Orders Cancelled."))
                self.db.commit()
                
                # Notify Telegram?
                from backend.services.telegram_service import telegram_service
                await telegram_service.send_message(f"⏰ <b>Auto-Flatten Executed</b>\nTarget time: {self.settings.auto_flatten_time}")
                
            except Exception as e:
                print(f"Auto-Flatten Failed: {e}")
                self.db.add(Log(level="ERROR", message=f"Auto-Flatten Failed: {e}"))
                self.db.commit()
