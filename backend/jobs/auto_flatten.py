"""
Auto Flatten Job

Global force flatten at scheduled time.
Affects ALL accounts regardless of trading_enabled setting.
"""

import asyncio
from datetime import time
from typing import Any

import pytz

from backend.database import SessionLocal, Log
from backend.services.topstep_client import topstep_client
from backend.services.telegram_service import telegram_service
from backend.services.risk_engine import RiskEngine

BRUSSELS_TZ = pytz.timezone("Europe/Brussels")


async def auto_flatten_job() -> None:
    """
    Global force flatten at scheduled time.
    Affects ALL accounts regardless of trading_enabled setting.
    """
    from datetime import datetime
    
    db = SessionLocal()

    try:
        risk_engine = RiskEngine(db)
        settings = risk_engine.get_global_settings()

        if not settings.get("auto_flatten_enabled", False):
            return

        flatten_time = settings.get("auto_flatten_time", "21:55")
        now_bru = datetime.now(BRUSSELS_TZ)

        try:
            flatten_h, flatten_m = map(int, flatten_time.split(':'))
            target = time(flatten_h, flatten_m)

            # Check if within 1 minute window (since job runs every minute)
            current_time = now_bru.time()
            if current_time.hour == target.hour and current_time.minute == target.minute:
                print("⏰ Auto-Flatten Triggered!")

                # Get all accounts and flatten each
                all_accounts = await topstep_client.get_accounts()

                for account in all_accounts:
                    account_id = account.get('id')
                    account_name = account.get('name', str(account_id))

                    try:
                        # Cancel all orders
                        orders = await topstep_client.get_orders(account_id)
                        for order in orders:
                            if order.get('status') in [1, 6]:
                                await topstep_client.cancel_order(account_id, order.get('id'))

                        # Close all positions
                        positions = await topstep_client.get_open_positions(account_id)
                        for pos in positions:
                            await topstep_client.close_position(account_id, pos.get('contractId'))

                        db.add(Log(level="WARNING", message=f"Auto-Flatten: Account {account_name} flattened"))

                    except Exception as e:
                        db.add(Log(level="ERROR", message=f"Auto-Flatten failed for {account_name}: {e}"))

                db.commit()
                await telegram_service.send_message("⏰ <b>Auto-Flatten Complete</b> - All accounts flattened")

        except ValueError:
            print(f"Invalid auto_flatten_time format: {flatten_time}")

    except Exception as e:
        print(f"Auto-flatten job error: {e}")
    finally:
        db.close()


async def execute_flatten_all(db: Any, reason: str) -> None:
    """
    Close all positions and cancel all orders across all accounts.
    
    Args:
        db: Database session
        reason: Reason for flattening (for logging/notification)
    """
    try:
        all_accounts = await topstep_client.get_accounts()
        total_positions_closed = 0
        total_orders_cancelled = 0

        for account in all_accounts:
            account_id = account.get('id')
            account_name = account.get('name', str(account_id))

            try:
                # Cancel all working orders
                orders = await topstep_client.get_orders(account_id)
                for order in orders:
                    if order.get('status') in [1, 6]:
                        await topstep_client.cancel_order(account_id, order.get('id'))
                        total_orders_cancelled += 1
                        await asyncio.sleep(0.1)  # Rate limit

                # Close all positions
                positions = await topstep_client.get_open_positions(account_id)
                for pos in positions:
                    await topstep_client.close_position(account_id, pos.get('contractId'))
                    total_positions_closed += 1
                    await asyncio.sleep(0.1)  # Rate limit

                db.add(Log(level="WARNING", message=f"FLATTEN: Account {account_name} flattened"))

            except Exception as e:
                db.add(Log(level="ERROR", message=f"FLATTEN failed for {account_name}: {e}"))

        # Notification
        message = (
            f"💨 <b>FLATTEN Executed</b>\n\n"
            f"• Reason: {reason}\n"
            f"• Positions Closed: {total_positions_closed}\n"
            f"• Orders Cancelled: {total_orders_cancelled}"
        )
        await telegram_service.send_message(message)
        db.add(Log(level="INFO", message=f"FLATTEN Complete: {total_positions_closed} positions, {total_orders_cancelled} orders"))

    except Exception as e:
        db.add(Log(level="ERROR", message=f"FLATTEN failed: {e}"))
        await telegram_service.send_message(f"🚨 <b>FLATTEN Failed</b>\n\nError: {e}")
