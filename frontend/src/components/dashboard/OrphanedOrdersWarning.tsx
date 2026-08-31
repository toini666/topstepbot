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
        <div
            className="max-w-7xl mx-auto mb-6 rounded-2xl p-4 flex items-center gap-4 animate-fade-in bg-amber-500/5 border border-amber-400/20"
            role="alert"
        >
            <div className="relative bg-amber-500/15 p-2 rounded-lg shrink-0">
                <AlertTriangle className="w-6 h-6 text-amber-400" aria-hidden="true" />
                <span className="lamp lamp-amber lamp-live absolute -top-0.5 -right-0.5" aria-hidden="true" />
            </div>
            <div className="flex-1">
                <h3 className="text-amber-300 font-bold mb-1">Warning: Active Orders without Position</h3>
                <p className="text-amber-100/70 text-sm">
                    You have <strong>{orphanedOrders.length}</strong> working order(s) for contracts where you have no open position.
                    These orders may execute unexpectedly.
                </p>
                <div className="flex flex-wrap gap-2 mt-2">
                    {orphanedOrders.map(o => (
                        <span key={`${o.accountId}-${o.id}`} className="text-xs bg-amber-950/40 text-amber-200 px-2 py-1 rounded-md font-mono border border-amber-700/30">
                            {o.symbolId} ({o.side === 0 ? 'BUY' : 'SELL'}) <span className="text-amber-400">@{o.accountName}</span>
                        </span>
                    ))}
                </div>
            </div>
        </div>
    );
}
