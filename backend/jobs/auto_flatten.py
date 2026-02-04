"""
Auto Flatten Job

Global force flatten at scheduled time.
Affects ALL accounts regardless of trading_enabled setting.
"""

import asyncio
import logging
from datetime import time
from typing import Any, List, Dict

import pytz

from backend.database import SessionLocal, Log
from backend.services.topstep_client import topstep_client
from backend.services.telegram_service import telegram_service
from backend.services.risk_engine import RiskEngine
from backend.constants import (
    RATE_LIMIT_DELAY_BETWEEN_CALLS,
    BATCH_SIZE_CANCEL_ORDERS,
    BATCH_SIZE_CLOSE_POSITIONS,
    ORDER_STATUS_WORKING_LIST
)

logger = logging.getLogger("topstepbot")
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
                        # Cancel all orders (batched parallel with rate limiting)
                        orders = await topstep_client.get_orders(account_id)
                        working_orders = [o for o in orders if o.get('status') in ORDER_STATUS_WORKING_LIST]

                        if working_orders:
                            await _cancel_orders_batched(account_id, working_orders)

                        # Close all positions (batched parallel with rate limiting)
                        positions = await topstep_client.get_open_positions(account_id)
                        if positions:
                            await _close_positions_batched(account_id, positions)

                        db.add(Log(level="WARNING", message=f"Auto-Flatten: Account {account_name} flattened"))

                    except Exception as e:
                        logger.error(f"Auto-Flatten failed for {account_name}: {e}")
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
                # Cancel all working orders (batched parallel with rate limiting)
                orders = await topstep_client.get_orders(account_id)
                working_orders = [o for o in orders if o.get('status') in ORDER_STATUS_WORKING_LIST]

                if working_orders:
                    cancelled = await _cancel_orders_batched(account_id, working_orders)
                    total_orders_cancelled += cancelled

                # Close all positions (batched parallel with rate limiting)
                positions = await topstep_client.get_open_positions(account_id)
                if positions:
                    closed = await _close_positions_batched(account_id, positions)
                    total_positions_closed += closed

                db.add(Log(level="WARNING", message=f"FLATTEN: Account {account_name} flattened"))

            except Exception as e:
                logger.error(f"FLATTEN failed for {account_name}: {e}")
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


# =============================================================================
# HELPER FUNCTIONS FOR BATCHED PARALLEL OPERATIONS
# =============================================================================

async def _cancel_orders_batched(account_id: int, orders: List[Dict]) -> int:
    """
    Cancel orders in batches with rate limiting.
    Respects TopStep API rate limit: 200 requests / 60 seconds.

    Args:
        account_id: The account to cancel orders for
        orders: List of order dicts to cancel

    Returns:
        Number of successfully cancelled orders
    """
    total_cancelled = 0

    # Process in batches to avoid rate limiting
    for i in range(0, len(orders), BATCH_SIZE_CANCEL_ORDERS):
        batch = orders[i:i + BATCH_SIZE_CANCEL_ORDERS]

        # Execute batch in parallel
        async def cancel_single(order):
            order_id = order.get('id') or order.get('orderId')
            if order_id:
                try:
                    success = await topstep_client.cancel_order(account_id, order_id)
                    return 1 if success else 0
                except Exception as e:
                    logger.warning(f"Failed to cancel order {order_id}: {e}")
                    return 0
            return 0

        results = await asyncio.gather(*[cancel_single(o) for o in batch], return_exceptions=True)

        # Count successes (ignore exceptions)
        total_cancelled += sum(r for r in results if isinstance(r, int))

        # Add delay between batches to respect rate limits
        if i + BATCH_SIZE_CANCEL_ORDERS < len(orders):
            await asyncio.sleep(RATE_LIMIT_DELAY_BETWEEN_CALLS * BATCH_SIZE_CANCEL_ORDERS)

    return total_cancelled


async def _close_positions_batched(account_id: int, positions: List[Dict]) -> int:
    """
    Close positions in batches with rate limiting.
    Respects TopStep API rate limit: 200 requests / 60 seconds.

    Args:
        account_id: The account to close positions for
        positions: List of position dicts to close

    Returns:
        Number of successfully closed positions
    """
    total_closed = 0

    # Process in batches to avoid rate limiting
    for i in range(0, len(positions), BATCH_SIZE_CLOSE_POSITIONS):
        batch = positions[i:i + BATCH_SIZE_CLOSE_POSITIONS]

        # Execute batch in parallel
        async def close_single(pos):
            contract_id = pos.get('contractId')
            if contract_id:
                try:
                    success = await topstep_client.close_position(account_id, contract_id)
                    return 1 if success else 0
                except Exception as e:
                    logger.warning(f"Failed to close position {contract_id}: {e}")
                    return 0
            return 0

        results = await asyncio.gather(*[close_single(p) for p in batch], return_exceptions=True)

        # Count successes (ignore exceptions)
        total_closed += sum(r for r in results if isinstance(r, int))

        # Add delay between batches to respect rate limits
        if i + BATCH_SIZE_CLOSE_POSITIONS < len(positions):
            await asyncio.sleep(RATE_LIMIT_DELAY_BETWEEN_CALLS * BATCH_SIZE_CLOSE_POSITIONS)

    return total_closed
