import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { ImportWizard } from '../components/contacts/ImportWizard';
import api from '../lib/api';
import {
    Users, Plus, Upload, List, Hash, Calendar,
    MoreVertical, Search, FileDown, ArrowRight, Table2
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface ContactList {
    id: string;
    name: string;
    description?: string;
    contact_count: number;
    created_at: string;
}

const Contacts: React.FC = () => {
    const [showImportWizard, setShowImportWizard] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const queryClient = useQueryClient();

    const { data: contactLists, isLoading: listsLoading } = useQuery<ContactList[]>({
        queryKey: ['contact-lists'],
        queryFn: async () => {
            const res = await api.get('/contacts/lists');
            return res.data;
        }
    });

    const deleteListMutation = useMutation({
        mutationFn: async (id: string) => {
            await api.delete(`/contacts/lists/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['contact-lists'] });
        }
    });

    if (showImportWizard) {
        return (
            <Layout>
                <div className="p-8 space-y-8">
                    <div className="flex items-center gap-4">
                        <Button
                            variant="ghost"
                            onClick={() => setShowImportWizard(false)}
                            className="rounded-xl px-4 py-2 hover:bg-slate-800"
                        >
                            <ArrowRight className="w-5 h-5 rotate-180" />
                        </Button>
                        <div>
                            <h1 className="text-4xl font-black text-slate-100 italic tracking-tighter leading-none">
                                IMPORT WIZARD
                            </h1>
                            <p className="text-slate-500 mt-2 font-semibold">
                                Securely ingest and map your contact data
                            </p>
                        </div>
                    </div>
                    <ImportWizard onComplete={() => {
                        setShowImportWizard(false);
                        queryClient.invalidateQueries({ queryKey: ['contact-lists'] });
                    }} />
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="p-8 space-y-8">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-5xl font-black text-slate-100 italic tracking-tighter leading-none">
                            AUDIENCE MANAGER
                        </h1>
                        <p className="text-slate-500 mt-3 text-lg font-semibold tracking-tight">
                            Organize your contact lists and segments
                        </p>
                    </div>
                    <Button
                        onClick={() => setShowImportWizard(true)}
                        className="rounded-2xl px-8 py-6 bg-indigo-500 hover:bg-indigo-400 font-black shadow-2xl shadow-indigo-500/20"
                    >
                        <Upload className="w-5 h-5 mr-3" />
                        IMPORT DATA
                    </Button>
                </div>

                {/* Content */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {/* Lists Grid */}
                    <div className="md:col-span-3 space-y-6">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xl font-black text-slate-300 flex items-center gap-3">
                                <List className="w-5 h-5 text-indigo-400" />
                                CONTACT LISTS
                            </h3>
                            {/* Search placeholder */}
                            <div className="relative">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input
                                    type="text"
                                    placeholder="Search lists..."
                                    className="bg-slate-900/50 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-sm text-slate-300 focus:ring-2 focus:ring-indigo-500/50 outline-none w-64 font-semibold"
                                />
                            </div>
                        </div>

                        {listsLoading ? (
                            <div className="grid md:grid-cols-3 gap-6">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="h-48 rounded-3xl bg-slate-900/50 animate-pulse border border-slate-800/50" />
                                ))}
                            </div>
                        ) : (
                            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {/* New List Card */}
                                <Card
                                    className="border-2 border-dashed border-slate-800/60 bg-slate-900/20 hover:bg-slate-900/40 hover:border-indigo-500/30 transition-all duration-300 cursor-pointer group flex flex-col items-center justify-center gap-4 min-h-[200px]"
                                    onClick={() => setShowImportWizard(true)}
                                >
                                    <div className="w-16 h-16 rounded-full bg-slate-800/50 group-hover:bg-indigo-500/10 flex items-center justify-center transition-all duration-500 group-hover:scale-110">
                                        <Plus className="w-8 h-8 text-slate-500 group-hover:text-indigo-400" />
                                    </div>
                                    <p className="text-slate-500 font-bold text-sm tracking-wide group-hover:text-slate-400">CREATE NEW LIST</p>
                                </Card>

                                {contactLists?.map(list => (
                                    <Card
                                        key={list.id}
                                        className="border-2 border-slate-800/60 hover:border-indigo-500/30 bg-slate-900/40 transition-all duration-300 group relative overflow-hidden"
                                    >
                                        <div className="p-6 h-full flex flex-col justify-between">
                                            <div>
                                                <div className="flex items-start justify-between mb-4">
                                                    <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 shadow-lg shadow-indigo-500/5">
                                                        <Table2 className="w-6 h-6 text-indigo-400" />
                                                    </div>
                                                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-lg hover:bg-slate-800">
                                                        <MoreVertical className="w-4 h-4 text-slate-500" />
                                                    </Button>
                                                </div>
                                                <h4 className="text-2xl font-bold text-slate-100 mb-1 truncate" title={list.name}>{list.name}</h4>
                                                <p className="text-slate-500 text-xs font-semibold uppercase tracking-wider">
                                                    Created {new Date(list.created_at).toLocaleDateString()}
                                                </p>
                                            </div>

                                            <div className="mt-8 pt-6 border-t border-slate-800/60 flex items-center justify-between">
                                                <div className="flex items-center gap-2 text-slate-400">
                                                    <Users className="w-4 h-4" />
                                                    <span className="font-bold text-lg tabular-nums">{list.contact_count || 0}</span>
                                                    <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Contacts</span>
                                                </div>
                                                <Link to={`/leads?contact_list_id=${list.id}`}>
                                                    <Button variant="secondary" className="rounded-xl h-9 text-xs px-4 font-bold border-slate-800 bg-slate-900/50 hover:bg-slate-800">
                                                        VIEW
                                                    </Button>
                                                </Link>
                                            </div>
                                        </div>
                                    </Card>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Contacts;
