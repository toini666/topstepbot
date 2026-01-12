import { useState, useEffect } from 'react';
import axios from 'axios';
import { Trash2, Plus, Layers, Pencil, X, Save, Clock, User, Settings } from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE } from '../config';

import type { Strategy, AccountStrategyConfig } from '../types';

interface StrategiesManagerProps {
    selectedAccountId: number | null;
    selectedAccountName?: string;
}

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
        setDefaultSessions(strat.default_allowed_sessions.split(',').map(s => s.trim()));
        setDefaultPartialPercent(strat.default_partial_tp_percent);
        setDefaultMoveSlToEntry(strat.default_move_sl_to_entry);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const payload = {
                name,
                tv_id: tvId,
                default_risk_factor: defaultFactor,
                default_allowed_sessions: defaultSessions.join(','),
                default_partial_tp_percent: defaultPartialPercent,
                default_move_sl_to_entry: defaultMoveSlToEntry
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
                move_sl_to_entry: strategy.default_move_sl_to_entry
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

    // Start editing an account config
    const startEditingConfig = (config: AccountStrategyConfig) => {
        setEditingConfigId(config.id);
        setConfigEnabled(config.enabled);
        setConfigRiskFactor(config.risk_factor);
        setConfigSessions(config.allowed_sessions.split(',').map(s => s.trim()));
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
            await axios.post(`${API_BASE}/settings/accounts/${selectedAccountId}/strategies`, {
                strategy_id: config.strategy_id,
                enabled: configEnabled,
                risk_factor: configRiskFactor,
                allowed_sessions: configSessions.join(','),
                partial_tp_percent: configPartialPercent,
                move_sl_to_entry: configMoveSlToEntry
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
                move_sl_to_entry: config.move_sl_to_entry
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
                <div className="flex gap-2 mb-4">
                    <button
                        onClick={() => setViewMode('account')}
                        className={`px-4 py-2 rounded-lg font-semibold text-sm flex items-center gap-2 transition-all ${viewMode === 'account'
                            ? 'bg-emerald-600 text-white'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                            }`}
                    >
                        <User className="w-4 h-4" />
                        Account Strategies
                    </button>
                    <button
                        onClick={() => setViewMode('global')}
                        className={`px-4 py-2 rounded-lg font-semibold text-sm flex items-center gap-2 transition-all ${viewMode === 'global'
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                            }`}
                    >
                        <Settings className="w-4 h-4" />
                        Global Templates
                    </button>
                </div>
            )}

            {/* ACCOUNT VIEW: Show per-account strategy configs */}
            {showAccountView && (
                <section className="bg-emerald-900/20 border border-emerald-500/30 rounded-2xl p-6">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-xl font-semibold flex items-center gap-2">
                            <User className="w-5 h-5 text-emerald-400" />
                            Strategies for {selectedAccountName || `Account ${selectedAccountId}`}
                        </h2>
                        <span className="text-xs bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded-lg">
                            {accountConfigs.length} stratégie(s) active(s)
                        </span>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="text-slate-500 border-b border-emerald-500/20 uppercase text-xs">
                                <tr>
                                    <th className="py-4 px-4 font-bold">Status</th>
                                    <th className="py-4 px-4 font-bold">Strategy</th>
                                    <th className="py-4 px-4 font-bold">Sessions</th>
                                    <th className="py-4 px-4 text-center font-bold">Risk Factor</th>
                                    <th className="py-4 px-4 text-center font-bold">Partial %</th>
                                    <th className="py-4 px-4 text-center font-bold">SL → BE</th>
                                    <th className="py-4 px-4 text-right font-bold">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/50">
                                {accountConfigs.map((config) => (
                                    <tr
                                        key={config.id}
                                        className={`transition-colors ${editingConfigId === config.id
                                            ? 'bg-emerald-500/10'
                                            : 'hover:bg-slate-800/30'
                                            }`}
                                    >
                                        {/* Enabled Toggle */}
                                        <td className="py-4 px-4">
                                            <button
                                                onClick={() => toggleStrategyEnabled(config)}
                                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${config.enabled ? 'bg-emerald-600' : 'bg-slate-700'
                                                    }`}
                                            >
                                                <span className={`${config.enabled ? 'translate-x-6' : 'translate-x-1'
                                                    } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`} />
                                            </button>
                                        </td>

                                        {/* Strategy Name */}
                                        <td className="py-4 px-4">
                                            <div className="flex flex-col">
                                                <span className="font-bold text-white">{config.strategy_name}</span>
                                                <span className="font-mono text-xs text-violet-300 bg-violet-500/10 px-2 py-0.5 rounded-md w-fit mt-1">
                                                    {config.strategy_tv_id}
                                                </span>
                                            </div>
                                        </td>

                                        {/* Sessions */}
                                        <td className="py-4 px-4">
                                            {editingConfigId === config.id ? (
                                                <div className="flex gap-1">
                                                    {['ASIA', 'UK', 'US'].map(session => (
                                                        <button
                                                            key={session}
                                                            type="button"
                                                            onClick={() => toggleConfigSession(session)}
                                                            className={`px-2 py-1 rounded text-xs font-bold transition-all ${configSessions.includes(session)
                                                                ? 'bg-emerald-600 text-white'
                                                                : 'bg-slate-800 text-slate-500'
                                                                }`}
                                                        >
                                                            {session}
                                                        </button>
                                                    ))}
                                                </div>
                                            ) : (
                                                <div className="flex gap-1">
                                                    {config.allowed_sessions.split(',').map(s => (
                                                        <span key={s} className="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded">
                                                            {s.trim()}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </td>

                                        {/* Risk Factor */}
                                        <td className="py-4 px-4 text-center font-mono">
                                            {editingConfigId === config.id ? (
                                                <input
                                                    type="number"
                                                    min="0.1"
                                                    step="0.1"
                                                    className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white text-center"
                                                    value={configRiskFactor}
                                                    onChange={e => setConfigRiskFactor(parseFloat(e.target.value))}
                                                />
                                            ) : (
                                                <span className="text-emerald-400 font-bold">{config.risk_factor.toFixed(1)}x</span>
                                            )}
                                        </td>

                                        {/* Partial % */}
                                        <td className="py-4 px-4 text-center font-mono">
                                            {editingConfigId === config.id ? (
                                                <input
                                                    type="number"
                                                    min="10"
                                                    max="90"
                                                    className="w-16 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white text-center"
                                                    value={configPartialPercent}
                                                    onChange={e => setConfigPartialPercent(parseInt(e.target.value))}
                                                />
                                            ) : (
                                                <span className="text-amber-400">{config.partial_tp_percent}%</span>
                                            )}
                                        </td>

                                        {/* Move SL to BE */}
                                        <td className="py-4 px-4 text-center">
                                            {editingConfigId === config.id ? (
                                                <button
                                                    type="button"
                                                    onClick={() => setConfigMoveSlToEntry(!configMoveSlToEntry)}
                                                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${configMoveSlToEntry ? 'bg-emerald-600' : 'bg-slate-700'}`}
                                                >
                                                    <span className={`${configMoveSlToEntry ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`} />
                                                </button>
                                            ) : (
                                                <span className={`px-2 py-1 rounded text-xs font-bold ${config.move_sl_to_entry ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-400'}`}>
                                                    {config.move_sl_to_entry ? 'ON' : 'OFF'}
                                                </span>
                                            )}
                                        </td>

                                        {/* Actions */}
                                        <td className="py-4 px-4 text-right">
                                            <div className="flex justify-end gap-2">
                                                {editingConfigId === config.id ? (
                                                    <>
                                                        <button
                                                            onClick={() => saveConfigChanges(config)}
                                                            className="p-2 bg-emerald-500/20 text-emerald-400 rounded-lg hover:bg-emerald-500/30"
                                                            title="Save"
                                                        >
                                                            <Save className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={cancelEditingConfig}
                                                            className="p-2 bg-slate-800 text-slate-400 rounded-lg hover:bg-slate-700"
                                                            title="Cancel"
                                                        >
                                                            <X className="w-4 h-4" />
                                                        </button>
                                                    </>
                                                ) : (
                                                    <>
                                                        <button
                                                            onClick={() => startEditingConfig(config)}
                                                            className="p-2 bg-slate-800 hover:bg-emerald-500/20 text-slate-400 hover:text-emerald-400 rounded-lg"
                                                            title="Edit"
                                                        >
                                                            <Pencil className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={() => removeStrategyFromAccount(config.strategy_id)}
                                                            className="p-2 bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 rounded-lg"
                                                            title="Remove"
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                                {accountConfigs.length === 0 && (
                                    <tr>
                                        <td colSpan={7} className="py-12 text-center text-slate-500 italic">
                                            Aucune stratégie activée sur ce compte.
                                            <br />
                                            <button
                                                onClick={() => setViewMode('global')}
                                                className="text-indigo-400 underline mt-2"
                                            >
                                                Ajouter depuis les templates
                                            </button>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </section>
            )}

            {/* GLOBAL VIEW: Create/Edit Strategy Template + List */}
            {(!selectedAccountId || viewMode === 'global') && (
                <>
                    {/* Create/Edit Strategy Template */}
                    <section className={`border rounded-2xl p-6 transition-all ${editingId ? 'bg-indigo-500/5 border-indigo-500/30' : 'bg-slate-900/50 border-slate-800'}`}>
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-semibold flex items-center gap-2">
                                {editingId ? <Pencil className="w-5 h-5 text-indigo-400" /> : <Plus className="w-5 h-5 text-indigo-400" />}
                                {editingId ? 'Edit Strategy Template' : 'New Strategy Template'}
                            </h2>
                            {editingId && (
                                <button onClick={resetForm} className="text-slate-400 hover:text-white text-xs flex items-center gap-1 bg-slate-800 px-3 py-1 rounded-lg">
                                    <X className="w-3 h-3" /> Cancel
                                </button>
                            )}
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {/* Name */}
                                <div>
                                    <label className="block text-slate-400 text-xs uppercase mb-2 font-bold">Display Name</label>
                                    <input
                                        type="text"
                                        required
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2.5 px-4 text-white focus:outline-none focus:border-indigo-500"
                                        placeholder="Scalp Alpha"
                                        value={name}
                                        onChange={e => setName(e.target.value)}
                                    />
                                </div>

                                {/* TV ID */}
                                <div>
                                    <label className="block text-slate-400 text-xs uppercase mb-2 font-bold">Webhook ID (tv_id)</label>
                                    <input
                                        type="text"
                                        required
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2.5 px-4 text-white font-mono text-sm focus:outline-none focus:border-violet-500"
                                        placeholder="scalp_v1"
                                        value={tvId}
                                        onChange={e => setTvId(e.target.value)}
                                    />
                                </div>

                                {/* Risk Factor */}
                                <div>
                                    <label className="block text-slate-400 text-xs uppercase mb-2 font-bold">Default Risk Factor</label>
                                    <input
                                        type="number"
                                        min="0.1"
                                        step="0.1"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2.5 px-4 text-white font-mono focus:outline-none focus:border-emerald-500"
                                        value={defaultFactor}
                                        onChange={e => setDefaultFactor(parseFloat(e.target.value))}
                                    />
                                </div>
                            </div>

                            {/* Sessions */}
                            <div>
                                <label className="block text-slate-400 text-xs uppercase mb-2 font-bold flex items-center gap-2">
                                    <Clock className="w-4 h-4" /> Allowed Sessions (Default)
                                </label>
                                <div className="flex gap-2">
                                    {['ASIA', 'UK', 'US'].map(session => (
                                        <button
                                            key={session}
                                            type="button"
                                            onClick={() => toggleSession(session)}
                                            className={`px-4 py-2 rounded-lg font-bold text-sm transition-all ${defaultSessions.includes(session)
                                                ? 'bg-indigo-600 text-white'
                                                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                                                }`}
                                        >
                                            {session}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Partial TP Settings */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-slate-400 text-xs uppercase mb-2 font-bold">Partial TP % (Default)</label>
                                    <input
                                        type="number"
                                        min="10"
                                        max="90"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2.5 px-4 text-white font-mono focus:outline-none focus:border-amber-500"
                                        value={defaultPartialPercent}
                                        onChange={e => setDefaultPartialPercent(parseInt(e.target.value))}
                                    />
                                </div>
                                <div className="flex items-center gap-3">
                                    <button
                                        type="button"
                                        onClick={() => setDefaultMoveSlToEntry(!defaultMoveSlToEntry)}
                                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${defaultMoveSlToEntry ? 'bg-indigo-600' : 'bg-slate-700'
                                            }`}
                                    >
                                        <span className={`${defaultMoveSlToEntry ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`} />
                                    </button>
                                    <span className="text-slate-300 text-sm">Move SL to Entry on Partial</span>
                                </div>
                            </div>

                            <button
                                type="submit"
                                className={`w-full font-bold py-2.5 px-8 rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg ${editingId ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-blue-600 hover:bg-blue-700'
                                    } text-white`}
                            >
                                {editingId ? <Save className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
                                {editingId ? 'Save Changes' : 'Create Strategy'}
                            </button>
                        </form>
                    </section>

                    {/* Strategy List */}
                    <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                        <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                            <Layers className="w-5 h-5 text-indigo-400" />
                            Strategy Templates
                            {selectedAccountId && (
                                <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded-lg ml-2">
                                    Click + to add to selected account
                                </span>
                            )}
                        </h2>

                        <div className="overflow-x-auto">
                            <table className="w-full text-sm text-left">
                                <thead className="text-slate-500 border-b border-slate-800 uppercase text-xs">
                                    <tr>
                                        <th className="py-4 px-4 font-bold">Strategy</th>
                                        <th className="py-4 px-4 font-bold">Sessions</th>
                                        <th className="py-4 px-4 text-center font-bold">Risk Factor</th>
                                        <th className="py-4 px-4 text-center font-bold">Partial %</th>
                                        <th className="py-4 px-4 text-center font-bold">SL → BE</th>
                                        <th className="py-4 px-4 text-right font-bold">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800/50">
                                    {strategies.map((strat) => (
                                        <tr key={strat.id} className={`transition-colors ${editingId === strat.id ? 'bg-indigo-500/10' : 'hover:bg-slate-800/30'}`}>
                                            {/* Strategy Name + TV ID */}
                                            <td className="py-4 px-4">
                                                <div className="flex flex-col">
                                                    <span className="font-bold text-white">{strat.name}</span>
                                                    <span className="font-mono text-xs text-violet-300 bg-violet-500/10 px-2 py-0.5 rounded-md w-fit mt-1">
                                                        {strat.tv_id}
                                                    </span>
                                                </div>
                                            </td>
                                            {/* Sessions */}
                                            <td className="py-4 px-4">
                                                <div className="flex gap-1">
                                                    {strat.default_allowed_sessions.split(',').map(s => (
                                                        <span key={s} className="text-xs bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                                                            {s.trim()}
                                                        </span>
                                                    ))}
                                                </div>
                                            </td>
                                            {/* Risk Factor */}
                                            <td className="py-4 px-4 text-center font-mono">
                                                <span className="text-emerald-400 font-bold">{strat.default_risk_factor.toFixed(1)}x</span>
                                            </td>
                                            {/* Partial % */}
                                            <td className="py-4 px-4 text-center font-mono">
                                                <span className="text-amber-400">{strat.default_partial_tp_percent}%</span>
                                            </td>
                                            {/* Move SL to BE */}
                                            <td className="py-4 px-4 text-center">
                                                <span className={`px-2 py-1 rounded text-xs font-bold ${strat.default_move_sl_to_entry ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-700 text-slate-400'}`}>
                                                    {strat.default_move_sl_to_entry ? 'ON' : 'OFF'}
                                                </span>
                                            </td>
                                            {/* Actions */}
                                            <td className="py-4 px-4 text-right">
                                                <div className="flex justify-end gap-2">
                                                    {selectedAccountId && (
                                                        isStrategyOnAccount(strat.id) ? (
                                                            <button
                                                                onClick={() => removeStrategyFromAccount(strat.id)}
                                                                className="p-2 bg-red-500/20 text-red-400 rounded-lg"
                                                                title="Remove from account"
                                                            >
                                                                <X className="w-4 h-4" />
                                                            </button>
                                                        ) : (
                                                            <button
                                                                onClick={() => addStrategyToAccount(strat.id)}
                                                                className="p-2 bg-emerald-500/20 text-emerald-400 rounded-lg"
                                                                title="Add to account"
                                                            >
                                                                <Plus className="w-4 h-4" />
                                                            </button>
                                                        )
                                                    )}
                                                    <button
                                                        onClick={() => handleEdit(strat)}
                                                        className="p-2 bg-slate-800 hover:bg-indigo-500/20 text-slate-400 hover:text-indigo-400 rounded-lg"
                                                    >
                                                        <Pencil className="w-4 h-4" />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(strat.id)}
                                                        className="p-2 bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 rounded-lg"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                    {strategies.length === 0 && !loading && (
                                        <tr>
                                            <td colSpan={6} className="py-12 text-center text-slate-500 italic">
                                                No strategies defined yet.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </section>
                </>
            )}
        </div>
    );
}
