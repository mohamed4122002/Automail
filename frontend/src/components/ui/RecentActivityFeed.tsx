import React from 'react';
import {
    Mail,
    MousePointerClick,
    AlertTriangle,
    UserX,
    Clock,
    Send
} from 'lucide-react';
import classNames from 'classnames';

interface ActivityEvent {
    id: string;
    type: 'sent' | 'opened' | 'clicked' | 'bounced' | 'unsubscribed' | 'campaign_activated' | 'campaign_paused' | 'campaign_completed' | 'WORKFLOW_NODE_ENTER';
    email: string;
    user_email?: string; // Support for websocket data
    timestamp: string;
    metadata?: {
        subject?: string;
        url?: string;
        reason?: string;
    };
}

interface RecentActivityFeedProps {
    events: ActivityEvent[];
    maxItems?: number;
}

export const RecentActivityFeed: React.FC<RecentActivityFeedProps> = ({
    events,
    maxItems = 10
}) => {
    const getIcon = (type: string) => {
        switch (type) {
            case 'sent':
                return <Send className="w-4 h-4" />;
            case 'opened':
                return <Mail className="w-4 h-4" />;
            case 'clicked':
                return <MousePointerClick className="w-4 h-4" />;
            case 'bounced':
                return <AlertTriangle className="w-4 h-4" />;
            case 'unsubscribed':
                return <UserX className="w-4 h-4" />;
            case 'campaign_activated':
                return <Send className="w-4 h-4 text-emerald-400" />;
            case 'campaign_paused':
                return <AlertTriangle className="w-4 h-4 text-orange-400" />;
            case 'WORKFLOW_NODE_ENTER':
                return <Clock className="w-4 h-4 text-slate-400" />;
            default:
                return <Mail className="w-4 h-4" />;
        }
    };

    const getColor = (type: string) => {
        switch (type) {
            case 'sent':
                return {
                    bg: 'bg-indigo-500/10',
                    text: 'text-indigo-400',
                    border: 'border-indigo-500/30'
                };
            case 'opened':
                return {
                    bg: 'bg-emerald-500/10',
                    text: 'text-emerald-400',
                    border: 'border-emerald-500/30'
                };
            case 'clicked':
                return {
                    bg: 'bg-blue-500/10',
                    text: 'text-blue-400',
                    border: 'border-blue-500/30'
                };
            case 'bounced':
                return {
                    bg: 'bg-red-500/10',
                    text: 'text-red-400',
                    border: 'border-red-500/30'
                };
            case 'unsubscribed':
                return {
                    bg: 'bg-amber-500/10',
                    text: 'text-amber-400',
                    border: 'border-amber-500/30'
                };
            case 'campaign_activated':
                return {
                    bg: 'bg-emerald-500/10',
                    text: 'text-emerald-400',
                    border: 'border-emerald-500/30'
                };
            case 'campaign_paused':
                return {
                    bg: 'bg-orange-500/10',
                    text: 'text-orange-400',
                    border: 'border-orange-500/30'
                };
            default:
                return {
                    bg: 'bg-slate-500/10',
                    text: 'text-slate-400',
                    border: 'border-slate-500/30'
                };
        }
    };

    const getLabel = (type: string) => {
        switch (type) {
            case 'sent':
                return 'Email Sent';
            case 'opened':
                return 'Email Opened';
            case 'clicked':
                return 'Link Clicked';
            case 'bounced':
                return 'Email Bounced';
            case 'unsubscribed':
                return 'Unsubscribed';
            case 'campaign_activated':
                return 'Campaign Activated';
            case 'campaign_paused':
                return 'Campaign Paused';
            case 'campaign_completed':
                return 'Campaign Completed';
            case 'WORKFLOW_NODE_ENTER':
                return 'Workflow Advancement';
            default:
                return 'Activity';
        }
    };

    const formatTime = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;

        return date.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    };

    const displayEvents = events.slice(0, maxItems);

    return (
        <div className="bg-gradient-to-br from-slate-800/40 to-slate-900/40 p-6 rounded-xl border border-slate-700/30 backdrop-blur-sm shadow-lg">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-slate-700/50">
                        <Clock className="w-5 h-5 text-slate-400" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-slate-100">
                            Recent Activity
                        </h3>
                        <p className="text-sm text-slate-400">
                            Last {displayEvents.length} events
                        </p>
                    </div>
                </div>
            </div>

            {/* Activity List */}
            <div className="space-y-3 max-h-[400px] overflow-y-auto custom-scrollbar">
                {displayEvents.length > 0 ? (
                    displayEvents.map((event) => {
                        const colors = getColor(event.type);

                        return (
                            <div
                                key={event.id}
                                className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/30 border border-slate-700/30 hover:bg-slate-800/50 transition-all"
                            >
                                {/* Icon */}
                                <div className={classNames(
                                    "flex-shrink-0 p-2 rounded-lg border",
                                    colors.bg,
                                    colors.text,
                                    colors.border
                                )}>
                                    {getIcon(event.type)}
                                </div>

                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-start justify-between gap-2 mb-1">
                                        <p className="text-sm font-medium text-slate-200">
                                            {getLabel(event.type)}
                                        </p>
                                        <span className="text-xs text-slate-500 whitespace-nowrap">
                                            {formatTime(event.timestamp)}
                                        </span>
                                    </div>

                                    {(event.email || event.user_email) && (
                                        <p className="text-sm text-slate-400 truncate">
                                            {event.email || event.user_email}
                                        </p>
                                    )}

                                    {/* Metadata */}
                                    {event.metadata && (
                                        <div className="mt-1">
                                            {event.metadata.subject && (
                                                <p className="text-xs text-slate-500 truncate">
                                                    Subject: {event.metadata.subject}
                                                </p>
                                            )}
                                            {event.metadata.url && (
                                                <p className="text-xs text-blue-400 truncate">
                                                    {event.metadata.url}
                                                </p>
                                            )}
                                            {event.metadata.reason && (
                                                <p className="text-xs text-red-400">
                                                    Reason: {event.metadata.reason}
                                                </p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })
                ) : (
                    <div className="text-center py-12 text-slate-500">
                        <Clock className="w-12 h-12 mx-auto mb-3 opacity-30" />
                        <p className="text-sm">No recent activity</p>
                        <p className="text-xs mt-1">Activity will appear here once the campaign starts</p>
                    </div>
                )}
            </div>

            {/* View All Link */}
            {events.length > maxItems && (
                <div className="mt-4 pt-4 border-t border-slate-700/50 text-center">
                    <button className="text-sm text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                        View all {events.length} events →
                    </button>
                </div>
            )}
        </div>
    );
};

export default RecentActivityFeed;
