import React, { useState, useMemo } from 'react';
import Layout from '../components/layout/Layout';
import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { StatsCard } from '../components/ui/StatsCard';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import {
    Filter, Target, Award, ArrowUpRight, CheckCircle2,
    TrendingUp, Phone, Calendar as CalendarIcon, Send, Clock
} from 'lucide-react';
import CRMTargetWidget from '../components/dashboard/CRMTargetWidget';
import { format, subDays, startOfWeek, startOfMonth, startOfQuarter, parseISO } from 'date-fns';

const Performance: React.FC = () => {
    const [selectedUser, setSelectedUser] = useState<string>("");
    const [timeRange, setTimeRange] = useState<string>("month");

    // Calculate dynamic date ranges based on selection
    const dateRangeArgs = useMemo(() => {
        const now = new Date();
        let startDate: Date;

        if (timeRange === 'week') {
            startDate = startOfWeek(now, { weekStartsOn: 1 });
        } else if (timeRange === 'quarter') {
            startDate = startOfQuarter(now);
        } else {
            // Default to month
            startDate = startOfMonth(now);
        }

        return {
            start_date: startDate.toISOString(),
            end_date: now.toISOString()
        };
    }, [timeRange]);

    const { data: users } = useQuery({
        queryKey: ['users'],
        queryFn: async () => {
            const res = await api.get('/users');
            return res.data;
        }
    });

    const { data: stats, isLoading: statsLoading } = useQuery({
        queryKey: ['performance-stats', selectedUser, timeRange],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (selectedUser) params.append('user_id', selectedUser);
            params.append('start_date', dateRangeArgs.start_date);
            params.append('end_date', dateRangeArgs.end_date);

            const res = await api.get(`/analytics/performance?${params.toString()}`);
            return res.data;
        }
    });

    // Fetch Recent Wins (Leads in 'won' stage)
    const { data: recentWins, isLoading: winsLoading } = useQuery({
        queryKey: ['recent-wins', selectedUser],
        queryFn: async () => {
            const params = new URLSearchParams({ stage: 'won' });
            if (selectedUser) params.append('assigned_to_id', selectedUser);

            const res = await api.get(`/leads?${params.toString()}`);
            // The API might not sort by created_at desc by default, so we'll sort here to be safe and take top 5
            const sorted = (res.data as any[]).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
            return sorted.slice(0, 5);
        }
    });

    return (
        <Layout title="Performance Dashboard">
            <div className="p-8 space-y-8 max-w-[1600px] mx-auto min-h-screen">
                {/* ── Header & Filters ── */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-slate-800/50">
                    <div>
                        <div className="flex items-center gap-3 mb-1">
                            <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                                <Target className="w-5 h-5 text-indigo-400" />
                            </div>
                            <h2 className="text-3xl font-black text-slate-100 italic tracking-tighter uppercase">
                                Team <span className="text-indigo-400">Performance</span>
                            </h2>
                        </div>
                        <p className="text-slate-500 font-bold uppercase text-[10px] tracking-[0.2em] pl-14">
                            Real-time analytics and target tracking
                        </p>
                    </div>

                    <div className="flex items-center gap-3 bg-slate-900/60 p-1.5 rounded-xl border border-slate-800/80 shadow-sm">
                        <div className="flex items-center gap-2 px-3 border-r border-slate-800/80">
                            <Filter className="w-3.5 h-3.5 text-indigo-400" />
                            <select
                                className="bg-transparent text-xs font-bold text-slate-300 outline-none uppercase tracking-wider min-w-[140px]"
                                value={selectedUser}
                                onChange={(e) => setSelectedUser(e.target.value)}
                            >
                                <option value="">All Members</option>
                                {users?.map((u: any) => (
                                    <option key={u.user.id} value={u.user.id}>{u.user.email.split('@')[0]}</option>
                                ))}
                            </select>
                        </div>
                        <div className="flex gap-1">
                            {['week', 'month', 'quarter'].map((range) => (
                                <button
                                    key={range}
                                    onClick={() => setTimeRange(range)}
                                    className={`px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${timeRange === range
                                            ? 'bg-slate-800 text-indigo-400 shadow-sm border border-slate-700/50'
                                            : 'text-slate-500 hover:text-slate-300 border border-transparent'
                                        }`}
                                >
                                    {range}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* ── Main Grid ── */}
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">

                    {/* Left Column: Target Widget & Conversion Card */}
                    <div className="xl:col-span-1 space-y-6 flex flex-col">
                        <div className="h-[380px]">
                            <CRMTargetWidget />
                        </div>

                        {/* Conversion Victory Card */}
                        <Card className="flex-1 bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800/80 shadow-2xl overflow-hidden relative group">
                            <div className="absolute -top-10 -right-10 p-6 opacity-[0.03] group-hover:opacity-[0.05] transition-opacity duration-500 pointer-events-none">
                                <Award className="w-64 h-64 text-indigo-100" />
                            </div>

                            {/* Decorative Accent Glow */}
                            <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent opacity-50" />

                            <CardContent className="p-8 text-white relative z-10 h-full flex flex-col justify-center">
                                <div className="flex items-center gap-2 mb-4">
                                    <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                                        <ArrowUpRight className="w-4 h-4 text-emerald-400" />
                                    </div>
                                    <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-emerald-400">Conversion Rate</h3>
                                </div>

                                <div className="flex items-baseline gap-2 mb-8">
                                    <span className="text-6xl font-black italic tracking-tighter bg-gradient-to-br from-white to-slate-400 bg-clip-text text-transparent">
                                        {stats?.conversion_rate?.toFixed(1) || 0}
                                        <span className="text-4xl ml-1">%</span>
                                    </span>
                                </div>

                                <div className="grid grid-cols-2 gap-4 mt-auto">
                                    <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/50 hover:bg-slate-900/80 transition-colors">
                                        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Won Deals</p>
                                        <p className="text-2xl font-black text-emerald-400">{stats?.leads_won || 0}</p>
                                    </div>
                                    <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/50 hover:bg-slate-900/80 transition-colors">
                                        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Lost Deals</p>
                                        <p className="text-2xl font-black text-rose-400">{stats?.leads_lost || 0}</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Right Column: Scalar Stats & Recent Wins List */}
                    <div className="xl:col-span-2 flex flex-col gap-6">

                        {/* 4 Scalar Stats Grid */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 flex-shrink-0">
                            <StatsCard
                                title="Closed Won Value"
                                value={`$${stats?.revenue?.toLocaleString() || 0}`}
                                icon={<TrendingUp className="w-4 h-4 text-emerald-400" />}
                                description="Recognized revenue"
                            />
                            <StatsCard
                                title="Proposals Sent"
                                value={stats?.proposals || 0}
                                icon={<Send className="w-4 h-4 text-indigo-400" />}
                                description="Active pipeline value"
                            />
                            <StatsCard
                                title="Meetings Held"
                                value={stats?.meetings || 0}
                                icon={<CalendarIcon className="w-4 h-4 text-amber-400" />}
                                description="Qualified prospects"
                            />
                            <StatsCard
                                title="Calls Logged"
                                value={stats?.calls || 0}
                                icon={<Phone className="w-4 h-4 text-sky-400" />}
                                description="Outbound activity"
                            />
                        </div>

                        {/* Recent Wins Data Table */}
                        <Card className="flex-1 bg-slate-900/30 border border-slate-800/60 rounded-2xl flex flex-col overflow-hidden">
                            <CardHeader className="border-b border-slate-800/50 bg-slate-900/50 py-4 px-6 flex flex-row items-center justify-between">
                                <CardTitle className="text-xs font-black text-slate-200 uppercase tracking-widest flex items-center gap-2">
                                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                    Recent Wins Trophy Room
                                </CardTitle>
                                <Badge variant="success" className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 text-[9px]">
                                    {timeRange.toUpperCase()}
                                </Badge>
                            </CardHeader>
                            <CardContent className="p-0 flex flex-col flex-1 overflow-auto">
                                {winsLoading ? (
                                    <div className="p-6 space-y-4">
                                        {[1, 2, 3].map(i => <Skeleton key={i} className="h-12 w-full rounded-xl bg-slate-800/50" />)}
                                    </div>
                                ) : recentWins && recentWins.length > 0 ? (
                                    <div className="divide-y divide-slate-800/30">
                                        <div className="grid grid-cols-12 gap-4 px-6 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-950/50 sticky top-0 z-10">
                                            <div className="col-span-5">Client / Company Name</div>
                                            <div className="col-span-3">Deal Value</div>
                                            <div className="col-span-2">Source</div>
                                            <div className="col-span-2 text-right">Date Closed</div>
                                        </div>
                                        {recentWins.map((win: any) => (
                                            <div key={win.id} className="grid grid-cols-12 gap-4 px-6 py-4 items-center hover:bg-slate-800/30 transition-colors group">
                                                <div className="col-span-5 flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
                                                        <Award className="w-4 h-4 text-emerald-400" />
                                                    </div>
                                                    <span className="font-semibold text-sm text-slate-200 group-hover:text-white transition-colors truncate">
                                                        {win.company_name}
                                                    </span>
                                                </div>
                                                <div className="col-span-3">
                                                    <Badge variant="success" className="bg-transparent border border-emerald-500/30 text-emerald-400 font-mono text-xs">
                                                        ${win.deal_value?.toLocaleString() || '0'}
                                                    </Badge>
                                                </div>
                                                <div className="col-span-2">
                                                    <span className="text-xs font-medium text-slate-400 capitalize">{win.source}</span>
                                                </div>
                                                <div className="col-span-2 text-right flex items-center justify-end gap-1.5 text-slate-500">
                                                    <Clock className="w-3.5 h-3.5" />
                                                    <span className="text-xs">{format(parseISO(win.created_at), 'MMM d, yyyy')}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="flex-1 flex flex-col items-center justify-center p-12 text-center h-[300px]">
                                        <div className="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mb-4 border border-slate-700/50">
                                            <Target className="w-8 h-8 text-slate-600" />
                                        </div>
                                        <h4 className="text-sm font-bold text-slate-300 mb-1">No Recent Wins</h4>
                                        <p className="text-xs text-slate-500 max-w-xs">There are no closed won deals matching the selected criteria for this time period.</p>
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Performance;
