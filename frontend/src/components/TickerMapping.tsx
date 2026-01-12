import { useState } from 'react';
import { Trash2, Plus, RefreshCw, Layers } from 'lucide-react';
import { API_BASE } from '../config';
import type { TickerMap } from '../types';

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
                <h4 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                    <Layers className="w-4 h-4 text-slate-400" />
                    Ticker Mappings
                </h4>
                <button
                    onClick={fetchContracts}
                    disabled={loadingContracts}
                    className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg flex items-center gap-2 transition-colors"
                >
                    <RefreshCw className={`w-3 h-3 ${loadingContracts ? 'animate-spin' : ''}`} />
                    {availableContracts.length > 0 ? 'Refetch Contracts' : 'Load Contracts'}
                </button>
            </div>

            {/* Add New Mapping Form */}
            <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex flex-col gap-3">
                <div className="flex gap-2">
                    <input
                        type="text"
                        placeholder="TradingView Ticker (e.g. MNQ1!)"
                        value={tvTicker}
                        onChange={(e) => setTvTicker(e.target.value)}
                        className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
                    />
                </div>

                <div className="flex gap-2">
                    <select
                        value={selectedContract}
                        onChange={(e) => setSelectedContract(e.target.value)}
                        disabled={availableContracts.length === 0}
                        className="flex-1 min-w-0 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono disabled:opacity-50 truncate"
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

                    <input
                        type="number"
                        value={microEquivalent}
                        onChange={(e) => setMicroEquivalent(Math.max(1, parseInt(e.target.value) || 1))}
                        className="w-14 bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-sm text-white text-center focus:outline-none focus:border-indigo-500 font-mono"
                        min="1"
                        title="Micro equivalent (1=micro, 10=mini)"
                    />

                    <button
                        onClick={handleAdd}
                        disabled={!tvTicker || !selectedContract || adding}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 rounded-lg flex items-center gap-1 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
                    >
                        <Plus size={16} /> Add
                    </button>
                </div>
            </div>

            {/* List */}
            <div className="space-y-2 pr-2">
                {mappings.map((m) => (
                    <div key={m.id} className="flex justify-between items-center bg-slate-900/50 p-2.5 rounded-lg border border-slate-800/50 hover:border-slate-700 transition-colors">
                        <div className="flex items-center gap-3">
                            <span className="font-mono text-indigo-400 font-bold text-sm w-20 truncate" title={m.tv_ticker}>{m.tv_ticker}</span>
                            <span className="text-slate-600 text-xs">→</span>
                            <div className="flex flex-col">
                                <span className="font-mono text-white text-sm font-bold">{m.ts_ticker}</span>
                                <span className="text-[10px] text-slate-500">
                                    Tick: {m.tick_size} / ${m.tick_value}
                                </span>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="flex items-center gap-1">
                                <span className="text-[10px] text-slate-500">×</span>
                                <input
                                    type="number"
                                    value={m.micro_equivalent}
                                    onChange={(e) => {
                                        const val = parseInt(e.target.value) || 1;
                                        if (onUpdate && val >= 1) {
                                            onUpdate(m.id, { micro_equivalent: val });
                                        }
                                    }}
                                    className="w-10 bg-slate-800 border border-slate-700 rounded px-1 py-0.5 text-xs text-white text-center focus:outline-none focus:border-indigo-500 font-mono"
                                    min="1"
                                    title="Micro equivalent (1=micro, 10=mini)"
                                />
                            </div>
                            <button
                                onClick={() => onDelete(m.id)}
                                className="p-1.5 hover:bg-red-500/10 text-slate-500 hover:text-red-400 rounded-lg transition-colors"
                            >
                                <Trash2 size={14} />
                            </button>
                        </div>
                    </div>
                ))}

                {mappings.length === 0 && (
                    <p className="text-xs text-slate-500 italic text-center py-4">
                        No mappings configured. The bot will try to auto-resolve tickers.
                    </p>
                )}
            </div>
        </div>
    );
}
