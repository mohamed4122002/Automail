import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { EnhancedStatCard } from '../components/ui/EnhancedStatCard';
import { DataTable } from '../components/ui/DataTable';
import api from '../lib/api';
import { toast } from 'sonner';
import {
    Users, Mail, TrendingUp, Flame, Snowflake,
    Zap, Search, Filter, UserPlus, Activity,
    Clock, Star, CheckCircle2, XCircle, List,
    LayoutGrid, BarChart3, ArrowRight, MoreHorizontal,
    User as UserIcon, Plus, X
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useGlobalWebSocket } from '../context/WebSocketContext';
import { cn } from '../lib/utils';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';

const LEAD_SOURCES = ['Marketing', 'Referral', 'Cold Outreach', 'Inbound', 'Website Form', 'Organic Search', 'Social Media', 'Conference', 'Other'];

interface Lead {
    id: string;
    company_name: string;
    source: string;
    stage: string;
    assigned_to_id?: string;
    assigned_by_id?: string;
    proposal_deadline?: string;
    deal_value?: number;
    deal_currency?: string;
    last_activity_at: string;
    lead_status: string;
    lead_score: number;
    created_at: string;
    updated_at: string;
    assigned_to_email?: string;
    assigned_to_name?: string;
    assigned_by_email?: string;
    assigned_by_name?: string;
}

interface LeadStats {
    total: number;
    by_stage: Record<string, number>;
    by_status: Record<string, number>;
}

const CRM_STAGES = [
    { id: 'lead', name: 'Lead', color: 'slate', icon: <Users className="w-5 h-5" /> },
    { id: 'call', name: 'Call', color: 'blue', icon: <Mail className="w-5 h-5" /> },
    { id: 'meeting', name: 'Meeting', color: 'indigo', icon: <Clock className="w-5 h-5" /> },
    { id: 'proposal', name: 'Proposal', color: 'violet', icon: <Zap className="w-5 h-5" /> },
    { id: 'negotiation', name: 'Negotiation', color: 'purple', icon: <TrendingUp className="w-5 h-5" /> },
    { id: 'project', name: 'Project', color: 'cyan', icon: <Activity className="w-5 h-5" /> },
    { id: 'won', name: 'Won', color: 'emerald', icon: <CheckCircle2 className="w-5 h-5" /> },
    { id: 'lost', name: 'Lost', color: 'rose', icon: <XCircle className="w-5 h-5" /> },
];

