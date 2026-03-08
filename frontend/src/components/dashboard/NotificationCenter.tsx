import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../lib/api';
import { Bell, Check, Info, AlertTriangle, XCircle, ExternalLink } from 'lucide-react';
import { Button } from '../ui/Button';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';

interface Notification {
    id: string;
    title: string;
    message: string;
    type: string;
    link?: string;
    is_read: boolean;
    created_at: string;
}

const NotificationCenter: React.FC = () => {
    const queryClient = useQueryClient();

    const { data: notifications, isLoading } = useQuery<Notification[]>({
        queryKey: ['notifications'],
        queryFn: async () => {
            const res = await api.get('/notifications');
            return res.data;
        },
        refetchInterval: 60000, // Refetch every minute
    });

    const markReadMutation = useMutation({
        mutationFn: async (id: string) => {
            await api.post(`/notifications/${id}/read`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
        }
    });

    const markAllReadMutation = useMutation({
        mutationFn: async () => {
            await api.post('/notifications/read-all');
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
        }
    });

    const unreadCount = notifications?.filter(n => !n.is_read).length || 0;

    const getIcon = (type: string) => {
        switch (type) {
            case 'success': return <Check className="w-4 h-4 text-emerald-400" />;
            case 'warning': return <AlertTriangle className="w-4 h-4 text-amber-400" />;
            case 'error': return <XCircle className="w-4 h-4 text-red-400" />;
            default: return <Info className="w-4 h-4 text-indigo-400" />;
        }
    };

    return (
        <div className="absolute right-0 mt-2 w-96 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden z-50 animate-in fade-in slide-in-from-top-2">
            <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50 backdrop-blur-md">
                <div>
                    <h3 className="text-sm font-black text-white italic tracking-tight">NOTIFICATIONS</h3>
                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">{unreadCount} UNREAD</p>
                </div>
                {unreadCount > 0 && (
                    <button
                        onClick={() => markAllReadMutation.mutate()}
                        className="text-[10px] font-black text-indigo-400 hover:text-indigo-300 uppercase tracking-widest transition-colors"
                    >
                        Mark all read
                    </button>
                )}
            </div>

            <div className="max-h-[400px] overflow-y-auto custom-scrollbar">
                {isLoading ? (
                    <div className="p-8 text-center">
                        <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                        <p className="text-xs text-slate-500 font-bold uppercase">Syncing alerts...</p>
                    </div>
                ) : notifications?.length === 0 ? (
                    <div className="p-12 text-center">
                        <Bell className="w-8 h-8 text-slate-700 mx-auto mb-3 opacity-20" />
                        <p className="text-sm text-slate-500 font-bold font-mono">ALL CLEAR</p>
                    </div>
                ) : (
                    <div className="divide-y divide-slate-800/50">
                        {notifications?.map((n) => (
                            <div
                                key={n.id}
                                className={`p-5 transition-all hover:bg-slate-800/40 relative group ${!n.is_read ? 'bg-indigo-500/[0.02]' : ''}`}
                            >
                                {!n.is_read && (
                                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-500" />
                                )}
                                <div className="flex gap-4">
                                    <div className={`mt-1 flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center ${n.type === 'warning' ? 'bg-amber-500/10' :
                                        n.type === 'error' ? 'bg-red-500/10' :
                                            n.type === 'success' ? 'bg-emerald-500/10' : 'bg-indigo-500/10'
                                        }`}>
                                        {getIcon(n.type)}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-start justify-between gap-2 mb-1">
                                            <h4 className={`text-sm font-black ${!n.is_read ? 'text-slate-100' : 'text-slate-400'}`}>
                                                {n.title}
                                            </h4>
                                            <span className="text-[10px] text-slate-500 font-bold whitespace-nowrap">
                                                {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
                                            </span>
                                        </div>
                                        <p className="text-xs text-slate-500 leading-relaxed mb-3 font-medium">
                                            {n.message}
                                        </p>
                                        <div className="flex items-center gap-3">
                                            {n.link && (
                                                <Link
                                                    to={n.link}
                                                    onClick={() => !n.is_read && markReadMutation.mutate(n.id)}
                                                    className="inline-flex items-center gap-1.5 text-[10px] font-black text-indigo-400 hover:text-indigo-300 uppercase tracking-widest transition-colors"
                                                >
                                                    View Details
                                                    <ExternalLink className="w-3 h-3" />
                                                </Link>
                                            )}
                                            {!n.is_read && (
                                                <button
                                                    onClick={() => markReadMutation.mutate(n.id)}
                                                    className="text-[10px] font-black text-slate-400 hover:text-slate-200 uppercase tracking-widest transition-colors"
                                                >
                                                    Dismiss
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="p-4 bg-slate-900 border-t border-slate-800 text-center">
                <Link to="/notifications" className="text-[10px] font-black text-slate-500 hover:text-white uppercase tracking-[0.2em] transition-colors">
                    View All Notifications
                </Link>
            </div>
        </div>
    );
};

export default NotificationCenter;
