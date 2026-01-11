import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Clock } from 'lucide-react';

interface TimePickerProps {
    value: string; // Format "HH:MM"
    onChange: (value: string) => void;
    disabled?: boolean;
}

export function TimePicker({ value, onChange, disabled = false }: TimePickerProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [coords, setCoords] = useState({ top: 0, left: 0, width: 0 });
    const containerRef = useRef<HTMLDivElement>(null);

    // Parse current value
    const [hours, minutes] = value ? value.split(':') : ['00', '00'];

    useEffect(() => {
        const handleGlobalClick = (event: MouseEvent) => {
            const dropdown = document.getElementById('time-picker-dropdown');
            // Close if click is NOT in container AND NOT in dropdown
            if (
                containerRef.current &&
                !containerRef.current.contains(event.target as Node) &&
                (!dropdown || !dropdown.contains(event.target as Node))
            ) {
                setIsOpen(false);
            }
        };

        const onScroll = (event: Event) => {
            // Close on scroll ONLY if the scroll happened outside the dropdown
            // i.e. we are scrolling the main page body, not the internal list
            const dropdown = document.getElementById('time-picker-dropdown');
            if (dropdown && dropdown.contains(event.target as Node)) {
                return; // Ignore scrolls inside the dropdown
            }
            if (isOpen) setIsOpen(false);
        };

        if (isOpen) {
            window.addEventListener('scroll', onScroll, true);
            window.addEventListener('resize', onScroll);
            document.addEventListener('mousedown', handleGlobalClick);
        }

        return () => {
            window.removeEventListener('scroll', onScroll, true);
            window.removeEventListener('resize', onScroll);
            document.removeEventListener('mousedown', handleGlobalClick);
        };
    }, [isOpen]);

    const toggleOpen = () => {
        if (isOpen) {
            setIsOpen(false);
        } else if (containerRef.current && !disabled) {
            const rect = containerRef.current.getBoundingClientRect();
            setCoords({
                top: rect.bottom + window.scrollY + 4,
                left: rect.left + window.scrollX,
                width: 160 // Fixed width for dropdown
            });
            setIsOpen(true);
        }
    };

    const handleHourClick = (h: string) => {
        onChange(`${h}:${minutes}`);
    };

    const handleMinuteClick = (m: string) => {
        onChange(`${hours}:${m}`);
    };

    const hourOptions = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0'));
    const allMinutes = Array.from({ length: 60 }, (_, i) => i.toString().padStart(2, '0'));

    return (
        <div className="relative inline-block" ref={containerRef}>
            <button
                type="button"
                onClick={toggleOpen}
                disabled={disabled}
                className={`flex items-center gap-2 bg-slate-950 border ${isOpen ? 'border-indigo-500' : 'border-slate-800'} rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none transition-all w-[100px] justify-between ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:border-slate-700'}`}
            >
                <div className="flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span>{value || "00:00"}</span>
                </div>
                <ChevronDown className={`w-3 h-3 text-slate-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && createPortal(
                <div
                    id="time-picker-dropdown"
                    style={{
                        position: 'absolute',
                        top: coords.top,
                        left: coords.left,
                        width: coords.width,
                        zIndex: 9999
                    }}
                    className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl flex overflow-hidden h-[200px] animate-in fade-in zoom-in-95 duration-100"
                >
                    {/* Hours Column */}
                    <div className="flex-1 overflow-y-auto custom-scrollbar border-r border-slate-800">
                        <div className="px-2 py-1 text-[10px] text-slate-500 font-bold uppercase text-center sticky top-0 bg-slate-900 border-b border-slate-800 mb-1">Hr</div>
                        {hourOptions.map((h) => (
                            <button
                                key={h}
                                onClick={() => handleHourClick(h)}
                                className={`w-full text-center py-1.5 text-sm font-mono hover:bg-slate-800 transition-colors ${h === hours ? 'bg-indigo-600/20 text-indigo-400 font-bold' : 'text-slate-300'}`}
                            >
                                {h}
                            </button>
                        ))}
                    </div>

                    {/* Minutes Column */}
                    <div className="flex-1 overflow-y-auto custom-scrollbar">
                        <div className="px-2 py-1 text-[10px] text-slate-500 font-bold uppercase text-center sticky top-0 bg-slate-900 border-b border-slate-800 mb-1">Min</div>
                        {allMinutes.map((m) => (
                            <button
                                key={m}
                                onClick={() => handleMinuteClick(m)}
                                className={`w-full text-center py-1.5 text-sm font-mono hover:bg-slate-800 transition-colors ${m === minutes ? 'bg-indigo-600/20 text-indigo-400 font-bold' : 'text-slate-300'}`}
                            >
                                {m}
                            </button>
                        ))}
                    </div>
                </div>,
                document.body
            )}
        </div>
    );
}
