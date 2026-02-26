import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import api from '../lib/api';
import {
    User as UserIcon,
    Mail,
    Calendar,
    TrendingUp,
    Search,
    Download,
    UserPlus,
    BarChart3,
    Activity
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { toast } from 'sonner';
import { AddUserModal } from '../components/users/AddUserModal';
import { ContactImport } from '../components/contacts/ContactImport';
import { LEAD_STATUS, LEAD_STATUS_COLORS, LEAD_STATUS_LABELS } from '../lib/constants';

interface User {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    created_at: string;
    lead_status: string;
    role?: string;
    ltv?: number;
    engagement_score?: number;
}

const Users: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedSegment, setSelectedSegment] = useState<string>('all');
    const [showAddUserModal, setShowAddUserModal] = useState(false);
    const [activeTab, setActiveTab] = useState<'list' | 'import'>('list');

    const { data: users, isLoading } = useQuery({
        queryKey: ['users'],
        queryFn: async () => {
            const res = await api.get<User[]>('/users');
            return res.data;
        },
        retry: false
    });

    // Calculate stats
    const stats = users ? {
        total: users.length,
        active: users.filter(u => u.engagement_score && u.engagement_score > 50).length,
        newThisMonth: users.filter(u => {
            const created = new Date(u.created_at);
            const now = new Date();
            return created.getMonth() === now.getMonth() && created.getFullYear() === now.getFullYear();
        }).length,
        avgEngagement: users.reduce((acc, u) => acc + (u.engagement_score || 0), 0) / users.length || 0
    } : { total: 0, active: 0, newThisMonth: 0, avgEngagement: 0 };

    // Filter users
    const filteredUsers = users?.filter(user => {
        const matchesSearch = searchTerm === '' ||
            user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
            `${user.first_name} ${user.last_name}`.toLowerCase().includes(searchTerm.toLowerCase());

        const matchesSegment = selectedSegment === 'all' || user.lead_status === selectedSegment;

        return matchesSearch && matchesSegment;
    }) || [];

    // Export to CSV
    const handleExport = () => {
        if (!filteredUsers.length) {
            toast.error('No users to export');
            return;
        }

        const headers = ['Name', 'Email', 'Engagement', 'LTV', 'Joined'];
        const csvData = filteredUsers.map(user => [
            `${user.first_name} ${user.last_name}`,
            user.email,
            `${user.engagement_score || 0}%`,
            `$${(user.ltv || 0).toFixed(2)}`,
            new Date(user.created_at).toLocaleDateString()
        ]);

        const csvContent = [
            headers.join(','),
            ...csvData.map(row => row.join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `users-export-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    };

    return (
        <Layout title="Users">
            <div className="space-y-6">
                {/* Tabs */}
                <div className="flex items-center gap-4 border-b border-slate-800">
                    <button
                        onClick={() => setActiveTab('list')}
                        className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${activeTab === 'list' ? 'text-indigo-400 border-indigo-500' : 'text-slate-500 border-transparent hover:text-slate-300'
                            }`}
                    >
                        User List
                    </button>
                    <button
                        onClick={() => setActiveTab('import')}
                        className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${activeTab === 'import' ? 'text-indigo-400 border-indigo-500' : 'text-slate-500 border-transparent hover:text-slate-300'
                            }`}
                    >
                        Import Contacts
                    </button>
                </div>

                {activeTab === 'list' ? (
                    <>
                        {/* Stats Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <Card className="p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-slate-400">Total Users</p>
                                        <p className="text-2xl font-bold text-slate-200">{stats.total}</p>
                                    </div>
                                    <div className="p-3 bg-indigo-500/10 rounded-lg">
                                        <UserIcon className="w-6 h-6 text-indigo-400" />
                                    </div>
                                </div>
                            </Card>

                            <Card className="p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-slate-400">Active Users</p>
                                        <p className="text-2xl font-bold text-slate-200">{stats.active}</p>
                                    </div>
                                    <div className="p-3 bg-emerald-500/10 rounded-lg">
                                        <Activity className="w-6 h-6 text-emerald-400" />
                                    </div>
                                </div>
                            </Card>

                            <Card className="p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-slate-400">New This Month</p>
                                        <p className="text-2xl font-bold text-slate-200">{stats.newThisMonth}</p>
                                    </div>
                                    <div className="p-3 bg-cyan-500/10 rounded-lg">
                                        <TrendingUp className="w-6 h-6 text-cyan-400" />
                                    </div>
                                </div>
                            </Card>

                            <Card className="p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-slate-400">Avg Engagement</p>
                                        <p className="text-2xl font-bold text-slate-200">{Math.round(stats.avgEngagement)}%</p>
                                    </div>
                                    <div className="p-3 bg-yellow-500/10 rounded-lg">
                                        <BarChart3 className="w-6 h-6 text-yellow-400" />
                                    </div>
                                </div>
                            </Card>
                        </div>

                        {/* Filters and Actions */}
                        <Card className="p-4">
                            <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
                                <div className="flex gap-2 w-full md:w-auto">
                                    <div className="relative flex-1 md:w-64">
                                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                                        <input
                                            type="text"
                                            placeholder="Search users..."
                                            value={searchTerm}
                                            onChange={(e) => setSearchTerm(e.target.value)}
                                            className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-10 pr-3 py-2 text-sm text-slate-200"
                                        />
                                    </div>

                                    <select
                                        value={selectedSegment}
                                        onChange={(e) => setSelectedSegment(e.target.value)}
                                        className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200"
                                    >
                                        <option value="all">All Users</option>
                                        <option value={LEAD_STATUS.HOT}>Hot Leads</option>
                                        <option value={LEAD_STATUS.WARM}>Warm Leads</option>
                                        <option value={LEAD_STATUS.COLD}>Cold Leads</option>
                                        <option value={LEAD_STATUS.NEW}>New Contacts</option>
                                    </select>
                                </div>

                                <div className="flex gap-2">
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        leftIcon={<Download className="w-4 h-4" />}
                                        onClick={handleExport}
                                    >
                                        Export
                                    </Button>
                                    <Button
                                        size="sm"
                                        leftIcon={<UserPlus className="w-4 h-4" />}
                                        onClick={() => setShowAddUserModal(true)}
                                    >
                                        Add User
                                    </Button>
                                </div>
                            </div>
                        </Card>

                        {/* Users Table */}
                        <Card>
                            <div className="overflow-x-auto">
                                <table className="w-full text-left text-sm text-slate-400">
                                    <thead className="bg-slate-900 text-slate-200 uppercase font-medium text-xs">
                                        <tr>
                                            <th className="px-6 py-3">User</th>
                                            <th className="px-6 py-3">Email</th>
                                            <th className="px-6 py-3">Engagement</th>
                                            <th className="px-6 py-3">Status</th>
                                            <th className="px-6 py-3">LTV</th>
                                            <th className="px-6 py-3">Joined</th>
                                            <th className="px-6 py-3">Action</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-800">
                                        {isLoading ? (
                                            <tr><td colSpan={6} className="px-6 py-4 text-center">Loading...</td></tr>
                                        ) : filteredUsers.map((user) => (
                                            <tr key={user.id} className="hover:bg-slate-800/50 transition-colors">
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-3">
                                                        <div className="p-2 bg-slate-800 rounded-full">
                                                            <UserIcon className="w-4 h-4 text-slate-400" />
                                                        </div>
                                                        <span className="font-medium text-slate-200">
                                                            {user.first_name} {user.last_name}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-2">
                                                        <Mail className="w-4 h-4 text-slate-500" />
                                                        {user.email}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-2">
                                                        <div className="w-24 bg-slate-700 rounded-full h-2">
                                                            <div
                                                                className="bg-indigo-500 h-2 rounded-full"
                                                                style={{ width: `${user.engagement_score || 0}%` }}
                                                            />
                                                        </div>
                                                        <span className="text-xs">{user.engagement_score || 0}%</span>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase border ${LEAD_STATUS_COLORS[user.lead_status as keyof typeof LEAD_STATUS_COLORS] || 'bg-slate-800 text-slate-400'}`}>
                                                        {LEAD_STATUS_LABELS[user.lead_status as keyof typeof LEAD_STATUS_LABELS] || user.lead_status}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className="text-emerald-400 font-medium">
                                                        ${(user.ltv || 0).toFixed(2)}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-2">
                                                        <Calendar className="w-4 h-4 text-slate-500" />
                                                        {new Date(user.created_at).toLocaleDateString()}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <Link
                                                        to={`/users/${user.id}`}
                                                        className="text-indigo-400 hover:text-indigo-300 font-medium"
                                                    >
                                                        View Profile
                                                    </Link>
                                                </td>
                                            </tr>
                                        ))}
                                        {!isLoading && filteredUsers.length === 0 && (
                                            <tr><td colSpan={6} className="px-6 py-8 text-center text-slate-500">No users found.</td></tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </Card>
                    </>
                ) : (
                    <ContactImport />
                )}

                {/* Add User Modal */}
                <AddUserModal
                    isOpen={showAddUserModal}
                    onClose={() => setShowAddUserModal(false)}
                />
            </div>
        </Layout>
    );
};

export default Users;
