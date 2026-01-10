import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { X, Play, AlertTriangle, ChevronDown, Check } from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE } from '../config';

interface MockWebhookModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function MockWebhookModal({ isOpen, onClose }: MockWebhookModalProps) {
    const [formData, setFormData] = useState({
        passphrase: 'secure_passphrase_here',
        time: new Date().toISOString(),
        exchange: 'CME_MINI',
        ticker: 'MNQ',
        bar: {
            time: new Date().toISOString(),
            open: 20000,
            high: 20010,
            low: 19990,
            close: 20005,
            volume: 100
        },
        strategy: {
            position_size: 1,
            order_action: 'buy',
            order_contracts: 1,
            order_price: 20000,
            order_id: 'mock_id',
            market_position: 'long',
            market_position_size: 1,
            prev_market_position: 'flat',
            prev_market_position_size: 0
        },
        type: 'SIGNAL',
        direction: 'BUY',
        entry: "20000",
        sl: "19950",
        tp: "20050",
        strategy_name: "RobReversal"
    });

    // Dropdown states
    const [typeOpen, setTypeOpen] = useState(false);
    const [directionOpen, setDirectionOpen] = useState(false);
    const typeRef = useRef<HTMLDivElement>(null);
    const directionRef = useRef<HTMLDivElement>(null);

