import type { ButtonHTMLAttributes, ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../../utils/cn';

type Variant = 'primary' | 'danger' | 'kill' | 'ghost' | 'outline';

const variantClass: Record<Variant, string> = {
    primary: 'btn-primary',
    danger: 'btn-danger',
    kill: 'btn-kill',
    ghost: 'btn-ghost',
    outline: 'btn-outline',
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: Variant;
    /** Compact size for toolbars and table actions. */
    size?: 'sm' | 'md';
    icon?: LucideIcon;
    /** Shows a spinner and disables the button. */
    loading?: boolean;
    children?: ReactNode;
}

export function Button({
    variant = 'primary',
    size = 'md',
    icon: Icon,
    loading = false,
    disabled,
    className,
    children,
    ...rest
}: ButtonProps) {
    return (
        <button
            className={cn(
                variantClass[variant],
                size === 'sm' && 'btn-sm',
                className,
            )}
            disabled={disabled || loading}
            {...rest}
        >
            {loading ? (
                <span
                    className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin"
                    aria-hidden="true"
                />
            ) : (
                Icon && <Icon className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} aria-hidden="true" />
            )}
            {children}
        </button>
    );
}
