import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import Layout from "../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { ArrowLeft, Mail, Clock, Calendar, MessageSquare, Flame, TrendingUp, Snowflake, Zap, XCircle, UserPlus, CheckCircle2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";

const LeadDetail: React.FC = () => {
    const { id } = useParams();
    const queryClient = useQueryClient();
    const [noteContent, setNoteContent] = useState("");

    // Fetch Lead Details
    const { data: lead, isLoading: leadLoading } = useQuery({
        queryKey: ['lead', id],
        queryFn: async () => {
            const res = await api.get(`/leads/${id}`);
            return res.data;
        },
        enabled: !!id,
    });

    // Fetch Activity Timeline
    const { data: activityData, isLoading: activityLoading } = useQuery({
        queryKey: ['lead-activity', id],
        queryFn: async () => {
            const res = await api.get(`/leads/${id}/activity`);
            return res.data;
        },
        enabled: !!id,
    });

    const { data: contactLists } = useQuery({
        queryKey: ['contact-lists'],
        queryFn: async () => {
            const res = await api.get('/contacts/lists');
            return res.data;
        }
    });

    const { data: users } = useQuery({
        queryKey: ['users'],
        queryFn: async () => {
            const res = await api.get('/users');
            return res.data;
        }
    });

    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editForm, setEditForm] = useState({
        email: "",
        first_name: "",
        last_name: "",
        lead_status: "",
        lead_score: 0,
        assigned_to_id: "" as string | null,
        contact_list_id: "",
        attributes: {} as Record<string, any>
    });

    // Initialize edit form when lead data loads
    React.useEffect(() => {
        if (lead) {
            setEditForm({
                email: lead.contact_email || "",
                first_name: lead.contact_first_name || "",
                last_name: lead.contact_last_name || "",
                lead_status: lead.lead_status || "new",
                lead_score: lead.lead_score || 0,
                assigned_to_id: lead.assigned_to_id || null,
                contact_list_id: lead.contact_list_id || "",
                attributes: lead.attributes || {}
            });
        }
    }, [lead]);

    // ... (rest of mutations as is)

    // Helper to update attributes
    const handleAttributeChange = (key: string, value: any) => {
        setEditForm(prev => ({
            ...prev,
            attributes: {
                ...prev.attributes,
                [key]: value
            }
        }));
    };

    const addAttribute = () => {
        const key = prompt("Attribute name (e.g. Phone, Company):");
        if (key && !editForm.attributes[key]) {
            handleAttributeChange(key, "");
        }
    };

    const removeAttribute = (key: string) => {
        const newAttrs = { ...editForm.attributes };
        delete newAttrs[key];
        setEditForm(prev => ({ ...prev, attributes: newAttrs }));
    };

    const createNoteMutation = useMutation({
        mutationFn: async (content: string) => {
            return await api.post(`/leads/${id}/notes`, { content });
        },
        onSuccess: () => {
            setNoteContent("");
            queryClient.invalidateQueries({ queryKey: ['lead-activity', id] });
        }
    });

    const updateLeadMutation = useMutation({
        mutationFn: async (data: typeof editForm) => {
            return await api.patch(`/leads/${id}`, data);
        },
        onSuccess: () => {
            setIsEditModalOpen(false);
            queryClient.invalidateQueries({ queryKey: ['lead', id] });
            queryClient.invalidateQueries({ queryKey: ['lead-activity', id] });
        }
    });

    const updateStatusMutation = useMutation({
        mutationFn: async (status: string) => {
            return await api.patch(`/leads/${id}`, { lead_status: status });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['lead', id] });
            queryClient.invalidateQueries({ queryKey: ['lead-activity', id] });
        }
    });

    if (leadLoading) return <Layout><div className="p-8 text-center text-slate-400">Loading profile...</div></Layout>;
    if (!lead) return <Layout><div className="p-8 text-center text-red-400">Lead not found</div></Layout>;

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

    return (
        <Layout title="Lead Profile">
            {isEditModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
                    <Card className="w-full max-w-2xl bg-slate-900 border-2 border-slate-800 shadow-2xl rounded-3xl">
                        <CardHeader className="border-b border-slate-800 pb-6">
                            <CardTitle className="text-2xl font-black text-slate-100 italic tracking-tight">EDIT LEAD PROFILE</CardTitle>
                        </CardHeader>
                        <CardContent className="p-8 overflow-y-auto max-h-[80vh]">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                {/* Left Section: Basic Info */}
                                <div className="space-y-6">
                                    <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em]">Contact Information</h3>
                                    <div>
                                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Email Address</label>
                                        <input
                                            type="email"
                                            className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                            value={editForm.email}
                                            onChange={e => setEditForm({ ...editForm, email: e.target.value })}
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">First Name</label>
                                            <input
                                                type="text"
                                                className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                                value={editForm.first_name}
                                                onChange={e => setEditForm({ ...editForm, first_name: e.target.value })}
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Last Name</label>
                                            <input
                                                type="text"
                                                className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                                value={editForm.last_name}
                                                onChange={e => setEditForm({ ...editForm, last_name: e.target.value })}
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Contact List</label>
                                        <select
                                            className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold appearance-none"
                                            value={editForm.contact_list_id}
                                            onChange={e => setEditForm({ ...editForm, contact_list_id: e.target.value })}
                                        >
                                            {contactLists?.map((list: any) => (
                                                <option key={list.id} value={list.id}>{list.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                {/* Right Section: Lead Props */}
                                <div className="space-y-6">
                                    <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em]">Lead Management</h3>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Status</label>
                                            <select
                                                className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold appearance-none"
                                                value={editForm.lead_status}
                                                onChange={e => setEditForm({ ...editForm, lead_status: e.target.value })}
                                            >
                                                <option value="new">New</option>
                                                <option value="warm">Warm</option>
                                                <option value="hot">Hot</option>
                                                <option value="cold">Cold</option>
                                                <option value="unsubscribed">Unsubscribed</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Score</label>
                                            <input
                                                type="number"
                                                className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                                value={editForm.lead_score}
                                                onChange={e => setEditForm({ ...editForm, lead_score: parseInt(e.target.value) || 0 })}
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Assigned To</label>
                                        <select
                                            className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold appearance-none"
                                            value={editForm.assigned_to_id || ""}
                                            onChange={e => setEditForm({ ...editForm, assigned_to_id: e.target.value || null })}
                                        >
                                            <option value="">Unassigned</option>
                                            {users?.map((u: any) => (
                                                <option key={u.user.id} value={u.user.id}>{u.user.email}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                            </div>

                            {/* Attributes Section */}
                            <div className="mt-8 pt-8 border-t border-slate-800 space-y-6">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em]">Custom attributes</h3>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="text-[10px] font-black hover:text-indigo-400"
                                        onClick={addAttribute}
                                    >
                                        + ADD ATTRIBUTE
                                    </Button>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {Object.entries(editForm.attributes).map(([key, value]) => (
                                        <div key={key} className="relative group">
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">{key}</label>
                                            <div className="flex gap-2">
                                                <input
                                                    type="text"
                                                    className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                                    value={value}
                                                    onChange={e => handleAttributeChange(key, e.target.value)}
                                                />
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="rounded-xl text-slate-600 hover:text-red-400 hover:bg-red-400/10"
                                                    onClick={() => removeAttribute(key)}
                                                >
                                                    <XCircle className="w-4 h-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                    {Object.keys(editForm.attributes).length === 0 && (
                                        <p className="text-xs text-slate-600 italic font-medium">No custom attributes defined.</p>
                                    )}
                                </div>
                            </div>

                            <div className="flex justify-end gap-4 mt-12 pt-8 border-t border-slate-800">
                                <Button
                                    variant="secondary"
                                    className="rounded-2xl px-8 py-6 font-black border-slate-800"
                                    onClick={() => setIsEditModalOpen(false)}
                                >
                                    CANCEL
                                </Button>
                                <Button
                                    className="rounded-2xl px-8 py-6 bg-indigo-500 hover:bg-indigo-400 font-black shadow-2xl shadow-indigo-500/20"
                                    onClick={() => updateLeadMutation.mutate(editForm)}
                                    isLoading={updateLeadMutation.isPending}
                                    disabled={!editForm.email}
                                >
                                    SAVE CHANGES
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 p-8">
                {/* Left Column: Lead Info */}
                <div className="lg:col-span-1 space-y-6">
                    <Link to="/leads">
                        <Button variant="ghost" size="sm" className="mb-4 text-slate-400 hover:text-white pl-0">
                            <ArrowLeft className="w-4 h-4 mr-2" />
                            Back to Leads
                        </Button>
                    </Link>

                    <Card className="border-2 border-slate-800/60 bg-slate-900/40">
                        <CardContent className="flex flex-col items-center pt-8 pb-8">
                            <div className={`w-24 h-24 rounded-3xl bg-gradient-to-br ${getStatusColor(lead.lead_status)} flex items-center justify-center shadow-2xl mb-6`}>
                                {getStatusIcon(lead.lead_status)}
                            </div>

                            <h2 className="text-2xl font-black text-slate-100 text-center">
                                {lead.contact_first_name || lead.contact_last_name
                                    ? `${lead.contact_first_name || ''} ${lead.contact_last_name || ''}`.trim()
                                    : 'Unknown Lead'}
                            </h2>
                            <p className="text-slate-400 font-medium mb-6">{lead.contact_list_name}</p>

                            <div className="flex gap-2 mb-8">
                                <span className="px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-xs font-bold text-slate-300 uppercase tracking-wider">
                                    Score: {lead.lead_score}
                                </span>
                                <span className={`px-3 py-1 rounded-full border text-xs font-bold uppercase tracking-wider ${lead.lead_status === 'hot' ? 'bg-red-500/10 border-red-500/20 text-red-400' :
                                    lead.lead_status === 'warm' ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' :
                                        'bg-slate-800 border-slate-700 text-slate-400'
                                    }`}>
                                    {lead.lead_status}
                                </span>
                            </div>

                            <div className="w-full space-y-4 border-t border-slate-800/60 pt-6">
                                <div className="flex items-center text-sm font-medium text-slate-300">
                                    <Mail className="w-4 h-4 mr-3 text-slate-500" />
                                    {lead.contact_email}
                                </div>
                                <div className="flex items-center text-sm font-medium text-slate-300">
                                    <Calendar className="w-4 h-4 mr-3 text-slate-500" />
                                    Created {new Date(lead.created_at).toLocaleDateString()}
                                </div>
                                {lead.last_contacted_at && (
                                    <div className="flex items-center text-sm font-medium text-slate-300">
                                        <Clock className="w-4 h-4 mr-3 text-slate-500" />
                                        Last Contact: {new Date(lead.last_contacted_at).toLocaleDateString()}
                                    </div>
                                )}
                                {lead.assigned_to_name ? (
                                    <div className="flex items-center text-sm font-medium text-slate-300">
                                        <UserPlus className="w-4 h-4 mr-3 text-slate-500" />
                                        Assigned to {lead.assigned_to_name}
                                    </div>
                                ) : (
                                    <div className="flex items-center text-sm font-medium text-slate-500 italic">
                                        <UserPlus className="w-4 h-4 mr-3" />
                                        Unassigned
                                    </div>
                                )}
                            </div>

                            <div className="w-full mt-8 grid grid-cols-2 gap-3">
                                <Button
                                    className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold"
                                    onClick={() => window.location.href = `mailto:${lead.contact_email}`}
                                >
                                    Email
                                </Button>
                                <Button
                                    variant="secondary"
                                    className="font-bold border-slate-700"
                                    onClick={() => setIsEditModalOpen(true)}
                                >
                                    Edit
                                </Button>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Status Actions */}
                    <Card className="border-2 border-slate-800/60 bg-slate-900/40">
                        <CardHeader><CardTitle className="text-sm uppercase tracking-widest text-slate-500">Quick Actions</CardTitle></CardHeader>
                        <CardContent className="grid grid-cols-2 gap-3">
                            {['new', 'warm', 'hot', 'cold'].map(s => (
                                <Button
                                    key={s}
                                    variant="ghost"
                                    onClick={() => updateStatusMutation.mutate(s)}
                                    disabled={lead.lead_status === s}
                                    className={`
                                        justify-start font-bold capitalize
                                        ${lead.lead_status === s ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' : 'text-slate-400 hover:text-slate-200'}
                                    `}
                                >
                                    {lead.lead_status === s && <CheckCircle2 className="w-4 h-4 mr-2" />}
                                    Mark {s}
                                </Button>
                            ))}
                        </CardContent>
                    </Card>
                </div>

                {/* Right Column: Timeline & Activity */}
                <div className="lg:col-span-2 space-y-6">
                    <Card className="h-full border-2 border-slate-800/60 bg-slate-900/40">
                        <CardHeader className="flex flex-row items-center justify-between border-b border-slate-800/60 pb-6">
                            <CardTitle className="text-xl font-black text-slate-100 italic">ACTIVITY TIMELINE</CardTitle>
                        </CardHeader>
                        <CardContent className="pt-8 flex-1 flex flex-col">
                            {/* Note Input */}
                            <div className="mb-8">
                                <textarea
                                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-300 focus:ring-2 focus:ring-indigo-500/50 outline-none resize-none font-medium text-sm"
                                    placeholder="Add a note or comment..."
                                    rows={3}
                                    value={noteContent}
                                    onChange={e => setNoteContent(e.target.value)}
                                />
                                <div className="flex justify-end mt-2">
                                    <Button
                                        size="sm"
                                        className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold"
                                        onClick={() => createNoteMutation.mutate(noteContent)}
                                        isLoading={createNoteMutation.isPending}
                                        disabled={!noteContent.trim()}
                                    >
                                        Add Note
                                    </Button>
                                </div>
                            </div>

                            {activityLoading ? (
                                <div className="text-center py-10 text-slate-500">Loading timeline...</div>
                            ) : activityData?.activities && activityData.activities.length > 0 ? (
                                <div className="relative border-l-2 border-slate-800 ml-4 space-y-8 py-2">
                                    {activityData.activities.map((item: any) => (
                                        <div key={item.id} className="relative pl-10 group">
                                            <span className={`absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 transition-colors shadow-[0_0_0_4px_rgba(15,23,42,1)]
                                                ${item.type === 'system' ? 'bg-slate-800 border-slate-600' :
                                                    item.type === 'note' ? 'bg-amber-500 border-amber-600' :
                                                        'bg-indigo-500 border-indigo-600'
                                                }`} />

                                            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                                                <div className="bg-slate-950/30 p-3 rounded-xl border border-slate-800/50 flex-1">
                                                    <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                                                        {item.type === 'note' && <MessageSquare className="w-3 h-3 text-amber-500" />}
                                                        {item.description}
                                                        {item.metadata?.campaign_id && (
                                                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase tracking-wider">
                                                                Campaign
                                                            </span>
                                                        )}
                                                    </h3>
                                                    <p className="text-xs text-slate-500 mt-1 font-medium flex items-center gap-1">
                                                        <span className="w-1.5 h-1.5 rounded-full bg-slate-700" />
                                                        {item.source || 'System'}
                                                    </p>
                                                </div>
                                                <time className="text-xs text-slate-500 font-semibold tabular-nums mt-1 whitespace-nowrap">
                                                    {new Date(item.created_at).toLocaleString()}
                                                </time>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-20">
                                    <div className="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mx-auto mb-4">
                                        <Clock className="w-8 h-8 text-slate-600" />
                                    </div>
                                    <p className="text-slate-500 font-semibold">No recent activity recorded.</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </Layout>
    );
};

export default LeadDetail;
