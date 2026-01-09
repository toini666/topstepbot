import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import type { Trade, Log, Account, Position, Order, HistoricalTrade, Config } from '../types';

const API_BASE = "http://localhost:8000/api";

export const useTopStep = () => {
    const [trades, setTrades] = useState<Trade[]>([]);
    const [logs, setLogs] = useState<Log[]>([]);
    const [stats, setStats] = useState({ daily_pnl: 0, active_trades: 0 });
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [positions, setPositions] = useState<Position[]>([]);
    const [orders, setOrders] = useState<Order[]>([]);
    const [historicalTrades, setHistoricalTrades] = useState<HistoricalTrade[]>([]);
    const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);

    const [isConnected, setIsConnected] = useState(false);

    const [settings, setSettings] = useState({ trading_enabled: true });
    const [config, setConfig] = useState<Config>({
        risk_per_trade: 200,
        blocked_periods_enabled: true,
        blocked_periods: [],
        auto_flatten_enabled: false,
        auto_flatten_time: "21:55"
    }); // Default

    // Log Fetch Params
    const [logParams, setLogParams] = useState<{ min_timestamp: string | null; limit: number }>({
        min_timestamp: new Date(new Date().setHours(0, 0, 0, 0)).toISOString(),
        limit: 1000
    });

    // History Filter: 'today' (1 day) or 'week' (7 days)
    const [historyFilter, setHistoryFilter] = useState<'today' | 'week'>('today');

    const fetchData = async () => {
        try {
            // 1. Fetch Basic Data
            const [tradesRes, logsRes, statsRes, settingsRes, statusRes, configRes] = await Promise.all([
                axios.get(`${API_BASE}/dashboard/trades`),
                axios.get(`${API_BASE}/dashboard/logs`, {
                    params: {
                        limit: logParams.limit,
                        min_timestamp: logParams.min_timestamp
                    }
                }),
                axios.get(`${API_BASE}/dashboard/stats`),
                axios.get(`${API_BASE}/dashboard/settings`),
                axios.get(`${API_BASE}/dashboard/status`),
                axios.get(`${API_BASE}/dashboard/config`)
            ]);

            setTrades(tradesRes.data);
            setLogs(logsRes.data);
            setStats(statsRes.data);
            if (settingsRes.data) setSettings(settingsRes.data);
            if (configRes.data) setConfig(configRes.data);

            // 2. Check & Update Connection Status
            const currentlyConnected = statusRes.data.connected;

            if (currentlyConnected !== isConnected) {
                setIsConnected(currentlyConnected);
            }

            // 3. Fetch TopStep Data if Connected
            if (currentlyConnected) {
                try {
                    const accountsRes = await axios.get(`${API_BASE}/dashboard/accounts`);
                    setAccounts(accountsRes.data);

                    // Sync Selected Account from Backend (always check for external updates)
                    try {
                        const selectedRes = await axios.get(`${API_BASE}/dashboard/accounts/selected`);
                        const remoteId = selectedRes.data.account_id;

                        if (remoteId !== selectedAccountId) {
                            setSelectedAccountId(remoteId);
                        }

                        // Fallback: If no account selected on backend but accounts exist, select first
                        if (!remoteId && accountsRes.data.length > 0 && selectedAccountId === null) {
                            // Optional: Auto-select logic if desired, or leave null
                            // For now, let's respect backend state. 
                            // If backend is null, we stay null unless we want to force auto-select.
                        }
                    } catch (e) {
                        console.warn("Error syncing selected account:", e);
                    }

                } catch (e) {
                    console.warn("Error fetching accounts despite being connected:", e);
                }

                // If account is selected, fetch deep data
                if (selectedAccountId) {
                    try {
                        const days = historyFilter === 'today' ? 1 : 7;

                        const [posRes, ordersRes, histTradesRes] = await Promise.all([
                            axios.get(`${API_BASE}/dashboard/positions`),
                            axios.get(`${API_BASE}/dashboard/orders`, { params: { days } }),
                            axios.get(`${API_BASE}/dashboard/trades-history`, { params: { days } })
                        ]);
                        setPositions(posRes.data);
                        setOrders(ordersRes.data);
                        setHistoricalTrades(histTradesRes.data);
                    } catch (e) {
                        console.warn("Error fetching account details:", e);
                    }
                } else {
                    setPositions([]);
                    setOrders([]);
                    setHistoricalTrades([]);
                }
            } else {
                if (isConnected) setIsConnected(false); // Double check fallback
            }

        } catch (error) {
            console.error("Failed to fetch dashboard data:", error);
        } finally {
            setLoading(false);
        }
    };

    const loadMoreLogs = () => {
        setLogParams({
            min_timestamp: null,
            limit: logs.length + 50
        });
    };

    const toggleTrading = async () => {
        try {
            const newState = !settings.trading_enabled;
            await axios.post(`${API_BASE}/dashboard/settings/switch`, { trading_enabled: newState });
            setSettings({ ...settings, trading_enabled: newState });
            toast.success(`Trading ${newState ? 'Enabled' : 'Disabled'} Successfully`);
        } catch (error) {
            console.error("Failed to toggle settings:", error);
            toast.error("Failed to toggle trading status");
        }
    };

    const updateConfig = async (newConfig: Partial<Config>) => {
        try {
            await axios.post(`${API_BASE}/dashboard/config`, newConfig);
            toast.success("Settings Saved Successfully");
            // Optimistic update or refresh? Refresh is safer.
            fetchData();
        } catch (error) {
            console.error("Failed to update config:", error);
            toast.error("Failed to save settings");
        }
    };

    const connect = async () => {
        setLoading(true);
        try {
            const accountsRes = await axios.get(`${API_BASE}/dashboard/accounts`);
            if (accountsRes.data && accountsRes.data.length > 0) {
                setAccounts(accountsRes.data);
                setIsConnected(true);
                toast.success("Connected to TopStep Successfully");
                const selectedRes = await axios.get(`${API_BASE}/dashboard/accounts/selected`);
                if (selectedRes.data.account_id) {
                    setSelectedAccountId(selectedRes.data.account_id);
                }
            } else {
                console.warn("No accounts returned from TopStep.");
                toast.error("Connected to Backend, but no TopStep accounts found.");
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
            setPositions([]);
            setOrders([]);
            setHistoricalTrades([]);
            toast.success("Disconnected Successfully");
        } catch (error) {
            console.error("Failed to logout", error);
            toast.error("Failed to disconnect");
        }
    };

    const selectAccount = async (id: number) => {
        try {
            await axios.post(`${API_BASE}/dashboard/accounts/select`, { account_id: id });
            setSelectedAccountId(id);
            toast.success("Account Selected");
        } catch (error) {
            console.error("Failed to select account:", error);
            toast.error("Failed to select account");
        }
    };

    useEffect(() => {
        fetchData(); // Initial fetch
        const interval = setInterval(fetchData, 5000); // Poll every 5 seconds
        return () => clearInterval(interval);
    }, [isConnected, selectedAccountId, logParams, historyFilter]);

    return {
        trades, logs, stats, accounts, positions, orders, historicalTrades,
        selectedAccountId,
        selectAccount,
        connect,
        logout,
        loadMoreLogs,
        isConnected,
        loading,
        settings,
        toggleTrading,
        config,
        updateConfig,
        refresh: fetchData,
        historyFilter,
        setHistoryFilter
    };
};
