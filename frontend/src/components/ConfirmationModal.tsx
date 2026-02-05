
import { AlertTriangle, Info, X } from 'lucide-react';

interface ConfirmationModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    title: string;
    message: string;
    type?: 'danger' | 'info';
    confirmText?: string;
    cancelText?: string;
}

export function ConfirmationModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    type = 'info',
    confirmText = 'Confirm',
    cancelText = 'Cancel'
}: ConfirmationModalProps) {
    if (!isOpen) return null;

    return (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
            <div
                className="modal-container w-full max-w-md"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Glow effect */}
                <div className={`absolute top-0 left-0 right-0 h-1 ${type === 'danger' ? 'bg-red-500' : 'bg-indigo-500'}`} />

                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
                    aria-label="Close dialog"
                >
                    <X size={20} />
                </button>

                <div className="p-6">
                    <div className="flex items-start gap-4">
                        <div className={`p-3 rounded-full shrink-0 ${type === 'danger' ? 'bg-red-500/10 text-red-500' : 'bg-indigo-500/10 text-indigo-500'}`}>
                            {type === 'danger' ? <AlertTriangle size={24} /> : <Info size={24} />}
                        </div>

                        <div className="flex-1">
                            <h3 id="confirm-title" className="text-xl font-bold text-white mb-2">{title}</h3>
                            <p className="text-slate-300 leading-relaxed text-sm">
                                {message}
                            </p>
                        </div>
                    </div>

                    <div className="mt-8 flex justify-end gap-3">
                        <button
                            onClick={onClose}
                            className="btn-ghost"
                        >
                            {cancelText}
                        </button>
                        <button
                            onClick={() => {
                                onConfirm();
                                onClose();
                            }}
                            className={type === 'danger' ? 'btn-danger' : 'btn-primary'}
                        >
                            {confirmText}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
