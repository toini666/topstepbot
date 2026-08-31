
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

    const isDanger = type === 'danger';

    return (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
            <div
                className="modal-container w-full max-w-md"
                onClick={(e) => e.stopPropagation()}
            >
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-slate-500 hover:text-white transition-colors"
                    aria-label="Close dialog"
                >
                    <X size={18} />
                </button>

                <div className="p-6 pt-8 flex flex-col items-center text-center">
                    <div
                        className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 ${isDanger
                            ? 'bg-red-500/10 ring-1 ring-red-400/30'
                            : 'bg-indigo-500/10 ring-1 ring-indigo-400/30'
                            }`}
                    >
                        {isDanger ? (
                            <AlertTriangle className="w-6 h-6 text-red-400" aria-hidden="true" />
                        ) : (
                            <Info className="w-6 h-6 text-indigo-400" aria-hidden="true" />
                        )}
                    </div>

                    <h3 id="confirm-title" className="text-lg font-bold text-white tracking-tight mb-2">
                        {title}
                    </h3>
                    <p className="text-sm text-slate-400 leading-relaxed">
                        {message}
                    </p>
                </div>

                <div className="px-6 pb-6 flex justify-end gap-3">
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
                        className={isDanger ? 'btn-danger' : 'btn-primary'}
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </div>
    );
}
