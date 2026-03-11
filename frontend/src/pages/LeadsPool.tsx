import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { DataTable } from '../components/ui/DataTable';
import api from '../lib/api';
import { toast } from 'sonner';
import {
    Inbox, User, ArrowRight, CheckCircle2,
    Calendar, Clock, Shield, Star
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '../lib/utils';

interface Lead {
    id: string;
    company_name: string;
    source: string;
    lead_score: number;
    created_at: string;
    is_claimable: boolean;
}

const LeadsPool: React.FC = () => {
    const queryClient = useQueryClient();
    const [page, setPage] = useState(1);
    const pageSize = 10;

    const { data: poolLeads, isLoading } = useQuery<Lead[]>({
        queryKey: ['leads-pool'],
        queryFn: async () => {
            const res = await api.get('/leads/pool');
            return res.data;
        }
    });

    const claimLeadMutation = useMutation({
        mutationFn: async (leadId: string) => {
            return api.post(`/leads/${leadId}/claim`);
        },
        onSuccess: () => {
            toast.success('Lead claimed successfully! It is now in your pipeline.');
            queryClient.invalidateQueries({ queryKey: ['leads-pool'] });
            queryClient.invalidateQueries({ queryKey: ['leads'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-me'] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || 'Failed to claim lead');
        }
    });

    const columns = [
        {
            key: 'company_name',
            header: 'Company',
            cell: (lead: Lead) => (
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
                        <User className="w-4 h-4 text-slate-400" />
                    </div>
                    <div>
                        <div className="font-bold text-slate-200">{lead.company_name}</div>
                        <div className="text-[10px] text-slate-500 uppercase font-black">{lead.source}</div>
                    </div>
                </div>
            )
        },
        {
            key: 'lead_score',
            header: 'Score',
            cell: (lead: Lead) => (
                <Badge variant="outline" className={cn(
                    "font-black italic uppercase text-[10px]",
                    lead.lead_score > 70 ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/5" :
                        lead.lead_score > 40 ? "text-amber-400 border-amber-500/30 bg-amber-500/5" :
                            "text-rose-400 border-rose-500/30 bg-rose-500/5"
                )}>
                    {lead.lead_score}
                </Badge>
            )
        },
        {
            key: 'created_at',
            header: 'Added',
            cell: (lead: Lead) => (
                <span className="text-xs text-slate-500 font-medium">
                    {new Date(lead.created_at).toLocaleDateString()}
                </span>
            )
        },
        {
            key: 'actions',
            header: '',
            cell: (lead: Lead) => (
                <div className="flex justify-end">
                    <Button
                        size="sm"
                        className="bg-indigo-500 hover:bg-indigo-400 text-[10px] font-black uppercase tracking-widest h-8 px-4"
                        onClick={() => claimLeadMutation.mutate(lead.id)}
                        isLoading={claimLeadMutation.isPending && claimLeadMutation.variables === lead.id}
                    >
                        Claim Lead
                    </Button>
                </div>
            )
        }
    ];

    return (
        <Layout>
            <div className="space-y-8 p-8 max-w-[1200px] mx-auto">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-indigo-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                        <Inbox className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-black text-slate-100 italic tracking-tight uppercase">
                            Lead <span className="text-indigo-400">Pool</span>
                        </h1>
                        <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-1">
                            Available leads for claiming · First come, first served
                        </p>
                    </div>
                </div>

                <Card className="border-2 border-slate-800/60 bg-slate-950/40 backdrop-blur-md rounded-3xl overflow-hidden shadow-2xl p-6">
                    {isLoading ? (
                        <div className="space-y-4">
                            {Array.from({ length: 5 }).map((_, i) => (
                                <Skeleton key={i} className="h-16 w-full rounded-xl" />
                            ))}
                        </div>
                    ) : (
                        <DataTable
                            data={poolLeads || []}
                            columns={columns}
                            keyField="id"
                            page={page}
                            pageSize={pageSize}
                            total={poolLeads?.length || 0}
                            onPageChange={setPage}
                            emptyMessage={
                                <div className="flex flex-col items-center justify-center py-20">
                                    <Inbox className="w-12 h-12 text-slate-700 mb-4" />
                                    <p className="text-slate-500 font-bold uppercase tracking-widest">The pool is currently empty</p>
                                    <p className="text-xs text-slate-600 mt-1">Check back later for new claimable leads</p>
                                </div>
                            }
                        />
                    )}
                </Card>
            </div>
        </Layout>
    );
};

export default LeadsPool;
