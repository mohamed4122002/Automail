import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useDebounce } from '../hooks/useDebounce';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { EnhancedStatCard } from '../components/ui/EnhancedStatCard';
import { DataTable } from '../components/ui/DataTable';
import api from '../lib/api';
import {
    Users, TrendingUp, CheckCircle2, BarChart3,
    Search, ArrowRight, User as UserIcon, UserPlus, LayoutGrid, List as ListIcon
} from 'lucide-react';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';
import { useGlobalWebSocket } from '../context/WebSocketContext';
import { cn } from '../lib/utils';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import { AddLeadModal } from '../components/modals/AddLeadModal';
import { useAuth } from '../auth/AuthContext';

interface Lead {
    id: string;
    company_name: string;
    source: string;
    stage: string;
    lead_score: number;
    assigned_to_id?: string | null;
    lead_status: string;
    deal_value?: number;
    deal_currency?: 'USD' | 'EGP' | 'EUR' | string;
    assigned_to_name?: string;
    assigned_to_email?: string;
    created_at: string;
}

interface LeadStats {
    total: number;
    by_stage: Record<string, number>;
    by_status: Record<string, number>;
}

const STAGE_LABELS: Record<string, string> = {
    lead: 'Lead', call: 'Call', meeting: 'Meeting',
    proposal: 'Proposal', negotiation: 'Negotiation',
    project: 'Project', won: 'Won', lost: 'Lost',
};

const STAGES_ORDER_DEFAULT = Object.keys(STAGE_LABELS);

function formatMoney(amount: number, currency: string) {
    const normalized = (currency || 'USD').toUpperCase();
    try {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: normalized,
            maximumFractionDigits: 0,
        }).format(amount);
    } catch {
        // Fallback if currency code isn't supported by Intl on the client
        return `${normalized} ${Math.round(amount).toLocaleString('en-US')}`;
    }
}

