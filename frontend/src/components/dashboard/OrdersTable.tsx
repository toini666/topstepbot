/**
 * Orders Table Component
 * 
 * Displays order history with time period filtering.
 */

import { TrendingUp } from 'lucide-react';
import { format } from 'date-fns';
import type { Order } from '../../types';

interface OrdersTableProps {
    orders: Order[];
    historyFilter: 'today' | 'week';
    setHistoryFilter: (filter: 'today' | 'week') => void;
}

const ORDER_TYPE_MAP = ['UNK', 'LMT', 'MKT', 'STL', 'STP', 'TRL'];
const ORDER_STATUS_MAP = ['NONE', 'OPEN', 'FILLED', 'CXLD', 'EXP', 'REJ', 'PEND'];

export function OrdersTable({
    orders,
    historyFilter,
    setHistoryFilter,
}: OrdersTableProps) {
    const sortedOrders = [...orders].sort(
        (a, b) => new Date(b.creationTimestamp).getTime() - new Date(a.creationTimestamp).getTime()
    );

    return (
        <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-indigo-400" />
                Order History
                <div className="ml-auto flex bg-slate-800 rounded-lg p-1 text-xs font-medium">
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
                </div>
            </h2>

            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead className="text-slate-500 border-b border-slate-800 uppercase text-xs">
                        <tr>
                            <th className="py-3 px-4">Time</th>
                            <th className="py-3 px-4">Symbol</th>
                            <th className="py-3 px-4 text-center">Side</th>
                            <th className="py-3 px-4 text-center">Qty</th>
                            <th className="py-3 px-4 text-center">Type</th>
                            <th className="py-3 px-4 text-right">Stop</th>
                            <th className="py-3 px-4 text-right">Limit</th>
                            <th className="py-3 px-4 text-right">Filled</th>
                            <th className="py-3 px-4 text-center">Status</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                        {sortedOrders.map((order) => (
                            <tr key={order.id} className="hover:bg-slate-800/30 transition-colors">
                                <td className="py-3 px-4 text-slate-500 font-mono text-xs">
                                    {format(new Date(order.creationTimestamp), 'MM/dd HH:mm:ss')}
                                </td>
                                <td className="py-3 px-4 font-bold text-white">{order.symbolId}</td>
                                <td className="py-3 px-4 text-center">
                                    <span className={`px-2 py-1 rounded-md text-xs font-bold ${order.side === 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                                        }`}>
                                        {order.side === 0 ? 'BUY' : 'SELL'}
                                    </span>
                                </td>
                                <td className="py-3 px-4 text-center font-mono">{order.size}</td>
                                <td className="py-3 px-4 text-center font-mono text-xs text-slate-400">
                                    {ORDER_TYPE_MAP[order.type] || order.type}
                                </td>
                                <td className="py-3 px-4 text-right font-mono text-slate-400">
                                    {order.stopPrice ? order.stopPrice.toFixed(2) : '-'}
                                </td>
                                <td className="py-3 px-4 text-right font-mono text-slate-400">
                                    {order.limitPrice ? order.limitPrice.toFixed(2) : '-'}
                                </td>
                                <td className="py-3 px-4 text-right font-mono text-slate-400">
                                    {order.filledPrice ? order.filledPrice.toFixed(2) : '-'}
                                </td>
                                <td className="py-3 px-4 text-center">
                                    <span className={`px-2 py-1 rounded-md text-xs font-bold ${order.status === 2 ? 'bg-blue-500/20 text-blue-400' :
                                        order.status === 3 ? 'bg-slate-700 text-slate-400' :
                                            order.status === 1 ? 'bg-yellow-500/20 text-yellow-400' :
                                                'bg-slate-800 text-slate-500'
                                        }`}>
                                        {ORDER_STATUS_MAP[order.status] || order.status}
                                    </span>
                                </td>
                            </tr>
                        ))}
                        {orders.length === 0 && (
                            <tr>
                                <td colSpan={9} className="py-8 text-center text-slate-500 italic">No orders found.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}
