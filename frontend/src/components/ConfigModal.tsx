import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { X, Save, Plus, Trash2, Clock, Settings, Calendar, Bell, ChevronDown, CheckCircle, Power, Newspaper, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import type { GlobalConfig, TimeBlock, TickerMap, TradingSession, Account, NewsBlock } from '../types';
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
    const [activeTab, setActiveTab] = useState<'general' | 'sessions' | 'mappings' | 'notifications'>('general');

    // General Settings
    const [blockedPeriodsEnabled, setBlockedPeriodsEnabled] = useState(true);
    const [blockedPeriods, setBlockedPeriods] = useState<TimeBlock[]>([]);
    const [autoFlattenEnabled, setAutoFlattenEnabled] = useState(false);
    const [autoFlattenTime, setAutoFlattenTime] = useState("21:55");
    const [marketOpenTime, setMarketOpenTime] = useState("00:00");
    const [marketCloseTime, setMarketCloseTime] = useState("22:00");
    const [weekendMarketsOpen, setWeekendMarketsOpen] = useState(false);

    // New settings
    const [tradingDays, setTradingDays] = useState<string[]>(['MON', 'TUE', 'WED', 'THU', 'FRI']);
    const [enforceSinglePosition, setEnforceSinglePosition] = useState(true);
    const [blockCrossAccount, setBlockCrossAccount] = useState(true);

    // News Block Settings
    const [newsBlockEnabled, setNewsBlockEnabled] = useState(false);
    const [newsBlockBefore, setNewsBlockBefore] = useState(5);
    const [newsBlockAfter, setNewsBlockAfter] = useState(5);
    const [newsBlocks, setNewsBlocks] = useState<NewsBlock[]>([]);

    // Position Action Settings
    const [positionAction, setPositionAction] = useState<'NOTHING' | 'BREAKEVEN' | 'FLATTEN'>('NOTHING');
    const [positionActionBuffer, setPositionActionBuffer] = useState(1);
    const [positionActionDropdownOpen, setPositionActionDropdownOpen] = useState(false);

    // Sessions
    const [sessions, setSessions] = useState<TradingSession[]>([]);
    const [sessionsModified, setSessionsModified] = useState<Record<number, TradingSession>>({});

    // Mappings
    const [mappings, setMappings] = useState<TickerMap[]>([]);

    // Discord Notifications
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [selectedNotifAccountId, setSelectedNotifAccountId] = useState<number | null>(null);
    const [accountDropdownOpen, setAccountDropdownOpen] = useState(false);
    const [discordEnabled, setDiscordEnabled] = useState(false);
    const [webhookUrl, setWebhookUrl] = useState('');
    const [notifyPositionOpen, setNotifyPositionOpen] = useState(true);
    const [notifyPositionClose, setNotifyPositionClose] = useState(true);
    const [notifyDailySummary, setNotifyDailySummary] = useState(false);
    const [dailySummaryTime, setDailySummaryTime] = useState('21:00');
    const [savingDiscord, setSavingDiscord] = useState(false);

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
            setWeekendMarketsOpen(config.weekend_markets_open ?? false);
            setTradingDays(config.trading_days || ['MON', 'TUE', 'WED', 'THU', 'FRI']);
            setEnforceSinglePosition(config.enforce_single_position_per_asset ?? true);
            setBlockCrossAccount(config.block_cross_account_opposite ?? true);
            // News Block Settings
            setNewsBlockEnabled(config.news_block_enabled ?? false);
            setNewsBlockBefore(config.news_block_before_minutes ?? 5);
            setNewsBlockAfter(config.news_block_after_minutes ?? 5);
            // Position Action Settings
            setPositionAction(config.blocked_hours_position_action ?? 'NOTHING');
            setPositionActionBuffer(config.position_action_buffer_minutes ?? 1);
            fetchSessions();
            fetchMappings();
            fetchAccounts();
            fetchNewsBlocks();
            initializedRef.current = true;
        } else if (!isOpen) {
            initializedRef.current = false;
            setSessionsModified({});
            setSelectedNotifAccountId(null);
            setPositionActionDropdownOpen(false);
        }
    }, [isOpen, config]);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (accountDropdownOpen && !target.closest('.group-account-selector')) {
                setAccountDropdownOpen(false);
            }
            if (positionActionDropdownOpen && !target.closest('.group-position-action')) {
                setPositionActionDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [accountDropdownOpen, positionActionDropdownOpen]);

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

    const fetchAccounts = async () => {
        try {
            const res = await axios.get(`${API_BASE}/dashboard/accounts`);
            setAccounts(res.data);
            // Auto-select first account if available
            if (res.data.length > 0 && !selectedNotifAccountId) {
                setSelectedNotifAccountId(res.data[0].id);
            }
        } catch (e) {
            console.error("Failed to fetch accounts", e);
        }
    };

    const fetchNewsBlocks = async () => {
        try {
            const res = await axios.get(`${API_BASE}/dashboard/news-blocks`);
            setNewsBlocks(res.data.blocks || []);
        } catch (e) {
            console.error("Failed to fetch news blocks", e);
        }
    };

    // Fetch Discord settings when account changes
    useEffect(() => {
        if (selectedNotifAccountId && activeTab === 'notifications') {
            fetchDiscordSettings(selectedNotifAccountId);
        }
    }, [selectedNotifAccountId, activeTab]);

    const fetchDiscordSettings = async (accountId: number) => {
        try {
            const res = await axios.get(`${API_BASE}/settings/discord/${accountId}`);
            const settings = res.data;
            setDiscordEnabled(settings.enabled);
            setWebhookUrl(settings.webhook_url || '');
            setNotifyPositionOpen(settings.notify_position_open);
            setNotifyPositionClose(settings.notify_position_close);
            setNotifyDailySummary(settings.notify_daily_summary);
            setDailySummaryTime(settings.daily_summary_time || '21:00');
        } catch (e) {
            console.error("Failed to fetch Discord settings", e);
            // Reset to defaults
            setDiscordEnabled(false);
            setWebhookUrl('');
            setNotifyPositionOpen(true);
            setNotifyPositionClose(true);
            setNotifyDailySummary(false);
            setDailySummaryTime('21:00');
        }
    };

    const saveDiscordSettings = async () => {
        if (!selectedNotifAccountId) return;

        setSavingDiscord(true);
        try {
            await axios.post(`${API_BASE}/settings/discord/${selectedNotifAccountId}`, {
                enabled: discordEnabled,
                webhook_url: webhookUrl,
                notify_position_open: notifyPositionOpen,
                notify_position_close: notifyPositionClose,
                notify_daily_summary: notifyDailySummary,
                daily_summary_time: dailySummaryTime
            });
            toast.success("Discord settings saved");
        } catch (e) {
            toast.error("Failed to save Discord settings");
        } finally {
            setSavingDiscord(false);
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
                weekend_markets_open: weekendMarketsOpen,
                trading_days: tradingDays,
                enforce_single_position_per_asset: enforceSinglePosition,
                block_cross_account_opposite: blockCrossAccount,
                // News Block Settings
                news_block_enabled: newsBlockEnabled,
                news_block_before_minutes: newsBlockBefore,
                news_block_after_minutes: newsBlockAfter,
                // Position Action Settings
                blocked_hours_position_action: positionAction,
                position_action_buffer_minutes: positionActionBuffer
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
        <div className="fixed inset-0 z-50 h-screen w-screen flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
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
                    {(['general', 'sessions', 'mappings', 'notifications'] as const).map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`py-3 px-4 text-sm font-medium border-b-2 transition-colors capitalize ${activeTab === tab
                                ? 'border-indigo-500 text-white'
                                : 'border-transparent text-slate-400 hover:text-white'
                                }`}
                        >
                            {tab === 'notifications' ? <span className="flex items-center gap-1"><Bell size={14} /> Notifications</span> : tab}
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

                                {/* Weekend Markets Toggle */}
                                <div className="flex items-center justify-between bg-slate-950 p-3 rounded-xl border border-slate-800">
                                    <div>
                                        <span className="text-sm text-slate-300">Weekend Markets Open</span>
                                        <p className="text-[10px] text-slate-500">Are futures markets open on Saturday/Sunday?</p>
                                    </div>
                                    <button
                                        onClick={() => setWeekendMarketsOpen(!weekendMarketsOpen)}
                                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${weekendMarketsOpen ? 'bg-indigo-500' : 'bg-slate-700'}`}
                                    >
                                        <span className={`${weekendMarketsOpen ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                                    </button>
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

                            {/* News Block Settings */}
                            <div className={`space-y-3 transition-opacity ${!newsBlockEnabled ? "opacity-50" : ""}`}>
                                <div className="flex justify-between items-center">
                                    <div className="flex items-center gap-3">
                                        <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                                            <Newspaper className="w-4 h-4 text-slate-400" />
                                            News Trading Blocks
                                        </label>
                                        <button
                                            onClick={() => setNewsBlockEnabled(!newsBlockEnabled)}
                                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${newsBlockEnabled ? 'bg-indigo-500' : 'bg-slate-700'}`}
                                        >
                                            <span className={`${newsBlockEnabled ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                                        </button>
                                    </div>
                                </div>

                                {newsBlockEnabled && (
                                    <div className="space-y-3 pl-6">
                                        <p className="text-[10px] text-slate-500 italic">
                                            Automatically block trading around major economic events based on calendar settings.
                                        </p>
                                        <div className="flex items-center gap-4">
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm text-slate-400">Block</span>
                                                <input
                                                    type="number"
                                                    value={newsBlockBefore}
                                                    onChange={(e) => setNewsBlockBefore(Number(e.target.value))}
                                                    className="w-16 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors font-mono text-center"
                                                    min={0}
                                                />
                                                <span className="text-sm text-slate-400">min before</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm text-slate-400">and</span>
                                                <input
                                                    type="number"
                                                    value={newsBlockAfter}
                                                    onChange={(e) => setNewsBlockAfter(Number(e.target.value))}
                                                    className="w-16 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors font-mono text-center"
                                                    min={0}
                                                />
                                                <span className="text-sm text-slate-400">min after</span>
                                            </div>
                                        </div>

                                        {/* Today's News Blocks Display */}
                                        {newsBlocks.length > 0 ? (
                                            <div className="space-y-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs font-semibold text-slate-400">Today's Blocks</span>
                                                    <span className="text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded">Today only</span>
                                                </div>
                                                <div className="space-y-1">
                                                    {newsBlocks.map((block, idx) => (
                                                        <div key={idx} className="flex items-center gap-2 text-xs bg-slate-950 p-2 rounded-lg">
                                                            <span className={`w-2 h-2 rounded-full ${block.impact === 'High' ? 'bg-red-500' : block.impact === 'Medium' ? 'bg-amber-500' : 'bg-green-500'}`} />
                                                            <span className="text-slate-500 font-mono">{block.start}-{block.end}</span>
                                                            <span className="text-slate-400">{block.country}</span>
                                                            <span className="text-slate-300 flex-1 truncate">{block.event}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ) : (
                                            <p className="text-xs text-slate-500 italic py-1">No news blocks for today.</p>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* Position Action on Blocked Hours */}
                            <div className="space-y-3">
                                <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                                    <AlertTriangle className="w-4 h-4 text-slate-400" />
                                    Position Action on Blocked Hours
                                </label>

                                <div className="pl-6 space-y-3">
                                    <div className="flex items-center gap-4">
                                        {/* Custom Dropdown */}
                                        <div className="relative group-position-action">
                                            <button
                                                onClick={() => setPositionActionDropdownOpen(!positionActionDropdownOpen)}
                                                className="min-w-[200px] flex items-center justify-between bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white hover:border-indigo-500/50 transition-colors"
                                            >
                                                <span>
                                                    {positionAction === 'NOTHING' && 'Do Nothing'}
                                                    {positionAction === 'BREAKEVEN' && 'Move SL to Breakeven'}
                                                    {positionAction === 'FLATTEN' && 'Flatten All Positions'}
                                                </span>
                                                <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${positionActionDropdownOpen ? 'rotate-180' : ''}`} />
                                            </button>

                                            {positionActionDropdownOpen && (
                                                <div className="absolute top-full left-0 mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20 animate-fade-in-down">
                                                    <div className="p-1">
                                                        {[
                                                            { value: 'NOTHING', label: 'Do Nothing' },
                                                            { value: 'BREAKEVEN', label: 'Move SL to Breakeven' },
                                                            { value: 'FLATTEN', label: 'Flatten All Positions' }
                                                        ].map((option) => (
                                                            <button
                                                                key={option.value}
                                                                onClick={() => {
                                                                    setPositionAction(option.value as any);
                                                                    setPositionActionDropdownOpen(false);
                                                                }}
                                                                className={`w-full text-left px-3 py-2 rounded-lg flex items-center justify-between transition-colors text-sm ${positionAction === option.value
                                                                    ? 'bg-indigo-500/10 text-indigo-400'
                                                                    : 'text-slate-300 hover:bg-slate-700/50'
                                                                    }`}
                                                            >
                                                                <span>{option.label}</span>
                                                                {positionAction === option.value && <CheckCircle className="w-3.5 h-3.5" />}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>

                                        {positionAction !== 'NOTHING' && (
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm text-slate-400">Buffer:</span>
                                                <input
                                                    type="number"
                                                    value={positionActionBuffer}
                                                    onChange={(e) => setPositionActionBuffer(Number(e.target.value))}
                                                    className="w-16 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors font-mono text-center"
                                                    min={1}
                                                />
                                                <span className="text-sm text-slate-400">min</span>
                                            </div>
                                        )}
                                    </div>

                                    {positionAction !== 'NOTHING' && (
                                        <div className={`text-[10px] p-2 rounded-lg inline-block ${positionAction === 'FLATTEN' ? 'bg-red-500/10 text-red-400' : 'bg-amber-500/10 text-amber-400'}`}>
                                            {positionAction === 'BREAKEVEN' && "Stop Loss will be moved to entry price for all open positions."}
                                            {positionAction === 'FLATTEN' && "All positions will be closed and orders cancelled."}
                                        </div>
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

                    {activeTab === 'notifications' && (
                        <div className="space-y-6">
                            <p className="text-sm text-slate-400">
                                Configure Discord webhook notifications per account.
                            </p>

                            {/* Account Selector */}
                            <div className="space-y-2">
                                <label className="text-sm font-semibold text-slate-300">Select Account</label>
                                <div className="bg-slate-950 border border-slate-700 p-2 rounded-xl w-full flex flex-col justify-center relative group-account-selector">
                                    <button
                                        onClick={() => accounts.length > 0 && setAccountDropdownOpen(!accountDropdownOpen)}
                                        className="w-full flex items-center justify-between text-left px-2 py-1 focus:outline-none"
                                        disabled={accounts.length === 0}
                                    >
                                        <span className="text-white font-mono text-sm truncate mr-2">
                                            {selectedNotifAccountId
                                                ? (() => {
                                                    const acc = accounts.find(a => a.id === selectedNotifAccountId);
                                                    return acc ? `${acc.name} (${acc.id})` : 'Select Account';
                                                })()
                                                : 'Select Account'}
                                        </span>
                                        <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${accountDropdownOpen ? 'rotate-180' : ''}`} />
                                    </button>

                                    {accountDropdownOpen && accounts.length > 0 && (
                                        <div className="absolute top-full left-0 mt-2 w-full bg-slate-900 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20">
                                            <div className="max-h-60 overflow-y-auto custom-scrollbar">
                                                {accounts.map((acc) => (
                                                    <button
                                                        key={acc.id}
                                                        onClick={() => {
                                                            setSelectedNotifAccountId(acc.id);
                                                            setAccountDropdownOpen(false);
                                                        }}
                                                        className={`w-full text-left px-4 py-2 flex items-center justify-between transition-colors hover:bg-slate-800/50 ${acc.id === selectedNotifAccountId
                                                            ? 'bg-indigo-500/10 text-indigo-400'
                                                            : 'text-slate-300'
                                                            }`}
                                                    >
                                                        <div className="flex items-center gap-2 truncate">
                                                            {/* Trading Status Icon */}
                                                            <div className={`p-0.5 rounded-full ${acc.canTrade ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-500'}`} title={acc.canTrade ? "Trading Enabled" : "Trading Disabled"}>
                                                                <Power className="w-3 h-3" />
                                                            </div>
                                                            <span className="font-mono text-xs truncate">{acc.name} ({acc.id})</span>
                                                        </div>
                                                        {acc.id === selectedNotifAccountId && <CheckCircle className="w-3 h-3 flex-shrink-0" />}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {selectedNotifAccountId && (
                                <div className="space-y-4">
                                    {/* Discord Enabled Toggle */}
                                    <div className="flex items-center justify-between bg-slate-950 p-4 rounded-xl border border-slate-800">
                                        <div>
                                            <span className="text-sm font-semibold text-white flex items-center gap-2">
                                                <Bell size={16} className="text-indigo-400" />
                                                Discord Notifications
                                            </span>
                                            <p className="text-[10px] text-slate-500 mt-1">Enable Discord webhook notifications for this account</p>
                                        </div>
                                        <button
                                            onClick={() => setDiscordEnabled(!discordEnabled)}
                                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${discordEnabled ? 'bg-indigo-500' : 'bg-slate-700'}`}
                                        >
                                            <span className={`${discordEnabled ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`} />
                                        </button>
                                    </div>

                                    {/* Webhook URL */}
                                    <div className={`space-y-2 transition-opacity ${!discordEnabled ? 'opacity-50' : ''}`}>
                                        <label className="text-sm font-semibold text-slate-300">Webhook URL</label>
                                        <input
                                            type="text"
                                            value={webhookUrl}
                                            onChange={(e) => setWebhookUrl(e.target.value)}
                                            disabled={!discordEnabled}
                                            placeholder="https://discord.com/api/webhooks/..."
                                            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
                                        />
                                        <p className="text-[10px] text-slate-500">
                                            Create a webhook in Discord: Server Settings → Integrations → Webhooks
                                        </p>
                                    </div>

                                    {/* Notification Types */}
                                    <div className={`space-y-3 transition-opacity ${!discordEnabled ? 'opacity-50' : ''}`}>
                                        <label className="text-sm font-semibold text-slate-300">Notification Types</label>

                                        {/* Position Opened */}
                                        <div className="flex items-center justify-between bg-slate-950 p-3 rounded-xl border border-slate-800">
                                            <span className="text-sm text-slate-300">Position Opened</span>
                                            <button
                                                onClick={() => setNotifyPositionOpen(!notifyPositionOpen)}
                                                disabled={!discordEnabled}
                                                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${notifyPositionOpen ? 'bg-indigo-500' : 'bg-slate-700'} disabled:opacity-50`}
                                            >
                                                <span className={`${notifyPositionOpen ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                                            </button>
                                        </div>

                                        {/* Position Closed */}
                                        <div className="flex items-center justify-between bg-slate-950 p-3 rounded-xl border border-slate-800">
                                            <span className="text-sm text-slate-300">Position Closed</span>
                                            <button
                                                onClick={() => setNotifyPositionClose(!notifyPositionClose)}
                                                disabled={!discordEnabled}
                                                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${notifyPositionClose ? 'bg-indigo-500' : 'bg-slate-700'} disabled:opacity-50`}
                                            >
                                                <span className={`${notifyPositionClose ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                                            </button>
                                        </div>

                                        {/* Daily Summary */}
                                        <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-3">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <span className="text-sm text-slate-300">Daily Summary</span>
                                                    <p className="text-[10px] text-slate-500">P&L, trades count, balance</p>
                                                </div>
                                                <button
                                                    onClick={() => setNotifyDailySummary(!notifyDailySummary)}
                                                    disabled={!discordEnabled}
                                                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${notifyDailySummary ? 'bg-indigo-500' : 'bg-slate-700'} disabled:opacity-50`}
                                                >
                                                    <span className={`${notifyDailySummary ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                                                </button>
                                            </div>

                                            {notifyDailySummary && discordEnabled && (
                                                <div className="flex items-center gap-3 pt-2 border-t border-slate-800">
                                                    <span className="text-xs text-slate-400">Send at:</span>
                                                    <TimePicker
                                                        value={dailySummaryTime}
                                                        onChange={setDailySummaryTime}
                                                    />
                                                    <span className="text-[10px] text-slate-500">(Only on trading days)</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
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
                    {activeTab === 'notifications' && (
                        <button
                            onClick={saveDiscordSettings}
                            disabled={savingDiscord || !selectedNotifAccountId}
                            className="px-6 py-2 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg flex items-center gap-2 disabled:opacity-50"
                        >
                            <Save size={16} /> {savingDiscord ? 'Saving...' : 'Save Discord Settings'}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
