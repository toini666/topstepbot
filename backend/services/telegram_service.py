"""
Telegram Service - Trading Bot Notifications

Updated for multi-account execution with:
- PARTIAL signal notifications
- CLOSE signal notifications
- Timeframe in signal notifications
- Account name in all trade notifications
"""

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

    # =========================================================================
    # SYSTEM NOTIFICATIONS
    # =========================================================================

    async def notify_startup(self):
        msg = "🤖 <b>TopStep Bot Online</b>\nMulti-account system ready."
        await self.send_message(msg)
        print("📨 Telegram Startup Message Sent")

    async def notify_shutdown(self):
        msg = "🛑 <b>TopStep Bot Shutting Down</b>\nSystem is offline."
        await self.send_message(msg)

    async def notify_error(self, error_msg: str):
        msg = f"⚠️ <b>System Error</b>\n{error_msg}"
        await self.send_message(msg)

    # =========================================================================
    # SIGNAL NOTIFICATIONS (NEW: timeframe, strategy visible)
    # =========================================================================

    async def notify_signal(
        self, 
        ticker: str, 
        action: str, 
        price: float, 
        sl: float, 
        tp: float, 
        strategy: str = "default",
        timeframe: str = None,
        accounts_count: int = 0
    ):
        """Notify of incoming SIGNAL alert."""
        emoji = "🟢" if action.upper() == "BUY" else "🔴"
        strat_tag = f"[{strategy}]" if strategy != "default" else "[default]"
        tf_tag = f" {timeframe}" if timeframe else ""
        
        msg = (
            f"⚡ <b>SIGNAL Received</b>\n"
            f"{emoji} <b>{action.upper()} {ticker}</b>{tf_tag}\n"
            f"Strategy: {strat_tag}\n"
            f"Entry: {price} | SL: {sl} | TP: {tp}"
        )
        
        if accounts_count > 0:
            msg += f"\n<i>Processing on {accounts_count} account(s)...</i>"
        
        await self.send_message(msg)

    async def notify_partial_signal(
        self,
        ticker: str,
        timeframe: str,
        strategy: str,
        price: float = None,
        new_sl: float = None,
        new_tp: float = None,
        accounts: list = None
    ):
        """Notify of incoming PARTIAL signal."""
        msg = (
            f"📊 <b>PARTIAL Signal Received</b>\n"
            f"<b>{ticker}</b> ({timeframe})\n"
            f"Strategy: [{strategy}]"
        )
        
        if price:
            msg += f"\nTV Price: {price}"
        if new_sl:
            msg += f"\nNew SL: {new_sl}"
        if new_tp:
            msg += f"\nNew TP: {new_tp}"
        
        if accounts and len(accounts) > 0:
            msg += f"\n<i>Processing on {len(accounts)} account(s)...</i>"
        
        await self.send_message(msg)

    async def notify_close_signal(
        self,
        ticker: str,
        timeframe: str,
        strategy: str,
        price: float = None
    ):
        """Notify of incoming CLOSE signal."""
        msg = (
            f"🛑 <b>CLOSE Signal</b>\n"
            f"Ticker: {ticker} ({timeframe})\n"
            f"Strategy: [{strategy}]"
        )
        
        if price:
            msg += f"\nTV Price: {price}"
        
        msg += f"\n<i>Closing positions on matching accounts...</i>"
        await self.send_message(msg)

    # =========================================================================
    # TRADE EXECUTION NOTIFICATIONS (NEW: account name)
    # =========================================================================

    async def notify_order_submitted(
        self, 
        ticker: str, 
        action: str, 
        quantity: int, 
        price: float, 
        order_id: str,
        account_name: str = None
    ):
        """Notify that order was sent to broker."""
        account_tag = f" ({account_name})" if account_name else ""
        amount_str = f"{action} {quantity}x {ticker}"
        msg = f"🚀 <b>Order Submitted</b>{account_tag}\n{amount_str} @ {price}\nOrder ID: {order_id}"
        await self.send_message(msg)

    async def notify_position_opened(
        self, 
        symbol: str, 
        side: str, 
        quantity: int, 
        price: float, 
        order_id: str = None,
        account_name: str = None
    ):
        """Notify real fill."""
        side_upper = str(side).upper()
        emoji = "🔵" if "BUY" in side_upper or "LONG" in side_upper else "🟠"
        account_tag = f" ({account_name})" if account_name else ""
        
        msg = (
            f"{emoji} <b>Position Opened: {symbol}</b>{account_tag}\n"
            f"{side_upper} {quantity}x @ {price:.2f}\n" 
            f"<i>Filled</i>"
        )
        await self.send_message(msg)

    async def notify_position_closed(
        self, 
        symbol: str, 
        side: str, 
        entry_price: float, 
        exit_price: float, 
        pnl: float, 
        quantity: int, 
        fees: float = 0.0,
        account_name: str = None,
        daily_pnl: float = None
    ):
        """Notify position closed with optional daily PnL."""
        pnl_val = pnl if pnl is not None else 0.0
        pnl_emoji = "💰" if pnl_val >= 0 else "💸"
        side_str = str(side).upper()
        account_tag = f" ({account_name})" if account_name else ""
        
        if "BUY" in side_str or "LONG" in side_str:
            side_emoji = "🟢"
        elif "SELL" in side_str or "SHORT" in side_str:
            side_emoji = "🔴"
        else:
            side_emoji = "⚪"
        
        msg = (
            f"{pnl_emoji} <b>Position Closed: {symbol}</b>{account_tag}\n"
            f"{side_emoji} {side_str} x {quantity}\n"
        )
        
        if entry_price > 0:
            msg += f"Entry: {entry_price:.2f} -> Exit: {exit_price:.2f}\n"
        else:
            msg += f"Exit Price: {exit_price:.2f}\n"
            
        msg += f"<b>PnL: ${pnl_val:.2f}</b>\n"
        msg += f"<i>Fees: ${fees:.2f}</i>"
        
        # Add daily PnL if provided
        if daily_pnl is not None:
            daily_emoji = "📈" if daily_pnl >= 0 else "📉"
            msg += f"\n\n{daily_emoji} <b>Daily PnL: ${daily_pnl:.2f}</b>"
        
        await self.send_message(msg)

    async def notify_partial_executed(
        self,
        ticker: str,
        reduced_qty: int,
        remaining_qty: int,
        account_name: str = None,
        sl_moved_to_entry: bool = False,
        side: str = None,
        fill_price: float = None
    ):
        """Notify partial take-profit executed."""
        account_tag = f" ({account_name})" if account_name else ""
        
        # Add side emoji if available
        side_emoji = ""
        if side:
            side_upper = str(side).upper()
            if "BUY" in side_upper or "LONG" in side_upper:
                side_emoji = "🟢 "
            elif "SELL" in side_upper or "SHORT" in side_upper:
                side_emoji = "🔴 "
        
        msg = (
            f"✂️ <b>Partial TP Executed</b>{account_tag}\n"
            f"{side_emoji}<b>{ticker}</b>\n"
            f"Closed: {reduced_qty} contracts\n"
            f"Remaining: {remaining_qty} contracts"
        )
        
        if fill_price:
            msg += f"\nFill Price: {fill_price}"
        
        if sl_moved_to_entry:
            msg += "\n🎯 <i>SL moved to breakeven</i>"
        
        await self.send_message(msg)

    async def notify_close_executed(
        self,
        ticker: str,
        account_name: str = None,
        fill_price: float = None
    ):
        """Notify full position closed by CLOSE signal."""
        account_tag = f" ({account_name})" if account_name else ""
        
        msg = (
            f"🛑 <b>Position Closed (Signal)</b>{account_tag}\n"
            f"Ticker: {ticker}"
        )
        
        if fill_price:
            msg += f"\nFill Price: {fill_price}"
        
        msg += f"\n<i>Position fully closed</i>"
        await self.send_message(msg)

    # =========================================================================
    # REJECTION & WARNING NOTIFICATIONS
    # =========================================================================

    async def notify_trade_rejection(
        self, 
        ticker: str, 
        reason: str,
        account_name: str = None
    ):
        """Notify trade rejection."""
        account_tag = f" ({account_name})" if account_name else ""
        
        msg = (
            f"❌ <b>Trade Rejected</b>{account_tag}\n"
            f"Ticker: {ticker}\n"
            f"Reason: {reason}"
        )
        await self.send_message(msg)

    async def notify_orphaned_orders(self, orders: list):
        """Notifies about working orders without matching positions."""
        if not orders:
            return
            
        msg = "⚠️ <b>Orphaned Orders Detected</b>\nOrders active without open positions:\n\n"
        
        for o in orders:
            symbol = o.get('symbol') or o.get('contractId') or "Unknown"
            account = o.get('_account_name', '')
            side = o.get('action') or o.get('side') or "Limit"
            price = o.get('price') or o.get('stopPrice') or "Mkt"
            qty = o.get('qty') or o.get('quantity') or "?"
            
            account_tag = f" ({account})" if account else ""
            msg += f"• <b>{symbol}</b>{account_tag}: {side} {qty} @ {price}\n"
            
        msg += "\nCheck dashboard to cancel if not intended."
        await self.send_message(msg)

    async def notify_cross_account_block(
        self,
        ticker: str,
        conflicting_account: str,
        conflicting_side: str
    ):
        """Notify when trade is blocked due to opposing position on another account."""
        msg = (
            f"🚫 <b>Cross-Account Block</b>\n"
            f"Ticker: {ticker}\n"
            f"Conflict: {conflicting_side} position on {conflicting_account}\n"
            f"<i>Cannot open opposing position on same asset</i>"
        )
        await self.send_message(msg)

    async def notify_flatten_all(self, accounts_count: int):
        """Notify global flatten executed."""
        msg = (
            f"⏰ <b>Force Flatten Complete</b>\n"
            f"Flattened {accounts_count} account(s)\n"
            f"<i>All positions closed, orders cancelled</i>"
        )
        await self.send_message(msg)


telegram_service = TelegramService()
