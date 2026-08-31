import type { ReactNode } from 'react';
import { cn } from '../../utils/cn';

type Variant = 'success' | 'danger' | 'warning' | 'info' | 'neutral' | 'violet';

const variantClass: Record<Variant, string> = {
    success: 'badge-success',
    danger: 'badge-danger',
    warning: 'badge-warning',
    info: 'badge-info',
    neutral: 'badge-neutral',
    violet: 'badge-violet',
};

interface BadgeProps {
    variant?: Variant;
    /** Renders a small status dot before the content. */
    dot?: boolean;
    className?: string;
    children: ReactNode;
}

export function Badge({ variant = 'neutral', dot = false, className, children }: BadgeProps) {
    return (
        <span className={cn(variantClass[variant], className)}>
            {dot && <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" aria-hidden="true" />}
            {children}
        </span>
    );
}
