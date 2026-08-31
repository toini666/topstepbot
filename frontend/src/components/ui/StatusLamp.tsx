import { cn } from '../../utils/cn';

type LampColor = 'emerald' | 'red' | 'amber' | 'sky' | 'slate';

interface StatusLampProps {
    color: LampColor;
    /** Pulses like a live console lamp. */
    live?: boolean;
    /** Caption before the value, e.g. "STATUS". */
    label?: string;
    /** Mono value, e.g. "ONLINE". */
    value?: string;
    className?: string;
    title?: string;
}

const valueColor: Record<LampColor, string> = {
    emerald: 'text-emerald-300',
    red: 'text-red-300',
    amber: 'text-amber-300',
    sky: 'text-sky-300',
    slate: 'text-slate-400',
};

/**
 * Console status lamp: a colored dot (optionally breathing) with an
 * uppercase caption and a mono value. Used for ONLINE/MARKET/SESSION states.
 */
export function StatusLamp({ color, live = false, label, value, className, title }: StatusLampProps) {
    return (
        <div className={cn('status-pill', className)} title={title}>
            <span className={cn('lamp', `lamp-${color}`, live && 'lamp-live')} aria-hidden="true" />
            {label && <span className="micro-label">{label}</span>}
            {value && <span className={cn('font-mono text-xs font-bold', valueColor[color])}>{value}</span>}
        </div>
    );
}
