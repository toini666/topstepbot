import httpx
import os
import asyncio
from backend.database import SessionLocal, Log

class TelegramService:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_ID")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        if self.bot_token and self.chat_id:
            print(f"✅ Telegram Service Initialized for Chat ID: {self.chat_id}")
        else:
            print("⚠️ Telegram Credentials Missing in .env")

    async def send_message(self, message: str):
        """Sends a raw message to Telegram."""
        if not self.bot_token or not self.chat_id:
            print("Telegram credentials missing. Skipping notification.")
            return

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10)
                if response.status_code != 200:
                    self._log_error(f"Failed to send Telegram message: {response.text}")
            except Exception as e:
                self._log_error(f"Telegram Send Error: {e}")

    def _log_error(self, message: str):
        db = SessionLocal()
        try:
            db.add(Log(level="ERROR", message=message))
            db.commit()
        except Exception:
            pass
        finally:
            db.close()

    async def notify_startup(self):
        msg = "🤖 <b>TopStep Bot Online</b>\nSystem is ready to trade."
        await self.send_message(msg)
        print("📨 Telegram Startup Message Sent")

    async def notify_shutdown(self):
        msg = "🛑 <b>TopStep Bot Shutting Down</b>\nSystem is offline."
        await self.send_message(msg)

    async def notify_signal(self, ticker: str, action: str, price: float, sl: float, tp: float):
        emoji = "🟢" if action.upper() == "BUY" else "🔴"
        msg = (
            f"⚡ <b>Signal Received</b>\n"
            f"{emoji} <b>{action.upper()} {ticker}</b>\n"
            f"Price: {price}\n"
            f"SL: {sl} | TP: {tp}"
        )
        await self.send_message(msg)

    async def notify_order_submitted(self, ticker: str, action: str, quantity: int, price: float, order_id: str):
        # Notify that order was sent to broker (Price is Requested Price, not Fill)
        amount_str = f"{action} {quantity}x {ticker}"
        msg = f"🚀 <b>Order Submitted</b>\n{amount_str} @ {price}\nOrder ID: {order_id}"
        await self.send_message(msg)

    async def notify_position_opened(self, symbol: str, side: str, quantity: int, price: float, order_id: str = None):
        # Notify real fill
        side_upper = str(side).upper()
        if "BUY" in side_upper or "LONG" in side_upper:
            emoji = "🔵"
        else:
            emoji = "🟠"
            
        msg = (
            f"{emoji} <b>Position Opened: {symbol}</b>\n"
            f"{side_upper} {quantity}x @ {price:.2f}\n" 
            f"<i>Filled</i>"
        )
        await self.send_message(msg)

    async def notify_trade_rejection(self, ticker: str, reason: str):
        msg = (
            f"❌ <b>Trade Rejected</b>\n"
            f"Ticker: {ticker}\n"
            f"Reason: {reason}"
        )
        await self.send_message(msg)

    async def notify_position_closed(self, symbol: str, side: str, entry_price: float, exit_price: float, pnl: float, quantity: int, fees: float = 0.0):
        pnl_val = pnl if pnl is not None else 0.0
        pnl_emoji = "💰" if pnl_val >= 0 else "💸"
        
        # Handle 'side' being int or str
        side_str = str(side).upper()
        
        # Enhance Side Emoji
        if "BUY" in side_str or "LONG" in side_str:
            side_emoji = "🟢"
        elif "SELL" in side_str or "SHORT" in side_str:
            side_emoji = "🔴"
        else:
            side_emoji = "⚪"
        
        msg = (
            f"{pnl_emoji} <b>Position Closed: {symbol}</b>\n"
            f"{side_emoji} {side_str} x {quantity}\n"
        )
        
        if entry_price > 0:
            msg += f"Entry: {entry_price:.2f} -> Exit: {exit_price:.2f}\n"
        else:
            msg += f"Exit Price: {exit_price:.2f}\n"
            
        msg += f"<b>PnL: ${pnl_val:.2f}</b>\n"
        msg += f"<i>Fees: ${fees:.2f}</i>"
        
        await self.send_message(msg)
        
    async def notify_error(self, error_msg: str):
        msg = f"⚠️ <b>System Error</b>\n{error_msg}"
        await self.send_message(msg)

    async def notify_orphaned_orders(self, orders: list):
        """
        Notifies about working orders that have no matching open position.
        """
        if not orders:
            return
            
        msg = "⚠️ <b>Orphaned Orders Detected</b>\n"
        msg += "Orders active without open positions:\n\n"
        
        for o in orders:
            # Try to get symbol/contract
            symbol = o.get('symbol') or o.get('contractId') or "Unknown"
            side = o.get('action') or o.get('side') or "Limit"
            price = o.get('price') or o.get('stopPrice') or "Mkt"
            qty = o.get('qty') or o.get('quantity') or "?"
            
            msg += f"• <b>{symbol}</b>: {side} {qty} @ {price}\n"
            
        msg += "\nCheck dashboard to cancel if not intended."
        await self.send_message(msg)

telegram_service = TelegramService()
