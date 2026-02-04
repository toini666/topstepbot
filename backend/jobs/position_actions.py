"""
Position Actions Job

Checks for upcoming blocked periods and executes position actions.
Actions: NOTHING, BREAKEVEN, FLATTEN
"""

import asyncio
from datetime import datetime
from typing import Any, Set

import pytz

from backend.database import SessionLocal, Log
from backend.services.topstep_client import topstep_client
from backend.services.telegram_service import telegram_service
from backend.services.risk_engine import RiskEngine
from backend.jobs.state import (
    get_handled_position_action_blocks,
    add_handled_position_action_block
)
from backend.jobs.auto_flatten import execute_flatten_all

BRUSSELS_TZ = pytz.timezone("Europe/Brussels")


async def position_action_job() -> None:
    """
    Checks for upcoming blocked periods and executes position actions.
    Runs every 30 seconds.
    
    Actions:
    - NOTHING: No action taken
    - BREAKEVEN: Move SL to entry price for all positions
    - FLATTEN: Close all positions and cancel all orders
    """
    db = SessionLocal()

    try:
        risk_engine = RiskEngine(db)
        settings = risk_engine.get_global_settings()

        action = settings.get("blocked_hours_position_action", "NOTHING")
        if action == "NOTHING":
            return

        buffer_minutes = settings.get("position_action_buffer_minutes", 1)

        # Check if we're approaching a blocked period
        upcoming_block = risk_engine.get_upcoming_block(buffer_minutes)

        if not upcoming_block:
            return

        # Create unique block ID for deduplication
        block_id = f"{upcoming_block['start']}-{upcoming_block['end']}-{datetime.now(BRUSSELS_TZ).date()}"
        
        handled_blocks = get_handled_position_action_blocks()
        if block_id in handled_blocks:
            return  # Already handled this block today

        # Mark as handled BEFORE executing to prevent race conditions
        add_handled_position_action_block(block_id)

        block_type = upcoming_block.get("type", "manual")
        block_event = upcoming_block.get("event")
        reason = f"Entering {'news' if block_type == 'news' else 'manual'} block ({upcoming_block['start']}-{upcoming_block['end']})"
        if block_event:
            reason = f"News: {block_event} ({upcoming_block['start']}-{upcoming_block['end']})"

        print(f"🚨 Position Action Triggered: {action} - {reason}")
        db.add(Log(level="WARNING", message=f"Position Action Triggered: {action} - {reason}"))

        # Execute the action
        if action == "BREAKEVEN":
            await execute_breakeven_all(db, reason)
        elif action == "FLATTEN":
            await execute_flatten_all(db, reason)

        db.commit()

    except Exception as e:
        print(f"Position action job error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def execute_breakeven_all(db: Any, reason: str) -> None:
    """
    Move Stop Loss to entry price for all open positions across all accounts.
    If already in loss, SL moves to entry which may trigger auto-close.
    
    Args:
        db: Database session
        reason: Reason for breakeven (for logging/notification)
    """
    try:
        all_accounts = await topstep_client.get_accounts()
        total_modified = 0
        total_skipped = 0

        for account in all_accounts:
            account_id = account.get('id')
            account_name = account.get('name', str(account_id))

            try:
                positions = await topstep_client.get_open_positions(account_id)
                orders = await topstep_client.get_orders(account_id)

                for pos in positions:
                    contract_id = pos.get('contractId')
                    entry_price = pos.get('averagePrice') or pos.get('price')
                    pos_type = pos.get('type')  # 1=Long, 2=Short

                    if not entry_price:
                        total_skipped += 1
                        continue

                    # Find corresponding SL order
                    sl_order = None
                    for order in orders:
                        if str(order.get('contractId')) == str(contract_id):
                            order_type = order.get('type')
                            order_status = order.get('status')
                            if order_status not in ["Working", "Accepted", 1, 6]:
                                continue

                            if order_type in [4, "STOP", "SL"]:
                                sl_order = order
                                break

                    if sl_order:
                        # Modify SL to entry price
                        try:
                            success = await topstep_client.modify_order(
                                account_id=account_id,
                                order_id=sl_order.get('id'),
                                stopPrice=entry_price
                            )
                            if success:
                                total_modified += 1
                            else:
                                db.add(Log(level="DEBUG", message=f"BREAKEVEN: Failed to modify SL for {contract_id} (API rejected)"))
                                total_skipped += 1

                            await asyncio.sleep(0.1)  # Rate limit protection
                        except Exception as e:
                            db.add(Log(level="WARNING", message=f"BREAKEVEN: Failed to modify SL for {contract_id}: {e}"))
                            total_skipped += 1
                    else:
                        total_skipped += 1

            except Exception as e:
                db.add(Log(level="ERROR", message=f"BREAKEVEN: Error processing account {account_name}: {e}"))

        # Notification
        message = (
            f"🔒 <b>BREAKEVEN Executed</b>\n\n"
            f"• Reason: {reason}\n"
            f"• SL Orders Modified: {total_modified}\n"
            f"• Skipped: {total_skipped}"
        )
        await telegram_service.send_message(message)
        db.add(Log(level="INFO", message=f"BREAKEVEN Complete: {total_modified} modified, {total_skipped} skipped"))

    except Exception as e:
        db.add(Log(level="ERROR", message=f"BREAKEVEN failed: {e}"))
        await telegram_service.send_message(f"🚨 <b>BREAKEVEN Failed</b>\n\nError: {e}")
