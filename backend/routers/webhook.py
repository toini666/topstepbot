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
    
    # Immediate notification with timeframe
    await telegram_service.notify_signal(
        ticker=alert.ticker,
        action=alert.side,
        price=alert.entry,
        sl=alert.stop,
        tp=alert.tp,
        strategy=strategy_name,
        timeframe=alert.timeframe,
        accounts_count=0  # Will update after eligibility check
    )
    
    # Global checks (apply to ALL accounts)
    allowed, reason = risk_engine.check_market_hours()
    if not allowed:
        db.add(Log(level="WARNING", message=f"Signal Rejected (Market): {reason}"))
        db.commit()
        await telegram_service.notify_trade_rejection(alert.ticker, reason)
        return {"status": "rejected", "reason": reason}
    
    allowed, reason = risk_engine.check_blocked_periods()
    if not allowed:
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
    eligible_accounts = []
    
    for account in all_accounts:
        account_id = account.get('id')
        
        # Ensure account settings exist
        risk_engine.ensure_account_settings(account_id, account.get('name'))
        
        # Check account enabled
        allowed, reason = risk_engine.check_account_enabled(account_id)
        if not allowed:
            db.add(Log(level="DEBUG", message=f"Account {account.get('name')} disabled, skipping"))
            continue
        
        # Check strategy enabled
        allowed, reason = risk_engine.check_strategy_enabled(account_id, strategy_name)
        if not allowed:
            db.add(Log(level="DEBUG", message=f"Strategy {strategy_name} not enabled on {account.get('name')}, skipping"))
            continue
        
        # Check session allowed
        allowed, reason = risk_engine.check_session_allowed(account_id, strategy_name)
        if not allowed:
            db.add(Log(level="DEBUG", message=f"Session not allowed for {strategy_name} on {account.get('name')}: {reason}"))
            continue
        
        # Check for existing position on this ticker
        allowed, reason = await risk_engine.check_open_position(account_id, alert.ticker, topstep_client)
        if not allowed:
            db.add(Log(level="INFO", message=f"Position exists for {alert.ticker} on {account.get('name')}: {reason}"))
            continue
        
        eligible_accounts.append(account)
    
    if not eligible_accounts:
        db.add(Log(level="INFO", message=f"No eligible accounts for {alert.ticker} [{strategy_name}]"))
        db.commit()
        return {"status": "skipped", "reason": "No eligible accounts"}
    
    # Cross-account direction check
    # Only need to check against the first eligible account's intended direction
    allowed, reason = await risk_engine.check_cross_account_direction(
        ticker=alert.ticker,
        direction=alert.side,
        exclude_account_id=-1,  # Check all
        topstep_client=topstep_client
    )
    if not allowed:
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
            db.add(Log(level="WARNING", message=f"Qty=0 for account {account_id}, skipping"))
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
    from backend.services.telegram_service import telegram_service
    
    # Notify PARTIAL signal received
    await telegram_service.notify_partial_signal(
        ticker=alert.ticker,
        timeframe=alert.timeframe,
        strategy=strategy_name,
        price=alert.entry,
        new_sl=alert.stop,
        new_tp=alert.tp
    )
    
    # Find matching trades in our DB
    matching_trades = db.query(Trade).filter(
        Trade.ticker == alert.ticker,
        Trade.timeframe == alert.timeframe,
        Trade.strategy == strategy_name,
        Trade.status == TradeStatus.OPEN
    ).all()
    
    if not matching_trades:
        db.add(Log(level="INFO", message=f"PARTIAL: No matching position for {alert.ticker} TF={alert.timeframe} [{strategy_name}]"))
        db.commit()
        return {"status": "skipped", "reason": "No matching position"}
    
    db.add(Log(level="INFO", message=f"PARTIAL: Found {len(matching_trades)} matching trade(s) for {alert.ticker}"))
    
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
                # This prevents over-closing when stop/TP is hit
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
                
                # Notify execution - get fill price from response if available
                fill_price = response.get('fillPrice') or response.get('price')
                
                # If API response doesn't have fill price, fetch from recent trades
                if not fill_price:
                    try:
                        import asyncio
                        await asyncio.sleep(0.5)  # Small delay for trade to be recorded
                        recent_trades = await topstep_client.get_historical_trades(account_id, days=1)
                        clean_ticker = alert.ticker.replace("1!", "").replace("2!", "").upper()
                        for t in sorted(recent_trades, key=lambda x: x.get('creationTimestamp', ''), reverse=True):
                            if clean_ticker in str(t.get('contractId', '')).upper():
                                fill_price = t.get('price') or t.get('fillPrice')
                                break
                    except Exception:
                        pass
                
                await telegram_service.notify_partial_executed(
                    ticker=alert.ticker,
                    reduced_qty=reduce_qty,
                    remaining_qty=remaining_qty,
                    account_name=account_name,
                    sl_moved_to_entry=sl_moved,
                    side="LONG" if matching_pos.get('type') == 1 else "SHORT",
                    fill_price=fill_price
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
    
    # Notify CLOSE signal received
    await telegram_service.notify_close_signal(
        ticker=alert.ticker,
        timeframe=alert.timeframe,
        strategy=strategy_name,
        price=alert.entry
    )
    
    # Find matching trades in our DB
    matching_trades = db.query(Trade).filter(
        Trade.ticker == alert.ticker,
        Trade.timeframe == alert.timeframe,
        Trade.strategy == strategy_name,
        Trade.status == TradeStatus.OPEN
    ).all()
    
    if not matching_trades:
        db.add(Log(level="INFO", message=f"CLOSE: No matching position for {alert.ticker} TF={alert.timeframe} [{strategy_name}]"))
        db.commit()
        return {"status": "skipped", "reason": "No matching position"}
    
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
            
            # Close position with proper contract_id
            success = await topstep_client.close_position(account_id, contract_id)
            
            if success:
                # Cancel remaining orders for this contract
                await topstep_client.cancel_all_orders(account_id)
                
                # Update trade record
                trade.status = TradeStatus.CLOSED
                trade.exit_time = datetime.now(timezone.utc)
                
                # Get account name for notification
                account_settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
                account_name = (account_settings.account_name if account_settings and account_settings.account_name else str(account_id))
                
                db.add(Log(level="INFO", message=f"CLOSE: Position closed for {alert.ticker} on {account_name}"))
                
                # Notify execution - try to get fill price from recent trades
                fill_price = None
                try:
                    recent = await topstep_client.get_historical_trades(account_id, days=1)
                    for t in recent:
                        if clean_ticker in str(t.get('contractId', '')).upper():
                            fill_price = t.get('price') or t.get('fillPrice')
                            break
                except Exception:
                    pass
                
                await telegram_service.notify_close_executed(
                    ticker=alert.ticker,
                    account_name=account_name,
                    fill_price=fill_price
                )
                
                processed.append(account_name)
            
        except Exception as e:
            db.add(Log(level="ERROR", message=f"CLOSE failed for account {account_id}: {e}"))
    
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
            
            await telegram_service.notify_order_submitted(
                ticker=trade.ticker,
                action=trade.action,
                quantity=trade.quantity,
                price=trade.entry_price,
                order_id=trade.topstep_order_id,
                account_name=account_name
            )
            
            # Fix SL/TP prices
            try:
                await asyncio.sleep(1.0)
                await topstep_client.update_sl_tp_orders(
                    account_id=account_id,
                    ticker=trade.ticker,
                    sl_price=trade.sl,
                    tp_price=trade.tp
                )
            except Exception as ex:
                db.add(Log(level="ERROR", message=f"Failed to fix prices: {ex}"))
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
from datetime import datetime, timezone
