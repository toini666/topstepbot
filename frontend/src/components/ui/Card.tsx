import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../../utils/cn';

interface CardProps {
    children: ReactNode;
    className?: string;
    /** Adds a hover elevation response (for interactive panels). */
    hover?: boolean;
}

/** Console panel: layered surface, hairline border, top-edge highlight. */
export function Card({ children, className, hover }: CardProps) {
    return (
        <div className={cn('card', hover && 'card-hover', className)}>
            {children}
        </div>
    );
}

interface CardHeaderProps {
    icon?: LucideIcon;
    iconClassName?: string;
    title: ReactNode;
    /** Small mono/annotation next to the title (e.g. a count). */
    annotation?: ReactNode;
    /** Right side of the header row: filters, actions. */
    actions?: ReactNode;
    className?: string;
}

/** Standard panel header row: icon + title on the left, actions on the right. */
export function CardHeader({ icon: Icon, iconClassName, title, annotation, actions, className }: CardHeaderProps) {
    return (
        <div className={cn('flex items-center justify-between gap-3 flex-wrap mb-4', className)}>
            <h2 className="section-title">
                {Icon && <Icon className={cn('w-5 h-5 text-indigo-400', iconClassName)} />}
                {title}
                {annotation != null && (
                    <span className="font-mono text-xs font-medium text-slate-500 mt-0.5">{annotation}</span>
                )}
            </h2>
            {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
        </div>
    );
}
