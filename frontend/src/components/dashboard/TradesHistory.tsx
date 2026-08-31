/**
 * Trades History Table Component
 *
 * Displays closed trades with filtering by time period and strategy.
 */

import { useState, useEffect } from 'react';
import type { CSSProperties } from 'react';
import { DollarSign, ChevronDown, CheckCircle, RefreshCw, History } from 'lucide-react';
import { formatInUserTz } from '../../utils/timezone';
import type { AggregatedTrade, Strategy } from '../../types';
import { Card, CardHeader, Badge, SegmentedControl, EmptyState } from '../ui';

interface TradesHistoryProps {
    trades: AggregatedTrade[];
    strategies: Strategy[];
    historyFilter: 'today' | 'week';
    setHistoryFilter: (filter: 'today' | 'week') => void;
    onReconcile: () => void;
    isReconcileDisabled: boolean;
    reconcileTitle: string;
}

const PERIOD_OPTIONS = [
    { value: 'today', label: 'Today' },
    { value: 'week', label: '7 Days' },
] as const;

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
        <Card>
            <CardHeader
                icon={DollarSign}
                iconClassName="text-emerald-400"
                title="Closed Trades (History)"
                annotation={trades.length > 0 ? `${filteredTrades.length}` : undefined}
                actions={
                    <>
                        {/* Reconcile Button */}
                        <button
                            onClick={onReconcile}
                            disabled={isReconcileDisabled}
                            className="btn-outline p-2"
                            title={reconcileTitle}
                        >
                            <RefreshCw className="w-4 h-4" />
                        </button>

                        {/* Time Filter */}
                        <SegmentedControl
                            options={PERIOD_OPTIONS}
                            value={historyFilter}
                            onChange={setHistoryFilter}
                            aria-label="Trade history period"
                        />

                        {/* Strategy Filter */}
                        <div className="relative group-strategy-selector">
                            <button
                                onClick={() => setStrategyDropdownOpen(!strategyDropdownOpen)}
                                className="btn-outline text-xs"
                            >
                                <span>
                                    {selectedStrategyFilter === 'ALL'
                                        ? 'All Strategies'
                                        : (strategies.find(s => s.tv_id === selectedStrategyFilter)?.name || selectedStrategyFilter)}
                                </span>
                                <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${strategyDropdownOpen ? 'rotate-180' : ''}`} />
                            </button>

                            {strategyDropdownOpen && (
                                <div className="dropdown-menu top-full right-0 mt-2 w-48">
                                    <div className="max-h-60 overflow-y-auto custom-scrollbar p-1">
                                        <button
                                            onClick={() => {
                                                setSelectedStrategyFilter('ALL');
                                                setStrategyDropdownOpen(false);
                                            }}
                                            className={selectedStrategyFilter === 'ALL' ? 'dropdown-item-active rounded-lg' : 'dropdown-item rounded-lg'}
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
                                                    className={selectedStrategyFilter === strat ? 'dropdown-item-active rounded-lg' : 'dropdown-item rounded-lg'}
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
                    </>
                }
            />

            {filteredTrades.length === 0 ? (
                <EmptyState
                    icon={History}
                    title="No closed trades found"
                    hint="Trades closed by the bot will show up here."
                />
            ) : (
            <div className="scroll-x">
                <table className="w-full text-sm text-left">
                    <thead>
                        <tr className="table-header">
                            <th className="table-cell text-left">Entry Time</th>
                            <th className="table-cell text-left">Exit Time</th>
                            <th className="table-cell text-left">Strategy</th>
                            <th className="table-cell text-left">Symbol</th>
                            <th className="table-cell text-center">Side</th>
                            <th className="table-cell num">Qty</th>
                            <th className="table-cell num">Entry Price</th>
                            <th className="table-cell num">Exit Price</th>
                            <th className="table-cell num" title="Trading fees + TopStep commissions">Fees + Comm.</th>
                            <th className="table-cell num" title="Net PnL = Gross PnL - Fees - Commissions">Net PnL</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredTrades.map((trade, index) => {
                            const fees = trade.fees || 0;
                            const grossPnl = trade.pnl ?? 0;
                            const netPnl = grossPnl - fees;
                            return (
                                <tr
                                    key={trade.id}
                                    className="table-row animate-stagger"
                                    style={{ '--i': index } as CSSProperties}
                                >
                                    <td className="table-cell text-slate-500 font-mono text-xs">
                                        {formatInUserTz(trade.entryTime, 'MM/dd HH:mm:ss')}
                                    </td>
                                    <td className="table-cell text-slate-500 font-mono text-xs">
                                        {formatInUserTz(trade.exitTime, 'HH:mm:ss')}
                                    </td>
                                    <td className="table-cell text-violet-300 font-mono text-xs">
                                        {(() => {
                                            const strat = strategies.find(s => s.tv_id === trade.strategy);
                                            const displayName = strat?.name || trade.strategy || '-';
                                            const tf = trade.timeframe;
                                            return tf ? `${displayName} (${tf})` : displayName;
                                        })()}
                                    </td>
                                    <td className="table-cell font-bold text-white">{trade.symbol}</td>
                                    <td className="table-cell text-center">
                                        <Badge variant={trade.side === 'LONG' ? 'success' : 'danger'} dot>
                                            {trade.side}
                                        </Badge>
                                    </td>
                                    <td className="table-cell num">{trade.size}</td>
                                    <td className="table-cell num">{trade.entryPrice.toFixed(2)}</td>
                                    <td className="table-cell num">{trade.exitPrice.toFixed(2)}</td>
                                    <td className="table-cell num text-slate-400">
                                        {fees ? `$${fees.toFixed(2)}` : '-'}
                                    </td>
                                    <td
                                        className={`table-cell num ${netPnl > 0 ? 'readout-up' : netPnl < 0 ? 'readout-down' : 'readout-flat'}`}
                                        title={`Gross: $${grossPnl.toFixed(2)} − Fees+Comm.: $${fees.toFixed(2)}`}
                                    >
                                        {trade.pnl !== undefined && trade.pnl !== null ? `$${netPnl.toFixed(2)}` : '-'}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
            )}
        </Card>
    );
}
