from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from backend.database import get_db, Trade, TradeStatus, Log, Setting, TickerMap
from backend.schemas import TradingViewAlert
from backend.services.risk_engine import RiskEngine
from backend.services.topstep_client import topstep_client
from datetime import datetime
import traceback

router = APIRouter()

@router.post("/webhook")
async def receive_webhook(alert: TradingViewAlert, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. Log Reception
    log_msg = f"Webhook Received: {alert.type} - {alert.ticker} {alert.direction} @ {alert.entry}"
    # Use model_dump_json for Pydantic v2
    log = Log(level="INFO", message=log_msg, details=alert.model_dump_json(exclude_none=True))
    db.add(log)
    db.commit()

    # 2. Handle SETUP (Log & Exit)
    if alert.type.upper() == "SETUP":
        # Already logged above, just return
        return {"status": "received", "message": "Setup logged", "type": "SETUP"}

    # 3. Handle SIGNAL (Execute Trade)
    if alert.type.upper() == "SIGNAL":
        # Initialize Services
        risk_engine = RiskEngine(db)
        from backend.services.telegram_service import telegram_service
        
        # 0. Notify Signal Received (Immediate)
        await telegram_service.notify_signal(
            ticker=alert.ticker,
            action=alert.direction,
            price=alert.entry,
            sl=alert.stop,
            tp=alert.tp
        )

        # Global Switch
        allowed, reason = risk_engine.check_global_switch()
        if not allowed:
            log_reject = Log(level="WARNING", message=f"Trade Rejected (Switch): {reason}")
            db.add(log_reject)
            db.commit()
            await telegram_service.notify_trade_rejection(alert.ticker, reason)
            return {"status": "rejected", "reason": reason}

        # Time Filters
        allowed, reason = risk_engine.check_time_filters()
        if not allowed:
            log_reject = Log(level="WARNING", message=f"Trade Rejected (Time): {reason}")
            db.add(log_reject)
            db.commit()
            await telegram_service.notify_trade_rejection(alert.ticker, reason)
            return {"status": "rejected", "reason": reason}



        # Check Active Account ID
        setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
        if not setting:
            return {"status": "rejected", "reason": "No Account Selected"}
        account_id = int(setting.value)

        # Check for Existing Position on Ticker
        # We need to await this
        allowed, reason = await risk_engine.check_open_position(account_id, alert.ticker, topstep_client)
        if not allowed:
            log_reject = Log(level="WARNING", message=f"Trade Rejected (Position Open): {reason}")
            db.add(log_reject)
            db.commit()
            await telegram_service.notify_trade_rejection(alert.ticker, reason)
            return {"status": "rejected", "reason": reason}

        # Resolve Instrument Info via API
        # We need to await this, but receive_webhook is async, so it's fine.
        # But wait, execute_trade is the background task. 
        # Ideally, we should fetch details HERE to validate/calculate risk effectively and fail fast?
        # OR we pass the ticker to background task and do it all there?
        # User wants position sizing based on risk. If we do it in background, we can't return immediate rejection reason for sizing issues (though 202 is fine).
        # Fetching external API here adds latency to the webhook response (TradingView might timeout if > 3-5s).
        # TopStep API might verify token which takes time.
        # Logic: Check TickerMap first, then Fallback to API
        contract_id = None
        tick_size = 0.25
        tick_value = 0.5
        
        # 1. Check Database Mapping
        mapping = db.query(TickerMap).filter(TickerMap.tv_ticker == alert.ticker).first()
        
        if mapping:
            # log_map = Log(level="INFO", message=f"Using Mapped Contract: {mapping.tv_ticker} -> {mapping.ts_ticker}")
            # db.add(log_map)
            contract_id = mapping.ts_contract_id
            tick_size = mapping.tick_size
            tick_value = mapping.tick_value
        else:
            # 2. Fallback to API Lookup
            contract = await topstep_client.get_contract_details(alert.ticker)
            if not contract:
                 log_err = Log(level="ERROR", message=f"Contract Retrieval Failed for {alert.ticker}")
                 db.add(log_err)
                 db.commit()
                 await telegram_service.notify_error(f"Contract Not Found for {alert.ticker}")
                 return {"status": "error", "reason": "Contract Not Found"}
    
            tick_size = contract.get("tickSize", 0.25)
            tick_value = contract.get("tickValue", 0.5)
            # Safe Fallback if API returns None/Null
            if tick_size is None or tick_size == 0: tick_size = 0.25 
            if tick_value is None: tick_value = 0.5
            
            contract_id = contract.get("id")

        # Calculate Quantity
        qty = risk_engine.calculate_position_size(
            entry_price=alert.entry, 
            sl_price=alert.stop, 
            risk_amount=risk_engine.settings.risk_per_trade,
            tick_size=tick_size,
            tick_value=tick_value
        )
        
        if qty == 0:
             await telegram_service.notify_trade_rejection(alert.ticker, "Calculated Quantity is 0 (Check Risk Settings)")
             return {"status": "rejected", "reason": "Calculated Quantity is 0"}

        # Map Direction
        direction_map = {
            "LONG": "BUY", "BUY": "BUY",
            "SHORT": "SELL", "SELL": "SELL"
        }
        action = direction_map.get(alert.direction.upper(), "BUY")

        # Calculate Ticks for Brackets (Signed)
        # API Rules:
        # Long (Buy): SL Ticks < 0, TP Ticks > 0
        # Short (Sell): SL Ticks > 0, TP Ticks < 0
        
        sl_dist_ticks = int(round(abs(alert.entry - alert.stop) / tick_size))
        tp_dist_ticks = int(round(abs(alert.entry - alert.tp) / tick_size))
        
        if action == "BUY":
            sl_ticks = -sl_dist_ticks
            tp_ticks = tp_dist_ticks
        else: # SELL
            sl_ticks = sl_dist_ticks
            tp_ticks = -tp_dist_ticks

        # Create Trade Record (Pending)
        trade = Trade(
            ticker=alert.ticker,
            action=action,
            entry_price=alert.entry,
            sl=alert.stop,
            tp=alert.tp,
            quantity=qty,
            status=TradeStatus.PENDING
        )
        db.add(trade)
        db.commit()

        # Execute Order (Background Task)
        # We process the order using the PRE-RESOLVED contract_id to avoid looking it up again
        background_tasks.add_task(execute_trade, trade.id, sl_ticks, tp_ticks, contract_id, db)

        return {"status": "received", "trade_id": trade.id, "type": "SIGNAL"}

    return {"status": "ignored", "reason": f"Unknown Alert Type: {alert.type}"}

async def execute_trade(trade_id: int, sl_ticks: int, tp_ticks: int, contract_id: str, db: Session):
    # Re-fetch trade because db session might be closed/different in implementation 
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        return

    from backend.services.telegram_service import telegram_service

    try:
        # Retrieve Selected Account from Settings
        setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
        if not setting:
            raise Exception("No Account Selected in Dashboard")
            
        account_id = int(setting.value)
        
        # db.add(Log(level="INFO", message=f"Execute Trade: {trade.ticker} x {trade.quantity} | SL: {trade.sl} | TP: {trade.tp}"))
        
        # Place Market Order with Brackets
        # We manually modify place_order to verify it accepts contract_id if we want to save a lookup
        # But our place_order method currently takes 'ticker' and looks it up.
        # We should update place_order to optinally take contract_id directly.
        # Checking topstep_client.place_order... it calls find_contract(ticker).
        # We can optimize this by updating place_order to accept contract_id argument. 
        # But for now, relying on cache or re-lookup is 'ok' but inefficient.
        # Actually I can just pass the contract_id as ticker if I update logic there? No, that's hacky.
        # I will update place_order in next step or assume re-lookup is fast enough for now (it's in background task).
        # Actually, I already have the contract ID. I passed it to execute_trade.
        # I should probably update place_order to allow skipping lookup.
        # For this edit, I'll stick to passing ticker and let it resolve again OR 
        # BETTER: I'll update place_order signature in the next step to accept contract_id override.
        # Wait, I can't do multiple file edits in one turn easily if I didn't plan it.
        # But I control topstep_client.py. 
        
        # UPDATE: The previous turn updated place_order to take brackets. 
        # It DOES NOT take contract_id override yet. 
        # Ideally I should have updated it. 
        # However, `find_contract` is robust.
        # I will proceed with calling `place_order` with ticker. 
        # NOTE: `find_contract` uses `get_contract_details`. 
        # It's an extra call but acceptable for MVP.
        
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
            # Log Success
            db.add(Log(level="INFO", message=f"Order Executed: {trade.ticker} x {trade.quantity} | ID: {trade.topstep_order_id}"))
            
            # NOTIFY TELEGRAM (SUCCESS)
            await telegram_service.notify_order_submitted(
                ticker=trade.ticker,
                action=trade.action,
                quantity=trade.quantity,
                price=trade.entry_price,
                order_id=trade.topstep_order_id
            )

            # Post-Fill: Correct SL/TP Prices (Drift Fix)
            try:
                # Wait briefly for brackets to register?
                import asyncio
                await asyncio.sleep(1.0) 
                updated_count = await topstep_client.update_sl_tp_orders(
                    account_id=account_id, 
                    ticker=trade.ticker, 
                    sl_price=trade.sl, 
                    tp_price=trade.tp
                )
                if updated_count > 0:
                    db.add(Log(level="INFO", message=f"Fixed Prices for {updated_count} Orders on {trade.ticker}"))
            except Exception as ex:
                 db.add(Log(level="ERROR", message=f"Failed to Fix Prices: {ex}"))
        else:
            trade.status = TradeStatus.REJECTED
            trade.rejection_reason = response.get("reason", "Unknown")
            db.add(Log(level="WARNING", message=f"Order Rejected: {trade.rejection_reason}"))
            
            # NOTIFY TELEGRAM (REJECTION - API)
            await telegram_service.notify_trade_rejection(
                ticker=trade.ticker,
                reason=trade.rejection_reason
            )
            
        db.commit()
        
    except Exception as e:
        trade.status = TradeStatus.REJECTED
        trade.rejection_reason = str(e)
        error_details = traceback.format_exc()
        db.add(Log(level="ERROR", message=f"Execution Failed: {e}", details=error_details))
        db.commit()
        
        # NOTIFY TELEGRAM (ERROR)
        try:
            await telegram_service.notify_error(f"Execution Failed for {trade.ticker}: {e}")
        except:
            pass
