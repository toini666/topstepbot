/**
 * Logs Panel Component
 *
 * Displays system logs with expandable details.
 */

import { useState, memo } from 'react';
import { Terminal, ChevronDown, ChevronRight, Copy, ScrollText } from 'lucide-react';
import { toast } from 'sonner';
import { formatInUserTz } from '../../utils/timezone';
import type { Log } from '../../types';
import { Card, CardHeader, Badge, EmptyState } from '../ui';

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
            <Card className="flex flex-col h-full overflow-hidden">
                <CardHeader
                    icon={Terminal}
                    title="System Logs"
                    actions={
                        <div className="flex gap-1.5" aria-hidden="true">
                            <span className="lamp lamp-red" />
                            <span className="lamp lamp-amber" />
                            <span className="lamp lamp-emerald" />
                        </div>
                    }
                />

                <div className="well custom-scrollbar flex-1 overflow-y-auto p-4 font-mono text-xs space-y-2 font-medium">
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
                                <div className="flex flex-wrap sm:flex-nowrap gap-x-3 gap-y-0.5 p-0.5 items-center">
                                    <span className="text-slate-500 shrink-0 flex items-center gap-1 w-32">
                                        {canExpand && (
                                            isExpanded ? <ChevronDown className="w-3 h-3 text-slate-400" /> : <ChevronRight className="w-3 h-3 text-slate-400" />
                                        )}
                                        {!canExpand && <div className="w-3" />}
                                        {formatInUserTz(log.timestamp, 'dd/MM HH:mm:ss')}
                                    </span>
                                    <span className="shrink-0 w-20">
                                        {log.level === 'ERROR' ? (
                                            <Badge variant="danger">{log.level}</Badge>
                                        ) : log.level === 'WARNING' ? (
                                            <Badge variant="warning">{log.level}</Badge>
                                        ) : (
                                            <Badge variant="info">{log.level}</Badge>
                                        )}
                                    </span>
                                    <span className="text-slate-300 break-words w-full sm:w-auto sm:flex-1 pl-4 sm:pl-0">
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
                    {logs.length === 0 && (
                        <EmptyState
                            icon={ScrollText}
                            title="Waiting for logs"
                            hint="System activity will stream here once the bot starts running."
                        />
                    )}

                    <div className="pt-2 flex justify-center">
                        <button
                            className="btn-ghost text-xs"
                            onClick={loadMoreLogs}
                        >
                            <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />
                            Load More Logs
                        </button>
                    </div>
                </div>
            </Card>
        </div>
    );
});
