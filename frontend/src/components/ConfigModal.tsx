import { useState, useEffect } from 'react';
import axios from 'axios';
import { X, Save, Plus, Trash2, Clock, DollarSign, Settings } from 'lucide-react';
import { toast } from 'sonner';
import type { Config, TimeBlock, TickerMap } from '../types';
import { TickerMapping } from './TickerMapping';
import { API_BASE } from '../config';

interface ConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
    config: Config;
    onSave: (newConfig: Partial<Config>) => Promise<void>;
}

export function ConfigModal({
    isOpen,
    onClose,
    config,
    onSave
}: ConfigModalProps) {
    const [activeTab, setActiveTab] = useState<'general' | 'mappings'>('general');
    const [riskAmount, setRiskAmount] = useState(200);
    const [blockedPeriodsEnabled, setBlockedPeriodsEnabled] = useState(true);
    const [blockedPeriods, setBlockedPeriods] = useState<TimeBlock[]>([]);
    const [autoFlattenEnabled, setAutoFlattenEnabled] = useState(false);
    const [autoFlattenTime, setAutoFlattenTime] = useState("21:55");
    const [saving, setSaving] = useState(false);

    // Mappings State
    const [mappings, setMappings] = useState<TickerMap[]>([]);

    useEffect(() => {
        if (isOpen) {
            setRiskAmount(config.risk_per_trade);
            setBlockedPeriodsEnabled(config.blocked_periods_enabled);
            setBlockedPeriods([...config.blocked_periods]);
            setAutoFlattenEnabled(config.auto_flatten_enabled ?? false);
            setAutoFlattenTime(config.auto_flatten_time || "21:55");
            fetchMappings();
        }
    }, [isOpen]);





    const fetchMappings = async () => {
        try {
            const res = await axios.get(`${API_BASE}/settings/ticker-map`);
            if (res.data.success) {
                setMappings(res.data.data);
            }
        } catch (e) {
            console.error("Failed to fetch mappings", e);
        }
    };

    const addMapping = async (mapping: Omit<TickerMap, 'id'>) => {
        try {
            const res = await axios.post(`${API_BASE}/settings/ticker-map`, {
                tv_ticker: mapping.tv_ticker,
                ts_contract_id: mapping.ts_contract_id,
                ts_ticker: mapping.ts_ticker,
                tick_size: mapping.tick_size,
                tick_value: mapping.tick_value
            });
            if (res.data.success) {
                toast.success("Mapping Added");
                fetchMappings();
            } else {
                toast.error(res.data.message || "Failed to add mapping");
            }
        } catch (e) {
            console.error("Failed to add mapping", e);
            toast.error("Error adding mapping");
        }
    };

    const deleteMapping = async (id: number) => {
        try {
            const res = await axios.delete(`${API_BASE}/settings/ticker-map/${id}`);
            if (res.data.success) {
                toast.success("Mapping Deleted");
                fetchMappings();
            } else {
                toast.error(res.data.message || "Failed to delete mapping");
            }
        } catch (e) {
            console.error("Failed to delete mapping", e);
            toast.error("Error deleting mapping");
        }
    };

    if (!isOpen) return null;

    const handleSave = async () => {
        setSaving(true);
        await onSave({
            risk_per_trade: riskAmount,
            blocked_periods_enabled: blockedPeriodsEnabled,
            blocked_periods: blockedPeriods,
            auto_flatten_enabled: autoFlattenEnabled,
            auto_flatten_time: autoFlattenTime
        });
        setSaving(false);
        onClose();
    };

    const addTimeBlock = () => {
        setBlockedPeriods([...blockedPeriods, { start: "00:00", end: "00:00" }]);
    };

    const removeTimeBlock = (index: number) => {
        const newBlocks = [...blockedPeriods];
        newBlocks.splice(index, 1);
        setBlockedPeriods(newBlocks);
    };

    const updateTimeBlock = (index: number, field: 'start' | 'end', value: string) => {
        const newBlocks = [...blockedPeriods];
        newBlocks[index] = { ...newBlocks[index], [field]: value };
        setBlockedPeriods(newBlocks);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div
                className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl relative overflow-hidden animate-in zoom-in-95 duration-200 flex flex-col max-h-[90vh]"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-slate-800 bg-slate-900/50 shrink-0">
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        <Settings className="w-5 h-5 text-indigo-400" />
                        Settings
                    </h3>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-slate-800 bg-slate-950/30 px-6 shrink-0">
                    <button
                        onClick={() => setActiveTab('general')}
                        className={`py-3 px-4 text-sm font-medium border-b-2 transition-colors ${activeTab === 'general'
                            ? 'border-indigo-500 text-white'
                            : 'border-transparent text-slate-400 hover:text-white'
                            }`}
                    >
                        General
                    </button>
                    <button
                        onClick={() => setActiveTab('mappings')}
                        className={`py-3 px-4 text-sm font-medium border-b-2 transition-colors ${activeTab === 'mappings'
                            ? 'border-indigo-500 text-white'
                            : 'border-transparent text-slate-400 hover:text-white'
                            }`}
                    >
                        Ticker Mappings
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto custom-scrollbar">
                    {activeTab === 'general' ? (
                        <div className="space-y-6">
                            {/* Risk Section */}
                            <div className="space-y-3">
                                <label className="text-sm font-semibold text-slate-300 block">Risk Per Trade ($)</label>
                                <div className="relative">
                                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                    <input
                                        type="number"
                                        value={riskAmount}
                                        onChange={(e) => setRiskAmount(parseFloat(e.target.value) || 0)}
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2 pl-9 pr-4 text-white focus:outline-none focus:border-indigo-500 transition-colors font-mono"
                                        min="1"
                                    />
                                </div>
                            </div>

                            {/* Time Blocks Section */}
                            <div className={`space-y-3 transition-opacity duration-200 ${!blockedPeriodsEnabled ? "opacity-50" : ""}`}>
                                <div className="flex justify-between items-center">
                                    <div className="flex items-center gap-3">
                                        <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                                            <Clock className="w-4 h-4 text-slate-400" />
                                            Blocked Trading Hours
                                        </label>
                                        <button
                                            onClick={() => setBlockedPeriodsEnabled(!blockedPeriodsEnabled)}
                                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${blockedPeriodsEnabled ? 'bg-indigo-500' : 'bg-slate-700'
                                                }`}
                                        >
                                            <span
                                                className={`${blockedPeriodsEnabled ? 'translate-x-5' : 'translate-x-1'
                                                    } inline-block h-3 w-3 transform rounded-full bg-white transition-transform`}
                                            />
                                        </button>
                                        <span className="text-xs text-slate-500 font-mono">
                                            {blockedPeriodsEnabled ? "Active" : "Disabled"}
                                        </span>
                                    </div>
                                    <button
                                        onClick={addTimeBlock}
                                        disabled={!blockedPeriodsEnabled}
                                        className="text-xs bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 px-2 py-1 rounded-lg flex items-center gap-1 transition-colors font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        <Plus size={12} /> Add
                                    </button>
                                </div>

                                <div className="space-y-2 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
                                    {blockedPeriods.map((block, index) => (
                                        <div key={index} className="flex items-center gap-2 bg-slate-950 p-2 rounded-xl border border-slate-800">
                                            <input
                                                type="time"
                                                value={block.start}
                                                onChange={(e) => updateTimeBlock(index, 'start', e.target.value)}
                                                className="bg-transparent text-white font-mono text-sm focus:outline-none w-20 text-center"
                                            />
                                            <span className="text-slate-500">-</span>
                                            <input
                                                type="time"
                                                value={block.end}
                                                onChange={(e) => updateTimeBlock(index, 'end', e.target.value)}
                                                className="bg-transparent text-white font-mono text-sm focus:outline-none w-20 text-center"
                                            />
                                            <div className="flex-1" />
                                            <button
                                                onClick={() => removeTimeBlock(index)}
                                                className="p-1.5 hover:bg-red-500/20 text-slate-500 hover:text-red-400 rounded-lg transition-colors"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    ))}
                                    {blockedPeriods.length === 0 && (
                                        <p className="text-xs text-slate-500 italic text-center py-2">No blocked times configured.</p>
                                    )}
                                </div>
                            </div>

                            {/* Auto Flatten Section */}
                            <div className="space-y-3">
                                <div className="flex justify-between items-center">
                                    <div className="flex items-center gap-3">
                                        <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-shield-alert text-slate-400"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" /><path d="M8 11h.01" /><path d="M12 11h.01" /><path d="M16 11h.01" /></svg>
                                            Auto-Flatten Daily
                                        </label>
                                        <button
                                            onClick={() => setAutoFlattenEnabled(!autoFlattenEnabled)}
                                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${autoFlattenEnabled ? 'bg-indigo-500' : 'bg-slate-700'}`}
                                        >
                                            <span
                                                className={`${autoFlattenEnabled ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`}
                                            />
                                        </button>
                                        <span className="text-xs text-slate-500 font-mono">
                                            {autoFlattenEnabled ? "Active" : "Disabled"}
                                        </span>
                                    </div>

                                    <input
                                        type="time"
                                        value={autoFlattenTime}
                                        onChange={(e) => setAutoFlattenTime(e.target.value)}
                                        disabled={!autoFlattenEnabled}
                                        className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-white font-mono text-sm focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                                    />
                                </div>
                                <p className="text-[10px] text-slate-500 italic">
                                    Automatically closes all positions and cancels orders at this time.
                                </p>
                            </div>
                        </div>
                    ) : (
                        <TickerMapping
                            mappings={mappings}
                            onAdd={addMapping}
                            onDelete={deleteMapping}
                        />
                    )}
                </div>

                <div className="p-6 border-t border-slate-800 bg-slate-900/50 flex justify-end gap-3 shrink-0">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 transition-colors font-medium text-sm"
                    >
                        Cancel
                    </button>
                    {activeTab === 'general' && (
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="px-6 py-2 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-900/20 flex items-center gap-2 transition-all"
                        >
                            {saving ? 'Saving...' : (
                                <>
                                    <Save size={16} /> Save Changes
                                </>
                            )}
                        </button>
                    )}
                    {activeTab === 'mappings' && (
                        <button
                            onClick={onClose}
                            className="px-6 py-2 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-900/20 flex items-center gap-2 transition-all"
                        >
                            Done
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
