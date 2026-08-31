/**
 * Open Positions Table Component
 *
 * Displays the current open positions with their PnL and close actions.
 */

import type { CSSProperties } from 'react';
import { Activity, AlertTriangle, X, LayoutGrid } from 'lucide-react';
import type { Position, Trade, Strategy } from '../../types';
import { Card, CardHeader, Badge, EmptyState } from '../ui';

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
        <Card className="flex flex-col lg:col-span-2">
            <CardHeader
                icon={Activity}
                title="Open Positions"
                annotation={positions.length > 0 ? `${positions.length}` : undefined}
                actions={
                    <button
                        onClick={onFlattenAll}
                        className="btn-kill"
                        title="Flatten & Cancel All"
                    >
                        <AlertTriangle className="w-4 h-4" />
                        Flatten &amp; Cancel All
                    </button>
                }
            />

            {positions.length === 0 ? (
                <EmptyState
                    icon={LayoutGrid}
                    title="No open positions"
                    hint="Positions opened by the bot or manually will appear here."
                    className="flex-1"
                />
            ) : (
            <div className="scroll-x flex-1">
                <table className="w-full text-sm text-left">
                    <thead>
                        <tr className="table-header">
                            <th className="table-cell text-left">Contract</th>
                            <th className="table-cell text-left">Strategy</th>
                            <th className="table-cell text-center">Side</th>
                            <th className="table-cell num">Qty</th>
                            <th className="table-cell num">Entry</th>
                            <th className="table-cell num">Current</th>
                            <th className="table-cell num">PnL</th>
                            <th className="table-cell text-center">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {positions.map((pos, index) => {
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
                                <tr
                                    key={pos.id}
                                    className="table-row animate-stagger"
                                    style={{ '--i': index } as CSSProperties}
                                >
                                    <td className="table-cell font-bold text-white">{pos.contractId}</td>
                                    <td className="table-cell text-violet-300 font-mono text-xs">
                                        {tf ? `${stratDisplay} (${tf})` : stratDisplay}
                                    </td>
                                    <td className="table-cell text-center">
                                        <Badge variant={pos.type === 1 ? 'success' : 'danger'} dot>
                                            {pos.type === 1 ? 'LONG' : 'SHORT'}
                                        </Badge>
                                    </td>
                                    <td className="table-cell num">{pos.size}</td>
                                    <td className="table-cell num">{pos.averagePrice.toFixed(2)}</td>
                                    <td className="table-cell num text-slate-400">
                                        {pos.currentPrice ? pos.currentPrice.toFixed(2) : '-'}
                                    </td>
                                    <td className={`table-cell num ${pos.unrealizedPnl === undefined || pos.unrealizedPnl === null
                                        ? 'font-mono font-bold text-slate-500'
                                        : pos.unrealizedPnl >= 0
                                            ? 'readout-up'
                                            : 'readout-down'
                                        }`}>
                                        {pos.unrealizedPnl !== undefined && pos.unrealizedPnl !== null
                                            ? `$${pos.unrealizedPnl.toFixed(2)}`
                                            : '-'}
                                    </td>
                                    <td className="table-cell text-center">
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
                    </tbody>
                </table>
            </div>
            )}
        </Card>
    );
}
