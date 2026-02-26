import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import api from '../../lib/api';
import { BarChart2, CheckCircle, TrendingUp, HelpCircle } from 'lucide-react';

export const ABTestingWidget: React.FC = () => {
    const { data: tests, isLoading } = useQuery({
        queryKey: ['active-ab-tests'],
        queryFn: async () => {
            const response = await api.get('/ab-testing/active');
            return response.data.status === 'no_active_test' ? [] : [response.data];
        },
        refetchInterval: 60000 // Refresh every minute
    });

    if (isLoading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>A/B Testing Beta</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-center h-48">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (!tests || tests.length === 0) {
        return (
            <Card className="bg-slate-900/50 border-dashed">
                <CardContent className="flex flex-col items-center justify-center py-10">
                    <HelpCircle className="w-12 h-12 text-slate-700 mb-4" />
                    <p className="text-slate-500 text-sm">No active A/B tests found.</p>
                    <p className="text-slate-600 text-xs mt-1">Start a test to optimize subject lines.</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-4">
            {tests.map((test: any) => (
                <Card key={test.id} className="border-slate-800 bg-slate-900 overflow-hidden">
                    <CardHeader className="pb-2 border-b border-slate-800/50">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                                <BarChart2 className="w-4 h-4 text-indigo-400" />
                                Subject Line A/B Test
                            </CardTitle>
                            <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase font-bold ${test.status === 'active' ? 'bg-indigo-500/10 text-indigo-400' : 'bg-emerald-500/10 text-emerald-400'
                                }`}>
                                {test.status}
                            </span>
                        </div>
                    </CardHeader>
                    <CardContent className="pt-4 space-y-6">
                        {/* Variant A */}
                        <div className="space-y-2">
                            <div className="flex justify-between items-start">
                                <div className="space-y-1">
                                    <span className="text-[10px] font-bold text-slate-500 uppercase">Variant A</span>
                                    <p className="text-sm text-slate-200 font-medium line-clamp-1">{test.subjects?.a || 'Subject A'}</p>
                                </div>
                                <div className="text-right">
                                    <span className="text-lg font-bold text-white">{test.stats.a.rate}%</span>
                                    <p className="text-[10px] text-slate-500">Open Rate</p>
                                </div>
                            </div>
                            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                <div
                                    className="bg-indigo-500 h-full transition-all duration-500"
                                    style={{ width: `${test.stats.a.rate}%` }}
                                />
                            </div>
                        </div>

                        {/* Variant B */}
                        <div className="space-y-2">
                            <div className="flex justify-between items-start">
                                <div className="space-y-1">
                                    <span className="text-[10px] font-bold text-slate-500 uppercase">Variant B</span>
                                    <p className="text-sm text-slate-200 font-medium line-clamp-1">{test.subjects?.b || 'Subject B'}</p>
                                </div>
                                <div className="text-right">
                                    <span className="text-lg font-bold text-white">{test.stats.b.rate}%</span>
                                    <p className="text-[10px] text-slate-500">Open Rate</p>
                                </div>
                            </div>
                            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                <div
                                    className="bg-emerald-500 h-full transition-all duration-500"
                                    style={{ width: `${test.stats.b.rate}%` }}
                                />
                            </div>
                        </div>

                        {/* Progress info */}
                        <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                            <div className="flex items-center gap-2 text-[11px] text-slate-500">
                                <TrendingUp className="w-3 h-3" />
                                <span>{test.total_sent} emails sent</span>
                            </div>

                            {test.winner && (
                                <div className="flex items-center gap-1 text-[11px] text-emerald-400 font-bold">
                                    <CheckCircle className="w-3 h-3" />
                                    <span>Winner: Variant {test.winner.toUpperCase()}</span>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
};
