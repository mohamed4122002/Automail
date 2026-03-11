import React, { useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { DataTable } from '../components/ui/DataTable';
import api from '../lib/api';
import {
    Building2, Globe, Users, ArrowLeft, ArrowRight,
    Calendar, Briefcase, ExternalLink, Mail
} from 'lucide-react';
import { cn } from '../lib/utils';

interface Organization {
    id: string;
    name: string;
    industry?: string;
    website?: string;
    logo_url?: string;
    created_at: string;
    updated_at: string;
}

interface Lead {
    id: string;
    company_name: string;
    source: string;
    stage: string;
    lead_score: number;
    lead_status: string;
    assigned_to_name?: string;
    created_at: string;
}

const STAGE_LABELS: Record<string, string> = {
    lead: 'Lead', call: 'Call', meeting: 'Meeting',
    proposal: 'Proposal', negotiation: 'Negotiation',
    project: 'Project', won: 'Won', lost: 'Lost',
};

const OrganizationDetail: React.FC = () => {
    const { id } = useParams<{ id: string }>();

    const { data: org, isLoading: orgLoading } = useQuery<Organization>({
        queryKey: ['organization', id],
        queryFn: async () => (await api.get(`/organizations/${id}`)).data,
    });

    const { data: leads, isLoading: leadsLoading } = useQuery<Lead[]>({
        queryKey: ['organization-leads', id],
        queryFn: async () => (await api.get(`/organizations/${id}/leads`)).data,
    });

    const columns = useMemo(() => [
        {
            key: 'name',
            header: 'Lead Name/Details',
            cell: (lead: Lead) => (
                <div className="flex flex-col">
                    <span className="font-bold text-slate-200 uppercase italic text-[11px] tracking-tight">{lead.company_name}</span>
                    <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">{lead.source}</span>
                </div>
            )
        },
        {
            key: 'stage',
            header: 'Current Stage',
            cell: (lead: Lead) => (
                <Badge variant="outline" className={cn(
                    "font-black italic uppercase text-[10px] whitespace-nowrap",
                    lead.stage === 'won' ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/5" :
                        lead.stage === 'lost' ? "text-rose-400 border-rose-500/30 bg-rose-500/5" :
                            "text-indigo-400 border-indigo-500/30 bg-indigo-500/5"
                )}>
                    {STAGE_LABELS[lead.stage] || lead.stage}
                </Badge>
            )
        },
        {
            key: 'assigned_to',
            header: 'Assigned To',
            cell: (lead: Lead) => (
                <div className="flex items-center gap-2">
                    {lead.assigned_to_name ? (
                        <span className="text-xs font-medium text-slate-400">{lead.assigned_to_name}</span>
                    ) : (
                        <span className="text-xs italic text-slate-600">Unassigned</span>
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
                        <Button variant="ghost" size="sm" className="h-7 text-[9px] font-black uppercase hover:bg-slate-800 tracking-widest">
                            OPEN LEAD
                        </Button>
                    </Link>
                </div>
            )
        }
    ], []);

    if (orgLoading) return (
        <Layout>
            <div className="p-8 max-w-[1200px] mx-auto space-y-6">
                <Skeleton className="h-32 rounded-2xl w-full" />
                <Skeleton className="h-96 rounded-2xl w-full" />
            </div>
        </Layout>
    );

    if (!org) return (
        <Layout>
            <div className="p-16 flex flex-col items-center justify-center">
                <p className="text-slate-500 font-black uppercase tracking-widest">Organization not found</p>
                <Link to="/organizations" className="mt-4">
                    <Button variant="outline">Back to Directory</Button>
                </Link>
            </div>
        </Layout>
    );

    return (
        <Layout>
            <div className="flex flex-col gap-6 p-8 max-w-[1200px] mx-auto animate-in fade-in slide-in-from-bottom-2 duration-500">
                {/* Breadcrumbs / Back */}
                <div className="flex items-center gap-2">
                    <Link to="/organizations" className="group flex items-center gap-2 text-slate-500 hover:text-indigo-400 transition-colors">
                        <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                        <span className="text-[10px] font-black uppercase tracking-widest italic">Back to Index</span>
                    </Link>
                </div>

                {/* Main Header Card */}
                <Card className="p-8 border-slate-800/60 bg-slate-950/40 backdrop-blur-md rounded-3xl overflow-hidden relative border-t-indigo-500/20 shadow-2xl">
                    <div className="flex flex-col md:flex-row gap-8 items-start relative z-10">
                        <div className="w-24 h-24 rounded-[32px] bg-slate-900 flex items-center justify-center border border-slate-800/50 shadow-inner ring-8 ring-indigo-500/5 overflow-hidden">
                            {org.logo_url ? (
                                <img src={org.logo_url} alt={org.name} className="w-full h-full object-cover" />
                            ) : (
                                <Building2 className="w-10 h-10 text-indigo-500/50" />
                            )}
                        </div>

                        <div className="flex-1 space-y-4">
                            <div>
                                <h1 className="text-5xl font-black text-slate-100 italic tracking-tighter uppercase leading-none mb-2">
                                    {org.name}
                                </h1>
                                <div className="flex flex-wrap gap-4 items-center">
                                    {org.industry && (
                                        <div className="flex items-center gap-2 text-indigo-400/80 uppercase font-black text-[10px] tracking-widest">
                                            <Briefcase className="w-3.5 h-3.5" />
                                            {org.industry}
                                        </div>
                                    )}
                                    {org.website && (
                                        <a href={org.website} target="_blank" rel="noopener noreferrer"
                                            className="flex items-center gap-2 text-slate-500 hover:text-indigo-400 transition-colors uppercase font-black text-[10px] tracking-widest">
                                            <Globe className="w-3.5 h-3.5" />
                                            {org.website.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                                            <ExternalLink className="w-2.5 h-2.5 opacity-50" />
                                        </a>
                                    )}
                                </div>
                            </div>

                            {/* Aggregated Stats (Phase 5) */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
                                <div className="space-y-1">
                                    <span className="block text-[9px] font-black text-slate-600 uppercase tracking-widest">Total Leads</span>
                                    <span className="text-xl font-black text-slate-200">{leads?.length || 0}</span>
                                </div>
                                <div className="space-y-1">
                                    <span className="block text-[9px] font-black text-slate-600 uppercase tracking-widest">Pipeline Value</span>
                                    <span className="text-xl font-black text-emerald-400 italic">${leads?.reduce((acc, l) => acc + (l as any).deal_value || 0, 0).toLocaleString()}</span>
                                </div>
                            </div>
                        </div>

                        {/* Stage Funnel Mini-Chart (Phase 5) */}
                        <div className="flex flex-col gap-2 min-w-[200px] items-end justify-center h-full pt-4">
                            <div className="flex flex-col gap-1 w-full max-w-[120px]">
                                {Object.entries(leads?.reduce((acc: any, l) => {
                                    acc[l.stage] = (acc[l.stage] || 0) + 1;
                                    return acc;
                                }, {}) || {}).slice(0, 4).sort((a: any, b: any) => b[1] - a[1]).map(([stage, count]: any) => (
                                    <div key={stage} className="space-y-1">
                                        <div className="flex justify-between text-[8px] font-black text-slate-500 uppercase">
                                            <span>{stage}</span>
                                            <span>{count}</span>
                                        </div>
                                        <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-indigo-500 rounded-full transition-all duration-1000"
                                                style={{ width: `${(count / (leads?.length || 1)) * 100}%` }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <span className="text-[9px] font-black text-slate-600 uppercase tracking-tighter">Org Stage Funnel</span>
                        </div>
                    </div>
                </Card>

                {/* Leads List */}
                <div className="space-y-4">
                    <div className="flex items-center gap-2 ml-2">
                        <Users className="w-4 h-4 text-slate-500" />
                        <h2 className="text-sm font-black text-slate-300 uppercase tracking-widest italic">Leads <span className="text-indigo-500">History</span></h2>
                    </div>

                    <Card className="border-slate-800/60 bg-slate-950/40 backdrop-blur-md rounded-2xl overflow-hidden shadow-xl border-b-indigo-500/10">
                        <DataTable
                            data={leads || []}
                            columns={columns}
                            keyField="id"
                            selection={new Set()}
                            onToggleSelection={() => { }}
                            onToggleAll={() => { }}
                            sortConfig={{ key: 'created_at', direction: 'desc' }}
                            onSort={() => { }}
                            page={1}
                            pageSize={100}
                            total={leads?.length || 0}
                            onPageChange={() => { }}
                            isLoading={leadsLoading}
                            emptyMessage={
                                <div className="py-20 text-center opacity-40">
                                    <p className="text-xs font-black uppercase tracking-widest italic">No leads associated with this organization</p>
                                </div>
                            }
                        />
                    </Card>
                </div>
            </div>
        </Layout>
    );
};

export default OrganizationDetail;
