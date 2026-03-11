import React, { useState, useRef, useMemo } from 'react';
import { useDebounce } from '../hooks/useDebounce';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { EnhancedStatCard } from '../components/ui/EnhancedStatCard';
import api from '../lib/api';
import {
    Users, Mail, TrendingUp, Snowflake,
    Zap, Search, Activity, Clock,
    CheckCircle2, XCircle, BarChart3,
    MoreHorizontal, Calendar, UserPlus
} from 'lucide-react';
import { AddLeadModal } from '../components/modals/AddLeadModal';
import { useAuth } from '../auth/AuthContext';
import { Link } from 'react-router-dom';
import { useGlobalWebSocket } from '../context/WebSocketContext';
import { cn } from '../lib/utils';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import { Modal } from '../components/ui/Modal';

interface TransitionModalState {
    isOpen: boolean;
    leadId: string;
    fromStage: string;
    toStage: string;
    companyName: string;
}

interface Lead {
    id: string;
    company_name: string;
    source: string;
    stage: string;
    lead_score: number;
    lead_status: string;
    assigned_to_name?: string;
    created_at: string;
}

interface LeadStats {
    total: number;
    by_stage: Record<string, number>;
    by_status: Record<string, number>;
}

const CRM_STAGES = [
    { id: 'lead', name: 'Lead', icon: <Users className="w-4 h-4" /> },
    { id: 'call', name: 'Call', icon: <Mail className="w-4 h-4" /> },
    { id: 'meeting', name: 'Meeting', icon: <Clock className="w-4 h-4" /> },
    { id: 'proposal', name: 'Proposal', icon: <Zap className="w-4 h-4" /> },
    { id: 'negotiation', name: 'Negotiation', icon: <TrendingUp className="w-4 h-4" /> },
    { id: 'project', name: 'Project', icon: <Activity className="w-4 h-4" /> },
    { id: 'won', name: 'Won', icon: <CheckCircle2 className="w-4 h-4" /> },
    { id: 'lost', name: 'Lost', icon: <XCircle className="w-4 h-4" /> },
];

