/**
 * Orphaned Orders Warning Component
 * 
 * Displays a warning banner when there are active orders without matching positions.
 */

import { AlertTriangle } from 'lucide-react';
import type { Order, Account, Position } from '../../types';

interface OrphanedOrdersWarningProps {
    accounts: Account[];
    ordersByAccount: Record<number, Order[]>;
    positionsByAccount: Record<number, Position[]>;
}

export function OrphanedOrdersWarning({
    accounts,
    ordersByAccount,
    positionsByAccount,
}: OrphanedOrdersWarningProps) {
    // Detect orphaned orders across ALL accounts
    const orphanedOrders: Array<Order & { accountName: string }> = [];

    for (const account of accounts) {
        const accountOrders = ordersByAccount[account.id] || [];
        const accountPositions = positionsByAccount[account.id] || [];

        for (const order of accountOrders) {
            if ((order.status === 1 || order.status === 6) &&
                !accountPositions.some(p => p.contractId === order.contractId)) {
                orphanedOrders.push({ ...order, accountName: account.name });
            }
        }
    }

    if (orphanedOrders.length === 0) {
        return null;
    }

    return (
        <div className="max-w-7xl mx-auto mb-6 bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 flex items-center gap-4 animate-fade-in">
            <div className="bg-yellow-500/20 p-2 rounded-lg shrink-0">
                <AlertTriangle className="w-6 h-6 text-yellow-500" />
            </div>
            <div className="flex-1">
                <h3 className="text-yellow-500 font-bold mb-1">Warning: Active Orders without Position</h3>
                <p className="text-yellow-200/80 text-sm">
                    You have <strong>{orphanedOrders.length}</strong> working order(s) for contracts where you have no open position.
                    These orders may execute unexpectedly.
                </p>
                <div className="flex flex-wrap gap-2 mt-2">
                    {orphanedOrders.map(o => (
                        <span key={`${o.accountId}-${o.id}`} className="text-xs bg-yellow-900/50 text-yellow-200 px-2 py-1 rounded font-mono border border-yellow-700/50">
                            {o.symbolId} ({o.side === 0 ? 'BUY' : 'SELL'}) <span className="text-yellow-400">@{o.accountName}</span>
                        </span>
                    ))}
                </div>
            </div>
        </div>
    );
}
