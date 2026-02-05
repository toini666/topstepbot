"""
Position Monitor Job

Polls TopStep API for open positions on ALL accounts.
Detects if a previously open position is missing (closed) or changed size (partial).
Triggers Telegram Notification for valid closed trades.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Set

import pytz

from backend.database import SessionLocal, Log, Trade, TickerMap
from backend.services.topstep_client import topstep_client
from backend.services.telegram_service import telegram_service
from backend.services.discord_service import discord_service
from backend.services.logging_service import logger, log_trade_event, log_job_execution
from backend.jobs.state import (
    get_last_open_positions,
    set_last_orphans_ids,
    get_last_orphans_ids,
    update_account_positions
)


def parse_topstep_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse TopStep API date strings to datetime objects."""
    if not date_str:
        return None
    clean = str(date_str).replace('Z', '+00:00')
    try:
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        # Handle non-standard microseconds (e.g. 5 digits)
        if "." in clean:
            try:
                left, right = clean.split(".", 1)
                if "+" in right:
                    micro, tz = right.split("+", 1)
                    # Pad or truncate to 6 digits
                    micro = (micro + "000000")[:6]
                    clean = f"{left}.{micro}+{tz}"
                    dt = datetime.fromisoformat(clean)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
            except Exception:
                pass
        return None


