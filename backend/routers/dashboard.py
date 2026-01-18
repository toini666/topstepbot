"""
Dashboard API - Settings Management & Account Controls

Provides endpoints for:
- Global settings management
- Account settings (per-account)
- Strategy configuration (per-account)
- Trading sessions
- Position and order management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import json

from backend.database import (
    get_db, Trade, Log, Setting, TickerMap,
    AccountSettings, AccountStrategyConfig, TradingSession, Strategy,
    DiscordNotificationSettings
)
from backend.schemas import (
    TradeResponse, LogResponse, AccountResponse,
    PositionResponse, OrderResponse, HistoricalTradeResponse,
    ClosePositionRequest, SettingsToggleRequest,
    GlobalSettingsResponse, GlobalSettingsUpdate, TimeBlock,
    TickerMapCreate, TickerMapResponse,
    AccountSettingsResponse, AccountSettingsUpdate,
    AccountStrategyConfigResponse, AccountStrategyConfigCreate, AccountStrategyConfigUpdate,
    TradingSessionResponse, TradingSessionCreate,
    AccountResponse,
    DiscordNotificationSettingsUpdate, DiscordNotificationSettingsResponse,
    PositionResponse,
    OrderResponse,
    TradeResponse,
    LogResponse
)
from backend.services.topstep_client import topstep_client
from backend.services.risk_engine import RiskEngine
from backend.services.reconciliation_service import preview_reconciliation, apply_reconciliation

router = APIRouter()


# =============================================================================
# CONNECTION STATUS
# =============================================================================

@router.get("/dashboard/status")
def get_connection_status():
    """Check if TopStep client has valid token."""
    return {"connected": bool(topstep_client.token)}


@router.get("/dashboard/market-status")
def get_market_status(db: Session = Depends(get_db)):
    """Check if market is open and if trading is allowed."""
    risk_engine = RiskEngine(db)
    
    # Market status (for UI banner) - based on market hours + weekend_markets_open
    is_market_open, market_reason = risk_engine.check_market_open()
    
    # Trading allowed (for trade validation) - based on trading_days + market hours + blocked periods
    is_trading_allowed, trading_reason = risk_engine.check_market_hours()
    if is_trading_allowed:
        is_trading_allowed, trading_reason = risk_engine.check_blocked_periods()
    
    current_session = risk_engine.get_current_session()
    
    return {
        "is_open": is_market_open,
        "reason": market_reason,
        "is_trading_allowed": is_trading_allowed,
        "trading_reason": trading_reason,
        "current_session": current_session
    }


# =============================================================================
# GLOBAL SETTINGS
# =============================================================================

@router.get("/dashboard/config", response_model=GlobalSettingsResponse)
def get_global_config(db: Session = Depends(get_db)):
    """Get all global settings."""
    risk_engine = RiskEngine(db)
    settings = risk_engine.get_global_settings()
    
    return GlobalSettingsResponse(
        blocked_periods_enabled=settings.get("blocked_periods_enabled", True),
        blocked_periods=[TimeBlock(**b) for b in settings.get("blocked_periods", [])],
        auto_flatten_enabled=settings.get("auto_flatten_enabled", False),
        auto_flatten_time=settings.get("auto_flatten_time", "21:55"),
        market_open_time=settings.get("market_open_time", "00:00"),
        market_close_time=settings.get("market_close_time", "22:00"),
        weekend_markets_open=settings.get("weekend_markets_open", False),
        trading_days=settings.get("trading_days", ["MON", "TUE", "WED", "THU", "FRI"]),
        enforce_single_position_per_asset=settings.get("enforce_single_position_per_asset", True),
        block_cross_account_opposite=settings.get("block_cross_account_opposite", True),
        # News Block Settings
        news_block_enabled=settings.get("news_block_enabled", False),
        news_block_before_minutes=settings.get("news_block_before_minutes", 5),
        news_block_after_minutes=settings.get("news_block_after_minutes", 5),
        # Position Action Settings
        blocked_hours_position_action=settings.get("blocked_hours_position_action", "NOTHING"),
        position_action_buffer_minutes=settings.get("position_action_buffer_minutes", 1)
    )


@router.post("/dashboard/config")
def update_global_config(req: GlobalSettingsUpdate, db: Session = Depends(get_db)):
    """Update global settings."""
    def set_setting(key: str, value: str):
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = value
        else:
            db.add(Setting(key=key, value=value))
    
    log_messages = []
    
    if req.blocked_periods_enabled is not None:
        set_setting("blocked_periods_enabled", "true" if req.blocked_periods_enabled else "false")
    
    if req.blocked_periods is not None:
        json_data = json.dumps([b.model_dump() for b in req.blocked_periods])
        set_setting("blocked_periods", json_data)
    
    if req.auto_flatten_enabled is not None:
        set_setting("auto_flatten_enabled", "true" if req.auto_flatten_enabled else "false")
    
    if req.auto_flatten_time is not None:
        set_setting("auto_flatten_time", req.auto_flatten_time)
    
    if req.market_open_time is not None:
        set_setting("market_open_time", req.market_open_time)
    
    if req.market_close_time is not None:
        set_setting("market_close_time", req.market_close_time)
    
    # Weekend markets toggle
    if req.weekend_markets_open is not None:
        set_setting("weekend_markets_open", "true" if req.weekend_markets_open else "false")
        status = "OPEN" if req.weekend_markets_open else "CLOSED"
        log_messages.append(f"Weekend markets set to {status}")
    
    # Trading days (user preference)
    if req.trading_days is not None:
        set_setting("trading_days", json.dumps(req.trading_days))
        log_messages.append(f"Trading days updated to [{','.join(req.trading_days)}]")
    
    if req.enforce_single_position_per_asset is not None:
        set_setting("enforce_single_position_per_asset", "true" if req.enforce_single_position_per_asset else "false")
        status = "ENABLED" if req.enforce_single_position_per_asset else "DISABLED"
        log_messages.append(f"Single position per asset rule {status}")
    
    if req.block_cross_account_opposite is not None:
        set_setting("block_cross_account_opposite", "true" if req.block_cross_account_opposite else "false")
        status = "ENABLED" if req.block_cross_account_opposite else "DISABLED"
        log_messages.append(f"Cross-account direction blocking {status}")
    
    # News Block Settings
    if req.news_block_enabled is not None:
        set_setting("news_block_enabled", "true" if req.news_block_enabled else "false")
        status = "ENABLED" if req.news_block_enabled else "DISABLED"
        log_messages.append(f"News block {status}")
    
    if req.news_block_before_minutes is not None:
        set_setting("news_block_before_minutes", str(req.news_block_before_minutes))
    
    if req.news_block_after_minutes is not None:
        set_setting("news_block_after_minutes", str(req.news_block_after_minutes))
    
    # Position Action on Blocked Hours
    if req.blocked_hours_position_action is not None:
        set_setting("blocked_hours_position_action", req.blocked_hours_position_action)
        log_messages.append(f"Blocked hours position action set to {req.blocked_hours_position_action}")
    
    if req.position_action_buffer_minutes is not None:
        set_setting("position_action_buffer_minutes", str(req.position_action_buffer_minutes))
    
    # Log changes
    for msg in log_messages:
        db.add(Log(level="INFO", message=f"Global Settings: {msg}"))
    
    db.add(Log(level="INFO", message="Global Settings Updated", details=json.dumps(req.model_dump(), default=str)))
    db.commit()
    return {"status": "updated"}


# =============================================================================
# NEWS BLOCKS
# =============================================================================

@router.get("/dashboard/news-blocks")
def get_news_blocks(db: Session = Depends(get_db)):
    """Get today's calculated news blocks from calendar service."""
    from backend.services.calendar_service import calendar_service
    
    risk_engine = RiskEngine(db)
    settings = risk_engine.get_global_settings()
    
    return {
        "enabled": settings.get("news_block_enabled", False),
        "blocks": calendar_service.get_today_news_blocks()
    }


