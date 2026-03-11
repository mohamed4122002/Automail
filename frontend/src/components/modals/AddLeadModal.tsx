import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input } from "../ui/input";
import { toast } from 'sonner';
import api from '../../lib/api';
import { UserPlus, Building2, Globe, Users } from 'lucide-react';
import { cn } from '../../lib/utils';

interface AddLeadModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const LEAD_SOURCES = [
    { value: 'Marketing', label: 'Marketing' },
    { value: 'Referral', label: 'Referral' },
    { value: 'Cold Outreach', label: 'Cold Outreach' },
    { value: 'Inbound', label: 'Inbound' },
    { value: 'Other', label: 'Other' },
];

const LEAD_STAGES = [
    { value: 'lead', label: 'Lead' },
    { value: 'call', label: 'Call' },
    { value: 'meeting', label: 'Meeting' },
    { value: 'proposal', label: 'Proposal' },
];

export function AddLeadModal({ isOpen, onClose }: AddLeadModalProps) {
    const [companyName, setCompanyName] = useState('');
    const [source, setSource] = useState('Marketing');
    const [stage, setStage] = useState('lead');
    const [assignedToId, setAssignedToId] = useState<string>('');

    const queryClient = useQueryClient();

    // Fetch users for assignment (Admins and Managers can assign)
    const { data: users } = useQuery<any[]>({
        queryKey: ['users-assignable'],
        queryFn: async () => {
            const res = await api.get('/admin/users');
            return res.data;
        },
        enabled: isOpen,
    });

    const createLead = useMutation({
        mutationFn: async (data: any) => {
            const res = await api.post('/leads', data);
            return res.data;
        },
        onSuccess: () => {
            toast.success('Lead created successfully');
            queryClient.invalidateQueries({ queryKey: ['leads'] });
            queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
            onClose();
            // Reset form
            setCompanyName('');
            setSource('Marketing');
            setStage('lead');
            setAssignedToId('');
        },
        onError: (error: any) => {
            const msg = error.response?.data?.detail || 'Failed to create lead';
            toast.error(msg);
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!companyName.trim()) {
            toast.error('Company name is required');
            return;
        }
        createLead.mutate({
            company_name: companyName,
            source: source,
            stage: stage,
            assigned_to_id: assignedToId || null,
        });
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Add New Lead">
            <form onSubmit={handleSubmit} className="space-y-5">
                <div className="space-y-2">
                    <label className="text-[10px] font-black uppercase text-slate-500 tracking-widest flex items-center gap-2 px-1">
                        <Building2 className="w-3 h-3" />
                        Company Name
                    </label>
                    <Input
                        placeholder="e.g. Acme Corp"
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        className="bg-slate-950 border-slate-800 focus:border-indigo-500/50 h-11"
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-[10px] font-black uppercase text-slate-500 tracking-widest flex items-center gap-2 px-1">
                            <Globe className="w-3 h-3" />
                            Source
                        </label>
                        <select
                            value={source}
                            onChange={(e) => setSource(e.target.value)}
                            className="w-full h-11 bg-slate-950 border border-slate-800 rounded-lg px-3 text-sm text-slate-200 outline-none focus:border-indigo-500 transition-colors"
                        >
                            {LEAD_SOURCES.map((s) => (
                                <option key={s.value} value={s.value}>
                                    {s.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="space-y-2">
                        <label className="text-[10px] font-black uppercase text-slate-500 tracking-widest flex items-center gap-2 px-1">
                            <UserPlus className="w-3 h-3" />
                            Initial Stage
                        </label>
                        <select
                            value={stage}
                            onChange={(e) => setStage(e.target.value)}
                            className="w-full h-11 bg-slate-950 border border-slate-800 rounded-lg px-3 text-sm text-slate-200 outline-none focus:border-indigo-500 transition-colors"
                        >
                            {LEAD_STAGES.map((s) => (
                                <option key={s.value} value={s.value}>
                                    {s.label}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="text-[10px] font-black uppercase text-slate-500 tracking-widest flex items-center gap-2 px-1">
                        <Users className="w-3 h-3" />
                        Assign To (Optional)
                    </label>
                    <select
                        value={assignedToId}
                        onChange={(e) => setAssignedToId(e.target.value)}
                        className="w-full h-11 bg-slate-950 border border-slate-800 rounded-lg px-3 text-sm text-slate-200 outline-none focus:border-indigo-500 transition-colors"
                    >
                        <option value="">Leave unassigned (Pool)</option>
                        {users?.map((u) => (
                            <option key={u.id} value={u.id}>
                                {u.first_name ? `${u.first_name} ${u.last_name || ''} (${u.email})` : u.email}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800/50">
                    <Button
                        type="button"
                        variant="ghost"
                        onClick={onClose}
                        className="text-slate-400 hover:text-slate-200"
                    >
                        Cancel
                    </Button>
                    <Button
                        type="submit"
                        className="bg-indigo-500 hover:bg-indigo-600 text-white shadow-xl shadow-indigo-500/20 px-8"
                        disabled={createLead.isPending}
                    >
                        {createLead.isPending ? 'Creating...' : 'Create Lead'}
                    </Button>
                </div>
            </form>
        </Modal>
    );
}
