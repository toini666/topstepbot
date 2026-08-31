import { useState, useEffect } from 'react';
import axios from 'axios';
import { Trash2, Plus, Layers, Pencil, X, Save, Clock, User } from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE } from '../config';
import { Card, CardHeader, Button, Toggle, EmptyState, SegmentedControl, Spinner } from './ui';

import type { Strategy, AccountStrategyConfig } from '../types';

interface StrategiesManagerProps {
    selectedAccountId: number | null;
    selectedAccountName?: string;
}

const SESSION_KEYS = ['ASIA', 'UK', 'US', 'OUTSIDE'] as const;

const VIEW_OPTIONS: readonly { value: 'account' | 'global'; label: string }[] = [
    { value: 'account', label: 'Account Strategies' },
    { value: 'global', label: 'Global Templates' },
];

/** Session/outside chip styling for both display and interactive toggle contexts. */
function sessionChipClass(active: boolean, isOutside: boolean) {
    if (!active) {
        return 'badge-neutral cursor-pointer select-none hover:text-slate-300 transition-colors';
    }
    return isOutside
        ? 'badge-warning cursor-pointer select-none transition-colors'
        : 'badge-info cursor-pointer select-none transition-colors';
}

const iconBtn = 'inline-flex items-center justify-center p-2 rounded-lg text-slate-400 transition-colors';

/**
 * Strategies Manager Component
 * - When no account selected: Manages global strategy templates
 * - When account selected: Shows and edits per-account strategy configs
 */
