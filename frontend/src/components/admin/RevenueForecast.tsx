import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, Legend } from 'recharts';
import { TrendingUp, DollarSign, Target } from 'lucide-react';

interface ForecastStage {
    stage: string;
    raw_value: number;
    weighted_value: number;
    count: number;
}

interface RevenueForecastResponse {
    stages: ForecastStage[];
    total_raw: number;
    total_weighted: number;
    currency: string;
}

const RevenueForecast: React.FC = () => {
    const { data, isLoading } = useQuery<RevenueForecastResponse>({
        queryKey: ['revenue-forecast'],
        queryFn: async () => {
            const res = await api.get('/admin/revenue-forecast');
            return res.data;
        }
    });

    if (isLoading) return <div className="h-80 bg-slate-900 animate-pulse rounded-3xl" />;

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: data?.currency || 'USD',
            maximumFractionDigits: 0
        }).format(val);
    };

    return (
        <Card className="col-span-1 lg:col-span-3 overflow-hidden border-indigo-500/20 shadow-2xl shadow-indigo-500/10">
            <CardHeader className="flex flex-row items-center justify-between bg-slate-900/50 border-b border-slate-800 px-6 py-5">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                        <Target className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <CardTitle className="text-xl font-black italic tracking-tight">Revenue Forecast</CardTitle>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Weighted pipeline projection</p>
                    </div>
                </div>
                <div className="flex items-center gap-6">
                    <div className="text-right">
                        <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest leading-none mb-1">Raw Pipeline</p>
                        <p className="text-lg font-black text-slate-300 italic">{formatCurrency(data?.total_raw || 0)}</p>
                    </div>
                    <div className="w-px h-8 bg-slate-800" />
                    <div className="text-right">
                        <p className="text-[10px] text-emerald-500 font-black uppercase tracking-widest leading-none mb-1">Expected Revenue</p>
                        <p className="text-2xl font-black text-emerald-400 italic flex items-center gap-2">
                            {formatCurrency(data?.total_weighted || 0)}
                            <TrendingUp className="w-4 h-4" />
                        </p>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-6">
                <div className="h-[350px] w-full mt-4">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                            data={data?.stages}
                            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                            <XAxis
                                dataKey="stage"
                                stroke="#64748b"
                                fontSize={10}
                                tickFormatter={(val) => val.toUpperCase()}
                                fontWeight="black"
                            />
                            <YAxis
                                stroke="#64748b"
                                fontSize={10}
                                fontWeight="black"
                                tickFormatter={(val) => `$${val / 1000}k`}
                            />
                            <Tooltip
                                cursor={{ fill: '#1e293b', opacity: 0.4 }}
                                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '16px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)' }}
                                itemStyle={{ color: '#f8fafc', fontWeight: 'bold' }}
                                labelStyle={{ color: '#6366f1', fontWeight: 'black', marginBottom: '4px', fontSize: '12px' }}
                            />
                            <Legend
                                wrapperStyle={{ paddingTop: '20px' }}
                                iconType="circle"
                            />
                            <Bar
                                name="Raw Deal Value"
                                dataKey="raw_value"
                                fill="#334155"
                                radius={[6, 6, 0, 0]}
                                barSize={40}
                            />
                            <Bar
                                name="Weighted (Expected)"
                                dataKey="weighted_value"
                                fill="url(#indigoGradient)"
                                radius={[6, 6, 0, 0]}
                                barSize={40}
                            >
                                {data?.stages.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.stage === 'won' ? '#10b981' : 'url(#indigoGradient)'} />
                                ))}
                            </Bar>
                            <defs>
                                <linearGradient id="indigoGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#6366f1" />
                                    <stop offset="100%" stopColor="#4f46e5" />
                                </linearGradient>
                            </defs>
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
                    {data?.stages.slice(-4).map((s) => (
                        <div key={s.stage} className="bg-slate-900/50 border border-slate-800 rounded-2xl p-4 group hover:border-indigo-500/40 transition-all">
                            <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mb-1">{s.stage}</p>
                            <p className="text-sm font-bold text-slate-200">{formatCurrency(s.weighted_value)}</p>
                            <div className="w-full bg-slate-800 h-1 rounded-full mt-2 overflow-hidden">
                                <div
                                    className="bg-indigo-500 h-full rounded-full transition-all duration-1000"
                                    style={{ width: `${(s.weighted_value / (data.total_weighted || 1)) * 100}%` }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
};

export default RevenueForecast;
