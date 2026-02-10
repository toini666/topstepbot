/**
 * General Settings Tab Component
 * 
 * Contains market hours, trading days, blocked periods, news blocks,
 * position actions, auto-flatten, and risk rules settings.
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { Clock, Calendar, Plus, Trash2, ChevronDown, CheckCircle, Newspaper, AlertTriangle, Globe } from 'lucide-react';
import type { TimeBlock, NewsBlock } from '../../types';
import { TimePicker } from '../TimePicker';
import { API_BASE } from '../../config';
import { getUserTimezone, setUserTimezone } from '../../utils/timezone';

export interface GeneralSettingsState {
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

    return (
        <div className="space-y-6">
            {/* Timezone */}
            <div className="space-y-3">
                <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                    <Globe className="w-4 h-4 text-slate-400" />
                    Timezone
                </label>
                <select
                    value={currentTz}
                    onChange={e => handleTimezoneChange(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
                >
                    {tzOptions.map(tz => (
                        <option key={tz} value={tz}>{tz}</option>
                    ))}
                </select>
                <p className="text-[10px] text-slate-500 italic">
                    All times (market hours, blocked periods, schedules, logs) use this timezone.
                </p>
            </div>

            {/* Market Hours */}
            <div className="space-y-3">
                <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-slate-400" />
                    Market Hours ({currentTz.split('/').pop()?.replace(/_/g, ' ') || currentTz})
                </label>
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
                <div className="flex items-center justify-between bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <div>
                        <span className="text-sm text-slate-300">Weekend Markets Open</span>
                        <p className="text-[10px] text-slate-500">Are futures markets open on Saturday/Sunday?</p>
                    </div>
                    <button
                        onClick={() => onChange('weekendMarketsOpen', !state.weekendMarketsOpen)}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${state.weekendMarketsOpen ? 'bg-indigo-500' : 'bg-slate-700'}`}
                    >
                        <span className={`${state.weekendMarketsOpen ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
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
                <p className="text-[10px] text-slate-500 italic">
                    Click to enable/disable trading on each day.
                </p>
            </div>

            {/* Blocked Periods */}
            <div className={`space-y-3 transition-opacity ${!state.blockedPeriodsEnabled ? "opacity-50" : ""}`}>
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                            <Clock className="w-4 h-4 text-slate-400" />
                            Blocked Trading Hours
                        </label>
                        <button
                            onClick={() => onChange('blockedPeriodsEnabled', !state.blockedPeriodsEnabled)}
                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${state.blockedPeriodsEnabled ? 'bg-indigo-500' : 'bg-slate-700'
                                }`}
                        >
                            <span className={`${state.blockedPeriodsEnabled ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                        </button>
                    </div>
                    <button
                        onClick={addTimeBlock}
                        disabled={!state.blockedPeriodsEnabled}
                        className="text-xs bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 px-2 py-1 rounded-lg flex items-center gap-1 disabled:opacity-50"
                    >
                        <Plus size={12} /> Add
                    </button>
                </div>

                <div className="space-y-2 pr-2">
                    {state.blockedPeriods.map((block, index) => (
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
                    {state.blockedPeriods.length === 0 && (
                        <p className="text-xs text-slate-500 italic text-center py-2">No blocked periods</p>
                    )}
                </div>
            </div>

            {/* News Block Settings */}
            <div className={`space-y-3 transition-opacity ${!state.newsBlockEnabled ? "opacity-50" : ""}`}>
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <label className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                            <Newspaper className="w-4 h-4 text-slate-400" />
                            News Trading Blocks
                        </label>
                        <button
                            onClick={() => onChange('newsBlockEnabled', !state.newsBlockEnabled)}
                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${state.newsBlockEnabled ? 'bg-indigo-500' : 'bg-slate-700'}`}
                        >
                            <span className={`${state.newsBlockEnabled ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                        </button>
                    </div>
                </div>

                {state.newsBlockEnabled && (
                    <div className="space-y-3 pl-6">
                        <p className="text-[10px] text-slate-500 italic">
                            Automatically block trading around major economic events.
                        </p>
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-slate-400">Block</span>
                                <input
                                    type="number"
                                    value={state.newsBlockBefore}
                                    onChange={(e) => onChange('newsBlockBefore', Number(e.target.value))}
                                    className="w-16 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors font-mono text-center"
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
                                    {state.positionAction === 'NOTHING' && 'Do Nothing'}
                                    {state.positionAction === 'BREAKEVEN' && 'Move SL to Breakeven'}
                                    {state.positionAction === 'FLATTEN' && 'Flatten All Positions'}
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
                                                    onChange('positionAction', option.value as any);
                                                    setPositionActionDropdownOpen(false);
                                                }}
                                                className={`w-full text-left px-3 py-2 rounded-lg flex items-center justify-between transition-colors text-sm ${state.positionAction === option.value
                                                    ? 'bg-indigo-500/10 text-indigo-400'
                                                    : 'text-slate-300 hover:bg-slate-700/50'
                                                    }`}
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
                                    className="w-16 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors font-mono text-center"
                                    min={1}
                                />
                                <span className="text-sm text-slate-400">min</span>
                            </div>
                        )}
                    </div>

                    {state.positionAction !== 'NOTHING' && (
                        <div className={`text-[10px] p-2 rounded-lg inline-block ${state.positionAction === 'FLATTEN' ? 'bg-red-500/10 text-red-400' : 'bg-amber-500/10 text-amber-400'}`}>
                            {state.positionAction === 'BREAKEVEN' && "Stop Loss will be moved to entry price for all open positions."}
                            {state.positionAction === 'FLATTEN' && "All positions will be closed and orders cancelled."}
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
                            onClick={() => onChange('autoFlattenEnabled', !state.autoFlattenEnabled)}
                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${state.autoFlattenEnabled ? 'bg-indigo-500' : 'bg-slate-700'
                                }`}
                        >
                            <span className={`${state.autoFlattenEnabled ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                        </button>
                    </div>
                    <TimePicker
                        value={state.autoFlattenTime}
                        onChange={(val) => onChange('autoFlattenTime', val)}
                        disabled={!state.autoFlattenEnabled}
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
                        onClick={() => onChange('enforceSinglePosition', !state.enforceSinglePosition)}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${state.enforceSinglePosition ? 'bg-indigo-500' : 'bg-slate-700'}`}
                    >
                        <span className={`${state.enforceSinglePosition ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                    </button>
                </div>

                {/* Block Cross-Account Opposite */}
                <div className="flex justify-between items-center">
                    <div>
                        <span className="text-sm text-slate-300">Block Cross-Account Opposite</span>
                        <p className="text-[10px] text-slate-500">Prevent LONG on one account if SHORT on another</p>
                    </div>
                    <button
                        onClick={() => onChange('blockCrossAccount', !state.blockCrossAccount)}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${state.blockCrossAccount ? 'bg-indigo-500' : 'bg-slate-700'}`}
                    >
                        <span className={`${state.blockCrossAccount ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
                    </button>
                </div>
            </div>
        </div>
    );
}
