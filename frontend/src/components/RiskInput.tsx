import { useState } from 'react';
import { Edit2, Check, X } from 'lucide-react';
import { toast } from 'sonner';

interface RiskInputProps {
    currentValue: number;
    onSave: (newValue: number) => void;
    isLoading?: boolean;
}

export function RiskInput({ currentValue, onSave, isLoading = false }: RiskInputProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [value, setValue] = useState(currentValue.toString());

    const handleEdit = () => {
        setValue(currentValue.toString());
        setIsEditing(true);
    };

    const handleCancel = () => {
        setIsEditing(false);
        setValue(currentValue.toString());
    };

    const handleSave = () => {
        const numValue = parseFloat(value);
        if (isNaN(numValue) || numValue < 0) {
            toast.error("Please enter a valid positive number");
            return;
        }

        // Only save if value changed
        if (numValue !== currentValue) {
            onSave(numValue);
        }
        setIsEditing(false);
    };

    if (isEditing) {
        return (
            <div className="flex items-center gap-1 animate-fade-in">
                <span className="text-slate-500">$</span>
                <input
                    type="number"
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    className="w-24 bg-slate-800 border border-indigo-500 rounded px-2 py-1 text-white font-mono text-right focus:outline-none shadow-[0_0_10px_rgba(99,102,241,0.2)] transition-all [-moz-appearance:_textfield] [&::-webkit-inner-spin-button]:m-0 [&::-webkit-inner-spin-button]:appearance-none"
                    step="25"
                    min="0"
                    autoFocus
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSave();
                        if (e.key === 'Escape') handleCancel();
                    }}
                />
                <div className="flex gap-1 ml-1">
                    <button
                        onClick={handleSave}
                        disabled={isLoading}
                        className="p-1 bg-green-500/10 text-green-400 hover:bg-green-500/20 rounded border border-green-500/20 transition-colors"
                        title="Save (Enter)"
                    >
                        <Check className="w-3.5 h-3.5" />
                    </button>
                    <button
                        onClick={handleCancel}
                        disabled={isLoading}
                        className="p-1 bg-red-500/10 text-red-400 hover:bg-red-500/20 rounded border border-red-500/20 transition-colors"
                        title="Cancel (Esc)"
                    >
                        <X className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="flex items-center justify-end gap-2 group">
            <span className="font-mono text-white text-lg font-bold tracking-tight">${currentValue}</span>
            <button
                onClick={handleEdit}
                className="p-1.5 text-slate-500 hover:text-indigo-400 hover:bg-indigo-500/10 rounded transition-all"
                title="Edit Risk Amount"
            >
                <Edit2 className="w-3.5 h-3.5" />
            </button>
        </div>
    );
}
