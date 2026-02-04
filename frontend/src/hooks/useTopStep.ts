import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import type {
    Trade, Log, Account, Position, Order, HistoricalTrade,
    GlobalConfig, MarketStatus, AccountSettings, TradingSession, Strategy
} from '../types';
import { API_BASE } from '../config';

/**
 * Main hook for TopStep Trading Bot.
 * Handles multi-account data fetching and settings management.
 */
export const useTopStep = () => {
    // Core Data
    const [trades, setTrades] = useState<Trade[]>([]);
    const [logs, setLogs] = useState<Log[]>([]);
    const [stats, setStats] = useState({ daily_pnl: 0, active_trades: 0 });

    // TopStep Connection
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [loading, setLoading] = useState(true);

    // Per-Account Data (indexed by account_id)
    const [positionsByAccount, setPositionsByAccount] = useState<Record<number, Position[]>>({});
    const [ordersByAccount, setOrdersByAccount] = useState<Record<number, Order[]>>({});
    const [tradesByAccount, setTradesByAccount] = useState<Record<number, HistoricalTrade[]>>({});

    // Settings
    const [globalConfig, setGlobalConfig] = useState<GlobalConfig>({
        blocked_periods_enabled: true,
        blocked_periods: [],
        auto_flatten_enabled: false,
        auto_flatten_time: "21:55",
        market_open_time: "00:00",
        market_close_time: "22:00",
        weekend_markets_open: false,
        trading_days: ['MON', 'TUE', 'WED', 'THU', 'FRI'],
        enforce_single_position_per_asset: true,
        block_cross_account_opposite: true,
        news_block_enabled: false,
        news_block_before_minutes: 15,
        news_block_after_minutes: 15,
        blocked_hours_position_action: 'NOTHING',
        position_action_buffer_minutes: 5
    });
    const [accountSettings, setAccountSettings] = useState<Record<number, AccountSettings>>({});
    const [tradingSessions, setTradingSessions] = useState<TradingSession[]>([]);
    const [strategies, setStrategies] = useState<Strategy[]>([]);
    const [marketStatus, setMarketStatus] = useState<MarketStatus>({
        is_open: false,
        reason: 'Connecting...',
        is_trading_allowed: false,
        trading_reason: 'Connecting...'
    });

    // UI State
    const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
    const [historyFilter, setHistoryFilter] = useState<'today' | 'week'>('today');
    const [logParams, setLogParams] = useState<{ min_timestamp: string | null; limit: number }>({
        min_timestamp: new Date(new Date().setHours(0, 0, 0, 0)).toISOString(),
        limit: 1000
    });

    // ==========================================================================
    // DATA FETCHING
    // ==========================================================================

    const fetchData = useCallback(async () => {
        try {
            // 1. Fetch Basic Data (always)
            const [tradesRes, logsRes, statsRes, statusRes, configRes, marketRes, sessionsRes, strategiesRes] = await Promise.all([
                axios.get(`${API_BASE}/dashboard/trades`),
                axios.get(`${API_BASE}/dashboard/logs`, {
                    params: { limit: logParams.limit, min_timestamp: logParams.min_timestamp }
                }),
                axios.get(`${API_BASE}/dashboard/stats`),
                axios.get(`${API_BASE}/dashboard/status`),
                axios.get(`${API_BASE}/dashboard/config`),
                axios.get(`${API_BASE}/dashboard/market-status`),
                axios.get(`${API_BASE}/settings/sessions`),
                axios.get(`${API_BASE}/strategies`)
            ]);

            setTrades(tradesRes.data);
            setLogs(logsRes.data);
            setStats(statsRes.data);
            if (configRes.data) setGlobalConfig(configRes.data);
            if (marketRes.data) setMarketStatus(marketRes.data);
            if (sessionsRes.data) setTradingSessions(sessionsRes.data);
            if (strategiesRes.data) setStrategies(strategiesRes.data);

            // 2. Check Connection Status
            const currentlyConnected = statusRes.data.connected;
            if (currentlyConnected !== isConnected) {
                setIsConnected(currentlyConnected);
            }

            // 3. Fetch TopStep Data if Connected
            if (currentlyConnected) {
                try {
                    const accountsRes = await axios.get(`${API_BASE}/dashboard/accounts`);
                    setAccounts(accountsRes.data);

                    // Fetch account settings
                    const settingsRes = await axios.get(`${API_BASE}/settings/accounts`);
                    const settingsMap: Record<number, AccountSettings> = {};
                    for (const s of settingsRes.data) {
                        settingsMap[s.account_id] = s;
                    }
                    setAccountSettings(settingsMap);

                    // Auto-select first account if none selected
                    if (!selectedAccountId && accountsRes.data.length > 0) {
                        setSelectedAccountId(accountsRes.data[0].id);
                    }

                    // Fetch per-account data for ALL accounts
                    const days = historyFilter === 'today' ? 1 : 7;
                    const newPositions: Record<number, Position[]> = {};
                    const newOrders: Record<number, Order[]> = {};
                    const newTrades: Record<number, HistoricalTrade[]> = {};

                    for (const account of accountsRes.data) {
                        const aid = account.id;
                        try {
                            const [posRes, ordRes, histRes] = await Promise.all([
                                axios.get(`${API_BASE}/dashboard/positions/${aid}`),
                                axios.get(`${API_BASE}/dashboard/orders/${aid}`, { params: { days } }),
                                // Use internal Trade table instead of TopStep API for aggregated view
                                axios.get(`${API_BASE}/dashboard/trades`, { params: { account_id: aid, days, status: 'CLOSED' } })
                            ]);
                            newPositions[aid] = posRes.data;
                            newOrders[aid] = ordRes.data;
                            // Map Trade format to HistoricalTrade-like format for display
                            // Helper to ensure timestamps are parsed as UTC
                            const parseUtcTimestamp = (ts: string | null | undefined): string | null => {
                                if (!ts) return null;
                                // If timestamp doesn't end with Z and doesn't contain timezone info, add Z
                                const tsStr = String(ts);
                                if (!tsStr.endsWith('Z') && !tsStr.includes('+')) {
                                    return tsStr.replace(' ', 'T') + 'Z';
                                }
                                return tsStr.replace(' ', 'T');
                            };

                            newTrades[aid] = histRes.data.map((t: Trade) => ({
                                id: t.id,
                                accountId: t.account_id || aid,
                                contractId: t.ticker,
                                creationTimestamp: parseUtcTimestamp(t.timestamp),
                                price: t.entry_price,
                                exitPrice: t.exit_price,
                                exitTime: parseUtcTimestamp(t.exit_time),
                                profitAndLoss: t.pnl,
                                fees: t.fees,
                                side: t.action === 'BUY' ? 0 : 1,
                                size: t.quantity,
                                strategy: t.strategy,
                                timeframe: t.timeframe,
                                // These fields help avoid needing aggregateTrades()
                                entryPrice: t.entry_price,
                                isAggregated: true
                            }))
                        } catch (e) {
                            console.warn(`Error fetching data for account ${aid}:`, e);
                            newPositions[aid] = [];
                            newOrders[aid] = [];
                            newTrades[aid] = [];
                        }
                    }

                    setPositionsByAccount(newPositions);
                    setOrdersByAccount(newOrders);
                    setTradesByAccount(newTrades);

                } catch (e) {
                    console.warn("Error fetching accounts:", e);
                }
            } else {
                setAccounts([]);
                setPositionsByAccount({});
                setOrdersByAccount({});
                setTradesByAccount({});
            }

        } catch (error) {
            console.error("Failed to fetch dashboard data:", error);
        } finally {
            setLoading(false);
        }
    }, [isConnected, selectedAccountId, logParams, historyFilter]);

    // ==========================================================================
    // ACTIONS
    // ==========================================================================

    const loadMoreLogs = () => {
        setLogParams({
            min_timestamp: null,
            limit: logs.length + 50
        });
    };

    const updateGlobalConfig = async (newConfig: Partial<GlobalConfig>) => {
        try {
            await axios.post(`${API_BASE}/dashboard/config`, newConfig);
            toast.success("Settings Saved Successfully");
            fetchData();
        } catch (error) {
            console.error("Failed to update config:", error);
            toast.error("Failed to save settings");
        }
    };

    const updateAccountSettings = async (accountId: number, updates: Partial<AccountSettings>) => {
        try {
            await axios.post(`${API_BASE}/settings/accounts/${accountId}`, updates);
            toast.success("Account Settings Updated");
            fetchData();
        } catch (error) {
            console.error("Failed to update account settings:", error);
            toast.error("Failed to update account settings");
        }
    };

    const toggleAccountTrading = async (accountId: number) => {
        const current = accountSettings[accountId];
        const newState = current ? !current.trading_enabled : false;
        await updateAccountSettings(accountId, { trading_enabled: newState });
    };

    const connect = async () => {
        setLoading(true);
        try {
            const accountsRes = await axios.get(`${API_BASE}/dashboard/accounts`);
            if (accountsRes.data && accountsRes.data.length > 0) {
                setAccounts(accountsRes.data);
                setIsConnected(true);
                setSelectedAccountId(accountsRes.data[0].id);
                toast.success("Connected to TopStep Successfully");
            } else {
                toast.error("Connected but no accounts found");
                setIsConnected(false);
            }
        } catch (e) {
            console.error("Connection Failed", e);
            toast.error("Failed to connect to TopStep");
        } finally {
            setLoading(false);
        }
    };

    const logout = async () => {
        try {
            await axios.post(`${API_BASE}/dashboard/logout`);
            setIsConnected(false);
            setAccounts([]);
            setPositionsByAccount({});
            setOrdersByAccount({});
            setTradesByAccount({});
            setSelectedAccountId(null);
            toast.success("Disconnected Successfully");
        } catch (error) {
            console.error("Failed to logout", error);
            toast.error("Failed to disconnect");
        }
    };

    const closePosition = async (accountId: number, contractId: string) => {
        try {
            await axios.post(`${API_BASE}/dashboard/positions/${accountId}/close`, { contract_id: contractId });
            toast.success("Position Closed");
            fetchData();
        } catch (error) {
            console.error("Failed to close position:", error);
            toast.error("Failed to close position");
        }
    };

    const flattenAccount = async (accountId: number) => {
        try {
            await axios.post(`${API_BASE}/dashboard/account/${accountId}/flatten`);
            toast.success("Account Flattened");
            fetchData();
        } catch (error) {
            console.error("Failed to flatten account:", error);
            toast.error("Failed to flatten account");
        }
    };

    const flattenAllAccounts = async () => {
        try {
            await axios.post(`${API_BASE}/dashboard/flatten-all`);
            toast.success("All Accounts Flattened");
            fetchData();
        } catch (error) {
            console.error("Failed to flatten all accounts:", error);
            toast.error("Failed to flatten all accounts");
        }
    };

    const previewReconciliation = async (accountId: number) => {
        try {
            const res = await axios.post(`${API_BASE}/dashboard/reconcile/${accountId}/preview`);
            return res.data;
        } catch (error) {
            console.error("Failed to preview reconciliation:", error);
            toast.error("Failed to analyze trades");
            return { success: false, proposed_changes: [], summary: { trades_to_close: 0, pnl_updates: 0, total_pnl_change: 0 } };
        }
    };

    const applyReconciliation = async (accountId: number, changes: any[]) => {
        try {
            const res = await axios.post(`${API_BASE}/dashboard/reconcile/${accountId}/apply`, changes);
            if (res.data.success) {
                toast.success(res.data.message || "Reconciliation applied");
                fetchData();
            }
            return res.data;
        } catch (error) {
            console.error("Failed to apply reconciliation:", error);
            toast.error("Failed to apply changes");
            return { success: false };
        }
    };

    // ==========================================================================
    // COMPUTED VALUES
    // ==========================================================================

    // Get data for currently selected account
    const positions = selectedAccountId ? positionsByAccount[selectedAccountId] || [] : [];
    const orders = selectedAccountId ? ordersByAccount[selectedAccountId] || [] : [];
    const historicalTrades = selectedAccountId ? tradesByAccount[selectedAccountId] || [] : [];
    const selectedAccountSettings = selectedAccountId ? accountSettings[selectedAccountId] : null;

    // Get all positions across all accounts (for orphan detection, etc.)
    const allPositions = Object.values(positionsByAccount).flat();
    const allOrders = Object.values(ordersByAccount).flat();

    // ==========================================================================
    // EFFECTS
    // ==========================================================================

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, [fetchData]);

    // ==========================================================================
    // RETURN
    // ==========================================================================

    return {
        // Core Data
        trades,
        logs,
        stats,

        // Connection
        accounts,
        isConnected,
        loading,
        connect,
        logout,

        // Per-Account Data
        positionsByAccount,
        ordersByAccount,
        tradesByAccount,

        // Current Selection (for backward compatibility)
        positions,
        orders,
        historicalTrades,
        selectedAccountId,
        setSelectedAccountId,
        selectedAccountSettings,

        // Aggregated Data
        allPositions,
        allOrders,

        // Settings
        globalConfig,
        updateGlobalConfig,
        accountSettings,
        updateAccountSettings,
        toggleAccountTrading,
        tradingSessions,
        strategies,
        marketStatus,

        // Actions
        closePosition,
        flattenAccount,
        flattenAllAccounts,
        previewReconciliation,
        applyReconciliation,
        loadMoreLogs,
        refresh: fetchData,

        // UI State
        historyFilter,
        setHistoryFilter,

        // Legacy compatibility
        config: globalConfig,
        updateConfig: updateGlobalConfig,
        settings: { trading_enabled: true }, // Legacy - now per-account
        toggleTrading: () => { }, // Legacy - use toggleAccountTrading
    };
};
