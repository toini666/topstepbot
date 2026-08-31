/**
 * General Settings Tab Component
 *
 * Contains market hours, trading days, blocked periods, news blocks,
 * position actions, auto-flatten, and risk rules settings.
 */

import { useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import axios from 'axios';
import { Clock, Calendar, Plus, Trash2, ChevronDown, CheckCircle, Newspaper, AlertTriangle, Globe, Radio, Bot } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { TimeBlock, NewsBlock } from '../../types';
import { TimePicker } from '../TimePicker';
import { API_BASE } from '../../config';
import { getUserTimezone, setUserTimezone } from '../../utils/timezone';
import { Toggle } from '../ui';

export interface GeneralSettingsState {
    botName: string;
    blockedPeriodsEnabled: boolean;
    blockedPeriods: TimeBlock[];
    autoFlattenEnabled: boolean;
    autoFlattenTime: string;
    marketOpenTime: string;
    marketCloseTime: string;
    weekendMarketsOpen: boolean;
    tradingDays: string[];
    enforceSinglePosition: boolean;
    blockCrossAccount: boolean;
    newsBlockEnabled: boolean;
    newsBlockBefore: number;
    newsBlockAfter: number;
    positionAction: 'NOTHING' | 'BREAKEVEN' | 'FLATTEN';
    positionActionBuffer: number;
    timezone: string;
    apiTimeout: number;
    jobInterval: number;
    websocketDisabled: boolean;
}

interface GeneralSettingsTabProps {
    state: GeneralSettingsState;
    onChange: <K extends keyof GeneralSettingsState>(key: K, value: GeneralSettingsState[K]) => void;
}

const COMMON_TIMEZONES = [
    'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
    'America/Toronto', 'America/Sao_Paulo',
    'Europe/London', 'Europe/Brussels', 'Europe/Paris', 'Europe/Berlin',
    'Europe/Amsterdam', 'Europe/Madrid', 'Europe/Rome', 'Europe/Zurich',
    'Europe/Moscow',
    'Asia/Dubai', 'Asia/Kolkata', 'Asia/Singapore', 'Asia/Tokyo',
    'Asia/Hong_Kong', 'Asia/Shanghai',
    'Australia/Sydney', 'Pacific/Auckland',
    'UTC',
];

/** Icon + micro-label field heading. Purely presentational grouping helper. */
function FieldLabel({ icon: Icon, children }: { icon: LucideIcon; children: ReactNode }) {
    return (
        <div className="flex items-center gap-2 mb-2">
            <Icon className="w-3.5 h-3.5 text-slate-500" />
            <label className="label mb-0">{children}</label>
        </div>
    );
}

export function GeneralSettingsTab({ state, onChange }: GeneralSettingsTabProps) {
    const [newsBlocks, setNewsBlocks] = useState<NewsBlock[]>([]);
    const [positionActionDropdownOpen, setPositionActionDropdownOpen] = useState(false);
    const [allTimezones, setAllTimezones] = useState<string[]>([]);

    useEffect(() => {
        const fetchNewsBlocks = async () => {
            try {
                const res = await axios.get(`${API_BASE}/dashboard/news-blocks`);
                setNewsBlocks(res.data.blocks || []);
            } catch (e) {
                console.error("Failed to fetch news blocks", e);
            }
        };
        fetchNewsBlocks();
    }, []);

    useEffect(() => {
        const fetchTimezones = async () => {
            try {
                const res = await axios.get(`${API_BASE}/dashboard/timezones`);
                setAllTimezones(res.data.timezones || []);
            } catch {
                // Fallback to common list
                setAllTimezones(COMMON_TIMEZONES);
            }
        };
        fetchTimezones();
    }, []);

    // Build deduplicated timezone list: current value + common + all
    const currentTz = state.timezone || getUserTimezone();
    const tzOptions = [...new Set([currentTz, ...COMMON_TIMEZONES, ...allTimezones])];

    const handleTimezoneChange = (tz: string) => {
        onChange('timezone', tz);
        setUserTimezone(tz);
    };

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (positionActionDropdownOpen && !target.closest('.group-position-action')) {
                setPositionActionDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [positionActionDropdownOpen]);

    const addTimeBlock = () => {
        onChange('blockedPeriods', [...state.blockedPeriods, { start: "00:00", end: "00:00", enabled: true }]);
    };

    const removeTimeBlock = (index: number) => {
        const newBlocks = [...state.blockedPeriods];
        newBlocks.splice(index, 1);
        onChange('blockedPeriods', newBlocks);
    };

    const updateTimeBlock = (index: number, field: keyof TimeBlock, value: any) => {
        const newBlocks = [...state.blockedPeriods];
        newBlocks[index] = { ...newBlocks[index], [field]: value };
        onChange('blockedPeriods', newBlocks);
    };

    const apiTimeoutBadge = state.apiTimeout <= 15 ? 'badge-success' : state.apiTimeout <= 25 ? 'badge-warning' : 'badge-danger';
    const apiTimeoutLabel = state.apiTimeout <= 15 ? 'Low latency' : state.apiTimeout <= 25 ? 'Med latency' : 'High latency';
    const jobIntervalBadge = state.jobInterval <= 15 ? 'badge-info' : state.jobInterval <= 30 ? 'badge-warning' : 'badge-neutral';
    const jobIntervalLabel = state.jobInterval <= 15 ? 'Réactif' : state.jobInterval <= 30 ? 'Modéré' : 'Lent';

    return (
        <div className="space-y-6">
            {/* Bot Name */}
            <div className="space-y-3">
                <FieldLabel icon={Bot}>Bot Name</FieldLabel>
                <input
                    type="text"
                    value={state.botName}
                    onChange={e => onChange('botName', e.target.value)}
                    className="input"
                    placeholder="TopStep Bot"
                />
                <p className="help-text">
                    Shown in the dashboard header and browser tab.
                </p>
            </div>

            <div className="divider-h" />

            {/* Timezone */}
            <div className="space-y-3">
                <FieldLabel icon={Globe}>Timezone</FieldLabel>
                <select
                    value={currentTz}
                    onChange={e => handleTimezoneChange(e.target.value)}
                    className="input"
                >
                    {tzOptions.map(tz => (
                        <option key={tz} value={tz}>{tz}</option>
                    ))}
                </select>
                <p className="help-text">
                    All times (market hours, blocked periods, schedules, logs) use this timezone.
                </p>
            </div>

            <div className="divider-h" />

            {/* Market Hours */}
            <div className="space-y-3">
                <FieldLabel icon={Calendar}>
                    Market Hours <span className="text-slate-500 normal-case font-normal">({currentTz.split('/').pop()?.replace(/_/g, ' ') || currentTz})</span>
                </FieldLabel>
                <div className="flex items-center gap-3">
                    <TimePicker
                        value={state.marketOpenTime}
                        onChange={(val) => onChange('marketOpenTime', val)}
                    />
                    <span className="text-slate-500">to</span>
                    <TimePicker
                        value={state.marketCloseTime}
                        onChange={(val) => onChange('marketCloseTime', val)}
                    />
                </div>

                {/* Weekend Markets Toggle */}
                <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800/60 p-3 rounded-xl">
                    <div>
                        <span className="text-sm text-slate-300">Weekend Markets Open</span>
                        <p className="help-text">Are futures markets open on Saturday/Sunday?</p>
                    </div>
                    <Toggle
                        checked={state.weekendMarketsOpen}
                        onChange={() => onChange('weekendMarketsOpen', !state.weekendMarketsOpen)}
                        size="sm"
                        activeColor="indigo"
                        label="Weekend markets open"
                    />
                </div>
            </div>

            <div className="divider-h" />

            {/* Trading Days */}
            <div className="space-y-3">
                <FieldLabel icon={Calendar}>Trading Days</FieldLabel>
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
                        const isEnabled = state.tradingDays.includes(day.key);
                        return (
                            <button
                                key={day.key}
                                onClick={() => {
                                    if (isEnabled) {
                                        onChange('tradingDays', state.tradingDays.filter(d => d !== day.key));
                                    } else {
                                        onChange('tradingDays', [...state.tradingDays, day.key]);
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
                <p className="help-text">
                    Click to enable/disable trading on each day.
                </p>
            </div>

            <div className="divider-h" />

            {/* Blocked Periods */}
            <div className={`space-y-3 transition-opacity ${!state.blockedPeriodsEnabled ? "opacity-50" : ""}`}>
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <Clock className="w-3.5 h-3.5 text-slate-500" />
                            <label className="label mb-0">Blocked Trading Hours</label>
                        </div>
                        <Toggle
                            checked={state.blockedPeriodsEnabled}
                            onChange={() => onChange('blockedPeriodsEnabled', !state.blockedPeriodsEnabled)}
                            size="sm"
                            activeColor="indigo"
                            label="Blocked trading hours enabled"
                        />
                    </div>
                    <button
                        onClick={addTimeBlock}
                        disabled={!state.blockedPeriodsEnabled}
                        className="text-xs bg-indigo-500/10 text-indigo-300 ring-1 ring-inset ring-indigo-400/20 hover:bg-indigo-500/20 px-2 py-1 rounded-lg flex items-center gap-1 disabled:opacity-40"
                    >
                        <Plus size={12} /> Add
                    </button>
                </div>

                <div className="space-y-2 pr-2">
                    {state.blockedPeriods.map((block, index) => (
                        <div key={index} className={`flex items-center gap-2 bg-slate-900/60 p-2 rounded-xl border ${block.enabled ? 'border-indigo-500/30' : 'border-slate-800/60 opacity-60'}`}>
                            <Toggle
                                checked={block.enabled}
                                onChange={() => updateTimeBlock(index, 'enabled', !block.enabled)}
                                size="sm"
                                activeColor="indigo"
                                label={`Blocked period ${index + 1} enabled`}
                            />
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
                    {state.blockedPeriods.length === 0 && (
                        <p className="text-xs text-slate-500 italic text-center py-2">No blocked periods</p>
                    )}
                </div>
            </div>

            <div className="divider-h" />

            {/* News Block Settings */}
            <div className={`space-y-3 transition-opacity ${!state.newsBlockEnabled ? "opacity-50" : ""}`}>
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <Newspaper className="w-3.5 h-3.5 text-slate-500" />
                            <label className="label mb-0">News Trading Blocks</label>
                        </div>
                        <Toggle
                            checked={state.newsBlockEnabled}
                            onChange={() => onChange('newsBlockEnabled', !state.newsBlockEnabled)}
                            size="sm"
                            activeColor="indigo"
                            label="News trading blocks enabled"
                        />
                    </div>
                </div>

                {state.newsBlockEnabled && (
                    <div className="space-y-3 pl-6">
                        <p className="help-text mt-0">
                            Automatically block trading around major economic events.
                        </p>
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-slate-400">Block</span>
                                <input
                                    type="number"
                                    value={state.newsBlockBefore}
                                    onChange={(e) => onChange('newsBlockBefore', Number(e.target.value))}
                                    className="input-mono !w-16 text-center"
                                    min={0}
                                />
                                <span className="text-sm text-slate-400">min before</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-slate-400">and</span>
                                <input
                                    type="number"
                                    value={state.newsBlockAfter}
                                    onChange={(e) => onChange('newsBlockAfter', Number(e.target.value))}
                                    className="input-mono !w-16 text-center"
                                    min={0}
                                />
                                <span className="text-sm text-slate-400">min after</span>
                            </div>
                        </div>

                        {/* Today's News Blocks Display */}
                        {newsBlocks.length > 0 ? (
                            <div className="space-y-2">
                                <div className="flex items-center gap-2">
                                    <span className="micro-label">Today's Blocks</span>
                                    <span className="badge-warning">Today only</span>
                                </div>
                                <div className="space-y-1">
                                    {newsBlocks.map((block, idx) => (
                                        <div key={idx} className="flex items-center gap-2 text-xs bg-slate-900/60 p-2 rounded-lg">
                                            <span className={`w-2 h-2 rounded-full ${block.impact === 'High' ? 'bg-red-500' : block.impact === 'Medium' ? 'bg-amber-500' : 'bg-emerald-500'}`} />
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

            <div className="divider-h" />

            {/* Position Action on Blocked Hours */}
            <div className="space-y-3">
                <FieldLabel icon={AlertTriangle}>Position Action on Blocked Hours</FieldLabel>

                <div className="pl-6 space-y-3">
                    <div className="flex items-center gap-4">
                        {/* Custom Dropdown */}
                        <div className="relative group-position-action">
                            <button
                                onClick={() => setPositionActionDropdownOpen(!positionActionDropdownOpen)}
                                className="input !w-auto min-w-[200px] flex items-center justify-between gap-3 text-sm hover:border-indigo-400/40"
                            >
                                <span>
                                    {state.positionAction === 'NOTHING' && 'Do Nothing'}
                                    {state.positionAction === 'BREAKEVEN' && 'Move SL to Breakeven'}
                                    {state.positionAction === 'FLATTEN' && 'Flatten All Positions'}
                                </span>
                                <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${positionActionDropdownOpen ? 'rotate-180' : ''}`} />
                            </button>

                            {positionActionDropdownOpen && (
                                <div className="dropdown-menu top-full left-0 mt-2 w-full">
                                    <div className="p-1">
                                        {[
                                            { value: 'NOTHING', label: 'Do Nothing' },
                                            { value: 'BREAKEVEN', label: 'Move SL to Breakeven' },
                                            { value: 'FLATTEN', label: 'Flatten All Positions' }
                                        ].map((option) => (
                                            <button
                                                key={option.value}
                                                onClick={() => {
                                                    onChange('positionAction', option.value as any);
                                                    setPositionActionDropdownOpen(false);
                                                }}
                                                className={state.positionAction === option.value ? 'dropdown-item-active rounded-lg' : 'dropdown-item rounded-lg'}
                                            >
                                                <span>{option.label}</span>
                                                {state.positionAction === option.value && <CheckCircle className="w-3.5 h-3.5" />}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {state.positionAction !== 'NOTHING' && (
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-slate-400">Buffer:</span>
                                <input
                                    type="number"
                                    value={state.positionActionBuffer}
                                    onChange={(e) => onChange('positionActionBuffer', Number(e.target.value))}
                                    className="input-mono !w-16 text-center"
                                    min={1}
                                />
                                <span className="text-sm text-slate-400">min</span>
                            </div>
                        )}
                    </div>

                    {state.positionAction !== 'NOTHING' && (
                        <div className="flex items-start gap-2 text-xs text-slate-400">
                            <AlertTriangle className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${state.positionAction === 'FLATTEN' ? 'text-red-400' : 'text-amber-400'}`} />
                            <span>
                                {state.positionAction === 'BREAKEVEN' && "Stop Loss will be moved to entry price for all open positions."}
                                {state.positionAction === 'FLATTEN' && "All positions will be closed and orders cancelled."}
                            </span>
                        </div>
                    )}
                </div>
            </div>

            {/* Auto Flatten */}
            <div className="space-y-3 pt-4 border-t border-slate-800/60">
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <label className="label mb-0">Auto-Flatten (All Accounts)</label>
                        <Toggle
                            checked={state.autoFlattenEnabled}
                            onChange={() => onChange('autoFlattenEnabled', !state.autoFlattenEnabled)}
                            size="sm"
                            activeColor="indigo"
                            label="Auto-flatten enabled"
                        />
                    </div>
                    <TimePicker
                        value={state.autoFlattenTime}
                        onChange={(val) => onChange('autoFlattenTime', val)}
                        disabled={!state.autoFlattenEnabled}
                    />
                </div>
                <p className="help-text flex items-start gap-1.5">
                    <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0 text-amber-400" />
                    <span>Closes ALL positions and cancels ALL orders across ALL accounts at this time.</span>
                </p>
            </div>

            {/* Risk Rules */}
            <div className="space-y-3 pt-4 border-t border-slate-800/60">
                <label className="label">Risk Rules</label>

                {/* Single Position per Asset */}
                <div className="flex justify-between items-center">
                    <div>
                        <span className="text-sm text-slate-300">Single Position Per Asset</span>
                        <p className="help-text">Prevent opening 2 positions on the same asset</p>
                    </div>
                    <Toggle
                        checked={state.enforceSinglePosition}
                        onChange={() => onChange('enforceSinglePosition', !state.enforceSinglePosition)}
                        size="sm"
                        activeColor="indigo"
                        label="Enforce single position per asset"
                    />
                </div>

                {/* Block Cross-Account Opposite */}
                <div className="flex justify-between items-center">
                    <div>
                        <span className="text-sm text-slate-300">Block Cross-Account Opposite</span>
                        <p className="help-text">Prevent LONG on one account if SHORT on another</p>
                    </div>
                    <Toggle
                        checked={state.blockCrossAccount}
                        onChange={() => onChange('blockCrossAccount', !state.blockCrossAccount)}
                        size="sm"
                        activeColor="indigo"
                        label="Block cross-account opposite positions"
                    />
                </div>

                {/* Manual Trading Mode */}
                <div className="flex justify-between items-center p-3 rounded-xl border border-slate-800/60 bg-slate-900/60">
                    <div>
                        <span className="text-sm text-slate-300 flex items-center gap-1.5">
                            <Radio className={`w-3.5 h-3.5 ${state.websocketDisabled ? 'text-amber-400' : 'text-slate-500'}`} />
                            Mode trading manuel
                        </span>
                        <p className="help-text">Désactive le WebSocket pour trader manuellement sur TopstepX en parallèle</p>
                        {state.websocketDisabled && (
                            <p className="text-[10px] text-amber-400 mt-0.5">WebSocket désactivé — prix via polling HTTP uniquement</p>
                        )}
                    </div>
                    <Toggle
                        checked={state.websocketDisabled}
                        onChange={() => onChange('websocketDisabled', !state.websocketDisabled)}
                        size="sm"
                        activeColor="indigo"
                        className={state.websocketDisabled ? 'bg-amber-500/90 border-amber-400/50 shadow-[0_0_12px_-2px_rgba(251,191,36,0.5)]' : undefined}
                        label="Manual trading mode (WebSocket disabled)"
                    />
                </div>
            </div>

            {/* Network / Performance */}
            <div className="space-y-3 pt-4 border-t border-slate-800/60">
                <div className="flex items-center justify-between">
                    <label className="label mb-0">Network / Performance</label>
                    <div className="flex gap-1.5">
                        <button
                            type="button"
                            onClick={() => { onChange('apiTimeout', 15); onChange('jobInterval', 10); }}
                            className="text-[10px] px-2 py-0.5 rounded-full border border-indigo-500/40 text-indigo-400 hover:bg-indigo-500/10 transition-colors"
                        >
                            Brussels
                        </button>
                        <button
                            type="button"
                            onClick={() => { onChange('apiTimeout', 25); onChange('jobInterval', 30); }}
                            className="text-[10px] px-2 py-0.5 rounded-full border border-amber-500/40 text-amber-400 hover:bg-amber-500/10 transition-colors"
                        >
                            Thailand
                        </button>
                    </div>
                </div>

                {/* API Timeout */}
                <div className="bg-slate-900/60 rounded-xl p-3 space-y-2 border border-slate-800/60">
                    <div className="flex justify-between items-center">
                        <div>
                            <span className="text-sm text-slate-300">API Timeout</span>
                            <span className="text-[10px] text-slate-500 ml-1.5">seconds</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className={apiTimeoutBadge}>{apiTimeoutLabel}</span>
                            <input
                                type="number"
                                min={3}
                                max={60}
                                value={state.apiTimeout}
                                onChange={e => onChange('apiTimeout', Math.max(3, Math.min(60, Number(e.target.value))))}
                                className="input-mono !w-16 text-center"
                            />
                        </div>
                    </div>
                    <p className="help-text mt-0">Temps max d'attente par requête TopStep. Si la requête dépasse ce délai, elle est annulée et retentée.</p>
                </div>

                {/* Job Interval */}
                <div className="bg-slate-900/60 rounded-xl p-3 space-y-2 border border-slate-800/60">
                    <div className="flex justify-between items-center">
                        <div>
                            <span className="text-sm text-slate-300">Job Interval</span>
                            <span className="text-[10px] text-slate-500 ml-1.5">seconds</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className={jobIntervalBadge}>{jobIntervalLabel}</span>
                            <input
                                type="number"
                                min={5}
                                max={60}
                                value={state.jobInterval}
                                onChange={e => onChange('jobInterval', Math.max(5, Math.min(60, Number(e.target.value))))}
                                className="input-mono !w-16 text-center"
                            />
                        </div>
                    </div>
                    <p className="help-text mt-0">Fréquence de vérification des positions. Nécessite un redémarrage pour être pris en compte.</p>
                </div>
            </div>
        </div>
    );
}
