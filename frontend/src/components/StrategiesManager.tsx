import { useState, useEffect } from 'react';
import axios from 'axios';
import { Trash2, Plus, DollarSign, Layers, Hash, Info, Pencil, X, Save } from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE } from '../config';
import { useTopStep } from '../hooks/useTopStep';
import type { Strategy } from '../types';

export function StrategiesManager() {
    const { config } = useTopStep();
    const [strategies, setStrategies] = useState<Strategy[]>([]);
    const [loading, setLoading] = useState(false);

    // Form State
    const [editingId, setEditingId] = useState<number | null>(null);
    const [name, setName] = useState('');
    const [tvId, setTvId] = useState('');
    const [factor, setFactor] = useState<number>(1.0); // Default 1.0

    useEffect(() => {
        fetchStrategies();
    }, []);

    const fetchStrategies = async () => {
        try {
            setLoading(true);
            const res = await axios.get(`${API_BASE}/strategies/`);
            setStrategies(res.data);
        } catch (e) {
            console.error(e);
            toast.error('Failed to load strategies');
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setEditingId(null);
        setName('');
        setTvId('');
        setFactor(1.0);
    };

    const handleEdit = (strat: Strategy) => {
        setEditingId(strat.id);
        setName(strat.name);
        setTvId(strat.tv_id);
        setFactor(strat.risk_factor);
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const payload = {
                name,
                tv_id: tvId,
                risk_factor: factor
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
        if (!confirm('Are you sure you want to delete this strategy?')) return;
        try {
            await axios.delete(`${API_BASE}/strategies/${id}`);
            toast.success('Strategy Deleted');
            fetchStrategies();
            if (editingId === id) resetForm();
        } catch (e) {
            toast.error('Failed to delete strategy');
        }
    };

    return (
        <div className="space-y-8 animate-fade-in">
            {/* Create/Edit Section */}
            <section className={`border rounded-2xl p-6 transition-all ${editingId ? 'bg-indigo-500/5 border-indigo-500/30' : 'bg-slate-900/50 border-slate-800'}`}>
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-semibold flex items-center gap-2">
                        {editingId ? <Pencil className="w-5 h-5 text-indigo-400" /> : <Plus className="w-5 h-5 text-indigo-400" />}
                        {editingId ? 'Edit Strategy' : 'Add New Strategy'}
                    </h2>
                    {editingId && (
                        <button
                            onClick={resetForm}
                            className="text-slate-400 hover:text-white text-xs flex items-center gap-1 bg-slate-800 px-3 py-1 rounded-lg"
                        >
                            <X className="w-3 h-3" /> Cancel Edit
                        </button>
                    )}
                </div>

                <form onSubmit={handleSubmit} className="flex flex-col md:flex-row gap-6 items-end">
                    <div className="flex-1 w-full">
                        <label className="block text-slate-400 text-xs uppercase mb-2 font-bold tracking-wider">Display Name</label>
                        <div className="relative group">
                            <Layers className="absolute left-3 top-3 w-4 h-4 text-slate-500 group-focus-within:text-indigo-400 transition-colors" />
                            <input
                                type="text"
                                required
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2.5 pl-10 pr-4 text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all placeholder:text-slate-600"
                                placeholder="e.g. Scalp Alpha"
                                value={name}
                                onChange={e => setName(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="flex-1 w-full">
                        <div className="flex items-center gap-2 mb-2">
                            <label className="block text-slate-400 text-xs uppercase font-bold tracking-wider">Webhook ID (tv_id)</label>
                            <div className="relative group cursor-help">
                                <Info className="w-3.5 h-3.5 text-slate-500 hover:text-indigo-400 transition-colors" />
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-slate-800 text-slate-200 text-xs rounded-lg shadow-xl border border-slate-700 opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-10 text-center leading-relaxed">
                                    Referenced in your TradingView alert JSON as <code className="bg-slate-950 px-1 py-0.5 rounded text-indigo-300">"strat": "your_id"</code>
                                    <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-800 rotate-45 border-r border-b border-slate-700"></div>
                                </div>
                            </div>
                        </div>
                        <div className="relative group">
                            <Hash className="absolute left-3 top-3 w-4 h-4 text-slate-500 group-focus-within:text-violet-400 transition-colors" />
                            <input
                                type="text"
                                required
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2.5 pl-10 pr-4 text-white focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500 transition-all font-mono text-sm placeholder:text-slate-600"
                                placeholder="e.g. scalp_v1"
                                value={tvId}
                                onChange={e => setTvId(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="w-full md:w-64">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <label className="block text-slate-400 text-xs uppercase font-bold tracking-wider">Risk Factor</label>
                                <div className="relative group cursor-help">
                                    <Info className="w-3.5 h-3.5 text-slate-500 hover:text-indigo-400 transition-colors" />
                                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-slate-800 text-slate-200 text-[10px] rounded-lg shadow-xl border border-slate-700 opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-10 text-center">
                                        Min: 0.5 | Increment: 0.1
                                        <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-800 rotate-45 border-r border-b border-slate-700"></div>
                                    </div>
                                </div>
                            </div>
                            <span className="text-[10px] text-emerald-400 font-mono">
                                ≈ ${(config?.risk_per_trade * factor).toFixed(2)}
                            </span>
                        </div>
                        <div className="relative group">
                            <DollarSign className="absolute left-3 top-3 w-4 h-4 text-slate-500 group-focus-within:text-emerald-400 transition-colors" />
                            <input
                                type="number"
                                min="0.5"
                                step="0.1"
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2.5 pl-10 pr-4 text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all font-mono placeholder:text-slate-700"
                                placeholder="1.0"
                                value={factor}
                                onChange={e => setFactor(parseFloat(e.target.value))}
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        className={`w-full md:w-auto font-bold py-2.5 px-8 rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg ${editingId
                            ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-900/20'
                            : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-900/20'
                            }`}
                    >
                        {editingId ? <Save className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
                        {editingId ? 'Save Changes' : 'Add Strategy'}
                    </button>
                </form>
            </section>

            {/* List Section */}
            <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                    <Layers className="w-5 h-5 text-indigo-400" />
                    Active Strategies
                </h2>

                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="text-slate-500 border-b border-slate-800 uppercase text-xs tracking-wider">
                            <tr>
                                <th className="py-4 px-4 font-bold">Name</th>
                                <th className="py-4 px-4 font-bold">Webhook ID (TV_ID)</th>
                                <th className="py-4 px-4 text-right font-bold">Risk Factor</th>
                                <th className="py-4 px-4 text-right font-bold">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                            {strategies.map((strat) => (
                                <tr key={strat.id} className={`transition-colors ${editingId === strat.id ? 'bg-indigo-500/10' : 'hover:bg-slate-800/30'}`}>
                                    <td className="py-4 px-4 font-bold text-white">{strat.name}</td>
                                    <td className="py-4 px-4">
                                        <span className="font-mono text-xs text-violet-300 bg-violet-500/10 border border-violet-500/20 rounded-md px-2 py-1">
                                            {strat.tv_id}
                                        </span>
                                    </td>
                                    <td className="py-4 px-4 text-right font-mono">
                                        <div className="flex flex-col items-end">
                                            <span className="text-emerald-400 font-bold">{strat.risk_factor.toFixed(1)}x</span>
                                            <span className="text-[10px] text-slate-500 hidden sm:inline-block">
                                                ≈ ${(config ? config.risk_per_trade * strat.risk_factor : 0).toFixed(2)}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="py-4 px-4 text-right">
                                        <div className="flex justify-end gap-2">
                                            <button
                                                onClick={() => handleEdit(strat)}
                                                className="p-2 bg-slate-800 hover:bg-indigo-500/20 text-slate-400 hover:text-indigo-400 rounded-lg transition-colors border border-transparent hover:border-indigo-500/30"
                                                title="Edit Strategy"
                                            >
                                                <Pencil className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(strat.id)}
                                                className="p-2 bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 rounded-lg transition-colors border border-transparent hover:border-red-500/30"
                                                title="Delete Strategy"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {strategies.length === 0 && !loading && (
                                <tr>
                                    <td colSpan={4} className="py-12 text-center text-slate-500 italic">
                                        <div className="flex flex-col items-center gap-2">
                                            <Layers className="w-8 h-8 text-slate-700" />
                                            <p>No strategies defined yet.</p>
                                            <p className="text-xs">Incoming webhooks will use the global risk setting (1.0x).</p>
                                        </div>
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