# =============================================================================
# TRADING SESSIONS
# =============================================================================

@router.get("/settings/sessions", response_model=List[TradingSessionResponse])
def get_trading_sessions(db: Session = Depends(get_db)):
    """Get all trading sessions."""
    return db.query(TradingSession).all()


@router.post("/settings/sessions", response_model=TradingSessionResponse)
def create_session(session: TradingSessionCreate, db: Session = Depends(get_db)):
    """Create a new trading session."""
    # Check if exists by name
    existing = db.query(TradingSession).filter(TradingSession.name == session.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Session with this name already exists")
    
    new_session = TradingSession(**session.model_dump())
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    db.add(Log(level="INFO", message=f"Created new session: {new_session.name}"))
    db.commit()
    
    return new_session


@router.put("/settings/sessions/{session_id}", response_model=TradingSessionResponse)
def update_session(session_id: int, session: TradingSessionCreate, db: Session = Depends(get_db)):
    """Update an existing trading session."""
    existing = db.query(TradingSession).filter(TradingSession.id == session_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update fields
    # Note: We might want to prevent name changes if used by strategies, but for now allow it.
    existing.name = session.name
    existing.display_name = session.display_name
    existing.start_time = session.start_time
    existing.end_time = session.end_time
    existing.is_active = session.is_active
    
    db.add(Log(
        level="INFO", 
        message=f"Updated session {existing.name} (Active: {existing.is_active})",
        details=json.dumps(session.model_dump(), default=str)
    ))
    
    db.commit()
    db.refresh(existing)
    return existing


@router.delete("/settings/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Delete a trading session."""
    session = db.query(TradingSession).filter(TradingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    return {"status": "deleted"}


# =============================================================================
# ACCOUNT SETTINGS
# =============================================================================

@router.get("/settings/accounts", response_model=List[AccountSettingsResponse])
def get_all_account_settings(db: Session = Depends(get_db)):
    """Get settings for all configured accounts."""
    return db.query(AccountSettings).all()


@router.get("/settings/accounts/{account_id}", response_model=AccountSettingsResponse)
def get_account_settings(account_id: int, db: Session = Depends(get_db)):
    """Get settings for a specific account."""
    settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Account settings not found")
    return settings


@router.post("/settings/accounts/{account_id}", response_model=AccountSettingsResponse)
def update_account_settings(account_id: int, req: AccountSettingsUpdate, db: Session = Depends(get_db)):
    """Create or update account settings."""
    settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
    
    if not settings:
        settings = AccountSettings(account_id=account_id)
        db.add(settings)
    
    if req.trading_enabled is not None:
        settings.trading_enabled = req.trading_enabled
    if req.risk_per_trade is not None and req.risk_per_trade != settings.risk_per_trade:
        old_val = settings.risk_per_trade
        settings.risk_per_trade = req.risk_per_trade
        db.add(Log(level="INFO", message=f"Risk per trade updated for account {account_id}: ${old_val} -> ${req.risk_per_trade}"))
    if req.account_name is not None:
        settings.account_name = req.account_name
    if req.max_contracts is not None and req.max_contracts != settings.max_contracts:
        old_val = settings.max_contracts or 50
        settings.max_contracts = req.max_contracts
        db.add(Log(level="INFO", message=f"Max contracts updated for account {account_id}: {old_val} -> {req.max_contracts}"))
    
    db.commit()
    db.refresh(settings)
    
    # Log toggle action
    if req.trading_enabled is not None:
        status = "ON" if req.trading_enabled else "OFF"
        db.add(Log(level="WARNING", message=f"Account {account_id} trading: {status}"))
        db.commit()
    
    return settings


# =============================================================================
# ACCOUNT STRATEGY CONFIGS
# =============================================================================

@router.get("/settings/accounts/{account_id}/strategies", response_model=List[AccountStrategyConfigResponse])
def get_account_strategy_configs(account_id: int, db: Session = Depends(get_db)):
    """Get all strategy configurations for an account."""
    configs = db.query(AccountStrategyConfig).filter(
        AccountStrategyConfig.account_id == account_id
    ).all()
    
    # Enrich with strategy info
    result = []
    for config in configs:
        strategy = db.query(Strategy).filter(Strategy.id == config.strategy_id).first()
        response = AccountStrategyConfigResponse(
            id=config.id,
            account_id=config.account_id,
            strategy_id=config.strategy_id,
            strategy_name=strategy.name if strategy else None,
            strategy_tv_id=strategy.tv_id if strategy else None,
            enabled=config.enabled,
            risk_factor=config.risk_factor,
            allowed_sessions=config.allowed_sessions,
            partial_tp_percent=config.partial_tp_percent,
            move_sl_to_entry=config.move_sl_to_entry,
            allow_outside_sessions=config.allow_outside_sessions,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        result.append(response)
    
    return result


@router.post("/settings/accounts/{account_id}/strategies", response_model=AccountStrategyConfigResponse)
def add_strategy_to_account(
    account_id: int, 
    config: AccountStrategyConfigCreate, 
    db: Session = Depends(get_db)
):
    """Add or update a strategy configuration for an account."""
    # Ensure account settings exist
    risk_engine = RiskEngine(db)
    risk_engine.ensure_account_settings(account_id)
    
    # Check strategy exists
    strategy = db.query(Strategy).filter(Strategy.id == config.strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Check for existing config
    existing = db.query(AccountStrategyConfig).filter(
        AccountStrategyConfig.account_id == account_id,
        AccountStrategyConfig.strategy_id == config.strategy_id
    ).first()
    
    if existing:
        existing.enabled = config.enabled
        existing.risk_factor = config.risk_factor
        existing.allowed_sessions = config.allowed_sessions
        existing.partial_tp_percent = config.partial_tp_percent
        existing.move_sl_to_entry = config.move_sl_to_entry
        existing.allow_outside_sessions = config.allow_outside_sessions
        db.commit()
        db.refresh(existing)
        
        # Log the update
        account_settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
        account_name = account_settings.account_name if account_settings and account_settings.account_name else f"Account #{account_id}"
        config_details = {
            "account_id": account_id,
            "strategy": strategy.name,
            "strategy_tv_id": strategy.tv_id,
            "enabled": config.enabled,
            "risk_factor": config.risk_factor,
            "allowed_sessions": config.allowed_sessions,
            "partial_tp_percent": config.partial_tp_percent,
            "move_sl_to_entry": config.move_sl_to_entry,
            "allow_outside_sessions": config.allow_outside_sessions
        }
        db.add(Log(
            level="INFO",
            message=f"Strategy Config Updated: {strategy.name} on {account_name} (sessions: {config.allowed_sessions}, factor: {config.risk_factor}x)",
            details=json.dumps(config_details)
        ))
        db.commit()
        
        return AccountStrategyConfigResponse(
            id=existing.id,
            account_id=existing.account_id,
            strategy_id=existing.strategy_id,
            strategy_name=strategy.name,
            strategy_tv_id=strategy.tv_id,
            enabled=existing.enabled,
            risk_factor=existing.risk_factor,
            allowed_sessions=existing.allowed_sessions,
            partial_tp_percent=existing.partial_tp_percent,
            move_sl_to_entry=existing.move_sl_to_entry,
            allow_outside_sessions=existing.allow_outside_sessions,
            created_at=existing.created_at,
            updated_at=existing.updated_at
        )
    
    new_config = AccountStrategyConfig(
        account_id=account_id,
        strategy_id=config.strategy_id,
        enabled=config.enabled,
        risk_factor=config.risk_factor,
        allowed_sessions=config.allowed_sessions,
        partial_tp_percent=config.partial_tp_percent,
        move_sl_to_entry=config.move_sl_to_entry,
        allow_outside_sessions=config.allow_outside_sessions,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    # Log the addition
    account_settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
    account_name = account_settings.account_name if account_settings and account_settings.account_name else f"Account #{account_id}"
    config_details = {
        "account_id": account_id,
        "strategy": strategy.name,
        "strategy_tv_id": strategy.tv_id,
        "enabled": config.enabled,
        "risk_factor": config.risk_factor,
        "allowed_sessions": config.allowed_sessions,
        "partial_tp_percent": config.partial_tp_percent,
        "move_sl_to_entry": config.move_sl_to_entry,
        "allow_outside_sessions": config.allow_outside_sessions
    }
    db.add(Log(
        level="INFO",
        message=f"Strategy Added to Account: {strategy.name} on {account_name} (sessions: {config.allowed_sessions})",
        details=json.dumps(config_details)
    ))
    db.commit()
    
    return AccountStrategyConfigResponse(
        id=new_config.id,
        account_id=new_config.account_id,
        strategy_id=new_config.strategy_id,
        strategy_name=strategy.name,
        strategy_tv_id=strategy.tv_id,
        enabled=new_config.enabled,
        risk_factor=new_config.risk_factor,
        allowed_sessions=new_config.allowed_sessions,
        partial_tp_percent=new_config.partial_tp_percent,
        move_sl_to_entry=new_config.move_sl_to_entry,
        allow_outside_sessions=new_config.allow_outside_sessions,
        created_at=new_config.created_at,
        updated_at=new_config.updated_at
    )


@router.get("/settings/contracts/available")
async def get_available_contracts():
    """Get all available contracts from TopStep."""
    contracts = await topstep_client.get_all_computable_contracts()
    return contracts


@router.delete("/settings/accounts/{account_id}/strategies/{strategy_id}")
def remove_strategy_from_account(account_id: int, strategy_id: int, db: Session = Depends(get_db)):
    """Remove a strategy configuration from an account."""
    config = db.query(AccountStrategyConfig).filter(
        AccountStrategyConfig.account_id == account_id,
        AccountStrategyConfig.strategy_id == strategy_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Strategy config not found")
    
    # Get strategy name for logging
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    strategy_name = strategy.name if strategy else str(strategy_id)
    account_settings = db.query(AccountSettings).filter(AccountSettings.account_id == account_id).first()
    account_name = account_settings.account_name if account_settings and account_settings.account_name else f"Account #{account_id}"
    
    db.delete(config)
    db.commit()
    
    # Log the removal
    removal_details = {
        "account_id": account_id,
        "strategy": strategy_name,
        "strategy_id": strategy_id
    }
    db.add(Log(
        level="WARNING",
        message=f"Strategy Removed from Account: {strategy_name} removed from {account_name}",
        details=json.dumps(removal_details)
    ))
    db.commit()
    
    return {"status": "deleted"}


# =============================================================================
# TOPSTEP ACCOUNTS
# =============================================================================

@router.get("/dashboard/accounts", response_model=List[AccountResponse])
async def get_accounts():
    """Get all accounts from TopStep API."""
    accounts = await topstep_client.get_accounts()
    return accounts


# =============================================================================
# TRADES & LOGS
# =============================================================================

@router.get("/dashboard/trades", response_model=List[TradeResponse])
def get_trades(
    account_id: Optional[int] = None,
    days: int = 1,
    status: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get trades from local database with optional filtering.
    
    Args:
        account_id: Filter by specific account
        days: Number of days to look back (1 = today, 7 = last week)
        status: Filter by status (OPEN, CLOSED, PENDING, REJECTED)
    """
    query = db.query(Trade)
    
    # Filter by account
    if account_id:
        query = query.filter(Trade.account_id == account_id)
    
    # Filter by status
    if status:
        query = query.filter(Trade.status == status)
    
    # Filter by date range
    if days > 0:
        import pytz
        from datetime import timedelta
        brussels_tz = pytz.timezone("Europe/Brussels")
        now_utc = datetime.now(timezone.utc)
        now_brussels = now_utc.astimezone(brussels_tz)
        
        # Get start of today in Brussels time
        today_start_brussels = now_brussels.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if days == 1:
            # Today: from midnight Brussels time
            start_date_brussels = today_start_brussels
        else:
            # Last N days (including today)
            # e.g. days=7 -> today + 6 previous days = start from 6 days ago midnight
            start_date_brussels = today_start_brussels - timedelta(days=days-1)
            
        # Convert back to UTC for DB comparison
        start_date = start_date_brussels.astimezone(timezone.utc)
        
        # Ensure correct type for comparison (offset-aware or naive depending on DB)
        # SQLite usually stores naive strings, but our models use DateTime(timezone=True) or similar?
        # Typically SQLAlchemy + SQLite with DateTime objects works best with naive or consistently aware.
        # If DB relies on naive UTC, we might need to strip tzinfo. 
        # But let's check if Trade.timestamp is aware.
        # Based on default=lambda: datetime.datetime.now(datetime.timezone.utc), it is aware (UTC).
        
        query = query.filter(Trade.timestamp >= start_date)
    
    trades = query.order_by(Trade.timestamp.desc()).offset(skip).limit(limit).all()
    return trades


@router.get("/dashboard/logs", response_model=List[LogResponse])
def get_logs(
    skip: int = 0, 
    limit: int = 100, 
    min_timestamp: Optional[datetime] = None, 
    db: Session = Depends(get_db)
):
    """Get system logs."""
    query = db.query(Log).order_by(Log.timestamp.desc())
    
    if min_timestamp:
        query = query.filter(Log.timestamp >= min_timestamp)
        if limit < 1000:
            limit = 1000
    
    logs = query.offset(skip).limit(limit).all()
    
    # Ensure timezone awareness
    for log in logs:
        if log.timestamp and log.timestamp.tzinfo is None:
            log.timestamp = log.timestamp.replace(tzinfo=timezone.utc)
    
    return logs


@router.get("/dashboard/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics."""
    return {
        "daily_pnl": 0.0,
        "active_trades": db.query(Trade).filter(Trade.status == "OPEN").count(),
    }


# =============================================================================
# POSITIONS & ORDERS (Per Account)
# =============================================================================

@router.get("/dashboard/positions/{account_id}", response_model=List[PositionResponse])
async def get_positions(account_id: int, db: Session = Depends(get_db)):
    """Get open positions for a specific account with unrealized PnL."""
    from backend.services.price_cache import price_cache
    from backend.services.risk_engine import calculate_unrealized_pnl
    
    positions = await topstep_client.get_open_positions(account_id)
    
    # Enrich positions with unrealized PnL
    enriched_positions = []
    
    for pos in positions:
        contract_id = pos.get("contractId")
        entry_price = pos.get("averagePrice", 0)
        quantity = pos.get("size", 0)
        is_long = pos.get("type") == 1
        
        # Get current price from cache
        current_price = price_cache.get_price(contract_id)
        
        unrealized_pnl = None
        if current_price and entry_price:
            # Get tick info from TickerMap
            ticker_map = db.query(TickerMap).filter(
                TickerMap.ts_contract_id == contract_id
            ).first()
            
            if ticker_map:
                unrealized_pnl = calculate_unrealized_pnl(
                    entry_price=entry_price,
                    current_price=current_price,
                    quantity=quantity,
                    is_long=is_long,
                    tick_size=ticker_map.tick_size,
                    tick_value=ticker_map.tick_value
                )
        
        enriched_positions.append({
            **pos,
            "currentPrice": current_price,
            "unrealizedPnl": unrealized_pnl
        })
    
    return enriched_positions


@router.get("/dashboard/orders/{account_id}", response_model=List[OrderResponse])
async def get_orders(account_id: int, days: int = 1):
    """Get orders for a specific account."""
    orders = await topstep_client.get_orders(account_id, days=days)
    return orders


@router.get("/dashboard/trades-history/{account_id}", response_model=List[HistoricalTradeResponse])
async def get_historical_trades(account_id: int, days: int = 1):
    """Get historical trades for a specific account."""
    trades = await topstep_client.get_historical_trades(account_id, days=days)
    return trades


# =============================================================================
# POSITION ACTIONS
# =============================================================================

@router.post("/dashboard/positions/{account_id}/close")
async def close_position(account_id: int, req: ClosePositionRequest, db: Session = Depends(get_db)):
    """Close a specific position."""
    db.add(Log(level="WARNING", message=f"Manual close: {req.contract_id} on account {account_id}"))
    db.commit()
    
    # Cancel associated orders
    try:
        orders = await topstep_client.get_orders(account_id, days=1)
        for order in orders:
            if order.get('status') in [1, 6]:  # Working/Pending
                o_contract = order.get('contractId', '')
                if str(o_contract) == str(req.contract_id):
                    oid = order.get('orderId') or order.get('id')
                    if oid:
                        await topstep_client.cancel_order(account_id, oid)
    except Exception as e:
        print(f"Auto-cancel failed: {e}")
    
    success = await topstep_client.close_position(account_id, req.contract_id)
    return {"success": success}


@router.post("/dashboard/account/{account_id}/flatten")
async def flatten_account(account_id: int, db: Session = Depends(get_db)):
    """Flatten a specific account (close all positions, cancel all orders)."""
    db.add(Log(level="WARNING", message=f"Manual flatten for account {account_id}"))
    db.commit()
    
    # Cancel all orders
    orders = await topstep_client.get_orders(account_id)
    for order in orders:
        if order.get('status') in [1, 6]:
            await topstep_client.cancel_order(account_id, order.get('id'))
    
    # Close all positions
    positions = await topstep_client.get_open_positions(account_id)
    for pos in positions:
        await topstep_client.close_position(account_id, pos.get('contractId'))
    
    return {"success": True}


@router.post("/dashboard/flatten-all")
async def flatten_all_accounts(db: Session = Depends(get_db)):
    """
    FORCE FLATTEN ALL ACCOUNTS.
    Ignores trading_enabled settings - this is a safety mechanism.
    """
    db.add(Log(level="WARNING", message="FORCE FLATTEN ALL ACCOUNTS triggered"))
    db.commit()
    
    accounts = await topstep_client.get_accounts()
    results = {}
    
    for account in accounts:
        account_id = account.get('id')
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
            
            results[account_id] = "flattened"
        except Exception as e:
            results[account_id] = f"error: {e}"
    
    return {"success": True, "results": results}


# =============================================================================
# AUTH
# =============================================================================

@router.post("/dashboard/logout")
async def logout(db: Session = Depends(get_db)):
    """Disconnect from TopStep."""
    await topstep_client.logout()
    db.add(Log(level="INFO", message="User disconnected"))
    db.commit()
    return {"success": True}


# =============================================================================
# TICKER MAPPINGS (Global)
# =============================================================================

@router.get("/settings/ticker-map")
def get_ticker_maps(db: Session = Depends(get_db)):
    """Get all ticker mappings."""
    maps = db.query(TickerMap).all()
    data = [TickerMapResponse.model_validate(m).model_dump() for m in maps]
    return {"success": True, "data": data}


@router.post("/settings/ticker-map")
def create_ticker_map(map_in: TickerMapCreate, db: Session = Depends(get_db)):
    """Create a ticker mapping."""
    existing = db.query(TickerMap).filter(TickerMap.tv_ticker == map_in.tv_ticker).first()
    if existing:
        return {"success": False, "message": "Mapping already exists"}
    
    new_map = TickerMap(**map_in.model_dump())
    db.add(new_map)
    db.commit()
    db.refresh(new_map)
    return {"success": True, "data": new_map}


@router.delete("/settings/ticker-map/{map_id}")
def delete_ticker_map(map_id: int, db: Session = Depends(get_db)):
    """Delete a ticker mapping."""
    mapping = db.query(TickerMap).filter(TickerMap.id == map_id).first()
    if not mapping:
        return {"success": False, "message": "Mapping not found"}
    
    db.delete(mapping)
    db.commit()
    return {"success": True}


@router.patch("/settings/ticker-map/{map_id}")
def update_ticker_map(map_id: int, updates: dict, db: Session = Depends(get_db)):
    """Update a ticker mapping (e.g., micro_equivalent)."""
    mapping = db.query(TickerMap).filter(TickerMap.id == map_id).first()
    if not mapping:
        return {"success": False, "message": "Mapping not found"}
    
    if "micro_equivalent" in updates:
        old_val = mapping.micro_equivalent or 1
        new_val = updates["micro_equivalent"]
        mapping.micro_equivalent = new_val
        db.add(Log(level="INFO", message=f"Ticker {mapping.tv_ticker} micro_equivalent updated: {old_val} -> {new_val}"))
    
    db.commit()
    db.refresh(mapping)
    return {"success": True, "data": TickerMapResponse.model_validate(mapping).model_dump()}


# =============================================================================
# TRADE RECONCILIATION
# =============================================================================

@router.post("/dashboard/reconcile/{account_id}/preview")
async def reconcile_preview(account_id: int, db: Session = Depends(get_db)):
    """
    Preview proposed reconciliation changes (dry-run).
    Compares local DB trades with TopStep API data.
    Returns proposed changes WITHOUT applying them.
    """
    db.add(Log(level="INFO", message=f"Reconciliation preview requested for account {account_id}"))
    db.commit()
    
    result = await preview_reconciliation(account_id, db)
    return result


@router.post("/dashboard/reconcile/{account_id}/apply")
async def reconcile_apply(account_id: int, changes: List[dict], db: Session = Depends(get_db)):
    """
    Apply reconciliation changes after user confirmation.
    Expects the list of proposed_changes from the preview endpoint.
    """
    if not changes:
        return {"success": True, "applied": {"closed": 0, "pnl_updated": 0}, "message": "No changes to apply"}
    
    result = await apply_reconciliation(account_id, changes, db)
    return result


# =============================================================================
# DISCORD NOTIFICATION SETTINGS
# =============================================================================

@router.get("/settings/discord/{account_id}", response_model=DiscordNotificationSettingsResponse)
def get_discord_settings(account_id: int, db: Session = Depends(get_db)):
    """Get Discord notification settings for a specific account."""
    settings = db.query(DiscordNotificationSettings).filter(
        DiscordNotificationSettings.account_id == account_id
    ).first()
    
    if not settings:
        # Return default settings (not saved yet)
        from datetime import datetime, timezone
        return DiscordNotificationSettingsResponse(
            id=0,
            account_id=account_id,
            enabled=False,
            webhook_url=None,
            notify_position_open=True,
            notify_position_close=True,
            notify_daily_summary=False,
            daily_summary_time="21:00",
            created_at=datetime.now(timezone.utc),
            updated_at=None
        )
    
    return settings


@router.post("/settings/discord/{account_id}", response_model=DiscordNotificationSettingsResponse)
def update_discord_settings(
    account_id: int, 
    req: DiscordNotificationSettingsUpdate, 
    db: Session = Depends(get_db)
):
    """Create or update Discord notification settings for an account."""
    settings = db.query(DiscordNotificationSettings).filter(
        DiscordNotificationSettings.account_id == account_id
    ).first()
    
    if not settings:
        settings = DiscordNotificationSettings(account_id=account_id)
        db.add(settings)
    
    # Update fields if provided
    if req.enabled is not None:
        settings.enabled = req.enabled
    if req.webhook_url is not None:
        settings.webhook_url = req.webhook_url
    if req.notify_position_open is not None:
        settings.notify_position_open = req.notify_position_open
    if req.notify_position_close is not None:
        settings.notify_position_close = req.notify_position_close
    if req.notify_daily_summary is not None:
        settings.notify_daily_summary = req.notify_daily_summary
    if req.daily_summary_time is not None:
        settings.daily_summary_time = req.daily_summary_time
    
    db.commit()
    db.refresh(settings)
    
    # Log the update
    status = "enabled" if settings.enabled else "disabled"
    db.add(Log(
        level="INFO", 
        message=f"Discord notifications {status} for account {account_id}",
        details=json.dumps(req.model_dump(exclude_none=True))
    ))
    db.commit()
    
    return settings

