from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# =============================================================================
# WEBHOOK SCHEMAS
# =============================================================================

class TradingViewAlert(BaseModel):
    """Alert payload from TradingView webhooks."""
    ticker: str
    type: str  # SETUP, SIGNAL, PARTIAL, CLOSE
    side: str  # BUY, SELL (renamed from 'direction')
    entry: float
    stop: Optional[float] = None  # Optional for PARTIAL/CLOSE
    tp: Optional[float] = None  # Optional for PARTIAL/CLOSE
    strat: Optional[str] = "default"  # Strategy identifier
    timeframe: str  # Required: M1, M5, M15, H1, H4, D1, etc.


# =============================================================================
# TRADING SESSION SCHEMAS
# =============================================================================

class TradingSessionBase(BaseModel):
    name: str
    display_name: str
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    is_active: bool = True


class TradingSessionCreate(TradingSessionBase):
    pass


class TradingSessionResponse(TradingSessionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# STRATEGY SCHEMAS (Global templates)
# =============================================================================

class StrategyBase(BaseModel):
    name: str
    tv_id: str
    default_risk_factor: float = 1.0
    default_allowed_sessions: str = "ASIA,UK,US"
    default_partial_tp_percent: float = 50.0
    default_move_sl_to_entry: bool = True
    default_allow_outside_sessions: bool = False


class StrategyCreate(StrategyBase):
    pass


class StrategyResponse(StrategyBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# ACCOUNT SETTINGS SCHEMAS
# =============================================================================

class AccountSettingsBase(BaseModel):
    account_id: int
    account_name: Optional[str] = None
    trading_enabled: bool = True
    risk_per_trade: float = 200.0
    max_contracts: int = 50  # Max micro-equivalent contracts


class AccountSettingsCreate(AccountSettingsBase):
    pass


class AccountSettingsUpdate(BaseModel):
    trading_enabled: Optional[bool] = None
    risk_per_trade: Optional[float] = None
    account_name: Optional[str] = None
    max_contracts: Optional[int] = None


class AccountSettingsResponse(AccountSettingsBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# ACCOUNT STRATEGY CONFIG SCHEMAS
# =============================================================================

class AccountStrategyConfigBase(BaseModel):
    strategy_id: int
    enabled: bool = True
    risk_factor: float = 1.0
    allowed_sessions: str = "ASIA,UK,US"
    partial_tp_percent: float = 50.0
    move_sl_to_entry: bool = True
    allow_outside_sessions: bool = False


class AccountStrategyConfigCreate(AccountStrategyConfigBase):
    pass


class AccountStrategyConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    risk_factor: Optional[float] = None
    allowed_sessions: Optional[str] = None
    partial_tp_percent: Optional[float] = None
    move_sl_to_entry: Optional[bool] = None
    allow_outside_sessions: Optional[bool] = None


class AccountStrategyConfigResponse(AccountStrategyConfigBase):
    id: int
    account_id: int
    strategy_name: Optional[str] = None  # Populated from join
    strategy_tv_id: Optional[str] = None  # Populated from join
    allow_outside_sessions: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# TRADE SCHEMAS
# =============================================================================

class TradeBase(BaseModel):
    ticker: str
    action: str
    entry_price: float
    quantity: int
    status: str


class TradeCreate(TradeBase):
    pass


class TradeResponse(TradeBase):
    id: int
    account_id: Optional[int] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    pnl: Optional[float] = None
    fees: Optional[float] = None  # Trading fees
    exit_price: Optional[float] = None  # Exit price for closed trades
    timeframe: Optional[str] = None
    timestamp: datetime
    exit_time: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    strategy: Optional[str] = "default"
    topstep_order_id: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# LOG SCHEMAS
# =============================================================================

class LogResponse(BaseModel):
    id: int
    level: str
    message: str
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# =============================================================================
# GLOBAL SETTINGS SCHEMAS
# =============================================================================

class TimeBlock(BaseModel):
    start: str  # HH:MM
    end: str  # HH:MM
    enabled: bool = True


class GlobalSettingsResponse(BaseModel):
    """All global settings combined."""
    blocked_periods_enabled: bool = True
    blocked_periods: List[TimeBlock] = []
    auto_flatten_enabled: bool = False
    auto_flatten_time: str = "21:55"
    market_open_time: str = "00:00"
    market_close_time: str = "22:00"
    weekend_markets_open: bool = False  # Are markets open on weekends?
    trading_days: List[str] = ["MON", "TUE", "WED", "THU", "FRI"]
    enforce_single_position_per_asset: bool = True
    block_cross_account_opposite: bool = True


class GlobalSettingsUpdate(BaseModel):
    blocked_periods_enabled: Optional[bool] = None
    blocked_periods: Optional[List[TimeBlock]] = None
    auto_flatten_enabled: Optional[bool] = None
    auto_flatten_time: Optional[str] = None
    market_open_time: Optional[str] = None
    market_close_time: Optional[str] = None
    weekend_markets_open: Optional[bool] = None  # Are markets open on weekends?
    trading_days: Optional[List[str]] = None
    enforce_single_position_per_asset: Optional[bool] = None
    block_cross_account_opposite: Optional[bool] = None


# =============================================================================
# TOPSTEP API RESPONSE SCHEMAS
# =============================================================================

class PositionResponse(BaseModel):
    id: int
    accountId: int
    contractId: str
    creationTimestamp: datetime
    type: int  # 1=Long, 2=Short
    size: int
    averagePrice: float


class OrderResponse(BaseModel):
    id: int
    accountId: int
    contractId: str
    symbolId: str
    creationTimestamp: datetime
    status: int
    type: int
    side: int
    size: int
    limitPrice: Optional[float] = None
    stopPrice: Optional[float] = None
    filledPrice: Optional[float] = None


class HistoricalTradeResponse(BaseModel):
    id: int
    accountId: int
    contractId: str
    creationTimestamp: datetime
    price: float
    profitAndLoss: Optional[float] = None
    fees: Optional[float] = None
    side: int
    size: int
    voided: bool
    orderId: int


class AccountResponse(BaseModel):
    id: int
    name: str
    canTrade: bool
    isVisible: bool
    balance: float
    simulated: bool


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class ClosePositionRequest(BaseModel):
    contract_id: str


class SettingsToggleRequest(BaseModel):
    trading_enabled: bool


# =============================================================================
# TICKER MAPPING SCHEMAS
# =============================================================================

class TickerMapBase(BaseModel):
    tv_ticker: str
    ts_contract_id: str
    ts_ticker: str
    tick_size: float
    tick_value: float
    micro_equivalent: int = 1  # 1 for micro, 10 for mini


class TickerMapCreate(TickerMapBase):
    pass


class TickerMapResponse(TickerMapBase):
    id: int

    class Config:
        from_attributes = True
