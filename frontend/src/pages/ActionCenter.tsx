import React, { useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import {
    Bell, CheckCircle2, Clock,
    AlertTriangle, ArrowRight, UserPlus,
    Calendar, Flame, TrendingUp,
    CheckCircle, MessageSquare
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";
import { toast } from "sonner";
import { cn } from "../lib/utils";
import { useAuth } from "../auth/AuthContext";

const ActionCenter: React.FC = () => {
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const [filter, setFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');

    const { data, isLoading } = useQuery({
        queryKey: ['action-center'],
        queryFn: async () => {
            const res = await api.get('/analytics/action-center');
            return res.data;
        }
    });

    const markReadMutation = useMutation({
        mutationFn: async (id: string) => {
            return await api.post(`/notifications/${id}/read`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['action-center'] });
        }
    });

    const completeTaskMutation = useMutation({
        mutationFn: async ({ taskId, leadId }: { taskId: string, leadId: string }) => {
            return await api.patch(`/leads/${leadId}/tasks/${taskId}`, { status: 'completed' });
        },
        onSuccess: () => {
            toast.success("Task marked as completed");
            queryClient.invalidateQueries({ queryKey: ['action-center'] });
        }
    });

    if (isLoading) return <Layout title="Action Center"><div className="p-8 text-center text-slate-400">Scanning for required actions...</div></Layout>;

    const actions = data?.actions || [];
    const filteredActions = filter === 'all' ? actions : actions.filter((a: any) => a.severity === filter);

    const getIcon = (type: string, severity: string) => {
        if (severity === 'high') return <AlertTriangle className="w-5 h-5 text-rose-400" />;
        switch (type) {
            case 'task': return <CheckCircle2 className="w-5 h-5 text-indigo-400" />;
            case 'lead_assignment': return <UserPlus className="w-5 h-5 text-emerald-400" />;
            case 'inactive_lead': return <Clock className="w-5 h-5 text-amber-400" />;
            case 'notification': return <Bell className="w-5 h-5 text-blue-400" />;
            default: return <Bell className="w-5 h-5 text-slate-400" />;
        }
    };

    return (
        <Layout title="Command Center">
            <div className="max-w-6xl mx-auto p-4 md:p-8 space-y-8">
                {/* Header Section */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div className="space-y-2">
                        <div className="flex items-center gap-3">
                            <h1 className="text-4xl font-black text-white italic tracking-tighter uppercase">Command Center</h1>
                            <Badge variant="outline" className="bg-indigo-500/10 border-indigo-500/20 text-indigo-400 font-black uppercase italic px-3 py-1 text-[10px] tracking-widest">
                                {data?.role || 'User'}
                            </Badge>
                        </div>
                        <p className="text-slate-500 font-medium max-w-lg">
                            {data?.counts?.total === 0
                                ? "System nominal. All tasks are up to date."
                                : `You have ${data?.counts?.total} urgent items requiring attention across your pipeline.`}
                        </p>
                    </div>

                    <div className="flex items-center gap-2 bg-slate-900/50 p-1.5 rounded-2xl border border-slate-800">
                        {['all', 'high', 'medium', 'low'].map((f) => (
                            <button
                                key={f}
                                onClick={() => setFilter(f as any)}
                                className={cn(
                                    "px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all",
                                    filter === f
                                        ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                                        : "text-slate-500 hover:text-slate-300"
                                )}
                            >
                                {f}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Priority Stats Bar */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-slate-900 border-2 border-slate-800 rounded-3xl p-6 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-4 opacity-5">
                            <AlertTriangle className="w-16 h-16" />
                        </div>
                        <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">CRITICAL</p>
                        <h3 className="text-4xl font-black text-rose-500 tabular-nums italic">{data?.counts?.high || 0}</h3>
                    </div>
                    <div className="bg-slate-900 border-2 border-slate-800 rounded-3xl p-6 relative overflow-hidden">
                        <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">WARNING</p>
                        <h3 className="text-4xl font-black text-amber-500 tabular-nums italic">{data?.counts?.medium || 0}</h3>
                    </div>
                    <div className="bg-slate-900 border-2 border-slate-800 rounded-3xl p-6 relative overflow-hidden">
                        <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">INFO</p>
                        <h3 className="text-4xl font-black text-blue-500 tabular-nums italic">{data?.counts?.low || 0}</h3>
                    </div>
                    <div className="bg-slate-900 border-2 border-indigo-500/20 rounded-3xl p-6 shadow-xl shadow-indigo-500/5">
                        <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-1">SYSTEM HEALTH</p>
                        <h3 className="text-2xl font-black text-white italic">OPERATIONAL</h3>
                    </div>
                </div>

                {/* Action Feed */}
                <div className="space-y-4">
                    {filteredActions.length === 0 ? (
                        <Card className="bg-slate-900/40 border-slate-800 border-dashed border-2 py-20">
                            <CardContent className="flex flex-col items-center justify-center text-center space-y-4">
                                <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center text-slate-600">
                                    <CheckCircle className="w-8 h-8" />
                                </div>
                                <div className="space-y-1">
                                    <h3 className="text-lg font-black text-slate-200">YOU'RE ALL CAUGHT UP</h3>
                                    <p className="text-slate-500 text-sm font-medium">No {filter !== 'all' ? filter : ''} priority actions found at this time.</p>
                                </div>
                            </CardContent>
                        </Card>
                    ) : (
                        filteredActions.map((action: any) => (
                            <div
                                key={action.id}
                                className={cn(
                                    "group bg-slate-900 border-2 rounded-3xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 transition-all hover:bg-slate-800/80",
                                    action.severity === 'high' ? "border-rose-500/20 hover:border-rose-500/40" : "border-slate-800 hover:border-slate-700"
                                )}
                            >
                                <div className="flex items-start gap-5">
                                    <div className={cn(
                                        "w-12 h-12 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110",
                                        action.severity === 'high' ? "bg-rose-500/10" :
                                            action.severity === 'medium' ? "bg-amber-500/10" : "bg-blue-500/10"
                                    )}>
                                        {getIcon(action.type, action.severity)}
                                    </div>
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <h4 className="text-lg font-black text-white tracking-tight leading-none group-hover:text-indigo-400 transition-colors">
                                                {action.title}
                                            </h4>
                                            <Badge className={cn(
                                                "text-[8px] font-black uppercase tracking-widest",
                                                action.type === 'task' ? "bg-indigo-500/20 text-indigo-400" :
                                                    action.type === 'lead_assignment' ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-800 text-slate-400"
                                            )}>
                                                {action.type.replace('_', ' ')}
                                            </Badge>
                                        </div>
                                        <p className="text-slate-400 text-sm font-medium leading-relaxed max-w-xl">
                                            {action.description}
                                        </p>
                                        <div className="flex items-center gap-4 pt-2">
                                            {action.due_date && (
                                                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-500">
                                                    <Calendar className="w-3 h-3" />
                                                    {new Date(action.due_date).toLocaleDateString()}
                                                </div>
                                            )}
                                            {action.metadata?.source && (
                                                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-600 uppercase tracking-tighter">
                                                    <Flame className="w-3 h-3 text-orange-500" />
                                                    {action.metadata.source}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 w-full md:w-auto">
                                    {action.type === 'task' && (
                                        <Button
                                            size="sm"
                                            className="bg-emerald-600 hover:bg-emerald-500 font-bold rounded-2xl px-6"
                                            onClick={() => completeTaskMutation.mutate({ taskId: action.id, leadId: action.metadata.lead_id })}
                                            disabled={completeTaskMutation.isPending}
                                        >
                                            RESOLVE
                                        </Button>
                                    )}
                                    {action.type === 'notification' && (
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="border-slate-800 text-slate-400 hover:bg-slate-800 font-bold rounded-2xl px-6"
                                            onClick={() => markReadMutation.mutate(action.id)}
                                        >
                                            DISMISS
                                        </Button>
                                    )}
                                    <Link to={action.link || '#'}>
                                        <Button
                                            variant="secondary"
                                            size="sm"
                                            className="bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-2xl px-6 flex items-center gap-2"
                                        >
                                            VIEW
                                            <ArrowRight className="w-4 h-4" />
                                        </Button>
                                    </Link>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </Layout>
    );
};

export default ActionCenter;
