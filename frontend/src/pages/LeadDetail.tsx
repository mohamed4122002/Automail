import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import Layout from "../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { ArrowLeft, ArrowRight, Mail, Clock, Calendar, MessageSquare, Flame, TrendingUp, Snowflake, Zap, XCircle, UserPlus, CheckCircle2, Activity, Users, Phone, List as ListIcon, PlusCircle, Trash2, Building2, StickyNote, AlertTriangle } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";
import { toast } from "sonner";
import { cn } from "../lib/utils";

import { useGlobalWebSocket } from "../context/WebSocketContext";

const CRM_STAGES = [
    { id: 'lead', name: 'Lead', color: 'bg-slate-500' },
    { id: 'call', name: 'Call', color: 'bg-blue-500' },
    { id: 'meeting', name: 'Meeting', color: 'bg-indigo-500' },
    { id: 'proposal', name: 'Proposal', color: 'bg-violet-500' },
    { id: 'negotiation', name: 'Negotiation', color: 'bg-purple-500' },
    { id: 'project', name: 'Project', color: 'bg-cyan-500' },
    { id: 'won', name: 'Won', color: 'bg-emerald-500' },
    { id: 'lost', name: 'Lost', color: 'bg-rose-500' },
];

const LeadDetail: React.FC = () => {
    const { id } = useParams();
    const queryClient = useQueryClient();
    const [noteContent, setNoteContent] = useState("");
    const [activeTab, setActiveTab] = useState<"timeline" | "actions" | "tasks">("timeline");

    // Interaction form state
    const [interactionType, setInteractionType] = useState<"call" | "meeting" | "note">("note");
    const [interactionContent, setInteractionContent] = useState("");
    const [filterType, setFilterType] = useState<string | null>(null);

    // Task form state
    const [isAddTaskOpen, setIsAddTaskOpen] = useState(false);
    const [isMeetingModalOpen, setIsMeetingModalOpen] = useState(false);
    const [meetingForm, setMeetingForm] = useState({
        summary: "",
        description: "",
        start_time: "",
        end_time: "",
    });
    const [meetingDuration, setMeetingDuration] = useState("60"); // default 60 mins
    const [newTask, setNewTask] = useState({
        title: "",
        description: "",
        due_date: "",
        assigned_to_id: ""
    });

    // WebSocket for real-time sync
    const { lastMessage } = useGlobalWebSocket();

    React.useEffect(() => {
        if (lastMessage !== null) {
            const message = JSON.parse(lastMessage.data);
            if (message.type === 'crm_event' || message.type === 'event') {
                // Determine if this event is relevant to THIS lead
                const isRelevant = !message.entity_id || message.entity_id === id;

                if (isRelevant) {
                    queryClient.invalidateQueries({ queryKey: ['lead', id] });
                    queryClient.invalidateQueries({ queryKey: ['lead-activity', id] });
                    queryClient.invalidateQueries({ queryKey: ['lead-tasks', id] });
                }

                // Always invalidate global stats
                queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
            }
        }
    });

    const { data: lead, isLoading: leadLoading } = useQuery({
        queryKey: ['lead', id],
        queryFn: async () => {
            const res = await api.get(`/leads/${id}`);
            return res.data;
        },
        enabled: !!id,
    });

    const { data: activityData, isLoading: activityLoading } = useQuery({
        queryKey: ['lead-activity', id],
        queryFn: async () => {
            const res = await api.get(`/leads/${id}/activity`);
            return res.data;
        },
        enabled: !!id,
    });

    const { data: users } = useQuery({
        queryKey: ['users'],
        queryFn: async () => {
            const res = await api.get('/admin/users');
            return res.data;
        }
    });

    const { data: integrationStatus } = useQuery({
        queryKey: ['integration-status'],
        queryFn: async () => {
            const res = await api.get('/integrations/status');
            return res.data;
        }
    });

    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editForm, setEditForm] = useState({
        company_name: "",
        source: "",
        stage: "",
        lead_status: "",
        lead_score: 0,
        assigned_to_id: "" as string | null,
        proposal_deadline: "" as string | null,
        deal_value: 0,
        deal_currency: "USD",
    });

    React.useEffect(() => {
        if (lead) {
            setEditForm({
                company_name: lead.company_name || "",
                source: lead.source || "",
                stage: lead.stage || "lead",
                lead_status: lead.lead_status || "new",
                lead_score: lead.lead_score || 0,
                assigned_to_id: lead.assigned_to_id || null,
                proposal_deadline: lead.proposal_deadline ? new Date(lead.proposal_deadline).toISOString().split('T')[0] : null,
                deal_value: lead.deal_value || 0,
                deal_currency: lead.deal_currency || "USD",
            });
        }
    }, [lead]);

    // ... (rest of mutations as is)


    const createNoteMutation = useMutation({
        mutationFn: async (content: string) => {
            return await api.post(`/leads/${id}/notes`, { content });
        },
        onSuccess: () => {
            setNoteContent("");
            queryClient.invalidateQueries({ queryKey: ['lead-activity', id] });
        }
    });

    React.useEffect(() => {
        if (meetingForm.start_time && meetingDuration) {
            const start = new Date(meetingForm.start_time);
            const end = new Date(start.getTime() + parseInt(meetingDuration) * 60000);

            // Format back to YYYY-MM-DDTHH:MM
            const endStr = end.getFullYear() + '-' +
                String(end.getMonth() + 1).padStart(2, '0') + '-' +
                String(end.getDate()).padStart(2, '0') + 'T' +
                String(end.getHours()).padStart(2, '0') + ':' +
                String(end.getMinutes()).padStart(2, '0');

            setMeetingForm(prev => ({ ...prev, end_time: endStr }));
        }
    }, [meetingForm.start_time, meetingDuration]);

    const updateLeadMutation = useMutation({
        mutationFn: async (data: typeof editForm) => {
            // Sanitize data
            const payload: any = { ...data };

            // Remove auto-calculated/readonly fields
            delete payload.lead_score;

            // Handle empty strings for optional dates/UUIDs
            if (!payload.proposal_deadline) payload.proposal_deadline = null;
            if (!payload.assigned_to_id) payload.assigned_to_id = null;

            return await api.patch(`/leads/${id}`, payload);
        },
        onSuccess: () => {
            setIsEditModalOpen(false);
            toast.success("Lead profile updated successfully.");
            queryClient.invalidateQueries({ queryKey: ['lead', id] });
            queryClient.invalidateQueries({ queryKey: ['lead-activity', id] });
        },
        onError: (error: any) => {
            const msg = error?.response?.data?.detail || "Failed to update lead profile. Please check your connection.";
            toast.error(msg);
        }
    });

    const { data: tasks, isLoading: tasksLoading } = useQuery({
        queryKey: ['lead-tasks', id],
        queryFn: async () => {
            const res = await api.get(`/leads/${id}/tasks`);
            return res.data;
        },
        enabled: !!id,
    });

    const logActivityMutation = useMutation({
        mutationFn: async (data: { type: string, content: string }) => {
            return await api.post(`/leads/${id}/activities`, data);
        },
        onSuccess: () => {
            setInteractionContent("");
            queryClient.invalidateQueries({ queryKey: ['lead-activity', id] });
            setActiveTab("timeline");
        }
    });

    const createTaskMutation = useMutation({
        mutationFn: async (data: typeof newTask) => {
            return await api.post(`/leads/${id}/tasks`, data);
        },
        onSuccess: () => {
            setIsAddTaskOpen(false);
            setNewTask({ title: "", description: "", due_date: "", assigned_to_id: "" });
            queryClient.invalidateQueries({ queryKey: ['lead-tasks', id] });
            queryClient.invalidateQueries({ queryKey: ['lead-activity', id] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
            queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
        }
    });

    const toggleTaskMutation = useMutation({
        mutationFn: async ({ taskId, status }: { taskId: string, status: string }) => {
            return await api.patch(`/leads/${id}/tasks/${taskId}`, { status });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['lead-tasks', id] });
            queryClient.invalidateQueries({ queryKey: ['lead-activity', id] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
            queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
        }
    });

    const updateStatusMutation = useMutation({
        mutationFn: async (status: string) => {
            return await api.patch(`/leads/${id}`, { lead_status: status });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['lead', id] });
            queryClient.invalidateQueries({ queryKey: ['lead-activity', id] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
            queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
        }
    });

    const bookMeetingMutation = useMutation({
        mutationFn: async (data: typeof meetingForm) => {
            return await api.post(`/integrations/google/events?lead_id=${id}`, data);
        },
        onSuccess: () => {
            setIsMeetingModalOpen(false);
            setMeetingForm({ summary: "", description: "", start_time: "", end_time: "" });
            toast.success("Meeting booked! A calendar invite has been sent to the lead.");
            queryClient.invalidateQueries({ queryKey: ['lead-activity', id] });
            queryClient.invalidateQueries({ queryKey: ['lead', id] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
            queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
        },
        onError: (error: any) => {
            const msg = error?.response?.data?.detail || "Failed to book meeting. Ensure Google Calendar is connected in Settings.";
            toast.error(msg);
        }
    });

    const updateStageMutation = useMutation({
        mutationFn: async (stage: string) => {
            return await api.patch(`/leads/${id}/stage`, { stage });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['lead', id] });
            queryClient.invalidateQueries({ queryKey: ['lead-activity', id] });
            queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
            queryClient.invalidateQueries({ queryKey: ['pipeline-summary'] });
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
            {/* Connection Banner */}
            {integrationStatus?.google_calendar?.connected === false && (
                <div className="bg-amber-500/10 border-b border-amber-500/20 px-8 py-3 flex items-center justify-between group">
                    <div className="flex items-center gap-3">
                        <AlertTriangle className="w-4 h-4 text-amber-500 animate-pulse" />
                        <p className="text-xs font-bold text-amber-200/80 tracking-tight">
                            Google Calendar is not connected. Connect now to enable one-click meeting booking.
                        </p>
                    </div>
                    <Link
                        to="/settings"
                        className="text-[10px] font-black text-amber-500 uppercase tracking-[0.2em] hover:text-amber-400 transition-colors flex items-center gap-2"
                    >
                        Connect Account
                        <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
                    </Link>
                </div>
            )}

            {/* Inline Stage Pills Header */}
            <div className="bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-8 py-4 sticky top-0 z-30 flex items-center justify-between gap-4">
                <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-1">
                    {CRM_STAGES.map((s) => {
                        const isActive = lead.stage === s.id;
                        return (
                            <button
                                key={s.id}
                                onClick={() => updateStageMutation.mutate(s.id)}
                                disabled={isActive || updateStageMutation.isPending}
                                className={cn(
                                    "px-4 py-2 rounded-2xl text-[10px] font-black uppercase tracking-widest border transition-all flex-shrink-0 flex items-center gap-2",
                                    isActive
                                        ? "bg-indigo-500 border-indigo-400 text-white shadow-lg shadow-indigo-500/20"
                                        : "bg-slate-950/40 border-slate-800 text-slate-500 hover:text-slate-300 hover:border-slate-700",
                                    (updateStageMutation.isPending && !isActive) ? "opacity-60 cursor-not-allowed" : ""
                                )}
                            >
                                {isActive && <CheckCircle2 className="w-3 h-3" />}
                                {s.name}
                            </button>
                        );
                    })}
                </div>
                <div className="hidden md:flex items-center gap-2 text-slate-500 text-[10px] font-black uppercase tracking-widest">
                    <Activity className="w-3 h-3 text-indigo-500" />
                    Pipeline Status
                </div>
            </div>
            {isMeetingModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
                    <Card className="w-full max-w-lg bg-slate-900 border-2 border-slate-800 shadow-2xl rounded-3xl">
                        <CardHeader className="border-b border-slate-800 pb-6">
                            <CardTitle className="text-xl font-black text-slate-100 italic tracking-tight uppercase">Book Google Calendar Meeting</CardTitle>
                        </CardHeader>
                        <CardContent className="p-8 space-y-6">
                            <div>
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Meeting Title</label>
                                <input
                                    type="text"
                                    className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                    value={meetingForm.summary}
                                    onChange={e => setMeetingForm({ ...meetingForm, summary: e.target.value })}
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Start Time</label>
                                    <input
                                        type="datetime-local"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                        value={meetingForm.start_time}
                                        onChange={e => setMeetingForm({ ...meetingForm, start_time: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Duration</label>
                                    <select
                                        className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold appearance-none"
                                        value={meetingDuration}
                                        onChange={e => setMeetingDuration(e.target.value)}
                                    >
                                        <option value="30">30 Minutes</option>
                                        <option value="60">1 Hour</option>
                                        <option value="90">1.5 Hours</option>
                                        <option value="120">2 Hours</option>
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">End Time (Calculated)</label>
                                <input
                                    type="datetime-local"
                                    className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-500 bg-slate-900/50 cursor-not-allowed opacity-60 outline-none font-semibold"
                                    value={meetingForm.end_time}
                                    readOnly
                                />
                            </div>
                            <div>
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Description</label>
                                <textarea
                                    className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold min-h-[100px]"
                                    value={meetingForm.description}
                                    onChange={e => setMeetingForm({ ...meetingForm, description: e.target.value })}
                                />
                            </div>

                            <div className="flex justify-end gap-4 pt-6 border-t border-slate-800">
                                <Button
                                    variant="secondary"
                                    className="rounded-2xl px-6 py-4 font-black border-slate-800"
                                    onClick={() => setIsMeetingModalOpen(false)}
                                >
                                    CANCEL
                                </Button>
                                <Button
                                    className="rounded-2xl px-6 py-4 bg-violet-600 hover:bg-violet-500 font-black shadow-2xl shadow-indigo-500/20"
                                    onClick={() => bookMeetingMutation.mutate(meetingForm)}
                                    isLoading={bookMeetingMutation.isPending}
                                >
                                    BOOK NOW
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}

            {isEditModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
                    <Card className="w-full max-w-2xl bg-slate-900 border-2 border-slate-800 shadow-2xl rounded-3xl">
                        <CardHeader className="border-b border-slate-800 pb-6">
                            <CardTitle className="text-2xl font-black text-slate-100 italic tracking-tight">EDIT LEAD PROFILE</CardTitle>
                        </CardHeader>
                        <CardContent className="p-8">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                {/* Left Section: Basic Info */}
                                <div className="space-y-6">
                                    <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em]">Company Details</h3>
                                    <div>
                                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Company Name</label>
                                        <input
                                            type="text"
                                            className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                            value={editForm.company_name}
                                            onChange={e => setEditForm({ ...editForm, company_name: e.target.value })}
                                        />
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Source</label>
                                        <select
                                            className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold appearance-none"
                                            value={editForm.source}
                                            onChange={e => setEditForm({ ...editForm, source: e.target.value })}
                                        >
                                            <option value="Marketing">Marketing</option>
                                            <option value="Referral">Referral</option>
                                            <option value="Cold Outreach">Cold Outreach</option>
                                            <option value="Inbound">Inbound</option>
                                            <option value="Website Form">Website Form</option>
                                            <option value="Organic Search">Organic Search</option>
                                            <option value="Social Media">Social Media</option>
                                            <option value="Conference">Conference</option>
                                            <option value="Other">Other</option>
                                            {!['Marketing', 'Referral', 'Cold Outreach', 'Inbound', 'Website Form', 'Organic Search', 'Social Media', 'Conference', 'Other'].includes(editForm.source) && (
                                                <option value={editForm.source}>{editForm.source}</option>
                                            )}
                                        </select>
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
                                                <option key={u.id} value={u.id}>{u.email} ({u.role})</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                {/* Right Section: Lead Props */}
                                <div className="space-y-6">
                                    <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em]">Pipeline Progress</h3>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Stage</label>
                                            <select
                                                className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold appearance-none"
                                                value={editForm.stage}
                                                onChange={e => setEditForm({ ...editForm, stage: e.target.value })}
                                            >
                                                {CRM_STAGES.map(s => (
                                                    <option key={s.id} value={s.id}>{s.name}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Marketing Status</label>
                                            <select
                                                className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold appearance-none"
                                                value={editForm.lead_status}
                                                onChange={e => setEditForm({ ...editForm, lead_status: e.target.value })}
                                            >
                                                <option value="new">New</option>
                                                <option value="warm">Warm</option>
                                                <option value="hot">Hot</option>
                                                <option value="cold">Cold</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Proposal Deadline</label>
                                        <input
                                            type="date"
                                            className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                            value={editForm.proposal_deadline || ""}
                                            onChange={e => setEditForm({ ...editForm, proposal_deadline: e.target.value })}
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Currency</label>
                                            <select
                                                className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold appearance-none"
                                                value={editForm.deal_currency}
                                                onChange={e => setEditForm({ ...editForm, deal_currency: e.target.value })}
                                            >
                                                <option value="USD">USD</option>
                                                <option value="EGP">EGP</option>
                                                <option value="EUR">EUR</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Value</label>
                                            <input
                                                type="number"
                                                className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-semibold"
                                                value={editForm.deal_value}
                                                onChange={e => setEditForm({ ...editForm, deal_value: Number(e.target.value) })}
                                                placeholder="0"
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Engagement Score <span className="text-indigo-400">(Auto-calculated)</span></label>
                                        <div className="flex items-center gap-4 bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4">
                                            <div className="flex-1 bg-slate-800 h-2 rounded-full overflow-hidden">
                                                <div
                                                    className={cn(
                                                        "h-full rounded-full transition-all duration-700",
                                                        (lead?.lead_score || 0) > 70 ? "bg-emerald-500" :
                                                            (lead?.lead_score || 0) > 40 ? "bg-amber-500" : "bg-rose-500"
                                                    )}
                                                    style={{ width: `${lead?.lead_score || 0}%` }}
                                                />
                                            </div>
                                            <span className={cn(
                                                "text-lg font-black italic min-w-[2.5rem] text-right",
                                                (lead?.lead_score || 0) > 70 ? "text-emerald-400" :
                                                    (lead?.lead_score || 0) > 40 ? "text-amber-400" : "text-rose-400"
                                            )}>
                                                {lead?.lead_score || 0}
                                            </span>
                                        </div>
                                        <p className="text-[10px] text-slate-600 mt-1.5 font-bold">Score updates automatically when you log calls, emails, and meetings.</p>
                                    </div>
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
                                >
                                    SAVE CHANGES
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}

            {isAddTaskOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <Card className="w-full max-w-md bg-slate-900 border-2 border-slate-800 shadow-2xl rounded-3xl">
                        <CardHeader><CardTitle className="text-xl font-black text-slate-100 italic">NEW FOLLOW-UP TASK</CardTitle></CardHeader>
                        <CardContent className="space-y-4 p-8">
                            <div>
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1 block">Task Title</label>
                                <input
                                    type="text"
                                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-300 outline-none"
                                    value={newTask.title}
                                    onChange={e => setNewTask({ ...newTask, title: e.target.value })}
                                    placeholder="e.g. Follow up on proposal"
                                />
                            </div>
                            <div>
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1 block">Description</label>
                                <textarea
                                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-300 outline-none h-24"
                                    value={newTask.description}
                                    onChange={e => setNewTask({ ...newTask, description: e.target.value })}
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1 block">Due Date</label>
                                    <input
                                        type="date"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-300 outline-none"
                                        value={newTask.due_date}
                                        onChange={e => setNewTask({ ...newTask, due_date: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1 block">Assign To</label>
                                    <select
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-300 outline-none"
                                        value={newTask.assigned_to_id}
                                        onChange={e => setNewTask({ ...newTask, assigned_to_id: e.target.value })}
                                    >
                                        <option value="">Me</option>
                                        {users?.map((u: any) => (
                                            <option key={u.id} value={u.id}>{u.email}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            <div className="flex justify-end gap-3 mt-6">
                                <Button variant="ghost" onClick={() => setIsAddTaskOpen(false)}>Cancel</Button>
                                <Button className="bg-indigo-600" onClick={() => createTaskMutation.mutate(newTask)} isLoading={createTaskMutation.isPending}>Create Task</Button>
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
                            <div className="w-24 h-24 rounded-3xl bg-indigo-500/20 flex items-center justify-center shadow-2xl mb-6">
                                <Users className="w-12 h-12 text-indigo-400" />
                            </div>

                            <h2 className="text-2xl font-black text-slate-100 text-center">
                                {lead.company_name || 'Unknown Company'}
                            </h2>
                            <p className="text-slate-400 font-medium mb-6">Source: {lead.source}</p>

                            <div className="flex flex-wrap justify-center gap-2 mb-8">
                                <span className={`px-4 py-1 rounded-full bg-indigo-500 text-[10px] font-black text-white uppercase tracking-wider shadow-lg shadow-indigo-500/20`}>
                                    {lead.stage}
                                </span>
                                <span className="px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-xs font-bold text-slate-400 uppercase tracking-wider">
                                    Score: {lead.lead_score}
                                </span>
                            </div>

                            <div className="w-full space-y-4 border-t border-slate-800/60 pt-6">
                                {lead.proposal_deadline && (
                                    <div className="flex items-center text-sm font-medium text-rose-400 font-bold italic">
                                        <Clock className="w-4 h-4 mr-3" />
                                        <span className="uppercase text-[10px] font-black mr-2">Deadline:</span>
                                        {new Date(lead.proposal_deadline).toLocaleDateString()}
                                    </div>
                                )}
                                <div className="flex items-center text-sm font-medium text-slate-300">
                                    <Activity className="w-4 h-4 mr-3 text-slate-500" />
                                    <span className="text-slate-500 mr-2 uppercase text-[10px] font-black">Status:</span>
                                    {lead.lead_status}
                                </div>
                                <div className="flex items-center text-sm font-medium text-slate-300">
                                    <UserPlus className="w-4 h-4 mr-3 text-slate-500" />
                                    <span className="text-slate-500 mr-2 uppercase text-[10px] font-black">Assignee:</span>
                                    {lead.assigned_to_name || 'Unassigned'}
                                </div>
                                <div className="flex items-center text-sm font-medium text-slate-300">
                                    <Calendar className="w-4 h-4 mr-3 text-slate-500" />
                                    <span className="text-slate-500 mr-2 uppercase text-[10px] font-black">Created:</span>
                                    {new Date(lead.created_at).toLocaleDateString()}
                                </div>
                                {lead.organization_id && (
                                    <div className="pt-4 mt-2 border-t border-slate-800/40">
                                        <div className="mb-4">
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest block mb-1">Potential Deal Value</label>
                                            <div className="text-xl font-black text-indigo-400 italic">
                                                {lead.deal_currency || 'USD'} {Number(lead.deal_value || 0).toLocaleString()}
                                            </div>
                                        </div>
                                        <Link
                                            to={`/organizations/${lead.organization_id}`}
                                            className="group flex items-center p-3 rounded-xl bg-indigo-500/5 border border-indigo-500/10 hover:bg-indigo-500/10 hover:border-indigo-500/30 transition-all"
                                        >
                                            <Building2 className="w-4 h-4 mr-3 text-indigo-400" />
                                            <div className="flex-1 min-w-0">
                                                <span className="block text-[8px] font-black text-slate-600 uppercase tracking-widest">Organization</span>
                                                <span className="block text-xs font-bold text-slate-200 truncate group-hover:text-indigo-400 transition-colors">View Company Details</span>
                                            </div>
                                            <ArrowRight className="w-3 h-3 text-slate-600 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all" />
                                        </Link>
                                    </div>
                                )}
                            </div>

                            <div className="w-full mt-8 grid grid-cols-2 gap-3">
                                <Button
                                    className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold"
                                    onClick={() => setIsEditModalOpen(true)}
                                >
                                    Quick Edit
                                </Button>
                                <Button
                                    className="bg-violet-600 hover:bg-violet-500 text-white font-bold"
                                    onClick={() => {
                                        setMeetingForm({
                                            ...meetingForm,
                                            summary: `Meeting with ${lead.company_name}`,
                                            start_time: new Date(Date.now() + 3600000).toISOString().slice(0, 16)
                                        });
                                        setIsMeetingModalOpen(true);
                                    }}
                                >
                                    Book Meeting
                                </Button>
                                <Button
                                    variant="secondary"
                                    className="font-bold border-slate-700"
                                    onClick={() => window.open(`https://www.google.com/search?q=${encodeURIComponent(lead.company_name)}`, '_blank')}
                                >
                                    Research
                                </Button>
                            </div>

                            {/* Inline Stage Pills In Side Column (Keeping as fallback or secondary) but primarily moving to header below */}
                        </CardContent>
                    </Card>

                    {/* Quick-Action Floating Bar (New Section) is at the bottom of the page */}
                </div>

                {/* Right Column: Timeline, Actions & Tasks */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="flex p-1 bg-slate-800/40 border border-slate-800 rounded-2xl w-fit">
                        <button
                            onClick={() => setActiveTab("timeline")}
                            className={`px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${activeTab === 'timeline' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}
                        >
                            Timeline
                        </button>
                        <button
                            onClick={() => setActiveTab("actions")}
                            className={`px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${activeTab === 'actions' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}
                        >
                            Log Interaction
                        </button>
                        <button
                            onClick={() => setActiveTab("tasks")}
                            className={`px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${activeTab === 'tasks' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}
                        >
                            To-Dos
                            {tasks?.filter((t: any) => t.status === 'pending').length > 0 && (
                                <span className="ml-2 px-1.5 py-0.5 rounded-full bg-indigo-500 text-[8px]">{tasks.filter((t: any) => t.status === 'pending').length}</span>
                            )}
                        </button>
                    </div>

                    <Card className="min-h-[500px] border-2 border-slate-800/60 bg-slate-900/40 overflow-hidden flex flex-col">
                        {activeTab === 'timeline' && (
                            <>
                                <CardHeader className="flex flex-row items-center justify-between border-b border-slate-800/60 pb-6">
                                    <CardTitle className="text-xl font-black text-slate-100 italic">ACTIVITY TIMELINE</CardTitle>
                                    <div className="flex gap-2">
                                        {['all', 'call', 'meeting', 'note', 'system'].map((t) => (
                                            <button
                                                key={t}
                                                onClick={() => setFilterType(t === 'all' ? null : t)}
                                                className={cn(
                                                    "px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest transition-all border",
                                                    (filterType === t || (t === 'all' && filterType === null))
                                                        ? "bg-indigo-500 border-indigo-500 text-white"
                                                        : "bg-slate-900 border-slate-800 text-slate-500 hover:border-slate-700"
                                                )}
                                            >
                                                {t}
                                            </button>
                                        ))}
                                    </div>
                                </CardHeader>
                                <CardContent className="pt-8 flex-1 flex flex-col">
                                    {/* Note Input */}
                                    <div className="mb-8 p-6 bg-slate-950/20 border border-slate-800/50 rounded-2xl">
                                        <textarea
                                            id="note-input-area"
                                            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-300 focus:ring-2 focus:ring-indigo-500/50 outline-none resize-none font-medium text-sm mb-4"
                                            placeholder="Write a quick note about this lead..."
                                            rows={2}
                                            value={noteContent}
                                            onChange={e => setNoteContent(e.target.value)}
                                        />
                                        <div className="flex justify-end">
                                            <Button
                                                size="sm"
                                                className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-6"
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
                                            {activityData.activities
                                                .filter((item: any) => !filterType || item.type === filterType)
                                                .map((item: any) => (
                                                    <div key={item.id} className="relative pl-10 group">
                                                        <span className={`absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 transition-colors shadow-[0_0_0_4px_rgba(15,23,42,1)]
                                                        ${item.type === 'system' ? 'bg-slate-800 border-slate-600' :
                                                                item.type === 'note' ? 'bg-amber-500 border-amber-600' :
                                                                    item.type === 'call' ? 'bg-emerald-500 border-emerald-600' :
                                                                        item.type === 'meeting' ? 'bg-violet-500 border-violet-600' :
                                                                            'bg-indigo-500 border-indigo-600'
                                                            }`} />

                                                        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                                                            <div className="bg-slate-950/30 p-4 rounded-2xl border border-slate-800/50 flex-1 hover:border-slate-700 transition-colors">
                                                                <div className="flex items-center gap-3 mb-2">
                                                                    {item.type === 'note' && <MessageSquare className="w-4 h-4 text-amber-500" />}
                                                                    {item.type === 'call' && <Phone className="w-4 h-4 text-emerald-500" />}
                                                                    {item.type === 'meeting' && <Calendar className="w-4 h-4 text-violet-500" />}
                                                                    {item.type === 'system' && <Zap className="w-4 h-4 text-slate-400" />}
                                                                    <h3 className="text-sm font-bold text-slate-200">
                                                                        {item.description}
                                                                    </h3>
                                                                </div>
                                                                <p className="text-xs text-slate-500 font-medium flex items-center gap-2">
                                                                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500/50" />
                                                                    Logged by {item.source || 'System'}
                                                                </p>
                                                            </div>
                                                            <time className="text-xs text-slate-500 font-semibold tabular-nums mt-2 whitespace-nowrap opacity-60">
                                                                {new Date(item.created_at).toLocaleString()}
                                                            </time>
                                                        </div>
                                                    </div>
                                                ))}
                                        </div>
                                    ) : (
                                        <div className="text-center py-20 flex-1">
                                            <div className="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mx-auto mb-4">
                                                <Clock className="w-8 h-8 text-slate-600" />
                                            </div>
                                            <p className="text-slate-500 font-semibold">No recent activity recorded.</p>
                                        </div>
                                    )}
                                </CardContent>
                            </>
                        )}

                        {activeTab === 'actions' && (
                            <CardContent className="p-12 space-y-8 flex-1">
                                <div className="text-center space-y-2 mb-10">
                                    <h2 className="text-3xl font-black text-white italic">LOG INTERACTION</h2>
                                    <p className="text-slate-500 text-sm font-medium tracking-wide">Record your discovery calls, meetings, or deep-dive notes.</p>
                                </div>

                                <div className="grid grid-cols-3 gap-4">
                                    {[
                                        { id: 'call', icon: Phone, label: 'Call', color: 'text-emerald-400' },
                                        { id: 'meeting', icon: Calendar, label: 'Meeting', color: 'text-violet-400' },
                                        { id: 'note', icon: MessageSquare, label: 'Note', color: 'text-amber-400' },
                                    ].map(type => (
                                        <button
                                            key={type.id}
                                            onClick={() => setInteractionType(type.id as any)}
                                            className={`
                                                flex flex-col items-center justify-center p-6 rounded-3xl border-2 transition-all
                                                ${interactionType === type.id ? 'bg-indigo-500/10 border-indigo-500 shadow-xl shadow-indigo-500/10' : 'bg-slate-950/40 border-slate-800 hover:border-slate-700'}
                                            `}
                                        >
                                            <type.icon className={`w-8 h-8 mb-3 ${interactionType === type.id ? 'text-indigo-400' : type.color}`} />
                                            <span className={`text-[10px] font-black uppercase tracking-widest ${interactionType === type.id ? 'text-indigo-400' : 'text-slate-400'}`}>
                                                {type.label}
                                            </span>
                                        </button>
                                    ))}
                                </div>

                                <div className="space-y-4">
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Detail & Outcome</label>
                                    <textarea
                                        id="log-interaction-area"
                                        className="w-full bg-slate-950 border-2 border-slate-800 rounded-3xl p-6 text-slate-200 outline-none focus:border-indigo-500 transition-all font-medium min-h-[150px]"
                                        placeholder={`What happened during the ${interactionType}?`}
                                        value={interactionContent}
                                        onChange={e => setInteractionContent(e.target.value)}
                                    />
                                </div>

                                <div className="flex justify-center pt-6">
                                    <Button
                                        className="rounded-2xl px-12 py-8 bg-indigo-600 hover:bg-indigo-500 font-black text-lg shadow-2xl shadow-indigo-500/20"
                                        onClick={() => logActivityMutation.mutate({ type: interactionType, content: interactionContent })}
                                        disabled={!interactionContent.trim()}
                                        isLoading={logActivityMutation.isPending}
                                    >
                                        SAVE LOG
                                    </Button>
                                </div>
                            </CardContent>
                        )}

                        {activeTab === 'tasks' && (
                            <>
                                <CardHeader className="flex flex-row items-center justify-between border-b border-slate-800/60 pb-6">
                                    <CardTitle className="text-xl font-black text-slate-100 italic">NEXT ACTIONS (TO-DOS)</CardTitle>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        className="rounded-xl border-slate-700 text-indigo-400 font-bold hover:bg-slate-800"
                                        onClick={() => setIsAddTaskOpen(true)}
                                    >
                                        <PlusCircle className="w-4 h-4 mr-2" />
                                        NEW TASK
                                    </Button>
                                </CardHeader>
                                <CardContent className="p-8 flex-1">
                                    {tasksLoading ? (
                                        <div className="text-center py-10 text-slate-500">Loading tasks...</div>
                                    ) : tasks && tasks.length > 0 ? (
                                        <div className="space-y-4">
                                            {tasks.map((task: any) => (
                                                <div
                                                    key={task.id}
                                                    className={`
                                                        group p-5 rounded-2xl border-2 transition-all flex items-center justify-between
                                                        ${task.status === 'completed' ? 'bg-slate-950/20 border-slate-900 opacity-60' : 'bg-slate-950/40 border-slate-800 hover:border-slate-700 shadow-lg shadow-black/20'}
                                                    `}
                                                >
                                                    <div className="flex items-center gap-4">
                                                        <button
                                                            onClick={() => toggleTaskMutation.mutate({ taskId: task.id, status: task.status === 'pending' ? 'completed' : 'pending' })}
                                                            className={`
                                                                w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-all
                                                                ${task.status === 'completed' ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-slate-700 hover:border-indigo-500 text-transparent hover:text-indigo-500/50'}
                                                            `}
                                                        >
                                                            <CheckCircle2 className="w-4 h-4" />
                                                        </button>
                                                        <div>
                                                            <h4 className={`text-sm font-bold ${task.status === 'completed' ? 'text-slate-500 line-through' : 'text-slate-100'}`}>
                                                                {task.title}
                                                            </h4>
                                                            <div className="flex items-center gap-3 mt-1">
                                                                <p className="text-[10px] text-slate-500 font-black uppercase flex items-center">
                                                                    <Clock className="w-3 h-3 mr-1" />
                                                                    {task.due_date ? new Date(task.due_date).toLocaleDateString() : 'No Deadline'}
                                                                </p>
                                                                {task.description && (
                                                                    <p className="text-xs text-slate-600 font-medium truncate max-w-[200px] border-l border-slate-800 pl-3">
                                                                        {task.description}
                                                                    </p>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>

                                                    <div className="flex items-center gap-4">
                                                        <div className="text-right">
                                                            <p className="text-[9px] font-black text-indigo-400 uppercase tracking-widest">{task.status}</p>
                                                            <p className="text-[9px] text-slate-600 font-bold">{task.assigned_to_id ? 'Assigned' : 'Personal'}</p>
                                                        </div>
                                                        <button className="text-slate-700 hover:text-rose-500 opacity-0 group-hover:opacity-100 transition-all">
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="text-center py-20">
                                            <div className="w-16 h-16 rounded-3xl bg-slate-800/50 flex items-center justify-center mx-auto mb-4 border border-slate-700">
                                                <ListIcon className="w-8 h-8 text-slate-600" />
                                            </div>
                                            <h3 className="text-slate-200 font-bold mb-1">Clear Horizon!</h3>
                                            <p className="text-slate-500 text-sm font-medium">No pending follow-ups for this lead.</p>
                                        </div>
                                    )}
                                </CardContent>
                            </>
                        )}
                    </Card>
                </div>
            </div>

            {/* Quick-Action Floating Bar */}
            <div className="fixed bottom-4 left-0 right-0 z-40 px-4">
                <div className="max-w-[1100px] mx-auto">
                    <div className="bg-slate-950/80 backdrop-blur-md border border-slate-800 rounded-2xl shadow-2xl shadow-black/40 p-2 flex items-center justify-between gap-2">
                        <div className="hidden sm:block pl-3 min-w-0">
                            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500">Quick actions</div>
                            <div className="text-xs font-bold text-slate-200 truncate">{lead.company_name}</div>
                        </div>
                        <div className="flex items-center gap-2 flex-wrap justify-end">
                            <Button
                                size="sm"
                                className="h-10 rounded-xl bg-emerald-600 hover:bg-emerald-500 font-black text-[10px] uppercase tracking-widest"
                                onClick={() => { setActiveTab("actions"); setInteractionType("call"); }}
                            >
                                <Phone className="w-4 h-4 mr-2" />
                                Log Call
                            </Button>
                            <Button
                                size="sm"
                                className="h-10 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-black text-[10px] uppercase tracking-widest"
                                onClick={() => { setActiveTab("actions"); /* keep existing form, but treat as email */ setInteractionType("note"); setInteractionContent("Email: "); }}
                            >
                                <Mail className="w-4 h-4 mr-2" />
                                Log Email
                            </Button>
                            <Button
                                size="sm"
                                className="h-10 rounded-xl bg-violet-600 hover:bg-violet-500 font-black text-[10px] uppercase tracking-widest"
                                onClick={() => {
                                    setMeetingForm({
                                        ...meetingForm,
                                        summary: `Meeting with ${lead.company_name}`,
                                        start_time: new Date(Date.now() + 3600000).toISOString().slice(0, 16)
                                    });
                                    setIsMeetingModalOpen(true);
                                }}
                            >
                                <Calendar className="w-4 h-4 mr-2" />
                                Book Meeting
                            </Button>
                            <Button
                                size="sm"
                                variant="secondary"
                                className="h-10 rounded-xl font-black text-[10px] uppercase tracking-widest border-slate-800"
                                onClick={() => {
                                    setActiveTab("timeline");
                                    setTimeout(() => {
                                        document.getElementById('note-input-area')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                        document.getElementById('note-input-area')?.focus();
                                    }, 100);
                                }}
                            >
                                <StickyNote className="w-4 h-4 mr-2" />
                                Note
                            </Button>
                            <Button
                                size="sm"
                                variant="ghost"
                                className="h-10 rounded-xl font-black text-[10px] uppercase tracking-widest text-rose-500 hover:text-rose-400 hover:bg-rose-500/10"
                                onClick={() => {
                                    if (confirm("Are you sure you want to mark this lead as LOST?")) {
                                        updateStageMutation.mutate("lost");
                                    }
                                }}
                                isLoading={updateStageMutation.isPending}
                            >
                                <XCircle className="w-4 h-4 mr-2" />
                                Mark Lost
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </Layout >
    );
};

export default LeadDetail;
