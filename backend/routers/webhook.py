"""
Webhook Handler - Multi-Account Signal Execution

Handles 4 alert types:
- SETUP: Informational, logged only
- SIGNAL: Opens positions on ALL configured accounts
- PARTIAL: Reduces position size on matching positions
- CLOSE: Closes positions completely

All signals iterate ALL accounts and execute where strategy is configured.
"""

from fastapi import APIRouter, Depends, BackgroundTasks, Request, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import traceback
import asyncio

from backend.database import (
    get_db, Trade, TradeStatus, Log, TickerMap, 
    AccountSettings, Strategy
)
from backend.schemas import TradingViewAlert
from backend.services.risk_engine import RiskEngine
from backend.services.topstep_client import topstep_client

router = APIRouter()

# TradingView Official IP Addresses (for webhook security)
# https://www.tradingview.com/support/solutions/43000529348
TRADINGVIEW_IPS = [
    "52.89.214.238",
    "34.212.75.30",
    "54.218.53.128",
    "52.32.178.7"
]

# Allow localhost for testing (ngrok proxies show as localhost sometimes)
LOCALHOST_IPS = ["127.0.0.1", "localhost", "::1"]

def verify_tradingview_ip(request: Request):
    """
    Security middleware: Only allow webhooks from TradingView IPs.
    Allows localhost for local testing.
    """
    client_ip = request.client.host if request.client else None
    
    # Check X-Forwarded-For header (for proxies like ngrok)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in the chain is the original client
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Allow localhost for testing
    if client_ip in LOCALHOST_IPS:
        return True
    
    # Allow TradingView IPs
    if client_ip in TRADINGVIEW_IPS:
        return True
    
    # Block all others
    raise HTTPException(
        status_code=403, 
        detail=f"IP {client_ip} not authorized. Only TradingView webhooks allowed."
    )


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    alert: TradingViewAlert, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """
    Main webhook endpoint for TradingView alerts.
    Iterates ALL accounts and executes on those where conditions are met.
    Security: Only accepts requests from TradingView IPs.
    """
    # Verify IP before processing
    verify_tradingview_ip(request)
    
    strategy_name = alert.strat or "default"
    risk_engine = RiskEngine(db)
    
    # Log reception
    log_msg = f"Webhook: {alert.type} - {alert.ticker} {alert.side} @ {alert.entry} [{strategy_name}] TF={alert.timeframe}"
    db.add(Log(level="INFO", message=log_msg, details=alert.model_dump_json(exclude_none=True)))
    db.commit()
    
    # Route by alert type
    alert_type = alert.type.upper()
    
    if alert_type == "SETUP":
        return await handle_setup(alert, db)
    
    elif alert_type == "SIGNAL":
        return await handle_signal(alert, db, background_tasks)
    
    elif alert_type == "PARTIAL":
        return await handle_partial(alert, db)
    
    elif alert_type == "CLOSE":
        return await handle_close(alert, db)
    
    return {"status": "ignored", "reason": f"Unknown Alert Type: {alert.type}"}


# =============================================================================
# SETUP HANDLER
# =============================================================================

async def handle_setup(alert: TradingViewAlert, db: Session) -> Dict[str, Any]:
    """SETUP alerts are informational only - just log and return."""
    return {"status": "received", "message": "Setup logged", "type": "SETUP"}


# =============================================================================
# SIGNAL HANDLER (Multi-Account)
# =============================================================================

