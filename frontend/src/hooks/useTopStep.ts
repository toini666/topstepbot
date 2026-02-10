import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import type {
    Trade, Log, Account, Position, Order, HistoricalTrade,
    GlobalConfig, MarketStatus, AccountSettings, TradingSession, Strategy
} from '../types';
import { API_BASE } from '../config';
import { setUserTimezone, todayMidnightUtcIso } from '../utils/timezone';

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

    // Polling cadence refs (ms)
    const lastPositionsFetchRef = useRef(0);
    const lastOrdersFetchRef = useRef(0);
    const lastTradesFetchRef = useRef(0);
    const lastAccountsFetchRef = useRef(0);

    // Keep latest positions in a ref to avoid extra deps
    const positionsByAccountRef = useRef<Record<number, Position[]>>({});

    // Settings
    const [globalConfig, setGlobalConfig] = useState<GlobalConfig>({
        timezone: 'Europe/Brussels',
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
        min_timestamp: todayMidnightUtcIso(),
        limit: 1000
    });

    // Keep ref in sync for interval decisions
    useEffect(() => {
        positionsByAccountRef.current = positionsByAccount;
    }, [positionsByAccount]);

    // Reset trades & orders fetch timers when history filter changes so data loads immediately
    useEffect(() => {
        lastTradesFetchRef.current = 0;
        lastOrdersFetchRef.current = 0;
    }, [historyFilter]);

    // ==========================================================================
    // DATA FETCHING
    // ==========================================================================

    // ==========================================================================
    // DATA FETCHING
    // ==========================================================================

    const fetchStaticData = useCallback(async () => {
        try {
            const [configRes, sessionsRes, strategiesRes, accountsRes, settingsRes] = await Promise.all([
                axios.get(`${API_BASE}/dashboard/config`),
                axios.get(`${API_BASE}/settings/sessions`),
                axios.get(`${API_BASE}/strategies`),
                axios.get(`${API_BASE}/dashboard/accounts`),
                axios.get(`${API_BASE}/settings/accounts`)
            ]);

            if (configRes.data) {
                setGlobalConfig(configRes.data);
                if (configRes.data.timezone) {
                    setUserTimezone(configRes.data.timezone);
                }
            }
            if (sessionsRes.data) setTradingSessions(sessionsRes.data);
            if (strategiesRes.data) setStrategies(strategiesRes.data);
            if (accountsRes.data) {
                setAccounts(accountsRes.data);
                if (accountsRes.data.length > 0 && !selectedAccountId) {
                    // Only set initial account if not already selected
                    // We use function update to be safe but here direct check is fine provided selectedAccountId is in closure
                    // Actually, inside useCallback, selectedAccountId might be stale if strict deps. 
                    // But for 'Static' fetch which happens once, we usually don't want to reset it.
                    // Let's rely on the effect to set default if null.
                }
            }

            if (settingsRes.data) {
                const settingsMap: Record<number, AccountSettings> = {};
                for (const s of settingsRes.data) {
                    settingsMap[s.account_id] = s;
                }
                setAccountSettings(settingsMap);
            }

        } catch (error) {
            console.error("Failed to fetch static data:", error);
        }
    }, []); // No dependencies, static fetch

    const fetchPollingData = useCallback(async () => {
        try {
            const now = Date.now();

            // 1. Fetch Dynamic Data
            const [tradesRes, logsRes, statsRes, statusRes, marketRes] = await Promise.all([
                axios.get(`${API_BASE}/dashboard/trades`),
                axios.get(`${API_BASE}/dashboard/logs`, {
                    params: { limit: logParams.limit, min_timestamp: logParams.min_timestamp }
                }),
                axios.get(`${API_BASE}/dashboard/stats`),
                axios.get(`${API_BASE}/dashboard/status`),
                axios.get(`${API_BASE}/dashboard/market-status`)
            ]);

            // Helper for smart updates to avoid effect triggering if data is same


            // Note: We access state via function updates or just rely on React's optimization.
            // But to use 'smartSet', we'd need current state in deps. 
            // To break the loop, we should just set state. React 18+ auto-batches and shallow compares primitives.
            // For objects/arrays, setting a new reference WILL trigger re-renders, but that's what we want if data changed.
            // The issue was the *fetching* loop. 
            // We will just set the data. React is smart enough.

            setTrades(prev => JSON.stringify(prev) !== JSON.stringify(tradesRes.data) ? tradesRes.data : prev);

            // For logs, check IDs
            setLogs(prev => {
                const newLogs = logsRes.data;
                if (prev.length !== newLogs.length || (newLogs.length > 0 && prev[0]?.id !== newLogs[0].id)) {
                    return newLogs;
                }
                return prev;
            });

            setStats(prev => JSON.stringify(prev) !== JSON.stringify(statsRes.data) ? statsRes.data : prev);
            setMarketStatus(prev => JSON.stringify(prev) !== JSON.stringify(marketRes.data) ? marketRes.data : prev);

            // 2. Check Connection & Fetch Account Details
            const currentlyConnected = statusRes.data.connected;
            setIsConnected(currentlyConnected); // Primitives are cheap to set repeatedly

            if (currentlyConnected) {
                try {
                    // We need accounts list to iterate. We can assume static list is ok, or fetch briefly.
                    // The 'accounts' list rarely changes, so we rely on static fetch or infrequent updates?
                    // Let's rely on static fetch for the *list* of accounts. 
                    // But we iterate 'accounts' state here. If 'accounts' is empty initially, we miss this?
                    // We should pass the current accounts list to this function or use a ref.
                    // Better: Fetch account list here too? No, expensive.
                    // Actually, let's just fetch positions for *known* accounts from state.
                    // But if we can't access state without deps...
                    // We will fetch the account list light-weight or just trust the 'accounts' state if added to deps.
                    // Adding 'accounts' to deps is safe IF 'accounts' itself doesn't change every poll.
                    // With fetchStaticData, accounts only changes on mount, so it's safe!

                    // Wait, we need 'accounts' in scope.

                    if (accounts.length > 0) {
                        const hasOpenPositions = Object.values(positionsByAccountRef.current).some(
                            (positions) => positions && positions.length > 0
                        );

                        const positionsIntervalMs = hasOpenPositions ? 5000 : 15000;
                        const ordersIntervalMs = 30000;
                        const tradesIntervalMs = 60000;
                        const accountsIntervalMs = 30000;

                        const shouldFetchPositions = now - lastPositionsFetchRef.current >= positionsIntervalMs;
                        const shouldFetchOrders = now - lastOrdersFetchRef.current >= ordersIntervalMs;
                        const shouldFetchTrades = now - lastTradesFetchRef.current >= tradesIntervalMs;
                        const shouldFetchAccounts = now - lastAccountsFetchRef.current >= accountsIntervalMs;

                        if (shouldFetchPositions) lastPositionsFetchRef.current = now;
                        if (shouldFetchOrders) lastOrdersFetchRef.current = now;
                        if (shouldFetchTrades) lastTradesFetchRef.current = now;
                        if (shouldFetchAccounts) lastAccountsFetchRef.current = now;

                        const days = historyFilter === 'today' ? 1 : 7;
                        const newPositions: Record<number, Position[]> | null = shouldFetchPositions ? {} : null;
                        const newOrders: Record<number, Order[]> | null = shouldFetchOrders ? {} : null;
                        const newTrades: Record<number, HistoricalTrade[]> | null = shouldFetchTrades ? {} : null;

                        const parseUtcTimestamp = (ts: string | null | undefined): string | null => {
                            if (!ts) return null;
                            const tsStr = String(ts);
                            if (!tsStr.endsWith('Z') && !tsStr.includes('+')) {
                                return tsStr.replace(' ', 'T') + 'Z';
                            }
                            return tsStr.replace(' ', 'T');
                        };

                        // Parallel Fetch for ALL accounts
                        await Promise.all(accounts.map(async (account) => {
                            const aid = account.id;
                            try {
                                const tasks: Promise<void>[] = [];

                                if (shouldFetchPositions) {
                                    tasks.push(
                                        axios.get(`${API_BASE}/dashboard/positions/${aid}`).then(res => {
                                            if (newPositions) newPositions[aid] = res.data;
                                        }).catch(() => {
                                            if (newPositions) newPositions[aid] = [];
                                        })
                                    );
                                }

                                if (shouldFetchOrders) {
                                    tasks.push(
                                        axios.get(`${API_BASE}/dashboard/orders/${aid}`, { params: { days } }).then(res => {
                                            if (newOrders) newOrders[aid] = res.data;
                                        }).catch(() => {
                                            if (newOrders) newOrders[aid] = [];
                                        })
                                    );
                                }

                                if (shouldFetchTrades) {
                                    tasks.push(
                                        axios.get(`${API_BASE}/dashboard/trades`, { params: { account_id: aid, days, status: 'CLOSED' } }).then(res => {
                                            if (!newTrades) return;
                                            newTrades[aid] = res.data.map((t: Trade) => ({
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
                                                entryPrice: t.entry_price,
                                                isAggregated: true
                                            }));
                                        }).catch(() => {
                                            if (newTrades) newTrades[aid] = [];
                                        })
                                    );
                                }

                                if (tasks.length > 0) {
                                    await Promise.all(tasks);
                                }
                            } catch (e) {
                                // console.warn(`Error fetching data for account ${aid}:`, e);
                                if (newPositions) newPositions[aid] = [];
                                if (newOrders) newOrders[aid] = [];
                                if (newTrades) newTrades[aid] = [];
                            }
                        }));

                        // Refresh accounts (balance) periodically
                        if (shouldFetchAccounts) {
                            try {
                                const accountsRes = await axios.get(`${API_BASE}/dashboard/accounts`);
                                if (accountsRes.data) {
                                    setAccounts(prev => JSON.stringify(prev) !== JSON.stringify(accountsRes.data) ? accountsRes.data : prev);
                                }
                            } catch {
                                // Silently ignore - accounts will refresh next cycle
                            }
                        }

                        // Smart update for big objects
                        if (newPositions) {
                            setPositionsByAccount(prev => JSON.stringify(prev) !== JSON.stringify(newPositions) ? newPositions : prev);
                        }
                        if (newOrders) {
                            setOrdersByAccount(prev => JSON.stringify(prev) !== JSON.stringify(newOrders) ? newOrders : prev);
                        }
                        if (newTrades) {
                            setTradesByAccount(prev => JSON.stringify(prev) !== JSON.stringify(newTrades) ? newTrades : prev);
                        }
                    } else {
                        // Maybe accounts not loaded yet?
                        // If we just started, static fetch might be running.
                    }

                } catch (e) {
                    // console.warn("Error fetching detailed account data:", e);
                }
            }

        } catch (error) {
            console.error("Failed to fetch polling data:", error);
        } finally {
            setLoading(false);
        }
    }, [logParams, historyFilter, accounts]); // Dependencies that *change what we fetch*, not the result of fetching

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
            // Optimistic update: merge saved values into local state immediately
            // No need for a re-fetch round-trip (which can fail in Docker/nginx)
            setGlobalConfig(prev => ({ ...prev, ...newConfig }));
            toast.success("Settings Saved Successfully");
        } catch (error) {
            console.error("Failed to update config:", error);
            toast.error("Failed to save settings");
        }
    };

    const updateAccountSettings = async (accountId: number, updates: Partial<AccountSettings>) => {
        try {
            await axios.post(`${API_BASE}/settings/accounts/${accountId}`, updates);
            toast.success("Account Settings Updated");
            fetchStaticData(); // Account settings are static
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
                fetchPollingData(); // Fetch initial data
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
            fetchPollingData();
        } catch (error) {
            console.error("Failed to close position:", error);
            toast.error("Failed to close position");
        }
    };

    const flattenAccount = async (accountId: number) => {
        try {
            await axios.post(`${API_BASE}/dashboard/account/${accountId}/flatten`);
            toast.success("Account Flattened");
            fetchPollingData();
        } catch (error) {
            console.error("Failed to flatten account:", error);
            toast.error("Failed to flatten account");
        }
    };

    const flattenAllAccounts = async () => {
        try {
            await axios.post(`${API_BASE}/dashboard/flatten-all`);
            toast.success("All Accounts Flattened");
            fetchPollingData();
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
                fetchPollingData();
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

    // Initial Using Static Load
    useEffect(() => {
        fetchStaticData();
    }, [fetchStaticData]);

    // Polling Effect
    useEffect(() => {
        let isMounted = true;
        let timeoutId: ReturnType<typeof setTimeout>;

        const poll = async () => {
            if (!isMounted) return;
            await fetchPollingData();
            if (isMounted) {
                // Determine poll interval based on connection status? 
                // Stick to 5s for now as requested.
                timeoutId = setTimeout(poll, 5000);
            }
        };

        poll();

        return () => {
            isMounted = false;
            clearTimeout(timeoutId);
        };
    }, [fetchPollingData]); // Re-starts polling only if fetchPollingData changes (e.g. filter change)

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
        refresh: () => { fetchStaticData(); fetchPollingData(); },

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
