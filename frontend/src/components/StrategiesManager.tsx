import { useState, useEffect } from 'react';
import axios from 'axios';
import { Trash2, Plus, Layers, Pencil, X, Save, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE } from '../config';

import type { Strategy, AccountStrategyConfig } from '../types';

interface StrategiesManagerProps {
    selectedAccountId: number | null;
}

/**
 * Strategies Manager Component
 * - Manages global strategy templates
 * - Configures per-account strategy settings (when account selected)
 */
export function StrategiesManager({ selectedAccountId }: StrategiesManagerProps) {

    // Global Strategies (Templates)
    const [strategies, setStrategies] = useState<Strategy[]>([]);
    const [loading, setLoading] = useState(false);

    // Account-Specific Configs
    const [accountConfigs, setAccountConfigs] = useState<AccountStrategyConfig[]>([]);

    // Form State
    const [editingId, setEditingId] = useState<number | null>(null);
    const [name, setName] = useState('');
    const [tvId, setTvId] = useState('');
    const [defaultFactor, setDefaultFactor] = useState<number>(1.0);
    const [defaultSessions, setDefaultSessions] = useState<string[]>(['ASIA', 'UK', 'US']);
    const [defaultPartialPercent, setDefaultPartialPercent] = useState<number>(50);
    const [defaultMoveSlToEntry, setDefaultMoveSlToEntry] = useState<boolean>(true);

    useEffect(() => {
        fetchStrategies();
    }, []);

    useEffect(() => {
        if (selectedAccountId) {
            setAccountConfigs([]); // Clear previous state to prevent ghosting
            fetchAccountConfigs(selectedAccountId);
        } else {
            setAccountConfigs([]);
        }
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

    return (
        <div className="space-y-8 animate-fade-in">
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
                                <th className="py-4 px-4 font-bold">Name</th>
                                <th className="py-4 px-4 font-bold">TV ID</th>
                                <th className="py-4 px-4 font-bold">Sessions</th>
                                <th className="py-4 px-4 text-right font-bold">Risk</th>
                                <th className="py-4 px-4 text-right font-bold">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                            {strategies.map((strat) => (
                                <tr key={strat.id} className={`transition-colors ${editingId === strat.id ? 'bg-indigo-500/10' : 'hover:bg-slate-800/30'}`}>
                                    <td className="py-4 px-4 font-bold text-white">{strat.name}</td>
                                    <td className="py-4 px-4">
                                        <span className="font-mono text-xs text-violet-300 bg-violet-500/10 px-2 py-1 rounded-md">
                                            {strat.tv_id}
                                        </span>
                                    </td>
                                    <td className="py-4 px-4">
                                        <div className="flex gap-1">
                                            {strat.default_allowed_sessions.split(',').map(s => (
                                                <span key={s} className="text-xs bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                                                    {s.trim()}
                                                </span>
                                            ))}
                                        </div>
                                    </td>
                                    <td className="py-4 px-4 text-right font-mono">
                                        <span className="text-emerald-400 font-bold">{strat.default_risk_factor.toFixed(1)}x</span>
                                    </td>
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
                                    <td colSpan={5} className="py-12 text-center text-slate-500 italic">
                                        No strategies defined yet.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    );
}
