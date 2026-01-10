from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- Webhook Schemas ---
class TradingViewAlert(BaseModel):
    ticker: str
    type: str  # SETUP / SIGNAL
    direction: str  # LONG/SHORT or BUY/SELL
    entry: float
    stop: float
    tp: float
    strat: Optional[str] = "default" # Strategy Name

# --- Strategy Schemas ---
class StrategyBase(BaseModel):
    name: str
    tv_id: str
    risk_factor: float = 1.0

class StrategyCreate(StrategyBase):
    pass

class StrategyResponse(StrategyBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# --- Trade Schemas ---
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
    sl: Optional[float]
    tp: Optional[float]
    pnl: Optional[float]
    timestamp: datetime
    rejection_reason: Optional[str] = None
    strategy: Optional[str] = "default"
    topstep_order_id: Optional[str] = None

    class Config:
        from_attributes = True

# --- Log Schemas ---
class LogResponse(BaseModel):
    id: int
    level: str
    message: str
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

# --- Settings Schemas ---
class TimeBlock(BaseModel):
    start: str # HH:MM
    end: str   # HH:MM

class RiskSettings(BaseModel):
    risk_per_trade: float = 200.0
    trading_enabled: bool = True
    blocked_periods_enabled: bool = True
    blocked_periods: List[TimeBlock] = [
        TimeBlock(start="08:55", end="09:15"),
        TimeBlock(start="15:25", end="15:45"),
        TimeBlock(start="21:30", end="00:15")
    ]
    auto_flatten_enabled: bool = False
    auto_flatten_time: str = "21:55"

class PositionResponse(BaseModel):
    id: int
    accountId: int
    contractId: str
    creationTimestamp: datetime
    type: int # 1=Long, 2=Short
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
    time_in_force: Optional[str] = "DAY" # Placeholder if not in API but good to have

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

class ClosePositionRequest(BaseModel):
    contract_id: str

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

class AccountResponse(BaseModel):
    id: int
    name: str
    canTrade: bool
    isVisible: bool
    balance: float
    simulated: bool

class AccountSelectRequest(BaseModel):
    account_id: int

class SettingsRequest(BaseModel):
    trading_enabled: bool

# --- Configuration Schemas ---
class ConfigResponse(BaseModel):
    risk_per_trade: float
    blocked_periods_enabled: bool
    blocked_periods: List[TimeBlock]
    auto_flatten_enabled: bool
    auto_flatten_time: str

class UpdateConfigRequest(BaseModel):
    risk_per_trade: Optional[float] = None
    blocked_periods_enabled: Optional[bool] = None
    blocked_periods: Optional[List[TimeBlock]] = None
    auto_flatten_enabled: Optional[bool] = None
    auto_flatten_time: Optional[str] = None

# --- Ticker Mapping Schemas ---
class TickerMapBase(BaseModel):
    tv_ticker: str
    ts_contract_id: str
    ts_ticker: str
    tick_size: float
    tick_value: float

class TickerMapCreate(TickerMapBase):
    pass

class TickerMapResponse(TickerMapBase):
    id: int

    class Config:
        from_attributes = True
