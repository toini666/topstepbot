from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db, Trade, Log, Setting, TickerMap
from typing import List, Optional
from backend.schemas import TradeResponse, LogResponse

router = APIRouter()

from backend.services.topstep_client import topstep_client
from backend.services.risk_engine import RiskEngine
from backend.schemas import (
    TradeResponse, LogResponse, AccountResponse, AccountSelectRequest, 
    SettingsRequest, PositionResponse, OrderResponse, HistoricalTradeResponse, 
    ClosePositionRequest, ConfigResponse, UpdateConfigRequest, TimeBlock,
    TickerMapCreate, TickerMapResponse
)
import json

@router.get("/dashboard/status")
def get_connection_status():
    """Checks if the TopStepClient has a valid token."""
    return {"connected": bool(topstep_client.token)}

@router.get("/dashboard/market-status")
def get_market_status(db: Session = Depends(get_db)):
    """Checks if the market is open using RiskEngine logic."""
    risk_engine = RiskEngine(db)
    is_open, reason = risk_engine.check_time_filters()
    return {
        "is_open": is_open,
        "reason": reason
    }

@router.get("/dashboard/config", response_model=ConfigResponse)
def get_config(db: Session = Depends(get_db)):
    risk_engine = RiskEngine(db)
    # RiskEngine calculates active settings based on DB defaults
    return ConfigResponse(
        risk_per_trade=risk_engine.settings.risk_per_trade,
        blocked_periods_enabled=risk_engine.settings.blocked_periods_enabled,
        blocked_periods=risk_engine.settings.blocked_periods,
        auto_flatten_enabled=risk_engine.settings.auto_flatten_enabled,
        auto_flatten_time=risk_engine.settings.auto_flatten_time
    )

@router.post("/dashboard/config")
def update_config(req: UpdateConfigRequest, db: Session = Depends(get_db)):
    if req.risk_per_trade is not None:
        setting = db.query(Setting).filter(Setting.key == "risk_amount").first()
        if not setting:
            setting = Setting(key="risk_amount", value=str(req.risk_per_trade))
            db.add(setting)
        else:
            setting.value = str(req.risk_per_trade)
    
    if req.blocked_periods_enabled is not None:
        setting = db.query(Setting).filter(Setting.key == "blocked_periods_enabled").first()
        val = "true" if req.blocked_periods_enabled else "false"
        if not setting:
            setting = Setting(key="blocked_periods_enabled", value=val)
            db.add(setting)
        else:
            setting.value = val

    if req.blocked_periods is not None:
        setting = db.query(Setting).filter(Setting.key == "blocked_periods").first()
        # Serialize list of objects to JSON
        json_data = json.dumps([b.model_dump() for b in req.blocked_periods])
        if not setting:
            setting = Setting(key="blocked_periods", value=json_data)
            db.add(setting)
        else:
            setting.value = json_data

    if req.auto_flatten_enabled is not None:
        setting = db.query(Setting).filter(Setting.key == "auto_flatten_enabled").first()
        val = "true" if req.auto_flatten_enabled else "false"
        if not setting:
            setting = Setting(key="auto_flatten_enabled", value=val)
            db.add(setting)
        else:
            setting.value = val

    if req.auto_flatten_time is not None:
        setting = db.query(Setting).filter(Setting.key == "auto_flatten_time").first()
        if not setting:
            setting = Setting(key="auto_flatten_time", value=req.auto_flatten_time)
            db.add(setting)
        else:
            setting.value = req.auto_flatten_time
            
    db.commit()
    return {"status": "updated"}

@router.post("/dashboard/settings/switch")
def toggle_master_switch(req: SettingsRequest, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == "master_switch").first()
    val = "ON" if req.trading_enabled else "OFF"
    
    if not setting:
        setting = Setting(key="master_switch", value=val)
        db.add(setting)
    else:
        setting.value = val
    db.commit()
    
    # Log Action
    db.add(Log(level="WARNING", message=f"Master Switch Toggled: {val}"))
    db.commit()
    return {"status": "updated", "trading_enabled": req.trading_enabled}

