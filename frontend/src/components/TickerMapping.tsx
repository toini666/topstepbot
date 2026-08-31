import { useState } from 'react';
import { Trash2, Plus, RefreshCw, Layers } from 'lucide-react';
import { API_BASE } from '../config';
import type { TickerMap } from '../types';
import { Button, EmptyState } from './ui';

interface TickerMappingProps {
    mappings: TickerMap[];
    onAdd: (mapping: Omit<TickerMap, 'id'>) => Promise<void>;
    onDelete: (id: number) => Promise<void>;
    onUpdate?: (id: number, updates: Partial<TickerMap>) => Promise<void>;
}

export function TickerMapping({ mappings, onAdd, onDelete, onUpdate }: TickerMappingProps) {
    const [tvTicker, setTvTicker] = useState('');
    const [selectedContract, setSelectedContract] = useState(''); // Stores JSON string of contract details
    const [microEquivalent, setMicroEquivalent] = useState(1);
    const [availableContracts, setAvailableContracts] = useState<any[]>([]);
    const [loadingContracts, setLoadingContracts] = useState(false);
    const [adding, setAdding] = useState(false);

    const fetchContracts = async () => {
        setLoadingContracts(true);
        try {
            const response = await fetch(`${API_BASE}/settings/contracts/available`);
            if (response.ok) {
                const data = await response.json();
                setAvailableContracts(data || []);
            }
        } catch (error) {
            console.error("Failed to fetch contracts", error);
        } finally {
            setLoadingContracts(false);
        }
    };

    const handleAdd = async () => {
        if (!tvTicker || !selectedContract) return;

        setAdding(true);
        try {
            const contract = JSON.parse(selectedContract);
            await onAdd({
                tv_ticker: tvTicker,
                ts_contract_id: contract.id, // e.g. CON.F.US.MNQ.H26
                ts_ticker: contract.name,    // e.g. MNQH6
                tick_size: contract.tickSize,
                tick_value: contract.tickValue,
                micro_equivalent: microEquivalent
            } as any); // Type assertion for Omit
            setTvTicker('');
            setSelectedContract('');
            setMicroEquivalent(1);
        } catch (e) {
            console.error(e);
        } finally {
            setAdding(false);
        }
    };

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <Layers className="w-4 h-4 text-indigo-400" />
                    Ticker Mappings
                </h4>
                <Button
                    variant="outline"
                    icon={RefreshCw}
                    loading={loadingContracts}
                    onClick={fetchContracts}
                    className="!px-3 !py-1.5 !text-xs"
                >
                    {availableContracts.length > 0 ? 'Refetch Contracts' : 'Load Contracts'}
                </Button>
            </div>

            {/* Add New Mapping Form */}
            <div className="well p-3 flex flex-col gap-3">
                <input
                    type="text"
                    placeholder="TradingView Ticker (e.g. MNQ1!)"
                    value={tvTicker}
                    onChange={(e) => setTvTicker(e.target.value)}
                    className="input-mono"
                />

                <div className="flex gap-2">
                    <select
                        value={selectedContract}
                        onChange={(e) => setSelectedContract(e.target.value)}
                        disabled={availableContracts.length === 0}
                        className="flex-1 min-w-0 input-mono disabled:opacity-50 truncate"
                    >
                        <option value="">
                            {availableContracts.length === 0 ? "Load contracts first..." : "Select TopStep Contract..."}
                        </option>
                        {availableContracts.map((c: any) => (
                            <option key={c.id} value={JSON.stringify(c)}>
                                {c.name} ({c.description}) - Tick: {c.tickSize} / ${c.tickValue}
                            </option>
                        ))}
                    </select>

                    <div className="w-16 shrink-0">
                        <input
                            type="number"
                            value={microEquivalent}
                            onChange={(e) => setMicroEquivalent(Math.max(1, parseInt(e.target.value) || 1))}
                            className="input-mono text-center px-2 py-2 text-sm"
                            min="1"
                            title="Micro equivalent (1=micro, 10=mini)"
                        />
                    </div>

                    <Button
                        variant="primary"
                        icon={Plus}
                        loading={adding}
                        disabled={!tvTicker || !selectedContract}
                        onClick={handleAdd}
                        className="shrink-0"
                    >
                        Add
                    </Button>
                </div>
                <p className="help-text -mt-1">Micro equivalent: 1 for a micro contract, 10 for a mini.</p>
            </div>

            {/* List */}
            {mappings.length > 0 ? (
                <div className="overflow-x-auto custom-scrollbar">
                    <table className="w-full text-sm text-left">
                        <thead>
                            <tr className="table-header">
                                <th className="table-cell font-semibold">TV Ticker</th>
                                <th className="table-cell font-semibold">TS Contract</th>
                                <th className="table-cell font-semibold text-right">Tick Size</th>
                                <th className="table-cell font-semibold text-right">Tick Value</th>
                                <th className="table-cell font-semibold text-right">Micro</th>
                                <th className="table-cell font-semibold text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {mappings.map((m, i) => (
                                <tr
                                    key={m.id}
                                    className="table-row animate-stagger"
                                    style={{ '--i': i } as React.CSSProperties}
                                >
                                    <td className="table-cell">
                                        <span className="font-mono text-indigo-300 font-semibold text-sm" title={m.tv_ticker}>
                                            {m.tv_ticker}
                                        </span>
                                    </td>
                                    <td className="table-cell">
                                        <span className="font-mono text-slate-100 text-sm">{m.ts_ticker}</span>
                                    </td>
                                    <td className="table-cell num text-slate-400">{m.tick_size}</td>
                                    <td className="table-cell num text-slate-400">${m.tick_value}</td>
                                    <td className="table-cell num">
                                        <div className="w-14 ml-auto">
                                            <input
                                                type="number"
                                                value={m.micro_equivalent}
                                                onChange={(e) => {
                                                    const val = parseInt(e.target.value) || 1;
                                                    if (onUpdate && val >= 1) {
                                                        onUpdate(m.id, { micro_equivalent: val });
                                                    }
                                                }}
                                                className="input-mono text-right px-2 py-1 text-xs"
                                                min="1"
                                                title="Micro equivalent (1=micro, 10=mini)"
                                            />
                                        </div>
                                    </td>
                                    <td className="table-cell text-right">
                                        <button
                                            onClick={() => onDelete(m.id)}
                                            className="inline-flex items-center justify-center p-1.5 rounded-lg text-slate-500 hover:text-red-300 hover:bg-red-500/15 transition-colors"
                                            aria-label={`Delete mapping ${m.tv_ticker}`}
                                        >
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <EmptyState
                    icon={Layers}
                    title="No ticker mappings configured"
                    hint="The bot will try to auto-resolve tickers."
                />
            )}
        </div>
    );
}