const LeadsList: React.FC = () => {
    const [viewMode, setViewMode] = useState<'table' | 'kanban'>(() => {
        const saved = localStorage.getItem('leads_view_mode');
        return saved === 'kanban' ? 'kanban' : 'table';
    });
    const [searchTerm, setSearchTerm] = useState('');
    const debouncedSearch = useDebounce(searchTerm, 300);
    const [stageFilter, setStageFilter] = useState('all');
    const [selection, setSelection] = useState<Set<string>>(new Set());
    const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' }>({ key: 'created_at', direction: 'desc' });
    const [page, setPage] = useState(1);
    const pageSize = 15;
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const { user, token } = useAuth();
    const isManager = ['super_admin', 'admin', 'manager'].includes(user?.role || '');

    const queryClient = useQueryClient();

    useEffect(() => {
        localStorage.setItem('leads_view_mode', viewMode);
    }, [viewMode]);

    useGlobalWebSocket();

    const { data: stats, isLoading: statsLoading } = useQuery<LeadStats>({
        queryKey: ['lead-stats'],
        queryFn: async () => (await api.get('/leads/stats')).data
    });

    const { data: pipelineSummary } = useQuery<any>({
        queryKey: ['pipeline-summary'],
        queryFn: async () => (await api.get('/leads/pipeline-summary')).data,
        enabled: viewMode === 'kanban'
    });

    const { data: kanbanOrder, isLoading: kanbanOrderLoading } = useQuery<{ stage_order: string[] }>({
        queryKey: ['kanban-order'],
        queryFn: async () => (await api.get('/leads/kanban-order')).data,
        enabled: viewMode === 'kanban',
    });

    const saveKanbanOrder = useMutation({
        mutationFn: async (stage_order: string[]) => (await api.put('/leads/kanban-order', { stage_order })).data,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['kanban-order'] });
        }
    });

    // use debounced search value for the query to avoid spamming the API
    const { data: leads, isLoading: leadsLoading } = useQuery<Lead[]>({
        queryKey: ['leads', stageFilter, debouncedSearch],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (stageFilter !== 'all') params.append('stage', stageFilter);
            if (debouncedSearch) params.append('search', debouncedSearch);
            return (await api.get(`/leads?${params}`)).data;
        }
    });

    const { data: leadsByStage, isLoading: groupedLoading } = useQuery<Record<string, Lead[]>>({
        queryKey: ['leads-grouped', debouncedSearch],
        queryFn: async () => {
            const params = new URLSearchParams();
            params.append('group_by', 'stage');
            if (debouncedSearch) params.append('search', debouncedSearch);
            return (await api.get(`/leads?${params}`)).data;
        },
        enabled: viewMode === 'kanban',
    });

    const patchStage = useMutation({
        mutationFn: async ({ leadId, stage }: { leadId: string; stage: string }) => (await api.patch(`/leads/${leadId}/stage`, { stage })).data,
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ['leads-grouped'] });
            queryClient.invalidateQueries({ queryKey: ['leads'] });
            queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
            queryClient.invalidateQueries({ queryKey: ['pipeline-summary'] });
        }
    });

    const { data: assignableUsers } = useQuery<any[]>({
        queryKey: ['users-assignable'],
        queryFn: async () => (await api.get('/admin/users')).data,
        enabled: isManager,
    });

    const assignLead = useMutation({
        mutationFn: async ({ leadId, userId }: { leadId: string; userId: string | null }) => {
            return (await api.patch(`/leads/${leadId}`, { assigned_to_id: userId })).data;
        },
        onSuccess: () => {
            toast.success('Lead assignment updated');
            queryClient.invalidateQueries({ queryKey: ['leads'] });
            queryClient.invalidateQueries({ queryKey: ['leads-grouped'] });
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to assign lead');
        }
    });

    const stages = Object.entries(STAGE_LABELS);

    const stageOrder = useMemo(() => {
        const order = kanbanOrder?.stage_order?.length ? kanbanOrder.stage_order : STAGES_ORDER_DEFAULT;
        // Only keep known stages + ensure all defaults exist
        const deduped: string[] = [];
        for (const s of order) if (STAGE_LABELS[s] && !deduped.includes(s)) deduped.push(s);
        for (const s of STAGES_ORDER_DEFAULT) if (!deduped.includes(s)) deduped.push(s);
        return deduped;
    }, [kanbanOrder?.stage_order]);

    const columns = useMemo(() => [
        {
            key: 'company_name',
            header: 'Company',
            sortable: true,
            cell: (lead: Lead) => (
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center flex-shrink-0">
                        <UserIcon className="w-4 h-4 text-slate-400" />
                    </div>
                    <div className="min-w-0">
                        <div className="font-bold text-slate-200 truncate">{lead.company_name}</div>
                        <div className="text-[10px] text-slate-500 uppercase font-black">{lead.source}</div>
                    </div>
                </div>
            ),
        },
        {
            key: 'stage',
            header: 'Stage',
            sortable: true,
            cell: (lead: Lead) => (
                <Badge variant="outline" className={cn(
                    "font-black italic uppercase text-[10px] whitespace-nowrap",
                    lead.stage === 'won' ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/5" :
                        lead.stage === 'lost' ? "text-rose-400 border-rose-500/30 bg-rose-500/5" :
                            "text-indigo-400 border-indigo-500/30 bg-indigo-500/5"
                )}>
                    {STAGE_LABELS[lead.stage] || lead.stage}
                </Badge>
            ),
        },
        {
            key: 'lead_score',
            header: 'Score',
            sortable: true,
            cell: (lead: Lead) => (
                <div className="flex items-center gap-2 w-28">
                    <div className="flex-1 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div
                            className={cn(
                                "h-full rounded-full transition-all duration-700",
                                lead.lead_score > 70 ? "bg-emerald-500" :
                                    lead.lead_score > 40 ? "bg-amber-500" : "bg-rose-500"
                            )}
                            style={{ width: `${lead.lead_score}%` }}
                        />
                    </div>
                    <span className="text-xs font-bold text-slate-400 w-6 text-right">{lead.lead_score}</span>
                </div>
            ),
        },
        {
            key: 'deal_value',
            header: 'Deal Value',
            sortable: true,
            cell: (lead: Lead) => (
                <span className="text-sm font-black text-slate-300 italic">
                    {lead.deal_value
                        ? `$${lead.deal_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
                        : <span className="text-slate-600 text-xs font-bold">—</span>}
                </span>
            ),
        },
        {
            key: 'assigned_to_name',
            header: 'Assigned To',
            sortable: true,
            cell: (lead: Lead) => (
                <div className="flex items-center gap-2">
                    {isManager ? (
                        <select
                            className="bg-slate-900 border border-slate-800 text-[10px] font-bold rounded-lg px-2 py-1 outline-none focus:border-indigo-500/50 transition-colors shadow-inner w-32 text-slate-300"
                            value={lead.assigned_to_id || ""}
                            onChange={(e) => assignLead.mutate({ leadId: lead.id, userId: e.target.value || null })}
                            onClick={(e) => e.stopPropagation()}
                        >
                            <option value="">(Unassigned)</option>
                            {assignableUsers?.map((u) => (
                                <option key={u.id} value={u.id}>
                                    {u.first_name ? `${u.first_name} ${u.last_name || ''}` : u.email}
                                </option>
                            ))}
                        </select>
                    ) : lead.assigned_to_name ? (
                        <>
                            <div className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-[10px] font-black border border-indigo-500/30 flex-shrink-0">
                                {lead.assigned_to_name[0]}
                            </div>
                            <span className="text-xs font-medium text-slate-300 truncate">{lead.assigned_to_name}</span>
                        </>
                    ) : (
                        <span className="text-xs italic text-slate-600">Unassigned</span>
                    )}
                </div>
            ),
        },
        {
            key: 'actions',
            header: '',
            cell: (lead: Lead) => (
                <div className="flex justify-end">
                    <Link to={`/leads/${lead.id}`}>
                        <Button variant="ghost" size="sm"
                            className="h-8 px-3 text-[10px] font-black hover:bg-indigo-500/10 hover:text-indigo-400 whitespace-nowrap">
                            OPEN
                            <ArrowRight className="w-3 h-3 ml-1.5" />
                        </Button>
                    </Link>
                </div>
            ),
        },
    ], []);

    const pagedLeads = useMemo(() => {
        if (!leads) return [];
        return leads.slice((page - 1) * pageSize, page * pageSize);
    }, [leads, page]);

    const onDragEnd = (result: DropResult) => {
        const { destination, source, draggableId, type } = result;
        if (!destination) return;

        // Column reorder
        if (type === 'COLUMN') {
            if (destination.index === source.index) return;
            const next = Array.from(stageOrder);
            const [moved] = next.splice(source.index, 1);
            next.splice(destination.index, 0, moved);
            queryClient.setQueryData(['kanban-order'], { stage_order: next });
            saveKanbanOrder.mutate(next);
            return;
        }

        // Card move
        if (destination.droppableId === source.droppableId && destination.index === source.index) return;
        const fromStage = source.droppableId;
        const toStage = destination.droppableId;

        const prev = queryClient.getQueryData<Record<string, Lead[]>>(['leads-grouped', searchTerm]);
        if (prev) {
            const next: Record<string, Lead[]> = { ...prev };
            const fromArr = Array.from(next[fromStage] || []);
            const toArr = Array.from(next[toStage] || []);
            const movedIdx = fromArr.findIndex(l => String(l.id) === String(draggableId));
            if (movedIdx !== -1) {
                const [moved] = fromArr.splice(movedIdx, 1);
                const movedUpdated = { ...moved, stage: toStage };
                toArr.splice(destination.index, 0, movedUpdated);
                next[fromStage] = fromArr;
                next[toStage] = toArr;
                queryClient.setQueryData(['leads-grouped', searchTerm], next);
            }
        }

        patchStage.mutate({ leadId: draggableId, stage: toStage });
    };

    return (
        <Layout>
            <div className="flex flex-col gap-6 p-8 max-w-[1400px] mx-auto">

                {/* ── Header ── */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div>
                        <div className="flex items-center gap-3 mb-1">
                            <div className="w-9 h-9 rounded-xl bg-indigo-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                                <Users className="w-5 h-5 text-white" />
                            </div>
                            <h1 className="text-3xl font-black text-slate-100 italic tracking-tighter uppercase">
                                Leads <span className="text-indigo-500">Directory</span>
                            </h1>
                        </div>
                        <p className="text-slate-500 text-xs font-bold uppercase tracking-widest pl-12">
                            Searchable, sortable and filterable leads table
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        {isManager && (
                            <Button
                                onClick={() => setIsAddModalOpen(true)}
                                className="bg-indigo-500 hover:bg-indigo-600 text-white shadow-lg shadow-indigo-500/20 px-6 h-11 flex items-center gap-2 font-black italic tracking-tighter uppercase text-xs"
                            >
                                <UserPlus className="w-4 h-4" />
                                Add Lead
                            </Button>
                        )}
                    </div>

                    {/* View toggle */}
                    <div className="flex p-1 bg-slate-900 border border-slate-800 rounded-2xl shadow-inner shadow-black/20 w-fit">
                        <button
                            onClick={() => setViewMode('kanban')}
                            className={cn(
                                "flex items-center gap-2 px-5 py-2 text-[10px] font-black rounded-xl transition-all uppercase tracking-widest",
                                viewMode === 'kanban' ? "bg-indigo-500 text-white shadow-lg shadow-indigo-500/20" : "text-slate-500 hover:text-slate-300"
                            )}
                        >
                            <LayoutGrid className="w-3.5 h-3.5" />
                            Kanban
                        </button>
                        <button
                            onClick={() => setViewMode('table')}
                            className={cn(
                                "flex items-center gap-2 px-5 py-2 text-[10px] font-black rounded-xl transition-all uppercase tracking-widest",
                                viewMode === 'table' ? "bg-indigo-500 text-white shadow-lg shadow-indigo-500/20" : "text-slate-500 hover:text-slate-300"
                            )}
                        >
                            <ListIcon className="w-3.5 h-3.5" />
                            Table
                        </button>
                    </div>
                </div>

                {/* ── Stats Strip ── */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {statsLoading ? (
                        Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-2xl" />)
                    ) : (
                        <>
                            <EnhancedStatCard title="Total Leads" value={stats?.total || 0} icon={<BarChart3 className="w-5 h-5" />} variant="info" />
                            <EnhancedStatCard title="Hot Leads" value={stats?.by_status?.['hot'] || 0} icon={<TrendingUp className="w-5 h-5" />} variant="warning" />
                            <EnhancedStatCard title="In Proposal" value={stats?.by_stage['proposal'] || 0} icon={<UserPlus className="w-5 h-5" />} variant="default" />
                            <EnhancedStatCard title="Deals Won" value={stats?.by_stage['won'] || 0} icon={<CheckCircle2 className="w-5 h-5" />} variant="success" />
                        </>
                    )}
                </div>

                {/* ── Filters ── */}
                <Card className="border-slate-800/60 bg-slate-950/40 backdrop-blur-md rounded-2xl overflow-hidden">
                    <div className="px-5 py-4 flex flex-col sm:flex-row gap-4 items-start sm:items-center">
                        {/* Search */}
                        <div className="relative flex-1 min-w-0">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                placeholder="Search by company name..."
                                value={searchTerm}
                                onChange={e => { setSearchTerm(e.target.value); setPage(1); }}
                                className="w-full bg-slate-900/50 border border-slate-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-slate-200 focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 outline-none transition-all font-medium"
                            />
                        </div>

                        {/* Stage filter pills */}
                        <div className="flex items-center gap-1.5 flex-wrap">
                            <button
                                onClick={() => { setStageFilter('all'); setPage(1); }}
                                className={cn(
                                    "px-3 py-1.5 text-[10px] font-black rounded-lg uppercase tracking-widest transition-all",
                                    stageFilter === 'all'
                                        ? "bg-indigo-500 text-white shadow-md shadow-indigo-500/20"
                                        : "text-slate-500 hover:text-slate-300 bg-slate-800/50"
                                )}
                            >
                                All
                            </button>
                            {stages.map(([id, label]) => (
                                <button
                                    key={id}
                                    onClick={() => { setStageFilter(id); setPage(1); }}
                                    className={cn(
                                        "px-3 py-1.5 text-[10px] font-black rounded-lg uppercase tracking-widest transition-all",
                                        stageFilter === id
                                            ? "bg-indigo-500 text-white shadow-md shadow-indigo-500/20"
                                            : "text-slate-500 hover:text-slate-300 bg-slate-800/50"
                                    )}
                                >
                                    {label}
                                </button>
                            ))}
                        </div>

                        {(searchTerm || stageFilter !== 'all') && (
                            <Button variant="ghost" size="sm" onClick={() => { setSearchTerm(''); setStageFilter('all'); setPage(1); }}
                                className="text-slate-500 hover:text-rose-400 text-[10px] font-black uppercase whitespace-nowrap">
                                Clear All
                            </Button>
                        )}
                    </div>
                </Card>

                {viewMode === 'table' ? (
                    <Card className="border-slate-800/60 bg-slate-950/40 backdrop-blur-md rounded-2xl overflow-hidden shadow-2xl">
                        <DataTable
                            data={pagedLeads}
                            columns={columns}
                            keyField="id"
                            selection={selection}
                            onToggleSelection={(id) => {
                                const s = new Set(selection);
                                s.has(id) ? s.delete(id) : s.add(id);
                                setSelection(s);
                            }}
                            onToggleAll={(ids) => {
                                setSelection(selection.size === ids.length ? new Set() : new Set(ids));
                            }}
                            sortConfig={sortConfig}
                            onSort={(key) => {
                                setSortConfig({ key, direction: sortConfig.key === key && sortConfig.direction === 'asc' ? 'desc' : 'asc' });
                            }}
                            page={page}
                            pageSize={pageSize}
                            total={leads?.length || 0}
                            onPageChange={setPage}
                            isLoading={leadsLoading}
                            emptyMessage={
                                <div className="flex flex-col items-center justify-center py-16 opacity-30">
                                    <Search className="w-12 h-12 text-slate-600 mb-3" />
                                    <p className="text-base font-black uppercase tracking-widest">No leads found</p>
                                </div>
                            }
                        />
                    </Card>
                ) : (
                    <DragDropContext onDragEnd={onDragEnd}>
                        <Droppable droppableId="kanban-columns" direction="horizontal" type="COLUMN">
                            {(provided) => (
                                <div
                                    ref={provided.innerRef}
                                    {...provided.droppableProps}
                                    className="flex gap-4 overflow-x-auto pb-6"
                                >
                                    {(kanbanOrderLoading || groupedLoading) ? (
                                        Array.from({ length: 6 }).map((_, i) => (
                                            <div key={i} className="min-w-[320px]">
                                                <Skeleton className="h-10 w-full rounded-xl mb-3" />
                                                <Skeleton className="h-32 w-full rounded-2xl mb-3" />
                                                <Skeleton className="h-32 w-full rounded-2xl" />
                                            </div>
                                        ))
                                    ) : (
                                        stageOrder.map((stageId, index) => {
                                            const items = leadsByStage?.[stageId] || [];
                                            const dealTotals = pipelineSummary?.stages?.find((s: any) => s.stage === stageId)?.deal_value_by_currency || {};
                                            const totalLine = Object.entries(dealTotals)
                                                .map(([cur, val]) => formatMoney(Number(val || 0), cur))
                                                .join(' · ');

                                            return (
                                                <Draggable key={stageId} draggableId={stageId} index={index}>
                                                    {(colProvided) => (
                                                        <div
                                                            ref={colProvided.innerRef}
                                                            {...colProvided.draggableProps}
                                                            className="min-w-[320px] max-w-[320px]"
                                                        >
                                                            <div className="flex items-center justify-between mb-3 px-1">
                                                                <div className="flex items-center gap-2 min-w-0">
                                                                    <div
                                                                        {...colProvided.dragHandleProps}
                                                                        className="px-2 py-1 rounded-lg bg-slate-900/60 border border-slate-800 text-slate-500 text-[10px] font-black uppercase tracking-widest cursor-grab active:cursor-grabbing"
                                                                        title="Drag to reorder columns"
                                                                    >
                                                                        {STAGE_LABELS[stageId]}
                                                                    </div>
                                                                    <Badge variant="neutral" className="bg-slate-950 text-slate-400 font-bold border border-slate-800">
                                                                        {items.length}
                                                                    </Badge>
                                                                </div>
                                                                {totalLine ? (
                                                                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest whitespace-nowrap">
                                                                        {totalLine}
                                                                    </span>
                                                                ) : null}
                                                            </div>

                                                            <Card className="border-slate-800/60 bg-slate-950/30 backdrop-blur-md rounded-2xl overflow-hidden shadow-2xl">
                                                                <Droppable droppableId={stageId} type="CARD">
                                                                    {(dropProvided, snapshot) => (
                                                                        <div
                                                                            ref={dropProvided.innerRef}
                                                                            {...dropProvided.droppableProps}
                                                                            className={cn(
                                                                                "p-3 space-y-3 min-h-[220px]",
                                                                                snapshot.isDraggingOver ? "bg-indigo-500/5" : ""
                                                                            )}
                                                                        >
                                                                            {items.length === 0 ? (
                                                                                <div className="h-40 border border-dashed border-slate-800 rounded-xl flex items-center justify-center text-slate-600 text-xs font-bold">
                                                                                    Empty
                                                                                </div>
                                                                            ) : (
                                                                                items.map((lead, i) => (
                                                                                    <Draggable key={lead.id} draggableId={String(lead.id)} index={i}>
                                                                                        {(cardProvided, cardSnapshot) => (
                                                                                            <div
                                                                                                ref={cardProvided.innerRef}
                                                                                                {...cardProvided.draggableProps}
                                                                                                {...cardProvided.dragHandleProps}
                                                                                                className={cn(
                                                                                                    "p-4 rounded-xl border border-slate-800/60 bg-slate-950/40 hover:bg-slate-900/50 hover:border-indigo-500/30 transition-colors cursor-grab active:cursor-grabbing",
                                                                                                    cardSnapshot.isDragging ? "shadow-2xl border-indigo-500/50 bg-slate-900" : ""
                                                                                                )}
                                                                                            >
                                                                                                <div className="flex items-start justify-between gap-3">
                                                                                                    <div className="min-w-0">
                                                                                                        <div className="font-black text-slate-200 truncate uppercase italic tracking-tight">
                                                                                                            {lead.company_name}
                                                                                                        </div>
                                                                                                        <div className="text-[10px] text-slate-500 uppercase font-black mt-1">
                                                                                                            {lead.source}
                                                                                                        </div>
                                                                                                    </div>
                                                                                                    <div className="text-right flex-shrink-0">
                                                                                                        <div className={cn(
                                                                                                            "text-sm font-black italic",
                                                                                                            lead.lead_score > 70 ? "text-emerald-400" :
                                                                                                                lead.lead_score > 40 ? "text-amber-400" : "text-rose-400"
                                                                                                        )}>
                                                                                                            {lead.lead_score}
                                                                                                        </div>
                                                                                                        <div className="text-[10px] text-slate-600 font-black uppercase">Score</div>
                                                                                                    </div>
                                                                                                </div>

                                                                                                <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-800/50">
                                                                                                    <div className="text-xs font-black text-slate-300 italic">
                                                                                                        {lead.deal_value ? formatMoney(Number(lead.deal_value), String(lead.deal_currency || 'USD')) : (
                                                                                                            <span className="text-slate-600 text-xs font-bold">—</span>
                                                                                                        )}
                                                                                                    </div>
                                                                                                    <Link to={`/leads/${lead.id}`}>
                                                                                                        <Button variant="ghost" size="sm" className="h-8 px-3 text-[10px] font-black hover:bg-indigo-500/10 hover:text-indigo-400 whitespace-nowrap">
                                                                                                            Open
                                                                                                            <ArrowRight className="w-3 h-3 ml-1.5" />
                                                                                                        </Button>
                                                                                                    </Link>
                                                                                                </div>
                                                                                            </div>
                                                                                        )}
                                                                                    </Draggable>
                                                                                ))
                                                                            )}
                                                                            {dropProvided.placeholder}
                                                                        </div>
                                                                    )}
                                                                </Droppable>
                                                            </Card>
                                                        </div>
                                                    )}
                                                </Draggable>
                                            );
                                        })
                                    )}
                                    {provided.placeholder}
                                </div>
                            )}
                        </Droppable>
                    </DragDropContext>
                )}
            </div>

            <AddLeadModal
                isOpen={isAddModalOpen}
                onClose={() => setIsAddModalOpen(false)}
            />
        </Layout>
    );
};

export default LeadsList;
