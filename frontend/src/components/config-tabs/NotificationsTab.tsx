/**
 * Notifications Settings Tab Component
 * 
 * Configure Discord webhook notifications per account.
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { Bell, ChevronDown, CheckCircle, Power } from 'lucide-react';
import { toast } from 'sonner';
import type { Account } from '../../types';
import { TimePicker } from '../TimePicker';
import { API_BASE } from '../../config';

interface NotificationsTabProps {
    accounts: Account[];
}

export interface DiscordSettings {
    enabled: boolean;
    webhookUrl: string;
    notifyPositionOpen: boolean;
    notifyPositionClose: boolean;
    notifyPartialClose: boolean;
    notifyDailySummary: boolean;
    dailySummaryTime: string;
}

export function NotificationsTab({ accounts }: NotificationsTabProps) {
    const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
    const [accountDropdownOpen, setAccountDropdownOpen] = useState(false);
    const [saving, setSaving] = useState(false);

    // Discord settings state
    const [discordEnabled, setDiscordEnabled] = useState(false);
    const [webhookUrl, setWebhookUrl] = useState('');
    const [notifyPositionOpen, setNotifyPositionOpen] = useState(true);
    const [notifyPositionClose, setNotifyPositionClose] = useState(true);
    const [notifyPartialClose, setNotifyPartialClose] = useState(true);
    const [notifyDailySummary, setNotifyDailySummary] = useState(false);
    const [dailySummaryTime, setDailySummaryTime] = useState('21:00');

    // Auto-select first account on load
    useEffect(() => {
        if (accounts.length > 0 && !selectedAccountId) {
            setSelectedAccountId(accounts[0].id);
        }
    }, [accounts, selectedAccountId]);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (accountDropdownOpen && !target.closest('.group-account-selector')) {
                setAccountDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [accountDropdownOpen]);

    // Fetch Discord settings when account changes
    useEffect(() => {
        if (selectedAccountId) {
            fetchDiscordSettings(selectedAccountId);
        }
    }, [selectedAccountId]);

    const fetchDiscordSettings = async (accountId: number) => {
        try {
            const res = await axios.get(`${API_BASE}/settings/discord/${accountId}`);
            const settings = res.data;
            setDiscordEnabled(settings.enabled);
            setWebhookUrl(settings.webhook_url || '');
            setNotifyPositionOpen(settings.notify_position_open);
            setNotifyPositionClose(settings.notify_position_close);
            setNotifyPartialClose(settings.notify_partial_close);
            setNotifyDailySummary(settings.notify_daily_summary);
            setDailySummaryTime(settings.daily_summary_time || '21:00');
        } catch (e) {
            console.error("Failed to fetch Discord settings", e);
            // Reset to defaults
            setDiscordEnabled(false);
            setWebhookUrl('');
            setNotifyPositionOpen(true);
            setNotifyPositionClose(true);
            setNotifyPartialClose(true);
            setNotifyDailySummary(false);
            setDailySummaryTime('21:00');
        }
    };

    const saveDiscordSettings = async () => {
        if (!selectedAccountId) return;

        setSaving(true);
        try {
            await axios.post(`${API_BASE}/settings/discord/${selectedAccountId}`, {
                enabled: discordEnabled,
                webhook_url: webhookUrl,
                notify_position_open: notifyPositionOpen,
                notify_position_close: notifyPositionClose,
                notify_partial_close: notifyPartialClose,
                notify_daily_summary: notifyDailySummary,
                daily_summary_time: dailySummaryTime
            });
            toast.success('Discord settings saved');
            return true;
        } catch (e) {
            console.error("Failed to save Discord settings", e);
            toast.error('Failed to save Discord settings');
            return false;
        } finally {
            setSaving(false);
        }
    };

    const selectedAccount = accounts.find(a => a.id === selectedAccountId);

    return (
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
                            {selectedAccount ? `${selectedAccount.name} (${selectedAccount.id})` : 'Select Account'}
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
                                            setSelectedAccountId(acc.id);
                                            setAccountDropdownOpen(false);
                                        }}
                                        className={`w-full text-left px-4 py-2 flex items-center justify-between transition-colors hover:bg-slate-800/50 ${acc.id === selectedAccountId
                                            ? 'bg-indigo-500/10 text-indigo-400'
                                            : 'text-slate-300'
                                            }`}
                                    >
                                        <div className="flex items-center gap-2 truncate">
                                            <div className={`p-0.5 rounded-full ${acc.canTrade ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-500'}`} title={acc.canTrade ? "Trading Enabled" : "Trading Disabled"}>
                                                <Power className="w-3 h-3" />
                                            </div>
                                            <span className="font-mono text-xs truncate">{acc.name} ({acc.id})</span>
                                        </div>
                                        {acc.id === selectedAccountId && <CheckCircle className="w-3 h-3 flex-shrink-0" />}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {selectedAccountId && (
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

                        {/* Partial Close */}
                        <div className="flex items-center justify-between bg-slate-950 p-3 rounded-xl border border-slate-800">
                            <span className="text-sm text-slate-300">Partial Close</span>
                            <button
                                onClick={() => setNotifyPartialClose(!notifyPartialClose)}
                                disabled={!discordEnabled}
                                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${notifyPartialClose ? 'bg-indigo-500' : 'bg-slate-700'} disabled:opacity-50`}
                            >
                                <span className={`${notifyPartialClose ? 'translate-x-5' : 'translate-x-1'} inline-block h-3 w-3 transform rounded-full bg-white transition-transform`} />
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

            {/* Save Button for this tab - handled internally */}
            {selectedAccountId && (
                <div className="pt-4 border-t border-slate-800">
                    <button
                        onClick={saveDiscordSettings}
                        disabled={saving}
                        className="w-full px-6 py-2.5 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                        <Bell size={16} /> {saving ? 'Saving...' : 'Save Discord Settings'}
                    </button>
                </div>
            )}
        </div>
    );
}
