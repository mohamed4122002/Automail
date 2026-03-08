import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Target, TrendingUp, Phone, Calendar as CalendarIcon, Send } from 'lucide-react';
import api from '../../lib/api';

const CRMTargetWidget: React.FC = () => {
    const { data: progress, isLoading } = useQuery({
        queryKey: ['crm-target-progress'],
        queryFn: async () => {
            const res = await api.get('/analytics/targets');
            return res.data;
        }
    });

    if (isLoading || !progress) return (
        <Card className="bg-slate-900/40 border-slate-800/60 animate-pulse h-full flex flex-col">
            <CardContent className="flex-1" />
        </Card>
    );

    const metrics = [
        { label: 'Revenue', key: 'revenue', icon: TrendingUp, color: 'emerald', unit: '$' },
        { label: 'Proposals', key: 'proposals', icon: Send, color: 'indigo', unit: '' },
        { label: 'Meetings', key: 'meetings', icon: CalendarIcon, color: 'amber', unit: '' },
        { label: 'Calls', key: 'calls', icon: Phone, color: 'sky', unit: '' }
    ];

    return (
        <Card className="bg-slate-900/60 border border-slate-800/80 shadow-xl overflow-hidden relative group h-full flex flex-col">
            <div className="absolute top-0 right-0 p-8 opacity-[0.02] group-hover:opacity-[0.04] transition-opacity duration-700 pointer-events-none">
                <Target className="w-48 h-48 text-indigo-200" />
            </div>

            <CardHeader className="pb-4 border-b border-slate-800/40 bg-slate-900/40">
                <div className="flex justify-between items-center">
                    <CardTitle className="text-xs font-black text-slate-300 uppercase tracking-[0.2em] flex items-center gap-2">
                        <Target className="w-4 h-4 text-indigo-400" />
                        Target Progress
                    </CardTitle>
                    <span className="text-[10px] font-black text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2 py-1 rounded-md uppercase tracking-widest shadow-[0_0_15px_rgba(99,102,241,0.1)]">
                        Overall {progress.overall_progress}%
                    </span>
                </div>
            </CardHeader>

            <CardContent className="space-y-6 pt-6 flex-1 flex flex-col justify-center relative z-10">
                {metrics.map((m) => {
                    const achieved = progress[m.key]?.achieved || 0;
                    const target = progress[m.key]?.target || 0;
                    const pct = target > 0 ? Math.min((achieved / target) * 100, 100) : 0;

                    const colorMap: Record<string, string> = {
                        emerald: 'from-emerald-500 to-emerald-400 border-emerald-400/50 shadow-[0_0_12px_rgba(16,185,129,0.3)]',
                        indigo: 'from-indigo-500 to-indigo-400 border-indigo-400/50 shadow-[0_0_12px_rgba(99,102,241,0.3)]',
                        amber: 'from-amber-500 to-amber-400 border-amber-400/50 shadow-[0_0_12px_rgba(245,158,11,0.3)]',
                        sky: 'from-sky-500 to-sky-400 border-sky-400/50 shadow-[0_0_12px_rgba(14,165,233,0.3)]'
                    };

                    const textMap: Record<string, string> = {
                        emerald: 'text-emerald-400',
                        indigo: 'text-indigo-400',
                        amber: 'text-amber-400',
                        sky: 'text-sky-400'
                    };

                    return (
                        <div key={m.label} className="space-y-2.5">
                            <div className="flex justify-between items-end">
                                <div className="flex items-center gap-2">
                                    <m.icon className={`w-3.5 h-3.5 ${textMap[m.color]}`} />
                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{m.label}</span>
                                </div>
                                <span className="text-[11px] font-black text-slate-200 tabular-nums tracking-wider">
                                    {m.unit}{achieved.toLocaleString()} <span className="text-slate-600 font-medium">/ {m.unit}{target.toLocaleString()}</span>
                                </span>
                            </div>

                            <div className="h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800/80">
                                <div
                                    className={`h-full bg-gradient-to-r ${colorMap[m.color]} transition-all duration-1000 ease-out`}
                                    style={{ width: `${pct}%` }}
                                />
                            </div>
                        </div>
                    );
                })}
            </CardContent>
        </Card>
    );
};

export default CRMTargetWidget;
