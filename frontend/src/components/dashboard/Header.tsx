/**
 * Dashboard Header Component
 *
 * Displays logo, status badges (connection, market, session),
 * account selector dropdown, and daily PnL/active trades stats.
 */

import { useState, useEffect } from 'react';
import { DollarSign, Activity, CheckCircle, ChevronDown, Power, RefreshCw } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import type { Account, AccountSettings, MarketStatus } from '../../types';
import { API_BASE } from '../../config';
import { StatusLamp, Stat } from '../ui';

interface HeaderProps {
    // Connection
    isConnected: boolean;
    loading: boolean;
    connect: () => void;
    logout: () => void;

    // Accounts
    accounts: Account[];
    selectedAccountId: number | null;
    setSelectedAccountId: (id: number) => void;
    accountSettings: Record<number, AccountSettings>;
    currentAccount: Account | undefined;

    // Status
    marketStatus: MarketStatus;

    // Stats
    dailyPnl: number;
    activePositions: number;

    // Modal handlers
    onDisconnect: () => void;
}

export function Header({
    isConnected,
    loading,
    connect,
    accounts,
    selectedAccountId,
    setSelectedAccountId,
    accountSettings,
    currentAccount,
    marketStatus,
    dailyPnl,
    activePositions,
    onDisconnect,
}: HeaderProps) {
    const [accountDropdownOpen, setAccountDropdownOpen] = useState(false);
    const [reconnecting, setReconnecting] = useState(false);
    const isMarketOpen = marketStatus.is_open;

    const handleForceReconnect = async () => {
        setReconnecting(true);
        try {
            const res = await axios.post(`${API_BASE}/reconnect`);
            if (res.data.success) {
                toast.success("Reconnected successfully");
                connect();
            } else {
                toast.error(res.data.message);
            }
        } catch {
            toast.error("Reconnection failed");
        } finally {
            setReconnecting(false);
        }
    };

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (accountDropdownOpen && !target.closest('.group-account-selector')) {
                setAccountDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [accountDropdownOpen]);

    return (
        <header className="max-w-7xl mx-auto mb-6 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5 bg-slate-900/50 p-4 sm:p-6 rounded-2xl border border-slate-800/60 shadow-lg shadow-black/20">
            <div className="flex items-center gap-4">
                <img
                    src="/robot_favicon.png"
                    alt="Bot Logo"
                    className="w-12 h-12 rounded-xl ring-1 ring-indigo-400/30 shadow-[0_0_20px_-4px_rgba(99,102,241,0.45)]"
                />
                <div>
                    <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                        TopStep Bot Toini666
                    </h1>
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                        {/* Connection Status */}
                        <StatusLamp
                            color={isConnected ? 'emerald' : 'red'}
                            live
                            label="STATUS"
                            value={isConnected ? 'ONLINE' : 'DISCONNECTED'}
                        />

                        {/* Market Status */}
                        <StatusLamp
                            color={isMarketOpen ? 'sky' : 'slate'}
                            live={isMarketOpen}
                            label="MARKET"
                            value={isMarketOpen ? 'OPEN' : 'CLOSED'}
                        />

                        {/* Current Session */}
                        {isMarketOpen && marketStatus.current_session && (
                            <StatusLamp
                                color="amber"
                                label="SESSION"
                                value={marketStatus.current_session}
                            />
                        )}
                    </div>
                </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 lg:gap-6">
                {/* Connect / Force Reconnect Buttons */}
                {!isConnected && (
                    <div className="flex gap-2">
                        <button
                            onClick={connect}
                            disabled={loading}
                            className="btn-primary"
                        >
                            {loading ? "Connecting..." : "Connect TopStep"}
                        </button>
                        <button
                            onClick={handleForceReconnect}
                            disabled={reconnecting}
                            title="Reset all backoff timers and force a fresh login"
                            className="inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold text-amber-400 rounded-xl border border-amber-500/40 bg-amber-500/5 hover:bg-amber-500/10 hover:border-amber-500/60 hover:text-amber-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <RefreshCw className={`w-3.5 h-3.5 ${reconnecting ? 'animate-spin' : ''}`} />
                            {reconnecting ? "..." : "Force"}
                        </button>
                    </div>
                )}

                {/* Account Selector */}
                {isConnected && (
                    <div className="relative group-account-selector flex flex-col justify-center min-w-[200px] bg-slate-900 border border-slate-800/60 p-2 rounded-xl">
                        <p className="micro-label mb-1 ml-1">Connected Account</p>
                        <button
                            onClick={() => accounts.length > 0 && setAccountDropdownOpen(!accountDropdownOpen)}
                            className="w-full flex items-center justify-between text-left px-1"
                            disabled={accounts.length === 0}
                        >
                            <span className="text-white font-mono text-sm truncate mr-2">
                                {currentAccount ? `${currentAccount.name} (${currentAccount.id})` : 'Select Account'}
                            </span>
                            <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${accountDropdownOpen ? 'rotate-180' : ''}`} />
                        </button>

                        {/* Dropdown */}
                        {accountDropdownOpen && accounts.length > 0 && (
                            <div className="dropdown-menu top-full left-0 mt-2 w-full">
                                <div className="max-h-60 overflow-y-auto custom-scrollbar">
                                    {accounts.map((acc) => (
                                        <button
                                            key={acc.id}
                                            onClick={() => {
                                                setSelectedAccountId(acc.id);
                                                setAccountDropdownOpen(false);
                                            }}
                                            className={acc.id === selectedAccountId ? 'dropdown-item-active' : 'dropdown-item'}
                                        >
                                            <div className="flex items-center gap-2 truncate">
                                                <div
                                                    className={`p-0.5 rounded-full ${accountSettings[acc.id]?.trading_enabled ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-500'}`}
                                                    title={accountSettings[acc.id]?.trading_enabled ? "Trading ON" : "Trading OFF"}
                                                >
                                                    <Power className="w-3 h-3" />
                                                </div>
                                                <span className="font-mono text-xs truncate">{acc.name} ({acc.id})</span>
                                            </div>
                                            {acc.id === selectedAccountId && <CheckCircle className="w-3 h-3 flex-shrink-0" />}
                                        </button>
                                    ))}
                                </div>

                                {/* Disconnect Option */}
                                <div className="border-t border-slate-700 mt-1 pt-1 bg-slate-900/50">
                                    <button
                                        onClick={() => {
                                            setAccountDropdownOpen(false);
                                            onDisconnect();
                                        }}
                                        className="w-full text-left px-4 py-2 flex items-center gap-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
                                    >
                                        <div className="p-0.5 rounded-full bg-red-500/10">
                                            <Power className="w-3 h-3" />
                                        </div>
                                        <span className="font-bold text-xs">Disconnect</span>
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                <div className="hidden lg:block h-8 w-px bg-slate-700/40" />

                {/* Stats */}
                <div className="flex flex-wrap gap-4">
                    <Stat
                        label="Daily P&L (Realized)"
                        value={`${dailyPnl > 0 ? '+' : dailyPnl < 0 ? '−' : ''}$${Math.abs(dailyPnl).toFixed(2)}`}
                        icon={DollarSign}
                        tone={dailyPnl > 0 ? 'up' : dailyPnl < 0 ? 'down' : 'flat'}
                    />
                    <Stat
                        label="Active Trades"
                        value={activePositions}
                        icon={Activity}
                        tone="neutral"
                    />
                </div>
            </div>
        </header>
    );
}