async def handle_signal(
    alert: TradingViewAlert, 
    db: Session, 
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    SIGNAL: Open position on ALL accounts where strategy is configured.
    """
    risk_engine = RiskEngine(db)
    from backend.services.telegram_service import telegram_service
    
    strategy_name = alert.strat or "default"
    
    # Track if we should notify - moved after eligibility checks (BR-1)
    should_notify_signal = False
    global_rejection_reason = None
    
    # Global checks (apply to ALL accounts)
    allowed, reason = risk_engine.check_market_hours()
    if not allowed:
        # BR-1: Notify signal + rejection for global rejection
        await telegram_service.notify_signal(
            ticker=alert.ticker, action=alert.side, price=alert.entry,
            sl=alert.stop, tp=alert.tp, strategy=strategy_name, timeframe=alert.timeframe
        )
        db.add(Log(level="WARNING", message=f"Signal Rejected (Market): {reason}"))
        db.commit()
        await telegram_service.notify_trade_rejection(alert.ticker, reason)
        return {"status": "rejected", "reason": reason}
    
    allowed, reason = risk_engine.check_blocked_periods()
    if not allowed:
        # BR-1: Notify signal + rejection for global rejection
        await telegram_service.notify_signal(
            ticker=alert.ticker, action=alert.side, price=alert.entry,
            sl=alert.stop, tp=alert.tp, strategy=strategy_name, timeframe=alert.timeframe
        )
        db.add(Log(level="WARNING", message=f"Signal Rejected (Blocked): {reason}"))
        db.commit()
        await telegram_service.notify_trade_rejection(alert.ticker, reason)
        return {"status": "rejected", "reason": reason}
    
    # Get ALL accounts from TopStep
    try:
        all_accounts = await topstep_client.get_accounts()
    except Exception as e:
        db.add(Log(level="ERROR", message=f"Failed to get accounts: {e}"))
        db.commit()
        return {"status": "error", "reason": "Failed to fetch accounts"}
    
    if not all_accounts:
        return {"status": "error", "reason": "No accounts available"}
    
    # Cross-account direction check (global across all accounts)
    # First, determine which accounts would execute and check for conflicts
    
    # Step 1: Fast sync checks (DB reads, no network I/O)
    accounts_for_position_check = []
    for account in all_accounts:
        account_id = account.get('id')
        
        # Ensure account settings exist
        risk_engine.ensure_account_settings(account_id, account.get('name'))
        
        # Check account enabled
        allowed, reason = risk_engine.check_account_enabled(account_id)
        if not allowed:
            continue
        
        # Check strategy enabled
        allowed, reason = risk_engine.check_strategy_enabled(account_id, strategy_name)
        if not allowed:
            continue
        
        # Check session allowed
        allowed, reason = risk_engine.check_session_allowed(account_id, strategy_name)
        if not allowed:
            continue
        
        accounts_for_position_check.append(account)
    
    # Step 2: Parallel async position checks (network I/O - the bottleneck)
    async def check_position_for_account(acc):
        account_id = acc.get('id')
        allowed, reason = await risk_engine.check_open_position(account_id, alert.ticker, topstep_client)
        return (acc, allowed, reason)
    
    eligible_accounts = []
    if accounts_for_position_check:
        position_results = await asyncio.gather(*[
            check_position_for_account(acc) for acc in accounts_for_position_check
        ])
        
        for acc, allowed, reason in position_results:
            if allowed:
                eligible_accounts.append(acc)
            else:
                db.add(Log(level="INFO", message=f"Position exists for {alert.ticker} on {acc.get('name')}: {reason}"))
    
    if not eligible_accounts:
        # BR-1: No notification if no eligible accounts (silent skip)
        db.add(Log(level="INFO", message=f"No eligible accounts for {alert.ticker} [{strategy_name}]"))
        db.commit()
        return {"status": "skipped", "reason": "No eligible accounts"}
    
    # BR-1: We have eligible accounts, send the signal notification
    await telegram_service.notify_signal(
        ticker=alert.ticker, action=alert.side, price=alert.entry,
        sl=alert.stop, tp=alert.tp, strategy=strategy_name,
        timeframe=alert.timeframe, accounts_count=len(eligible_accounts)
    )
    
    # Cross-account direction check
    # Only need to check against the first eligible account's intended direction
    allowed, reason = await risk_engine.check_cross_account_direction(
        ticker=alert.ticker,
        direction=alert.side,
        exclude_account_id=-1,  # Check all
        topstep_client=topstep_client
    )
    if not allowed:
        # Cross-account conflict - already notified signal above, just add rejection
        db.add(Log(level="WARNING", message=f"Signal Rejected (Cross-Account): {reason}"))
        db.commit()
        await telegram_service.notify_trade_rejection(alert.ticker, reason)
        return {"status": "rejected", "reason": reason}
    
    # Resolve contract info (once, reuse for all accounts)
    contract_id, tick_size, tick_value = await resolve_contract(alert.ticker, db)
    if not contract_id:
        await telegram_service.notify_error(f"Contract Not Found for {alert.ticker}")
        return {"status": "error", "reason": "Contract Not Found"}
    
    # Execute on all eligible accounts
    executed_accounts = []
    for account in eligible_accounts:
        account_id = account.get('id')
        
        # Calculate position size for this account
        risk_amount = risk_engine.get_risk_amount(account_id, strategy_name)
        qty = risk_engine.calculate_position_size(
            entry_price=alert.entry,
            sl_price=alert.stop,
            risk_amount=risk_amount,
            tick_size=tick_size,
            tick_value=tick_value
        )
        
        if qty == 0:
            # BR-4: Notify qty=0 rejection per account
            account_settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
            account_name = (account_settings.account_name if account_settings and account_settings.account_name else str(account_id))
            reason = f"Position size < 1 contract (risk: ${risk_amount}, SL distance too wide)"
            db.add(Log(level="WARNING", message=f"Qty=0 for {account_name}: {reason}"))
            await telegram_service.notify_trade_rejection(alert.ticker, reason, account_name=account_name)
            continue
        
        # Check contract limit
        limit_ok, limit_reason = await risk_engine.check_contract_limit(
            account_id, alert.ticker, qty, topstep_client
        )
        if not limit_ok:
            account_settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
            account_name = (account_settings.account_name if account_settings and account_settings.account_name else str(account_id))
            db.add(Log(level="WARNING", message=f"Contract limit exceeded for {alert.ticker} on {account_name}: {limit_reason}"))
            db.commit()
            await telegram_service.send_message(
                f"⚠️ <b>Trade Rejected: Contract Limit</b>\n\n"
                f"• Account: {account_name}\n"
                f"• Ticker: {alert.ticker}\n"
                f"• Reason: {limit_reason}"
            )
            continue
        
        # Map direction
        action = "BUY" if alert.side.upper() in ["BUY", "LONG"] else "SELL"
        
        # Calculate bracket ticks
        sl_dist_ticks = int(round(abs(alert.entry - alert.stop) / tick_size))
        tp_dist_ticks = int(round(abs(alert.entry - alert.tp) / tick_size)) if alert.tp else 0
        
        if action == "BUY":
            sl_ticks = -sl_dist_ticks
            tp_ticks = tp_dist_ticks if tp_dist_ticks else None
        else:
            sl_ticks = sl_dist_ticks
            tp_ticks = -tp_dist_ticks if tp_dist_ticks else None
        
        # Create trade record
        # Get current session for tracking
        current_session = risk_engine.get_current_session()
        
        # Create trade record
        trade = Trade(
            account_id=account_id,
            ticker=alert.ticker,
            action=action,
            entry_price=alert.entry,
            signal_entry_price=alert.entry,  # Preserve original signal price
            sl=alert.stop,
            tp=alert.tp,
            quantity=qty,
            status=TradeStatus.PENDING,
            strategy=strategy_name,
            timeframe=alert.timeframe,
            session=current_session
        )
        db.add(trade)
        db.commit()
        
        # Execute in background
        background_tasks.add_task(
            execute_trade, 
            trade.id, 
            sl_ticks, 
            tp_ticks, 
            contract_id, 
            account_id,
            db
        )
        
        db.add(Log(level="INFO", message=f"Trade executing: {trade.ticker} x{qty} on {account.get('name')}"))
        
        executed_accounts.append({"id": account_id, "name": account.get('name')})
    
    if executed_accounts:
        account_names = [a['name'] for a in executed_accounts]
        db.add(Log(level="INFO", message=f"Signal executing on accounts: {account_names}"))
        db.commit()
        return {"status": "received", "accounts": account_names, "type": "SIGNAL"}
    else:
        return {"status": "skipped", "reason": "No trades executed (qty=0 for all)"}


# =============================================================================
# PARTIAL HANDLER
# =============================================================================

async def handle_partial(alert: TradingViewAlert, db: Session) -> Dict[str, Any]:
    """
    PARTIAL: Reduce position size on matching positions.
    Matches on ticker + timeframe + strategy.
    """
    strategy_name = alert.strat or "default"
    risk_engine = RiskEngine(db)

    # Import services locally to avoid circular dependencies
    from backend.services.telegram_service import telegram_service
    from backend.services.discord_service import discord_service
    
    # BR-2: Notification moved after finding matching trades
    
    # Find matching trades in our DB
    matching_trades = db.query(Trade).filter(
        Trade.ticker == alert.ticker,
        Trade.timeframe == alert.timeframe,
        Trade.strategy == strategy_name,
        Trade.status == TradeStatus.OPEN
    ).all()
    
    if not matching_trades:
        # BR-2: No notification if no matching position (silent skip)
        db.add(Log(level="INFO", message=f"PARTIAL: No matching position for {alert.ticker} TF={alert.timeframe} [{strategy_name}]"))
        db.commit()
        return {"status": "skipped", "reason": "No matching position"}
    
    # BR-2: Matching trades found, send notification
    await telegram_service.notify_partial_signal(
        ticker=alert.ticker,
        timeframe=alert.timeframe,
        strategy=strategy_name,
        price=alert.entry,
        new_sl=alert.stop,
        new_tp=alert.tp,
        accounts=[t.account_id for t in matching_trades]
    )
    
    db.add(Log(level="INFO", message=f"PARTIAL: Found {len(matching_trades)} matching trade(s) for {alert.ticker}"))
    
    # Resolve tick info for calculations
    _, tick_size, tick_value = await resolve_contract(alert.ticker, db)
    
    processed = []
    
    for trade in matching_trades:
        account_id = trade.account_id
        
        # Get strategy config for partial settings
        config = risk_engine.get_strategy_config(account_id, strategy_name)
        if not config:
            continue
        
        partial_percent = config.partial_tp_percent
        move_sl_to_entry = config.move_sl_to_entry
        
        # Get current position from TopStep
        try:
            positions = await topstep_client.get_open_positions(account_id)
            clean_ticker = alert.ticker.replace("1!", "").replace("2!", "").upper()
            
            matching_pos = None
            for pos in positions:
                if clean_ticker in pos.get('contractId', '').upper():
                    matching_pos = pos
                    break
            
            if not matching_pos:
                continue
            
            current_size = matching_pos.get('size', 0)
            reduce_qty = max(1, int(current_size * (partial_percent / 100)))
            
            if reduce_qty >= current_size:
                reduce_qty = current_size - 1  # Keep at least 1
            
            if reduce_qty <= 0:
                continue
            
            # Use TopStep's dedicated partial close API
            contract_id = matching_pos.get('contractId')
            response = await topstep_client.partial_close_position(
                account_id=account_id,
                contract_id=contract_id,
                size=reduce_qty
            )
            
            if response.get("success"):
                # Get account name
                account_settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
                account_name = (account_settings.account_name if account_settings and account_settings.account_name else str(account_id))
                
                remaining_qty = current_size - reduce_qty
                
                db.add(Log(level="INFO", message=f"PARTIAL: Reduced {reduce_qty} on {alert.ticker} for {account_name} (remaining: {remaining_qty})"))
                
                # CRITICAL: Sync SL/TP order quantities with remaining position
                try:
                    synced_count = await topstep_client.sync_order_quantities(
                        account_id=account_id,
                        ticker=alert.ticker,
                        new_quantity=remaining_qty
                    )
                    if synced_count > 0:
                        db.add(Log(level="INFO", message=f"PARTIAL: Synced {synced_count} order(s) to qty={remaining_qty}"))
                except Exception as e:
                    db.add(Log(level="ERROR", message=f"Failed to sync order quantities: {e}"))
                
                # Move SL to entry if configured
                sl_moved = False
                if move_sl_to_entry and trade.entry_price:
                    try:
                        await topstep_client.update_sl_tp_orders(
                            account_id=account_id,
                            ticker=alert.ticker,
                            sl_price=trade.entry_price,
                            tp_price=alert.tp if alert.tp else trade.tp
                        )
                        db.add(Log(level="INFO", message=f"PARTIAL: SL moved to entry for {alert.ticker}"))
                        sl_moved = True
                    except Exception as e:
                        db.add(Log(level="ERROR", message=f"Failed to move SL: {e}"))
                
                # Update SL/TP if provided in alert
                if alert.stop or alert.tp:
                    try:
                        await topstep_client.update_sl_tp_orders(
                            account_id=account_id,
                            ticker=alert.ticker,
                            sl_price=alert.stop if alert.stop else trade.sl,
                            tp_price=alert.tp if alert.tp else trade.tp
                        )
                    except Exception as e:
                        db.add(Log(level="ERROR", message=f"Failed to update SL/TP: {e}"))
                
                # Fetch Financial Data (PnL)
                realized_pnl = 0.0
                fees = 0.0
                fill_price = response.get('fillPrice') or response.get('price')
                
                try:
                    await asyncio.sleep(4.0)  # Wait for trade to settle
                    recent_trades = await topstep_client.get_historical_trades(account_id, days=1)
                    
                    # Aggregate fills for this partial close
                    # We summed fills until we reach the reduced_qty
                    accumulated_qty = 0
                    accumulated_pnl = 0.0
                    accumulated_fees = 0.0
                    last_fill_price = 0.0
                    
                    now_utc = datetime.now(timezone.utc)
                    cutoff_time = now_utc - timedelta(seconds=60) # Look back 1 min
                    
                    # Sort by NEWEST first to find recent fills
                    sorted_fills = sorted(recent_trades, key=lambda x: x.get('creationTimestamp', ''), reverse=True)
                    
                    for t in sorted_fills:
                        if accumulated_qty >= reduce_qty:
                            break
                            
                        # Parse time
                        t_created_str = t.get('creationTimestamp') or t.get('timestamp')
                        if t_created_str:
                            try:
                                t_ts = datetime.fromisoformat(str(t_created_str).replace('Z', '+00:00'))
                                if t_ts.tzinfo is None: t_ts = t_ts.replace(tzinfo=timezone.utc)
                                
                                if t_ts < cutoff_time:
                                    continue
                            except ValueError:
                                # Date parsing failed, skip this fill
                                continue

                        # Check Contract
                        if clean_ticker not in str(t.get('contractId', '')).upper():
                            continue
                        
                        # Check if it's a closing trade (must have PnL)
                        # We ignore Side because it can be ambiguous, but PnL checks are robust for Exits.
                        raw_pnl = t.get('profitAndLoss')
                        if raw_pnl is None:
                            # Try 'pnl' key just in case
                            raw_pnl = t.get('pnl')
                        
                        if raw_pnl is None:
                            # No PnL means it's likely an entry or not a realized trade
                            continue
                        
                        # Aggregate
                        qty = int(t.get('size') or t.get('quantity') or t.get('qty') or 0)
                        pnl = float(t.get('pnl') or t.get('profitAndLoss') or 0.0)
                        fee = float(t.get('fees') or 0.0)
                        price = float(t.get('price') or t.get('fillPrice') or 0.0)
                        
                        # If this fill is part of our partial close
                        accumulated_qty += qty
                        accumulated_pnl += pnl
                        accumulated_fees += fee
                        last_fill_price = price
                        
                    if accumulated_qty > 0:
                        realized_pnl = accumulated_pnl
                        fees = accumulated_fees
                        fill_price = last_fill_price
                        db.add(Log(level="INFO", message=f"PARTIAL: Aggregated {accumulated_qty} qty, PnL: ${realized_pnl:.2f}, Fees: ${fees:.2f}"))
                    else:
                        db.add(Log(level="WARNING", message=f"PARTIAL: No matching fills found for aggregation."))

                except Exception as ex:
                    db.add(Log(level="WARNING", message=f"PARTIAL: Failed to fetch PnL: {ex}"))

                # Calculate Unrealized PnL (Latent)
                unrealized_pnl = 0.0
                if fill_price and trade.entry_price and tick_size > 0:
                    price_diff = fill_price - trade.entry_price
                    if matching_pos.get('type') == 2: # Short (TopStep type 2 usually 'Short', check docs if needed, but standard is 1=Long, 2=Short)
                         # Wait, TopStep API 'type' enum? 
                         # Usually standard: Side can be "BUY" or "SELL".
                         # Let's trust trade.action for direction
                         pass
                    
                    # Use trade action to be safe
                    if trade.action == "SELL": # It was a SHORT
                        price_diff = -price_diff
                    
                    unrealized_pnl = (price_diff / tick_size) * tick_value * remaining_qty
                
                # Notify Telegram
                await telegram_service.notify_partial_executed(
                    ticker=alert.ticker,
                    reduced_qty=reduce_qty,
                    remaining_qty=remaining_qty,
                    account_name=account_name,
                    sl_moved_to_entry=sl_moved,
                    side=trade.action,
                    fill_price=fill_price,
                    realized_pnl=realized_pnl,
                    unrealized_pnl=unrealized_pnl,
                    fees=fees
                )
                
                # Notify Discord
                await discord_service.notify_partial_executed(
                    account_id=account_id,
                    ticker=alert.ticker,
                    reduced_qty=reduce_qty,
                    remaining_qty=remaining_qty,
                    fill_price=fill_price,
                    realized_pnl=realized_pnl,
                    unrealized_pnl=unrealized_pnl,
                    fees=fees,
                    account_name=account_name,
                    strategy=strategy_name,
                    timeframe=alert.timeframe
                )
                
                processed.append(account_name)
            
        except Exception as e:
            db.add(Log(level="ERROR", message=f"PARTIAL failed for account {account_id}: {e}"))
    
    db.commit()
    
    if processed:
        return {"status": "processed", "accounts": processed, "type": "PARTIAL"}
    return {"status": "skipped", "reason": "No positions processed"}


# =============================================================================
# CLOSE HANDLER
# =============================================================================

async def handle_close(alert: TradingViewAlert, db: Session) -> Dict[str, Any]:
    """
    CLOSE: Close entire position for matching trades.
    Matches on ticker + timeframe + strategy.
    """
    strategy_name = alert.strat or "default"
    from backend.services.telegram_service import telegram_service
    
    # BR-3: Notification moved after finding matching trades
    
    # Find matching trades in our DB
    matching_trades = db.query(Trade).filter(
        Trade.ticker == alert.ticker,
        Trade.timeframe == alert.timeframe,
        Trade.strategy == strategy_name,
        Trade.status == TradeStatus.OPEN
    ).all()
    
    if not matching_trades:
        # BR-3: No notification if no matching position (silent skip)
        db.add(Log(level="INFO", message=f"CLOSE: No matching position for {alert.ticker} TF={alert.timeframe} [{strategy_name}]"))
        db.commit()
        return {"status": "skipped", "reason": "No matching position"}
    
    # BR-3: Matching trades found, send notification
    await telegram_service.notify_close_signal(
        ticker=alert.ticker,
        timeframe=alert.timeframe,
        strategy=strategy_name,
        price=alert.entry
    )
    
    db.add(Log(level="INFO", message=f"CLOSE: Found {len(matching_trades)} matching trade(s) for {alert.ticker}"))
    
    processed = []
    
    for trade in matching_trades:
        account_id = trade.account_id
        
        try:
            # Get current position from TopStep to find proper contract_id
            positions = await topstep_client.get_open_positions(account_id)
            clean_ticker = alert.ticker.replace("1!", "").replace("2!", "").upper()
            
            matching_pos = None
            for pos in positions:
                if clean_ticker in pos.get('contractId', '').upper():
                    matching_pos = pos
                    break
            
            if not matching_pos:
                db.add(Log(level="WARNING", message=f"CLOSE: No open position found for {alert.ticker} on account {account_id}"))
                continue
            
            contract_id = matching_pos.get('contractId')
            
        except Exception as e:
            db.add(Log(level="ERROR", message=f"CLOSE failed for account {account_id}: {e}"))
            continue
            
        # Execute Close
        success = await topstep_client.close_position(account_id, contract_id)
        
        if success:
            # Cancel remaining orders for this contract
            await topstep_client.cancel_all_orders(account_id)
            
            # Fetch recent trades to calculate final PnL/Fees
            # This ensures the database record is complete
            current_pnl = 0.0
            current_fees = 0.0
            exit_px = 0.0
            
            try:
                await asyncio.sleep(1.0) # Wait for fill to propagate
                recent_trades = await topstep_client.get_historical_trades(account_id, days=1)
                    
                # Filter for trades relevant to this position
                # Logic mirrors monitor_closed_positions_job
                relevant_trades = []
                
                # Determine start time validation
                start_time_fallback = None
                trade_entry_time = trade.timestamp
                if trade_entry_time:
                     if trade_entry_time.tzinfo is None:
                         trade_entry_time = trade_entry_time.replace(tzinfo=timezone.utc)
                     start_time_fallback = trade_entry_time - timedelta(seconds=5)
                
                for t in recent_trades:
                    t_cid = str(t.get('contractId') or '')
                    
                    # Check Contract Match
                    if clean_ticker in t_cid.upper() or t_cid == str(contract_id):
                        # Check Time Match (if available)
                        t_created_str = t.get('creationTimestamp') or t.get('timestamp') or t.get('time')
                        if t_created_str:
                            try:
                                t_created = datetime.fromisoformat(str(t_created_str).replace('Z', '+00:00'))
                                if t_created.tzinfo is None: t_created = t_created.replace(tzinfo=timezone.utc)
                                
                                if start_time_fallback and t_created >= start_time_fallback:
                                    relevant_trades.append(t)
                            except ValueError:
                                # If date parsing fails, include trade to be safe
                                relevant_trades.append(t)
                        else:
                            relevant_trades.append(t)
                
                # Calculate proper totals
                current_pnl = sum((t.get('pnl') or t.get('profitAndLoss') or 0) for t in relevant_trades)
                current_fees = sum((t.get('fees') or 0) for t in relevant_trades)
                
                # Get exit price from the latest fill
                if relevant_trades:
                    sorted_rel = sorted(relevant_trades, key=lambda x: x.get('creationTimestamp', ''), reverse=True)
                    last_fill = sorted_rel[0]
                    exit_px = last_fill.get('price') or last_fill.get('fillPrice') or 0
                    
            except Exception as ex:
                db.add(Log(level="WARNING", message=f"CLOSE: Failed to aggregate PnL: {ex}"))
            
            # Update trade record with final stats
            trade.status = TradeStatus.CLOSED
            trade.exit_time = datetime.now(timezone.utc)
            if current_pnl != 0: trade.pnl = current_pnl
            if current_fees != 0: trade.fees = current_fees
            if exit_px != 0: trade.exit_price = exit_px
            
            # Get account name for notification
            account_settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
            account_name = (account_settings.account_name if account_settings and account_settings.account_name else str(account_id))
            
            db.add(Log(level="INFO", message=f"CLOSE: Position closed for {alert.ticker} on {account_name} (PnL: ${current_pnl:.2f})"))
            
            await telegram_service.notify_close_executed(
                ticker=alert.ticker,
                account_name=account_name,
                fill_price=exit_px if exit_px else None,
                pnl=current_pnl,
                fees=current_fees
            )
            
            processed.append(account_name)
    
    db.commit()
    
    if processed:
        return {"status": "processed", "accounts": processed, "type": "CLOSE"}
    return {"status": "skipped", "reason": "No positions closed"}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def resolve_contract(ticker: str, db: Session):
    """Resolve contract ID and tick info from mapping or API."""
    # Check database mapping first
    mapping = db.query(TickerMap).filter(TickerMap.tv_ticker == ticker).first()
    
    if mapping:
        return mapping.ts_contract_id, mapping.tick_size, mapping.tick_value
    
    # Fallback to API
    contract = await topstep_client.get_contract_details(ticker)
    if not contract:
        return None, 0.25, 0.5
    
    tick_size = contract.get("tickSize", 0.25)
    tick_value = contract.get("tickValue", 0.5)
    
    if tick_size is None or tick_size == 0:
        tick_size = 0.25
    if tick_value is None:
        tick_value = 0.5
    
    # SAVE MAPPING FOR FUTURE USE (e.g. Reconciliation)
    try:
        new_map = TickerMap(
            tv_ticker=ticker,
            ts_contract_id=contract.get("id"),
            ts_ticker=contract.get("name"),
            tick_size=tick_size,
            tick_value=tick_value,
            micro_equivalent=1 # Default to 1, user can edit later
        )
        db.add(new_map)
        db.commit()
    except Exception as e:
        print(f"Failed to save TickerMap for {ticker}: {e}")
        # Continue even if save fails
    
    return contract.get("id"), tick_size, tick_value


async def execute_trade(
    trade_id: int, 
    sl_ticks: int, 
    tp_ticks: int, 
    contract_id: str, 
    account_id: int,
    db: Session
):
    """Execute trade in background."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        return
    
    from backend.services.telegram_service import telegram_service
    
    # Get account name for notifications
    account_settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
    account_name = (account_settings.account_name if account_settings and account_settings.account_name else str(account_id))
    
    try:
        response = await topstep_client.place_order(
            ticker=trade.ticker,
            action=trade.action,
            quantity=trade.quantity,
            price=trade.entry_price,
            account_id=account_id,
            sl_ticks=sl_ticks,
            tp_ticks=tp_ticks,
            contract_id=contract_id
        )
        
        if response.get("status") == "filled":
            trade.status = TradeStatus.OPEN
            trade.topstep_order_id = str(response.get('order_id', 'unknown'))
            
            db.add(Log(level="INFO", message=f"Order Executed: {trade.ticker} x{trade.quantity} on {account_name}"))
            
            # Notify Telegram (non-blocking to prioritize SL/TP setup)
            asyncio.create_task(telegram_service.notify_order_submitted(
                ticker=trade.ticker,
                action=trade.action,
                quantity=trade.quantity,
                price=trade.entry_price,
                order_id=trade.topstep_order_id,
                account_name=account_name
            ))
            
            # Fix SL/TP prices with retry logic
            sl_tp_success = False
            for attempt in range(3):
                try:
                    await asyncio.sleep(0.3 if attempt == 0 else 0.5 * (attempt + 1))
                    count = await topstep_client.update_sl_tp_orders(
                        account_id=account_id,
                        ticker=trade.ticker,
                        sl_price=trade.sl,
                        tp_price=trade.tp
                    )
                    if count > 0:
                        db.add(Log(level="INFO", message=f"SL/TP orders corrected ({count} orders) for {trade.ticker}"))
                        sl_tp_success = True
                        break
                    elif attempt < 2:
                        db.add(Log(level="DEBUG", message=f"SL/TP update attempt {attempt + 1}: No orders found, retrying..."))
                except Exception as ex:
                    if attempt < 2:
                        db.add(Log(level="WARNING", message=f"SL/TP update attempt {attempt + 1} failed: {ex}"))
                    else:
                        db.add(Log(level="ERROR", message=f"Failed to fix SL/TP after 3 attempts: {ex}"))
        else:
            trade.status = TradeStatus.REJECTED
            trade.rejection_reason = response.get("reason", "Unknown")
            db.add(Log(level="WARNING", message=f"Order Rejected: {trade.rejection_reason}"))
            await telegram_service.notify_trade_rejection(trade.ticker, trade.rejection_reason)
        
        db.commit()
        
    except Exception as e:
        trade.status = TradeStatus.REJECTED
        trade.rejection_reason = str(e)
        db.add(Log(level="ERROR", message=f"Execution Failed: {e}", details=traceback.format_exc()))
        db.commit()
        
        try:
            await telegram_service.notify_error(f"Execution Failed for {trade.ticker}: {e}")
        except Exception:
            pass


# Import for datetime in close handler
# Import for datetime in close handler
from datetime import datetime, timezone, timedelta