def ensure_aware(d: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is timezone-aware (default to UTC if naive)."""
    if not d:
        return None
    if d.tzinfo is None:
        return d.replace(tzinfo=timezone.utc)
    return d


async def monitor_closed_positions_job() -> None:
    """
    Polls TopStep API for open positions on ALL accounts.
    Detects if a previously open position is missing (closed) or changed size (partial).
    Triggers Telegram Notification for valid closed trades.
    """
    db = SessionLocal()
    _last_open_positions = get_last_open_positions()
    _last_orphans_ids = get_last_orphans_ids()

    try:
        # Get all accounts from TopStep
        all_accounts = await topstep_client.get_accounts()

        if not all_accounts:
            return

        all_orphans: List[Dict[str, Any]] = []

        for account in all_accounts:
            account_id = account.get('id')
            account_name = account.get('name', str(account_id))

            try:
                # Fetch Current Positions for this account
                current_positions = await topstep_client.get_open_positions(account_id)

                # Convert to Dictionary: { 'contractId': position_data }
                current_map: Dict[str, Any] = {}
                for pos in current_positions:
                    cid = str(pos.get('contractId'))
                    current_map[cid] = pos

                # Get last known state for this account
                last_map = _last_open_positions.get(account_id, {})

                # Pre-fetch historical trades ONCE for this account (used multiple times below)
                recent_trades_cache: Optional[List[Dict[str, Any]]] = None
                recent_orders_cache: Optional[List[Dict[str, Any]]] = None

                # Detect Closures (Full or Partial)
                if last_map:
                    for prev_cid, prev_pos in last_map.items():
                        target_symbol = prev_pos.get('symbolId') or prev_cid

                        # Check State Change
                        is_full_close = prev_cid not in current_map
                        is_partial = False
                        current_size = 0

                        if not is_full_close:
                            current_pos = current_map[prev_cid]
                            prev_size = prev_pos.get('size', 0)
                            current_size = current_pos.get('size', 0)
                            if current_size < prev_size:
                                is_partial = True
                                log_trade_event("Partial close detected", prev_cid, account_name=account_name, extra={"from": prev_size, "to": current_size})

                        if is_full_close or is_partial:
                            if is_full_close:
                                log_trade_event("Position closed detected", prev_cid, account_name=account_name)

                            # 1. Find the Open Trade Record FIRST
                            ticker_variants = [prev_cid, target_symbol]

                            ticker_map_entry = db.query(TickerMap).filter(
                                TickerMap.ts_contract_id == prev_cid
                            ).first()
                            if ticker_map_entry:
                                ticker_variants.append(ticker_map_entry.tv_ticker)

                            open_trade = db.query(Trade).filter(
                                Trade.account_id == account_id,
                                Trade.ticker.in_(ticker_variants),
                                Trade.status == "OPEN"
                            ).order_by(Trade.timestamp.desc()).first()

                            # 2. Fetch History to calculate PnL (use cached if available)
                            if recent_trades_cache is None:
                                recent_trades_cache = await topstep_client.get_historical_trades(account_id, days=1)
                            recent_trades = recent_trades_cache

                            # 3. Filter Trades (Symbol match AND Time >= Entry Time)
                            relevant_trades: List[Dict[str, Any]] = []
                            matching_trade: Optional[Dict[str, Any]] = None

                            target_entry_time: Optional[datetime] = None
                            if open_trade and open_trade.timestamp:
                                target_entry_time = ensure_aware(open_trade.timestamp)

                            # Helper to safely get fallback ts
                            start_time_fallback: Optional[datetime] = None
                            if target_entry_time:
                                start_time_fallback = target_entry_time - timedelta(seconds=5)

                            for t in recent_trades:
                                t_sym = str(t.get('symbol') or '')
                                t_cid = str(t.get('contractId') or '')

                                # Check Symbol Match
                                if t_sym == str(target_symbol) or t_cid == str(prev_cid):

                                    # Try to extract Entry Time from API Trade
                                    t_entry_ts = parse_topstep_date(t.get('entryTime') or t.get('entryTimestamp'))

                                    # If no explicit entry time in API, fallback to filtering by > open_trade time
                                    if not t_entry_ts and start_time_fallback:
                                        # Fallback to Time-based logic
                                        t_created = parse_topstep_date(t.get('creationTimestamp') or t.get('timestamp') or t.get('time'))
                                        if t_created and t_created >= start_time_fallback:
                                            relevant_trades.append(t)
                                            if is_full_close and not matching_trade:
                                                matching_trade = t
                                        continue

                                    # Primary Logic: Match Entry Timestamp
                                    if t_entry_ts and target_entry_time:
                                        # Allow 2s tolerance for micro-variations
                                        diff = abs((t_entry_ts - target_entry_time).total_seconds())
                                        if diff < 2.0:
                                            relevant_trades.append(t)
                                            if is_full_close and not matching_trade:
                                                matching_trade = t

                            # Calculate Stats
                            pnl_val = sum((t.get('pnl') or t.get('profitAndLoss') or 0) for t in relevant_trades)
                            total_fees = sum((t.get('fees') or 0) for t in relevant_trades)

                            # Update DB
                            if open_trade:
                                if is_full_close:
                                    # Full Close Update
                                    exit_px = 0
                                    if relevant_trades:
                                        sorted_rel = sorted(relevant_trades, key=lambda x: x.get('creationTimestamp', ''), reverse=True)
                                        last_fill = sorted_rel[0]
                                        exit_px = last_fill.get('price') or last_fill.get('fillPrice') or 0

                                    open_trade.status = "CLOSED"
                                    open_trade.exit_price = exit_px
                                    open_trade.pnl = pnl_val
                                    open_trade.fees = total_fees
                                    open_trade.exit_time = datetime.now(pytz.UTC)
                                    db.commit()

                                    side_str = "FLAT"
                                    if matching_trade:
                                        raw_side = matching_trade.get('side')
                                        raw_side_upper = str(raw_side).upper().strip()
                                        if raw_side_upper in ["0", "BUY", "LONG"]:
                                            side_str = "SHORT"
                                        elif raw_side_upper in ["1", "2", "SELL", "SHORT"]:
                                            side_str = "LONG"

                                    # Calculate Real Daily PnL
                                    today_utc = datetime.now(timezone.utc).date()
                                    real_daily_pnl = 0.0
                                    real_daily_fees = 0.0

                                    for t in recent_trades:
                                        pnl = t.get('profitAndLoss') or t.get('pnl')
                                        fees = t.get('fees')
                                        if pnl is not None:
                                            real_daily_pnl += float(pnl)
                                        if fees is not None:
                                            real_daily_fees += float(fees)

                                    final_daily_pnl = real_daily_pnl - real_daily_fees

                                    await telegram_service.notify_position_closed(
                                        symbol=f"{target_symbol} ({account_name})",
                                        side=side_str,
                                        entry_price=open_trade.entry_price or 0,
                                        exit_price=exit_px,
                                        pnl=pnl_val,
                                        fees=total_fees,
                                        quantity=open_trade.quantity,
                                        daily_pnl=final_daily_pnl
                                    )

                                    # Discord notification
                                    await discord_service.notify_position_closed(
                                        account_id=account_id,
                                        symbol=open_trade.ticker or target_symbol,
                                        side=side_str,
                                        entry_price=open_trade.entry_price or 0,
                                        exit_price=exit_px,
                                        pnl=pnl_val,
                                        quantity=open_trade.quantity,
                                        fees=total_fees,
                                        strategy=open_trade.strategy or "-",
                                        timeframe=open_trade.timeframe or "-",
                                        account_name=account_name,
                                        daily_pnl=final_daily_pnl
                                    )
                                    log_trade_event("Trade marked CLOSED", open_trade.ticker, account_name=account_name, extra={"trade_id": open_trade.id, "pnl": f"${pnl_val:.2f}"})

                                elif is_partial:
                                    # Partial Update
                                    open_trade.pnl = pnl_val
                                    open_trade.fees = total_fees
                                    db.commit()
                                    log_trade_event("Trade updated PARTIAL", open_trade.ticker, account_name=account_name, extra={"trade_id": open_trade.id, "pnl": f"${pnl_val:.2f}"})

                            elif is_full_close:
                                # Fallback if no trade found
                                matching_closed_trade = db.query(Trade).filter(
                                    Trade.account_id == account_id,
                                    Trade.ticker.in_(ticker_variants),
                                    Trade.status == "CLOSED"
                                ).order_by(Trade.exit_time.desc()).first()

                                is_recently_closed = False
                                if matching_closed_trade and matching_closed_trade.exit_time:
                                    time_since_close = (datetime.now(timezone.utc) - ensure_aware(matching_closed_trade.exit_time)).total_seconds()
                                    if time_since_close < 120:
                                        is_recently_closed = True

                                if is_recently_closed:
                                    logger.debug(f"Full close for {prev_cid} already handled by webhook")
                                else:
                                    logger.warning(f"Full close but no OPEN trade record found for {prev_cid}")
                                    await telegram_service.send_message(
                                        f"💰 <b>Position Closed: {target_symbol}</b> ({account_name})"
                                    )

                # Detect New Positions (Opens)
                if last_map is not None:
                    for curr_cid, curr_pos in current_map.items():
                        if curr_cid not in last_map:
                            log_trade_event("New position detected", curr_cid, account_name=account_name)

                            # Use cached trades
                            if recent_trades_cache is None:
                                recent_trades_cache = await topstep_client.get_historical_trades(account_id, days=1)
                            recent_trades = recent_trades_cache
                            matching_fill: Optional[Dict[str, Any]] = None

                            if recent_trades:
                                for t in recent_trades:
                                    if str(t.get('contractId')) == str(curr_cid):
                                        matching_fill = t
                                        break

                            if matching_fill:
                                fill_price = matching_fill.get('price') or 0
                                fill_side = str(matching_fill.get('side')).upper().strip()
                                entry_ts = parse_topstep_date(matching_fill.get('entryTime') or matching_fill.get('entryTimestamp'))
                                if not entry_ts:
                                    entry_ts = parse_topstep_date(matching_fill.get('creationTimestamp') or matching_fill.get('timestamp') or matching_fill.get('time'))

                                if fill_side in ["0", "BUY", "LONG"]:
                                    side_str = "BUY"
                                elif fill_side in ["1", "2", "SELL", "SHORT"]:
                                    side_str = "SELL"
                                else:
                                    side_str = "UNK"

                                # Check if trade record exists or create one for manual trades
                                ticker_variants = [curr_cid]
                                ticker_map_entry = db.query(TickerMap).filter(
                                    TickerMap.ts_contract_id == curr_cid
                                ).first()
                                tv_ticker = ticker_map_entry.tv_ticker if ticker_map_entry else curr_cid
                                if ticker_map_entry:
                                    ticker_variants.append(tv_ticker)

                                open_trade = db.query(Trade).filter(
                                    Trade.account_id == account_id,
                                    Trade.ticker.in_(ticker_variants),
                                    Trade.status.in_(["OPEN", "PENDING"])
                                ).order_by(Trade.timestamp.desc()).first()

                                if open_trade and fill_price:
                                    open_trade.entry_price = fill_price
                                    if entry_ts:
                                        open_trade.timestamp = entry_ts
                                    db.commit()
                                    log_trade_event("Trade fill updated", open_trade.ticker, account_name=account_name, extra={"trade_id": open_trade.id, "price": fill_price})
                                elif not open_trade:
                                    # MANUAL TRADE - Create a Trade record
                                    fill_qty = matching_fill.get('size', 1)
                                    manual_trade = Trade(
                                        account_id=account_id,
                                        ticker=tv_ticker,
                                        action=side_str,
                                        entry_price=fill_price,
                                        quantity=fill_qty,
                                        status="OPEN",
                                        strategy="MANUAL",
                                        timeframe="-",
                                        timestamp=entry_ts or datetime.now(pytz.UTC)
                                    )
                                    db.add(manual_trade)
                                    db.commit()
                                    log_trade_event("Manual trade created", tv_ticker, account_name=account_name, extra={"trade_id": manual_trade.id, "qty": fill_qty, "price": fill_price})
                                    open_trade = manual_trade

                                # Prepare notification data
                                strat = open_trade.strategy if open_trade else "MANUAL"
                                tf = open_trade.timeframe if open_trade else "-"
                                
                                # Get signal entry price and tick size for slippage calculation
                                signal_entry = open_trade.signal_entry_price if open_trade else None
                                tick_size = ticker_map_entry.tick_size if ticker_map_entry else None

                                await telegram_service.notify_position_opened(
                                    symbol=f"{matching_fill.get('symbol', curr_cid)} ({account_name})",
                                    side=side_str,
                                    quantity=matching_fill.get('size', 1),
                                    price=fill_price,
                                    order_id=str(matching_fill.get('orderId', '')),
                                    signal_entry_price=signal_entry,
                                    tick_size=tick_size
                                )

                                # Discord notification
                                await discord_service.notify_position_opened(
                                    account_id=account_id,
                                    symbol=matching_fill.get('symbol', curr_cid),
                                    side=side_str,
                                    quantity=matching_fill.get('size', 1),
                                    price=fill_price,
                                    strategy=strat,
                                    timeframe=tf,
                                    account_name=account_name
                                )

                # Update state for this account
                update_account_positions(account_id, current_map)

                # =================================================================
                # DB RECONCILIATION (Detect Closures missed during downtime)
                # =================================================================

                # Get ALL OPEN trades for this account from DB
                db_open_trades = db.query(Trade).filter(
                    Trade.account_id == account_id,
                    Trade.status == "OPEN"
                ).all()

                for trade in db_open_trades:
                    # Resolve expected contract ID for this trade
                    expected_cid: Optional[str] = None
                    ticker_map_entry = db.query(TickerMap).filter(TickerMap.tv_ticker == trade.ticker).first()

                    if ticker_map_entry:
                        expected_cid = ticker_map_entry.ts_contract_id

                    # Fallback: try to match by partial string in current map
                    if not expected_cid:
                        clean_ticker = trade.ticker.replace("1!", "").replace("2!", "").upper()
                        for cid, pos in current_map.items():
                            if clean_ticker in str(pos.get('symbolId') or cid).upper():
                                expected_cid = cid
                                break

                    if not expected_cid:
                        continue

                    # CHECK: Is this trade physically present in TopStep?
                    if expected_cid not in current_map:
                        logger.info(f"[RECONCILE] Trade #{trade.id} ({trade.ticker}) OPEN in DB but missing in API, verifying...")

                        # Verify against history
                        if recent_trades_cache is None:
                            recent_trades_cache = await topstep_client.get_historical_trades(account_id, days=1)
                        recent_trades = recent_trades_cache
                        trade_entry_time = trade.timestamp

                        # Find matching exit execution
                        confirm_close = False
                        exit_fill: Optional[Dict[str, Any]] = None

                        for t in recent_trades:
                            t_cid = str(t.get('contractId') or '')
                            if t_cid == expected_cid:
                                t_time = parse_topstep_date(t.get('creationTimestamp') or t.get('timestamp') or t.get('time'))
                                t_time = ensure_aware(t_time)

                                if trade_entry_time:
                                    trade_entry_time = ensure_aware(trade_entry_time)

                                    try:
                                        if t_time and t_time > trade_entry_time:
                                            confirm_close = True
                                            exit_fill = t
                                            break
                                    except TypeError as e:
                                        logger.warning(f"[RECONCILE] Date comparison error: {e}")
                                        continue

                                if not trade_entry_time:
                                    confirm_close = True
                                    exit_fill = t
                                    break

                        if confirm_close and exit_fill:
                            exit_px = exit_fill.get('price') or exit_fill.get('fillPrice') or 0
                            pnl_val = exit_fill.get('pnl') or exit_fill.get('profitAndLoss') or 0
                            fees_val = exit_fill.get('fees') or 0

                            trade.status = "CLOSED"
                            trade.exit_price = exit_px
                            trade.exit_time = datetime.now(pytz.UTC)
                            trade.pnl = pnl_val
                            trade.fees = fees_val
                            db.commit()

                            log_trade_event("Reconciled trade CLOSED", trade.ticker, extra={"trade_id": trade.id, "pnl": f"${pnl_val:.2f}"})
                            db.add(Log(level="INFO", message=f"RECONCILIATION: Trade #{trade.id} marked as CLOSED (PnL: ${pnl_val:.2f})"))
                            db.commit()

                            await telegram_service.notify_position_closed(
                                symbol=f"{trade.ticker} ({account_name})",
                                side="LONG" if trade.action == "BUY" else "SHORT",
                                entry_price=trade.entry_price,
                                exit_price=exit_px,
                                pnl=pnl_val,
                                fees=fees_val,
                                quantity=trade.quantity
                            )
                        else:
                            logger.warning(f"[RECONCILE] Could not confirm closure for #{trade.id}, keeping OPEN")
                            db.add(Log(level="DEBUG", message=f"RECONCILIATION: Could not confirm closure in history for #{trade.id}"))
                            db.commit()

                # Check for orphaned orders on this account
                if recent_orders_cache is None:
                    recent_orders_cache = await topstep_client.get_orders(account_id, days=1)
                for o in recent_orders_cache:
                    st = o.get('status')
                    if str(st).upper() in ["WORKING", "ACCEPTED", "1", "6"]:
                        cid = str(o.get('contractId'))
                        if cid not in current_map:
                            o['_account_name'] = account_name
                            all_orphans.append(o)

            except Exception as e:
                logger.error(f"Monitor error for account {account_id}: {e}", exc_info=True)
                # Notify user of monitoring error (fire-and-forget)
                asyncio.create_task(
                    telegram_service.notify_position_monitor_error(
                        account_name=account_name,
                        error_message=str(e)
                    )
                )
                continue

        # Notify orphans (globally)
        current_orphan_ids = set(str(o.get('orderId') or o.get('id')) for o in all_orphans)

        if all_orphans and current_orphan_ids != _last_orphans_ids:
            logger.warning(f"Orphaned orders detected: {current_orphan_ids}")
            await telegram_service.notify_orphaned_orders(all_orphans)

        set_last_orphans_ids(current_orphan_ids)

    except Exception as e:
        logger.error(f"Monitor Job Failed: {e}", exc_info=True)
        # Notify user of critical monitoring failure
        try:
            await telegram_service.notify_critical_error(
                component="Position Monitor",
                error_message=str(e),
                context={"status": "Job failed completely"}
            )
        except Exception:
            pass  # Don't fail if notification fails
    finally:
        db.close()
