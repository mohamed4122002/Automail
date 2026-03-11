import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { DataTable } from '../components/ui/DataTable';
import api from '../lib/api';
import {
    Building2, Search, ArrowRight, Globe, Layers
} from 'lucide-react';
import { Link } from 'react-router-dom';
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

const Organizations: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [page, setPage] = useState(1);
    const pageSize = 15;

    const { data: organizations, isLoading } = useQuery<Organization[]>({
        queryKey: ['organizations', searchTerm],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (searchTerm) params.append('search', searchTerm);
            return (await api.get(`/organizations?${params}`)).data;
        },
    });

    const columns = useMemo(() => [
        {
            key: 'name',
            header: 'Organization',
            sortable: true,
            cell: (org: Organization) => (
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center flex-shrink-0 border border-slate-700/50 shadow-inner">
                        <Building2 className="w-5 h-5 text-indigo-400" />
                    </div>
                    <div className="min-w-0">
                        <div className="font-bold text-slate-200 truncate text-base tracking-tight">{org.name}</div>
                        {org.industry && (
                            <div className="text-[10px] text-slate-500 uppercase font-black tracking-widest">{org.industry}</div>
                        )}
                    </div>
                </div>
            ),
        },
        {
            key: 'website',
            header: 'Website',
            sortable: true,
            cell: (org: Organization) => (
                org.website ? (
                    <a href={org.website} target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-xs font-bold text-slate-400 hover:text-indigo-400 transition-colors uppercase tracking-tight">
                        <Globe className="w-3 h-3" />
                        {org.website.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                    </a>
                ) : (
                    <span className="text-slate-600 text-xs font-bold italic">—</span>
                )
            ),
        },
        {
            key: 'created_at',
            header: 'Added On',
            sortable: true,
            cell: (org: Organization) => (
                <div className="text-xs font-medium text-slate-400">
                    {new Date(org.created_at).toLocaleDateString()}
                </div>
            ),
        },
        {
            key: 'actions',
            header: '',
            cell: (org: Organization) => (
                <div className="flex justify-end">
                    <Link to={`/organizations/${org.id}`}>
                        <Button variant="ghost" size="sm"
                            className="h-9 px-4 text-[10px] font-black hover:bg-indigo-500/10 hover:text-indigo-400 whitespace-nowrap tracking-widest uppercase">
                            VIEW DETAILS
                            <ArrowRight className="w-3.5 h-3.5 ml-2" />
                        </Button>
                    </Link>
                </div>
            ),
        },
    ], []);

    const pagedEntries = useMemo(() => {
        if (!organizations) return [];
        return organizations.slice((page - 1) * pageSize, page * pageSize);
    }, [organizations, page]);

    return (
        <Layout>
            <div className="flex flex-col gap-6 p-8 max-w-[1400px] mx-auto">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div>
                        <div className="flex items-center gap-4 mb-2">
                            <div className="w-12 h-12 rounded-2xl bg-indigo-500 flex items-center justify-center shadow-2xl shadow-indigo-500/30 ring-4 ring-indigo-500/10">
                                <Building2 className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-4xl font-black text-slate-100 italic tracking-tighter uppercase leading-none">
                                    Organizations <span className="text-indigo-500">Directory</span>
                                </h1>
                                <p className="text-slate-500 text-[10px] font-black uppercase tracking-[0.2em] mt-1.5 opacity-80">
                                    Entity management and grouping for multi-lead companies
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Filters */}
                <Card className="border-slate-800/60 bg-slate-950/40 backdrop-blur-md rounded-2xl overflow-hidden border-t-indigo-500/20">
                    <div className="px-6 py-5 flex flex-col sm:flex-row gap-4 items-center">
                        <div className="relative flex-1 w-full">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4.5 h-4.5 text-slate-500" />
                            <input
                                type="text"
                                placeholder="Filter by organization name..."
                                value={searchTerm}
                                onChange={e => { setSearchTerm(e.target.value); setPage(1); }}
                                className="w-full bg-slate-900/40 border border-slate-800/80 rounded-xl pl-12 pr-4 py-3 text-sm text-slate-200 focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 outline-none transition-all font-medium placeholder:text-slate-600 shadow-inner"
                            />
                        </div>
                        {searchTerm && (
                            <Button variant="ghost" size="sm" onClick={() => { setSearchTerm(''); setPage(1); }}
                                className="text-slate-500 hover:text-rose-400 text-[10px] font-black uppercase tracking-widest px-4 border border-slate-800 bg-slate-900/30">
                                Clear
                            </Button>
                        )}
                    </div>
                </Card>

                {/* DataTable */}
                <Card className="border-slate-800/60 bg-slate-950/40 backdrop-blur-md rounded-2xl overflow-hidden shadow-2xl relative">
                    <DataTable
                        data={pagedEntries}
                        columns={columns}
                        keyField="id"
                        selection={new Set()}
                        onToggleSelection={() => { }}
                        onToggleAll={() => { }}
                        sortConfig={{ key: 'name', direction: 'asc' }}
                        onSort={() => { }}
                        page={page}
                        pageSize={pageSize}
                        total={organizations?.length || 0}
                        onPageChange={setPage}
                        isLoading={isLoading}
                        emptyMessage={
                            <div className="flex flex-col items-center justify-center py-24 opacity-40">
                                <div className="w-20 h-20 rounded-full bg-slate-900 flex items-center justify-center mb-6 border border-slate-800/50 shadow-inner">
                                    <Layers className="w-10 h-10 text-slate-600" />
                                </div>
                                <p className="text-lg font-black uppercase tracking-[0.3em] text-slate-500 italic">No organizations found</p>
                                <p className="text-[10px] font-bold text-slate-600 uppercase mt-2 tracking-widest">Leads will be automatically grouped as they are created</p>
                            </div>
                        }
                    />
                </Card>
            </div>
        </Layout>
    );
};

export default Organizations;
