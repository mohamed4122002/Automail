import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import api from '../lib/api';
import { Download, CheckCircle, Filter, Mail, Clock, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';
import NotesSidebar from '../components/crm/NotesSidebar';

import { LEAD_STATUS_COLORS, LEAD_STATUS_LABELS } from '../lib/constants';

interface HumanHandlingUser {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    last_email_opened: string;
    days_since_open: number;
    lead_status: string;
    contacted: boolean;
}

const HumanHandlingList: React.FC = () => {
    const [days, setDays] = useState(30);
    const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
    const [selectedUserName, setSelectedUserName] = useState<string>('');
    const queryClient = useQueryClient();

    // Fetch human handling list
    const { data, isLoading, error } = useQuery({
        queryKey: ['human-handling-list', days],
        queryFn: async () => {
            const response = await api.get(`/users/human-handling-list?days=${days}`);
            return response.data;
        }
    });

    // Mark as contacted mutation
    const markContactedMutation = useMutation({
        mutationFn: async (userId: string) => {
            const response = await api.post(`/users/${userId}/mark-contacted`);
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['human-handling-list'] });
        },
        onError: (error: any) => {
            toast.error(`Failed to mark as contacted: ${error.response?.data?.detail || error.message}`);
        }
    });

    // Export to CSV
    const handleExport = async () => {
        try {
            const response = await api.post(`/users/human-handling-list/export?days=${days}`, {}, {
                responseType: 'blob'
            });

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `human_handling_list_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error: any) {
            toast.error(`Export failed: ${error.message}`);
        }
    };

    if (isLoading) {
        return (
            <Layout title="Human Handling List">
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
                </div>
            </Layout>
        );
    }

    if (error) {
        return (
            <Layout title="Human Handling List">
                <div className="text-red-500">Error loading human handling list.</div>
            </Layout>
        );
    }

    const users: HumanHandlingUser[] = data?.users || [];
    const total = data?.total || 0;

    return (
        <Layout title="Human Handling List">
            <div className="space-y-6 relative">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-200">Human Handling List</h1>
                        <p className="text-slate-400 mt-1">
                            Users who opened emails but didn't click - need personal follow-up
                        </p>
                    </div>

                    <Button
                        leftIcon={<Download className="w-4 h-4" />}
                        onClick={handleExport}
                    >
                        Export to CSV
                    </Button>
                </div>

                {/* Filters */}
                <Card className="p-4">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <Filter className="w-5 h-5 text-slate-400" />
                            <span className="text-sm font-medium text-slate-300">Time Period:</span>
                        </div>

                        <select
                            value={days}
                            onChange={(e) => setDays(parseInt(e.target.value))}
                            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200"
                        >
                            <option value={7}>Last 7 days</option>
                            <option value={14}>Last 14 days</option>
                            <option value={30}>Last 30 days</option>
                            <option value={60}>Last 60 days</option>
                            <option value={90}>Last 90 days</option>
                        </select>

                        <div className="ml-auto text-sm text-slate-400">
                            <strong className="text-slate-200">{total}</strong> users need follow-up
                        </div>
                    </div>
                </Card>

                {/* User List */}
                <Card>
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-slate-800">
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">User</th>
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">Email</th>
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">Last Opened</th>
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">Days Since</th>
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">Status</th>
                                    <th className="text-right p-4 text-sm font-medium text-slate-400">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="text-center p-8 text-slate-500">
                                            No users found matching criteria
                                        </td>
                                    </tr>
                                ) : (
                                    users.map((user) => (
                                        <tr key={user.id} className="border-b border-slate-800 hover:bg-slate-900/50">
                                            <td className="p-4">
                                                <div className="font-medium text-slate-200">
                                                    {user.first_name} {user.last_name}
                                                </div>
                                            </td>
                                            <td className="p-4">
                                                <div className="flex items-center gap-2 text-slate-300">
                                                    <Mail className="w-4 h-4 text-slate-500" />
                                                    {user.email}
                                                </div>
                                            </td>
                                            <td className="p-4 text-slate-300">
                                                {new Date(user.last_email_opened).toLocaleDateString()}
                                            </td>
                                            <td className="p-4">
                                                <div className="flex items-center gap-2">
                                                    <Clock className="w-4 h-4 text-slate-500" />
                                                    <span className={`text-sm ${user.days_since_open <= 3 ? 'text-emerald-400' :
                                                        user.days_since_open <= 7 ? 'text-yellow-400' :
                                                            'text-red-400'
                                                        }`}>
                                                        {user.days_since_open} days
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="p-4">
                                                <div className="flex flex-col gap-1">
                                                    <span className={`w-fit px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${LEAD_STATUS_COLORS[user.lead_status as keyof typeof LEAD_STATUS_COLORS] || 'bg-slate-800 text-slate-400'}`}>
                                                        {LEAD_STATUS_LABELS[user.lead_status as keyof typeof LEAD_STATUS_LABELS] || user.lead_status}
                                                    </span>
                                                    {user.contacted ? (
                                                        <span className="text-[10px] text-emerald-400 font-medium">✓ Contacted</span>
                                                    ) : (
                                                        <span className="text-[10px] text-amber-400 font-medium">○ Pending</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="p-4 text-right">
                                                <div className="flex items-center justify-end gap-2">
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => {
                                                            setSelectedUserId(user.id);
                                                            setSelectedUserName(`${user.first_name} ${user.last_name}`);
                                                        }}
                                                        leftIcon={<MessageSquare className="w-4 h-4" />}
                                                    >
                                                        Notes
                                                    </Button>
                                                    {!user.contacted && (
                                                        <Button
                                                            size="sm"
                                                            variant="secondary"
                                                            leftIcon={<CheckCircle className="w-4 h-4" />}
                                                            onClick={() => markContactedMutation.mutate(user.id)}
                                                            disabled={markContactedMutation.isPending}
                                                        >
                                                            Mark Contacted
                                                        </Button>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </Card>

                {/* Sidebar Overlay */}
                {selectedUserId && (
                    <NotesSidebar
                        userId={selectedUserId}
                        userName={selectedUserName}
                        onClose={() => setSelectedUserId(null)}
                    />
                )}

                {/* Info Card */}
                <Card className="p-4 bg-blue-500/5 border-blue-500/20">
                    <div className="flex items-start gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-lg">
                            <Mail className="w-5 h-5 text-blue-400" />
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold text-blue-400 mb-1">About Human Handling</h3>
                            <p className="text-sm text-slate-400">
                                These users showed interest by opening emails but didn't take action.
                                They're warm leads that need personalized outreach from your sales team.
                                Export the list and assign follow-up tasks to your team members.
                            </p>
                        </div>
                    </div>
                </Card>
            </div>
        </Layout>
    );
};

export default HumanHandlingList;
