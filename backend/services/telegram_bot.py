
import asyncio
import os
import httpx
from backend.services.telegram_service import telegram_service
from backend.services.topstep_client import topstep_client
from backend.services.risk_engine import RiskEngine
from backend.database import SessionLocal, Setting, Log

class TelegramBot:
    def __init__(self):
        self.polling_active = False
        self.last_update_id = 0
        self.admin_id = os.getenv("TELEGRAM_ID")
        # Reuse the sender service for replies
        self.sender = telegram_service

    async def start_polling(self):
        """Starts the infinite polling loop."""
        if not self.sender.bot_token or not self.admin_id:
            print("⚠️ Telegram Bot Token or Admin ID missing. Polling disabled.")
            return

        self.polling_active = True
        print("🤖 Telegram Bot Polling Started...")
        
        # Clean shutdown handling
        while self.polling_active:
            try:
                await self.poll_once()
            except Exception as e:
                print(f"Polling Error: {e}")
                await asyncio.sleep(5) # Backoff
            
            # Small sleep to prevent tight loop if network is fast/cached
            await asyncio.sleep(1)

    def stop_polling(self):
        self.polling_active = False

    async def poll_once(self):
        url = f"{self.sender.base_url}/getUpdates"
        params = {
            "offset": self.last_update_id + 1,
            "timeout": 30, # Long polling
            "allowed_updates": ["message"]
        }
        
        async with httpx.AsyncClient(timeout=40) as client:
            try:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        for result in data.get("result", []):
                            self.last_update_id = result["update_id"]
                            await self.handle_update(result)
            except httpx.ReadTimeout:
                pass # Normal timeout
            except Exception as e:
                print(f"Telegram Connection Error: {e}")

    async def handle_update(self, update):
        message = update.get("message")
        if not message:
            return

        # Security Check
        sender_id = str(message.get("from", {}).get("id"))
        if sender_id != str(self.admin_id):
            print(f"⚠️ Unauthorized command attempt from: {sender_id}")
            return # Ignore silent

        text = message.get("text", "").strip()
        if not text.startswith("/"):
            return # Ignore non-commands

        parts = text.split()
        command = parts[0].lower()
        args = parts[1:]

        print(f"📩 Telegram Command: {command} {args}")
        
        if command == "/start" or command == "/help":
            await self.cmd_help()
        elif command == "/status":
            await self.cmd_status()
        elif command == "/flatten":
            await self.cmd_flatten()
        elif command == "/cancel_orders":
            await self.cmd_cancel_orders()
        elif command == "/on":
            await self.cmd_set_master_switch(True)
        elif command == "/off":
            await self.cmd_set_master_switch(False)
        elif command == "/accounts":
            await self.cmd_accounts()
        elif command == "/switch":
            await self.cmd_switch(args)
        elif command == "/login":
            await self.cmd_login()
        elif command == "/logout":
            await self.cmd_logout()
        else:
            await self.reply(f"❌ Unknown command: {command}")

    async def reply(self, text):
        await self.sender.send_message(text)

    # --- COMMAND HANDLERS ---

    async def cmd_help(self):
        msg = (
            "🤖 <b>Bot Commands</b>\n\n"
            "<b>Monitoring</b>\n"
            "/status - Account balance, PnL, Positions\n"
            "/accounts - List all accounts\n\n"
            "<b>Control</b>\n"
            "/on - Enable Trading (Master Switch)\n"
            "/off - Disable Trading\n"
            "/login - Connect to TopStep\n"
            "/logout - Disconnect from TopStep\n"
            "/switch [ID] - Switch Active Account\n\n"
            "<b>Emergency</b>\n"
            "/cancel_orders - Cancel OPEN orders (keep positions)\n"
            "/flatten - 🚨 CLOSE ALL POSITIONS & CANCEL ORDERS"
        )
        await self.reply(msg)

    async def cmd_status(self):
        db = SessionLocal()
        try:
            # 1. Get Master Switch
            # 1. Get Master Switch
            switch = db.query(Setting).filter(Setting.key == "master_switch").first()
            # Dashboard uses "ON"/"OFF"
            is_on = switch and switch.value == "ON"
            status_emoji = "🟢 ON" if is_on else "🔴 OFF"

            # 2. Get Account
            acc_setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
            if not acc_setting:
                await self.reply("⚠️ No Account Selected")
                return
            
            account_id = int(acc_setting.value)
            
            # 3. Fetch Data
            # Check connection first
            if not topstep_client.token:
                # Try auto-login
                if not await topstep_client.login():
                     await self.reply(f"📊 <b>System Status</b>\nMaster Switch: {status_emoji}\n\n❌ <b>Disconnected from TopStep</b>\nUse /login to connect.")
                     return

            # Refresh account info
            accounts_list = await topstep_client.get_accounts()
            account_name = f"Account {account_id}"
            balance = 0.0
            
            # Find account in list
            for acc in accounts_list:
                 if int(acc.get('id')) == account_id:
                     account_name = acc.get('name')
                     balance = acc.get('balance', 0)
                     break
            
            # 4. Positions & Orders & PnL
            positions = await topstep_client.get_open_positions(account_id)
            daily_pnl = await self._get_daily_pnl(account_id)
            
            msg = (
                f"📊 <b>System Status</b>\n"
                f"Master Switch: {status_emoji}\n"
                f"Account: <b>{account_name}</b>\n"
                f"Balance: <b>${balance:,.2f}</b>\n"
                f"Daily PnL: <b>${daily_pnl:,.2f}</b>\n\n"
            )
            
            if positions:
                msg += "📈 <b>Open Positions:</b>\n"
                for p in positions:
                    # API Key 'type': 1=Long, 2=Short
                    # API Key 'averagePrice' for entry
                    raw_type = str(p.get('type', p.get('side'))) 
                    
                    if raw_type in ['1', 'Buy', 'LONG']: 
                        side_icon = "🟢 LONG"
                    elif raw_type in ['2', 'Sell', 'SHORT']: 
                        side_icon = "🔴 SHORT"
                    else: 
                        side_icon = f"⚪ {raw_type}"
                    
                    price = p.get('averagePrice', p.get('price'))
                    qty = p.get('size', p.get('quantity'))
                    contract = p.get('contractId', p.get('symbol'))
                    
                    msg += f"• {contract}: {side_icon} x{qty} @ {price}\n"
            else:
                msg += "✅ No Open Positions"
                
            await self.reply(msg)

        except Exception as e:
            await self.reply(f"❌ Error fetching status: {e}")
        finally:
            db.close()

    async def _get_daily_pnl(self, account_id):
        try:
            # Fetch "Today's" trades
            trades = await topstep_client.get_historical_trades(account_id, days=1)
            total_pnl = 0.0
            total_fees = 0.0
            
            for t in trades:
                pnl = t.get('profitAndLoss') or t.get('pnl')
                if pnl is not None:
                    total_pnl += float(pnl)
                
                f = t.get('fees')
                if f: total_fees += float(f)
            
            # Net PnL = Gross PnL - Fees
            return total_pnl - total_fees
        except Exception as e:
            print(f"PnL Calc Error: {e}")
            return 0.0

    async def cmd_set_master_switch(self, enable: bool):
        db = SessionLocal()
        try:
            val = "ON" if enable else "OFF"
            setting = db.query(Setting).filter(Setting.key == "master_switch").first()
            if not setting:
                setting = Setting(key="master_switch", value=val)
                db.add(setting)
            else:
                setting.value = val
            db.commit()
            
            state = "🟢 ENABLED" if enable else "🔴 DISABLED"
            await self.reply(f"✅ Master Switch {state}")
        except Exception as e:
            await self.reply(f"❌ Failed to toggle switch: {e}")
        finally:
            db.close()

    async def cmd_flatten(self):
        await self.reply("🚨 <b>FLATTENING ALL POSITIONS...</b>")
        db = SessionLocal()
        try:
            setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
            if not setting:
                await self.reply("❌ No account selected.")
                return
            
            account_id = int(setting.value)
            
            # Use Risk Engine logic manually? or just call client?
            # Client flatten is easiest.
            # 1. Cancel Orders
            await topstep_client.cancel_all_orders(account_id)
            
            # 2. Close Positions
            positions = await topstep_client.get_open_positions(account_id)
            count = 0
            for pos in positions:
                # Invert side? 
                # contractId is needed.
                # TopStepClient likely handles flattening? No, we implemented 'flatten_position' usually.
                # Let's use the raw implementation here to be safe and explicit.
                contract_id = pos.get('contractId')
                qty = pos.get('size', pos.get('quantity'))
                # Fix: Use 'type' for direction (1=Long, 2=Short)
                # If Long (1), we SELL. If Short (2), we BUY.
                p_type = pos.get('type')
                
                action = "SELL" # Default Close Long
                if str(p_type) == '2': # Short
                    action = "BUY"
                elif str(p_type) == '1': # Long
                    action = "SELL"
                else:
                    # Fallback check
                    raw_side = str(pos.get('side')).upper()
                    if raw_side in ['1', '2', 'SELL', 'SHORT']:
                        action = "BUY"
                
                await topstep_client.place_order(
                    ticker=contract_id, # Use ID directly
                    action=action,
                    quantity=qty,
                    account_id=account_id,
                    contract_id=contract_id # Optimization
                )
                count += 1
            
            await self.reply(f"✅ Flatten Complete. Closed {count} positions and cancelled orders.")

        except Exception as e:
            await self.reply(f"❌ Flatten Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()

    async def cmd_cancel_orders(self):
        db = SessionLocal()
        try:
            setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
            if not setting: return
            account_id = int(setting.value)
            
            await topstep_client.cancel_all_orders(account_id)
            await self.reply("✅ All working orders cancelled.")
        finally:
            db.close()

    async def cmd_accounts(self):
        accounts_list = await topstep_client.get_accounts()
        msg = "💳 <b>Available Accounts:</b>\n"
        
        # Get Current
        db = SessionLocal()
        curr_id = 0
        try:
            s = db.query(Setting).filter(Setting.key == "selected_account_id").first()
            if s: curr_id = int(s.value)
        finally:
            db.close()
            
        for acc in accounts_list:
            aid = int(acc.get('id'))
            name = acc.get('name')
            marker = "✅ " if aid == curr_id else ""
            msg += f"{marker}<code>{aid}</code>: {name}\n"
            
        msg += "\nUse <code>/switch ID</code> to change."
        await self.reply(msg)

    async def cmd_switch(self, args):
        if not args:
            await self.reply("❌ Usage: /switch [ACCOUNT_ID]")
            return
            
        new_id_str = args[0]
        try:
            new_id = int(new_id_str)
            # Notify Client/DB
            # We reuse the logic that the Dashboard would use (Setting DB)
            db = SessionLocal()
            try:
                setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
                if not setting:
                    setting = Setting(key="selected_account_id", value=str(new_id))
                    db.add(setting)
                else:
                    setting.value = str(new_id)
                db.commit()
                
                # Update Client state
                topstep_client.account_id = new_id
                
                await self.reply(f"✅ Switched to Account ID: {new_id}")
            finally:
                db.close()
                
        except ValueError:
             await self.reply("❌ Invalid ID format")
        except Exception as e:
             await self.reply(f"❌ Error switching: {e}")

    async def cmd_login(self):
        await self.reply("🔄 Connecting to TopStep...")
        try:
            success = await topstep_client.login()
            if success:
                await self.reply("✅ Connected successfully!")
            else:
                 await self.reply("❌ Login Failed. Check logs/credentials.")
        except Exception as e:
            await self.reply(f"❌ Login Error: {e}")

    async def cmd_logout(self):
        await topstep_client.logout()
        await self.reply("🔌 Disconnected.")

telegram_bot = TelegramBot()
