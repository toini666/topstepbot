
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Calendar as CalendarIcon, RefreshCw, Bell, Settings, CheckCircle, Filter, X, Globe, ChevronDown, Check } from 'lucide-react';
import { format } from 'date-fns';
import { API_BASE } from '../config';
import { toast } from 'sonner';

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
}

export function Calendar() {
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [settings, setSettings] = useState<CalendarSettings>({
        discord_url: '',
        enabled: false,
        major_countries: ['USD'],
        major_impacts: ['High', 'Medium']
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
    const todayStr = format(new Date(), 'MM-dd-yyyy');
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

    const getImpactColor = (impact: string) => {
        switch (impact) {
            case 'High': return 'text-red-400 bg-red-400/10 border-red-400/20';
            case 'Medium': return 'text-orange-400 bg-orange-400/10 border-orange-400/20';
            default: return 'text-slate-400 bg-slate-400/10 border-slate-400/20';
        }
    };

    const filteredEvents = events.filter(ev => {
        if (filterTimeframe === 'Today' && ev.date !== todayStr) return false;
        if (filterImpact !== 'ALL' && ev.impact !== filterImpact) return false;
        if (filterCountry !== 'ALL' && ev.country !== filterCountry) return false;
        return true;
    });

    // Helper to toggle array items
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
            className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all ${checked
                ? 'bg-indigo-500/10 border-indigo-500/30 text-white'
                : 'bg-slate-800/30 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
        >
            <div className={`w-5 h-5 rounded-md border flex items-center justify-center transition-colors ${checked ? 'bg-indigo-500 border-indigo-500' : 'border-slate-600 bg-slate-900'
                }`}>
                {checked && <Check className="w-3.5 h-3.5 text-white" />}
            </div>
            <span className="text-sm font-medium">{label}</span>
        </div>
    );

    return (
        <div className="space-y-8 animate-fade-in">

            {/* Header */}
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
                    <CalendarIcon className="w-6 h-6 text-indigo-400" />
                    Economic Calendar
                </h2>
                <div className="flex gap-2">
                    <button
                        onClick={refreshCalendar}
                        disabled={loading}
                        className="p-2 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 transition-colors border border-slate-700 hover:border-indigo-500/30"
                        title="Refresh Calendar"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                    <button
                        onClick={() => setSettingsOpen(!settingsOpen)}
                        className={`p-2 rounded-lg transition-colors border ${settings.enabled ? 'text-indigo-400 border-indigo-500/30 bg-indigo-500/10' : 'text-slate-400 border-slate-700 hover:text-white'}`}
                        title="Notification Settings"
                    >
                        <Settings className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Settings Modal */}
            {settingsOpen && (
                <div className="fixed inset-0 z-50 h-screen w-screen flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-lg shadow-2xl animate-scale-in">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold text-white flex items-center gap-2">
                                <Bell className="w-5 h-5 text-indigo-400" />
                                Calendar Settings
                            </h3>
                            <button
                                onClick={() => setSettingsOpen(false)}
                                className="text-slate-400 hover:text-white transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="space-y-6">
                            <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                                <div>
                                    <p className="font-medium text-slate-200">Daily Summary</p>
                                    <p className="text-xs text-slate-400">Receive a daily summary of major events at 7:00 AM</p>
                                </div>
                                <button
                                    onClick={() => setSettings({ ...settings, enabled: !settings.enabled })}
                                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${settings.enabled ? 'bg-indigo-500' : 'bg-slate-600'}`}
                                >
                                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${settings.enabled ? 'translate-x-6' : 'translate-x-1'}`} />
                                </button>
                            </div>

                            {settings.enabled && (
                                <div className="animate-fade-in-down">
                                    <label className="block text-sm text-slate-400 mb-2">Discord Webhook URL</label>
                                    <input
                                        type="text"
                                        value={settings.discord_url}
                                        onChange={(e) => setSettings({ ...settings, discord_url: e.target.value })}
                                        placeholder="https://discord.com/api/webhooks/..."
                                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-slate-200 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all font-mono text-sm"
                                    />
                                </div>
                            )}

                            <div className="space-y-3 pt-2 border-t border-slate-800">
                                <label className="block text-sm font-semibold text-slate-300">Definition of "Major Event"</label>
                                <p className="text-xs text-slate-500 mb-2">Select criteria for daily notifications and dashboard highlights.</p>

                                <div className="grid grid-cols-2 gap-6">
                                    <div>
                                        <label className="text-xs text-slate-500 font-bold mb-3 block uppercase tracking-wider">Impacts</label>
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
                                            <label className="text-xs text-slate-500 font-bold block uppercase tracking-wider">Countries</label>
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

                            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                                <button
                                    onClick={testNotification}
                                    className="px-4 py-2 text-sm font-bold text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-all"
                                >
                                    Test Notification
                                </button>
                                <button
                                    onClick={saveSettings}
                                    disabled={saving}
                                    className="px-6 py-2 text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-all shadow-lg shadow-indigo-900/20"
                                >
                                    {saving ? 'Saving...' : 'Save Changes'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Today's Highlights */}
            <section className="bg-gradient-to-br from-slate-900 to-slate-900/50 border border-slate-800 rounded-2xl p-6">
                <h3 className="text-lg font-semibold mb-4 text-slate-300">Today's Major Events ({formatDateDisplay(todayStr)})</h3>
                {majorToday.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {majorToday.map((ev, idx) => (
                            <div key={idx} className={`p-4 rounded-xl border ${ev.impact === 'High' ? 'bg-red-500/5 border-red-500/20' : 'bg-orange-500/5 border-orange-500/20'}`}>
                                <div className="flex justify-between items-start mb-2">
                                    <span className={`text-xs font-bold px-2 py-0.5 rounded border ${getImpactColor(ev.impact)}`}>{ev.impact.toUpperCase()}</span>
                                    <span className="font-mono text-sm text-slate-400">{ev.time}</span>
                                </div>
                                <div className="font-bold text-slate-200 mb-1">{ev.country} - {ev.title}</div>
                                <div className="text-xs text-slate-500 flex justify-between mt-3 pt-3 border-t border-slate-800/50">
                                    <span>Fcst: <span className="text-slate-300">{ev.forecast || '-'}</span></span>
                                    <span>Prev: <span className="text-slate-300">{ev.previous || '-'}</span></span>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-8 text-slate-500 bg-slate-900/30 rounded-xl border border-slate-800/50 border-dashed">
                        <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        No major events remaining today.
                    </div>
                )}
            </section>

            {/* Full Weekly Calendar Table */}
            <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                        <CalendarIcon className="w-5 h-5 text-slate-400" />
                        Weekly Schedule
                    </h3>

                    <div className="flex flex-wrap items-center gap-4">
                        {/* Timeframe Filter */}
                        <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-1">
                            {['Today', 'Week'].map(tf => (
                                <button
                                    key={tf}
                                    onClick={() => setFilterTimeframe(tf as 'Today' | 'Week')}
                                    className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${filterTimeframe === tf
                                        ? 'bg-indigo-600 text-white shadow-lg'
                                        : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
                                >
                                    {tf}
                                </button>
                            ))}
                        </div>

                        <div className="h-4 w-px bg-slate-800"></div>

                        {/* Impact Filter */}
                        <div className="flex items-center gap-2">
                            <Filter className="w-4 h-4 text-slate-500" />
                            <span className="text-xs text-slate-500 uppercase font-bold mr-1 hidden md:block">Impact:</span>
                            <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-1">
                                {['ALL', 'High', 'Medium', 'Low'].map(option => (
                                    <button
                                        key={option}
                                        onClick={() => setFilterImpact(option)}
                                        className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${filterImpact === option
                                            ? 'bg-indigo-600 text-white shadow-lg'
                                            : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
                                    >
                                        {option}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="h-4 w-px bg-slate-800"></div>

                        {/* Country Filter */}
                        <div className="flex items-center gap-2">
                            <Globe className="w-4 h-4 text-slate-500" />
                            <div className="relative">
                                <button
                                    onClick={() => setCountryDropdownOpen(!countryDropdownOpen)}
                                    className="flex items-center justify-between gap-2 bg-slate-900 border border-slate-800 text-slate-300 text-xs font-bold rounded-lg px-3 py-1.5 hover:bg-slate-800 hover:text-white transition-colors min-w-[140px]"
                                >
                                    <span>{filterCountry === 'ALL' ? 'ALL COUNTRIES' : filterCountry}</span>
                                    <ChevronDown className="w-3 h-3 text-slate-500" />
                                </button>

                                {countryDropdownOpen && (
                                    <>
                                        <div
                                            className="fixed inset-0 z-10"
                                            onClick={() => setCountryDropdownOpen(false)}
                                        />
                                        <div className="absolute top-full mt-2 right-0 w-48 bg-slate-900 border border-slate-800 rounded-xl shadow-xl z-20 max-h-60 overflow-y-auto custom-scrollbar animate-scale-in">
                                            <button
                                                onClick={() => {
                                                    setFilterCountry('ALL');
                                                    setCountryDropdownOpen(false);
                                                }}
                                                className={`w-full text-left px-4 py-2 text-xs font-medium hover:bg-slate-800 transition-colors ${filterCountry === 'ALL' ? 'text-indigo-400 bg-indigo-500/10' : 'text-slate-400'}`}
                                            >
                                                ALL COUNTRIES
                                            </button>
                                            {uniqueCountries.map(c => (
                                                <button
                                                    key={c}
                                                    onClick={() => {
                                                        setFilterCountry(c);
                                                        setCountryDropdownOpen(false);
                                                    }}
                                                    className={`w-full text-left px-4 py-2 text-xs font-medium hover:bg-slate-800 transition-colors ${filterCountry === c ? 'text-indigo-400 bg-indigo-500/10' : 'text-slate-400'}`}
                                                >
                                                    {c}
                                                </button>
                                            ))}
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="text-slate-500 border-b border-slate-800 uppercase text-xs">
                            <tr>
                                <th className="py-3 px-4">Date</th>
                                <th className="py-3 px-4">Time</th>
                                <th className="py-3 px-4">Country</th>
                                <th className="py-3 px-4">Event</th>
                                <th className="py-3 px-4 text-center">Impact</th>
                                <th className="py-3 px-4 text-right">Forecast</th>
                                <th className="py-3 px-4 text-right">Previous</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                            {filteredEvents.map((ev, i) => (
                                <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                                    <td className="py-3 px-4 font-mono text-xs text-slate-400 whitespace-nowrap">{formatDateDisplay(ev.date)}</td>
                                    <td className="py-3 px-4 font-mono text-xs text-slate-400 whitespace-nowrap">{ev.time}</td>
                                    <td className="py-3 px-4 font-bold text-slate-500">{ev.country}</td>
                                    <td className={`py-3 px-4 font-medium ${ev.impact === 'High' ? 'text-white' : 'text-slate-300'}`}>{ev.title}</td>
                                    <td className="py-3 px-4 text-center">
                                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${getImpactColor(ev.impact)}`}>
                                            {ev.impact}
                                        </span>
                                    </td>
                                    <td className="py-3 px-4 text-right font-mono text-slate-400">{ev.forecast || '-'}</td>
                                    <td className="py-3 px-4 text-right font-mono text-slate-400">{ev.previous || '-'}</td>
                                </tr>
                            ))}
                            {filteredEvents.length === 0 && !loading && (
                                <tr><td colSpan={7} className="py-8 text-center text-slate-500 italic">No events found matching filters.</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>

        </div>
    );
}
