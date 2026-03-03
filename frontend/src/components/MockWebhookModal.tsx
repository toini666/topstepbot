import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { X, Play, AlertTriangle, ChevronDown, Check, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE } from '../config';

interface MockWebhookModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const ALERT_TYPES = ['SETUP', 'SIGNAL', 'PARTIAL', 'CLOSE', 'MOVEBE'] as const;
const TIMEFRAMES = ['M1', 'M2', 'M5', 'M15', 'H1', 'H4', 'D1'] as const;

export function MockWebhookModal({ isOpen, onClose }: MockWebhookModalProps) {
    const [formData, setFormData] = useState({
        ticker: 'MNQ1!',
        type: 'SIGNAL' as typeof ALERT_TYPES[number],
        side: 'BUY',
        entry: '20000',
        sl: '19950',
        tp: '20050',
        strat: 'default',
        timeframe: 'M5' as typeof TIMEFRAMES[number]
    });

    // Dropdown states
    const [typeOpen, setTypeOpen] = useState(false);
    const [sideOpen, setSideOpen] = useState(false);
    const [tfOpen, setTfOpen] = useState(false);

    const typeRef = useRef<HTMLDivElement>(null);
    const sideRef = useRef<HTMLDivElement>(null);
    const tfRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (typeRef.current && !typeRef.current.contains(event.target as Node)) setTypeOpen(false);
            if (sideRef.current && !sideRef.current.contains(event.target as Node)) setSideOpen(false);
            if (tfRef.current && !tfRef.current.contains(event.target as Node)) setTfOpen(false);
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    if (!isOpen) return null;

    const parseNumber = (val: string | number) => {
        if (typeof val === 'number') return val;
        if (!val) return 0;
        return Number(val.toString().replace(/,/g, '.'));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const payload = {
                ticker: formData.ticker,
                type: formData.type,
                side: formData.side,
                entry: parseNumber(formData.entry),
                stop: ['CLOSE', 'MOVEBE'].includes(formData.type) ? null : parseNumber(formData.sl),
                tp: ['CLOSE', 'MOVEBE'].includes(formData.type) ? null : parseNumber(formData.tp),
                strat: formData.strat || 'default',
                timeframe: formData.timeframe
            };

            await axios.post(`${API_BASE}/webhook`, payload);
            toast.success(`${formData.type} Webhook Sent Successfully!`);
            onClose();
        } catch (err: any) {
            console.error(err);
            toast.error("Failed to send webhook: " + (err.response?.data?.detail || err.message));
        }
    };

    const showEntry = formData.type === 'SIGNAL' || formData.type === 'PARTIAL' || formData.type === 'CLOSE' || formData.type === 'MOVEBE';
    const showSlTp = formData.type === 'SIGNAL' || formData.type === 'PARTIAL';
    const showSide = formData.type !== 'CLOSE';

    return (
        <div className="fixed inset-0 z-50 h-screen w-screen flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <Play className="w-5 h-5 text-blue-400" />
                        Mock Webhook
                    </h2>
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        {/* Alert Type */}
                        <div ref={typeRef} className="relative">
                            <label className="block text-xs font-bold text-slate-400 mb-1">Type</label>
                            <button
                                type="button"
                                onClick={() => setTypeOpen(!typeOpen)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white flex justify-between items-center focus:outline-none focus:border-blue-500 hover:bg-slate-900 transition-colors"
                            >
                                <span className={`font-mono ${formData.type === 'SIGNAL' ? 'text-emerald-400' :
                                    formData.type === 'PARTIAL' ? 'text-amber-400' :
                                        formData.type === 'CLOSE' ? 'text-red-400' :
                                            formData.type === 'MOVEBE' ? 'text-blue-400' :
                                                'text-slate-400'
                                    }`}>{formData.type}</span>
                                <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform ${typeOpen ? 'rotate-180' : ''}`} />
                            </button>

                            {typeOpen && (
                                <div className="absolute top-full left-0 mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20">
                                    {ALERT_TYPES.map((opt) => (
                                        <button
                                            key={opt}
                                            type="button"
                                            onClick={() => {
                                                setFormData({ ...formData, type: opt });
                                                setTypeOpen(false);
                                            }}
                                            className={`w-full text-left px-4 py-2 flex items-center justify-between transition-colors hover:bg-slate-700/50 ${formData.type === opt
                                                ? opt === 'SIGNAL' ? 'text-emerald-400 bg-emerald-500/10'
                                                    : opt === 'PARTIAL' ? 'text-amber-400 bg-amber-500/10'
                                                        : opt === 'CLOSE' ? 'text-red-400 bg-red-500/10'
                                                            : opt === 'MOVEBE' ? 'text-blue-400 bg-blue-500/10'
                                                                : 'text-slate-400 bg-slate-500/10'
                                                : 'text-slate-300'
                                                }`}
                                        >
                                            <span className="font-mono text-sm">{opt}</span>
                                            {formData.type === opt && <Check className="w-3 h-3" />}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Timeframe */}
                        <div ref={tfRef} className="relative">
                            <label className="block text-xs font-bold text-slate-400 mb-1 flex items-center gap-1">
                                <Clock className="w-3 h-3" /> Timeframe
                            </label>
                            <button
                                type="button"
                                onClick={() => setTfOpen(!tfOpen)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white flex justify-between items-center focus:outline-none focus:border-indigo-500 hover:bg-slate-900 transition-colors"
                            >
                                <span className="font-mono text-indigo-400">{formData.timeframe}</span>
                                <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform ${tfOpen ? 'rotate-180' : ''}`} />
                            </button>

                            {tfOpen && (
                                <div className="absolute top-full left-0 mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20">
                                    {TIMEFRAMES.map((opt) => (
                                        <button
                                            key={opt}
                                            type="button"
                                            onClick={() => {
                                                setFormData({ ...formData, timeframe: opt });
                                                setTfOpen(false);
                                            }}
                                            className={`w-full text-left px-4 py-2 flex items-center justify-between transition-colors hover:bg-slate-700/50 ${formData.timeframe === opt ? 'text-indigo-400 bg-indigo-500/10' : 'text-slate-300'
                                                }`}
                                        >
                                            <span className="font-mono text-sm">{opt}</span>
                                            {formData.timeframe === opt && <Check className="w-3 h-3" />}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        {/* Ticker */}
                        <div>
                            <label className="block text-xs font-bold text-slate-400 mb-1">Ticker</label>
                            <input
                                type="text"
                                value={formData.ticker}
                                onChange={e => setFormData({ ...formData, ticker: e.target.value.toUpperCase() })}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 font-mono"
                            />
                        </div>

                        {/* Side */}
                        {showSide && (
                            <div ref={sideRef} className="relative">
                                <label className="block text-xs font-bold text-slate-400 mb-1">Side</label>
                                <button
                                    type="button"
                                    onClick={() => setSideOpen(!sideOpen)}
                                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white flex justify-between items-center focus:outline-none focus:border-blue-500 hover:bg-slate-900 transition-colors"
                                >
                                    <span className={formData.side === 'BUY' ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>
                                        {formData.side === 'BUY' ? 'BUY' : 'SELL'}
                                    </span>
                                    <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform ${sideOpen ? 'rotate-180' : ''}`} />
                                </button>

                                {sideOpen && (
                                    <div className="absolute top-full left-0 mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20">
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setFormData({ ...formData, side: 'BUY' });
                                                setSideOpen(false);
                                            }}
                                            className={`w-full text-left px-4 py-2 flex items-center justify-between transition-colors hover:bg-slate-700/50 ${formData.side === 'BUY' ? 'text-green-400 bg-green-500/10' : 'text-slate-300'
                                                }`}
                                        >
                                            <span className="font-mono text-sm font-bold">BUY</span>
                                            {formData.side === 'BUY' && <Check className="w-3 h-3" />}
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setFormData({ ...formData, side: 'SELL' });
                                                setSideOpen(false);
                                            }}
                                            className={`w-full text-left px-4 py-2 flex items-center justify-between transition-colors hover:bg-slate-700/50 ${formData.side === 'SELL' ? 'text-red-400 bg-red-500/10' : 'text-slate-300'
                                                }`}
                                        >
                                            <span className="font-mono text-sm font-bold">SELL</span>
                                            {formData.side === 'SELL' && <Check className="w-3 h-3" />}
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Price Fields */}
                    {showEntry && (
                        <div className={`grid gap-4 ${showSlTp ? 'grid-cols-3' : 'grid-cols-1'}`}>
                            <div>
                                <label className="block text-xs font-bold text-slate-400 mb-1">Entry</label>
                                <input
                                    type="text"
                                    value={formData.entry}
                                    onChange={e => setFormData({ ...formData, entry: e.target.value })}
                                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 font-mono"
                                />
                            </div>
                            {showSlTp && (
                                <>
                                    <div>
                                        <label className="block text-xs font-bold text-slate-400 mb-1">SL</label>
                                        <input
                                            type="text"
                                            value={formData.sl}
                                            onChange={e => setFormData({ ...formData, sl: e.target.value })}
                                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-red-400 focus:outline-none focus:border-red-500 font-mono"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-bold text-slate-400 mb-1">TP</label>
                                        <input
                                            type="text"
                                            value={formData.tp}
                                            onChange={e => setFormData({ ...formData, tp: e.target.value })}
                                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-green-400 focus:outline-none focus:border-green-500 font-mono"
                                        />
                                    </div>
                                </>
                            )}
                        </div>
                    )}

                    {/* Strategy */}
                    <div>
                        <label className="block text-xs font-bold text-slate-400 mb-1">Strategy ID</label>
                        <input
                            type="text"
                            value={formData.strat}
                            onChange={e => setFormData({ ...formData, strat: e.target.value })}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-violet-400 focus:outline-none focus:border-violet-500 font-mono"
                            placeholder="default"
                        />
                    </div>

                    <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 flex items-start gap-3">
                        <AlertTriangle className="w-5 h-5 text-blue-400 shrink-0" />
                        <p className="text-xs text-blue-200">
                            This triggers a REAL webhook signal sent to ALL configured accounts.
                            Risk checks and validation will apply per account.
                        </p>
                    </div>

                    <button
                        type="submit"
                        className={`w-full font-bold py-3 rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 ${formData.type === 'SIGNAL' ? 'bg-emerald-600 hover:bg-emerald-700 shadow-emerald-900/30' :
                            formData.type === 'PARTIAL' ? 'bg-amber-600 hover:bg-amber-700 shadow-amber-900/30' :
                                formData.type === 'CLOSE' ? 'bg-red-600 hover:bg-red-700 shadow-red-900/30' :
                                    formData.type === 'MOVEBE' ? 'bg-blue-600 hover:bg-blue-700 shadow-blue-900/30' :
                                        'bg-slate-600 hover:bg-slate-700 shadow-slate-900/30'
                            } text-white`}
                    >
                        <Play className="w-4 h-4" />
                        Send {formData.type} Signal
                    </button>
                </form>
            </div>
        </div>
    );
}