const LeadsPipeline: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const debouncedSearch = useDebounce(searchTerm, 300);
    const [transitionModal, setTransitionModal] = useState<TransitionModalState | null>(null);
    const [dealValue, setDealValue] = useState<string>('');
    const [note, setNote] = useState<string>('');
    const [meetingDate, setMeetingDate] = useState<string>('');
    const [proposalDate, setProposalDate] = useState<string>('');
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const { user } = useAuth();
    const isManager = ['super_admin', 'admin', 'manager'].includes(user?.role || '');

    // Reference to the scrollable Kanban container
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const scrollIntervalRef = useRef<NodeJS.Timeout | null>(null);

    const queryClient = useQueryClient();

    useGlobalWebSocket();

    const { data: stats, isLoading: statsLoading } = useQuery<LeadStats>({
        queryKey: ['lead-stats'],
        queryFn: async () => (await api.get('/leads/stats')).data
    });

    const { data: leads, isLoading: leadsLoading } = useQuery<Lead[]>({
        queryKey: ['leads', 'all', debouncedSearch],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (debouncedSearch) params.append('search', debouncedSearch);
            return (await api.get(`/leads?${params}`)).data;
        }
    });

    // group leads by stage, memoized so each stage column only re-renders when
    // its own list changes
    const leadsGrouped = useMemo(() => {
        if (!leads || !Array.isArray(leads)) return {} as Record<string, Lead[]>;
        return leads.reduce((acc: Record<string, Lead[]>, l) => {
            acc[l.stage] = acc[l.stage] || [];
            acc[l.stage].push(l);
            return acc;
        }, {});
    }, [leads]);

    const StageColumn: React.FC<{ stage: typeof CRM_STAGES[0]; leads: Lead[] }> = React.memo(({ stage, leads }) => {
        const isWon = stage.id === 'won';
        const isLost = stage.id === 'lost';

        return (
            <div key={stage.id} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm flex flex-col">
                {/* Top Accent Line */}
                <div className={cn(
                    "h-1 w-full",
                    isWon ? "bg-emerald-500" : isLost ? "bg-rose-500" : "bg-indigo-500"
                )} />

                {/* Group Header */}
                <div className="bg-slate-800/40 px-5 py-3 flex items-center justify-between border-b border-slate-800/80">
                    <div className="flex items-center gap-3">
                        <span className={cn(
                            "w-6 h-6 rounded flex items-center justify-center",
                            isWon ? "bg-emerald-500/20 text-emerald-400" :
                                isLost ? "bg-rose-500/20 text-rose-400" :
                                    "bg-indigo-500/20 text-indigo-400"
                        )}>
                            {React.cloneElement(stage.icon as React.ReactElement, { className: "w-4 h-4" })}
                        </span>
                        <h3 className="text-sm font-bold text-slate-200 tracking-wider uppercase">
                            {stage.name}
                        </h3>
                        <Badge variant="neutral" className="ml-2 bg-slate-950 text-slate-400 font-bold border border-slate-800">
                            {leads.length} Leads
                        </Badge>
                    </div>
                </div>

                {/* Table Columns Header */}
                {leads.length > 0 && (
                    <div className="grid grid-cols-12 gap-4 px-6 py-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest border-b border-slate-800/50 bg-slate-900/50">
                        <div className="col-span-4 pl-3">Company Name</div>
                        <div className="col-span-2">Source</div>
                        <div className="col-span-2">Score</div>
                        <div className="col-span-3">Assigned To</div>
                        <div className="col-span-1 text-right">Action</div>
                    </div>
                )}

                {/* Droppable Area */}
                <Droppable droppableId={stage.id}>
                    {(provided, snapshot) => (
                        <div
                            ref={provided.innerRef}
                            {...provided.droppableProps}
                            className={cn(
                                "flex flex-col gap-1.5 min-h-[60px] p-2 transition-colors",
                                snapshot.isDraggingOver ? "bg-slate-800/20 ring-1 ring-inset ring-indigo-500/50 rounded-b-xl" : ""
                            )}
                        >
                            {leads.length === 0 && (
                                <div className={cn(
                                    "flex items-center justify-center h-16 text-slate-500 transition-opacity",
                                    snapshot.isDraggingOver ? "opacity-0" : "opacity-100"
                                )}>
                                    <span className="text-xs font-semibold">No leads currently in {stage.name}</span>
                                </div>
                            )}

                            {leads.map((lead, index) => (
                                <Draggable key={lead.id} draggableId={String(lead.id)} index={index}>
                                    {(provided, snapshot) => (
                                        <div
                                            ref={provided.innerRef}
                                            {...provided.draggableProps}
                                            {...provided.dragHandleProps}
                                            className={cn(
                                                "grid grid-cols-12 gap-4 items-center px-4 py-3 bg-slate-950/40 hover:bg-slate-800/80 border border-transparent rounded-lg cursor-grab active:cursor-grabbing transition-colors",
                                                snapshot.isDragging ? "shadow-2xl border-indigo-500/50 scale-[1.01] bg-slate-900 z-50" : "hover:border-slate-700/50"
                                            )}
                                            style={{
                                                ...provided.draggableProps.style,
                                            }}
                                        >
                                            <div className="flex items-center gap-3 col-span-4">
                                                <div className={cn(
                                                    "w-1.5 h-1.5 rounded-full flex-shrink-0",
                                                    lead.lead_score > 70 ? "bg-emerald-500" : lead.lead_score > 40 ? "bg-amber-500" : "bg-rose-500"
                                                )} />
                                                <span className="font-semibold text-sm text-slate-200 truncate" title={lead.company_name}>
                                                    {lead.company_name}
                                                </span>
                                                {lead.lead_score > 70 && !snapshot.isDragging && (
                                                    <Badge variant="success" className="text-[9px] px-1.5 py-0">Hot</Badge>
                                                )}
                                            </div>

                                            <div className="col-span-2">
                                                <Badge variant="neutral" className="text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700/50">
                                                    {lead.source}
                                                </Badge>
                                            </div>

                                            <div className="flex items-center gap-1.5 col-span-2">
                                                <span className="text-xs font-bold text-slate-400">{lead.lead_score}</span>
                                                <span className="text-[10px] text-slate-600">pts</span>
                                            </div>

                                            <div className="col-span-3">
                                                {lead.assigned_to_name ? (
                                                    <div className="flex items-center gap-2">
                                                        <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-[9px] font-bold text-white shadow-sm ring-1 ring-slate-900" title={lead.assigned_to_name}>
                                                            {lead.assigned_to_name[0]}
                                                        </div>
                                                        <span className="text-xs text-slate-400 truncate">{lead.assigned_to_name.split(' ')[0]}</span>
                                                    </div>
                                                ) : (
                                                    <div className="flex items-center gap-2">
                                                        <div className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center text-[10px] text-slate-500 border border-slate-700 border-dashed">?</div>
                                                        <span className="text-xs text-slate-600 italic">Unassigned</span>
                                                    </div>
                                                )}
                                            </div>

                                            <div className="flex justify-end col-span-1">
                                                <Link to={`/leads/${lead.id}`} className="p-1.5 text-slate-500 hover:text-indigo-400 hover:bg-indigo-500/10 rounded-md transition-colors" title="View details">
                                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg>
                                                </Link>
                                            </div>
                                        </div>
                                    )}
                                </Draggable>
                            ))}
                            {provided.placeholder}
                        </div>
                    )}
                </Droppable>
            </div>
        );
    });

    const updateLead = useMutation({
        mutationFn: ({ leadId, update }: { leadId: string; update: any }) =>
            api.patch(`/leads/${leadId}`, update),
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ['leads'] });
            queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
        }
    });

    // ── Edge Scrolling Logic ──
    const startScroll = (direction: 'left' | 'right') => {
        if (scrollIntervalRef.current) return; // already scrolling
        scrollIntervalRef.current = setInterval(() => {
            if (scrollContainerRef.current) {
                scrollContainerRef.current.scrollBy({ left: direction === 'right' ? 15 : -15, behavior: 'auto' });
            }
        }, 16);
    };

    const stopScroll = () => {
        if (scrollIntervalRef.current) {
            clearInterval(scrollIntervalRef.current);
            scrollIntervalRef.current = null;
        }
    };

    const onDragStart = () => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!scrollContainerRef.current) return;
            const containerBounds = scrollContainerRef.current.getBoundingClientRect();
            const edgeThreshold = 100; // pixels from edge to trigger scroll

            if (e.clientX > containerBounds.right - edgeThreshold) {
                startScroll('right');
            } else if (e.clientX < containerBounds.left + edgeThreshold) {
                startScroll('left');
            } else {
                stopScroll();
            }
        };

        window.addEventListener('mousemove', handleMouseMove);

        // Clean up when mouse leaves entirely or on drag end
        const cleanup = () => {
            window.removeEventListener('mousemove', handleMouseMove);
            stopScroll();
            window.removeEventListener('mouseup', cleanup);
        };
        window.addEventListener('mouseup', cleanup);
    };

    const onDragEnd = (result: DropResult) => {
        stopScroll(); // Ensure we stop scrolling

        const { destination, source, draggableId } = result;
        if (!destination) return;
        if (destination.droppableId === source.droppableId && destination.index === source.index) return;

        // Optimistic update
        const previousLeads = queryClient.getQueryData<Lead[]>(['leads', 'all', searchTerm]);
        if (previousLeads) {
            const newLeads = previousLeads.map(l =>
                l.id.toString() === draggableId ? { ...l, stage: destination.droppableId } : l
            );
            // Move item to new index position visually
            const leadToMove = newLeads.find(l => l.id.toString() === draggableId);
            if (leadToMove) {
                const leadsFiltered = newLeads.filter(l => l.id.toString() !== draggableId);
                // We don't perfectly sort by index here as the server sorts by created_at normally, 
                // but we map it cleanly to the stage
                queryClient.setQueryData(['leads', 'all', searchTerm], newLeads);
            }
        }

        // Optimistically update stats strip
        const previousStats = queryClient.getQueryData<LeadStats>(['lead-stats']);
        if (previousStats && source.droppableId !== destination.droppableId) {
            queryClient.setQueryData<LeadStats>(['lead-stats'], {
                ...previousStats,
                by_stage: {
                    ...previousStats.by_stage,
                    [source.droppableId]: Math.max(0, (previousStats.by_stage[source.droppableId] || 0) - 1),
                    [destination.droppableId]: (previousStats.by_stage[destination.droppableId] || 0) + 1
                }
            });
        }

        // Trigger Stage Options Modal instead of immediate mutation
        if (source.droppableId !== destination.droppableId) {
            const leadName = previousLeads?.find((l: Lead) => l.id.toString() === draggableId)?.company_name || 'Lead';
            setTransitionModal({
                isOpen: true,
                leadId: draggableId,
                fromStage: source.droppableId,
                toStage: destination.droppableId,
                companyName: leadName
            });
        }
    };

    const handleCloseModal = async (save: boolean) => {
        if (!transitionModal) return;

        if (save) {
            // Loss reason is required for 'lost'
            if (transitionModal.toStage === 'lost' && !note.trim()) {
                alert("Please provide a loss reason.");
                return; // don't close
            }

            const updatePayload: any = { stage: transitionModal.toStage };

            // Map lead updates
            if (['proposal', 'negotiation', 'project', 'won'].includes(transitionModal.toStage) && dealValue !== '') {
                updatePayload.deal_value = Number(dealValue);
            }
            if (transitionModal.toStage === 'proposal' && proposalDate !== '') {
                updatePayload.proposal_deadline = proposalDate;
            }

            updateLead.mutate({ leadId: transitionModal.leadId, update: updatePayload });

            // Map Activity creation
            const activitiesToCreate = [];
            if (transitionModal.toStage === 'call' && note.trim()) {
                activitiesToCreate.push({ type: 'call', content: `Call Summary: ${note}`, metadata: { stage_moved_to: 'call' } });
            } else if (transitionModal.toStage === 'meeting' && (note.trim() || meetingDate)) {
                activitiesToCreate.push({
                    type: 'meeting',
                    content: note.trim() ? `Meeting Notes: ${note}` : 'Meeting Scheduled',
                    metadata: { meeting_date: meetingDate, stage_moved_to: 'meeting' }
                });
            } else if (transitionModal.toStage === 'lost' && note.trim()) {
                activitiesToCreate.push({ type: 'note', content: `Loss Reason: ${note}`, metadata: { stage_moved_to: 'lost' } });
            } else if (note.trim() && !['call', 'meeting', 'lost'].includes(transitionModal.toStage)) {
                activitiesToCreate.push({ type: 'note', content: note, metadata: { stage_moved_to: transitionModal.toStage } });
            }

            for (const act of activitiesToCreate) {
                await api.post(`/leads/${transitionModal.leadId}/activities`, act);
            }
        } else {
            // Revert optimistic updates
            queryClient.invalidateQueries({ queryKey: ['leads'] });
            queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
        }

        setTransitionModal(null);
        setDealValue('');
        setNote('');
        setMeetingDate('');
        setProposalDate('');
    };



    return (
        <Layout>
            <div className="h-full flex flex-col gap-6 p-8 max-w-[1800px] mx-auto">

                {/* ── Header ── */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 flex-shrink-0">
                    <div>
                        <div className="flex items-center gap-3 mb-1">
                            <div className="w-9 h-9 rounded-xl bg-indigo-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                                <Activity className="w-5 h-5 text-white" />
                            </div>
                            <h1 className="text-3xl font-black text-slate-100 italic tracking-tighter uppercase">
                                Pipeline <span className="text-indigo-500">Board</span>
                            </h1>
                        </div>
                        <p className="text-slate-500 text-xs font-bold uppercase tracking-widest pl-12">
                            Drag-and-drop view of your sales pipeline
                        </p>
                    </div>

                    {/* Search */}
                    <div className="flex items-center gap-3">
                        {isManager && (
                            <Button
                                onClick={() => setIsAddModalOpen(true)}
                                className="bg-indigo-500 hover:bg-indigo-600 text-white shadow-lg shadow-indigo-500/20 px-6 h-11 flex items-center gap-2 font-black italic tracking-tighter uppercase text-xs"
                            >
                                <UserPlus className="w-4 h-4" />
                                Add Lead
                            </Button>
                        )}
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                placeholder="Search leads..."
                                value={searchTerm}
                                onChange={e => setSearchTerm(e.target.value)}
                                className="bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-200 focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 outline-none transition-all w-64 font-medium"
                            />
                        </div>
                        {searchTerm && (
                            <Button variant="ghost" size="sm" onClick={() => setSearchTerm('')}
                                className="text-slate-500 hover:text-slate-300 text-xs">
                                Clear
                            </Button>
                        )}
                    </div>
                </div>

                {/* ── Stats Strip ── */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 flex-shrink-0">
                    {statsLoading ? (
                        Array.from({ length: 4 }).map((_, i) => (
                            <Skeleton key={i} className="h-28 rounded-2xl" />
                        ))
                    ) : (
                        <>
                            <EnhancedStatCard title="Total Leads" value={stats?.total || 0} icon={<BarChart3 className="w-5 h-5" />} variant="info" />
                            <EnhancedStatCard title="In Meeting" value={stats?.by_stage['meeting'] || 0} icon={<Clock className="w-5 h-5" />} variant="warning" />
                            <EnhancedStatCard title="In Negotiation" value={stats?.by_stage['negotiation'] || 0} icon={<TrendingUp className="w-5 h-5" />} variant="default" />
                            <EnhancedStatCard title="Deals Won" value={stats?.by_stage['won'] || 0} icon={<CheckCircle2 className="w-5 h-5" />} variant="success" />
                        </>
                    )}
                </div>

                {/* ── Table Board (Vertical Grouped Layout) ── */}
                <DragDropContext onDragStart={onDragStart} onDragEnd={onDragEnd}>
                    <div className="flex-1 overflow-y-auto pb-4 scroll-smooth space-y-6">

                        {leadsLoading ? (
                            <div className="space-y-4">
                                {Array.from({ length: 3 }).map((_, i) => (
                                    <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                                        <Skeleton className="h-6 w-1/4 mb-4 rounded-md" />
                                        <Skeleton className="h-12 mb-2 rounded-lg" />
                                        <Skeleton className="h-12 rounded-lg" />
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="space-y-6 min-w-[800px]">
                                {CRM_STAGES.map(stage => (
                                    <StageColumn key={stage.id} stage={stage} leads={leadsGrouped[stage.id] || []} />
                                ))}
                            </div>
                        )}
                    </div>
                </DragDropContext>
            </div>

            {/* Transition Modal */}
            {transitionModal && (
                <Modal
                    isOpen={transitionModal.isOpen}
                    onClose={() => handleCloseModal(false)}
                    title={`Move ${transitionModal.companyName}?`}
                >
                    <div className="space-y-5">
                        <div className="flex items-center gap-3 p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-200">
                            <span className="font-bold text-xs uppercase tracking-widest">{CRM_STAGES.find(s => s.id === transitionModal.fromStage)?.name}</span>
                            <MoreHorizontal className="w-4 h-4 text-indigo-500" />
                            <span className="font-bold text-xs uppercase tracking-widest text-indigo-400">{CRM_STAGES.find(s => s.id === transitionModal.toStage)?.name}</span>
                        </div>

                        <div className="space-y-4">
                            {/* CALL */}
                            {transitionModal.toStage === 'call' && (
                                <div className="space-y-1">
                                    <label className="text-xs font-black uppercase text-slate-400 tracking-widest px-1">Call Summary</label>
                                    <textarea
                                        placeholder="What was discussed?"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 outline-none transition-all h-24 resize-none"
                                        value={note}
                                        onChange={(e) => setNote(e.target.value)}
                                    />
                                </div>
                            )}

                            {/* MEETING */}
                            {transitionModal.toStage === 'meeting' && (
                                <>
                                    <div className="space-y-1">
                                        <label className="text-xs font-black uppercase text-slate-400 tracking-widest px-1">Meeting Date</label>
                                        <div className="relative">
                                            <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                                            <input
                                                type="datetime-local"
                                                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-11 pr-4 py-3 text-sm text-slate-200 focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 outline-none transition-all cursor-pointer"
                                                value={meetingDate}
                                                onChange={(e) => setMeetingDate(e.target.value)}
                                                onClick={(e) => {
                                                    try {
                                                        if ('showPicker' in HTMLInputElement.prototype) {
                                                            e.currentTarget.showPicker();
                                                        }
                                                    } catch (err) { }
                                                }}
                                            />
                                        </div>
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-xs font-black uppercase text-slate-400 tracking-widest px-1">Meeting Notes / Agenda</label>
                                        <textarea
                                            placeholder="Agenda or discussion points..."
                                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 outline-none transition-all h-24 resize-none"
                                            value={note}
                                            onChange={(e) => setNote(e.target.value)}
                                        />
                                    </div>
                                </>
                            )}

                            {/* PROPOSAL */}
                            {transitionModal.toStage === 'proposal' && (
                                <>
                                    <div className="space-y-1">
                                        <label className="text-xs font-black uppercase text-slate-400 tracking-widest px-1">Proposal Deadline</label>
                                        <div className="relative">
                                            <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                                            <input
                                                type="date"
                                                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-11 pr-4 py-3 text-sm text-slate-200 focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 outline-none transition-all cursor-pointer"
                                                value={proposalDate}
                                                onChange={(e) => setProposalDate(e.target.value)}
                                                onClick={(e) => {
                                                    try {
                                                        if ('showPicker' in HTMLInputElement.prototype) {
                                                            e.currentTarget.showPicker();
                                                        }
                                                    } catch (err) { }
                                                }}
                                            />
                                        </div>
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-xs font-black uppercase text-slate-400 tracking-widest px-1">Estimated Deal Value ($)</label>
                                        <input
                                            type="number"
                                            placeholder="e.g. 25000"
                                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 outline-none transition-all"
                                            value={dealValue}
                                            onChange={(e) => setDealValue(e.target.value)}
                                        />
                                    </div>
                                </>
                            )}

                            {/* GENERAL VALUE (Negotiation, Project, Won) */}
                            {['negotiation', 'project', 'won'].includes(transitionModal.toStage) && (
                                <div className="space-y-1">
                                    <label className="text-xs font-black uppercase text-slate-400 tracking-widest px-1">Confirmed Deal Value ($)</label>
                                    <input
                                        type="number"
                                        placeholder="e.g. 50000"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 outline-none transition-all"
                                        value={dealValue}
                                        onChange={(e) => setDealValue(e.target.value)}
                                    />
                                </div>
                            )}

                            {/* LOST */}
                            {transitionModal.toStage === 'lost' && (
                                <div className="space-y-1">
                                    <label className="text-xs font-black uppercase text-slate-400 tracking-widest px-1 flex justify-between">
                                        <span>Loss Reason</span>
                                        <span className="text-rose-500">Required</span>
                                    </label>
                                    <textarea
                                        placeholder="Why didn't this deal close?"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 focus:ring-2 focus:ring-rose-500/30 focus:border-rose-500 outline-none transition-all h-24 resize-none"
                                        value={note}
                                        onChange={(e) => setNote(e.target.value)}
                                        required
                                    />
                                </div>
                            )}

                            {/* GENERIC NOTE FOR NON-SPECIFIC */}
                            {['lead', 'negotiation', 'project', 'won'].includes(transitionModal.toStage) && (
                                <div className="space-y-1">
                                    <label className="text-xs font-black uppercase text-slate-400 tracking-widest px-1">Add Note (Optional)</label>
                                    <textarea
                                        placeholder="Anything to add?"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 outline-none transition-all h-24 resize-none"
                                        value={note}
                                        onChange={(e) => setNote(e.target.value)}
                                    />
                                </div>
                            )}
                        </div>

                        <div className="flex items-center justify-end gap-3 pt-3">
                            <Button variant="ghost" onClick={() => handleCloseModal(false)} className="text-slate-400 hover:text-rose-400 transition-colors">
                                Cancel Move
                            </Button>
                            <Button variant="primary" onClick={() => handleCloseModal(true)} className="bg-indigo-500 hover:bg-indigo-600 shadow-xl shadow-indigo-500/20">
                                Confirm & Update
                            </Button>
                        </div>
                    </div>
                </Modal>
            )}

            <AddLeadModal
                isOpen={isAddModalOpen}
                onClose={() => setIsAddModalOpen(false)}
            />
        </Layout>
    );
};

export default LeadsPipeline;

