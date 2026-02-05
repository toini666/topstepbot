/**
 * Open Positions Table Component
 * 
 * Displays the current open positions with their PnL and close actions.
 */

import { Activity, AlertTriangle, X } from 'lucide-react';
import type { Position, Trade, Strategy } from '../../types';

interface PositionsTableProps {
    positions: Position[];
    trades: Trade[];
    strategies: Strategy[];
    onClosePosition: (contractId: string) => void;
    onFlattenAll: () => void;
}

export function PositionsTable({
    positions,
    trades,
    strategies,
    onClosePosition,
    onFlattenAll,
}: PositionsTableProps) {
    return (
        <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 flex flex-col lg:col-span-2">
            <div className="flex justify-between items-start mb-6">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                    <Activity className="w-5 h-5 text-indigo-400" />
                    Open Positions
                </h2>
                <button
                    onClick={onFlattenAll}
                    className="btn-danger text-xs"
                    title="Flatten & Cancel All"
                >
                    <AlertTriangle className="w-4 h-4" />
                    Flatten & Cancel All
                </button>
            </div>

            <div className="overflow-x-auto flex-1">
                <table className="w-full text-sm text-left">
                    <thead className="text-slate-500 border-b border-slate-800 uppercase text-xs">
                        <tr>
                            <th className="py-3 px-4">Contract</th>
                            <th className="py-3 px-4">Strategy</th>
                            <th className="py-3 px-4 text-center">Side</th>
                            <th className="py-3 px-4 text-center">Qty</th>
                            <th className="py-3 px-4 text-right">Entry</th>
                            <th className="py-3 px-4 text-right">Current</th>
                            <th className="py-3 px-4 text-right">PnL</th>
                            <th className="py-3 px-4 text-center">Action</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                        {positions.map((pos) => {
                            // Find matching trade for strategy info
                            const matchingTrade = trades.find(t =>
                                t.ticker && pos.contractId &&
                                pos.contractId.toUpperCase().includes(t.ticker.replace('1!', '').replace('2!', '').toUpperCase()) &&
                                t.status === 'OPEN'
                            );
                            const strat = matchingTrade ? strategies.find(s => s.tv_id === matchingTrade.strategy) : null;
                            const stratDisplay = strat?.name || matchingTrade?.strategy || '-';
                            const tf = matchingTrade?.timeframe;

                            return (
                                <tr key={pos.id} className="hover:bg-slate-800/30 transition-colors">
                                    <td className="py-3 px-4 font-bold text-white">{pos.contractId}</td>
                                    <td className="py-3 px-4 text-violet-300 font-mono text-xs">
                                        {tf ? `${stratDisplay} (${tf})` : stratDisplay}
                                    </td>
                                    <td className="py-3 px-4 text-center">
                                        <span className={pos.type === 1 ? 'badge-success' : 'badge-danger'}>
                                            {pos.type === 1 ? 'LONG' : 'SHORT'}
                                        </span>
                                    </td>
                                    <td className="py-3 px-4 text-center font-mono">{pos.size}</td>
                                    <td className="py-3 px-4 text-right font-mono">{pos.averagePrice.toFixed(2)}</td>
                                    <td className="py-3 px-4 text-right font-mono text-slate-400">
                                        {pos.currentPrice ? pos.currentPrice.toFixed(2) : '-'}
                                    </td>
                                    <td className={`py-3 px-4 text-right font-mono font-bold ${pos.unrealizedPnl === undefined || pos.unrealizedPnl === null
                                        ? 'text-slate-500'
                                        : pos.unrealizedPnl >= 0
                                            ? 'text-green-400'
                                            : 'text-red-400'
                                        }`}>
                                        {pos.unrealizedPnl !== undefined && pos.unrealizedPnl !== null
                                            ? `$${pos.unrealizedPnl.toFixed(2)}`
                                            : '-'}
                                    </td>
                                    <td className="py-3 px-4 text-center">
                                        <button
                                            onClick={() => onClosePosition(pos.contractId)}
                                            className="p-1.5 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
                                            title="Close Position"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </td>
                                </tr>
                            );
                        })}
                        {positions.length === 0 && (
                            <tr>
                                <td colSpan={8} className="py-8 text-center text-slate-500 italic">No open positions.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}
