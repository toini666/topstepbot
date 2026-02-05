/**
 * Sessions Settings Tab Component
 * 
 * Configure market session times (Asia, London, New York).
 */

import type { TradingSession } from '../../types';
import { TimePicker } from '../TimePicker';

interface SessionsTabProps {
    sessions: TradingSession[];
    onUpdateSession: (id: number, field: keyof TradingSession, value: any) => void;
}

export function SessionsTab({ sessions, onUpdateSession }: SessionsTabProps) {
    return (
        <div className="space-y-4">
            <p className="text-sm text-slate-400">
                Configure market sessions times. Active sessions are used for strategy filtering.
            </p>

            {sessions.map(session => (
                <div key={session.id} className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                    <div className="flex justify-between items-center">
                        <div>
                            <span className="font-bold text-white">{session.display_name}</span>
                            <span className="text-slate-500 text-sm ml-2">({session.name})</span>
                        </div>
                        <button
                            onClick={() => onUpdateSession(session.id, 'is_active', !session.is_active)}
                            aria-pressed={session.is_active}
                            className={session.is_active ? 'badge-success hover:bg-emerald-500/30 transition-colors cursor-pointer' : 'badge-neutral hover:bg-slate-600 transition-colors cursor-pointer'}
                        >
                            {session.is_active ? 'Active' : 'Inactive'}
                        </button>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500 uppercase font-bold">Start</span>
                            <TimePicker
                                value={session.start_time}
                                onChange={(val) => onUpdateSession(session.id, 'start_time', val)}
                            />
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500 uppercase font-bold">End</span>
                            <TimePicker
                                value={session.end_time}
                                onChange={(val) => onUpdateSession(session.id, 'end_time', val)}
                            />
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}
