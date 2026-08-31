
import { useState, useEffect } from 'react';
import type { CSSProperties } from 'react';
import { createPortal } from 'react-dom';
import axios from 'axios';
import { Calendar as CalendarIcon, RefreshCw, Bell, Settings, CheckCircle, Filter, X, Globe, ChevronDown, Check } from 'lucide-react';
import { API_BASE } from '../config';
import { formatInUserTz } from '../utils/timezone';
import { toast } from 'sonner';
import { cn } from '../utils/cn';
import { Card, CardHeader, Badge, SegmentedControl, EmptyState, Toggle, Button } from './ui';

interface CalendarEvent {
    title: string;
    country: string;
    date: string; // MM-DD-YYYY
    time: string; // HH:MMam/pm
    impact: string;
    forecast: string;
    previous: string;
}

interface CalendarSettings {
    discord_url: string;
    enabled: boolean;
    major_countries: string[];
    major_impacts: string[];
    news_alert_enabled: boolean;
    news_alert_minutes: number;
}

const IMPACT_OPTIONS = [
    { value: 'ALL', label: 'ALL' },
    { value: 'High', label: 'High' },
    { value: 'Medium', label: 'Medium' },
    { value: 'Low', label: 'Low' },
];

const TIMEFRAME_OPTIONS = [
    { value: 'Today', label: 'Today' },
    { value: 'Week', label: 'Week' },
] as const;

/** Impact level -> badge tone. Presentational mapping only. */
const impactVariant = (impact: string): 'danger' | 'warning' | 'neutral' => {
    if (impact === 'High') return 'danger';
    if (impact === 'Medium') return 'warning';
    return 'neutral';
};

