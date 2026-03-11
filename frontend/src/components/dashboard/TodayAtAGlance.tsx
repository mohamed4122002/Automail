import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../lib/api';
import { Card, CardContent } from '../ui/Card';
import { Calendar, CheckCircle2, Flame, ArrowRight, Clock, Star } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '../../lib/utils';

interface Meeting {
    id: string;
    lead_id: string;
    company_name: string;
    title: string;
    start_time: string;
}

interface Task {
    id: string;
    lead_id: string;
    company_name: string;
    title: string;
    due_date: string;
}

interface Lead {
    id: string;
    company_name: string;
    lead_score: number;
    stage: string;
}

const TodayAtAGlance: React.FC = () => {
    const { data: meetings } = useQuery<Meeting[]>({
        queryKey: ['my-meetings-today'],
        queryFn: async () => {
            const res = await api.get('/meetings/today'); // I will implement this endpoint next if missing, or use existing generic ones
            return res.data;
        }
    });

    const { data: tasks } = useQuery<Task[]>({
        queryKey: ['my-tasks-overdue'],
        queryFn: async () => {
            const res = await api.get('/leads/tasks/overdue');
            return res.data;
        }
    });

    const { data: hotLeads } = useQuery<Lead[]>({
        queryKey: ['my-hot-leads'],
        queryFn: async () => {
            const res = await api.get('/leads/my/hot');
            return res.data;
        }
    });

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Meetings Column */}
            <Card className="bg-indigo-950/20 border-indigo-500/20 shadow-xl overflow-hidden group">
                <div className="bg-indigo-500/10 px-6 py-4 border-b border-indigo-500/20 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-indigo-400" />
                        <h3 className="text-xs font-black text-indigo-300 uppercase tracking-widest">Meetings Today</h3>
                    </div>
                    <span className="text-xs font-black text-indigo-400 bg-indigo-500/20 px-2 py-0.5 rounded-full">{meetings?.length || 0}</span>
                </div>
                <CardContent className="p-4 space-y-3">
                    {meetings && meetings.length > 0 ? (
                        meetings.map(m => (
                            <Link key={m.id} to={`/leads/${m.lead_id}`} className="block">
                                <div className="p-3 rounded-2xl bg-indigo-500/5 border border-indigo-500/10 hover:border-indigo-500/40 transition-all flex items-center justify-between">
                                    <div>
                                        <p className="text-xs font-bold text-slate-100">{m.company_name}</p>
                                        <p className="text-[10px] text-indigo-400 font-bold uppercase">{new Date(m.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                                    </div>
                                    <Clock className="w-3.5 h-3.5 text-indigo-500" />
                                </div>
                            </Link>
                        ))
                    ) : (
                        <div className="py-8 text-center">
                            <CheckCircle2 className="w-8 h-8 text-slate-800 mx-auto mb-2" />
                            <p className="text-[10px] font-black text-slate-600 uppercase tracking-widest">Clear Schedule</p>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Overdue Tasks Column */}
            <Card className="bg-rose-950/10 border-rose-500/20 shadow-xl overflow-hidden group">
                <div className="bg-rose-500/10 px-6 py-4 border-b border-rose-500/20 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-rose-400" />
                        <h3 className="text-xs font-black text-rose-300 uppercase tracking-widest">Action Required</h3>
                    </div>
                    <span className="text-xs font-black text-rose-400 bg-rose-500/20 px-2 py-0.5 rounded-full">{tasks?.length || 0}</span>
                </div>
                <CardContent className="p-4 space-y-3">
                    {tasks && tasks.length > 0 ? (
                        tasks.slice(0, 3).map(t => (
                            <Link key={t.id} to={`/leads/${t.lead_id}`} className="block">
                                <div className="p-3 rounded-2xl bg-rose-500/5 border border-rose-500/10 hover:border-rose-500/40 transition-all">
                                    <p className="text-xs font-bold text-slate-100 truncate">{t.title}</p>
                                    <p className="text-[10px] text-rose-400 font-black uppercase tracking-tighter mt-0.5">{t.company_name}</p>
                                </div>
                            </Link>
                        ))
                    ) : (
                        <div className="py-8 text-center text-slate-600 italic text-[10px] font-bold uppercase tracking-widest">
                            No overdue tasks
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Hot Leads Column */}
            <Card className="bg-emerald-950/10 border-emerald-500/20 shadow-xl overflow-hidden group">
                <div className="bg-emerald-500/10 px-6 py-4 border-b border-emerald-500/20 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Flame className="w-4 h-4 text-emerald-400" />
                        <h3 className="text-xs font-black text-emerald-300 uppercase tracking-widest">Hot Opportunities</h3>
                    </div>
                    <div className="flex -space-x-1.5">
                        {hotLeads?.slice(0, 3).map((_, i) => (
                            <div key={i} className="w-5 h-5 rounded-full bg-emerald-500 border border-slate-950 flex items-center justify-center">
                                <Star className="w-2 h-2 text-white fill-current" />
                            </div>
                        ))}
                    </div>
                </div>
                <CardContent className="p-4 space-y-3">
                    {hotLeads && hotLeads.length > 0 ? (
                        hotLeads.slice(0, 3).map(l => (
                            <Link key={l.id} to={`/leads/${l.id}`} className="block">
                                <div className="p-3 rounded-2xl bg-emerald-500/5 border border-emerald-500/10 hover:border-emerald-500/40 transition-all flex items-center justify-between group/item">
                                    <div>
                                        <p className="text-xs font-bold text-slate-100">{l.company_name}</p>
                                        <p className="text-[10px] text-emerald-400 font-black uppercase tracking-widest">Score: {l.lead_score}</p>
                                    </div>
                                    <ArrowRight className="w-3.5 h-3.5 text-emerald-600 group-hover/item:translate-x-1 transition-all" />
                                </div>
                            </Link>
                        ))
                    ) : (
                        <div className="py-8 text-center text-slate-600 italic text-[10px] font-bold uppercase tracking-widest">
                            Nothing hot yet
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
};

export default TodayAtAGlance;
