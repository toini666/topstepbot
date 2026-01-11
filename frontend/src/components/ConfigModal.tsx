import { useState, useEffect } from 'react';
import axios from 'axios';
import { X, Save, Plus, Trash2, Clock, Settings, Calendar } from 'lucide-react';
import { toast } from 'sonner';
import type { GlobalConfig, TimeBlock, TickerMap, TradingSession } from '../types';
import { TickerMapping } from './TickerMapping';
import { API_BASE } from '../config';

interface ConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
    config: GlobalConfig;
    onSave: (newConfig: Partial<GlobalConfig>) => Promise<void>;
}

export function ConfigModal({ isOpen, onClose, config, onSave }: ConfigModalProps) {
    const [activeTab, setActiveTab] = useState<'general' | 'sessions' | 'mappings'>('general');

    // General Settings
    const [blockedPeriodsEnabled, setBlockedPeriodsEnabled] = useState(true);
    const [blockedPeriods, setBlockedPeriods] = useState<TimeBlock[]>([]);
    const [autoFlattenEnabled, setAutoFlattenEnabled] = useState(false);
    const [autoFlattenTime, setAutoFlattenTime] = useState("21:55");
    const [marketOpenTime, setMarketOpenTime] = useState("00:00");
    const [marketCloseTime, setMarketCloseTime] = useState("22:00");

    // Sessions
    const [sessions, setSessions] = useState<TradingSession[]>([]);

    // Mappings
    const [mappings, setMappings] = useState<TickerMap[]>([]);

    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setBlockedPeriodsEnabled(config.blocked_periods_enabled);
            setBlockedPeriods([...config.blocked_periods]);
            setAutoFlattenEnabled(config.auto_flatten_enabled ?? false);
            setAutoFlattenTime(config.auto_flatten_time || "21:55");
            setMarketOpenTime(config.market_open_time || "00:00");
            setMarketCloseTime(config.market_close_time || "22:00");
            fetchSessions();
            fetchMappings();
        }
    }, [isOpen, config]);

    const fetchSessions = async () => {
        try {
            const res = await axios.get(`${API_BASE}/settings/sessions`);
            setSessions(res.data);
        } catch (e) {
            console.error("Failed to fetch sessions", e);
        }
    };

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
            const res = await axios.post(`${API_BASE}/settings/ticker-map`, mapping);
            if (res.data.success) {
                toast.success("Mapping Added");
                fetchMappings();
            } else {
                toast.error(res.data.message || "Failed to add mapping");
            }
        } catch (e) {
            toast.error("Error adding mapping");
        }
    };

    const deleteMapping = async (id: number) => {
        try {
            const res = await axios.delete(`${API_BASE}/settings/ticker-map/${id}`);
            if (res.data.success) {
                toast.success("Mapping Deleted");
                fetchMappings();
            }
        } catch (e) {
            toast.error("Error deleting mapping");
        }
    };

    if (!isOpen) return null;

    const handleSave = async () => {
        setSaving(true);
        await onSave({
            blocked_periods_enabled: blockedPeriodsEnabled,
            blocked_periods: blockedPeriods,
            auto_flatten_enabled: autoFlattenEnabled,
            auto_flatten_time: autoFlattenTime,
            market_open_time: marketOpenTime,
            market_close_time: marketCloseTime
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
                        Global Settings
                    </h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-slate-800 bg-slate-950/30 px-6 shrink-0">
                    {(['general', 'sessions', 'mappings'] as const).map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`py-3 px-4 text-sm font-medium border-b-2 transition-colors capitalize ${activeTab === tab
                                ? 'border-indigo-500 text-white'
                                : 'border-transparent text-slate-400 hover:text-white'
                                }`}
                        >
                            {tab}
                        </button>
                    ))}
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto custom-scrollbar">
                    {activeTab === 'general' && (
                        <div className="space-y-6">
                            {/* Market Hours */}
                            <div className="space-y-3">
                                <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                                    <Calendar className="w-4 h-4 text-slate-400" />
                                    Market Hours (Brussels TZ)
                                </label>
                                <div className="flex items-center gap-3">
                                    <input
                                        type="time"
                                        value={marketOpenTime}
                                        onChange={(e) => setMarketOpenTime(e.target.value)}
                                        className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-indigo-500"
                                    />
                                    <span className="text-slate-500">to</span>
                                    <input
                                        type="time"
                                        value={marketCloseTime}
                                        onChange={(e) => setMarketCloseTime(e.target.value)}
                                        className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                            </div>

                            {/* Blocked Periods */}
                            <div className={`space-y-3 transition-opacity ${!blockedPeriodsEnabled ? "opacity-50" : ""}`}>
                                <div className="flex justify-between items-center">
                                    <div className="flex items-center gap-3">
                                        <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                                            <Clock className="w-4 h-4 text-slate-400" />
                                            Blocked Trading Hours
                                        </label>
                                        <button
                                            onClick={() => setBlockedPeriodsEnabled(!blockedPeriodsEnabled)}
                                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${blockedPeriodsEnabled ? 'bg-indigo-500' : 'bg-slate-700'
                                                }`}
                                        >
                                            <span className={`${blockedPeriodsEnabled ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                                        </button>
                                    </div>
                                    <button
                                        onClick={addTimeBlock}
                                        disabled={!blockedPeriodsEnabled}
                                        className="text-xs bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 px-2 py-1 rounded-lg flex items-center gap-1 disabled:opacity-50"
                                    >
                                        <Plus size={12} /> Add
                                    </button>
                                </div>

                                <div className="space-y-2 max-h-[150px] overflow-y-auto">
                                    {blockedPeriods.map((block, index) => (
                                        <div key={index} className="flex items-center gap-2 bg-slate-950 p-2 rounded-xl border border-slate-800">
                                            <input
                                                type="time"
                                                value={block.start}
                                                onChange={(e) => updateTimeBlock(index, 'start', e.target.value)}
                                                className="bg-transparent text-white font-mono text-sm focus:outline-none w-20"
                                            />
                                            <span className="text-slate-500">-</span>
                                            <input
                                                type="time"
                                                value={block.end}
                                                onChange={(e) => updateTimeBlock(index, 'end', e.target.value)}
                                                className="bg-transparent text-white font-mono text-sm focus:outline-none w-20"
                                            />
                                            <div className="flex-1" />
                                            <button
                                                onClick={() => removeTimeBlock(index)}
                                                className="p-1.5 hover:bg-red-500/20 text-slate-500 hover:text-red-400 rounded-lg"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Auto Flatten */}
                            <div className="space-y-3">
                                <div className="flex justify-between items-center">
                                    <div className="flex items-center gap-3">
                                        <label className="text-sm font-semibold text-slate-300">Auto-Flatten (All Accounts)</label>
                                        <button
                                            onClick={() => setAutoFlattenEnabled(!autoFlattenEnabled)}
                                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${autoFlattenEnabled ? 'bg-indigo-500' : 'bg-slate-700'
                                                }`}
                                        >
                                            <span className={`${autoFlattenEnabled ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                                        </button>
                                    </div>
                                    <input
                                        type="time"
                                        value={autoFlattenTime}
                                        onChange={(e) => setAutoFlattenTime(e.target.value)}
                                        disabled={!autoFlattenEnabled}
                                        className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-white font-mono text-sm disabled:opacity-50"
                                    />
                                </div>
                                <p className="text-[10px] text-slate-500 italic">
                                    Closes ALL positions and cancels ALL orders across ALL accounts at this time.
                                </p>
                            </div>
                        </div>
                    )}

                    {activeTab === 'sessions' && (
                        <div className="space-y-4">
                            <p className="text-sm text-slate-400">
                                Trading sessions define time windows when strategies can execute.
                            </p>

                            {sessions.map(session => (
                                <div key={session.id} className="bg-slate-950 border border-slate-800 rounded-xl p-4">
                                    <div className="flex justify-between items-center">
                                        <div>
                                            <span className="font-bold text-white">{session.display_name}</span>
                                            <span className="text-slate-500 text-sm ml-2">({session.name})</span>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <span className="font-mono text-sm text-slate-300">
                                                {session.start_time} - {session.end_time}
                                            </span>
                                            <span className={`text-xs px-2 py-0.5 rounded ${session.is_active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-400'}`}>
                                                {session.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {activeTab === 'mappings' && (
                        <TickerMapping
                            mappings={mappings}
                            onAdd={addMapping}
                            onDelete={deleteMapping}
                        />
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-slate-800 bg-slate-900/50 flex justify-end gap-3 shrink-0">
                    <button onClick={onClose} className="px-4 py-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 font-medium text-sm">
                        Cancel
                    </button>
                    {activeTab === 'general' && (
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="px-6 py-2 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg flex items-center gap-2"
                        >
                            <Save size={16} /> {saving ? 'Saving...' : 'Save Changes'}
                        </button>
                    )}
                    {activeTab !== 'general' && (
                        <button onClick={onClose} className="px-6 py-2 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-700 text-white">
                            Done
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