export function StrategiesManager({ selectedAccountId, selectedAccountName }: StrategiesManagerProps) {

    // Global Strategies (Templates)
    const [strategies, setStrategies] = useState<Strategy[]>([]);
    const [loading, setLoading] = useState(false);

    // Account-Specific Configs
    const [accountConfigs, setAccountConfigs] = useState<AccountStrategyConfig[]>([]);

    // View Mode: 'account' when account selected, 'global' otherwise or when toggled
    const [viewMode, setViewMode] = useState<'account' | 'global'>('account');

    // Template Form State (for creating/editing global templates)
    const [editingId, setEditingId] = useState<number | null>(null);
    const [name, setName] = useState('');
    const [tvId, setTvId] = useState('');
    const [defaultFactor, setDefaultFactor] = useState<number>(1.0);
    const [defaultSessions, setDefaultSessions] = useState<string[]>(['ASIA', 'UK', 'US']);
    const [defaultPartialPercent, setDefaultPartialPercent] = useState<number>(50);
    const [defaultMoveSlToEntry, setDefaultMoveSlToEntry] = useState<boolean>(true);

    // Account Config Edit State
    const [editingConfigId, setEditingConfigId] = useState<number | null>(null);
    const [configEnabled, setConfigEnabled] = useState(true);
    const [configRiskFactor, setConfigRiskFactor] = useState(1.0);
    const [configSessions, setConfigSessions] = useState<string[]>(['ASIA', 'UK', 'US']);
    const [configPartialPercent, setConfigPartialPercent] = useState(50);
    const [configMoveSlToEntry, setConfigMoveSlToEntry] = useState(true);


    useEffect(() => {
        fetchStrategies();
    }, []);

    useEffect(() => {
        if (selectedAccountId) {
            setAccountConfigs([]); // Clear previous state to prevent ghosting
            fetchAccountConfigs(selectedAccountId);
            setViewMode('account'); // Switch to account view when account selected
        } else {
            setAccountConfigs([]);
            setViewMode('global');
        }
        // Reset editing state when account changes
        setEditingConfigId(null);
    }, [selectedAccountId]);

    const fetchStrategies = async () => {
        try {
            setLoading(true);
            const res = await axios.get(`${API_BASE}/strategies/`);
            setStrategies(res.data);
        } catch (e) {
            toast.error('Failed to load strategies');
        } finally {
            setLoading(false);
        }
    };

    const fetchAccountConfigs = async (accountId: number) => {
        try {
            const res = await axios.get(`${API_BASE}/settings/accounts/${accountId}/strategies`);
            setAccountConfigs(res.data);
        } catch (e) {
            console.error('Failed to load account configs:', e);
            setAccountConfigs([]);
        }
    };

    const resetForm = () => {
        setEditingId(null);
        setName('');
        setTvId('');
        setDefaultFactor(1.0);
        setDefaultSessions(['ASIA', 'UK', 'US']);
        setDefaultPartialPercent(50);
        setDefaultMoveSlToEntry(true);
    };

    const handleEdit = (strat: Strategy) => {
        setEditingId(strat.id);
        setName(strat.name);
        setTvId(strat.tv_id);
        setDefaultFactor(strat.default_risk_factor);

        const sessions = strat.default_allowed_sessions.split(',').map(s => s.trim());
        if (strat.default_allow_outside_sessions) sessions.push('OUTSIDE');
        setDefaultSessions(sessions);

        setDefaultPartialPercent(strat.default_partial_tp_percent);
        setDefaultMoveSlToEntry(strat.default_move_sl_to_entry);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            // Logic: 'OUTSIDE' in list -> boolean true, remove from string list
            const isOutside = defaultSessions.includes('OUTSIDE');
            const sessionsToSend = defaultSessions.filter(s => s !== 'OUTSIDE').join(',');

            const payload = {
                name,
                tv_id: tvId,
                default_risk_factor: defaultFactor,
                default_allowed_sessions: sessionsToSend,
                default_partial_tp_percent: defaultPartialPercent,
                default_move_sl_to_entry: defaultMoveSlToEntry,
                default_allow_outside_sessions: isOutside
            };

            if (editingId) {
                await axios.put(`${API_BASE}/strategies/${editingId}`, payload);
                toast.success('Strategy Updated');
            } else {
                await axios.post(`${API_BASE}/strategies/`, payload);
                toast.success('Strategy Created');
            }

            resetForm();
            fetchStrategies();
        } catch (e: any) {
            toast.error(e.response?.data?.detail || 'Operation failed');
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Delete this strategy?')) return;
        try {
            await axios.delete(`${API_BASE}/strategies/${id}`);
            toast.success('Strategy Deleted');
            fetchStrategies();
            if (editingId === id) resetForm();
        } catch (e) {
            toast.error('Failed to delete strategy');
        }
    };

    const toggleSession = (session: string) => {
        if (defaultSessions.includes(session)) {
            setDefaultSessions(defaultSessions.filter(s => s !== session));
        } else {
            setDefaultSessions([...defaultSessions, session]);
        }
    };

    const toggleConfigSession = (session: string) => {
        if (configSessions.includes(session)) {
            setConfigSessions(configSessions.filter(s => s !== session));
        } else {
            setConfigSessions([...configSessions, session]);
        }
    };

    const addStrategyToAccount = async (strategyId: number) => {
        if (!selectedAccountId) {
            toast.error('Select an account first');
            return;
        }

        const strategy = strategies.find(s => s.id === strategyId);
        if (!strategy) return;

        try {
            await axios.post(`${API_BASE}/settings/accounts/${selectedAccountId}/strategies`, {
                strategy_id: strategyId,
                enabled: true,
                risk_factor: strategy.default_risk_factor,
                allowed_sessions: strategy.default_allowed_sessions,
                partial_tp_percent: strategy.default_partial_tp_percent,
                move_sl_to_entry: strategy.default_move_sl_to_entry,
                allow_outside_sessions: strategy.default_allow_outside_sessions
            });
            toast.success('Strategy added to account');
            fetchAccountConfigs(selectedAccountId);
            setViewMode('account'); // Switch back to account view
        } catch (e) {
            toast.error('Failed to add strategy to account');
        }
    };

    const removeStrategyFromAccount = async (strategyId: number) => {
        if (!selectedAccountId) return;
        try {
            await axios.delete(`${API_BASE}/settings/accounts/${selectedAccountId}/strategies/${strategyId}`);
            toast.success('Strategy removed from account');
            fetchAccountConfigs(selectedAccountId);
        } catch (e) {
            toast.error('Failed to remove strategy');
        }
    };

    const isStrategyOnAccount = (strategyId: number) => {
        return accountConfigs.some(c => c.strategy_id === strategyId);
    };

    const startEditingConfig = (config: AccountStrategyConfig) => {
        setEditingConfigId(config.id);
        setConfigEnabled(config.enabled);
        setConfigRiskFactor(config.risk_factor);

        const sessions = config.allowed_sessions.split(',').map(s => s.trim());
        if (config.allow_outside_sessions) sessions.push('OUTSIDE');
        setConfigSessions(sessions);

        setConfigPartialPercent(config.partial_tp_percent);
        setConfigMoveSlToEntry(config.move_sl_to_entry);
    };

    const cancelEditingConfig = () => {
        setEditingConfigId(null);
    };

    // Save account config changes
    const saveConfigChanges = async (config: AccountStrategyConfig) => {
        if (!selectedAccountId) return;

        try {
            const isOutside = configSessions.includes('OUTSIDE');
            const sessionsToSend = configSessions.filter(s => s !== 'OUTSIDE').join(',');

            await axios.post(`${API_BASE}/settings/accounts/${selectedAccountId}/strategies`, {
                strategy_id: config.strategy_id,
                enabled: configEnabled,
                risk_factor: configRiskFactor,
                allowed_sessions: sessionsToSend,
                partial_tp_percent: configPartialPercent,
                move_sl_to_entry: configMoveSlToEntry,
                allow_outside_sessions: isOutside
            });
            toast.success('Configuration saved');
            setEditingConfigId(null);
            fetchAccountConfigs(selectedAccountId);
        } catch (e) {
            toast.error('Failed to save configuration');
        }
    };

    // Toggle strategy enabled status quickly
    const toggleStrategyEnabled = async (config: AccountStrategyConfig) => {
        if (!selectedAccountId) return;

        try {
            await axios.post(`${API_BASE}/settings/accounts/${selectedAccountId}/strategies`, {
                strategy_id: config.strategy_id,
                enabled: !config.enabled,
                risk_factor: config.risk_factor,
                allowed_sessions: config.allowed_sessions,
                partial_tp_percent: config.partial_tp_percent,
                move_sl_to_entry: config.move_sl_to_entry,
                allow_outside_sessions: config.allow_outside_sessions || false
            });
            toast.success(config.enabled ? 'Strategy disabled' : 'Strategy enabled');
            fetchAccountConfigs(selectedAccountId);
        } catch (e) {
            toast.error('Failed to toggle strategy');
        }
    };

    // Determine what to show
    const showAccountView = selectedAccountId && viewMode === 'account';

    return (
        <div className="space-y-8 animate-fade-in">
            {/* View Mode Toggle (when account selected) */}
            {selectedAccountId && (
                <SegmentedControl
                    options={VIEW_OPTIONS}
                    value={viewMode}
                    onChange={setViewMode}
                    aria-label="Strategy view"
                />
            )}

            {/* ACCOUNT VIEW: Show per-account strategy configs */}
            {showAccountView && (
                <Card className="animate-rise">
                    <CardHeader
                        icon={User}
                        title={`Strategies for ${selectedAccountName || `Account ${selectedAccountId}`}`}
                        annotation={`${accountConfigs.length} active`}
                    />

                    {accountConfigs.length > 0 ? (
                        <div className="scroll-x">
                            <table className="w-full min-w-[640px] md:min-w-0 text-sm text-left">
                                <thead>
                                    <tr className="table-header">
                                        <th className="table-cell font-semibold">Status</th>
                                        <th className="table-cell font-semibold">Strategy</th>
                                        <th className="table-cell font-semibold">Sessions</th>
                                        <th className="table-cell font-semibold text-right">Risk Factor</th>
                                        <th className="table-cell font-semibold text-right">Partial %</th>
                                        <th className="table-cell font-semibold text-center">SL → BE</th>
                                        <th className="table-cell font-semibold text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {accountConfigs.map((config, i) => (
                                        <tr
                                            key={config.id}
                                            className={`table-row animate-stagger ${editingConfigId === config.id ? 'bg-indigo-500/10 hover:bg-indigo-500/15' : ''}`}
                                            style={{ '--i': i } as React.CSSProperties}
                                        >
                                            {/* Enabled Toggle */}
                                            <td className="table-cell">
                                                <Toggle
                                                    checked={config.enabled}
                                                    onChange={() => toggleStrategyEnabled(config)}
                                                    activeColor="emerald"
                                                    label={`Toggle ${config.strategy_name || 'strategy'} enabled`}
                                                />
                                            </td>

                                            {/* Strategy Name */}
                                            <td className="table-cell">
                                                <div className="flex flex-col gap-0.5">
                                                    <span className="font-semibold text-slate-100">{config.strategy_name}</span>
                                                    <span className="font-mono text-xs text-slate-500">{config.strategy_tv_id}</span>
                                                </div>
                                            </td>

                                            {/* Sessions */}
                                            <td className="table-cell">
                                                {editingConfigId === config.id ? (
                                                    <div className="flex gap-1.5 flex-wrap">
                                                        {SESSION_KEYS.map(session => (
                                                            <button
                                                                key={session}
                                                                type="button"
                                                                onClick={() => toggleConfigSession(session)}
                                                                className={sessionChipClass(configSessions.includes(session), session === 'OUTSIDE')}
                                                            >
                                                                {session}
                                                            </button>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <div className="flex gap-1.5 flex-wrap">
                                                        {config.allowed_sessions.split(',').map(s => (
                                                            <span key={s} className="badge-info">
                                                                {s.trim()}
                                                            </span>
                                                        ))}
                                                        {config.allow_outside_sessions && (
                                                            <span className="badge-warning">OUTSIDE</span>
                                                        )}
                                                    </div>
                                                )}
                                            </td>

                                            {/* Risk Factor */}
                                            <td className="table-cell num">
                                                {editingConfigId === config.id ? (
                                                    <div className="w-20 ml-auto">
                                                        <input
                                                            type="number"
                                                            min="0.1"
                                                            step="0.1"
                                                            className="input-mono text-right px-2 py-1 text-sm"
                                                            value={configRiskFactor}
                                                            onChange={e => setConfigRiskFactor(parseFloat(e.target.value))}
                                                        />
                                                    </div>
                                                ) : (
                                                    <span className="text-slate-200 font-semibold">{config.risk_factor.toFixed(1)}x</span>
                                                )}
                                            </td>

                                            {/* Partial % */}
                                            <td className="table-cell num">
                                                {editingConfigId === config.id ? (
                                                    <div className="w-16 ml-auto">
                                                        <input
                                                            type="number"
                                                            min="10"
                                                            max="90"
                                                            className="input-mono text-right px-2 py-1 text-sm"
                                                            value={configPartialPercent}
                                                            onChange={e => setConfigPartialPercent(parseInt(e.target.value))}
                                                        />
                                                    </div>
                                                ) : (
                                                    <span className="text-slate-300">{config.partial_tp_percent}%</span>
                                                )}
                                            </td>

                                            {/* Move SL to BE */}
                                            <td className="table-cell text-center">
                                                {editingConfigId === config.id ? (
                                                    <Toggle
                                                        checked={configMoveSlToEntry}
                                                        onChange={() => setConfigMoveSlToEntry(!configMoveSlToEntry)}
                                                        activeColor="emerald"
                                                        size="sm"
                                                        label="Move SL to entry"
                                                        className="mx-auto"
                                                    />
                                                ) : (
                                                    <span className={config.move_sl_to_entry ? 'badge-success' : 'badge-neutral'}>
                                                        {config.move_sl_to_entry ? 'ON' : 'OFF'}
                                                    </span>
                                                )}
                                            </td>

                                            {/* Actions */}
                                            <td className="table-cell text-right">
                                                <div className="flex justify-end gap-1.5">
                                                    {editingConfigId === config.id ? (
                                                        <>
                                                            <button
                                                                onClick={() => saveConfigChanges(config)}
                                                                className={`${iconBtn} hover:bg-emerald-500/15 hover:text-emerald-300`}
                                                                title="Save"
                                                                aria-label="Save"
                                                            >
                                                                <Save className="w-4 h-4" />
                                                            </button>
                                                            <button
                                                                onClick={cancelEditingConfig}
                                                                className={`${iconBtn} hover:bg-slate-700/60 hover:text-slate-200`}
                                                                title="Cancel"
                                                                aria-label="Cancel"
                                                            >
                                                                <X className="w-4 h-4" />
                                                            </button>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <button
                                                                onClick={() => startEditingConfig(config)}
                                                                className={`${iconBtn} hover:bg-indigo-500/15 hover:text-indigo-300`}
                                                                title="Edit"
                                                                aria-label="Edit"
                                                            >
                                                                <Pencil className="w-4 h-4" />
                                                            </button>
                                                            <button
                                                                onClick={() => removeStrategyFromAccount(config.strategy_id)}
                                                                className={`${iconBtn} hover:bg-red-500/15 hover:text-red-300`}
                                                                title="Remove"
                                                                aria-label="Remove"
                                                            >
                                                                <Trash2 className="w-4 h-4" />
                                                            </button>
                                                        </>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <EmptyState
                            icon={Layers}
                            title="No strategies enabled on this account"
                            hint="Add one from Global Templates to enable it here."
                            action={
                                <Button variant="outline" onClick={() => setViewMode('global')}>
                                    Add from templates
                                </Button>
                            }
                        />
                    )}
                </Card>
            )}

            {/* GLOBAL VIEW: Create/Edit Strategy Template + List */}
            {(!selectedAccountId || viewMode === 'global') && (
                <>
                    {/* Create/Edit Strategy Template */}
                    <Card className={`animate-rise ${editingId ? 'ring-1 ring-indigo-500/30' : ''}`}>
                        <CardHeader
                            icon={editingId ? Pencil : Plus}
                            title={editingId ? 'Edit Strategy Template' : 'New Strategy Template'}
                            actions={editingId && (
                                <Button variant="ghost" icon={X} onClick={resetForm}>
                                    Cancel
                                </Button>
                            )}
                        />

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {/* Name */}
                                <div>
                                    <label className="label">Display Name</label>
                                    <input
                                        type="text"
                                        required
                                        className="input"
                                        placeholder="Scalp Alpha"
                                        value={name}
                                        onChange={e => setName(e.target.value)}
                                    />
                                </div>

                                {/* TV ID */}
                                <div>
                                    <label className="label">Webhook ID (tv_id)</label>
                                    <input
                                        type="text"
                                        required
                                        className="input-mono"
                                        placeholder="scalp_v1"
                                        value={tvId}
                                        onChange={e => setTvId(e.target.value)}
                                    />
                                    <p className="help-text">Must match the identifier sent from the TradingView alert.</p>
                                </div>

                                {/* Risk Factor */}
                                <div>
                                    <label className="label">Default Risk Factor</label>
                                    <input
                                        type="number"
                                        min="0.1"
                                        step="0.1"
                                        className="input-mono"
                                        value={defaultFactor}
                                        onChange={e => setDefaultFactor(parseFloat(e.target.value))}
                                    />
                                </div>
                            </div>

                            {/* Sessions */}
                            <div>
                                <label className="label !flex items-center gap-1.5">
                                    <Clock className="w-3.5 h-3.5" /> Allowed Sessions (Default)
                                </label>
                                <div className="flex gap-1.5 flex-wrap">
                                    {SESSION_KEYS.map(session => (
                                        <button
                                            key={session}
                                            type="button"
                                            onClick={() => toggleSession(session)}
                                            className={sessionChipClass(defaultSessions.includes(session), session === 'OUTSIDE')}
                                        >
                                            {session}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Partial TP Settings */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="label">Partial TP % (Default)</label>
                                    <input
                                        type="number"
                                        min="10"
                                        max="90"
                                        className="input-mono"
                                        value={defaultPartialPercent}
                                        onChange={e => setDefaultPartialPercent(parseInt(e.target.value))}
                                    />
                                </div>

                                {/* Move SL Logic */}
                                <div className="flex items-center gap-3 well px-3 py-2.5">
                                    <Toggle
                                        checked={defaultMoveSlToEntry}
                                        onChange={() => setDefaultMoveSlToEntry(!defaultMoveSlToEntry)}
                                        activeColor="emerald"
                                        label="Move SL to entry"
                                    />
                                    <span className="text-slate-300 text-sm font-medium">Move SL to Entry</span>
                                </div>
                            </div>

                            <Button type="submit" variant="primary" icon={editingId ? Save : Plus} className="w-full">
                                {editingId ? 'Save Changes' : 'Create Strategy'}
                            </Button>
                        </form>
                    </Card>

                    {/* Strategy List */}
                    <Card className="animate-rise">
                        <CardHeader
                            icon={Layers}
                            title="Strategy Templates"
                            annotation={loading ? <Spinner size="sm" /> : `${strategies.length}`}
                            actions={selectedAccountId && (
                                <span className="micro-label">Click + to add to selected account</span>
                            )}
                        />

                        {strategies.length > 0 ? (
                            <div className="scroll-x">
                                <table className="w-full min-w-[640px] md:min-w-0 text-sm text-left">
                                    <thead>
                                        <tr className="table-header">
                                            <th className="table-cell font-semibold">Strategy</th>
                                            <th className="table-cell font-semibold">Sessions</th>
                                            <th className="table-cell font-semibold text-right">Risk Factor</th>
                                            <th className="table-cell font-semibold text-right">Partial %</th>
                                            <th className="table-cell font-semibold text-center">SL → BE</th>
                                            <th className="table-cell font-semibold text-right">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {strategies.map((strat, i) => (
                                            <tr
                                                key={strat.id}
                                                className={`table-row animate-stagger ${editingId === strat.id ? 'bg-indigo-500/10 hover:bg-indigo-500/15' : ''}`}
                                                style={{ '--i': i } as React.CSSProperties}
                                            >
                                                {/* Strategy Name + TV ID */}
                                                <td className="table-cell">
                                                    <div className="flex flex-col gap-0.5">
                                                        <span className="font-semibold text-slate-100">{strat.name}</span>
                                                        <span className="font-mono text-xs text-slate-500">{strat.tv_id}</span>
                                                    </div>
                                                </td>
                                                {/* Sessions */}
                                                <td className="table-cell">
                                                    <div className="flex gap-1.5 flex-wrap">
                                                        {strat.default_allowed_sessions.split(',').map(s => (
                                                            <span key={s} className="badge-neutral">
                                                                {s.trim()}
                                                            </span>
                                                        ))}
                                                        {strat.default_allow_outside_sessions && (
                                                            <span className="badge-warning">OUTSIDE</span>
                                                        )}
                                                    </div>
                                                </td>
                                                {/* Risk Factor */}
                                                <td className="table-cell num">
                                                    <span className="text-slate-200 font-semibold">{strat.default_risk_factor.toFixed(1)}x</span>
                                                </td>
                                                {/* Partial % */}
                                                <td className="table-cell num">
                                                    <span className="text-slate-300">{strat.default_partial_tp_percent}%</span>
                                                </td>

                                                {/* Move SL to BE */}
                                                <td className="table-cell text-center">
                                                    <span className={strat.default_move_sl_to_entry ? 'badge-success' : 'badge-neutral'}>
                                                        {strat.default_move_sl_to_entry ? 'ON' : 'OFF'}
                                                    </span>
                                                </td>

                                                {/* Actions */}
                                                <td className="table-cell text-right">
                                                    <div className="flex justify-end gap-1.5">
                                                        {selectedAccountId && (
                                                            isStrategyOnAccount(strat.id) ? (
                                                                <button
                                                                    onClick={() => removeStrategyFromAccount(strat.id)}
                                                                    className={`${iconBtn} hover:bg-red-500/15 hover:text-red-300`}
                                                                    title="Remove from account"
                                                                    aria-label="Remove from account"
                                                                >
                                                                    <X className="w-4 h-4" />
                                                                </button>
                                                            ) : (
                                                                <button
                                                                    onClick={() => addStrategyToAccount(strat.id)}
                                                                    className={`${iconBtn} hover:bg-emerald-500/15 hover:text-emerald-300`}
                                                                    title="Add to account"
                                                                    aria-label="Add to account"
                                                                >
                                                                    <Plus className="w-4 h-4" />
                                                                </button>
                                                            )
                                                        )}
                                                        <button
                                                            onClick={() => handleEdit(strat)}
                                                            className={`${iconBtn} hover:bg-indigo-500/15 hover:text-indigo-300`}
                                                            title="Edit"
                                                            aria-label="Edit"
                                                        >
                                                            <Pencil className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={() => handleDelete(strat.id)}
                                                            className={`${iconBtn} hover:bg-red-500/15 hover:text-red-300`}
                                                            title="Delete"
                                                            aria-label="Delete"
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            !loading && (
                                <EmptyState
                                    icon={Layers}
                                    title="No strategies defined yet"
                                    hint="Create a strategy template above — its Webhook ID is what your TradingView alerts must send to route into it."
                                />
                            )
                        )}
                    </Card>
                </>
            )}
        </div>
    );
}
