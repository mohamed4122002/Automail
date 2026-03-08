import React, { useEffect, useState } from "react";
import axios from "axios";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/ui/Button";

interface UserInfo {
    id: string;
    email: string;
    first_name: string | null;
    last_name: string | null;
    role: string;
    roles: string[];
}

const AdminPortal: React.FC = () => {
    const { token } = useAuth();
    const [users, setUsers] = useState<UserInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState<any>(null);

    const fetchAll = async () => {
        try {
            const [usersRes, statsRes] = await Promise.all([
                axios.get("/api/admin/users", { headers: { Authorization: `Bearer ${token}` } }),
                axios.get("/api/admin/stats", { headers: { Authorization: `Bearer ${token}` } })
            ]);
            setUsers(usersRes.data);
            setStats(statsRes.data);
        } catch (err) {
            console.error("Failed to fetch admin data", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAll();
    }, [token]);

    const handleRoleChange = async (userId: string, newRole: string) => {
        try {
            await axios.patch(`/api/admin/users/${userId}/role`, { role: newRole }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            fetchAll();
        } catch (err) {
            alert("Failed to update role");
        }
    };

    if (loading) return <div className="p-8 text-slate-400">Loading admin data...</div>;

    return (
        <div className="p-8 bg-[#020617] min-h-screen text-slate-200">
            <h1 className="text-3xl font-bold mb-8 bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
                Admin Portal
            </h1>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
                {stats && Object.entries(stats).map(([key, value]: [string, any]) => (
                    <div key={key} className="bg-slate-900/50 border border-slate-800 p-6 rounded-2xl">
                        <p className="text-slate-500 text-sm uppercase tracking-wider mb-1">{key.replace('_', ' ')}</p>
                        <p className="text-2xl font-bold text-white">{value}</p>
                    </div>
                ))}
            </div>

            {/* User Management Table */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-slate-800">
                    <h2 className="text-xl font-semibold">User Management</h2>
                </div>
                <table className="w-full text-left">
                    <thead>
                        <tr className="bg-slate-950/50 text-slate-400 text-sm uppercase tracking-wider">
                            <th className="px-6 py-4 font-medium">Email</th>
                            <th className="px-6 py-4 font-medium">Name</th>
                            <th className="px-6 py-4 font-medium">Current Role</th>
                            <th className="px-6 py-4 font-medium">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        {users.map(u => (
                            <tr key={u.id} className="hover:bg-slate-800/30 transition-colors">
                                <td className="px-6 py-4 font-medium text-white">{u.email}</td>
                                <td className="px-6 py-4 text-slate-400">{u.first_name} {u.last_name}</td>
                                <td className="px-6 py-4">
                                    <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${u.role === 'admin' ? 'bg-indigo-500/20 text-indigo-400' :
                                            u.role === 'sales_lead' ? 'bg-cyan-500/20 text-cyan-400' :
                                                'bg-slate-800 text-slate-500'
                                        }`}>
                                        {u.role}
                                    </span>
                                </td>
                                <td className="px-6 py-4 space-x-2">
                                    <select
                                        className="bg-slate-950 border border-slate-800 text-xs rounded px-2 py-1 outline-none focus:border-indigo-500"
                                        value={u.role}
                                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                                    >
                                        <option value="admin">Admin</option>
                                        <option value="sales_lead">Sales Lead</option>
                                        <option value="team_member">Team Member</option>
                                    </select>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default AdminPortal;
