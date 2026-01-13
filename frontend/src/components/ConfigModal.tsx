import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { X, Save, Plus, Trash2, Clock, Settings, Calendar } from 'lucide-react';
import { toast } from 'sonner';
import type { GlobalConfig, TimeBlock, TickerMap, TradingSession } from '../types';
import { TickerMapping } from './TickerMapping';
import { TimePicker } from './TimePicker';
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

    // New settings
    const [tradingDays, setTradingDays] = useState<string[]>(['MON', 'TUE', 'WED', 'THU', 'FRI']);
    const [enforceSinglePosition, setEnforceSinglePosition] = useState(true);
    const [blockCrossAccount, setBlockCrossAccount] = useState(true);

    // Sessions
    const [sessions, setSessions] = useState<TradingSession[]>([]);
    const [sessionsModified, setSessionsModified] = useState<Record<number, TradingSession>>({});

    // Mappings
    const [mappings, setMappings] = useState<TickerMap[]>([]);

    const [saving, setSaving] = useState(false);
    const initializedRef = useRef(false);

    useEffect(() => {
        if (isOpen && !initializedRef.current) {
            // Only initialize state ONCE when opening
            setBlockedPeriodsEnabled(config.blocked_periods_enabled);
            setBlockedPeriods([...config.blocked_periods]);
            setAutoFlattenEnabled(config.auto_flatten_enabled ?? false);
            setAutoFlattenTime(config.auto_flatten_time || "21:55");
            setMarketOpenTime(config.market_open_time || "00:00");
            setMarketCloseTime(config.market_close_time || "22:00");
            setTradingDays(config.trading_days || ['MON', 'TUE', 'WED', 'THU', 'FRI']);
            setEnforceSinglePosition(config.enforce_single_position_per_asset ?? true);
            setBlockCrossAccount(config.block_cross_account_opposite ?? true);
            fetchSessions();
            fetchMappings();
            initializedRef.current = true;
        } else if (!isOpen) {
            initializedRef.current = false;
            setSessionsModified({});
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

    const updateMapping = async (id: number, updates: Partial<TickerMap>) => {
        try {
            const res = await axios.patch(`${API_BASE}/settings/ticker-map/${id}`, updates);
            if (res.data.success) {
                // Update local state immediately
                setMappings(mappings.map(m => m.id === id ? { ...m, ...updates } : m));
                toast.success("Mapping Updated");
            }
        } catch (e) {
            toast.error("Error updating mapping");
        }
    };

    if (!isOpen) return null;

    const handleSave = async () => {
        setSaving(true);
        try {
            // Save Global Config
            await onSave({
                blocked_periods_enabled: blockedPeriodsEnabled,
                blocked_periods: blockedPeriods,
                auto_flatten_enabled: autoFlattenEnabled,
                auto_flatten_time: autoFlattenTime,
                market_open_time: marketOpenTime,
                market_close_time: marketCloseTime,
                trading_days: tradingDays,
                enforce_single_position_per_asset: enforceSinglePosition,
                block_cross_account_opposite: blockCrossAccount
            });

            // Save Sessions if modified
            const promises = Object.values(sessionsModified).map(session =>
                axios.put(`${API_BASE}/settings/sessions/${session.id}`, session)
            );

            if (promises.length > 0) {
                await Promise.all(promises);
                toast.success("Sessions Updated");
            }

        } catch (e) {
            toast.error("Error saving changes");
        } finally {
            setSaving(false);
            onClose();
        }
    };

    const addTimeBlock = () => {
        setBlockedPeriods([...blockedPeriods, { start: "00:00", end: "00:00", enabled: true }]);
    };

    const removeTimeBlock = (index: number) => {
        const newBlocks = [...blockedPeriods];
        newBlocks.splice(index, 1);
        setBlockedPeriods(newBlocks);
    };

    const updateTimeBlock = (index: number, field: keyof TimeBlock, value: any) => {
        const newBlocks = [...blockedPeriods];
        newBlocks[index] = { ...newBlocks[index], [field]: value };
        setBlockedPeriods(newBlocks);
    };

    const updateSession = (id: number, field: keyof TradingSession, value: any) => {
        const session = sessions.find(s => s.id === id);
        if (!session) return;

        const updated = { ...session, [field]: value };

        // Update local list
        setSessions(sessions.map(s => s.id === id ? updated : s));

        // Track modification
        setSessionsModified(prev => ({
            ...prev,
            [id]: updated
        }));
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
                                    <TimePicker
                                        value={marketOpenTime}
                                        onChange={setMarketOpenTime}
                                    />
                                    <span className="text-slate-500">to</span>
                                    <TimePicker
                                        value={marketCloseTime}
                                        onChange={setMarketCloseTime}
                                    />
                                </div>
                            </div>

                            {/* Trading Days */}
                            <div className="space-y-3">
                                <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                                    <Calendar className="w-4 h-4 text-slate-400" />
                                    Trading Days
                                </label>
                                <div className="flex gap-2">
                                    {[
                                        { key: 'MON', label: 'M' },
                                        { key: 'TUE', label: 'T' },
                                        { key: 'WED', label: 'W' },
                                        { key: 'THU', label: 'T' },
                                        { key: 'FRI', label: 'F' },
                                        { key: 'SAT', label: 'S' },
                                        { key: 'SUN', label: 'S' }
                                    ].map(day => {
                                        const isEnabled = tradingDays.includes(day.key);
                                        return (
                                            <button
                                                key={day.key}
                                                onClick={() => {
                                                    if (isEnabled) {
                                                        setTradingDays(tradingDays.filter(d => d !== day.key));
                                                    } else {
                                                        setTradingDays([...tradingDays, day.key]);
                                                    }
                                                }}
                                                className={`w-9 h-9 rounded-lg font-bold text-sm transition-all ${isEnabled
                                                    ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/30'
                                                    : 'bg-slate-800 text-slate-500 hover:bg-slate-700'
                                                    }`}
                                                title={day.key}
                                            >
                                                {day.label}
                                            </button>
                                        );
                                    })}
                                </div>
                                <p className="text-[10px] text-slate-500 italic">
                                    Click to enable/disable trading on each day. Di=Dimanche, S=Samedi.
                                </p>
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

                                <div className="space-y-2 pr-2">
                                    {blockedPeriods.map((block, index) => (
                                        <div key={index} className={`flex items-center gap-2 bg-slate-950 p-2 rounded-xl border ${block.enabled ? 'border-indigo-500/30' : 'border-slate-800 opacity-60'}`}>
                                            <button
                                                onClick={() => updateTimeBlock(index, 'enabled', !block.enabled)}
                                                className={`relative inline-flex h-4 w-7 items-center rounded-full transition-colors ${block.enabled ? 'bg-indigo-500' : 'bg-slate-700'}`}
                                            >
                                                <span className={`${block.enabled ? 'translate-x-3.5' : 'translate-x-0.5'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                                            </button>
                                            <TimePicker
                                                value={block.start}
                                                onChange={(val) => updateTimeBlock(index, 'start', val)}
                                            />
                                            <span className="text-slate-500">-</span>
                                            <TimePicker
                                                value={block.end}
                                                onChange={(val) => updateTimeBlock(index, 'end', val)}
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
                                    {blockedPeriods.length === 0 && (
                                        <p className="text-xs text-slate-500 italic text-center py-2">No blocked periods</p>
                                    )}
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
                                    <TimePicker
                                        value={autoFlattenTime}
                                        onChange={setAutoFlattenTime}
                                        disabled={!autoFlattenEnabled}
                                    />
                                </div>
                                <p className="text-[10px] text-slate-500 italic">
                                    Closes ALL positions and cancels ALL orders across ALL accounts at this time.
                                </p>
                            </div>

                            {/* Risk Rules */}
                            <div className="space-y-3 pt-4 border-t border-slate-800">
                                <label className="text-sm font-semibold text-slate-300">Risk Rules</label>

                                {/* Single Position per Asset */}
                                <div className="flex justify-between items-center">
                                    <div>
                                        <span className="text-sm text-slate-300">Single Position Per Asset</span>
                                        <p className="text-[10px] text-slate-500">Prevent opening 2 positions on the same asset</p>
                                    </div>
                                    <button
                                        onClick={() => setEnforceSinglePosition(!enforceSinglePosition)}
                                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${enforceSinglePosition ? 'bg-indigo-500' : 'bg-slate-700'}`}
                                    >
                                        <span className={`${enforceSinglePosition ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                                    </button>
                                </div>

                                {/* Block Cross-Account Opposite */}
                                <div className="flex justify-between items-center">
                                    <div>
                                        <span className="text-sm text-slate-300">Block Cross-Account Opposite</span>
                                        <p className="text-[10px] text-slate-500">Prevent LONG on one account if SHORT on another</p>
                                    </div>
                                    <button
                                        onClick={() => setBlockCrossAccount(!blockCrossAccount)}
                                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${blockCrossAccount ? 'bg-indigo-500' : 'bg-slate-700'}`}
                                    >
                                        <span className={`${blockCrossAccount ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'sessions' && (
                        <div className="space-y-4">
                            <p className="text-sm text-slate-400">
                                Configure market sessions times. Active sessions are used for strategy filtering.
                            </p>

                            {sessions.map(session => (
                                <div key={session.id} className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                                    <div className="flex justify-between items-center">
                                        <div>
                                            <span className="font-bold text-white">{session.display_name}</span>
                                            <span className="text-slate-500 text-sm ml-2">({session.name})</span>
                                        </div>
                                        <button
                                            onClick={() => updateSession(session.id, 'is_active', !session.is_active)}
                                            className={`text-xs px-2 py-0.5 rounded transition-colors ${session.is_active
                                                ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                                                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                                                }`}
                                        >
                                            {session.is_active ? 'Active' : 'Inactive'}
                                        </button>
                                    </div>

                                    <div className="flex items-center gap-3">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-slate-500 uppercase font-bold">Start</span>
                                            <TimePicker
                                                value={session.start_time}
                                                onChange={(val) => updateSession(session.id, 'start_time', val)}
                                            />
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-slate-500 uppercase font-bold">End</span>
                                            <TimePicker
                                                value={session.end_time}
                                                onChange={(val) => updateSession(session.id, 'end_time', val)}
                                            />
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
                            onUpdate={updateMapping}
                        />
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-slate-800 bg-slate-900/50 flex justify-end gap-3 shrink-0">
                    <button onClick={onClose} className="px-4 py-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 font-medium text-sm">
                        Cancel
                    </button>
                    {(activeTab === 'general' || activeTab === 'sessions') && (
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="px-6 py-2 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg flex items-center gap-2"
                        >
                            <Save size={16} /> {saving ? 'Saving...' : 'Save Changes'}
                        </button>
                    )}
                    {activeTab === 'mappings' && (
                        <button onClick={onClose} className="px-6 py-2 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-700 text-white">
                            Done
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
