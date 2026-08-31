import { cn } from '../../utils/cn';

interface SpinnerProps {
    size?: 'sm' | 'md' | 'lg';
    className?: string;
}

const sizeClass = { sm: 'w-4 h-4 border-2', md: 'w-6 h-6 border-2', lg: 'w-9 h-9 border-[3px]' };

export function Spinner({ size = 'md', className }: SpinnerProps) {
    return (
        <span
            className={cn(
                'inline-block rounded-full border-indigo-400 border-t-transparent animate-spin',
                sizeClass[size],
                className,
            )}
            role="status"
            aria-label="Loading"
        />
    );
}

interface FullScreenLoaderProps {
    message?: string;
}

/** Full-viewport loading screen used by App boot states. */
export function FullScreenLoader({ message = 'Loading…' }: FullScreenLoaderProps) {
    return (
        <div className="h-screen flex items-center justify-center text-white" role="status" aria-busy="true">
            <div className="flex flex-col items-center gap-5 animate-rise">
                <div className="relative">
                    <div className="w-12 h-12 rounded-2xl bg-slate-900/80 border border-slate-700/60 flex items-center justify-center shadow-[0_0_40px_-8px_rgba(99,102,241,0.45)]">
                        <Spinner size="md" />
                    </div>
                </div>
                <span className="text-slate-400 text-sm font-medium tracking-wide">{message}</span>
            </div>
        </div>
    );
}
