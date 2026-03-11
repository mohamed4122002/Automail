import React, { useEffect, useState } from "react";
import axios from "axios";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/ui/Button";
import Layout from "../components/layout/Layout";
import {
    Users,
    Settings,
    BarChart3,
    ShieldCheck,
    TrendingUp,
    Target,
    Activity,
    Zap,
    MousePointerClick,
    Award,
    Briefcase,
    ChevronRight,
    Search,
    ShieldAlert,
    Calendar as CalendarIcon
} from "lucide-react";
import { ScheduleMeetingModal } from "../components/modals/ScheduleMeetingModal";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { toast } from "sonner";

interface UserInfo {
    id: string;
    email: string;
    first_name: string | null;
    last_name: string | null;
    role: string;
    roles: string[];
    manager_id: string | null;
}

interface BusinessStats {
    funnel: {
        total: number;
        hot: number;
        warm: number;
        conversion_opportunity: number;
    };
    engagement: {
        sent: number;
        open_rate: number;
        click_rate: number;
    };
    team: Array<{
        email: string;
        name: string;
        activity: number;
        role: string;
    }>;
}

const AdminPortal: React.FC = () => {
    const { token, isSuperAdmin } = useAuth();
    const [activeTab, setActiveTab] = useState<"insights" | "users">("insights");
    const [users, setUsers] = useState<UserInfo[]>([]);
    const [businessStats, setBusinessStats] = useState<BusinessStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [isMeetingModalOpen, setIsMeetingModalOpen] = useState(false);
    const [selectedUserForMeeting, setSelectedUserForMeeting] = useState<{ id: string, email: string, name: string } | null>(null);

    const userRoleValue = (role: string) => {
        const hierarchy: Record<string, number> = {
            'super_admin': 4,
            'admin': 3,
            'manager': 2,
            'sales_lead': 2,
            'team_member': 1
        };
        return hierarchy[role] || 0;
    };

    const canCurrentAssignTo = (targetRole: string) => {
        const currentUser = users.find(u => u.email === (useAuth().user as any)?.email);
        if (!currentUser) return false;

        const currentVal = userRoleValue(currentUser.role);
        const targetVal = userRoleValue(targetRole);
        return currentVal > targetVal && currentVal > 1;
    };

    const fetchAll = async () => {
        try {
            const [usersRes, businessRes] = await Promise.all([
                axios.get("/api/admin/users", { headers: { Authorization: `Bearer ${token}` } }),
                axios.get("/api/admin/business-stats", { headers: { Authorization: `Bearer ${token}` } })
            ]);
            setUsers(usersRes.data);
            setBusinessStats(businessRes.data);
        } catch (err) {
            console.error("Failed to fetch admin data", err);
            toast.error("Failed to load business intelligence data");
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
            toast.success("User role updated and synchronized");
            fetchAll();
        } catch (err: any) {
            const msg = err.response?.data?.detail || "Failed to update role";
            toast.error(msg);
        }
    };

    const handleManagerChange = async (userId: string, managerId: string | null) => {
        try {
            await axios.patch(`/api/admin/users/${userId}/manager`, { manager_id: managerId }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            toast.success("Reporting hierarchy updated");
            fetchAll();
        } catch (err: any) {
            const msg = err.response?.data?.detail || "Failed to update manager";
            toast.error(msg);
        }
    };

    const getRoleBadgeColor = (role: string) => {
        switch (role) {
            case 'super_admin': return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
            case 'admin': return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
            case 'manager': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
            case 'sales_lead': return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
            default: return 'bg-slate-800 text-slate-400 border-slate-700/50';
        }
    };

    const filteredUsers = users.filter(u =>
        u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (u.first_name || "").toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (loading) return (
        <Layout title="Business Intelligence">
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="flex flex-col items-center gap-4">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
                    <p className="text-slate-500 text-sm animate-pulse">Aggregating real-time database reflections...</p>
                </div>
            </div>
        </Layout>
    );

    return (
        <Layout title="Admin Command Center">
            <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">

                {/* Visual Section Header */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-8">
                    <div>
                        <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-3">
                            <Briefcase className="w-8 h-8 text-indigo-500" />
                            Business Awareness
                        </h1>
                        <p className="text-slate-500 mt-1">High-level strategic overview and team orchestration.</p>
                    </div>

                    <div className="flex bg-slate-900/50 p-1 rounded-2xl border border-slate-800 backdrop-blur-md">
                        <button
                            onClick={() => setActiveTab("insights")}
                            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === "insights" ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20" : "text-slate-400 hover:text-slate-200"}`}
                        >
                            Business Insights
                        </button>
                        <button
                            onClick={() => setActiveTab("users")}
                            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === "users" ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20" : "text-slate-400 hover:text-slate-200"}`}
                        >
                            Team Roles
                        </button>
                    </div>
                </div>

                {activeTab === "insights" && (
                    <div className="space-y-8">
                        {/* KPI Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <Card className="bg-gradient-to-br from-indigo-500/10 to-transparent border-slate-800/50 relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
                                    <Target className="w-24 h-24" />
                                </div>
                                <CardContent className="pt-6">
                                    <p className="text-xs font-bold text-indigo-400 uppercase tracking-widest mb-1">Lead Funnel</p>
                                    <div className="text-4xl font-black text-white">{businessStats?.funnel.total}</div>
                                    <div className="flex items-center gap-2 mt-4">
                                        <Badge className="bg-rose-500/20 text-rose-400 border-0">{businessStats?.funnel.hot} Hot</Badge>
                                        <Badge className="bg-amber-500/20 text-amber-400 border-0">{businessStats?.funnel.warm} Warm</Badge>
                                    </div>
                                    <p className="text-[10px] text-slate-500 mt-4 italic">Total growth potential based on current database state.</p>
                                </CardContent>
                            </Card>

                            <Card className="bg-gradient-to-br from-emerald-500/10 to-transparent border-slate-800/50 relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
                                    <TrendingUp className="w-24 h-24" />
                                </div>
                                <CardContent className="pt-6">
                                    <p className="text-xs font-bold text-emerald-400 uppercase tracking-widest mb-1">Engagement Pulse</p>
                                    <div className="text-4xl font-black text-white">{businessStats?.engagement.open_rate}%</div>
                                    <div className="flex items-center gap-4 mt-4">
                                        <div className="flex flex-col">
                                            <span className="text-[10px] text-slate-500 uppercase">Click Rate</span>
                                            <span className="text-emerald-400 font-bold">{businessStats?.engagement.click_rate}%</span>
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-[10px] text-slate-500 uppercase">Volume</span>
                                            <span className="text-slate-300 font-bold">{businessStats?.engagement.sent}</span>
                                        </div>
                                    </div>
                                    <p className="text-[10px] text-slate-500 mt-4 italic">Aggregated interaction metrics across all active campaigns.</p>
                                </CardContent>
                            </Card>

                            <Card className="bg-gradient-to-br from-amber-500/10 to-transparent border-slate-800/50 relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
                                    <Activity className="w-24 h-24" />
                                </div>
                                <CardContent className="pt-6">
                                    <p className="text-xs font-bold text-amber-400 uppercase tracking-widest mb-1">Conversion Opps</p>
                                    <div className="text-4xl font-black text-white">{businessStats?.funnel.conversion_opportunity}</div>
                                    <div className="flex space-x-1 mt-4">
                                        {Array.from({ length: 10 }).map((_, i) => (
                                            <div key={i} className={`h-1 w-full rounded-full ${i < 7 ? 'bg-amber-500' : 'bg-slate-800'}`} />
                                        ))}
                                    </div>
                                    <p className="text-[10px] text-slate-500 mt-4 italic">Quality leads ready for sales lead handoff.</p>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Team Leaderboard */}
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                            <div className="lg:col-span-2 space-y-6">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                        <Award className="w-5 h-5 text-indigo-400" />
                                        Team Productivity Leaderboard (Last 30 Days)
                                    </h3>
                                    <span className="text-xs text-slate-500 underline cursor-pointer hover:text-indigo-400">View Full Report</span>
                                </div>

                                <div className="space-y-4">
                                    {businessStats?.team.map((member, i) => (
                                        <div key={member.email} className="bg-slate-900/40 border border-slate-800/50 p-4 rounded-2xl flex items-center justify-between hover:bg-slate-800/40 transition-all group">
                                            <div className="flex items-center gap-4">
                                                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center font-bold text-indigo-400 text-xs">
                                                    #{i + 1}
                                                </div>
                                                <div>
                                                    <div className="text-sm font-bold text-white group-hover:text-indigo-300 transition-colors">{member.name}</div>
                                                    <div className="text-[10px] text-slate-500 uppercase tracking-tighter">{member.role.replace('_', ' ')}</div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-8">
                                                <div className="text-right">
                                                    <div className="text-sm font-bold text-white">{member.activity}</div>
                                                    <div className="text-[10px] text-slate-500 uppercase">Activities</div>
                                                </div>
                                                <ChevronRight className="w-4 h-4 text-slate-700 group-hover:text-indigo-500 transition-colors" />
                                            </div>
                                        </div>
                                    ))}
                                    {(!businessStats?.team || businessStats.team.length === 0) && (
                                        <div className="text-center py-12 bg-slate-900/20 rounded-2xl border border-dashed border-slate-800">
                                            <p className="text-slate-500 italic text-sm">No activity recorded in the last 30 days.</p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="space-y-6">
                                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                    <Zap className="w-5 h-5 text-amber-400" />
                                    Awareness Actions
                                </h3>
                                <div className="space-y-3">
                                    <Button className="w-full justify-start gap-3 bg-indigo-500 hover:bg-indigo-600 text-white border-0 shadow-lg shadow-indigo-500/20 py-6">
                                        <TrendingUp className="w-4 h-4" />
                                        Export Business ROI Report
                                    </Button>
                                    <Button variant="outline" className="w-full justify-start gap-3 border-slate-800 hover:bg-slate-800/50 text-slate-300 py-6">
                                        <Users className="w-4 h-4" />
                                        Bulk Adjust Team Roles
                                    </Button>
                                    <Card className="bg-slate-950/50 border-slate-800 p-4 mt-6">
                                        <div className="flex items-center gap-3 mb-2">
                                            <ShieldAlert className="w-4 h-4 text-rose-500" />
                                            <span className="text-xs font-bold text-white text-rose-500">Notice</span>
                                        </div>
                                        <p className="text-[10px] text-slate-500 leading-relaxed italic">
                                            "A 5% increase in lead conversion was detected in the last 48 hours. Consider scaling Sales Lead involvement."
                                        </p>
                                    </Card>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === "users" && (
                    <div className="space-y-6">
                        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                            <div>
                                <h2 className="text-xl font-black text-white">Team Orchestration</h2>
                                <p className="text-sm text-slate-500">Assign granular roles to reflect your organizational hierarchy.</p>
                            </div>

                            <div className="relative w-full md:w-80">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input
                                    type="text"
                                    placeholder="Search by name or email..."
                                    className="w-full bg-slate-900/50 border border-slate-800 rounded-xl py-2 pl-10 pr-4 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-md">
                            <table className="w-full text-left">
                                <thead className="bg-slate-950/50 border-b border-slate-800">
                                    <tr className="text-[10px] uppercase font-black text-slate-500 tracking-widest">
                                        <th className="px-6 py-4">Individual</th>
                                        <th className="px-6 py-4">Database Reflection</th>
                                        <th className="px-6 py-4">Reports To (Manager)</th>
                                        <th className="px-6 py-4 text-right">Administrative Action</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800/50">
                                    {filteredUsers.map(u => (
                                        <tr key={u.id} className="group hover:bg-slate-800/20 transition-all">
                                            <td className="px-6 py-5">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center font-black text-indigo-400 border border-slate-700/50 group-hover:scale-110 transition-transform">
                                                        {u.email[0].toUpperCase()}
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-bold text-slate-100">{u.email}</div>
                                                        <div className="text-[10px] text-slate-500 font-medium">Joined {new Date().toLocaleDateString()}</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-5">
                                                <Badge className={getRoleBadgeColor(u.role)}>
                                                    {u.role.replace('_', ' ')}
                                                </Badge>
                                            </td>
                                            <td className="px-6 py-5">
                                                {isSuperAdmin ? (
                                                    <select
                                                        className="bg-slate-950 border border-slate-800 text-xs font-bold rounded-xl px-4 py-2 outline-none focus:border-indigo-500 transition-colors shadow-inner w-full"
                                                        value={u.manager_id || ""}
                                                        onChange={(e) => handleManagerChange(u.id, e.target.value || null)}
                                                    >
                                                        <option value="">No Manager</option>
                                                        {users.filter(potential =>
                                                            ['super_admin', 'admin', 'manager'].includes(potential.role) &&
                                                            potential.id !== u.id
                                                        ).map(manager => (
                                                            <option key={manager.id} value={manager.id}>
                                                                {manager.first_name ? `${manager.first_name} (${manager.email})` : manager.email}
                                                            </option>
                                                        ))}
                                                    </select>
                                                ) : (
                                                    <div className="text-xs text-slate-400">
                                                        {users.find(m => m.id === u.manager_id)?.email || 'None'}
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-6 py-5 text-right">
                                                <div className="flex items-center justify-end gap-3">
                                                    {canCurrentAssignTo(u.role) && (
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => {
                                                                setSelectedUserForMeeting({
                                                                    id: u.id,
                                                                    email: u.email,
                                                                    name: `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.email
                                                                });
                                                                setIsMeetingModalOpen(true);
                                                            }}
                                                            className="flex items-center gap-2 border-blue-500/20 text-blue-400 hover:bg-blue-500/10"
                                                        >
                                                            <CalendarIcon className="w-3 h-3" />
                                                            Schedule
                                                        </Button>
                                                    )}

                                                    {isSuperAdmin ? (
                                                        <select
                                                            className="bg-slate-950 border border-slate-800 text-xs font-bold rounded-xl px-4 py-2 outline-none focus:border-indigo-500 transition-colors shadow-inner"
                                                            value={u.role}
                                                            onChange={(e) => handleRoleChange(u.id, e.target.value)}
                                                        >
                                                            <option value="super_admin">Super Admin</option>
                                                            <option value="admin">Admin</option>
                                                            <option value="manager">Manager</option>
                                                            <option value="sales_lead">Sales Lead</option>
                                                            <option value="team_member">Team Member</option>
                                                        </select>
                                                    ) : (
                                                        <span className="text-xs text-slate-600 font-bold italic">Orchestration Restricted</span>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {filteredUsers.length === 0 && (
                                <div className="py-20 text-center">
                                    <p className="text-slate-500 text-sm">No members matching your criteria were found in the database.</p>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            <ScheduleMeetingModal
                isOpen={isMeetingModalOpen}
                onClose={() => {
                    setIsMeetingModalOpen(false);
                    setSelectedUserForMeeting(null);
                }}
                assignee={selectedUserForMeeting}
            />
        </Layout>
    );
};

export default AdminPortal;
