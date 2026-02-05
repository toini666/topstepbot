"""
Discord Service - Trading Bot Notifications via Webhook

Sends notifications to Discord channels using webhooks:
- Position opened notifications
- Position closed notifications with P&L
- Daily summary with account statistics
"""

import httpx
import asyncio
from typing import Optional
from datetime import datetime
from backend.database import SessionLocal, Log, DiscordNotificationSettings


class DiscordService:
    """Discord notification service using webhooks."""
    
    def __init__(self):
        self.enabled = True
    
    def _log_error(self, message: str):
        """Log error to database."""
        try:
            db = SessionLocal()
            log = Log(level="ERROR", message=message)
            db.add(log)
            db.commit()
            db.close()
        except Exception as e:
            print(f"FAILED TO LOG ERROR TO DB: {message} | Error: {e}")
    
    def _log_info(self, message: str):
        """Log info to database."""
        try:
            db = SessionLocal()
            log = Log(level="INFO", message=message)
            db.add(log)
            db.commit()
            db.close()
        except Exception as e:
            print(f"FAILED TO LOG INFO TO DB: {message} | Error: {e}")
    
    def get_settings(self, account_id: int) -> Optional[DiscordNotificationSettings]:
        """Get Discord notification settings for an account."""
        try:
            db = SessionLocal()
            settings = db.query(DiscordNotificationSettings).filter(
                DiscordNotificationSettings.account_id == account_id
            ).first()
            db.close()
            return settings
        except Exception as e:
            self._log_error(f"Failed to get Discord settings for account {account_id}: {e}")
            return None
    
    async def send_message(
        self, 
        webhook_url: str, 
        content: str = None, 
        embeds: list = None,
        username: str = "TopStep Bot"
    ) -> bool:
        """
        Send a message to Discord via webhook with robust retry logic.
        Handles rate limits (429) and network transients automatically.
        """
        if not webhook_url:
            return False
        
        payload = {"username": username}
        if content: payload["content"] = content
        if embeds: payload["embeds"] = embeds
        
        # Retry configuration
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries + 1):
            try:
                # Use a fresh client for now to avoid complexity with event loops
                # In a full valid implementation we would use a shared client on the app state
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(webhook_url, json=payload)
                    
                    # Success
                    if response.status_code in [200, 204]:
                        return True
                    
                    # Rate Limit
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", base_delay))
                        # Cap retry wait to avoid hanging too long
                        wait_time = min(retry_after, 5.0)
                        
                        warning_msg = f"Discord Rate Limit (429). Waiting {wait_time}s..."
                        # Only log on first retry to avoid spam
                        if attempt == 0:
                            self._log_info(warning_msg)
                        
                        await asyncio.sleep(wait_time)
                        continue
                    
                    # Other Server Errors (5xx) -> Retry
                    if 500 <= response.status_code < 600:
                        wait_time = base_delay * (2 ** attempt) # Exponential backoff
                        await asyncio.sleep(wait_time)
                        continue
                        
                    # Client Errors (4xx) -> Fail immediately (except 429)
                    self._log_error(f"Discord Webhook Rejected ({response.status_code}): {response.text}")
                    return False
                    
            except httpx.TimeoutException:
                if attempt < max_retries:
                    await asyncio.sleep(base_delay)
                    continue
                self._log_error("Discord Webhook Timeout")
                
            except Exception as e:
                self._log_error(f"Discord Send Fail: {e}")
                return False
        
        self._log_error(f"Discord Webhook failed after {max_retries} retries")
        return False
    
    async def notify_position_opened(
        self,
        account_id: int,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        strategy: str = "-",
        timeframe: str = "-",
        account_name: str = None
    ):
        """Notify that a position was opened."""
        settings = self.get_settings(account_id)
        
        if not settings or not settings.enabled or not settings.notify_position_open:
            return
        
        if not settings.webhook_url:
            return
        
        # Format side and color
        is_long = side.upper() in ["BUY", "LONG"]
        side_title = "Ouverture Long" if is_long else "Ouverture Short"
        emoji = "🟢" if is_long else "🔴"
        color = 0x22C55E if is_long else 0xEF4444  # Green or Red
        
        description = (
            f"**{symbol}**\n"
            f"Quantité: {quantity}\n"
            f"Prix: ${price:,.2f}\n"
            f"Stratégie: {strategy}"
        )
        
        embed = {
            "title": f"{emoji} {side_title}",
            "description": description,
            "color": color,
            "footer": {"text": f"Timeframe: {timeframe}"},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        await self.send_message(settings.webhook_url, embeds=[embed])
        self._log_info(f"Discord: Position opened notification sent for {symbol} on account {account_id}")
    
    async def notify_position_closed(
        self,
        account_id: int,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        quantity: int,
        fees: float = 0.0,
        strategy: str = "-",
        timeframe: str = "-",
        account_name: str = None,
        daily_pnl: float = None
    ):
        """Notify that a position was closed with P&L details."""
        settings = self.get_settings(account_id)
        
        if not settings or not settings.enabled or not settings.notify_position_close:
            return
        
        if not settings.webhook_url:
            return
        
        # Determine color based on P&L (Vertical Bar)
        net_pnl = pnl - fees
        color = 0x22C55E if net_pnl >= 0 else 0xEF4444  # Green or Red
        
        # Title Emoji based on Side
        is_long = side.upper() in ["BUY", "LONG"]
        side_title = "Fermeture Long" if is_long else "Fermeture Short"
        title_emoji = "🟢" if is_long else "🔴"
        
        pnl_emoji = "💰" if net_pnl >= 0 else "💸"
        
        description = (
            f"**{symbol}**\n"
            f"Quantité: {quantity}\n"
            f"Stratégie: {strategy}\n\n"
            f"📥 Entrée: ${entry_price:,.2f}\n"
            f"📤 Sortie: ${exit_price:,.2f}\n"
            f"{pnl_emoji} **Net P&L: ${net_pnl:+,.2f}**\n"
        )
        
        if daily_pnl is not None:
            daily_emoji = "📈" if daily_pnl >= 0 else "📉"
            description += f"{daily_emoji} Daily P&L: ${daily_pnl:+,.2f}"
            
        embed = {
            "title": f"{title_emoji} {side_title}",
            "description": description,
            "color": color,
            "footer": {"text": f"Timeframe: {timeframe}"},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        await self.send_message(settings.webhook_url, embeds=[embed])
        self._log_info(f"Discord: Position closed notification sent for {symbol} on account {account_id}")
    
    async def send_daily_summary(
        self,
        account_id: int,
        account_name: str,
        pnl: float,
        trade_count: int,
        balance: float
    ):
        """Send daily summary message."""
        settings = self.get_settings(account_id)
        
        if not settings or not settings.enabled or not settings.notify_daily_summary:
            return
        
        if not settings.webhook_url:
            return
        
        # Determine color based on P&L
        color = 0x22C55E if pnl >= 0 else 0xEF4444  # Green or Red
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        
        description = (
            f"{pnl_emoji} **Daily P&L:** ${pnl:+,.2f}\n"
            f"🔢 **Trades:** {trade_count}\n"
            f"💰 **Balance:** ${balance:,.2f}"
        )
        
        embed = {
            "title": "📊 Daily Trading Summary",
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": f"{account_name} • End of day"}
        }
        
        await self.send_message(settings.webhook_url, embeds=[embed])
        self._log_info(f"Discord: Daily summary sent for account {account_id}")

    async def notify_partial_executed(
        self,
        account_id: int,
        ticker: str,
        reduced_qty: int,
        remaining_qty: int,
        fill_price: float = None,
        realized_pnl: float = None,
        unrealized_pnl: float = None,
        fees: float = 0.0,
        account_name: str = None,
        strategy: str = "-",
        timeframe: str = "-"
    ):
        """Notify partial take-profit executed."""
        settings = self.get_settings(account_id)
        
        if not settings or not settings.enabled:
            return
            
        # Check newly added setting (handle case where DB might calculate defaults differently if missing)
        if not getattr(settings, 'notify_partial_close', True):
            return
        
        if not settings.webhook_url:
            return
            
        # Determine color based on Realized P&L
        net_pnl = (realized_pnl or 0) - fees
        color = 0x22C55E if net_pnl >= 0 else 0xEF4444  # Green or Red
        
        pnl_emoji = "💰" if net_pnl >= 0 else "💸"
        
        description = (
            f"**{ticker}**\n"
            f"Clôture Partielle: {reduced_qty}\n"
            f"Restant: {remaining_qty}\n"
            f"Stratégie: {strategy}\n\n"
        )
        
        if fill_price:
            description += f"Prix: ${fill_price:,.2f}\n"
            
        if realized_pnl is not None:
            description += f"{pnl_emoji} **Realized P&L: ${net_pnl:+,.2f}**\n"
            
        if unrealized_pnl is not None:
            latent_emoji = "📈" if unrealized_pnl >= 0 else "📉"
            description += f"{latent_emoji} Latent (Rem): ${unrealized_pnl:+,.2f}"
            
        embed = {
            "title": "✂️ Fermeture Partielle",
            "description": description,
            "color": color,
            "footer": {"text": f"Timeframe: {timeframe} • {account_name}"},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        await self.send_message(settings.webhook_url, embeds=[embed])
        self._log_info(f"Discord: Partial close notification sent for {ticker} on account {account_id}")


# Singleton instance
discord_service = DiscordService()
