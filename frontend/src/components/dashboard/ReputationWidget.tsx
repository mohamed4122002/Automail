import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ShieldCheck, AlertTriangle, Info, TrendingUp, TrendingDown, Mail, MousePointer, XCircle, Share2 } from 'lucide-react';
import { Card } from '../ui/Card';
import api from '../../lib/api';

interface ReputationData {
    score: number;
    status: string;
    metrics: {
        total_emails_sent: number;
        open_rate: number;
        click_rate: number;
        bounce_rate: number;
        unsubscribe_rate: number;
    };
    warnings: string[];
}

export const ReputationWidget: React.FC = () => {
    const { data, isLoading, error } = useQuery<ReputationData>({
        queryKey: ['sender-reputation'],
        queryFn: async () => {
            const response = await api.get('/analytics/reputation');
            return response.data;
        },
        refetchInterval: 60000 // Refetch every minute
    });

    if (isLoading) {
        return (
            <Card className="p-6 animate-pulse">
                <div className="h-4 w-1/3 bg-slate-700 rounded mb-4"></div>
                <div className="h-8 w-1/4 bg-slate-700 rounded mb-6"></div>
                <div className="space-y-3">
                    <div className="h-3 w-full bg-slate-700 rounded"></div>
                    <div className="h-3 w-full bg-slate-700 rounded"></div>
                </div>
            </Card>
        );
    }

    if (error || !data) {
        return (
            <Card className="p-6 border-red-500/50 bg-red-500/5">
                <div className="flex items-center gap-2 text-red-400 mb-2">
                    <XCircle className="w-5 h-5" />
                    <h3 className="font-semibold">Reputation Tool Unavailable</h3>
                </div>
                <p className="text-sm text-slate-400">Unable to load reputation data. Please check your connection.</p>
            </Card>
        );
    }

    const { score, status, metrics, warnings } = data;

    const getScoreColor = (s: number) => {
        if (s >= 85) return 'text-emerald-400';
        if (s >= 70) return 'text-yellow-400';
        if (s >= 50) return 'text-orange-400';
        return 'text-red-400';
    };

    const getScoreBg = (s: number) => {
        if (s >= 85) return 'bg-emerald-500/10 border-emerald-500/20';
        if (s >= 70) return 'bg-yellow-500/10 border-yellow-500/20';
        if (s >= 50) return 'bg-orange-500/10 border-orange-500/20';
        return 'bg-red-500/10 border-red-500/20';
    };

    return (
        <Card className="p-6 overflow-hidden relative">
            {/* Background Accent */}
            <div className={`absolute top-0 right-0 w-32 h-32 -mr-8 -mt-8 opacity-10 rounded-full blur-3xl ${getScoreBg(score).split(' ')[0]}`}></div>

            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                    <ShieldCheck className={`w-5 h-5 ${getScoreColor(score)}`} />
                    <h3 className="text-lg font-semibold text-slate-200 uppercase tracking-wider">Sender Reputation</h3>
                </div>
                <div className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest border ${getScoreBg(score)} ${getScoreColor(score)}`}>
                    {status}
                </div>
            </div>

            <div className="flex flex-col md:flex-row items-center gap-8 mb-8">
                <div className="relative">
                    {/* Simple Circular Progress - SVG */}
                    <svg className="w-32 h-32 transform -rotate-90">
                        <circle
                            cx="64"
                            cy="64"
                            r="58"
                            stroke="currentColor"
                            strokeWidth="8"
                            fill="transparent"
                            className="text-slate-800"
                        />
                        <circle
                            cx="64"
                            cy="64"
                            r="58"
                            stroke="currentColor"
                            strokeWidth="8"
                            strokeDasharray={364.4}
                            strokeDashoffset={364.4 - (364.4 * score) / 100}
                            strokeLinecap="round"
                            fill="transparent"
                            className={`${getScoreColor(score)} transition-all duration-1000 ease-out`}
                        />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className={`text-3xl font-bold ${getScoreColor(score)}`}>{score}</span>
                        <span className="text-[10px] text-slate-500 uppercase tracking-tighter">Score</span>
                    </div>
                </div>

                <div className="flex-1 grid grid-cols-2 gap-4 w-full">
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/50">
                        <div className="flex items-center gap-2 mb-1">
                            <Mail className="w-3 h-3 text-emerald-400" />
                            <span className="text-[10px] text-slate-500 uppercase font-bold">Open Rate</span>
                        </div>
                        <div className="text-lg font-bold text-slate-200">{metrics.open_rate}%</div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/50">
                        <div className="flex items-center gap-2 mb-1">
                            <Share2 className="w-3 h-3 text-blue-400" />
                            <span className="text-[10px] text-slate-500 uppercase font-bold">Unsub Rate</span>
                        </div>
                        <div className="text-lg font-bold text-slate-200">{metrics.unsubscribe_rate}%</div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/50">
                        <div className="flex items-center gap-2 mb-1">
                            <MousePointer className="w-3 h-3 text-indigo-400" />
                            <span className="text-[10px] text-slate-500 uppercase font-bold">Click Rate</span>
                        </div>
                        <div className="text-lg font-bold text-slate-200">{metrics.click_rate}%</div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/50">
                        <div className="flex items-center gap-2 mb-1">
                            <AlertTriangle className="w-3 h-3 text-red-500" />
                            <span className="text-[10px] text-slate-500 uppercase font-bold">Bounce Rate</span>
                        </div>
                        <div className="text-lg font-bold text-slate-200">{metrics.bounce_rate}%</div>
                    </div>
                </div>
            </div>

            {warnings.length > 0 && (
                <div className="space-y-2 mt-4">
                    {warnings.map((warning, idx) => (
                        <div key={idx} className="flex gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                            <AlertTriangle className="w-4 h-4 shrink-0" />
                            <span>{warning}</span>
                        </div>
                    ))}
                </div>
            )}

            <div className="mt-4 pt-4 border-t border-slate-800/50 flex items-center gap-2">
                <Info className="w-3 h-3 text-slate-500" />
                <p className="text-[10px] text-slate-500 italic">
                    Reputation is calculated based on activity from the last 30 days.
                </p>
            </div>
        </Card>
    );
};
