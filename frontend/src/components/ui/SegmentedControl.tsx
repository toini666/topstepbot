import { cn } from '../../utils/cn';

interface SegmentedControlProps<T extends string> {
    options: readonly { value: T; label: string }[];
    value: T;
    onChange: (value: T) => void;
    className?: string;
    'aria-label'?: string;
}

/** Segmented filter control (period filters, view switches). */
export function SegmentedControl<T extends string>({
    options,
    value,
    onChange,
    className,
    'aria-label': ariaLabel,
}: SegmentedControlProps<T>) {
    return (
        <div className={cn('filter-group', className)} role="group" aria-label={ariaLabel}>
            {options.map(opt => (
                <button
                    key={opt.value}
                    type="button"
                    onClick={() => onChange(opt.value)}
                    aria-pressed={value === opt.value}
                    className={value === opt.value ? 'filter-btn-active' : 'filter-btn-inactive'}
                >
                    {opt.label}
                </button>
            ))}
        </div>
    );
}