    // Close dropdowns when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (typeRef.current && !typeRef.current.contains(event.target as Node)) {
                setTypeOpen(false);
            }
            if (directionRef.current && !directionRef.current.contains(event.target as Node)) {
                setDirectionOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    if (!isOpen) return null;

    const parseNumber = (val: string | number) => {
        if (typeof val === 'number') return val;
        if (!val) return 0;
        // Replace comma with dot and parse safely
        return Number(val.toString().replace(/,/g, '.'));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const entryVal = parseNumber(formData.entry);
            const slVal = parseNumber(formData.sl);
            const tpVal = parseNumber(formData.tp);
            // Construct payload matching schemas.py TradingViewAlert
            const payload = {
                passphrase: "secure_passphrase_here",
                ticker: formData.ticker,
                type: formData.type,
                direction: formData.direction, // "BUY" or "SELL"
                entry: entryVal,
                stop: slVal,
                tp: tpVal,
                strat: formData.strategy_name || "default"
            };

            await axios.post(`${API_BASE}/webhook`, payload);
            toast.success("Webhook Sent Successfully!");
            onClose();
        } catch (err: any) {
            console.error(err);
            toast.error("Failed to send webhook: " + (err.response?.data?.detail || err.message));
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <Play className="w-5 h-5 text-blue-400" />
                        Mock Webhook Trigger
                    </h2>
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">

                    <div className="grid grid-cols-2 gap-4">
                        {/* Custom Dropdown: Type */}
                        <div ref={typeRef} className="relative">
                            <label className="block text-xs font-bold text-slate-400 mb-1">Type</label>
                            <button
                                type="button"
                                onClick={() => setTypeOpen(!typeOpen)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white flex justify-between items-center focus:outline-none focus:border-blue-500 hover:bg-slate-900 transition-colors"
                            >
                                <span>{formData.type}</span>
                                <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform ${typeOpen ? 'rotate-180' : ''}`} />
                            </button>

                            {typeOpen && (
                                <div className="absolute top-full left-0 mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20">
                                    {['SIGNAL', 'SETUP'].map((opt) => (
                                        <button
                                            key={opt}
                                            type="button"
                                            onClick={() => {
                                                setFormData({ ...formData, type: opt });
                                                setTypeOpen(false);
                                            }}
                                            className={`w-full text-left px-4 py-2 flex items-center justify-between transition-colors hover:bg-slate-700/50 ${formData.type === opt ? 'text-blue-400 bg-blue-500/10' : 'text-slate-300'
                                                }`}
                                        >
                                            <span className="font-mono text-sm">{opt}</span>
                                            {formData.type === opt && <Check className="w-3 h-3" />}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Custom Dropdown: Direction */}
                        <div ref={directionRef} className="relative">
                            <label className="block text-xs font-bold text-slate-400 mb-1">Direction</label>
                            <button
                                type="button"
                                onClick={() => setDirectionOpen(!directionOpen)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white flex justify-between items-center focus:outline-none focus:border-blue-500 hover:bg-slate-900 transition-colors"
                            >
                                <span className={formData.direction === 'BUY' ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>
                                    {formData.direction === 'BUY' ? 'BUY (Long)' : 'SELL (Short)'}
                                </span>
                                <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform ${directionOpen ? 'rotate-180' : ''}`} />
                            </button>

                            {directionOpen && (
                                <div className="absolute top-full left-0 mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setFormData({ ...formData, direction: 'BUY' });
                                            setDirectionOpen(false);
                                        }}
                                        className={`w-full text-left px-4 py-2 flex items-center justify-between transition-colors hover:bg-slate-700/50 ${formData.direction === 'BUY' ? 'text-green-400 bg-green-500/10' : 'text-slate-300'
                                            }`}
                                    >
                                        <span className="font-mono text-sm font-bold">BUY (Long)</span>
                                        {formData.direction === 'BUY' && <Check className="w-3 h-3" />}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setFormData({ ...formData, direction: 'SELL' });
                                            setDirectionOpen(false);
                                        }}
                                        className={`w-full text-left px-4 py-2 flex items-center justify-between transition-colors hover:bg-slate-700/50 ${formData.direction === 'SELL' ? 'text-red-400 bg-red-500/10' : 'text-slate-300'
                                            }`}
                                    >
                                        <span className="font-mono text-sm font-bold">SELL (Short)</span>
                                        {formData.direction === 'SELL' && <Check className="w-3 h-3" />}
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-bold text-slate-400 mb-1">Ticker</label>
                        <input
                            type="text"
                            value={formData.ticker}
                            onChange={e => setFormData({ ...formData, ticker: e.target.value.toUpperCase() })}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 font-mono"
                        />
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                        <div>
                            <label className="block text-xs font-bold text-slate-400 mb-1">Entry</label>
                            <input
                                type="text"
                                value={formData.entry}
                                onChange={e => setFormData({ ...formData, entry: e.target.value })}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 font-mono"
                                placeholder="0.00"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-bold text-slate-400 mb-1">SL</label>
                            <input
                                type="text"
                                value={formData.sl}
                                onChange={e => setFormData({ ...formData, sl: e.target.value })}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-red-400 focus:outline-none focus:border-red-500 font-mono"
                                placeholder="0.00"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-bold text-slate-400 mb-1">TP</label>
                            <input
                                type="text"
                                value={formData.tp}
                                onChange={e => setFormData({ ...formData, tp: e.target.value })}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-green-400 focus:outline-none focus:border-green-500 font-mono"
                                placeholder="0.00"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-bold text-slate-400 mb-1">Strategy (Optional)</label>
                        <input
                            type="text"
                            value={formData.strategy_name}
                            onChange={e => setFormData({ ...formData, strategy_name: e.target.value })}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-violet-400 focus:outline-none focus:border-violet-500 font-mono"
                            placeholder="RobReversal"
                        />
                    </div>



                    <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 flex items-start gap-3">
                        <AlertTriangle className="w-5 h-5 text-blue-400 shrink-0" />
                        <p className="text-xs text-blue-200">
                            This will trigger a REAL webhook signal processed by the backend.
                            Risk checks will apply.
                        </p>
                    </div>

                    <button
                        type="submit"
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition-all shadow-lg shadow-blue-900/20 flex items-center justify-center gap-2"
                    >
                        <Play className="w-4 h-4" />
                        Send Mock Signal
                    </button>
                </form>
            </div>
        </div>
    );
}