const Leads: React.FC = () => {
    const [viewMode, setViewMode] = useState<'list' | 'kanban'>(
        (localStorage.getItem('crm_view_mode') as 'list' | 'kanban') || 'kanban'
    );
    const [selectedStage, setSelectedStage] = useState<string>('all');
    const [searchTerm, setSearchTerm] = useState('');
    const [selection, setSelection] = useState<Set<string>>(new Set());
    const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' }>({ key: 'created_at', direction: 'desc' });
    const [page, setPage] = useState(1);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [createForm, setCreateForm] = useState({ company_name: '', source: 'Marketing', email: '' });
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [showBulkAssign, setShowBulkAssign] = useState(false);
    const [bulkAssigneeId, setBulkAssigneeId] = useState('');
    const pageSize = 10;

    const queryClient = useQueryClient();

    const { data: teamMembers } = useQuery<any[]>({
        queryKey: ['team-members'],
        queryFn: async () => {
            const res = await api.get('/admin/users?role=team_member');
            return res.data;
        }
    });

    const bulkAssignMutation = useMutation({
        mutationFn: async ({ leadIds, assigneeId }: { leadIds: string[]; assigneeId: string }) => {
            return Promise.all(leadIds.map(id => api.patch(`/leads/${id}`, { assigned_to_id: assigneeId })));
        },
        onSuccess: () => {
            toast.success('Leads reassigned successfully');
            setSelection(new Set());
            setShowBulkAssign(false);
            setBulkAssigneeId('');
            queryClient.invalidateQueries({ queryKey: ['leads'] });
        },
        onError: () => {
            toast.error('Failed to reassign some leads');
        }
    });

    // WebSocket for real-time sync
    useGlobalWebSocket();

    const { data: pipelineSummary, isLoading: summaryLoading } = useQuery<any>({
        queryKey: ['pipeline-summary'],
        queryFn: async () => {
            const res = await api.get('/leads/pipeline-summary');
            return res.data;
        }
    });

    // Keeping stats for backward compatibility / other parts if needed, but summary is more detailed for Kanban
    const { data: stats, isLoading: statsLoading } = useQuery<LeadStats>({
        queryKey: ['lead-stats'],
        queryFn: async () => {
            const res = await api.get('/leads/stats');
            return res.data;
        }
    });

    const { data: leadsData, isLoading: leadsLoading } = useQuery<Lead[] | Record<string, Lead[]>>({
        queryKey: ['leads', selectedStage, searchTerm, viewMode],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (selectedStage !== 'all') params.append('stage', selectedStage);
            if (searchTerm) params.append('search', searchTerm);
            if (viewMode === 'kanban') params.append('group_by', 'stage');

            const res = await api.get(`/leads?${params.toString()}`);
            return res.data;
        }
    });

    const { data: kanbanOrderData, isLoading: orderLoading } = useQuery<{ stage_order: string[] }>({
        queryKey: ['kanban-order'],
        queryFn: async () => {
            const res = await api.get('/leads/kanban-order');
            return res.data;
        }
    });

    const leads = Array.isArray(leadsData) ? leadsData : [];
    const groupedLeads = (leadsData && !Array.isArray(leadsData)) ? (leadsData as Record<string, Lead[]>) : {};

    const orderedStages = useMemo(() => {
        if (!kanbanOrderData?.stage_order) return CRM_STAGES;
        return kanbanOrderData.stage_order
            .map(id => CRM_STAGES.find(s => s.id === id))
            .filter((s): s is typeof CRM_STAGES[0] => !!s);
    }, [kanbanOrderData]);

    const updateKanbanOrderMutation = useMutation({
        mutationFn: async (stage_order: string[]) => {
            return api.put('/leads/kanban-order', { stage_order });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['kanban-order'] });
        }
    });

    const onDragEnd = (result: DropResult) => {
        const { destination, source, draggableId, type } = result;
        if (!destination) return;
        if (destination.droppableId === source.droppableId && destination.index === source.index) return;

        if (type === 'column') {
            const newOrder = Array.from(orderedStages.map(s => s.id));
            const [removed] = newOrder.splice(source.index, 1);
            newOrder.splice(destination.index, 0, removed);
            updateKanbanOrderMutation.mutate(newOrder);
            return;
        }

        // Lead card move
        const leadId = draggableId;
        const newStage = destination.droppableId;

        // Optimistic UI handled by updateLeadMutation (which we reuse)
        updateLeadMutation.mutate({ leadId, update: { stage: newStage } });
    };

    const updateLeadMutation = useMutation({
        mutationFn: async ({ leadId, update }: { leadId: string; update: any }) => {
            return api.patch(`/leads/${leadId}`, update);
        },
        onMutate: async ({ leadId, update }) => {
            const queryKey = ['leads', selectedStage, searchTerm, viewMode];
            await queryClient.cancelQueries({ queryKey });
            const previousData = queryClient.getQueryData(queryKey);

            queryClient.setQueryData(queryKey, (old: any) => {
                if (!old) return old;

                if (Array.isArray(old)) {
                    // List view
                    return old.map(lead =>
                        lead.id === leadId ? { ...lead, ...update } : lead
                    );
                } else {
                    // Kanban view (Record<string, Lead[]>)
                    const newGrouped = { ...old };
                    let leadToMove: Lead | undefined;
                    let oldStage: string | undefined;

                    // Find the lead and its current stage
                    for (const stage in newGrouped) {
                        const found = newGrouped[stage].find((l: Lead) => l.id === leadId);
                        if (found) {
                            leadToMove = { ...found, ...update };
                            oldStage = stage;
                            break;
                        }
                    }

                    if (leadToMove && oldStage) {
                        const nextStage = update.stage || oldStage;

                        // Remove from old stage
                        newGrouped[oldStage] = newGrouped[oldStage].filter((l: Lead) => l.id !== leadId);

                        // Add to next stage (at the end for now)
                        if (!newGrouped[nextStage]) newGrouped[nextStage] = [];
                        newGrouped[nextStage] = [...newGrouped[nextStage], leadToMove];
                    }

                    return newGrouped;
                }
            });
            return { previousData, queryKey };
        },
        onError: (err, variables, context) => {
            if (context?.previousData) {
                queryClient.setQueryData(context.queryKey, context.previousData);
            }
            toast.error("Failed to update lead");
        },
        onSettled: (data, error, variables, context) => {
            queryClient.invalidateQueries({ queryKey: context?.queryKey });
            queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
            queryClient.invalidateQueries({ queryKey: ['pipeline-summary'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
        }
    });

    const createLeadMutation = useMutation({
        mutationFn: async (data: typeof createForm) => {
            return api.post('/leads', {
                company_name: data.company_name,
                source: data.source,
            });
        },
        onSuccess: () => {
            setIsCreateOpen(false);
            setCreateForm({ company_name: '', source: 'Marketing', email: '' });
            setShowAdvanced(false);
            toast.success('Lead created successfully!');
            queryClient.invalidateQueries({ queryKey: ['leads'] });
            queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
        },
        onError: (error: any) => {
            const msg = error?.response?.data?.detail || 'Failed to create lead. Please check your input.';
            toast.error(msg);
        }
    });

    const columns = useMemo(() => [
        {
            key: 'company_name',
            header: 'Company',
            sortable: true,
            cell: (lead: Lead) => (
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
                        <UserIcon className="w-4 h-4 text-slate-400" />
                    </div>
                    <div>
                        <div className="font-bold text-slate-200">{lead.company_name}</div>
                        <div className="text-[10px] text-slate-500 uppercase font-black">{lead.source}</div>
                    </div>
                </div>
            )
        },
        {
            key: 'stage',
            header: 'Stage',
            sortable: true,
            cell: (lead: Lead) => {
                const stage = CRM_STAGES.find(s => s.id === lead.stage);
                return (
                    <Badge variant="outline" className={cn(
                        "font-black italic uppercase text-[10px]",
                        lead.stage === 'won' ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/5" :
                            lead.stage === 'lost' ? "text-rose-400 border-rose-500/30 bg-rose-500/5" :
                                "text-indigo-400 border-indigo-500/30 bg-indigo-500/5"
                    )}>
                        {stage?.name || lead.stage}
                    </Badge>
                );
            }
        },
        {
            key: 'lead_score',
            header: 'Score',
            sortable: true,
            cell: (lead: Lead) => (
                <div className="flex items-center gap-2">
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden w-16">
                        <div
                            className={cn(
                                "h-full rounded-full transition-all duration-1000",
                                lead.lead_score > 70 ? "bg-emerald-500" :
                                    lead.lead_score > 40 ? "bg-amber-500" : "bg-rose-500"
                            )}
                            style={{ width: `${lead.lead_score}%` }}
                        />
                    </div>
                    <span className="text-xs font-bold text-slate-400">{lead.lead_score}</span>
                </div>
            )
        },
        {
            key: 'proposal_deadline',
            header: 'Deadline',
            sortable: true,
            cell: (lead: Lead) => (
                <div className="flex flex-col">
                    {lead.proposal_deadline ? (
                        <>
                            <span className={cn(
                                "text-xs font-bold",
                                new Date(lead.proposal_deadline) < new Date() ? "text-rose-400" : "text-slate-300"
                            )}>
                                {new Date(lead.proposal_deadline).toLocaleDateString()}
                            </span>
                            <span className="text-[9px] uppercase text-slate-500 font-bold">Proposal</span>
                        </>
                    ) : (
                        <span className="text-xs text-slate-600 italic">No deadline</span>
                    )}
                </div>
            )
        },
        {
            key: 'assigned_to_name',
            header: 'Assigned To',
            sortable: true,
            cell: (lead: Lead) => (
                <div className="flex items-center gap-2">
                    {lead.assigned_to_name ? (
                        <>
                            <div className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-[10px] font-black border border-indigo-500/30">
                                {lead.assigned_to_name[0]}
                            </div>
                            <span className="text-xs font-medium text-slate-300">{lead.assigned_to_name}</span>
                        </>
                    ) : (
                        <span className="text-xs italic text-slate-500">Unassigned</span>
                    )}
                </div>
            )
        },
        {
            key: 'actions',
            header: '',
            cell: (lead: Lead) => (
                <div className="flex justify-end">
                    <Link to={`/leads/${lead.id}`}>
                        <Button variant="ghost" size="sm" className="h-8 px-3 text-[10px] font-black hover:bg-indigo-500/10 hover:text-indigo-400">
                            VIEW DETAILS
                            <ArrowRight className="w-3 h-3 ml-2" />
                        </Button>
                    </Link>
                </div>
            )
        }
    ], []);

    const filteredLeads = useMemo(() => {
        if (!leads) return [];
        return leads.slice((page - 1) * pageSize, page * pageSize);
    }, [leads, page]);

    return (
        <Layout>
            <div className="space-y-8 p-8 max-w-[1600px] mx-auto">

                {/* ── Create Lead Modal ── */}
                {isCreateOpen && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                        <div className="w-full max-w-md bg-slate-900 border-2 border-slate-800 rounded-3xl shadow-2xl">
                            <div className="flex items-center justify-between p-8 border-b border-slate-800">
                                <div>
                                    <h2 className="text-2xl font-black text-slate-100 italic uppercase tracking-tight">New Lead</h2>
                                    <p className="text-xs text-slate-500 font-bold mt-1">3 required fields · more can be added later</p>
                                </div>
                                <button onClick={() => setIsCreateOpen(false)} className="w-8 h-8 flex items-center justify-center rounded-xl bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-all">
                                    <X className="w-4 h-4" />
                                </button>
                            </div>
                            <div className="p-8 space-y-5">
                                <div>
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Company Name <span className="text-rose-500">*</span></label>
                                    <input
                                        type="text"
                                        autoFocus
                                        placeholder="e.g. Acme Corp"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-200 placeholder-slate-600 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                        value={createForm.company_name}
                                        onChange={e => setCreateForm({ ...createForm, company_name: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Source <span className="text-rose-500">*</span></label>
                                    <select
                                        className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-200 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold appearance-none"
                                        value={createForm.source}
                                        onChange={e => setCreateForm({ ...createForm, source: e.target.value })}
                                    >
                                        {LEAD_SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Contact Email <span className="text-rose-500">*</span></label>
                                    <input
                                        type="email"
                                        placeholder="contact@company.com"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-200 placeholder-slate-600 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                        value={createForm.email}
                                        onChange={e => setCreateForm({ ...createForm, email: e.target.value })}
                                    />
                                </div>

                                {/* Advanced toggle */}
                                <button onClick={() => setShowAdvanced(!showAdvanced)} className="text-[10px] font-black text-indigo-400 hover:text-indigo-300 uppercase tracking-widest flex items-center gap-1 transition-colors">
                                    {showAdvanced ? '− Hide' : '+ Show'} Advanced Fields
                                </button>
                                {showAdvanced && (
                                    <div className="space-y-4 pt-2 border-t border-slate-800">
                                        <p className="text-[10px] text-slate-600 font-bold uppercase tracking-widest">Optional — fill in later from Lead Detail</p>
                                        <div>
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Deal Value ($)</label>
                                            <input type="number" placeholder="0" className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-3 text-sm text-slate-300 focus:border-indigo-500 outline-none font-semibold" />
                                        </div>
                                    </div>
                                )}

                                <div className="flex gap-3 pt-4 border-t border-slate-800">
                                    <Button variant="secondary" className="flex-1 rounded-2xl py-4 font-black border-slate-800" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
                                    <Button
                                        className="flex-1 rounded-2xl py-4 bg-indigo-500 hover:bg-indigo-400 font-black shadow-lg shadow-indigo-500/20"
                                        isLoading={createLeadMutation.isPending}
                                        onClick={() => {
                                            if (!createForm.company_name.trim()) { toast.error('Company name is required'); return; }
                                            if (!createForm.email.trim()) { toast.error('Contact email is required'); return; }
                                            createLeadMutation.mutate(createForm);
                                        }}
                                    >
                                        <Plus className="w-4 h-4 mr-1.5" /> Create Lead
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Header Section */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-xl bg-indigo-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                                <Users className="w-6 h-6 text-white" />
                            </div>
                            <h1 className="text-4xl font-black text-slate-100 italic tracking-tighter uppercase leading-none">
                                Leads <span className="text-indigo-500">Pipeline</span>
                            </h1>
                        </div>
                        <p className="text-slate-500 text-sm font-bold uppercase tracking-widest pl-13">
                            Manage your sales opportunities in real-time
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        <Button
                            onClick={() => setIsCreateOpen(true)}
                            className="h-11 px-6 bg-indigo-500 hover:bg-indigo-400 rounded-2xl font-black text-[11px] tracking-widest uppercase shadow-lg shadow-indigo-500/20"
                        >
                            <Plus className="w-4 h-4 mr-2" /> Add Lead
                        </Button>
                        <div className="flex p-1 bg-slate-900 border border-slate-800 rounded-2xl shadow-inner shadow-black/20">
                            <button
                                onClick={() => {
                                    setViewMode('kanban');
                                    localStorage.setItem('crm_view_mode', 'kanban');
                                }}
                                className={cn(
                                    "flex items-center gap-2 px-6 py-2.5 text-[10px] font-black rounded-xl transition-all uppercase tracking-widest",
                                    viewMode === 'kanban'
                                        ? "bg-indigo-500 text-white shadow-lg shadow-indigo-500/20"
                                        : "text-slate-500 hover:text-slate-300"
                                )}
                            >
                                <LayoutGrid className="w-3.5 h-3.5" />
                                Kanban
                            </button>
                            <button
                                onClick={() => {
                                    setViewMode('list');
                                    localStorage.setItem('crm_view_mode', 'list');
                                }}
                                className={cn(
                                    "flex items-center gap-2 px-6 py-2.5 text-[10px] font-black rounded-xl transition-all uppercase tracking-widest",
                                    viewMode === 'list'
                                        ? "bg-indigo-500 text-white shadow-lg shadow-indigo-500/20"
                                        : "text-slate-500 hover:text-slate-300"
                                )}
                            >
                                <List className="w-3.5 h-3.5" />
                                List
                            </button>
                        </div>
                    </div>
                </div>

                {/* Stats Header */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {statsLoading ? (
                        Array.from({ length: 4 }).map((_, i) => (
                            <div key={i} className="h-32 bg-slate-800/20 rounded-2xl border border-slate-700/30">
                                <Skeleton className="h-full w-full rounded-2xl" />
                            </div>
                        ))
                    ) : (
                        <>
                            <EnhancedStatCard
                                title="Total Pipeline"
                                value={stats?.total || 0}
                                icon={<BarChart3 className="w-6 h-6" />}
                                variant="info"
                                tooltip="Total number of active leads in the system"
                            />
                            <EnhancedStatCard
                                title="Direct Leads"
                                value={stats?.by_stage['lead'] || 0}
                                icon={<Users className="w-6 h-6" />}
                                variant="default"
                            />
                            <EnhancedStatCard
                                title="Active Meetings"
                                value={stats?.by_stage['meeting'] || 0}
                                icon={<Clock className="w-6 h-6" />}
                                variant="warning"
                            />
                            <EnhancedStatCard
                                title="Deals Won"
                                value={stats?.by_stage['won'] || 0}
                                icon={<CheckCircle2 className="w-6 h-6" />}
                                variant="success"
                            />
                        </>
                    )}
                </div>

                {/* Filters Row */}
                <div className="flex flex-col lg:flex-row gap-6">
                    <Card className="flex-1 border-slate-800/60 bg-slate-950/40 backdrop-blur-md rounded-3xl overflow-hidden shadow-2xl">
                        <div className="p-4 flex items-center gap-4">
                            {selection.size > 0 && (
                                <div className="flex items-center gap-3 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl px-4 py-2 animate-in zoom-in-95 duration-200">
                                    <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest leading-none">
                                        {selection.size} Selected
                                    </span>
                                    <div className="h-4 w-px bg-slate-800" />
                                    <select
                                        className="bg-slate-900 border border-slate-700 text-[10px] font-bold rounded-lg px-2 py-1 outline-none text-slate-300"
                                        value={bulkAssigneeId}
                                        onChange={(e) => setBulkAssigneeId(e.target.value)}
                                    >
                                        <option value="">Select Assignee</option>
                                        {teamMembers?.map(m => (
                                            <option key={m.id} value={m.id}>{m.email}</option>
                                        ))}
                                    </select>
                                    <Button
                                        size="sm"
                                        className="h-7 px-3 text-[9px] font-black bg-indigo-500"
                                        disabled={!bulkAssigneeId || bulkAssignMutation.isPending}
                                        onClick={() => bulkAssignMutation.mutate({ leadIds: Array.from(selection), assigneeId: bulkAssigneeId })}
                                    >
                                        REASSIGN
                                    </Button>
                                    <button onClick={() => setSelection(new Set())} className="text-slate-500 hover:text-slate-300 transition-colors">
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                            )}
                            <div className="relative flex-1">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                <input
                                    type="text"
                                    placeholder="Search leads, companies..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="w-full bg-slate-900/50 border border-slate-800/60 rounded-2xl pl-12 pr-5 py-3.5 text-sm text-slate-200 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold italic tracking-tight"
                                />
                            </div>
                            <Button
                                variant="secondary"
                                className="h-12 px-6 rounded-2xl border-slate-800 font-black text-[10px] tracking-widest uppercase italic"
                                onClick={() => {
                                    setSearchTerm('');
                                    setSelectedStage('all');
                                }}
                            >
                                Reset All Filters
                            </Button>
                        </div>
                    </Card>
                </div>

                {/* View Content */}
                {leadsLoading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {Array.from({ length: 8 }).map((_, i) => (
                            <div key={i} className="h-48 bg-slate-900/20 rounded-3xl p-4 border border-slate-800/40">
                                <Skeleton className="h-6 w-3/4 mb-4" />
                                <Skeleton className="h-4 w-1/2 mb-8" />
                                <Skeleton className="h-10 w-full rounded-2xl" />
                            </div>
                        ))}
                    </div>
                ) : viewMode === 'kanban' ? (
                    <DragDropContext onDragEnd={onDragEnd}>
                        <Droppable droppableId="board" direction="horizontal" type="column">
                            {(provided) => (
                                <div
                                    {...provided.droppableProps}
                                    ref={provided.innerRef}
                                    className="flex gap-6 overflow-x-auto pb-12 snap-x scrollbar-hide"
                                >
                                    {orderedStages.map((stage, index) => {
                                        const stageLeads = groupedLeads[stage.id] || [];
                                        const summary = pipelineSummary?.stages?.find((s: any) => s.stage === stage.id);
                                        const values = summary?.deal_value_by_currency || {};

                                        return (
                                            <Draggable key={stage.id} draggableId={stage.id} index={index}>
                                                {(columnProvided) => (
                                                    <div
                                                        {...columnProvided.draggableProps}
                                                        ref={columnProvided.innerRef}
                                                        className="min-w-[340px] flex-1 snap-start first:ml-0"
                                                    >
                                                        <div className="flex items-center justify-between mb-5 px-4" {...columnProvided.dragHandleProps}>
                                                            <div className="flex items-center gap-3">
                                                                <div className={cn(
                                                                    "w-10 h-10 rounded-xl flex items-center justify-center shadow-lg",
                                                                    stage.id === 'won' ? "bg-emerald-500/20 text-emerald-400" :
                                                                        stage.id === 'lost' ? "bg-rose-500/20 text-rose-400" :
                                                                            "bg-slate-800 text-slate-400"
                                                                )}>
                                                                    {stage.icon}
                                                                </div>
                                                                <div className="flex flex-col">
                                                                    <h3 className="font-black text-slate-100 uppercase tracking-widest text-[11px] italic">
                                                                        {stage.name}
                                                                    </h3>
                                                                    <div className="flex flex-col">
                                                                        <p className="text-[10px] font-black text-slate-500 uppercase leading-none">
                                                                            {stageLeads.length} {stageLeads.length === 1 ? 'Opportunity' : 'Opportunities'}
                                                                        </p>
                                                                        {Object.entries(values).length > 0 && (
                                                                            <p className="text-[9px] font-black text-indigo-400 uppercase mt-0.5">
                                                                                {Object.entries(values).map(([cur, val]) => `${cur} ${Number(val).toLocaleString()}`).join(' · ')}
                                                                            </p>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-600 hover:text-slate-400">
                                                                <MoreHorizontal className="w-4 h-4" />
                                                            </Button>
                                                        </div>

                                                        <Droppable droppableId={stage.id} type="card">
                                                            {(cardProvided, cardSnapshot) => (
                                                                <div
                                                                    {...cardProvided.droppableProps}
                                                                    ref={cardProvided.innerRef}
                                                                    className={cn(
                                                                        "space-y-4 min-h-[600px] border-x-2 border-slate-900/40 px-3 py-1 transition-colors rounded-3xl",
                                                                        cardSnapshot.isDraggingOver ? "bg-indigo-500/5 border-indigo-500/20" : "bg-slate-950/20"
                                                                    )}
                                                                >
                                                                    {stageLeads.length === 0 ? (
                                                                        <div className="flex flex-col items-center justify-center h-48 border-2 border-dashed border-slate-800/30 rounded-3xl opacity-30">
                                                                            <Snowflake className="w-8 h-8 text-slate-600 mb-2" />
                                                                            <span className="text-[10px] font-black uppercase tracking-widest">Stage Empty</span>
                                                                        </div>
                                                                    ) : (
                                                                        stageLeads.map((lead, leadIndex) => (
                                                                            <Draggable key={lead.id} draggableId={lead.id} index={leadIndex}>
                                                                                {(leadProvided, leadSnapshot) => (
                                                                                    <div
                                                                                        ref={leadProvided.innerRef}
                                                                                        {...leadProvided.draggableProps}
                                                                                        {...leadProvided.dragHandleProps}
                                                                                        className={cn(
                                                                                            "transform transition-transform",
                                                                                            leadSnapshot.isDragging && "scale-105 rotate-1"
                                                                                        )}
                                                                                    >
                                                                                        <Card
                                                                                            className="group relative border-2 border-slate-800/60 bg-slate-900/40 hover:border-indigo-500/40 hover:bg-slate-900/60 transition-all duration-300 transform rounded-2xl overflow-hidden"
                                                                                        >
                                                                                            <div className="p-5">
                                                                                                <div className="flex items-start justify-between mb-4">
                                                                                                    <div className="flex-1 min-w-0">
                                                                                                        <h4 className="font-black text-slate-100 group-hover:text-indigo-400 transition-colors uppercase italic truncate tracking-tight text-lg mb-0.5">
                                                                                                            {lead.company_name}
                                                                                                        </h4>
                                                                                                        <div className="flex items-center gap-2">
                                                                                                            <Badge variant="neutral" className="bg-slate-800/50 text-[9px] font-black">
                                                                                                                {lead.source}
                                                                                                            </Badge>
                                                                                                            {lead.lead_score > 70 && (
                                                                                                                <Badge variant="success" className="text-[9px] font-black animate-pulse">HOT</Badge>
                                                                                                            )}
                                                                                                        </div>
                                                                                                    </div>
                                                                                                    <div className="text-right">
                                                                                                        <div className="text-[10px] font-black text-slate-500 uppercase tracking-tighter">Value</div>
                                                                                                        <div className="text-sm font-black text-indigo-400 italic">
                                                                                                            {(lead as any).deal_currency || 'USD'} {Number(lead.deal_value || 0).toLocaleString()}
                                                                                                        </div>
                                                                                                        <div className="text-[10px] font-black text-slate-500 uppercase mt-1">Score</div>
                                                                                                        <div className={cn(
                                                                                                            "text-lg font-black italic tracking-tighter leading-none",
                                                                                                            lead.lead_score > 70 ? "text-emerald-400" :
                                                                                                                lead.lead_score > 40 ? "text-amber-400" : "text-rose-400"
                                                                                                        )}>
                                                                                                            {lead.lead_score}
                                                                                                        </div>
                                                                                                    </div>
                                                                                                </div>

                                                                                                <div className="flex items-center gap-3 mt-6 pt-4 border-t border-slate-800/50">
                                                                                                    <div className="flex -space-x-1.5 flex-1">
                                                                                                        {lead.assigned_to_name ? (
                                                                                                            <div
                                                                                                                className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-[10px] font-black border-2 border-slate-900 shadow-lg"
                                                                                                                title={lead.assigned_to_name}
                                                                                                            >
                                                                                                                {lead.assigned_to_name[0]}
                                                                                                            </div>
                                                                                                        ) : (
                                                                                                            <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center text-[10px] font-black border-2 border-slate-900 text-slate-500 italic">
                                                                                                                ?
                                                                                                            </div>
                                                                                                        )}
                                                                                                    </div>
                                                                                                    <Link to={`/leads/${lead.id}`}>
                                                                                                        <Button
                                                                                                            variant="ghost"
                                                                                                            size="sm"
                                                                                                            className="h-8 px-4 text-[10px] font-black uppercase italic tracking-widest text-slate-400 group-hover:bg-indigo-500 group-hover:text-white transition-all transform group-hover:scale-105"
                                                                                                        >
                                                                                                            Details
                                                                                                        </Button>
                                                                                                    </Link>
                                                                                                </div>
                                                                                            </div>
                                                                                            <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 blur-3xl rounded-full -mr-16 -mt-16 group-hover:bg-indigo-500/10 transition-colors pointer-events-none" />
                                                                                        </Card>
                                                                                    </div>
                                                                                )}
                                                                            </Draggable>
                                                                        ))
                                                                    )}
                                                                    {cardProvided.placeholder}
                                                                </div>
                                                            )}
                                                        </Droppable>
                                                    </div>
                                                )}
                                            </Draggable>
                                        );
                                    })}
                                    {provided.placeholder}
                                </div>
                            )}
                        </Droppable>
                    </DragDropContext>
                ) : (
                    <Card className="border-2 border-slate-800/60 bg-slate-950/40 backdrop-blur-md rounded-3xl overflow-hidden shadow-2xl p-6">
                        <DataTable
                            data={filteredLeads}
                            columns={columns}
                            keyField="id"
                            selection={selection}
                            onToggleSelection={(id) => {
                                const newSelection = new Set(selection);
                                if (newSelection.has(id)) newSelection.delete(id);
                                else newSelection.add(id);
                                setSelection(newSelection);
                            }}
                            onToggleAll={(ids) => {
                                if (selection.size === ids.length) setSelection(new Set());
                                else setSelection(new Set(ids));
                            }}
                            sortConfig={sortConfig}
                            onSort={(key) => {
                                setSortConfig({
                                    key,
                                    direction: sortConfig.key === key && sortConfig.direction === 'asc' ? 'desc' : 'asc'
                                });
                            }}
                            page={page}
                            pageSize={pageSize}
                            total={leads?.length || 0}
                            onPageChange={setPage}
                            isLoading={leadsLoading}
                            emptyMessage={
                                <div className="flex flex-col items-center justify-center py-20">
                                    <div className="w-20 h-20 rounded-3xl bg-slate-800/50 flex items-center justify-center mb-6">
                                        <Users className="w-10 h-10 text-slate-600" />
                                    </div>
                                    <p className="text-lg font-black uppercase tracking-widest text-slate-500 mb-2">No leads in your pipeline yet</p>
                                    <p className="text-sm text-slate-600 mb-6">Add your first lead to start tracking opportunities</p>
                                    <Button
                                        onClick={() => setIsCreateOpen(true)}
                                        className="px-6 py-3 bg-indigo-500 hover:bg-indigo-400 rounded-2xl font-black text-sm shadow-lg shadow-indigo-500/20"
                                    >
                                        <Plus className="w-4 h-4 mr-2" /> Add Your First Lead
                                    </Button>
                                </div>
                            }
                        />
                    </Card>
                )}
            </div>
        </Layout>
    );
};

export default Leads;