@router.get("/dashboard/settings")
def get_settings(db: Session = Depends(get_db)):
    # Quick retrieval of Master Switch
    switch = db.query(Setting).filter(Setting.key == "master_switch").first()
    enabled = True
    if switch and switch.value == "OFF":
        enabled = False
    return {"trading_enabled": enabled}

@router.get("/dashboard/trades", response_model=List[TradeResponse])
def get_trades(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    trades = db.query(Trade).order_by(Trade.timestamp.desc()).offset(skip).limit(limit).all()
    return trades

@router.get("/dashboard/accounts", response_model=List[AccountResponse])
async def get_accounts():
    accounts = await topstep_client.get_accounts()
    return accounts

@router.post("/dashboard/accounts/select")
def select_account(req: AccountSelectRequest, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
    if not setting:
        setting = Setting(key="selected_account_id", value=str(req.account_id))
        db.add(setting)
    else:
        setting.value = str(req.account_id)
    db.commit()
    return {"status": "updated", "account_id": req.account_id}

@router.get("/dashboard/accounts/selected")
def get_selected_account(db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
    if setting:
        return {"account_id": int(setting.value)}
    return {"account_id": None}

from datetime import datetime
from typing import List, Optional

@router.get("/dashboard/logs", response_model=List[LogResponse])
def get_logs(skip: int = 0, limit: int = 100, min_timestamp: Optional[datetime] = None, db: Session = Depends(get_db)):
    query = db.query(Log).order_by(Log.timestamp.desc())
    
    if min_timestamp:
        query = query.filter(Log.timestamp >= min_timestamp)
        # If filtering by time, ensure we get all logs (up to a reasonable safety max)
        if limit < 1000:
            limit = 1000
            
    logs = query.offset(skip).limit(limit).all()
    
    # Ensure Timezone Awareness (UTC)
    from datetime import timezone
    for log in logs:
        if log.timestamp and log.timestamp.tzinfo is None:
            log.timestamp = log.timestamp.replace(tzinfo=timezone.utc)
            
    return logs

@router.get("/dashboard/stats")
async def get_stats(db: Session = Depends(get_db)):
    # Calculate daily P&L, Win Rate, etc.
    # Placeholder
    return {
        "daily_pnl": 0.0,
        "active_trades":  db.query(Trade).filter(Trade.status == "OPEN").count(),
        # "account_balance": ... (Need to fetch from TopStep)
    }

@router.get("/dashboard/positions", response_model=List[PositionResponse])
async def get_positions(db: Session = Depends(get_db)):
    # 1. Get Selected Account
    setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
    if not setting:
        return []
        
    account_id = int(setting.value)
    positions = await topstep_client.get_open_positions(account_id)
    return positions

@router.get("/dashboard/orders", response_model=List[OrderResponse])
async def get_orders(days: int = 1, db: Session = Depends(get_db)):
    # 1. Get Selected Account
    setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
    if not setting:
        return []
        
    account_id = int(setting.value)
    orders = await topstep_client.get_orders(account_id, days=days)
    return orders

@router.get("/dashboard/trades-history", response_model=List[HistoricalTradeResponse])
async def get_historical_trades(days: int = 1, db: Session = Depends(get_db)):
    # 1. Get Selected Account
    setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
    if not setting:
        return []
        
    account_id = int(setting.value)
    trades = await topstep_client.get_historical_trades(account_id, days=days)
    return trades

@router.post("/dashboard/positions/close")
async def close_position_endpoint(req: ClosePositionRequest, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
    if not setting:
        return {"success": False, "message": "No account selected"}
    
    account_id = int(setting.value)

    # Log Action
    db.add(Log(level="WARNING", message=f"User Triggered: Close Position {req.contract_id} for Account {account_id}"))
    db.commit()

    # Auto-Cancel Associated Orders
    try:
        # Fetch recent orders to find working ones
        orders = await topstep_client.get_orders(account_id, days=1)
        
        for order in orders:
            # 1. Check Status (Working/Accepted/Pending)
            status = order.get('status')
            if status not in ["Working", "Accepted", 1, 6]:
                continue
                
            # 2. Check Contract Match
            # We match strict contractId strings as passed from frontend/position
            o_contract = order.get('contractId') or order.get('symbol')
            # Handle potential mismatch formats, but usually contractId should match
            if str(o_contract) == str(req.contract_id):
                oid = order.get('orderId') or order.get('id')
                if oid:
                    await topstep_client.cancel_order(account_id, oid)
                    
    except Exception as e:
        print(f"Auto-Cancel Matching Orders Failed: {e}")
        # Proceed to close position anyway

    success = await topstep_client.close_position(account_id, req.contract_id)
    return {"success": success}

@router.post("/dashboard/account/flatten")
async def flatten_account_endpoint(db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == "selected_account_id").first()
    if not setting:
        return {"success": False, "message": "No account selected"}
    
    account_id = int(setting.value)

    # Log Action
    db.add(Log(level="WARNING", message=f"User Triggered: Flatten & Cancel All for Account {account_id}"))
    db.commit()
    
    # 1. Cancel all open orders
    orders = await topstep_client.get_orders(account_id)
    # We need to filter for orders that are technically "open" or "working" if get_orders returns history
    # Based on API docs, get_orders likely searches history but also current.
    # Actually, to be safe, we should probably fetch open orders specifically if available, 
    # but `get_orders` filters by time.
    # Alternatively, we can use the `status` field from `get_orders`. 
    # Status: 1=Open, 6=Pending. Reference from previous view of App.tsx
    
    # Let's use get_orders and filter on the backend for now, or use `get_orders` which calls `/api/Order/search`.
    # Better yet, let's just loop through what we have.
    # A robust implementation would be to call `/api/Order/searchOpen` if it exists (it does in docs: /api/Order/searchOpen).
    # But I haven't implemented `get_open_orders` in client yet.
    # I can just iterate through `get_orders` (which I implemented to fetch last 24h) and cancel if status is OPEN/PENDING.
    
    for order in orders:
        if order['status'] in [1, 6]: # Open or Pending
             await topstep_client.cancel_order(account_id, order['id'])
    
    # 2. Close all positions
    positions = await topstep_client.get_open_positions(account_id)
    for pos in positions:
        await topstep_client.close_position(account_id, pos['contractId'])

    return {"success": True}

@router.post("/dashboard/logout")
async def logout_endpoint(db: Session = Depends(get_db)):
    await topstep_client.logout()
    db.add(Log(level="INFO", message="User Disconnected (Manual Logout)"))
    db.commit()
    return {"success": True}

# --- Ticker Mapping Endpoints (restored) ---

@router.get("/settings/ticker-map", response_model=dict)
def get_ticker_maps(db: Session = Depends(get_db)):
    maps = db.query(TickerMap).all()
    # Frontend expects { success: true, data: [...] } based on ConfigModal.tsx
    # We need to manually convert ORM objects to dict/Schema because we are wrapping them in a custom dict structure
    # and response_model=dict is too generic to trigger automagic ORM serialization for the nested list.
    data = [TickerMapResponse.model_validate(m).model_dump() for m in maps]
    return {"success": True, "data": data}

@router.post("/settings/ticker-map")
def create_ticker_map(map_in: TickerMapCreate, db: Session = Depends(get_db)):
    # Check if exists
    existing = db.query(TickerMap).filter(TickerMap.tv_ticker == map_in.tv_ticker).first()
    if existing:
        return {"success": False, "message": "Ticker map already exists"}
        
    new_map = TickerMap(
        tv_ticker=map_in.tv_ticker,
        ts_contract_id=map_in.ts_contract_id,
        ts_ticker=map_in.ts_ticker,
        tick_size=map_in.tick_size,
        tick_value=map_in.tick_value
    )
    db.add(new_map)
    db.commit()
    db.refresh(new_map)
    return {"success": True, "data": new_map}

@router.delete("/settings/ticker-map/{map_id}")
def delete_ticker_map(map_id: int, db: Session = Depends(get_db)):
    mapping = db.query(TickerMap).filter(TickerMap.id == map_id).first()
    if not mapping:
        return {"success": False, "message": "Mapping not found"}
    
    db.delete(mapping)
    db.commit()
    return {"success": True}
