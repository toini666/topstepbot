export interface Trade {
    id: number;
    ticker: string;
    action: string;
    entry_price: number;
    sl: number;
    tp: number;
    quantity: number;
    status: string;
    pnl?: number;
    timestamp: string;
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
    balance: number;
    simulated: boolean;
}

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
}

export interface TimeBlock {
    start: string;
    end: string;
}

export interface Config {
    risk_per_trade: number;
    blocked_periods_enabled: boolean;
    blocked_periods: TimeBlock[];
    auto_flatten_enabled: boolean;
    auto_flatten_time: string;
}

export interface TickerMap {
    id: number;
    tv_ticker: string;
    ts_contract_id: string;
    ts_ticker: string;
    tick_size: number;
    tick_value: number;
}

export interface Strategy {
    id: number;
    name: string;
    tv_id: string;
    risk_factor: number;
    created_at: string;
}
