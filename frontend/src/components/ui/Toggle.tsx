import { cn } from '../../utils/cn';

interface ToggleProps {
    checked: boolean;
    onChange: () => void;
    size?: 'sm' | 'md';
    disabled?: boolean;
    /** Accessible name for the switch. */
    label?: string;
    /** Track color when checked. Defaults to emerald (armed). */
    activeColor?: 'emerald' | 'indigo';
    className?: string;
}

/** Controlled switch styled as a console toggle. Purely presentational. */
export function Toggle({
    checked,
    onChange,
    size = 'md',
    disabled = false,
    label,
    activeColor = 'emerald',
    className,
}: ToggleProps) {
    const trackOn = activeColor === 'emerald'
        ? 'bg-emerald-500/90 border-emerald-400/50 shadow-[0_0_12px_-2px_rgba(16,185,129,0.5)]'
        : 'bg-indigo-500/90 border-indigo-400/50 shadow-[0_0_12px_-2px_rgba(99,102,241,0.5)]';

    return (
        <button
            type="button"
            role="switch"
            aria-checked={checked}
            aria-label={label}
            disabled={disabled}
            onClick={onChange}
            className={cn(
                size === 'sm' ? 'toggle-sm' : 'toggle-md',
                checked ? trackOn : 'bg-slate-700/80',
                disabled && 'opacity-40 cursor-not-allowed',
                className,
            )}
        >
            <span
                className={cn(
                    size === 'sm' ? 'toggle-dot-sm' : 'toggle-dot-md',
                    size === 'sm'
                        ? (checked ? 'translate-x-[1.15rem]' : 'translate-x-0.5')
                        : (checked ? 'translate-x-[1.4rem]' : 'translate-x-1'),
                )}
            />
        </button>
    );
}
