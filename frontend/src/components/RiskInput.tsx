import { useState } from 'react';
import { Edit2, Check, X } from 'lucide-react';
import { toast } from 'sonner';

interface RiskInputProps {
    currentValue: number;
    onSave: (newValue: number) => void;
    isLoading?: boolean;
    prefix?: string;  // Optional prefix (defaults to "$")
}

export function RiskInput({ currentValue, onSave, isLoading = false, prefix = "$" }: RiskInputProps) {
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
                {prefix && <span className="text-slate-500">{prefix}</span>}
                <input
                    type="number"
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    className="input-mono !w-24 text-right [-moz-appearance:_textfield] [&::-webkit-inner-spin-button]:m-0 [&::-webkit-inner-spin-button]:appearance-none"
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
                        className="p-1 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 rounded border border-emerald-500/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                        title="Save (Enter)"
                    >
                        <Check className="w-3.5 h-3.5" />
                    </button>
                    <button
                        onClick={handleCancel}
                        disabled={isLoading}
                        className="p-1 bg-red-500/10 text-red-400 hover:bg-red-500/20 rounded border border-red-500/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
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
            <span className="num text-white text-lg font-bold tracking-tight">{prefix}{currentValue}</span>
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
