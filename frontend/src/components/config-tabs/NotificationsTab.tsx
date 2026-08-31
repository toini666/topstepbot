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
import { Toggle, Button } from '../ui';

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
                <label className="label">Select Account</label>
                <div className="relative group-account-selector">
                    <button
                        onClick={() => accounts.length > 0 && setAccountDropdownOpen(!accountDropdownOpen)}
                        className="input flex items-center justify-between text-left"
                        disabled={accounts.length === 0}
                    >
                        <span className="text-white font-mono text-sm truncate mr-2">
                            {selectedAccount ? `${selectedAccount.name} (${selectedAccount.id})` : 'Select Account'}
                        </span>
                        <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform duration-200 flex-shrink-0 ${accountDropdownOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {accountDropdownOpen && accounts.length > 0 && (
                        <div className="dropdown-menu top-full left-0 mt-2 w-full">
                            <div className="max-h-60 overflow-y-auto custom-scrollbar">
                                {accounts.map((acc) => (
                                    <button
                                        key={acc.id}
                                        onClick={() => {
                                            setSelectedAccountId(acc.id);
                                            setAccountDropdownOpen(false);
                                        }}
                                        className={acc.id === selectedAccountId ? 'dropdown-item-active' : 'dropdown-item'}
                                    >
                                        <div className="flex items-center gap-2 truncate">
                                            <div className={`p-0.5 rounded-full ${acc.canTrade ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`} title={acc.canTrade ? "Trading Enabled" : "Trading Disabled"}>
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
                    <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800/60 p-4 rounded-xl">
                        <div>
                            <span className="text-sm font-semibold text-white flex items-center gap-2">
                                <Bell size={16} className="text-indigo-400" />
                                Discord Notifications
                            </span>
                            <p className="help-text">Enable Discord webhook notifications for this account</p>
                        </div>
                        <Toggle
                            checked={discordEnabled}
                            onChange={() => setDiscordEnabled(!discordEnabled)}
                            size="md"
                            activeColor="indigo"
                            label="Discord notifications enabled"
                        />
                    </div>

                    {/* Webhook URL */}
                    <div className={`space-y-2 transition-opacity ${!discordEnabled ? 'opacity-50' : ''}`}>
                        <label className="label">Webhook URL</label>
                        <input
                            type="text"
                            value={webhookUrl}
                            onChange={(e) => setWebhookUrl(e.target.value)}
                            disabled={!discordEnabled}
                            placeholder="https://discord.com/api/webhooks/..."
                            className="input-mono disabled:opacity-50"
                        />
                        <p className="help-text">
                            Create a webhook in Discord: Server Settings → Integrations → Webhooks
                        </p>
                    </div>

                    {/* Notification Types */}
                    <div className={`space-y-3 transition-opacity ${!discordEnabled ? 'opacity-50' : ''}`}>
                        <label className="label">Notification Types</label>

                        {/* Position Opened */}
                        <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800/60 p-3 rounded-xl">
                            <span className="text-sm text-slate-300">Position Opened</span>
                            <Toggle
                                checked={notifyPositionOpen}
                                onChange={() => setNotifyPositionOpen(!notifyPositionOpen)}
                                disabled={!discordEnabled}
                                size="sm"
                                activeColor="indigo"
                                label="Notify on position opened"
                            />
                        </div>

                        {/* Position Closed */}
                        <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800/60 p-3 rounded-xl">
                            <span className="text-sm text-slate-300">Position Closed</span>
                            <Toggle
                                checked={notifyPositionClose}
                                onChange={() => setNotifyPositionClose(!notifyPositionClose)}
                                disabled={!discordEnabled}
                                size="sm"
                                activeColor="indigo"
                                label="Notify on position closed"
                            />
                        </div>

                        {/* Partial Close */}
                        <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800/60 p-3 rounded-xl">
                            <span className="text-sm text-slate-300">Partial Close</span>
                            <Toggle
                                checked={notifyPartialClose}
                                onChange={() => setNotifyPartialClose(!notifyPartialClose)}
                                disabled={!discordEnabled}
                                size="sm"
                                activeColor="indigo"
                                label="Notify on partial close"
                            />
                        </div>

                        {/* Daily Summary */}
                        <div className="bg-slate-900/60 border border-slate-800/60 p-3 rounded-xl space-y-3">
                            <div className="flex items-center justify-between">
                                <div>
                                    <span className="text-sm text-slate-300">Daily Summary</span>
                                    <p className="help-text">P&L, trades count, balance</p>
                                </div>
                                <Toggle
                                    checked={notifyDailySummary}
                                    onChange={() => setNotifyDailySummary(!notifyDailySummary)}
                                    disabled={!discordEnabled}
                                    size="sm"
                                    activeColor="indigo"
                                    label="Notify daily summary"
                                />
                            </div>

                            {notifyDailySummary && discordEnabled && (
                                <div className="flex items-center gap-3 pt-2 border-t border-slate-800/60">
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
                <div className="pt-4 border-t border-slate-800/60">
                    <Button variant="primary" icon={Bell} loading={saving} onClick={saveDiscordSettings} className="w-full">
                        {saving ? 'Saving...' : 'Save Discord Settings'}
                    </Button>
                </div>
            )}
        </div>
    );
}
