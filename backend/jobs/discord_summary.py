"""
Discord Daily Summary Job

Checks if any account has reached its configured Discord daily summary time.
Sends daily summary with P&L, trade count, and balance.
"""

from datetime import datetime
from typing import List, Dict, Any

from backend.database import SessionLocal, Log, DiscordNotificationSettings, Trade
from backend.services.topstep_client import topstep_client
from backend.services.discord_service import discord_service
from backend.services.risk_engine import RiskEngine
from backend.services.timezone_service import now_user_tz


async def discord_daily_summary_job() -> None:
    """
    Checks if any account has reached its configured Discord daily summary time.
    Sends daily summary with P&L, trade count, and balance.
    Only sends if trading day is enabled in global settings.
    """
    db = SessionLocal()
    
    try:
        # Check if today is a trading day
        risk_engine = RiskEngine(db)
        settings = risk_engine.get_global_settings()
        trading_days = settings.get("trading_days", ["MON", "TUE", "WED", "THU", "FRI"])
        
        now_local = now_user_tz()
        day_abbr = now_local.strftime("%a").upper()[:3]  # MON, TUE, etc.
        
        if day_abbr not in trading_days:
            # Not a trading day, skip
            return
        
        current_time = now_local.strftime("%H:%M")
        
        # Get all Discord settings with daily summary enabled
        all_discord_settings = db.query(DiscordNotificationSettings).filter(
            DiscordNotificationSettings.enabled == True,
            DiscordNotificationSettings.notify_daily_summary == True
        ).all()
        
        if not all_discord_settings:
            return
        
        for discord_settings in all_discord_settings:
            # Check if current time matches the configured summary time
            if discord_settings.daily_summary_time != current_time:
                continue
            
            account_id = discord_settings.account_id
            
            try:
                # Get account info
                all_accounts = await topstep_client.get_accounts()
                account_info = next((a for a in all_accounts if a.get('id') == account_id), None)
                
                if not account_info:
                    continue
                
                account_name = account_info.get('name', str(account_id))
                balance = account_info.get('balance', 0)
                
                # Calculate today's P&L from API
                recent_trades = await topstep_client.get_historical_trades(account_id, days=1)
                
                today_pnl = 0.0
                today_fees = 0.0
                trade_count = 0
                
                for t in recent_trades:
                    pnl = t.get('profitAndLoss') or t.get('pnl')
                    fees = t.get('fees')
                    if pnl is not None:
                        today_pnl += float(pnl)
                        trade_count += 1
                    if fees is not None:
                        today_fees += float(fees)
                
                net_pnl = today_pnl - today_fees
                
                # Send the summary
                await discord_service.send_daily_summary(
                    account_id=account_id,
                    account_name=account_name,
                    pnl=net_pnl,
                    trade_count=trade_count,
                    balance=balance
                )
                
                print(f"📊 Discord daily summary sent for account {account_name}")
                
            except Exception as e:
                print(f"Error sending Discord daily summary for account {account_id}: {e}")
                continue
    
    except Exception as e:
        print(f"Discord daily summary job error: {e}")
    finally:
        db.close()
