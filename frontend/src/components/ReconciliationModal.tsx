import { useState } from 'react';
import { X, RefreshCw, Check, AlertTriangle } from 'lucide-react';

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
    const pnlChangeClass = totalPnlChange >= 0 ? 'text-green-400' : 'text-red-400';

    return (
        <div className="fixed inset-0 z-50 h-screen w-screen flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden animate-fade-in">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-800">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-500/20 rounded-lg">
                            <RefreshCw className="w-5 h-5 text-indigo-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Trade Reconciliation</h2>
                            <p className="text-sm text-slate-400">Review proposed changes before applying</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
                        disabled={applying || isLoading}
                    >
                        <X className="w-5 h-5 text-slate-400" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto max-h-[50vh]">
                    {isLoading ? (
                        <div className="flex flex-col items-center justify-center py-12">
                            <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mb-4" />
                            <p className="text-slate-400">Analyzing trades...</p>
                        </div>
                    ) : !hasChanges ? (
                        <div className="flex flex-col items-center justify-center py-12">
                            <Check className="w-12 h-12 text-green-400 mb-4" />
                            <p className="text-lg font-semibold text-white mb-2">All trades are synchronized</p>
                            <p className="text-slate-400 text-sm">No discrepancies found between dashboard and TopStep</p>
                        </div>
                    ) : (
                        <>
                            {/* Summary */}
                            <div className="grid grid-cols-4 gap-4 mb-6">
                                <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                                    <p className="text-2xl font-bold text-green-400">{summary?.trades_to_create || 0}</p>
                                    <p className="text-xs text-slate-400 mt-1">Found Missing</p>
                                </div>
                                <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                                    <p className="text-2xl font-bold text-orange-400">{summary?.trades_to_close || 0}</p>
                                    <p className="text-xs text-slate-400 mt-1">To Close</p>
                                </div>
                                <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                                    <p className="text-2xl font-bold text-blue-400">{summary?.pnl_updates || 0}</p>
                                    <p className="text-xs text-slate-400 mt-1">PnL Updates</p>
                                </div>
                                <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                                    <p className={`text-2xl font-bold ${pnlChangeClass}`}>
                                        {totalPnlChange >= 0 ? '+' : ''}${totalPnlChange.toFixed(2)}
                                    </p>
                                    <p className="text-xs text-slate-400 mt-1">Net PnL Change</p>
                                </div>
                            </div>

                            {/* Changes Table */}
                            <div className="border border-slate-700 rounded-xl overflow-hidden">
                                <table className="w-full text-sm">
                                    <thead className="bg-slate-800/50">
                                        <tr>
                                            <th className="text-left text-slate-400 text-xs uppercase py-3 px-4">Trade</th>
                                            <th className="text-left text-slate-400 text-xs uppercase py-3 px-4">Type</th>
                                            <th className="text-right text-slate-400 text-xs uppercase py-3 px-4">Old PnL</th>
                                            <th className="text-right text-slate-400 text-xs uppercase py-3 px-4">New PnL</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-800">
                                        {changes.map((change, idx) => (
                                            <tr key={change.trade_id || idx} className="hover:bg-slate-800/30">
                                                <td className="py-3 px-4">
                                                    <span className="font-mono text-white">#{change.trade_id || 'NEW'}</span>
                                                    <span className="text-slate-400 ml-2">{change.ticker}</span>
                                                </td>
                                                <td className="py-3 px-4">
                                                    <span className={`px-2 py-1 rounded text-xs font-bold ${change.type === 'create' ? 'bg-green-500/20 text-green-400' :
                                                            change.type === 'delete' ? 'bg-red-500/20 text-red-500' :
                                                                change.type === 'close' ? 'bg-orange-500/20 text-orange-400' :
                                                                    'bg-blue-500/20 text-blue-400'
                                                        }`}>
                                                        {change.type.toUpperCase().replace('_', ' ')}
                                                    </span>
                                                </td>
                                                <td className="py-3 px-4 text-right font-mono text-slate-400">
                                                    {change.old_pnl != null ? `$${Number(change.old_pnl).toFixed(2)}` : '-'}
                                                </td>
                                                <td className={`py-3 px-4 text-right font-mono font-bold ${(change.new_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                                                    }`}>
                                                    {change.new_pnl != null ? `$${Number(change.new_pnl).toFixed(2)}` : '-'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {/* Warning */}
                            <div className="mt-4 flex items-start gap-3 bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4">
                                <AlertTriangle className="w-5 h-5 text-yellow-500 shrink-0 mt-0.5" />
                                <p className="text-sm text-yellow-200/80">
                                    These changes will update your local trade records to match TopStep data.
                                    This action cannot be undone.
                                </p>
                            </div>
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-3 p-6 border-t border-slate-800 bg-slate-900/50">
                    <button
                        onClick={onClose}
                        className="px-5 py-2.5 rounded-xl font-semibold text-slate-300 hover:bg-slate-800 transition-colors"
                        disabled={applying}
                    >
                        {hasChanges ? 'Cancel' : 'Close'}
                    </button>
                    {hasChanges && (
                        <button
                            onClick={handleApply}
                            disabled={applying || isLoading}
                            className="px-5 py-2.5 rounded-xl font-semibold bg-indigo-600 hover:bg-indigo-700 text-white transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {applying ? (
                                <>
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                    Applying...
                                </>
                            ) : (
                                <>
                                    <Check className="w-4 h-4" />
                                    Apply Changes
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
