/**
 * Logs Panel Component
 * 
 * Displays system logs with expandable details.
 */

import { useState, memo } from 'react';
import { Terminal, ChevronDown, ChevronRight, Copy } from 'lucide-react';
import { toast } from 'sonner';
import { formatInUserTz } from '../../utils/timezone';
import type { Log } from '../../types';

interface LogsPanelProps {
    logs: Log[];
    loadMoreLogs: () => void;
}

export const LogsPanel = memo(function LogsPanel({ logs, loadMoreLogs }: LogsPanelProps) {
    const [expandedLogs, setExpandedLogs] = useState<Set<number>>(new Set());

    const toggleLog = (id: number) => {
        const newSet = new Set(expandedLogs);
        if (newSet.has(id)) {
            newSet.delete(id);
        } else {
            newSet.add(id);
        }
        setExpandedLogs(newSet);
    };

    return (
        <div className="animate-fade-in h-[calc(100vh-250px)] min-h-[500px]">
            <section className="bg-black/40 border border-slate-800 rounded-2xl overflow-hidden flex flex-col h-full">
                <div className="bg-slate-900/80 p-4 border-b border-slate-800 flex justify-between items-center">
                    <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                        <Terminal className="w-4 h-4" />
                        System Logs
                    </h3>
                    <div className="flex gap-2 items-center">
                        <div className="flex gap-2">
                            <span className="w-2.5 h-2.5 rounded-full bg-red-500 opacity-80"></span>
                            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500 opacity-80"></span>
                            <span className="w-2.5 h-2.5 rounded-full bg-green-500 opacity-80"></span>
                        </div>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-2 custom-scrollbar font-medium">
                    {logs.map((log) => {
                        const isExpanded = expandedLogs.has(log.id);
                        const hasDetails = !!log.details;
                        const isLongMessage = log.message && log.message.length > 150;
                        const canExpand = hasDetails || isLongMessage;

                        return (
                            <div
                                key={log.id}
                                className={`flex flex-col hover:bg-slate-800/30 rounded px-2 -mx-2 transition-colors ${canExpand ? 'cursor-pointer' : ''}`}
                                onClick={() => canExpand && toggleLog(log.id)}
                            >
                                <div className="flex gap-3 p-0.5">
                                    <span className="text-slate-500 shrink-0 flex items-center gap-1 w-32">
                                        {canExpand && (
                                            isExpanded ? <ChevronDown className="w-3 h-3 text-slate-400" /> : <ChevronRight className="w-3 h-3 text-slate-400" />
                                        )}
                                        {!canExpand && <div className="w-3" />}
                                        {formatInUserTz(log.timestamp, 'dd/MM HH:mm:ss')}
                                    </span>
                                    <span className={`shrink-0 w-16 ${log.level === 'ERROR' ? 'text-red-400' :
                                        log.level === 'WARNING' ? 'text-yellow-400' :
                                            'text-blue-300'
                                        }`}>
                                        [{log.level}]
                                    </span>
                                    <span className="text-slate-300 break-words flex-1">
                                        {isExpanded || !isLongMessage ? log.message : log.message.substring(0, 150) + '...'}
                                    </span>
                                </div>

                                {isExpanded && hasDetails && (
                                    <div className="ml-10 mt-1 mb-2 relative group">
                                        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    const content = (() => {
                                                        try {
                                                            return JSON.stringify(JSON.parse(log.details || "{}"), null, 2);
                                                        } catch {
                                                            return log.details;
                                                        }
                                                    })();
                                                    if (content) {
                                                        navigator.clipboard.writeText(content);
                                                        toast.success("Log details copied!");
                                                    }
                                                }}
                                                className="p-1 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded border border-slate-700 shadow-lg"
                                                title="Copy to clipboard"
                                            >
                                                <Copy className="w-3 h-3" />
                                            </button>
                                        </div>
                                        <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800/50 overflow-x-auto">
                                            <pre className="text-[10px] text-slate-400 font-mono whitespace-pre-wrap">
                                                {(() => {
                                                    try {
                                                        return JSON.stringify(JSON.parse(log.details || "{}"), null, 2);
                                                    } catch {
                                                        return log.details;
                                                    }
                                                })()}
                                            </pre>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                    {logs.length === 0 && <span className="text-slate-600">Waiting for logs...</span>}

                    <div className="pt-2 flex justify-center">
                        <button
                            className="btn-ghost text-xs"
                            onClick={loadMoreLogs}
                        >
                            Load More Logs
                        </button>
                    </div>
                </div>
            </section>
        </div>
    );
});
