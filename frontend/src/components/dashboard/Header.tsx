/**
 * Dashboard Header Component
 * 
 * Displays logo, status badges (connection, market, session), 
 * account selector dropdown, and daily PnL/active trades stats.
 */

import { useState, useEffect } from 'react';
import { DollarSign, Activity, CheckCircle, ChevronDown, Power } from 'lucide-react';
import type { Account, AccountSettings, MarketStatus } from '../../types';

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
    const isMarketOpen = marketStatus.is_open;

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
        <header className="max-w-7xl mx-auto mb-6 flex justify-between items-center bg-slate-900/50 p-6 rounded-2xl border border-slate-800">
            <div className="flex items-center gap-4">
                <img src="/robot_favicon.png" alt="Bot Logo" className="w-12 h-12 rounded-xl" />
                <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                        TopStep Bot Toini666
                    </h1>
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                        {/* Connection Status */}
                        <div className="flex items-center gap-2 bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700/50 text-xs text-slate-400">
                            <span>Status:</span>
                            <span className={`font-mono font-bold ${isConnected ? 'text-green-400' : 'text-orange-400'}`}>
                                {isConnected ? 'ONLINE' : 'DISCONNECTED'}
                            </span>
                        </div>

                        {/* Market Status */}
                        <div className="flex items-center gap-2 bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700/50 text-xs text-slate-400">
                            <span>Market:</span>
                            <span className={`font-mono font-bold ${isMarketOpen ? 'text-blue-400' : 'text-slate-500'}`}>
                                {isMarketOpen ? 'OPEN' : 'CLOSED'}
                            </span>
                        </div>

                        {/* Current Session */}
                        {isMarketOpen && marketStatus.current_session && (
                            <div className="flex items-center gap-2 bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700/50 text-xs text-slate-400">
                                <span>Session:</span>
                                <span className="font-mono font-bold text-amber-400">{marketStatus.current_session}</span>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-8">
                {/* Connect Button */}
                {!isConnected && (
                    <button
                        onClick={connect}
                        disabled={loading}
                        className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-xl transition-all flex items-center gap-2 shadow-lg shadow-blue-900/20"
                    >
                        {loading ? "Connecting..." : "Connect TopStep"}
                    </button>
                )}

                {/* Account Selector */}
                {isConnected && (
                    <div className="flex items-center gap-2">
                        <div className="bg-slate-900 border border-slate-800 p-2 rounded-xl min-w-[200px] flex flex-col justify-center relative group-account-selector">
                            <p className="text-slate-400 text-xs uppercase tracking-wider mb-1 ml-1">Connected Account</p>
                            <button
                                onClick={() => accounts.length > 0 && setAccountDropdownOpen(!accountDropdownOpen)}
                                className="w-full flex items-center justify-between text-left px-1 focus:outline-none"
                                disabled={accounts.length === 0}
                            >
                                <span className="text-white font-mono text-sm truncate mr-2">
                                    {currentAccount ? `${currentAccount.name} (${currentAccount.id})` : 'Select Account'}
                                </span>
                                <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${accountDropdownOpen ? 'rotate-180' : ''}`} />
                            </button>

                            {/* Dropdown */}
                            {accountDropdownOpen && accounts.length > 0 && (
                                <div className="absolute top-full left-0 mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20">
                                    <div className="max-h-60 overflow-y-auto custom-scrollbar">
                                        {accounts.map((acc) => (
                                            <button
                                                key={acc.id}
                                                onClick={() => {
                                                    setSelectedAccountId(acc.id);
                                                    setAccountDropdownOpen(false);
                                                }}
                                                className={`w-full text-left px-4 py-2 flex items-center justify-between transition-colors hover:bg-slate-700/50 ${acc.id === selectedAccountId ? 'bg-indigo-500/10 text-indigo-400' : 'text-slate-300'
                                                    }`}
                                            >
                                                <div className="flex items-center gap-2 truncate">
                                                    <div
                                                        className={`p-0.5 rounded-full ${accountSettings[acc.id]?.trading_enabled ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-500'}`}
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
                    </div>
                )}

                <div className="h-8 w-px bg-slate-800" />

                {/* Stats */}
                <div className="flex gap-8">
                    <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl min-w-[150px] flex flex-col justify-between">
                        <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Daily P&L (Realized)</p>
                        <div className="flex items-center gap-2">
                            <DollarSign className={`w-5 h-5 ${dailyPnl >= 0 ? 'text-green-400' : 'text-red-400'}`} />
                            <span className={`text-2xl font-mono font-bold ${dailyPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {dailyPnl.toFixed(2)}
                            </span>
                        </div>
                    </div>
                    <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl min-w-[150px] flex flex-col justify-between">
                        <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Active Trades</p>
                        <div className="flex items-center gap-2">
                            <Activity className="w-5 h-5 text-blue-400" />
                            <span className="text-2xl font-mono font-bold text-white">
                                {activePositions}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
}
