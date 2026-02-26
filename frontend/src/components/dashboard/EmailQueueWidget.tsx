import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import api from '../../lib/api';
import { Mail, Clock, AlertCircle, CheckCircle } from 'lucide-react';

export const EmailQueueWidget: React.FC = () => {
    const { data, isLoading } = useQuery({
        queryKey: ['email-queue-stats'],
        queryFn: async () => {
            const response = await api.get('/email-queue/stats');
            return response.data;
        },
        refetchInterval: 30000 // Refresh every 30 seconds
    });

    if (isLoading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Email Queue Status</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-center h-32">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-500"></div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    const stats = data || {};
    const hourlyPercent = (stats.sent_last_hour / stats.max_per_hour) * 100;
    const dailyPercent = (stats.sent_today / stats.max_per_day) * 100;

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Mail className="w-5 h-5" />
                    Email Queue Status
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Queue Status */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-slate-900 p-3 rounded-lg">
                        <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
                            <Clock className="w-4 h-4" />
                            Queued
                        </div>
                        <div className="text-2xl font-bold text-slate-200">{stats.queued || 0}</div>
                    </div>

                    <div className="bg-slate-900 p-3 rounded-lg">
                        <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
                            <CheckCircle className="w-4 h-4" />
                            Sent Today
                        </div>
                        <div className="text-2xl font-bold text-emerald-400">{stats.sent_today || 0}</div>
                    </div>
                </div>

                {/* Hourly Limit */}
                <div>
                    <div className="flex items-center justify-between text-sm mb-2">
                        <span className="text-slate-400">Hourly Limit</span>
                        <span className="text-slate-300">
                            {stats.sent_last_hour || 0} / {stats.max_per_hour || 50}
                        </span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2">
                        <div
                            className={`h-2 rounded-full transition-all ${hourlyPercent >= 90 ? 'bg-red-500' :
                                    hourlyPercent >= 70 ? 'bg-yellow-500' :
                                        'bg-emerald-500'
                                }`}
                            style={{ width: `${Math.min(hourlyPercent, 100)}%` }}
                        />
                    </div>
                </div>

                {/* Daily Limit */}
                <div>
                    <div className="flex items-center justify-between text-sm mb-2">
                        <span className="text-slate-400">Daily Limit</span>
                        <span className="text-slate-300">
                            {stats.sent_today || 0} / {stats.max_per_day || 300}
                        </span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2">
                        <div
                            className={`h-2 rounded-full transition-all ${dailyPercent >= 90 ? 'bg-red-500' :
                                    dailyPercent >= 70 ? 'bg-yellow-500' :
                                        'bg-emerald-500'
                                }`}
                            style={{ width: `${Math.min(dailyPercent, 100)}%` }}
                        />
                    </div>
                </div>

                {/* Failed Count */}
                {stats.failed > 0 && (
                    <div className="flex items-center gap-2 p-2 bg-red-500/10 rounded-lg">
                        <AlertCircle className="w-4 h-4 text-red-400" />
                        <span className="text-sm text-red-400">
                            {stats.failed} failed emails
                        </span>
                    </div>
                )}

                {/* Status Badge */}
                <div className="pt-2 border-t border-slate-800">
                    {stats.rate_limit_enabled ? (
                        <span className="text-xs text-slate-500">
                            Rate limiting: <span className="text-emerald-400">Active</span>
                        </span>
                    ) : (
                        <span className="text-xs text-slate-500">
                            Rate limiting: <span className="text-yellow-400">Disabled</span>
                        </span>
                    )}
                </div>
            </CardContent>
        </Card>
    );
};
