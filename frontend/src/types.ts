// =============================================================================
// BASIC TYPES
// =============================================================================

export interface Trade {
    id: number;
    account_id?: number;
    ticker: string;
    action: string;
    entry_price: number;
    sl: number;
    tp: number;
    quantity: number;
    status: string;
    pnl?: number;
    timeframe?: string;  // NEW
    timestamp: string;
    exit_time?: string;
    rejection_reason?: string;
    strategy?: string;
    topstep_order_id?: string;
}

export interface Log {
    id: number;
    level: string;
    message: string;
    details?: string;
    timestamp: string;
}

export interface Account {
    id: number;
    name: string;
    canTrade: boolean;
    isVisible: boolean;
    balance: number;
    simulated: boolean;
}

// =============================================================================
// TOPSTEP API TYPES
// =============================================================================

export interface Position {
    id: number;
    accountId: number;
    contractId: string;
    creationTimestamp: string;
    type: number; // 1=Long, 2=Short
    size: number;
    averagePrice: number;
}

export interface Order {
    id: number;
    accountId: number;
    contractId: string;
    symbolId: string;
    creationTimestamp: string;
    status: number;
    type: number;
    side: number;
    size: number;
    limitPrice?: number;
    stopPrice?: number;
    filledPrice?: number;
    timeInForce?: string;
}

export interface HistoricalTrade {
    id: number;
    accountId: number;
    contractId: string;
    creationTimestamp: string;
    price: number;
    profitAndLoss?: number;
    fees?: number;
    side: number;
    size: number;
    voided: boolean;
    orderId: number;
    strategy?: string;
    timeframe?: string;  // NEW: timeframe from Trade record
}

export interface AggregatedTrade {
    id: number;
    symbol: string;
    side: 'LONG' | 'SHORT';
    size: number;
    entryTime: string;
    exitTime: string;
    entryPrice: number;
    exitPrice: number;
    pnl: number;
    fees: number;
    strategy?: string;
    timeframe?: string;  // NEW
}

// =============================================================================
// SETTINGS TYPES
// =============================================================================

export interface TimeBlock {
    start: string;
    end: string;
    enabled: boolean;
}

export interface GlobalConfig {
    blocked_periods_enabled: boolean;
    blocked_periods: TimeBlock[];
    auto_flatten_enabled: boolean;
    auto_flatten_time: string;
    market_open_time: string;
    market_close_time: string;
}

// =============================================================================
// TRADING SESSIONS
// =============================================================================

export interface TradingSession {
    id: number;
    name: string;
    display_name: string;
    start_time: string;
    end_time: string;
    is_active: boolean;
}

// =============================================================================
// ACCOUNT SETTINGS
// =============================================================================

export interface AccountSettings {
    id: number;
    account_id: number;
    account_name?: string;
    trading_enabled: boolean;
    risk_per_trade: number;
    created_at: string;
    updated_at?: string;
}

// =============================================================================
// STRATEGY TYPES
// =============================================================================

export interface Strategy {
    id: number;
    name: string;
    tv_id: string;
    default_risk_factor: number;
    default_allowed_sessions: string;
    default_partial_tp_percent: number;
    default_move_sl_to_entry: boolean;
    created_at: string;
}

export interface AccountStrategyConfig {
    id: number;
    account_id: number;
    strategy_id: number;
    strategy_name?: string;
    strategy_tv_id?: string;
    enabled: boolean;
    risk_factor: number;
    allowed_sessions: string;
    partial_tp_percent: number;
    move_sl_to_entry: boolean;
    created_at: string;
    updated_at?: string;
}

// =============================================================================
// TICKER MAPPING
// =============================================================================

export interface TickerMap {
    id: number;
    tv_ticker: string;
    ts_contract_id: string;
    ts_ticker: string;
    tick_size: number;
    tick_value: number;
}

// =============================================================================
// MARKET STATUS
// =============================================================================

export interface MarketStatus {
    is_open: boolean;
    reason: string;
    current_session?: string;
}

// =============================================================================
// LEGACY COMPATIBILITY (Config alias)
// =============================================================================

/** @deprecated Use GlobalConfig instead */
export type Config = GlobalConfig;
