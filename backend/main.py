"""
TopStepBot Main Application - Multi-Account Trading Bot

Key Features:
- Multi-account position monitoring
- Global force flatten (all accounts)
- Trading session awareness
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db, get_db, Setting, AccountSettings, seed_default_sessions, TickerMap
from backend.routers import webhook, dashboard, strategies, export, calendar
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.services.risk_engine import RiskEngine
from backend.services.topstep_client import topstep_client
from backend.services.telegram_service import telegram_service
from backend.services.discord_service import discord_service
from backend.services.telegram_bot import telegram_bot
from backend.services.maintenance_service import backup_database, clean_logs, check_and_run_startup_backup
from backend.services.persistence_service import save_state, load_state, save_ngrok_url, get_last_ngrok_url
import asyncio
import aiohttp
import json
import os
from datetime import datetime, time, timedelta, timezone
import pytz

from datetime import datetime, time, timedelta, timezone
import pytz
from backend.services.calendar_service import calendar_service
from backend.services.price_cache import price_cache
from backend.services.contract_validator import contract_validator

# Scheduler Setup
scheduler = AsyncIOScheduler()

# Brussels Timezone
BRUSSELS_TZ = pytz.timezone("Europe/Brussels")

# Global State for Position Monitoring (per-account)
# Key: account_id, Value: { contractId: position_data }
_last_open_positions = {}
_last_orphans_ids = set()

# Health Check State
_api_health = {
    "consecutive_failures": 0,
    "last_check_time": None,
    "last_response_time": None,
    "is_healthy": True,
    "notified_down": False
}

# Heartbeat State
_heartbeat_state = {
    "start_time": None,
    "last_sent": None,
    "consecutive_failures": 0
}


async def monitor_closed_positions_job():
    """
    Polls TopStep API for open positions on ALL accounts.
    Detects if a previously open position is missing (closed) or changed size (partial).
    Triggers Telegram Notification for valid closed trades.
    """
    global _last_open_positions, _last_orphans_ids
    from backend.database import SessionLocal, Log
    db = SessionLocal()
    
    # Helper for parsing dates
    def parse_topstep_date(date_str):
        if not date_str: return None
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
                except:
                    pass
            return None

    # Helper for robust time comparison
    def ensure_aware_internal(d):
        if not d: return None
        if d.tzinfo is None:
            return d.replace(tzinfo=timezone.utc)
        return d

    try:
        # Get all accounts from TopStep
        all_accounts = await topstep_client.get_accounts()
        
        if not all_accounts:
            return
        
        all_orphans = []
        
        for account in all_accounts:
            account_id = account.get('id')
            account_name = account.get('name', str(account_id))
            
            try:
                # Fetch Current Positions for this account
                current_positions = await topstep_client.get_open_positions(account_id)
                
                # Convert to Dictionary: { 'contractId': position_data }
                current_map = {}
                for pos in current_positions:
                    cid = str(pos.get('contractId'))
                    current_map[cid] = pos
                
                # Get last known state for this account
                last_map = _last_open_positions.get(account_id, {})
                
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
                                print(f"📉 DETECTED PARTIAL: {prev_cid} on Account {account_name} ({prev_size} -> {current_size})")
                        
                        if is_full_close or is_partial:
                            if is_full_close:
                                print(f"💰 DETECTED CLOSURE: {prev_cid} on Account {account_name}")

                            # 1. Find the Open Trade Record FIRST
                            from backend.database import Trade
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

                            # 2. Fetch History to calculate PnL
                            recent_trades = await topstep_client.get_historical_trades(account_id, days=1)
                            
                            # 3. Filter Trades (Symbol match AND Time >= Entry Time)
                            relevant_trades = []
                            matching_trade = None # The specific close trade if any
                            
                            target_entry_time = None
                            if open_trade and open_trade.timestamp:
                                target_entry_time = ensure_aware_internal(open_trade.timestamp)

                            # Helper to safely get fallback ts
                            start_time_fallback = None
                            if target_entry_time:
                                start_time_fallback = target_entry_time - timedelta(seconds=5)
                            
                            for t in recent_trades:
                                t_sym = str(t.get('symbol') or '')
                                t_cid = str(t.get('contractId') or '')
                                
                                # Check Symbol Match
                                if t_sym == str(target_symbol) or t_cid == str(prev_cid):
                                    
                                    # Try to extract Entry Time from API Trade
                                    # Keys vary: entryTime, entryTimestamp, or fallback to creationTimestamp (fills)
                                    t_entry_ts = parse_topstep_date(t.get('entryTime') or t.get('entryTimestamp'))
                                    
                                    # If no explicit entry time in API (e.g. flat fill), fallback to filtering by > open_trade time
                                    if not t_entry_ts and start_time_fallback:
                                        # Fallback to Time-based logic
                                        t_created = parse_topstep_date(t.get('creationTimestamp') or t.get('timestamp') or t.get('time'))
                                        if t_created and t_created >= start_time_fallback:
                                            relevant_trades.append(t)
                                            if is_full_close and not matching_trade: matching_trade = t
                                        continue

                                    # Primary Logic: Match Entry Timestamp
                                    if t_entry_ts and target_entry_time:
                                        # Allow 2s tolerance for micro-variations
                                        diff = abs((t_entry_ts - target_entry_time).total_seconds())
                                        if diff < 2.0:
                                            relevant_trades.append(t)
                                            if is_full_close and not matching_trade: matching_trade = t
                            
                            # Calculate Stats
                            pnl_val = sum((t.get('pnl') or t.get('profitAndLoss') or 0) for t in relevant_trades)
                            total_fees = sum((t.get('fees') or 0) for t in relevant_trades)
                            
                            # Update DB
                            if open_trade:
                                if is_full_close:
                                    # Full Close Update
                                    exit_px = 0
                                    # Try to find the exit price from recent trades (first one is newest)
                                    if relevant_trades:
                                         # Assume API returns newest first? If not, sort.
                                         # Sort by time desc just to be sure
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
                                    # Notify
                                    if matching_trade:
                                        # Try to determine side
                                        raw_side = matching_trade.get('side')
                                        raw_side_upper = str(raw_side).upper().strip()
                                        if raw_side_upper in ["0", "BUY", "LONG"]: side_str = "SHORT"
                                        elif raw_side_upper in ["1", "2", "SELL", "SHORT"]: side_str = "LONG"
                                    
                                    # Calculate Real Daily PnL (Closed Trades Today + including this one)
                                    # Use API data to perfectly match /status command logic and avoid DB sync issues
                                    # We already have recent_trades (last 24h), we can filter them for "today"
                                    # But to be 100% aligned with /status, let's just sum the PnL of all trades returned by API for the day.
                                    # Since recent_trades = get_historical_trades(days=1), it contains today's trades.
                                    
                                    today_utc = datetime.now(timezone.utc).date()
                                    real_daily_pnl = 0.0
                                    real_daily_fees = 0.0
                                    
                                    for t in recent_trades:
                                        pnl = t.get('profitAndLoss') or t.get('pnl')
                                        fees = t.get('fees')
                                        if pnl is not None: real_daily_pnl += float(pnl)
                                        if fees is not None: real_daily_fees += float(fees)
                                    
                                    # Net PnL = Gross PnL - Fees (TopStep API PnL is usually Gross)
                                    # Verify if /status logic subtracts fees.
                                    # TelegramBot._get_daily_pnl: return total_pnl - total_fees
                                    final_daily_pnl = real_daily_pnl - real_daily_fees

                                    await telegram_service.notify_position_closed(
                                        symbol=f"{target_symbol} ({account_name})",
                                        side=side_str,
                                        entry_price=open_trade.entry_price or 0,
                                        exit_price=exit_px,
                                        pnl=pnl_val,
                                        fees=total_fees,
                                        quantity=open_trade.quantity, # Initial Qty
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
                                    print(f"✅ Trade #{open_trade.id} marked as CLOSED (PnL: ${pnl_val:.2f})")
                                
                                elif is_partial:
                                    # Partial Update
                                    # Update PnL/Fees accumulated so far (realized)
                                    open_trade.pnl = pnl_val
                                    open_trade.fees = total_fees
                                    db.commit()
                                    print(f"🔄 Trade #{open_trade.id} updated for PARTIAL (PnL: ${pnl_val:.2f})")

                            elif is_full_close:
                                # Fallback if no trade found (Manual close of manual position not in DB?)
                                # CHECK: Did we already close this via Webhook recently?
                                matching_closed_trade = db.query(Trade).filter(
                                    Trade.account_id == account_id,
                                    Trade.ticker.in_(ticker_variants),
                                    Trade.status == "CLOSED"
                                ).order_by(Trade.exit_time.desc()).first()
                                
                                is_recently_closed = False
                                if matching_closed_trade and matching_closed_trade.exit_time:
                                    # If closed within last 2 minutes, assume it's handled
                                    time_since_close = (datetime.now(timezone.utc) - ensure_aware_internal(matching_closed_trade.exit_time)).total_seconds()
                                    if time_since_close < 120:
                                        is_recently_closed = True
                                
                                if is_recently_closed:
                                    print(f"ℹ️ Full close detected for {prev_cid} (Handled by Webhook/Manual Close)")
                                else:
                                    print(f"⚠️ Full close but no OPEN trade record found for {prev_cid}")
                                    await telegram_service.send_message(
                                        f"💰 <b>Position Closed: {target_symbol}</b> ({account_name})"
                                    )
                
                # Detect New Positions (Opens)
                if last_map is not None:
                    for curr_cid, curr_pos in current_map.items():
                        if curr_cid not in last_map:
                            print(f"🔵 DETECTED OPEN: {curr_cid} on Account {account_name}")
                            
                            recent_trades = await topstep_client.get_historical_trades(account_id, days=1)
                            matching_fill = None
                            
                            if recent_trades:
                                for t in recent_trades:
                                    if str(t.get('contractId')) == str(curr_cid):
                                        matching_fill = t
                                        break
                            
                            if matching_fill:
                                fill_price = matching_fill.get('price') or 0
                                fill_side = str(matching_fill.get('side')).upper().strip()
                                # Try to capture the native Entry Timestamp from the API
                                entry_ts = parse_topstep_date(matching_fill.get('entryTime') or matching_fill.get('entryTimestamp'))
                                # Fallback to creation timestamp if entryTime not separate
                                if not entry_ts:
                                    entry_ts = parse_topstep_date(matching_fill.get('creationTimestamp') or matching_fill.get('timestamp') or matching_fill.get('time'))
                                
                                if fill_side in ["0", "BUY", "LONG"]:
                                    side_str = "BUY"
                                elif fill_side in ["1", "2", "SELL", "SHORT"]:
                                    side_str = "SELL"
                                else:
                                    side_str = "UNK"
                                
                                # Check if trade record exists or create one for manual trades
                                from backend.database import Trade
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
                                    # Update with real execution price AND time
                                    open_trade.entry_price = fill_price
                                    # CRITICAL: Update timestamp to match API Entry Time for future grouping
                                    if entry_ts:
                                         open_trade.timestamp = entry_ts
                                    db.commit()
                                    print(f"✅ Trade #{open_trade.id} updated with real fill: {fill_price}")
                                elif not open_trade:
                                    # NO MATCHING TRADE = MANUAL TRADE
                                    # Create a Trade record so it appears in history
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
                                    print(f"📝 Created Trade #{manual_trade.id} for MANUAL position: {tv_ticker} x{fill_qty} @ {fill_price}")
                                    open_trade = manual_trade
                                
                                # Prepare notification data
                                strat = open_trade.strategy if open_trade else "MANUAL"
                                tf = open_trade.timeframe if open_trade else "-"

                                await telegram_service.notify_position_opened(
                                    symbol=f"{matching_fill.get('symbol', curr_cid)} ({account_name})",
                                    side=side_str,
                                    quantity=matching_fill.get('size', 1),
                                    price=fill_price,
                                    order_id=str(matching_fill.get('orderId', ''))
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
                _last_open_positions[account_id] = current_map
                
                # =================================================================
                # DB RECONCILIATION (Detect Closures missed during downtime)
                # =================================================================
                from backend.database import Trade
                
                # Get ALL OPEN trades for this account from DB
                db_open_trades = db.query(Trade).filter(
                    Trade.account_id == account_id,
                    Trade.status == "OPEN"
                ).all()
                
                for trade in db_open_trades:
                    # Resolve expected contract ID for this trade
                    expected_cid = None
                    ticker_map_entry = db.query(TickerMap).filter(TickerMap.tv_ticker == trade.ticker).first()
                    
                    if ticker_map_entry:
                        expected_cid = ticker_map_entry.ts_contract_id
                    
                    # If we can't find contract ID via map, try to match by partial string in current map
                    # This is a fallback
                    if not expected_cid:
                        clean_ticker = trade.ticker.replace("1!", "").replace("2!", "").upper()
                        # Try to find match in current positions
                        for cid, pos in current_map.items():
                            if clean_ticker in str(pos.get('symbolId') or cid).upper():
                                expected_cid = cid
                                break
                    
                    # If still no expected CID, we can't properly verify, so skip
                    if not expected_cid:
                        continue
                        
                    # CHECK: Is this trade physically present in TopStep?
                    if expected_cid not in current_map:
                        print(f"🕵️ RECONCILIATION: Trade #{trade.id} ({trade.ticker}) is OPEN in DB but missing in API. Verifying closure...")
                        
                        # Verify against history (look for exit execution after trade entry)
                        recent_trades = await topstep_client.get_historical_trades(account_id, days=1)
                        trade_entry_time = trade.timestamp
                        
                        # Find matching exit execution
                        # We look for a trade with matching symbol and time > entry time
                        confirm_close = False
                        exit_fill = None
                        
                        for t in recent_trades:
                            t_cid = str(t.get('contractId') or '')
                            if t_cid == expected_cid:
                                t_time = parse_topstep_date(t.get('creationTimestamp') or t.get('timestamp') or t.get('time'))
                                t_time = ensure_aware_internal(t_time)
                                
                                # If trade has entry time, ensure this fill is AFTER it
                                if trade_entry_time:
                                    # Ensure trade_entry_time is aware
                                    trade_entry_time = ensure_aware_internal(trade_entry_time)
                                    
                                    try:
                                        if t_time and t_time > trade_entry_time:
                                            confirm_close = True
                                            exit_fill = t
                                            break
                                    except TypeError as e:
                                        print(f"⚠️ Date Comp Error: {e} | T: {t_time} ({t_time.tzinfo if t_time else 'None'}) vs Entry: {trade_entry_time} ({trade_entry_time.tzinfo if trade_entry_time else 'None'})")
                                        continue
                                
                                # If no entry time in DB (legacy?), assume recent fill is the exit
                                if not trade_entry_time:
                                    confirm_close = True
                                    exit_fill = t
                                    break
                        
                        if confirm_close:
                            # It is confirmed closed
                            exit_px = exit_fill.get('price') or exit_fill.get('fillPrice') or 0
                            pnl_val = exit_fill.get('pnl') or exit_fill.get('profitAndLoss') or 0
                            fees_val = exit_fill.get('fees') or 0
                            
                            trade.status = "CLOSED"
                            trade.exit_price = exit_px
                            trade.exit_time = datetime.now(pytz.UTC)
                            trade.pnl = pnl_val
                            trade.fees = fees_val
                            db.commit()
                            
                            print(f"✅ RECONCILIATION: Trade #{trade.id} marked as CLOSED (PnL: ${pnl_val:.2f})")
                            db.add(Log(level="INFO", message=f"RECONCILIATION: Trade #{trade.id} marked as CLOSED (PnL: ${pnl_val:.2f})"))
                            db.commit()
                            
                            await telegram_service.notify_position_closed(
                                symbol=f"{trade.ticker} ({account_name})",
                                side="LONG" if trade.action == "BUY" else "SHORT", # Use DB side
                                entry_price=trade.entry_price,
                                exit_price=exit_px,
                                pnl=pnl_val,
                                fees=fees_val,
                                quantity=trade.quantity
                            )
                        else:
                            print(f"⚠️ RECONCILIATION: Could not confirm closure in history for #{trade.id}. Keeping OPEN.")
                            db.add(Log(level="DEBUG", message=f"RECONCILIATION: Could not confirm closure in history for #{trade.id}"))
                            db.commit()

                # Check for orphaned orders on this account
                recent_orders = await topstep_client.get_orders(account_id, days=1)
                for o in recent_orders:
                    st = o.get('status')
                    if str(st).upper() in ["WORKING", "ACCEPTED", "1", "6"]:
                        cid = str(o.get('contractId'))
                        if cid not in current_map:
                            o['_account_name'] = account_name
                            all_orphans.append(o)
            
            except Exception as e:
                print(f"Monitor error for account {account_id}: {e}")
                continue
        
        # Notify orphans (globally)
        current_orphan_ids = set(str(o.get('orderId') or o.get('id')) for o in all_orphans)
        
        if all_orphans and current_orphan_ids != _last_orphans_ids:
            print(f"⚠️ Orphaned Orders Detected: {current_orphan_ids}")
            await telegram_service.notify_orphaned_orders(all_orphans)
        
        _last_orphans_ids = current_orphan_ids
        
    except Exception as e:
        print(f"Monitor Job Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def auto_flatten_job():
    """
    Global force flatten at scheduled time.
    Affects ALL accounts regardless of trading_enabled setting.
    """
    from backend.database import SessionLocal, Log
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


# Track handled blocks to prevent duplicate actions (reset daily by calendar job)
_handled_position_action_blocks = set()


async def position_action_job():
    """
    Checks for upcoming blocked periods and executes position actions.
    Runs every 30 seconds.
    
    Actions:
    - NOTHING: No action taken
    - BREAKEVEN: Move SL to entry price for all positions
    - FLATTEN: Close all positions and cancel all orders
    """
    global _handled_position_action_blocks
    from backend.database import SessionLocal, Log
    
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
        
        if block_id in _handled_position_action_blocks:
            return  # Already handled this block today
        
        # Mark as handled BEFORE executing to prevent race conditions
        _handled_position_action_blocks.add(block_id)
        
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


async def execute_breakeven_all(db, reason: str):
    """
    Move Stop Loss to entry price for all open positions across all accounts.
    If already in loss, SL moves to entry which may trigger auto-close.
    """
    from backend.database import Log
    
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
                            order_type = order.get('type')  # Looking for STOP type (4=Stop)
                            # STATUS CHECK: Only modify active orders
                            order_status = order.get('status')
                            if order_status not in ["Working", "Accepted", 1, 6]:
                                continue
                                
                            # existing code checked 2/STOP/SL, adding 4.
                            if order_type in [4, "STOP", "SL"]:
                                sl_order = order
                                break
                    
                    if sl_order:
                        # Modify SL to entry price
                        try:
                            # Use stopPrice for Stop orders as required by API
                            success = await topstep_client.modify_order(
                                account_id=account_id,
                                order_id=sl_order.get('id'),
                                stopPrice=entry_price
                            )
                            if success:
                                total_modified += 1
                            else:
                                # Quiet failure or debug log
                                db.add(Log(level="DEBUG", message=f"BREAKEVEN: Failed to modify SL for {contract_id} (API rejected)"))
                                total_skipped += 1
                            
                            await asyncio.sleep(0.1)  # Rate limit protection
                        except Exception as e:
                            db.add(Log(level="WARNING", message=f"BREAKEVEN: Failed to modify SL for {contract_id}: {e}"))
                            total_skipped += 1
                    else:
                        # No SL order found - log warning
                        # db.add(Log(level="WARNING", message=f"BREAKEVEN: No SL order found for {contract_id} on {account_name}"))
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


async def execute_flatten_all(db, reason: str):
    """
    Close all positions and cancel all orders across all accounts.
    Reuses logic from auto_flatten_job.
    """
    from backend.database import Log
    
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


async def api_health_check_job():
    """
    Periodically checks TopStep API health using /api/Status/ping.
    Sends Telegram notification after 3 consecutive failures.
    Logs recovery when API comes back online.
    """
    global _api_health
    from backend.database import SessionLocal, Log
    
    FAILURE_THRESHOLD = 3  # Notify after 3 consecutive failures
    
    is_healthy, response_time, error = await topstep_client.ping()
    
    _api_health["last_check_time"] = datetime.now(BRUSSELS_TZ).isoformat()
    _api_health["last_response_time"] = response_time
    
    if is_healthy:
        # API is healthy
        if not _api_health["is_healthy"]:
            # Was down, now recovered
            db = SessionLocal()
            try:
                db.add(Log(level="INFO", message=f"TopStep API recovered - Response time: {response_time:.0f}ms"))
                db.commit()
                await telegram_service.send_message(
                    f"✅ <b>TopStep API Recovered</b>\n\n"
                    f"• Response time: {response_time:.0f}ms\n"
                    f"• Previous failures: {_api_health['consecutive_failures']}"
                )
            finally:
                db.close()
        
        _api_health["consecutive_failures"] = 0
        _api_health["is_healthy"] = True
        _api_health["notified_down"] = False
    else:
        # API is down
        _api_health["consecutive_failures"] += 1
        _api_health["is_healthy"] = False
        
        db = SessionLocal()
        try:
            db.add(Log(level="ERROR", message=f"TopStep API ping failed: {error} (#{_api_health['consecutive_failures']})"))
            db.commit()
            
            # Send notification only after threshold and only once
            if _api_health["consecutive_failures"] >= FAILURE_THRESHOLD and not _api_health["notified_down"]:
                await telegram_service.send_message(
                    f"🚨 <b>TopStep API DOWN</b>\n\n"
                    f"• Error: {error}\n"
                    f"• Consecutive failures: {_api_health['consecutive_failures']}\n"
                    f"• Trading may be affected!"
                )
                _api_health["notified_down"] = True
        finally:
            db.close()


async def heartbeat_job():
    """
    Sends a heartbeat ping to external monitoring system (N8N).
    Includes metadata about bot status for richer monitoring.
    """
    global _heartbeat_state
    from backend.database import SessionLocal, Setting, AccountSettings
    
    webhook_url = os.getenv("HEARTBEAT_WEBHOOK_URL")
    if not webhook_url:
        return  # Heartbeat not configured
    
    db = SessionLocal()
    try:
        now = datetime.now(BRUSSELS_TZ)
        
        # Detect sleep: if last heartbeat was > 2 minutes ago, reset start_time
        if _heartbeat_state["last_sent"]:
            time_since_last = (now - _heartbeat_state["last_sent"]).total_seconds()
            if time_since_last > 120:  # More than 2 minutes = likely sleep/wake
                print(f"💤 Sleep detected ({int(time_since_last)}s gap). Resetting uptime.")
                _heartbeat_state["start_time"] = now
        
        # Calculate uptime
        uptime_seconds = 0
        if _heartbeat_state["start_time"]:
            uptime_seconds = (now - _heartbeat_state["start_time"]).total_seconds()
        
        # Get global trading status
        trading_enabled = True
        setting = db.query(Setting).filter(Setting.key == "trading_enabled").first()
        if setting:
            trading_enabled = setting.value == "true"
        
        # Get active accounts count
        try:
            all_accounts = await topstep_client.get_accounts()
            active_accounts = len(all_accounts) if all_accounts else 0
        except Exception:
            active_accounts = 0
        
        # Get API health status
        api_healthy = _api_health.get("is_healthy", True)
        
        # Build payload with both timestamp formats for flexibility
        payload = {
            "bot_name": "TopStepBot",
            "timestamp": now.isoformat(),
            "timestamp_unix": int(now.timestamp()),
            "uptime_seconds": int(uptime_seconds),
            "uptime_formatted": format_uptime(uptime_seconds),
            "trading_enabled": trading_enabled,
            "active_accounts": active_accounts,
            "api_healthy": api_healthy,
            "version": "2.0.0"
        }
        
        # Build headers (with optional auth)
        headers = {"Content-Type": "application/json"}
        auth_token = os.getenv("HEARTBEAT_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = auth_token
        
        # Send heartbeat
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload, headers=headers, timeout=10) as response:
                if response.status in [200, 201, 202, 204]:
                    _heartbeat_state["last_sent"] = datetime.now(BRUSSELS_TZ)
                    _heartbeat_state["consecutive_failures"] = 0
                else:
                    _heartbeat_state["consecutive_failures"] += 1
                    print(f"⚠️ Heartbeat failed: HTTP {response.status}")
    
    except asyncio.TimeoutError:
        _heartbeat_state["consecutive_failures"] += 1
        print("⚠️ Heartbeat timeout")
    except Exception as e:
        _heartbeat_state["consecutive_failures"] += 1
        print(f"⚠️ Heartbeat error: {e}")
    finally:
        db.close()


def format_uptime(seconds: float) -> str:
    """Format uptime in a human-readable way."""
    seconds = int(seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


async def send_shutdown_webhook():
    """
    Sends a shutdown notification to external monitoring system (N8N).
    This indicates a graceful shutdown (not a crash), so N8N can differentiate.
    """
    webhook_url = os.getenv("HEARTBEAT_WEBHOOK_URL")
    if not webhook_url:
        return
    
    try:
        now = datetime.now(BRUSSELS_TZ)
        
        # Calculate final uptime
        uptime_seconds = 0
        if _heartbeat_state["start_time"]:
            uptime_seconds = (now - _heartbeat_state["start_time"]).total_seconds()
        
        # Build payload with both timestamp formats for flexibility
        payload = {
            "bot_name": "TopStepBot",
            "timestamp": now.isoformat(),
            "timestamp_unix": int(now.timestamp()),
            "event": "shutdown",
            "reason": "graceful",
            "uptime_seconds": int(uptime_seconds),
            "uptime_formatted": format_uptime(uptime_seconds),
            "version": "2.0.0"
        }
        
        # Build headers (with optional auth)
        headers = {"Content-Type": "application/json"}
        auth_token = os.getenv("HEARTBEAT_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = auth_token
        
        # Send shutdown notification
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload, headers=headers, timeout=5) as response:
                if response.status in [200, 201, 202, 204]:
                    print("✅ Shutdown notification sent to monitoring")
                else:
                    print(f"⚠️ Shutdown notification failed: HTTP {response.status}")
    
    except Exception as e:
        print(f"⚠️ Shutdown notification error: {e}")


async def price_refresh_job():
    """
    Refresh current prices for all active contracts.
    Runs every 5 seconds to support near real-time unrealized PnL display.
    """
    try:
        # Get all open positions across all accounts
        accounts = await topstep_client.get_accounts()
        active_contracts = set()
        is_simulated = True  # Default to simulated
        
        for account in accounts:
            # Check if any account is live (not simulated)
            if not account.get("simulated", True):
                is_simulated = False
            
            positions = await topstep_client.get_open_positions(account.get("id"))
            for pos in positions:
                contract_id = pos.get("contractId")
                if contract_id:
                    active_contracts.add(contract_id)
        
        if active_contracts:
            await price_cache.refresh_prices(
                list(active_contracts), 
                topstep_client, 
                is_simulated=is_simulated
            )
    
    except Exception as e:
        print(f"Price refresh error: {e}")



async def discord_daily_summary_job():
    """
    Checks if any account has reached its configured Discord daily summary time.
    Sends daily summary with P&L, trade count, and balance.
    Only sends if trading day is enabled in global settings.
    """
    from backend.database import SessionLocal, Log, DiscordNotificationSettings, Trade
    db = SessionLocal()
    
    try:
        # Check if today is a trading day
        risk_engine = RiskEngine(db)
        settings = risk_engine.get_global_settings()
        trading_days = settings.get("trading_days", ["MON", "TUE", "WED", "THU", "FRI"])
        
        now_brussels = datetime.now(BRUSSELS_TZ)
        day_abbr = now_brussels.strftime("%a").upper()[:3]  # MON, TUE, etc.
        
        if day_abbr not in trading_days:
            # Not a trading day, skip
            return
        
        current_time = now_brussels.strftime("%H:%M")
        
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    
    # Seed default trading sessions
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        seed_default_sessions(db)
    except Exception as e:
        print(f"Session seeding error: {e}")
    finally:
        db.close()
    
    # Check & Run Startup Backup
    check_and_run_startup_backup()
    
    # Load Persistence State
    global _last_open_positions
    state = load_state()
    if "last_open_positions" in state:
        _last_open_positions = state["last_open_positions"]
        print(f"Loaded position state for {len(_last_open_positions)} accounts from persistence.")
    
    # Log System Restart
    db = SessionLocal()
    try:
        from backend.database import Log
        db.add(Log(level="WARNING", message="System Restarted: Connection Reset"))
        db.commit()
    except Exception as e:
        print(f"Startup Log Error: {e}")
    finally:
        db.close()

    # Auto-Connect to TopStep
    try:
        await topstep_client.login()
        
        # Pre-load existing positions to avoid false "Position Opened" notifications
        all_accounts = await topstep_client.get_accounts()
        open_positions_summary = []
        
        for account in all_accounts:
            account_id = account.get('id')
            account_name = account.get('name', str(account_id))
            
            try:
                positions = await topstep_client.get_open_positions(account_id)
                current_map = {}
                
                for pos in positions:
                    cid = str(pos.get('contractId'))
                    current_map[cid] = pos
                    
                    # Collect for summary
                    p_type = pos.get('type')
                    side = "LONG" if str(p_type) == '1' else "SHORT"
                    qty = pos.get('size', 1)
                    open_positions_summary.append({
                        'account': account_name,
                        'contract': cid,
                        'side': side,
                        'qty': qty
                    })
                
                # Store in state to prevent monitor from treating as new
                _last_open_positions[account_id] = current_map
                
            except Exception as e:
                print(f"Error pre-loading positions for {account_name}: {e}")
        
        # Send startup notification with positions summary
        if open_positions_summary:
            summary_msg = "🤖 <b>TopStep Bot Online</b>\n\n📈 <b>Open Positions:</b>\n"
            for p in open_positions_summary:
                side_emoji = "🟢" if p['side'] == "LONG" else "🔴"
                summary_msg += f"• {side_emoji} {p['contract']} x{p['qty']} ({p['account']})\n"
            await telegram_service.send_message(summary_msg)
        else:
            await telegram_service.notify_startup()
        
    except Exception as e:
        print(f"Auto-login failed: {e}")

    # Add Scheduled Jobs
    scheduler.add_job(auto_flatten_job, 'interval', minutes=1)
    scheduler.add_job(monitor_closed_positions_job, 'interval', seconds=5)
    scheduler.add_job(price_refresh_job, 'interval', seconds=5)
    
    # Maintenance Jobs
    scheduler.add_job(backup_database, 'cron', hour=3, minute=0)
    scheduler.add_job(clean_logs, 'cron', hour=3, minute=15, kwargs={'days': 7})
    
    # API Health Check (every 60 seconds)
    scheduler.add_job(api_health_check_job, 'interval', seconds=60)
    
    # Discord Daily Summary (every minute, checks configured times per account)
    scheduler.add_job(discord_daily_summary_job, 'interval', minutes=1)
    
    # Position Action Job (every 30 seconds - checks for upcoming blocked periods)
    scheduler.add_job(position_action_job, 'interval', seconds=30)

    # Heartbeat Job (configurable interval, default 60s)
    heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "60"))
    if os.getenv("HEARTBEAT_WEBHOOK_URL"):
        scheduler.add_job(heartbeat_job, 'interval', seconds=heartbeat_interval)
        print(f"Heartbeat configured: every {heartbeat_interval}s -> {os.getenv('HEARTBEAT_WEBHOOK_URL')}")

    # Initialize heartbeat start time
    _heartbeat_state["start_time"] = datetime.now(BRUSSELS_TZ)

    # Calendar Job (7:00 AM Brussels)
    scheduler.add_job(calendar_service.check_calendar_job, 'cron', hour=7, minute=0, timezone=BRUSSELS_TZ)
    
    # Init News Blocks on Startup - REMOVED to avoid 429 Rate Limits
    # try:
    #     print("📅 Initializing News Blocks...")
    #     await calendar_service.recalculate_news_blocks()
    # except Exception as e:
    #     print(f"⚠️ Failed to init news blocks: {e}")

    # Daily Contract Validation (Daily at 23:00 Brussels)
    scheduler.add_job(contract_validator.validate_active_mappings, 'cron', hour=23, minute=0, timezone=BRUSSELS_TZ, id='contract_validation')

    scheduler.start()
    print("Scheduler started.")

    # Start Telegram Polling (Background)
    polling_task = asyncio.create_task(telegram_bot.start_polling())
    
    yield
    
    # Shutdown
    print("\n🛑 Graceful shutdown initiated...")
    
    # Stop scheduler FIRST to prevent jobs from running during shutdown
    scheduler.shutdown(wait=False)
    print("   ✓ Scheduler stopped")
    
    # Stop Telegram polling
    telegram_bot.stop_polling()
    print("   ✓ Telegram polling stopped")
    
    # Send shutdown notification to monitoring
    await send_shutdown_webhook()
    print("   ✓ Shutdown notification sent")
    
    # Save Persistence State
    save_state({
        "last_open_positions": _last_open_positions
    })
    print("   ✓ State persisted")
    
    # Notify Telegram users
    await telegram_service.notify_shutdown()
    print("   ✓ Telegram notification sent")
    
    # Wait for polling task to finish
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
    
    print("✅ Shutdown complete")


app = FastAPI(title="TopStep Trading Bot", version="2.0.0", lifespan=lifespan)

# CORS Setup (for Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include Routers
app.include_router(webhook.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(strategies.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")


@app.get("/")
def read_root():
    return {"status": "online", "service": "TopStep Trading Bot", "version": "2.0.0"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/ngrok-url")
async def set_ngrok_url(payload: dict):
    """
    Receives the current Ngrok URL from start_bot.sh.
    Detects if URL has changed and notifies user via:
    - Terminal (print)
    - System Logs (DB)
    - Telegram
    """
    from backend.database import SessionLocal, Log
    
    new_url = payload.get("url", "").strip()
    if not new_url:
        return {"status": "error", "message": "No URL provided"}
    
    # Get last known URL
    last_url = get_last_ngrok_url()
    
    # Check for change
    if last_url and last_url != new_url:
        # URL has changed - notify on all channels
        print(f"⚠️  NGROK URL CHANGED!")
        print(f"   Old: {last_url}")
        print(f"   New: {new_url}")
        print(f"   👉 Update your TradingView webhooks to: {new_url}/api/webhook")
        
        # Log to database
        db = SessionLocal()
        try:
            db.add(Log(
                level="WARNING",
                message=f"Ngrok URL changed: {last_url} -> {new_url}"
            ))
            db.commit()
        finally:
            db.close()
        
        # Send Telegram notification
        await telegram_service.notify_ngrok_url_changed(last_url, new_url)
        
        # Save new URL
        save_ngrok_url(new_url)
        
        return {"status": "changed", "old_url": last_url, "new_url": new_url}
    
    elif not last_url:
        # First run - just save
        print(f"📝 Ngrok URL saved: {new_url}")
        save_ngrok_url(new_url)
        return {"status": "saved", "url": new_url}
    
    else:
        # URL unchanged
        return {"status": "unchanged", "url": new_url}
