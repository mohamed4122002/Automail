import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import api from '../lib/api';
import {
    Users, Mail, TrendingUp, Flame, Snowflake,
    Zap, Search, Filter, UserPlus, Activity,
    Clock, Star, CheckCircle2, XCircle, List
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { LEAD_STATUS_COLORS, LEAD_STATUS_LABELS } from '../lib/constants';

interface Lead {
    id: string;
    contact_id: string;
    lead_status: string;
    lead_score: number;
    assigned_to_id?: string;
    claimed_at?: string;
    last_contacted_at?: string;
    last_email_opened_at?: string;
    last_link_clicked_at?: string;
    created_at: string;
    updated_at: string;
    contact_email: string;
    contact_first_name?: string;
    contact_last_name?: string;
    contact_list_id: string;
    contact_list_name: string;
    assigned_to_email?: string;
    assigned_to_name?: string;
}

interface LeadStats {
    total: number;
    new: number;
    warm: number;
    hot: number;
    cold: number;
    unsubscribed: number;
    by_list: Record<string, number>;
}

const Leads: React.FC = () => {
    const [selectedListId, setSelectedListId] = useState<string>('all');
    const [selectedStatus, setSelectedStatus] = useState<string>('all');
    const [searchTerm, setSearchTerm] = useState('');
    const queryClient = useQueryClient();

    const { data: stats, isLoading: statsLoading } = useQuery<LeadStats>({
        queryKey: ['lead-stats'],
        queryFn: async () => {
            const res = await api.get('/leads/stats');
            return res.data;
        }
    });

    const { data: contactLists } = useQuery({
        queryKey: ['contact-lists'],
        queryFn: async () => {
            const res = await api.get('/contacts/lists');
            return res.data;
        }
    });

    const { data: leads, isLoading: leadsLoading } = useQuery<Lead[]>({
        queryKey: ['leads', selectedListId, selectedStatus, searchTerm],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (selectedListId !== 'all') params.append('contact_list_id', selectedListId);
            if (selectedStatus !== 'all') params.append('lead_status', selectedStatus);
            if (searchTerm) params.append('search', searchTerm);

            const res = await api.get(`/leads?${params.toString()}`);
            return res.data;
        }
    });

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'hot': return <Flame className="w-5 h-5" />;
            case 'warm': return <TrendingUp className="w-5 h-5" />;
            case 'cold': return <Snowflake className="w-5 h-5" />;
            case 'new': return <Zap className="w-5 h-5" />;
            default: return <XCircle className="w-5 h-5" />;
        }
    };

    const getStatusColor = (status: string) => {
        const colors: Record<string, string> = {
            hot: 'from-red-500 to-orange-500',
            warm: 'from-amber-500 to-yellow-500',
            cold: 'from-blue-500 to-cyan-500',
            new: 'from-indigo-500 to-violet-500',
            unsubscribed: 'from-slate-600 to-slate-700'
        };
        return colors[status] || 'from-slate-500 to-slate-600';
    };

    const [isMoveModalOpen, setIsMoveModalOpen] = useState(false);
    const [movingLead, setMovingLead] = useState<Lead | null>(null);
    const [targetListId, setTargetListId] = useState<string>('');

    const moveLeadMutation = useMutation({
        mutationFn: async ({ leadId, listId }: { leadId: string; listId: string }) => {
            return api.patch(`/leads/${leadId}`, { contact_list_id: listId });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['leads'] });
            queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
            setIsMoveModalOpen(false);
            setMovingLead(null);
        }
    });

    const handleMoveLead = () => {
        if (movingLead && targetListId) {
            moveLeadMutation.mutate({ leadId: movingLead.id, listId: targetListId });
        }
    };

    return (
        <Layout>
            <div className="space-y-8 p-8">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-5xl font-black text-slate-100 italic tracking-tighter leading-none">
                            LEADS DASHBOARD
                        </h1>
                        <p className="text-slate-500 mt-3 text-lg font-semibold tracking-tight">
                            Manage and track your imported contacts with precision
                        </p>
                    </div>
                    <Link to="/contacts">
                        <Button className="rounded-2xl px-8 py-6 bg-indigo-500 hover:bg-indigo-400 font-black shadow-2xl shadow-indigo-500/20">
                            <UserPlus className="w-5 h-5 mr-2" />
                            IMPORT CONTACTS
                        </Button>
                    </Link>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
                    {[
                        { label: 'NEW', value: stats?.new || 0, status: 'new', icon: Zap },
                        { label: 'WARM', value: stats?.warm || 0, status: 'warm', icon: TrendingUp },
                        { label: 'HOT', value: stats?.hot || 0, status: 'hot', icon: Flame },
                        { label: 'COLD', value: stats?.cold || 0, status: 'cold', icon: Snowflake },
                        { label: 'TOTAL', value: stats?.total || 0, status: 'total', icon: Users }
                    ].map((stat) => (
                        <Card
                            key={stat.label}
                            className={`relative overflow-hidden border-2 transition-all duration-500 cursor-pointer group ${selectedStatus === stat.status.toLowerCase()
                                ? 'border-indigo-500/50 bg-indigo-500/10 scale-105'
                                : 'border-slate-800/60 hover:border-slate-700/80'
                                }`}
                            onClick={() => setSelectedStatus(stat.status === 'total' ? 'all' : stat.status)}
                        >
                            <div className={`absolute inset-0 bg-gradient-to-br ${getStatusColor(stat.status)} opacity-0 group-hover:opacity-5 transition-opacity`} />
                            <div className="p-6 relative z-10">
                                <div className="flex items-center justify-between mb-4">
                                    <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${getStatusColor(stat.status)} flex items-center justify-center shadow-lg`}>
                                        <stat.icon className="w-7 h-7 text-white" />
                                    </div>
                                    {selectedStatus === stat.status.toLowerCase() && (
                                        <CheckCircle2 className="w-6 h-6 text-indigo-400 animate-pulse" />
                                    )}
                                </div>
                                <div className="text-4xl font-black text-slate-100 tabular-nums mb-2">
                                    {stat.value}
                                </div>
                                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-black">
                                    {stat.label}
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>

                {/* Filters */}
                <Card className="border-2 border-slate-800/60 bg-slate-900/40">
                    <div className="p-6">
                        <div className="flex flex-col md:flex-row gap-6">
                            {/* Search */}
                            <div className="flex-1">
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">
                                    SEARCH LEADS
                                </label>
                                <div className="relative">
                                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                    <input
                                        type="text"
                                        placeholder="Search by email, name..."
                                        value={searchTerm}
                                        onChange={(e) => setSearchTerm(e.target.value)}
                                        className="w-full bg-slate-950 border border-slate-800 rounded-2xl pl-12 pr-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                    />
                                </div>
                            </div>

                            {/* Contact List Filter */}
                            <div className="w-full md:w-80">
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block flex items-center gap-2">
                                    <List className="w-3 h-3" />
                                    CONTACT LIST
                                </label>
                                <select
                                    value={selectedListId}
                                    onChange={(e) => setSelectedListId(e.target.value)}
                                    className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold appearance-none"
                                >
                                    <option value="all">All Lists</option>
                                    {contactLists?.map((list: any) => (
                                        <option key={list.id} value={list.id}>
                                            {list.name} ({stats?.by_list[list.name] || 0})
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Status Filter */}
                            <div className="w-full md:w-64">
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block flex items-center gap-2">
                                    <Filter className="w-3 h-3" />
                                    STATUS
                                </label>
                                <select
                                    value={selectedStatus}
                                    onChange={(e) => setSelectedStatus(e.target.value)}
                                    className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold appearance-none"
                                >
                                    <option value="all">All Statuses</option>
                                    <option value="new">New</option>
                                    <option value="warm">Warm</option>
                                    <option value="hot">Hot</option>
                                    <option value="cold">Cold</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </Card>

                {/* Leads List */}
                <div className="space-y-4">
                    {leadsLoading ? (
                        <div className="flex items-center justify-center py-20">
                            <div className="text-center">
                                <Activity className="w-12 h-12 text-indigo-400 animate-spin mx-auto mb-4" />
                                <p className="text-slate-500 font-semibold">Loading leads...</p>
                            </div>
                        </div>
                    ) : leads && leads.length > 0 ? (
                        leads.map((lead) => (
                            <Card
                                key={lead.id}
                                className="border-2 border-slate-800/60 hover:border-indigo-500/30 transition-all duration-300 group bg-slate-900/40"
                            >
                                <div className="p-6">
                                    <div className="flex items-start justify-between gap-6">
                                        {/* Lead Info */}
                                        <div className="flex-1">
                                            <div className="flex items-center gap-4 mb-3">
                                                <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${getStatusColor(lead.lead_status)} flex items-center justify-center shadow-lg`}>
                                                    {getStatusIcon(lead.lead_status)}
                                                </div>
                                                <div>
                                                    <div className="flex items-center gap-3">
                                                        <h3 className="text-xl font-bold text-slate-100">
                                                            {lead.contact_first_name || lead.contact_last_name
                                                                ? `${lead.contact_first_name || ''} ${lead.contact_last_name || ''}`.trim()
                                                                : 'Unknown'}
                                                        </h3>
                                                        <span className="text-xs px-3 py-1 rounded-full bg-slate-800/60 text-slate-400 font-bold uppercase tracking-wider">
                                                            Score: {lead.lead_score}
                                                        </span>
                                                    </div>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <Mail className="w-4 h-4 text-slate-500" />
                                                        <span className="text-sm text-slate-400 font-medium">{lead.contact_email}</span>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Metadata */}
                                            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 font-semibold">
                                                <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-800/40">
                                                    <List className="w-3 h-3 text-indigo-400" />
                                                    {lead.contact_list_name}
                                                </div>
                                                {lead.last_contacted_at && (
                                                    <div className="flex items-center gap-2">
                                                        <Clock className="w-3 h-3" />
                                                        Last contacted: {new Date(lead.last_contacted_at).toLocaleDateString()}
                                                    </div>
                                                )}
                                                {lead.assigned_to_name && (
                                                    <div className="flex items-center gap-2">
                                                        <UserPlus className="w-3 h-3" />
                                                        Assigned to: {lead.assigned_to_name}
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        {/* Actions */}
                                        <div className="flex flex-col gap-3">
                                            <Link to={`/leads/${lead.id}`}>
                                                <Button
                                                    variant="secondary"
                                                    className="rounded-xl px-6 py-3 border-slate-800 font-bold text-xs whitespace-nowrap"
                                                >
                                                    VIEW DETAILS
                                                </Button>
                                            </Link>
                                            <Button
                                                variant="ghost"
                                                className="rounded-xl px-6 py-3 font-bold text-xs whitespace-nowrap"
                                                onClick={() => {
                                                    setMovingLead(lead);
                                                    setTargetListId(lead.contact_list_id);
                                                    setIsMoveModalOpen(true);
                                                }}
                                            >
                                                MOVE TO LIST
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            </Card>
                        ))
                    ) : (
                        <Card className="border-2 border-slate-800/60 bg-slate-900/40">
                            <div className="p-20 text-center">
                                <Users className="w-16 h-16 text-slate-700 mx-auto mb-4" />
                                <h3 className="text-2xl font-black text-slate-400 mb-2">NO LEADS FOUND</h3>
                                <p className="text-slate-600 font-semibold">
                                    {searchTerm || selectedListId !== 'all' || selectedStatus !== 'all'
                                        ? 'Try adjusting your filters'
                                        : 'Import contacts to get started'}
                                </p>
                            </div>
                        </Card>
                    )}
                </div>
            </div>

            {/* Move to List Modal */}
            {isMoveModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
                    <Card className="w-full max-w-md border-2 border-slate-800 bg-slate-900 shadow-2xl">
                        <div className="p-8">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center">
                                    <List className="w-6 h-6 text-indigo-400" />
                                </div>
                                <h2 className="text-2xl font-black text-slate-100 italic tracking-tight">MOVE TO LIST</h2>
                            </div>

                            <p className="text-slate-400 text-sm font-semibold mb-6">
                                Select the target list for <span className="text-indigo-400">{movingLead?.contact_email}</span>
                            </p>

                            <div className="space-y-6">
                                <div>
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">
                                        TARGET CONTACT LIST
                                    </label>
                                    <select
                                        value={targetListId}
                                        onChange={(e) => setTargetListId(e.target.value)}
                                        className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold appearance-none"
                                    >
                                        {contactLists?.map((list: any) => (
                                            <option key={list.id} value={list.id}>
                                                {list.name}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div className="flex gap-4">
                                    <Button
                                        variant="secondary"
                                        className="flex-1 rounded-2xl py-6 font-black border-slate-800"
                                        onClick={() => setIsMoveModalOpen(false)}
                                    >
                                        CANCEL
                                    </Button>
                                    <Button
                                        className="flex-1 rounded-2xl py-6 bg-indigo-500 hover:bg-indigo-400 font-black shadow-xl shadow-indigo-500/20"
                                        onClick={handleMoveLead}
                                        isLoading={moveLeadMutation.isPending}
                                    >
                                        CONFIRM MOVE
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </Card>
                </div>
            )}
        </Layout>
    );
};

export default Leads;
