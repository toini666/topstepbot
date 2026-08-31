/**
 * Orders Table Component
 *
 * Displays order history with time period filtering.
 */

import type { CSSProperties } from 'react';
import { TrendingUp, ListOrdered } from 'lucide-react';
import { formatInUserTz } from '../../utils/timezone';
import type { Order } from '../../types';
import { Card, CardHeader, Badge, SegmentedControl, EmptyState } from '../ui';

interface OrdersTableProps {
    orders: Order[];
    historyFilter: 'today' | 'week';
    setHistoryFilter: (filter: 'today' | 'week') => void;
}

const ORDER_TYPE_MAP = ['UNK', 'LMT', 'MKT', 'STL', 'STP', 'TRL'];
const ORDER_STATUS_MAP = ['NONE', 'OPEN', 'FILLED', 'CXLD', 'EXP', 'REJ', 'PEND'];

const PERIOD_OPTIONS = [
    { value: 'today', label: 'Today' },
    { value: 'week', label: '7 Days' },
] as const;

/** status code -> Badge variant, matching ORDER_STATUS_MAP semantics */
function statusBadgeVariant(status: number): 'info' | 'warning' | 'neutral' {
    if (status === 2) return 'info';    // FILLED
    if (status === 1) return 'warning'; // OPEN
    return 'neutral';                   // CXLD / EXP / REJ / PEND / unknown
}

export function OrdersTable({
    orders,
    historyFilter,
    setHistoryFilter,
}: OrdersTableProps) {
    const sortedOrders = [...orders].sort(
        (a, b) => new Date(b.creationTimestamp).getTime() - new Date(a.creationTimestamp).getTime()
    );

    return (
        <Card>
            <CardHeader
                icon={TrendingUp}
                title="Order History"
                annotation={orders.length > 0 ? `${orders.length}` : undefined}
                actions={
                    <SegmentedControl
                        options={PERIOD_OPTIONS}
                        value={historyFilter}
                        onChange={setHistoryFilter}
                        aria-label="Order history period"
                    />
                }
            />

            {orders.length === 0 ? (
                <EmptyState
                    icon={ListOrdered}
                    title="No orders found"
                    hint="Orders placed by the bot will appear here."
                />
            ) : (
            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead>
                        <tr className="table-header">
                            <th className="table-cell text-left">Time</th>
                            <th className="table-cell text-left">Symbol</th>
                            <th className="table-cell text-center">Side</th>
                            <th className="table-cell num">Qty</th>
                            <th className="table-cell text-center">Type</th>
                            <th className="table-cell num">Stop</th>
                            <th className="table-cell num">Limit</th>
                            <th className="table-cell num">Filled</th>
                            <th className="table-cell text-center">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sortedOrders.map((order, index) => (
                            <tr
                                key={order.id}
                                className="table-row animate-stagger"
                                style={{ '--i': index } as CSSProperties}
                            >
                                <td className="table-cell text-slate-500 font-mono text-xs">
                                    {formatInUserTz(order.creationTimestamp, 'MM/dd HH:mm:ss')}
                                </td>
                                <td className="table-cell font-bold text-white">{order.symbolId}</td>
                                <td className="table-cell text-center">
                                    <Badge variant={order.side === 0 ? 'success' : 'danger'} dot>
                                        {order.side === 0 ? 'BUY' : 'SELL'}
                                    </Badge>
                                </td>
                                <td className="table-cell num">{order.size}</td>
                                <td className="table-cell text-center">
                                    <Badge variant="neutral">{ORDER_TYPE_MAP[order.type] || order.type}</Badge>
                                </td>
                                <td className="table-cell num text-slate-400">
                                    {order.stopPrice ? order.stopPrice.toFixed(2) : '-'}
                                </td>
                                <td className="table-cell num text-slate-400">
                                    {order.limitPrice ? order.limitPrice.toFixed(2) : '-'}
                                </td>
                                <td className="table-cell num text-slate-400">
                                    {order.filledPrice ? order.filledPrice.toFixed(2) : '-'}
                                </td>
                                <td className="table-cell text-center">
                                    <Badge variant={statusBadgeVariant(order.status)}>
                                        {ORDER_STATUS_MAP[order.status] || order.status}
                                    </Badge>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            )}
        </Card>
    );
}
