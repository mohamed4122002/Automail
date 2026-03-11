import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import TodayAtAGlance from '../components/dashboard/TodayAtAGlance';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { EnhancedStatCard } from '../components/ui/EnhancedStatCard';
import api from '../lib/api';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';
import {
    Users, Calendar, AlertTriangle, Activity, Zap, ArrowRight,
    Inbox, CheckCircle2, Clock, Star
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { cn } from '../lib/utils';

interface PersonalStats {
    my_leads_count: number;
    my_meetings_today: number;
    my_overdue_tasks: number;
    recent_activity: Array<{
        id: string;
        type: string;
        content: string;
        lead_id: string;
        created_at: string;
    }>;
}

interface Lead {
    id: string;
    company_name: string;
    source: string;
    stage: string;
    lead_score: number;
    last_activity_at: string;
    assigned_to_name?: string;
    proposal_deadline?: string;
}

const ACTIVITY_ICONS: Record<string, React.ReactNode> = {
    call: <Calendar className="w-4 h-4 text-blue-400" />,
    meeting: <Calendar className="w-4 h-4 text-indigo-400" />,
    email_sent: <Activity className="w-4 h-4 text-slate-400" />,
    note: <Activity className="w-4 h-4 text-slate-400" />,
    system: <Zap className="w-4 h-4 text-amber-400" />,
};

const MyDashboard: React.FC = () => {
    const { user } = useAuth();
    const queryClient = useQueryClient();

    const { data: stats, isLoading: statsLoading } = useQuery<PersonalStats>({
        queryKey: ['my-dashboard'],
        queryFn: async () => {
            const res = await api.get('/dashboard/me');
            return res.data;
        },
        refetchInterval: 60_000, // refresh every minute
    });

    const { data: myLeads, isLoading: leadsLoading } = useQuery<Lead[]>({
        queryKey: ['my-leads'],
        queryFn: async () => {
            const res = await api.get('/leads/my');
            return res.data;
        },
    });

    const { data: poolLeads, isLoading: poolLoading } = useQuery<Lead[]>({
        queryKey: ['lead-pool'],
        queryFn: async () => {
            const res = await api.get('/leads/pool');
            return res.data;
        },
    });

    const claimMutation = useMutation({
        mutationFn: async (leadId: string) => {
            const res = await api.post(`/leads/${leadId}/claim`);
            return res.data;
        },
        onSuccess: () => {
            toast.success('Lead claimed! It is now in your pipeline.');
            queryClient.invalidateQueries({ queryKey: ['my-leads'] });
            queryClient.invalidateQueries({ queryKey: ['lead-pool'] });
            queryClient.invalidateQueries({ queryKey: ['my-dashboard'] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || 'Could not claim this lead.');
        },
    });

    const firstName = user?.first_name || user?.email?.split('@')[0] || 'there';
    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

    return (
        <Layout>
            <div className="space-y-8 p-8 max-w-[1400px] mx-auto">

                {/* Header */}
                <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-indigo-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                            <Star className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-black text-slate-100 italic tracking-tight">
                                {greeting}, <span className="text-indigo-400">{firstName}</span>
                            </h1>
                            <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">Your personal CRM dashboard</p>
                        </div>
                    </div>
                </div>

                {/* Today at a Glance (Phase 5) */}
                <TodayAtAGlance />

                {/* Stat Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {statsLoading ? (
                        Array.from({ length: 3 }).map((_, i) => (
                            <div key={i} className="h-32 bg-slate-800/30 rounded-3xl animate-pulse" />
                        ))
                    ) : (
                        <>
                            <EnhancedStatCard
                                title="My Leads"
                                value={stats?.my_leads_count ?? 0}
                                icon={<Users className="w-6 h-6" />}
                                variant="info"
                                tooltip="Leads currently assigned to you"
                            />
                            <EnhancedStatCard
                                title="Meetings Today"
                                value={stats?.my_meetings_today ?? 0}
                                icon={<Calendar className="w-6 h-6" />}
                                variant="success"
                            />
                            <EnhancedStatCard
                                title="Overdue Tasks"
                                value={stats?.my_overdue_tasks ?? 0}
                                icon={<AlertTriangle className="w-6 h-6" />}
                                variant={(stats?.my_overdue_tasks ?? 0) > 0 ? "danger" : "default"}
                            />
                        </>
                    )}
                </div>

                {/* Deadlines Alert */}
                {myLeads?.some(l => l.proposal_deadline && new Date(l.proposal_deadline) < new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)) && (
                    <div className="bg-rose-500/10 border border-rose-500/20 rounded-3xl p-6 flex flex-col md:flex-row items-center justify-between gap-4 animate-in slide-in-from-top-4 duration-500">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-2xl bg-rose-500/20 flex items-center justify-center">
                                <Clock className="w-6 h-6 text-rose-500 animate-pulse" />
                            </div>
                            <div>
                                <h3 className="text-sm font-black text-rose-200 uppercase tracking-widest">Immediate Attention Required</h3>
                                <p className="text-xs text-rose-400/80 font-bold">You have proposal deadlines approaching this week.</p>
                            </div>
                        </div>
                        <Link to="/leads">
                            <Button className="bg-rose-500 hover:bg-rose-400 text-white font-black px-6">
                                REVIEW DEADLINES
                            </Button>
                        </Link>
                    </div>
                )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* My Leads */}
                <div className="lg:col-span-2 space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-sm font-black text-slate-300 uppercase tracking-widest">My Leads</h2>
                        <Link to="/leads/pipeline">
                            <Button variant="ghost" size="sm" className="text-[10px] font-black text-indigo-400 hover:text-indigo-300">
                                View Pipeline <ArrowRight className="w-3 h-3 ml-1" />
                            </Button>
                        </Link>
                    </div>

                    {leadsLoading ? (
                        <div className="space-y-3">
                            {Array.from({ length: 4 }).map((_, i) => (
                                <div key={i} className="h-16 bg-slate-800/30 rounded-2xl animate-pulse" />
                            ))}
                        </div>
                    ) : myLeads && myLeads.length > 0 ? (
                        <div className="space-y-3">
                            {myLeads.slice(0, 8).map(lead => (
                                <Link key={lead.id} to={`/leads/${lead.id}`}>
                                    <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800/60 hover:border-indigo-500/40 rounded-2xl px-5 py-3.5 transition-all group">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-xl bg-indigo-500/10 flex items-center justify-center">
                                                <Users className="w-4 h-4 text-indigo-400" />
                                            </div>
                                            <div>
                                                <p className="text-sm font-bold text-slate-200 group-hover:text-indigo-400 transition-colors">{lead.company_name}</p>
                                                <div className="flex items-center gap-2 mt-0.5">
                                                    <p className="text-[10px] text-slate-500 uppercase font-black tracking-wider">{lead.source} · {lead.stage}</p>
                                                    {lead.proposal_deadline && (
                                                        <>
                                                            <div className="w-1 h-1 rounded-full bg-slate-700" />
                                                            <p className={cn(
                                                                "text-[9px] font-black uppercase tracking-widest",
                                                                new Date(lead.proposal_deadline) < new Date() ? "text-rose-500" : "text-amber-500"
                                                            )}>
                                                                Deadline: {new Date(lead.proposal_deadline).toLocaleDateString()}
                                                            </p>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <div className={cn(
                                                "text-sm font-black italic",
                                                lead.lead_score > 70 ? "text-emerald-400" :
                                                    lead.lead_score > 40 ? "text-amber-400" : "text-slate-500"
                                            )}>
                                                {lead.lead_score}
                                            </div>
                                            <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-indigo-400 transition-colors" />
                                        </div>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center py-16 border-2 border-dashed border-slate-800/50 rounded-3xl">
                            <Users className="w-10 h-10 text-slate-700 mb-3" />
                            <p className="text-sm font-black text-slate-500 uppercase tracking-widest mb-1">No leads yet</p>
                            <p className="text-xs text-slate-600 mb-4">Claim leads from the pool below to get started</p>
                        </div>
                    )}
                </div>

                {/* Recent Activity + Pool Preview */}
                <div className="space-y-6">

                    {/* Recent Activity */}
                    <div className="space-y-3">
                        <h2 className="text-sm font-black text-slate-300 uppercase tracking-widest">Recent Activity</h2>
                        {stats?.recent_activity && stats.recent_activity.length > 0 ? (
                            <div className="space-y-2">
                                {stats.recent_activity.map(a => (
                                    <div key={a.id} className="flex items-start gap-3 bg-slate-900/40 border border-slate-800/40 rounded-2xl px-4 py-3">
                                        <div className="mt-0.5">
                                            {ACTIVITY_ICONS[a.type] || <Activity className="w-4 h-4 text-slate-500" />}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs text-slate-300 font-semibold truncate">{a.content}</p>
                                            <p className="text-[10px] text-slate-600 mt-0.5">
                                                {new Date(a.created_at).toLocaleDateString()}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-10 border-2 border-dashed border-slate-800/50 rounded-3xl">
                                <Clock className="w-8 h-8 text-slate-700 mb-2" />
                                <p className="text-xs font-black text-slate-600 uppercase tracking-widest">No recent activity</p>
                            </div>
                        )}
                    </div>

                    {/* Lead Pool Preview */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <h2 className="text-sm font-black text-slate-300 uppercase tracking-widest flex items-center gap-2">
                                <Inbox className="w-4 h-4 text-amber-400" />
                                Lead Pool
                            </h2>
                            {poolLeads && poolLeads.length > 0 && (
                                <Badge variant="warning" className="text-[9px] font-black animate-pulse">
                                    {poolLeads.length} available
                                </Badge>
                            )}
                        </div>

                        {poolLoading ? (
                            <div className="space-y-2">
                                {[1, 2].map(i => <div key={i} className="h-14 bg-slate-800/30 rounded-2xl animate-pulse" />)}
                            </div>
                        ) : poolLeads && poolLeads.length > 0 ? (
                            <div className="space-y-2">
                                {poolLeads.slice(0, 4).map(lead => (
                                    <div key={lead.id} className="flex items-center justify-between bg-slate-900/40 border border-amber-500/20 rounded-2xl px-4 py-3 hover:border-amber-500/50 transition-all">
                                        <div>
                                            <p className="text-xs font-bold text-slate-200">{lead.company_name}</p>
                                            <p className="text-[10px] text-slate-500 uppercase font-black">{lead.source}</p>
                                        </div>
                                        <Button
                                            size="sm"
                                            className="h-7 px-3 text-[9px] font-black bg-amber-500 hover:bg-amber-400 text-black rounded-xl"
                                            isLoading={claimMutation.isPending}
                                            onClick={() => claimMutation.mutate(lead.id)}
                                        >
                                            Claim
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-8 border-2 border-dashed border-slate-800/50 rounded-3xl">
                                <CheckCircle2 className="w-7 h-7 text-emerald-600 mb-2" />
                                <p className="text-xs font-black text-slate-600 uppercase tracking-widest">Pool is empty</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default MyDashboard;