export function Calendar() {
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [settings, setSettings] = useState<CalendarSettings>({
        discord_url: '',
        enabled: false,
        major_countries: ['USD'],
        major_impacts: ['High', 'Medium'],
        news_alert_enabled: false,
        news_alert_minutes: 5,
    });
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [saving, setSaving] = useState(false);

    // Filters
    const [filterImpact, setFilterImpact] = useState<string>('ALL');
    const [filterTimeframe, setFilterTimeframe] = useState<'Today' | 'Week'>('Week');
    const [filterCountry, setFilterCountry] = useState<string>('ALL');
    const [countryDropdownOpen, setCountryDropdownOpen] = useState(false);

    useEffect(() => {
        fetchData();
        fetchSettings();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const res = await axios.get(`${API_BASE}/calendar/`);
            setEvents(res.data);
        } catch (e) {
            console.error(e);
            toast.error("Failed to load calendar");
        } finally {
            setLoading(false);
        }
    };

    const fetchSettings = async () => {
        try {
            const res = await axios.get(`${API_BASE}/calendar/settings`);
            setSettings(res.data);
        } catch (e) {
            console.error(e);
        }
    };

    const saveSettings = async () => {
        setSaving(true);
        try {
            await axios.post(`${API_BASE}/calendar/settings`, settings);
            toast.success("Settings saved");
            setSettingsOpen(false);
        } catch (e) {
            toast.error("Failed to save settings");
        } finally {
            setSaving(false);
        }
    };

    const refreshCalendar = async () => {
        setLoading(true);
        try {
            const res = await axios.get(`${API_BASE}/calendar/refresh`);
            setEvents(res.data);
            toast.success("Calendar refreshed");
        } catch (e) {
            toast.error("Failed to refresh");
        } finally {
            setLoading(false);
        }
    };

    const testNotification = async () => {
        try {
            await axios.post(`${API_BASE}/calendar/test-notification`);
            toast.success("Test notification sent (check Discord)");
        } catch (e) {
            toast.error("Failed to send test");
        }
    };

    // Helper to get Today's events
    const todayStr = formatInUserTz(new Date(), 'MM-dd-yyyy');
    const todaysEvents = events.filter(e => e.date === todayStr);

    // Helper to get unique countries
    const uniqueCountries = Array.from(new Set(events.map(ev => ev.country))).sort();

    // Helper to verify major event based on SETTINGS
    const isMajorEvent = (ev: CalendarEvent) => {
        const isImpactMajor = settings.major_impacts.includes(ev.impact);
        const isCountryMajor = settings.major_countries.includes(ev.country);
        return isImpactMajor && isCountryMajor;
    };

    const majorToday = todaysEvents.filter(e => isMajorEvent(e));

    const filteredEvents = events.filter(ev => {
        if (filterTimeframe === 'Today' && ev.date !== todayStr) return false;
        if (filterImpact !== 'ALL' && ev.impact !== filterImpact) return false;
        if (filterCountry !== 'ALL' && ev.country !== filterCountry) return false;
        return true;
    });

    // Helper to toggle array items
    const toggleArrayItem = (arr: string[], item: string) => {
        if (arr.includes(item)) return arr.filter(i => i !== item);
        return [...arr, item];
    };

    // Helper to format date display (MM-DD-YYYY -> DD-MM-YYYY)
    const formatDateDisplay = (dateStr: string) => {
        if (!dateStr) return '';
        const parts = dateStr.split('-');
        if (parts.length !== 3) return dateStr;
        return `${parts[1]}-${parts[0]}-${parts[2]}`;
    };

    // Helper component for stylized checkbox
    const StyledCheckbox = ({ checked, onChange, label }: { checked: boolean, onChange: () => void, label: string }) => (
        <div
            onClick={onChange}
            role="checkbox"
            aria-checked={checked}
            tabIndex={0}
            onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onChange(); } }}
            className={cn(
                'flex items-center gap-3 p-3 rounded-xl border cursor-pointer select-none transition-all',
                checked
                    ? 'bg-indigo-500/10 border-indigo-500/30 text-white'
                    : 'bg-slate-900/40 border-slate-800/60 text-slate-400 hover:border-slate-700'
            )}
        >
            <div className={cn(
                'w-5 h-5 rounded-md border flex items-center justify-center transition-colors flex-shrink-0',
                checked ? 'bg-indigo-500 border-indigo-500' : 'border-slate-700 bg-slate-950/60'
            )}>
                {checked && <Check className="w-3.5 h-3.5 text-white" />}
            </div>
            <span className="text-sm font-medium">{label}</span>
        </div>
    );

    return (
        <div className="space-y-8">

            {/* Header */}
            <div className="flex justify-between items-center">
                <h2 className="section-title">
                    <CalendarIcon className="w-5 h-5 text-indigo-400" />
                    Economic Calendar
                </h2>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        icon={RefreshCw}
                        loading={loading}
                        onClick={refreshCalendar}
                        title="Refresh Calendar"
                    >
                        Refresh
                    </Button>
                    <button
                        onClick={() => setSettingsOpen(!settingsOpen)}
                        className={cn(
                            'p-2 rounded-lg transition-colors border',
                            settings.enabled
                                ? 'text-indigo-300 border-indigo-500/40 bg-indigo-500/10'
                                : 'text-slate-400 border-slate-700/60 hover:text-white hover:bg-slate-800/60'
                        )}
                        title="Notification Settings"
                        aria-label="Notification settings"
                    >
                        <Settings className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Settings Modal */}
            {settingsOpen && createPortal(
                <div className="modal-backdrop" style={{ zIndex: 9999 }}>
                    <div className="modal-container w-full max-w-lg p-6" style={{ zIndex: 10000 }}>
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold text-white flex items-center gap-2">
                                <Bell className="w-5 h-5 text-indigo-400" />
                                Calendar Settings
                            </h3>
                            <button
                                onClick={() => setSettingsOpen(false)}
                                className="text-slate-400 hover:text-white transition-colors"
                                aria-label="Close settings"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="space-y-6">
                            <div className="flex items-center justify-between p-4 rounded-xl border border-slate-800/60 bg-slate-900/40">
                                <div>
                                    <p className="font-medium text-slate-200 text-sm">Daily Summary</p>
                                    <p className="help-text">Receive a daily summary of major events at 7:00 AM</p>
                                </div>
                                <Toggle
                                    checked={settings.enabled}
                                    onChange={() => setSettings({ ...settings, enabled: !settings.enabled })}
                                    activeColor="indigo"
                                    label="Daily summary notifications"
                                />
                            </div>

                            {/* Pre-News Alerts Section */}
                            <div className="flex items-center justify-between p-4 rounded-xl border border-slate-800/60 bg-slate-900/40">
                                <div>
                                    <p className="font-medium text-slate-200 text-sm">Pre-News Alerts</p>
                                    <p className="help-text">Receive a warning {settings.news_alert_minutes} minutes before major events</p>
                                </div>
                                <Toggle
                                    checked={settings.news_alert_enabled}
                                    onChange={() => setSettings({ ...settings, news_alert_enabled: !settings.news_alert_enabled })}
                                    activeColor="indigo"
                                    label="Pre-news alerts"
                                />
                            </div>

                            {settings.news_alert_enabled && (
                                <div className="animate-fade-in-down">
                                    <label className="label">Minutes Before Event</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="60"
                                        value={settings.news_alert_minutes}
                                        onChange={(e) => setSettings({ ...settings, news_alert_minutes: parseInt(e.target.value) || 5 })}
                                        className="input-mono"
                                    />
                                </div>
                            )}

                            {settings.enabled && (
                                <div className="animate-fade-in-down">
                                    <label className="label">Discord Webhook URL</label>
                                    <input
                                        type="text"
                                        value={settings.discord_url}
                                        onChange={(e) => setSettings({ ...settings, discord_url: e.target.value })}
                                        placeholder="https://discord.com/api/webhooks/..."
                                        className="input-mono"
                                    />
                                </div>
                            )}

                            <div className="divider-h" />

                            <div className="space-y-3">
                                <label className="block text-sm font-semibold text-slate-200">Definition of "Major Event"</label>
                                <p className="help-text -mt-1">Select criteria for daily notifications and dashboard highlights.</p>

                                <div className="grid grid-cols-2 gap-6">
                                    <div>
                                        <label className="micro-label mb-3 block">Impacts</label>
                                        <div className="flex flex-col gap-2">
                                            {['High', 'Medium', 'Low'].map(imp => (
                                                <StyledCheckbox
                                                    key={imp}
                                                    label={imp}
                                                    checked={settings.major_impacts.includes(imp)}
                                                    onChange={() => setSettings({ ...settings, major_impacts: toggleArrayItem(settings.major_impacts, imp) })}
                                                />
                                            ))}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="flex justify-between items-center mb-3">
                                            <label className="micro-label">Countries</label>
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => setSettings({ ...settings, major_countries: uniqueCountries })}
                                                    className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold uppercase"
                                                >
                                                    All
                                                </button>
                                                <span className="text-slate-700">|</span>
                                                <button
                                                    onClick={() => setSettings({ ...settings, major_countries: [] })}
                                                    className="text-[10px] text-slate-500 hover:text-slate-400 font-bold uppercase"
                                                >
                                                    None
                                                </button>
                                            </div>
                                        </div>
                                        <div className="space-y-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                                            {uniqueCountries.map(c => (
                                                <StyledCheckbox
                                                    key={c}
                                                    label={c}
                                                    checked={settings.major_countries.includes(c)}
                                                    onChange={() => setSettings({ ...settings, major_countries: toggleArrayItem(settings.major_countries, c) })}
                                                />
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="divider-h" />

                            <div className="flex justify-end gap-3">
                                <Button variant="outline" onClick={testNotification}>
                                    Test Notification
                                </Button>
                                <Button variant="primary" onClick={saveSettings} loading={saving}>
                                    Save Changes
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>,
                document.body
            )}

            {/* Today's Highlights */}
            <Card>
                <CardHeader
                    icon={CalendarIcon}
                    title="Today's Major Events"
                    annotation={formatDateDisplay(todayStr)}
                />
                {majorToday.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {majorToday.map((ev, idx) => (
                            <div
                                key={idx}
                                style={{ '--i': idx } as CSSProperties}
                                className={cn(
                                    'animate-stagger p-4 rounded-xl border',
                                    ev.impact === 'High' ? 'bg-red-500/5 border-red-500/20' : 'bg-amber-500/5 border-amber-500/20'
                                )}
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <Badge variant={impactVariant(ev.impact)}>{ev.impact.toUpperCase()}</Badge>
                                    <span className="font-mono text-sm text-slate-400">{ev.time}</span>
                                </div>
                                <div className="font-bold text-slate-200 mb-1">{ev.country} - {ev.title}</div>
                                <div className="text-xs text-slate-500 flex justify-between mt-3 pt-3 border-t border-slate-800/50">
                                    <span>Fcst: <span className="text-slate-300 font-mono">{ev.forecast || '-'}</span></span>
                                    <span>Prev: <span className="text-slate-300 font-mono">{ev.previous || '-'}</span></span>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <EmptyState
                        icon={CheckCircle}
                        title="No major events remaining today"
                        hint="Filtered by your major-impact and major-country criteria in Settings."
                    />
                )}
            </Card>

            {/* Full Weekly Calendar Table */}
            <Card>
                <CardHeader
                    icon={CalendarIcon}
                    iconClassName="text-slate-400"
                    title="Weekly Schedule"
                    actions={
                        <div className="flex flex-wrap items-center gap-4">
                            {/* Timeframe Filter */}
                            <SegmentedControl
                                options={TIMEFRAME_OPTIONS}
                                value={filterTimeframe}
                                onChange={setFilterTimeframe}
                                aria-label="Timeframe filter"
                            />

                            <div className="h-4 w-px bg-slate-800" />

                            {/* Impact Filter */}
                            <div className="flex items-center gap-2">
                                <Filter className="w-4 h-4 text-slate-500" />
                                <span className="micro-label mr-1 hidden md:block">Impact</span>
                                <SegmentedControl
                                    options={IMPACT_OPTIONS}
                                    value={filterImpact}
                                    onChange={setFilterImpact}
                                    aria-label="Impact filter"
                                />
                            </div>

                            <div className="h-4 w-px bg-slate-800" />

                            {/* Country Filter */}
                            <div className="flex items-center gap-2">
                                <Globe className="w-4 h-4 text-slate-500" />
                                <div className="relative">
                                    <button
                                        onClick={() => setCountryDropdownOpen(!countryDropdownOpen)}
                                        className="flex items-center justify-between gap-2 bg-slate-900/60 border border-slate-800/60 text-slate-300 text-xs font-bold rounded-lg px-3 py-1.5 hover:bg-slate-800/60 hover:text-white transition-colors min-w-[140px]"
                                    >
                                        <span>{filterCountry === 'ALL' ? 'ALL COUNTRIES' : filterCountry}</span>
                                        <ChevronDown className={cn('w-3 h-3 text-slate-500 transition-transform', countryDropdownOpen && 'rotate-180')} />
                                    </button>

                                    {countryDropdownOpen && (
                                        <>
                                            <div
                                                className="fixed inset-0 z-10"
                                                onClick={() => setCountryDropdownOpen(false)}
                                            />
                                            <div className="dropdown-menu top-full mt-2 right-0 w-48">
                                                <div className="max-h-60 overflow-y-auto custom-scrollbar p-1">
                                                    <button
                                                        onClick={() => {
                                                            setFilterCountry('ALL');
                                                            setCountryDropdownOpen(false);
                                                        }}
                                                        className={filterCountry === 'ALL' ? 'dropdown-item-active rounded-lg' : 'dropdown-item rounded-lg'}
                                                    >
                                                        <span>ALL COUNTRIES</span>
                                                        {filterCountry === 'ALL' && <Check className="w-3.5 h-3.5" />}
                                                    </button>
                                                    {uniqueCountries.map(c => (
                                                        <button
                                                            key={c}
                                                            onClick={() => {
                                                                setFilterCountry(c);
                                                                setCountryDropdownOpen(false);
                                                            }}
                                                            className={filterCountry === c ? 'dropdown-item-active rounded-lg' : 'dropdown-item rounded-lg'}
                                                        >
                                                            <span>{c}</span>
                                                            {filterCountry === c && <Check className="w-3.5 h-3.5" />}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>
                        </div>
                    }
                />
                {filteredEvents.length === 0 && !loading ? (
                    <EmptyState
                        icon={Filter}
                        title="No events found"
                        hint="Try widening your timeframe, impact, or country filters."
                    />
                ) : (
                <div className="overflow-x-auto custom-scrollbar">
                    <table className="w-full min-w-[600px] md:min-w-0 text-sm text-left">
                        <thead>
                            <tr className="table-header">
                                <th className="table-cell text-left">Date</th>
                                <th className="table-cell text-left">Time</th>
                                <th className="table-cell text-left">Country</th>
                                <th className="table-cell text-left">Event</th>
                                <th className="table-cell text-center">Impact</th>
                                <th className="table-cell num">Forecast</th>
                                <th className="table-cell num">Previous</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredEvents.map((ev, i) => (
                                <tr
                                    key={i}
                                    className="table-row animate-stagger"
                                    style={{ '--i': i } as CSSProperties}
                                >
                                    <td className="table-cell font-mono text-xs text-slate-400 whitespace-nowrap">{formatDateDisplay(ev.date)}</td>
                                    <td className="table-cell font-mono text-xs text-slate-400 whitespace-nowrap">{ev.time}</td>
                                    <td className="table-cell font-bold text-slate-500">{ev.country}</td>
                                    <td className={cn('table-cell font-medium', ev.impact === 'High' ? 'text-white' : 'text-slate-300')}>{ev.title}</td>
                                    <td className="table-cell text-center">
                                        <Badge variant={impactVariant(ev.impact)}>{ev.impact}</Badge>
                                    </td>
                                    <td className="table-cell num text-slate-400">{ev.forecast || '-'}</td>
                                    <td className="table-cell num text-slate-400">{ev.previous || '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                )}
            </Card>

        </div>
    );
}
