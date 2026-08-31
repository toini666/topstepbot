import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../../utils/cn';

interface StatProps {
    label: string;
    value: ReactNode;
    icon?: LucideIcon;
    /** Directional coloring for P&L-style values. */
    tone?: 'up' | 'down' | 'flat' | 'neutral';
    /** Extra line under the value. */
    sub?: ReactNode;
    className?: string;
}

const toneClass = {
    up: 'readout-up',
    down: 'readout-down',
    flat: 'readout-flat',
    neutral: 'font-mono font-bold text-slate-100',
};

const iconTone = {
    up: 'text-emerald-400',
    down: 'text-red-400',
    flat: 'text-slate-400',
    neutral: 'text-indigo-400',
};

/** Console readout module: micro caption + big tabular-mono value. */
export function Stat({ label, value, icon: Icon, tone = 'neutral', sub, className }: StatProps) {
    return (
        <div className={cn('flex flex-col justify-between rounded-xl px-4 py-3 min-w-[9.5rem] bg-slate-900/60 border border-slate-800/60', className)}>
            <p className="micro-label mb-1.5">{label}</p>
            <div className="flex items-center gap-2">
                {Icon && <Icon className={cn('w-4 h-4 flex-shrink-0', iconTone[tone])} aria-hidden="true" />}
                <span className={cn('text-xl leading-tight', toneClass[tone])}>{value}</span>
            </div>
            {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
        </div>
    );
}
