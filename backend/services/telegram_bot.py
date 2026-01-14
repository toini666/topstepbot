
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
        elif command == "/status_all":
            await self.cmd_status_all()
        elif command == "/flatten":
            await self.cmd_flatten()
        elif command == "/flatten_all":
            await self.cmd_flatten_all()
        elif command == "/cancel_orders":
            await self.cmd_cancel_orders()
        elif command == "/cancel_all":
            await self.cmd_cancel_all()
        elif command == "/on":
            await self.cmd_set_trading(True)
        elif command == "/off":
            await self.cmd_set_trading(False)
        elif command == "/on_all":
            await self.cmd_set_trading_all(True)
        elif command == "/off_all":
            await self.cmd_set_trading_all(False)
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
            "/status - Current account status\n"
            "/status_all - All accounts overview\n"
            "/accounts - List all accounts\n\n"
            "<b>Trading Control</b>\n"
            "/on - Enable trading (current account)\n"
            "/off - Disable trading (current account)\n"
            "/on_all - Enable trading (ALL accounts)\n"
            "/off_all - Disable trading (ALL accounts)\n"
            "/switch [ID] - Switch active account\n\n"
            "<b>Connection</b>\n"
            "/login - Connect to TopStep\n"
            "/logout - Disconnect from TopStep\n\n"
            "<b>Emergency</b>\n"
            "/cancel_orders - Cancel orders (current account)\n"
            "/cancel_all - Cancel orders (ALL accounts)\n"
            "/flatten - Close positions (current account)\n"
            "/flatten_all - 🚨 FLATTEN ALL ACCOUNTS"
        )
        await self.reply(msg)

    async def cmd_status(self):
        db = SessionLocal()
        try:
            # Get selected account
            acc_setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
            if not acc_setting:
                await self.reply("⚠️ No Account Selected")
                return
            
            account_id = int(acc_setting.value)
            
            # Get account trading status from AccountSettings
            from backend.database import AccountSettings
            account_settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
            is_trading_on = account_settings and account_settings.trading_enabled
            status_emoji = "🟢 Trading ON" if is_trading_on else "🔴 Trading OFF"
            
            # Check connection first
            if not topstep_client.token:
                if not await topstep_client.login():
                    await self.reply(f"📊 <b>System Status</b>\n{status_emoji}\n\n❌ <b>Disconnected from TopStep</b>\nUse /login to connect.")
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
            
            # Positions & PnL
            positions = await topstep_client.get_open_positions(account_id)
            daily_pnl = await self._get_daily_pnl(account_id)
            
            msg = (
                f"📊 <b>System Status</b>\n"
                f"{status_emoji}\n"
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

    async def cmd_set_trading(self, enable: bool):
        """Toggle trading_enabled on the SELECTED account."""
        db = SessionLocal()
        try:
            # Get selected account
            acc_setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
            if not acc_setting:
                await self.reply("❌ No account selected. Use /switch [ID]")
                return
            
            account_id = int(acc_setting.value)
            
            # Update account settings
            from backend.database import AccountSettings
            account = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
            if not account:
                await self.reply(f"❌ Account {account_id} not configured in settings")
                return
            
            account.trading_enabled = enable
            db.commit()
            
            account_name = account.account_name or str(account_id)
            state = "🟢 ENABLED" if enable else "🔴 DISABLED"
            await self.reply(f"✅ Trading {state} for {account_name}")
            
            # Log Action
            db.add(Log(level="WARNING", message=f"Telegram: Trading {'enabled' if enable else 'disabled'} for account {account_name}"))
            db.commit()
        except Exception as e:
            await self.reply(f"❌ Error: {e}")
        finally:
            db.close()

    async def cmd_set_trading_all(self, enable: bool):
        """Toggle trading_enabled on ALL accounts."""
        db = SessionLocal()
        try:
            from backend.database import AccountSettings
            accounts = db.query(AccountSettings).all()
            
            if not accounts:
                await self.reply("⚠️ No accounts configured")
                return
            
            count = 0
            for acc in accounts:
                acc.trading_enabled = enable
                count += 1
            
            db.commit()
            
            state = "🟢 ENABLED" if enable else "🔴 DISABLED"
            await self.reply(f"✅ Trading {state} for {count} account(s)")
            
            # Log Action
            db.add(Log(level="WARNING", message=f"Telegram: Trading {'enabled' if enable else 'disabled'} for ALL {count} accounts"))
            db.commit()
        except Exception as e:
            await self.reply(f"❌ Error: {e}")
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
            
            # Get account name
            from backend.database import AccountSettings
            account_settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
            account_name = account_settings.account_name if account_settings and account_settings.account_name else str(account_id)
            
            # 1. Cancel Orders and count
            orders_cancelled = await topstep_client.cancel_all_orders(account_id)
            
            # 2. Close Positions
            positions = await topstep_client.get_open_positions(account_id)
            positions_closed = 0
            for pos in positions:
                contract_id = pos.get('contractId')
                qty = pos.get('size', pos.get('quantity'))
                p_type = pos.get('type')
                
                action = "SELL" if str(p_type) == '1' else "BUY"
                
                await topstep_client.place_order(
                    ticker=contract_id,
                    action=action,
                    quantity=qty,
                    account_id=account_id,
                    contract_id=contract_id
                )
                positions_closed += 1
            
            await self.reply(f"✅ <b>Flatten Complete</b>\n📍 Closed {positions_closed} position(s)\n📋 Cancelled {orders_cancelled} order(s)\n💼 Account: {account_name}")
            
            # Log Action
            db.add(Log(level="WARNING", message=f"Telegram: Flatten Executed on {account_name} ({positions_closed} pos, {orders_cancelled} orders)"))
            db.commit()

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
            if not setting:
                await self.reply("❌ No account selected.")
                return
            account_id = int(setting.value)
            
            # Get account name
            from backend.database import AccountSettings
            account_settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
            account_name = account_settings.account_name if account_settings and account_settings.account_name else str(account_id)
            
            count = await topstep_client.cancel_all_orders(account_id)
            await self.reply(f"✅ Cancelled {count} order(s) on {account_name}")
            
            # Log Action
            db.add(Log(level="WARNING", message=f"Telegram: Cancelled {count} orders on {account_name}"))
            db.commit()
        except Exception as e:
            await self.reply(f"❌ Error: {e}")
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

                # Log Action
                db.add(Log(level="WARNING", message=f"Telegram: Switched to Account {new_id}"))
                db.commit()
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

    # --- MULTI-ACCOUNT COMMANDS ---

    async def cmd_status_all(self):
        """Show status of ALL accounts."""
        try:
            if not topstep_client.token:
                if not await topstep_client.login():
                    await self.reply("❌ Not connected to TopStep. Use /login")
                    return
            
            accounts_list = await topstep_client.get_accounts()
            if not accounts_list:
                await self.reply("⚠️ No accounts found")
                return

            # Get per-account trading status
            db = SessionLocal()
            try:
                from backend.database import AccountSettings
                account_settings_map = {}
                for acc_settings in db.query(AccountSettings).all():
                    account_settings_map[acc_settings.account_id] = acc_settings.trading_enabled
            finally:
                db.close()

            msg = f"📊 <b>All Accounts Status</b>\n\n"
            
            total_pnl = 0.0
            total_positions = 0
            
            for acc in accounts_list:
                acc_id = int(acc.get('id'))
                acc_name = acc.get('name', str(acc_id))
                balance = acc.get('balance', 0)
                
                # Trading status for this account
                is_trading_on = account_settings_map.get(acc_id, False)
                trading_status = "🟢" if is_trading_on else "🔴"
                
                # Get positions & PnL for this account
                positions = await topstep_client.get_open_positions(acc_id)
                daily_pnl = await self._get_daily_pnl(acc_id)
                total_pnl += daily_pnl
                total_positions += len(positions)
                
                pos_str = f"{len(positions)} pos" if positions else "Flat"
                
                msg += f"{trading_status} <b>{acc_name}</b>\n"
                msg += f"   💰 ${balance:,.2f} | PnL: ${daily_pnl:,.2f} | {pos_str}\n"
            
            pnl_total_emoji = "🟢" if total_pnl >= 0 else "🔴"
            msg += f"\n<b>TOTAL:</b> {pnl_total_emoji} ${total_pnl:,.2f} PnL | {total_positions} position(s)"
            
            await self.reply(msg)
            
        except Exception as e:
            await self.reply(f"❌ Error: {e}")

    async def cmd_flatten_all(self):
        """Flatten ALL accounts - emergency command."""
        await self.reply("🚨 <b>FLATTENING ALL ACCOUNTS...</b>")
        db = SessionLocal()
        
        try:
            accounts_list = await topstep_client.get_accounts()
            if not accounts_list:
                await self.reply("⚠️ No accounts found")
                return
            
            results = []
            
            for acc in accounts_list:
                acc_id = int(acc.get('id'))
                acc_name = acc.get('name', str(acc_id))
                
                try:
                    # 1. Cancel all orders
                    orders_cancelled = await topstep_client.cancel_all_orders(acc_id)
                    
                    # 2. Close all positions
                    positions = await topstep_client.get_open_positions(acc_id)
                    positions_closed = 0
                    
                    for pos in positions:
                        contract_id = pos.get('contractId')
                        qty = pos.get('size', pos.get('quantity'))
                        p_type = pos.get('type')
                        
                        action = "SELL" if str(p_type) == '1' else "BUY"
                        
                        await topstep_client.place_order(
                            ticker=contract_id,
                            action=action,
                            quantity=qty,
                            account_id=acc_id,
                            contract_id=contract_id
                        )
                        positions_closed += 1
                    
                    results.append(f"• {acc_name}: {positions_closed} pos, {orders_cancelled} orders")
                    
                except Exception as e:
                    results.append(f"• {acc_name}: ⚠️ Error - {e}")
            
            msg = "✅ <b>Flatten Complete</b>\n" + "\n".join(results)
            await self.reply(msg)
            
            # Log Action
            db.add(Log(level="WARNING", message=f"Telegram: Flatten ALL Executed"))
            db.commit()
            
        except Exception as e:
            await self.reply(f"❌ Flatten Error: {e}")
        finally:
            db.close()

    async def cmd_cancel_all(self):
        """Cancel orders on ALL accounts."""
        db = SessionLocal()
        try:
            accounts_list = await topstep_client.get_accounts()
            if not accounts_list:
                await self.reply("⚠️ No accounts found")
                return
            
            results = []
            
            for acc in accounts_list:
                acc_id = int(acc.get('id'))
                acc_name = acc.get('name', str(acc_id))
                try:
                    count = await topstep_client.cancel_all_orders(acc_id)
                    results.append(f"• {acc_name}: {count} order(s)")
                except Exception as e:
                    results.append(f"• {acc_name}: ⚠️ Error")
                    print(f"Cancel error for account {acc_id}: {e}")
            
            msg = "✅ <b>Cancelled Orders</b>\n" + "\n".join(results)
            await self.reply(msg)
            
            # Log Action
            db.add(Log(level="WARNING", message=f"Telegram: Cancel ALL Orders Executed"))
            db.commit()
        except Exception as e:
            await self.reply(f"❌ Error: {e}")
        finally:
            db.close()


telegram_bot = TelegramBot()
