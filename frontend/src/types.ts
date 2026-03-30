// =============================================================================
// BASIC TYPES
// =============================================================================

export interface Trade {
    id: number;
    account_id?: number;
    ticker: string;
    action: string;
    entry_price: number;
    exit_price?: number;  // Exit price for closed trades
    sl: number;
    tp: number;
    quantity: number;
    status: string;
    pnl?: number;
    fees?: number;  // Trading fees
    timeframe?: string;
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
    currentPrice?: number;     // Current market price
    unrealizedPnl?: number;    // Floating PnL
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

export interface NewsBlock {
    start: string;       // HH:MM
    end: string;         // HH:MM
    event: string;       // Event name
    country: string;     // USD, EUR, etc.
    impact: string;      // High, Medium, Low
}

export interface GlobalConfig {
    timezone: string;
    blocked_periods_enabled: boolean;
    blocked_periods: TimeBlock[];
    auto_flatten_enabled: boolean;
    auto_flatten_time: string;
    market_open_time: string;
    market_close_time: string;
    weekend_markets_open: boolean;  // Are markets open on weekends?
    trading_days: string[];  // ['MON', 'TUE', 'WED', 'THU', 'FRI'] - user preference
    enforce_single_position_per_asset: boolean;
    block_cross_account_opposite: boolean;

    // News Block Settings
    news_block_enabled: boolean;
    news_block_before_minutes: number;
    news_block_after_minutes: number;

    // Position Action on Blocked Hours
    blocked_hours_position_action: 'NOTHING' | 'BREAKEVEN' | 'FLATTEN';
    position_action_buffer_minutes: number;
    api_timeout_seconds: number;
    job_interval_seconds: number;
    websocket_disabled: boolean;
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
    max_contracts: number;  // Max micro-equivalent contracts
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
    default_allow_outside_sessions: boolean;
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
    allow_outside_sessions: boolean;
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
    micro_equivalent: number;  // 1 for micro, 10 for mini
}

// =============================================================================
// MARKET STATUS
// =============================================================================

export interface MarketStatus {
    is_open: boolean;              // Is the market actually open (hours + weekend_markets_open)
    reason: string;                // Reason for market status
    is_trading_allowed: boolean;   // Is trading allowed (trading_days + blocked periods)
    trading_reason: string;        // Reason if trading is blocked
    current_session?: string;
}

// =============================================================================
// DISCORD NOTIFICATION SETTINGS
// =============================================================================

export interface DiscordNotificationSettings {
    id?: number;
    account_id: number;
    enabled: boolean;
    webhook_url: string;
    notify_position_open: boolean;
    notify_position_close: boolean;
    notify_daily_summary: boolean;
    daily_summary_time: string;
    created_at?: string;
    updated_at?: string;
}

// =============================================================================
// SETUP WIZARD
// =============================================================================

export interface SetupStatus {
  configured: boolean;
  details: {
    topstep: boolean;
    telegram: boolean;
    heartbeat: boolean;
  };
}

export interface SetupConfig {
  TOPSTEP_USERNAME: string;
  TOPSTEP_APIKEY: string;
  TELEGRAM_BOT_TOKEN?: string;
  TELEGRAM_ID?: string;
  HEARTBEAT_WEBHOOK_URL?: string;
  HEARTBEAT_INTERVAL_SECONDS?: string;
  HEARTBEAT_AUTH_TOKEN?: string;
  USER_TIMEZONE?: string;
}

// =============================================================================
// LEGACY COMPATIBILITY (Config alias)
// =============================================================================

/** @deprecated Use GlobalConfig instead */
export type Config = GlobalConfig;

