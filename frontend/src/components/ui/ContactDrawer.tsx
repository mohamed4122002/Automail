import React from 'react';
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetDescription
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/Badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
    User,
    Mail,
    Clock,
    MousePointerClick,
    Eye,
    AlertCircle,
    CheckCircle2,
    Calendar,
    Activity
} from "lucide-react";
import { format } from 'date-fns';

interface RecipientDetail {
    user_id: string;
    email: string;
    name?: string;
    status: string;
    engagement_score: number;
    sent_at?: string;
    opened_at?: string;
    clicked_at?: string;
    total_opens: number;
    total_clicks: number;
    events: Array<{
        type: string;
        timestamp: string;
        metadata: any;
    }>;
}

interface ContactDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    recipient: RecipientDetail | null;
    loading: boolean;
}

export function ContactDrawer({ isOpen, onClose, recipient, loading }: ContactDrawerProps) {
    if (!recipient && !loading) return null;

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'opened': return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
            case 'clicked': return 'text-indigo-400 bg-indigo-400/10 border-indigo-400/20';
            case 'bounced': return 'text-red-400 bg-red-400/10 border-red-400/20';
            case 'sent': return 'text-blue-400 bg-blue-400/10 border-blue-400/20';
            default: return 'text-slate-400 bg-slate-400/10 border-slate-400/20';
        }
    };

    const getEventIcon = (type: string) => {
        switch (type) {
            case 'sent': return <Mail className="w-4 h-4 text-blue-400" />;
            case 'opened': return <Eye className="w-4 h-4 text-emerald-400" />;
            case 'clicked': return <MousePointerClick className="w-4 h-4 text-indigo-400" />;
            case 'bounced': return <AlertCircle className="w-4 h-4 text-red-400" />;
            default: return <Activity className="w-4 h-4 text-slate-400" />;
        }
    };

    return (
        <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <SheetContent className="w-[400px] sm:w-[540px] border-l border-slate-700 bg-slate-900 text-slate-100 p-0 overflow-hidden flex flex-col">
                {loading ? (
                    <div className="flex-1 flex items-center justify-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500"></div>
                    </div>
                ) : recipient ? (
                    <>
                        <SheetHeader className="p-6 border-b border-slate-700/50 bg-slate-800/20">
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400 text-xl font-bold">
                                        {recipient.name ? recipient.name[0].toUpperCase() : recipient.email[0].toUpperCase()}
                                    </div>
                                    <div>
                                        <SheetTitle className="text-xl font-bold text-white">
                                            {recipient.name || "Unknown Name"}
                                        </SheetTitle>
                                        <SheetDescription className="text-slate-400 flex items-center gap-2 mt-1">
                                            <Mail className="w-3 h-3" /> {recipient.email}
                                        </SheetDescription>
                                    </div>
                                </div>
                                <Badge variant="outline" className={getStatusColor(recipient.status)}>
                                    {recipient.status.toUpperCase()}
                                </Badge>
                            </div>
                        </SheetHeader>

                        <ScrollArea className="flex-1">
                            <div className="p-6 space-y-8">
                                {/* Engagement Score */}
                                <div className="space-y-3">
                                    <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Engagement Score</h3>
                                    <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="text-2xl font-bold text-white">{recipient.engagement_score}/100</span>
                                            <Activity className="w-5 h-5 text-indigo-400" />
                                        </div>
                                        <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500"
                                                style={{ width: `${recipient.engagement_score}%` }}
                                            ></div>
                                        </div>
                                    </div>
                                </div>

                                {/* Stats Grid */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-slate-800/30 p-4 rounded-lg border border-slate-700/30">
                                        <div className="flex items-center gap-2 text-slate-400 mb-1">
                                            <Eye className="w-4 h-4" />
                                            <span className="text-xs font-medium">Total Opens</span>
                                        </div>
                                        <span className="text-xl font-semibold text-white">{recipient.total_opens}</span>
                                    </div>
                                    <div className="bg-slate-800/30 p-4 rounded-lg border border-slate-700/30">
                                        <div className="flex items-center gap-2 text-slate-400 mb-1">
                                            <MousePointerClick className="w-4 h-4" />
                                            <span className="text-xs font-medium">Total Clicks</span>
                                        </div>
                                        <span className="text-xl font-semibold text-white">{recipient.total_clicks}</span>
                                    </div>
                                </div>

                                {/* Activity Timeline */}
                                <div className="space-y-4">
                                    <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider flex items-center gap-2">
                                        <Clock className="w-4 h-4" /> Activity Timeline
                                    </h3>
                                    <div className="space-y-0 relative border-l border-slate-700 ml-2">
                                        {recipient.events?.map((event, idx) => (
                                            <div key={idx} className="relative pl-6 pb-6 last:pb-0">
                                                <div className="absolute -left-2 top-0 bg-slate-900 p-1 rounded-full border border-slate-700">
                                                    {getEventIcon(event.type)}
                                                </div>
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-medium text-slate-200 capitalize">
                                                        {event.type.replace('_', ' ')}
                                                    </span>
                                                    <span className="text-xs text-slate-500">
                                                        {format(new Date(event.timestamp), "MMM d, yyyy 'at' h:mm a")}
                                                    </span>
                                                    {event.metadata && Object.keys(event.metadata).length > 0 && (
                                                        <div className="mt-2 text-xs bg-slate-800/50 p-2 rounded border border-slate-700/50 text-slate-400 font-mono">
                                                            {/* Simplify metadata display */}
                                                            {event.metadata.url && (
                                                                <div className="truncate max-w-[200px]" title={event.metadata.url}>
                                                                    URL: {event.metadata.url}
                                                                </div>
                                                            )}
                                                            {event.metadata.reason && <div>Reason: {event.metadata.reason}</div>}
                                                            {event.metadata.browser && <div>Browser: {event.metadata.browser}</div>}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                        {(!recipient.events || recipient.events.length === 0) && (
                                            <div className="pl-6 text-sm text-slate-500 italic">No activity recorded yet</div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </ScrollArea>
                    </>
                ) : null}
            </SheetContent>
        </Sheet>
    );
}
