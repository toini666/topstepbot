import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { X, Save, Settings, Bell } from 'lucide-react';
import { toast } from 'sonner';
import type { GlobalConfig, TickerMap, TradingSession, Account } from '../types';
import { TickerMapping } from './TickerMapping';
import { API_BASE } from '../config';
import { GeneralSettingsTab, SessionsTab, NotificationsTab, type GeneralSettingsState } from './config-tabs';

interface ConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
    config: GlobalConfig;
    onSave: (newConfig: Partial<GlobalConfig>) => Promise<void>;
}

export function ConfigModal({ isOpen, onClose, config, onSave }: ConfigModalProps) {
    const [activeTab, setActiveTab] = useState<'general' | 'sessions' | 'mappings' | 'notifications'>('general');
    const [saving, setSaving] = useState(false);
    const initializedRef = useRef(false);

    // === General Settings State ===
    const [generalState, setGeneralState] = useState<GeneralSettingsState>({
        blockedPeriodsEnabled: true,
        blockedPeriods: [],
        autoFlattenEnabled: false,
        autoFlattenTime: "21:55",
        marketOpenTime: "00:00",
        marketCloseTime: "22:00",
        weekendMarketsOpen: false,
        tradingDays: ['MON', 'TUE', 'WED', 'THU', 'FRI'],
        enforceSinglePosition: true,
        blockCrossAccount: true,
        newsBlockEnabled: false,
        newsBlockBefore: 5,
        newsBlockAfter: 5,
        positionAction: 'NOTHING',
        positionActionBuffer: 1
    });

    // === Sessions State ===
    const [sessions, setSessions] = useState<TradingSession[]>([]);
    const [sessionsModified, setSessionsModified] = useState<Record<number, TradingSession>>({});

    // === Mappings State ===
    const [mappings, setMappings] = useState<TickerMap[]>([]);

    // === Notifications State ===
    const [accounts, setAccounts] = useState<Account[]>([]);

    // Initialization
    useEffect(() => {
        if (isOpen && !initializedRef.current) {
            setGeneralState({
                blockedPeriodsEnabled: config.blocked_periods_enabled,
                blockedPeriods: [...config.blocked_periods],
                autoFlattenEnabled: config.auto_flatten_enabled ?? false,
                autoFlattenTime: config.auto_flatten_time || "21:55",
                marketOpenTime: config.market_open_time || "00:00",
                marketCloseTime: config.market_close_time || "22:00",
                weekendMarketsOpen: config.weekend_markets_open ?? false,
                tradingDays: config.trading_days || ['MON', 'TUE', 'WED', 'THU', 'FRI'],
                enforceSinglePosition: config.enforce_single_position_per_asset ?? true,
                blockCrossAccount: config.block_cross_account_opposite ?? true,
                newsBlockEnabled: config.news_block_enabled ?? false,
                newsBlockBefore: config.news_block_before_minutes ?? 5,
                newsBlockAfter: config.news_block_after_minutes ?? 5,
                positionAction: config.blocked_hours_position_action ?? 'NOTHING',
                positionActionBuffer: config.position_action_buffer_minutes ?? 1
            });

            fetchSessions();
            fetchMappings();
            fetchAccounts();
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

    const fetchAccounts = async () => {
        try {
            const res = await axios.get(`${API_BASE}/dashboard/accounts`);
            setAccounts(res.data);
        } catch (e) {
            console.error("Failed to fetch accounts", e);
        }
    };

    // === Handlers ===

    const handleGeneralChange = <K extends keyof GeneralSettingsState>(key: K, value: GeneralSettingsState[K]) => {
        setGeneralState(prev => ({ ...prev, [key]: value }));
    };

    const handleUpdateSession = (id: number, field: keyof TradingSession, value: any) => {
        const session = sessions.find(s => s.id === id);
        if (!session) return;
        const updated = { ...session, [field]: value };
        setSessions(sessions.map(s => s.id === id ? updated : s));
        setSessionsModified(prev => ({ ...prev, [id]: updated }));
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
                setMappings(mappings.map(m => m.id === id ? { ...m, ...updates } : m));
                toast.success("Mapping Updated");
            }
        } catch (e) {
            toast.error("Error updating mapping");
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            // Save Global Config
            await onSave({
                blocked_periods_enabled: generalState.blockedPeriodsEnabled,
                blocked_periods: generalState.blockedPeriods,
                auto_flatten_enabled: generalState.autoFlattenEnabled,
                auto_flatten_time: generalState.autoFlattenTime,
                market_open_time: generalState.marketOpenTime,
                market_close_time: generalState.marketCloseTime,
                weekend_markets_open: generalState.weekendMarketsOpen,
                trading_days: generalState.tradingDays,
                enforce_single_position_per_asset: generalState.enforceSinglePosition,
                block_cross_account_opposite: generalState.blockCrossAccount,
                news_block_enabled: generalState.newsBlockEnabled,
                news_block_before_minutes: generalState.newsBlockBefore,
                news_block_after_minutes: generalState.newsBlockAfter,
                blocked_hours_position_action: generalState.positionAction,
                position_action_buffer_minutes: generalState.positionActionBuffer
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

    if (!isOpen) return null;

    const configTabs = [
        { key: 'general' as const, label: 'General' },
        { key: 'sessions' as const, label: 'Sessions' },
        { key: 'mappings' as const, label: 'Mappings' },
        { key: 'notifications' as const, label: 'Notifications', icon: Bell },
    ];

    return (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="config-title">
            <div
                className="modal-container w-full max-w-lg flex flex-col max-h-[90vh]"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-slate-800 bg-slate-900/50 shrink-0">
                    <h3 id="config-title" className="text-xl font-bold text-white flex items-center gap-2">
                        <Settings className="w-5 h-5 text-indigo-400" />
                        Global Settings
                    </h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors" aria-label="Close settings">
                        <X size={20} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-slate-800 bg-slate-950/30 px-6 shrink-0" role="tablist" aria-label="Settings sections">
                    {configTabs.map(tab => (
                        <button
                            key={tab.key}
                            role="tab"
                            aria-selected={activeTab === tab.key}
                            onClick={() => setActiveTab(tab.key)}
                            className={`py-3 px-4 text-sm font-medium border-b-2 transition-colors capitalize ${activeTab === tab.key
                                ? 'border-indigo-500 text-white'
                                : 'border-transparent text-slate-400 hover:text-white'
                                }`}
                        >
                            {tab.icon ? (
                                <span className="flex items-center gap-1">
                                    <tab.icon size={14} /> {tab.label}
                                </span>
                            ) : tab.label}
                        </button>
                    ))}
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto custom-scrollbar" role="tabpanel">
                    {activeTab === 'general' && (
                        <GeneralSettingsTab state={generalState} onChange={handleGeneralChange} />
                    )}

                    {activeTab === 'sessions' && (
                        <SessionsTab sessions={sessions} onUpdateSession={handleUpdateSession} />
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
                        <NotificationsTab accounts={accounts} />
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-slate-800 bg-slate-900/50 flex justify-end gap-3 shrink-0">
                    <button onClick={onClose} className="btn-ghost">
                        Cancel
                    </button>
                    {(activeTab === 'general' || activeTab === 'sessions') && (
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="btn-primary"
                        >
                            <Save size={16} /> {saving ? 'Saving...' : 'Save Changes'}
                        </button>
                    )}
                    {activeTab === 'mappings' && (
                        <button onClick={onClose} className="btn-primary">
                            Done
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
