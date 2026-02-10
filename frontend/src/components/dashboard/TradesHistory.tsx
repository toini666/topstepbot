/**
 * Trades History Table Component
 * 
 * Displays closed trades with filtering by time period and strategy.
 */

import { useState, useEffect } from 'react';
import { DollarSign, ChevronDown, CheckCircle, RefreshCw } from 'lucide-react';
import { formatInUserTz } from '../../utils/timezone';
import type { AggregatedTrade, Strategy } from '../../types';

interface TradesHistoryProps {
    trades: AggregatedTrade[];
    strategies: Strategy[];
    historyFilter: 'today' | 'week';
    setHistoryFilter: (filter: 'today' | 'week') => void;
    onReconcile: () => void;
    isReconcileDisabled: boolean;
    reconcileTitle: string;
}

export function TradesHistory({
    trades,
    strategies,
    historyFilter,
    setHistoryFilter,
    onReconcile,
    isReconcileDisabled,
    reconcileTitle,
}: TradesHistoryProps) {
    const [selectedStrategyFilter, setSelectedStrategyFilter] = useState<string>('ALL');
    const [strategyDropdownOpen, setStrategyDropdownOpen] = useState(false);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (strategyDropdownOpen && !target.closest('.group-strategy-selector')) {
                setStrategyDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [strategyDropdownOpen]);

    const filteredTrades = trades.filter(t =>
        selectedStrategyFilter === 'ALL' || t.strategy === selectedStrategyFilter
    );

    return (
        <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-emerald-400" />
                Closed Trades (History)
                <div className="ml-auto flex items-center gap-2">
                    {/* Reconcile Button */}
                    <button
                        onClick={onReconcile}
                        disabled={isReconcileDisabled}
                        className="btn-outline p-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:text-slate-400 disabled:hover:bg-transparent disabled:hover:border-slate-700/60"
                        title={reconcileTitle}
                    >
                        <RefreshCw className="w-4 h-4" />
                    </button>

                    {/* Time Filter */}
                    <div className="flex bg-slate-800 rounded-lg p-1 text-xs font-medium">
                        <button
                            onClick={() => setHistoryFilter('today')}
                            className={`px-3 py-1 rounded-md transition-all ${historyFilter === 'today' ? 'bg-indigo-500 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
                        >
                            Today
                        </button>
                        <button
                            onClick={() => setHistoryFilter('week')}
                            className={`px-3 py-1 rounded-md transition-all ${historyFilter === 'week' ? 'bg-indigo-500 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
                        >
                            7 Days
                        </button>

                        <div className="w-px h-4 bg-slate-700 mx-2 self-center"></div>

                        {/* Strategy Filter */}
                        <div className="relative group-strategy-selector">
                            <button
                                onClick={() => setStrategyDropdownOpen(!strategyDropdownOpen)}
                                className="flex items-center gap-2 bg-slate-800 text-slate-300 text-xs font-medium px-3 py-1.5 rounded-md border border-slate-700 hover:bg-slate-700 hover:text-white transition-colors"
                            >
                                <span>
                                    {selectedStrategyFilter === 'ALL'
                                        ? 'All Strategies'
                                        : (strategies.find(s => s.tv_id === selectedStrategyFilter)?.name || selectedStrategyFilter)}
                                </span>
                                <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${strategyDropdownOpen ? 'rotate-180' : ''}`} />
                            </button>

                            {strategyDropdownOpen && (
                                <div className="absolute top-full right-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20 animate-fade-in-down">
                                    <div className="max-h-60 overflow-y-auto custom-scrollbar p-1">
                                        <button
                                            onClick={() => {
                                                setSelectedStrategyFilter('ALL');
                                                setStrategyDropdownOpen(false);
                                            }}
                                            className={`w-full text-left px-3 py-2 rounded-lg flex items-center justify-between transition-colors text-xs ${selectedStrategyFilter === 'ALL' ? 'bg-indigo-500/10 text-indigo-400' : 'text-slate-300 hover:bg-slate-700/50'
                                                }`}
                                        >
                                            <span>All Strategies</span>
                                            {selectedStrategyFilter === 'ALL' && <CheckCircle className="w-3 h-3" />}
                                        </button>
                                        {[...new Set(trades.map(t => t.strategy).filter(Boolean))].map(strat => {
                                            const stratInfo = strategies.find(s => s.tv_id === strat);
                                            const displayName = stratInfo?.name || strat;
                                            return (
                                                <button
                                                    key={strat}
                                                    onClick={() => {
                                                        setSelectedStrategyFilter(strat || '');
                                                        setStrategyDropdownOpen(false);
                                                    }}
                                                    className={`w-full text-left px-3 py-2 rounded-lg flex items-center justify-between transition-colors text-xs ${selectedStrategyFilter === strat ? 'bg-indigo-500/10 text-indigo-400' : 'text-slate-300 hover:bg-slate-700/50'
                                                        }`}
                                                >
                                                    <span>{displayName}</span>
                                                    {selectedStrategyFilter === strat && <CheckCircle className="w-3 h-3" />}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </h2>

            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead className="text-slate-500 border-b border-slate-800 uppercase text-xs">
                        <tr>
                            <th className="py-3 px-4">Entry Time</th>
                            <th className="py-3 px-4">Exit Time</th>
                            <th className="py-3 px-4">Strategy</th>
                            <th className="py-3 px-4">Symbol</th>
                            <th className="py-3 px-4 text-center">Side</th>
                            <th className="py-3 px-4 text-center">Qty</th>
                            <th className="py-3 px-4 text-right">Entry Price</th>
                            <th className="py-3 px-4 text-right">Exit Price</th>
                            <th className="py-3 px-4 text-right">Fees</th>
                            <th className="py-3 px-4 text-right">PnL</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                        {filteredTrades.map((trade) => (
                            <tr key={trade.id} className="hover:bg-slate-800/30 transition-colors">
                                <td className="py-3 px-4 text-slate-500 font-mono text-xs">
                                    {formatInUserTz(trade.entryTime, 'MM/dd HH:mm:ss')}
                                </td>
                                <td className="py-3 px-4 text-slate-500 font-mono text-xs">
                                    {formatInUserTz(trade.exitTime, 'HH:mm:ss')}
                                </td>
                                <td className="py-3 px-4 text-violet-300 font-mono text-xs">
                                    {(() => {
                                        const strat = strategies.find(s => s.tv_id === trade.strategy);
                                        const displayName = strat?.name || trade.strategy || '-';
                                        const tf = trade.timeframe;
                                        return tf ? `${displayName} (${tf})` : displayName;
                                    })()}
                                </td>
                                <td className="py-3 px-4 font-bold text-white">{trade.symbol}</td>
                                <td className="py-3 px-4 text-center">
                                    <span className={trade.side === 'LONG' ? 'badge-success' : 'badge-danger'}>
                                        {trade.side}
                                    </span>
                                </td>
                                <td className="py-3 px-4 text-center font-mono">{trade.size}</td>
                                <td className="py-3 px-4 text-right font-mono">{trade.entryPrice.toFixed(2)}</td>
                                <td className="py-3 px-4 text-right font-mono">{trade.exitPrice.toFixed(2)}</td>
                                <td className="py-3 px-4 text-right font-mono text-slate-400">
                                    {trade.fees ? `$${trade.fees.toFixed(2)}` : '-'}
                                </td>
                                <td className={`py-3 px-4 text-right font-mono font-bold ${trade.pnl > 0 ? 'text-green-400' : trade.pnl < 0 ? 'text-red-400' : 'text-slate-500'
                                    }`}>
                                    {trade.pnl !== undefined && trade.pnl !== null ? `$${trade.pnl.toFixed(2)}` : '-'}
                                </td>
                            </tr>
                        ))}
                        {filteredTrades.length === 0 && (
                            <tr>
                                <td colSpan={10} className="py-8 text-center text-slate-500 italic">No closed trades found.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}
