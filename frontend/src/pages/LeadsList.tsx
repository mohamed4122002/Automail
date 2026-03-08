import React, { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
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
    Search, ArrowRight, User as UserIcon, UserPlus
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useWebSocket } from '../hooks/useWebSocket';
import { cn } from '../lib/utils';

interface Lead {
    id: string;
    company_name: string;
    source: string;
    stage: string;
    lead_score: number;
    lead_status: string;
    deal_value?: number;
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

const LeadsList: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [stageFilter, setStageFilter] = useState('all');
    const [selection, setSelection] = useState<Set<string>>(new Set());
    const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' }>({ key: 'created_at', direction: 'desc' });
    const [page, setPage] = useState(1);
    const pageSize = 15;

    const queryClient = useQueryClient();

    useWebSocket(`ws://${window.location.host}/api/ws/dashboard`, {
        onMessage: (msg) => {
            if (msg.type === 'crm_event' || msg.type === 'event') {
                queryClient.invalidateQueries({ queryKey: ['leads'] });
                queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
            }
        }
    });

    const { data: stats, isLoading: statsLoading } = useQuery<LeadStats>({
        queryKey: ['lead-stats'],
        queryFn: async () => (await api.get('/leads/stats')).data,
    });

    const { data: leads, isLoading: leadsLoading } = useQuery<Lead[]>({
        queryKey: ['leads', stageFilter, searchTerm],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (stageFilter !== 'all') params.append('stage', stageFilter);
            if (searchTerm) params.append('search', searchTerm);
            return (await api.get(`/leads?${params}`)).data;
        },
    });

    const stages = Object.entries(STAGE_LABELS);

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
                    {lead.assigned_to_name ? (
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

                {/* ── DataTable ── */}
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
            </div>
        </Layout>
    );
};

export default LeadsList;
