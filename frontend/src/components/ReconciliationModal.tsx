import { useState } from 'react';
import type { CSSProperties } from 'react';
import { RefreshCw, Check, AlertTriangle, X } from 'lucide-react';
import { Stat, Badge, EmptyState, Spinner, Button } from './ui';

interface ReconciliationChange {
    trade_id?: number;
    ticker: string;
    type: 'close' | 'pnl_update' | 'create' | 'delete';
    description: string;
    old_status?: string;
    new_status?: string;
    old_pnl?: number;
    new_pnl?: number;
    new_exit_price?: number;
    new_fees?: number;
    old_fees?: number;
}

interface ReconciliationSummary {
    trades_to_create?: number;
    trades_to_close: number;
    trades_to_delete?: number;
    pnl_updates: number;
    total_pnl_change: number;
}

interface ReconciliationModalProps {
    isOpen: boolean;
    onClose: () => void;
    changes: ReconciliationChange[];
    summary: ReconciliationSummary;
    onApply: () => Promise<void>;
    isLoading: boolean;
}

type BadgeVariant = 'success' | 'danger' | 'warning' | 'info' | 'neutral' | 'violet';

const typeBadgeVariant = (type: ReconciliationChange['type']): BadgeVariant => {
    if (type === 'create') return 'success';
    if (type === 'delete') return 'danger';
    if (type === 'close') return 'warning';
    return 'info';
};

export default function ReconciliationModal({
    isOpen,
    onClose,
    changes,
    summary,
    onApply,
    isLoading
}: ReconciliationModalProps) {
    const [applying, setApplying] = useState(false);

    if (!isOpen) return null;

    const handleApply = async () => {
        setApplying(true);
        try {
            await onApply();
        } finally {
            setApplying(false);
        }
    };

    const hasChanges = changes.length > 0;
    const totalPnlChange = summary?.total_pnl_change ?? 0;

    return (
        <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="reconciliation-title">
            <div
                className="modal-container w-full max-w-2xl max-h-[80vh] flex flex-col"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-800/60 shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-indigo-500/10 ring-1 ring-indigo-400/30">
                            <RefreshCw className="w-5 h-5 text-indigo-400" />
                        </div>
                        <div>
                            <h2 id="reconciliation-title" className="text-xl font-bold text-white tracking-tight">Trade Reconciliation</h2>
                            <p className="text-sm text-slate-400">Review proposed changes before applying</p>
                        </div>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        icon={X}
                        onClick={onClose}
                        disabled={applying || isLoading}
                        aria-label="Close dialog"
                        className="!p-2"
                    />
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto custom-scrollbar">
                    {isLoading ? (
                        <div className="flex flex-col items-center justify-center py-12 gap-4">
                            <Spinner size="lg" />
                            <p className="text-slate-400">Analyzing trades...</p>
                        </div>
                    ) : !hasChanges ? (
                        <EmptyState
                            icon={Check}
                            title="All trades are synchronized"
                            hint="No discrepancies found between dashboard and TopStep"
                        />
                    ) : (
                        <>
                            {/* Summary */}
                            <div className="grid grid-cols-2 gap-3 mb-6">
                                <Stat label="Found Missing" value={summary?.trades_to_create || 0} tone="neutral" />
                                <Stat label="To Close" value={summary?.trades_to_close || 0} tone="neutral" />
                                <Stat label="PnL Updates" value={summary?.pnl_updates || 0} tone="neutral" />
                                <Stat
                                    label="Net PnL Change"
                                    value={`${totalPnlChange >= 0 ? '+' : ''}$${totalPnlChange.toFixed(2)}`}
                                    tone={totalPnlChange >= 0 ? 'up' : 'down'}
                                />
                            </div>

                            {/* Changes Table */}
                            <div className="border border-slate-800/60 rounded-xl overflow-hidden">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="table-header">
                                            <th className="table-cell text-left">Trade</th>
                                            <th className="table-cell text-left">Type</th>
                                            <th className="table-cell num">Old PnL</th>
                                            <th className="table-cell num">New PnL</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {changes.map((change, idx) => (
                                            <tr
                                                key={change.trade_id || idx}
                                                className="table-row animate-stagger"
                                                style={{ '--i': idx } as CSSProperties}
                                            >
                                                <td className="table-cell">
                                                    <span className="font-mono text-white">#{change.trade_id || 'NEW'}</span>
                                                    <span className="text-slate-400 ml-2">{change.ticker}</span>
                                                </td>
                                                <td className="table-cell">
                                                    <Badge variant={typeBadgeVariant(change.type)}>
                                                        {change.type.toUpperCase().replace('_', ' ')}
                                                    </Badge>
                                                </td>
                                                <td className="table-cell num text-slate-400">
                                                    {change.old_pnl != null ? `$${Number(change.old_pnl).toFixed(2)}` : '-'}
                                                </td>
                                                <td className={`table-cell num font-bold ${(change.new_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                    {change.new_pnl != null ? `$${Number(change.new_pnl).toFixed(2)}` : '-'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {/* Warning */}
                            <div className="mt-4 flex items-start gap-3 bg-amber-500/10 ring-1 ring-inset ring-amber-400/20 rounded-xl p-4">
                                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                                <p className="text-sm text-amber-200/80 leading-relaxed">
                                    These changes will update your local trade records to match TopStep data.
                                    This action cannot be undone.
                                </p>
                            </div>
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-3 p-6 border-t border-slate-800/60 shrink-0">
                    <button
                        onClick={onClose}
                        className="btn-ghost"
                        disabled={applying}
                    >
                        {hasChanges ? 'Cancel' : 'Close'}
                    </button>
                    {hasChanges && (
                        <Button
                            variant="primary"
                            icon={Check}
                            loading={applying}
                            disabled={isLoading}
                            onClick={handleApply}
                        >
                            {applying ? 'Applying...' : 'Apply Changes'}
                        </Button>
                    )}
                </div>
            </div>
        </div>
    );
}
