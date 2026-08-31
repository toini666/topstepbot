import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../../utils/cn';

interface EmptyStateProps {
    icon: LucideIcon;
    title: string;
    /** Secondary hint under the title. */
    hint?: string;
    /** Optional action (e.g. a button). */
    action?: ReactNode;
    className?: string;
}

/** Quiet empty state: ringed icon, title, hint. */
export function EmptyState({ icon: Icon, title, hint, action, className }: EmptyStateProps) {
    return (
        <div className={cn('empty-state', className)}>
            <div className="w-14 h-14 mx-auto mb-4 rounded-2xl flex items-center justify-center bg-slate-800/50 ring-1 ring-inset ring-slate-700/50">
                <Icon className="w-6 h-6 text-slate-500" aria-hidden="true" />
            </div>
            <p className="text-sm font-medium text-slate-300">{title}</p>
            {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
            {action && <div className="mt-4 flex justify-center">{action}</div>}
        </div>
    );
}
