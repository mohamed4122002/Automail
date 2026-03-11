import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import Layout from "../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { StatsCard } from "../components/ui/StatsCard";
import { EnhancedStatCard } from "../components/ui/EnhancedStatCard";
import { CampaignHeader } from "../components/ui/CampaignHeader";
import { WorkflowVisualizationCard } from "../components/ui/WorkflowVisualizationCard";
import { RecentActivityFeed } from "../components/ui/RecentActivityFeed";
import { TimeSeriesChart } from "../components/charts/TimeSeriesChart";
import { EngagementHeatmap } from "../components/charts/EngagementHeatmap";
import { DataTable } from "../components/ui/DataTable";
import { ContactDrawer } from "../components/ui/ContactDrawer";
import { useDataTable } from "../hooks/useDataTable";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator
} from "../components/ui/dropdown-menu";
import { Input } from "../components/ui/input";
import api from "../lib/api";
import { toast } from "sonner";
import { useGlobalWebSocket } from "../context/WebSocketContext";
import {
  ArrowLeft,
  Edit,
  Send,
  BookOpen,
  MousePointerClick,
  AlertCircle,
  UserCheck,
  Zap,
  CheckCircle2,
  TrendingUp,
  Settings as SettingsIcon,
  Save,
  Mail,
  XCircle,
  UserMinus,
  Reply,
  Target,
  Search,
  Filter,
  MoreHorizontal,
  Download,
  Trash2,
  Tag,
  Layers,
  PauseCircle,
  PlayCircle,
  ChevronRight,
  Info,
  Activity,
  History as HistoryIcon
} from "lucide-react";
import classNames from "classnames";
import { useQueryClient } from "@tanstack/react-query";
interface Recipient {
  id: string;
  email: string;
  status: string;
  last_activity: string;
}

interface Campaign {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  contact_list_id: string | null;
  created_at: string;
  updated_at: string;
  warmup_config: {
    enabled: boolean;
    initial_volume: number;
    daily_increase_pct: number;
    max_volume: number;
    current_limit: number;
  };
  warmup_last_limit_increase: string | null;
}

interface ContactList {
  id: string;
  name: string;
  contact_count: number;
}

const CampaignDetail: React.FC = () => {
  const { id } = useParams();
  const [activeTab, setActiveTab] = useState<"overview" | "workflow" | "recipients" | "settings">("overview");
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [contactLists, setContactLists] = useState<ContactList[]>([]);
  const [selectedContactList, setSelectedContactList] = useState<ContactList | null>(null);
  const [workflow, setWorkflow] = useState<any>(null);
  const [progress, setProgress] = useState({ processed: 0, total: 0 });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activating, setActivating] = useState(false);

  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [workflowViz, setWorkflowViz] = useState<any>(null);
  const [recentActivity, setRecentActivity] = useState<any[]>([]);
  const [isNodeDrawerOpen, setIsNodeDrawerOpen] = useState(false);
  const [selectedNode, setSelectedNode] = useState<any>(null);

  const [isTestDrawerOpen, setIsTestDrawerOpen] = useState(false);
  const [testEmail, setTestEmail] = useState("");
  const [testResult, setTestResult] = useState<any>(null);
  const [isSimulating, setIsSimulating] = useState(false);

  // Advanced Workflow Systematization State
  const [availableWorkflows, setAvailableWorkflows] = useState<any[]>([]);
  const [workflowSelectionOpen, setWorkflowSelectionOpen] = useState(false);
  const [swappingWorkflow, setSwappingWorkflow] = useState(false);

  // WebSocket for real-time campaign events
  const { lastMessage } = useGlobalWebSocket();
  const queryClient = useQueryClient(); // Added useQueryClient hook

  useEffect(() => {
    if (lastMessage) {
      const message = lastMessage;
      // Filter for events belonging to this campaign
      if (message.type === 'event' && message.campaign_id === id) {
        setRecentActivity(prev => [message as any, ...prev].slice(0, 50));
        queryClient.invalidateQueries({ queryKey: ["campaign", id] });
        queryClient.invalidateQueries({ queryKey: ["campaign-events", id] });
      }
    }
  }, [lastMessage, id, queryClient]);

  // Recipients state
  const {
    data: recipients,
    setData: setRecipients,
    selection,
    setSelection,
    toggleSelection,
    toggleAll,
    sortConfig,
    handleSort,
    page,
    setPage,
    pageSize,
    setPageSize,
    total,
    setTotal
  } = useDataTable<any>([]);

  const [recipientsLoading, setRecipientsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedRecipientId, setSelectedRecipientId] = useState<string | null>(null);
  const [drawerRecipient, setDrawerRecipient] = useState<any>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Fetch recipients
  const fetchRecipients = async () => {
    if (!id) return;
    setRecipientsLoading(true);
    try {
      const params: any = {
        page,
        page_size: pageSize,
        sort_by: sortConfig.key,
        order: sortConfig.direction
      };

      if (searchQuery) params.search = searchQuery;
      if (statusFilter !== "all") params.status_filter = statusFilter;

      const res = await api.get(`/campaigns/${id}/recipients`, { params });
      setRecipients(res.data.recipients);
      setTotal(res.data.total);
    } catch (err) {
      console.error("Failed to fetch recipients", err);
      toast.error("Failed to load recipients");
    } finally {
      setRecipientsLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "recipients") {
      fetchRecipients();
    }
  }, [activeTab, page, pageSize, sortConfig, searchQuery, statusFilter]);

  // Handle drawer open
  const handleRecipientClick = async (recipient: any) => {
    setSelectedRecipientId(recipient.id); // Assuming ID is the key
    setDrawerOpen(true);
    setDrawerLoading(true);

    try {
      if (recipient.user_id) {
        const res = await api.get(`/campaigns/${id}/recipients/${recipient.user_id}`);
        setDrawerRecipient(res.data);
      } else {
        // Fallback to minimal data if ID is missing (should not happen with new schema)
        setDrawerRecipient({
          ...recipient,
          events: [],
          total_opens: recipient.total_opens || 0,
          total_clicks: recipient.total_clicks || 0
        });
      }

    } catch (err) {
      console.error(err);
      toast.error("Failed to load recipient details");
    } finally {
      setDrawerLoading(false);
    }
  };

  // Bulk Actions
  const handleBulkAction = async (action: string) => {
    if (!id || selection.size === 0) return;

    const recipientIds = Array.from(selection);
    const confirmMsg = action === 'remove'
      ? `Are you sure you want to remove ${recipientIds.length} recipients from this campaign?`
      : `Apply '${action}' to ${recipientIds.length} recipients?`;

    if (!window.confirm(confirmMsg)) return;

    try {
      await api.post(`/campaigns/${id}/recipients/bulk`, {
        action,
        recipient_ids: recipientIds
      });

      toast.success(`Bulk ${action} successful`);
      setSelection(new Set());
      fetchRecipients();
    } catch (err) {
      console.error(err);
      toast.error(`Failed to perform ${action}`);
    }
  };

  // Export
  const handleRecipientsExport = async () => {
    if (!id) return;
    try {
      const params: any = {
        format: 'csv'
      };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter !== "all") params.status_filter = statusFilter;
      if (selection.size > 0) params.recipient_ids = Array.from(selection);

      const res = await api.post(`/campaigns/${id}/recipients/export`, params, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `campaign_${id}_recipients.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error(err);
      toast.error("Export failed");
    }
  };

  // Stats for the detail cards (placeholders till we have a real analytics endpoint for this campaign)
  const [stats, setStats] = useState({
    sent: 0,
    delivered: 0,
    opened: 0,
    clicked: 0,
    bounce_rate: 0
  });

  const [warmupStatus, setWarmupStatus] = useState({
    enabled: false,
    current_limit: 0,
    sent_today: 0,
    max_volume: 0,
    progress_pct: 0
  });

  const fetchCampaignDetails = async () => {
    if (!id) return;
    setLoading(true);
    try {
      // 1. Fetch core data that must succeed
      const [campRes, listsRes] = await Promise.all([
        api.get(`/campaigns/${id}`),
        api.get("/contacts/lists")
      ]);

      setCampaign(campRes.data);
      setContactLists(listsRes.data);

      if (campRes.data.workflow) {
        setWorkflow(campRes.data.workflow);
      }

      // Find and set selected contact list
      if (campRes.data.contact_list_id) {
        const list = listsRes.data.find((l: ContactList) => l.id === campRes.data.contact_list_id);
        if (list) {
          setSelectedContactList(list);
          setProgress({ processed: 0, total: list.contact_count });
        }
      }

      // 2. Fetch non-critical data that can fail gracefully
      try {
        const [analyticRes, vizRes, warmupRes] = await Promise.all([
          api.get(`/campaigns/${id}/analytics`),
          api.get(`/campaigns/${id}/workflow`),
          api.get(`/campaigns/${id}/warmup-status`)
        ]);

        setAnalyticsData(analyticRes.data);
        setWorkflowViz(vizRes.data);
        setWarmupStatus(warmupRes.data);

        // Update stats from analytics
        if (analyticRes.data.metrics) {
          setStats({
            sent: analyticRes.data.metrics.sent,
            delivered: analyticRes.data.metrics.delivered,
            opened: analyticRes.data.metrics.opened,
            clicked: analyticRes.data.metrics.clicked,
            bounce_rate: analyticRes.data.metrics.bounce_rate
          });
        }
      } catch (subErr) {
        console.warn("Some campaign data failed to load:", subErr);
        // We don't toast here to avoid annoying the user if non-critical data is missing
      }

    } catch (err) {
      console.error("Failed to fetch critical campaign details", err);
      toast.error("Failed to load campaign data");
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableWorkflows = async () => {
    try {
      const res = await api.get("/workflows");
      // Filter out the current workflow from selection if it exists
      setAvailableWorkflows(res.data.filter((wf: any) => wf.campaign_id !== id));
    } catch (err) {
      console.error("Failed to fetch available workflows", err);
    }
  };

  const handleSwapWorkflow = async (workflowId: string) => {
    setSwappingWorkflow(true);
    try {
      await api.put(`/campaigns/${id}/workflow?workflow_id=${workflowId}`);
      toast.success("Campaign workflow updated successfully!");
      setWorkflowSelectionOpen(false);
      fetchCampaignDetails();
    } catch (err) {
      console.error("Failed to swap workflow", err);
      toast.error("Failed to update campaign workflow");
    } finally {
      setSwappingWorkflow(false);
    }
  };

  useEffect(() => {
    fetchCampaignDetails();
  }, [id]);

  useEffect(() => {
    if (workflowSelectionOpen) {
      fetchAvailableWorkflows();
    }
  }, [workflowSelectionOpen]);

  const handleUpdateCampaign = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!campaign) return;
    setSaving(true);
    try {
      await api.patch(`/campaigns/${id}`, {
        name: campaign.name,
        description: campaign.description,
        contact_list_id: campaign.contact_list_id,
        warmup_config: campaign.warmup_config
      });

      toast.success('Campaign settings synchronized', {
        description: 'Changes are now live and broadcasted to the dashboard feed.'
      });

      const statusRes = await api.get(`/campaigns/${id}/warmup-status`);
      setWarmupStatus(statusRes.data);
    } catch (err) {
      console.error("Failed to update campaign", err);
      toast.error('Failed to sync settings');
    } finally {
      setSaving(false);
    }
  };

  // Quick action handlers
  const handleUpdateDescription = async (description: string) => {
    try {
      await api.patch(`/campaigns/${id}`, { description });
      setCampaign(prev => prev ? { ...prev, description } : null);
      toast.success('Description updated successfully');
    } catch (err) {
      console.error('Failed to update description', err);
      toast.error('Failed to update description');
      throw err;
    }
  };

  const handleSendTestEmail = async () => {
    setIsTestDrawerOpen(true);
    setTestEmail("");
    setTestResult(null);
  };

  const handleRunSimulation = async () => {
    if (!testEmail || !testEmail.includes("@")) {
      toast.error("Valid email required for simulation");
      return;
    }
    setIsSimulating(true);
    setTestResult(null);

    try {
      // Simulate real-time lead pulse through the workflow
      const nodes = workflowViz?.nodes || [];
      const simulatedHits: string[] = [];

      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];
        simulatedHits.push(node.id);
        setTestResult({ current: node.id, hits: [...simulatedHits] });
        await new Promise(r => setTimeout(r, 800)); // Lead pulse speed
      }

      toast.success("Sequence verified successfully", {
        description: `Path validated for ${testEmail}`
      });
    } catch (err) {
      toast.error("Simulation interrupted");
    } finally {
      setIsSimulating(false);
    }
  };

  const handleDuplicate = async () => {
    const newName = prompt('Enter name for duplicated campaign:', `${campaign?.name} (Copy)`);
    if (!newName) return;

    try {
      const res = await api.post(`/campaigns/${id}/duplicate`, {
        new_name: newName,
        copy_workflow: true,
        copy_contacts: true
      });
      toast.success('Campaign duplicated successfully');
      // Optionally redirect to new campaign
      window.location.href = `/campaigns/${res.data.campaign_id}`;
    } catch (err) {
      console.error('Failed to duplicate campaign', err);
      toast.error('Failed to duplicate campaign');
    }
  };

  const handleExport = async () => {
    try {
      const response = await api.get(`/campaigns/${id}/export?format=csv&include_recipients=true&include_analytics=true`, {
        responseType: 'blob'
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `campaign_${id}_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      toast.success('Campaign data exported successfully');
    } catch (err) {
      console.error('Failed to export data', err);
      toast.error('Failed to export data');
    }
  };

  const handleArchive = async () => {
    if (!confirm('Are you sure you want to archive this campaign?')) return;

    try {
      await api.patch(`/campaigns/${id}`, { is_active: false, archived: true });
      toast.success('Campaign archived');
      window.location.href = '/campaigns';
    } catch (err) {
      console.error('Failed to archive campaign', err);
      toast.error('Failed to archive campaign');
    }
  };

  const handleToggleActivation = async () => {
    if (!campaign) return;

    // Optimistic update
    const previousState = campaign.is_active;
    setCampaign({ ...campaign, is_active: !previousState });
    setActivating(true);

    try {
      if (previousState) {
        await api.post(`/campaigns/${id}/pause`);
        toast.success('Campaign paused', {
          icon: <PauseCircle className="w-4 h-4 text-amber-500" />,
          description: 'Automatic workflow processing suspended.'
        });
      } else {
        await api.post(`/campaigns/${id}/activate`);
        toast.success('Campaign Successfully Launched!', {
          icon: <PlayCircle className="w-5 h-5 text-emerald-400" />,
          description: 'The dispatch sequence has been initialized. Leads are now flowing through your workflow.',
          duration: 5000
        });
      }
      // Refresh campaign data from server to ensure sync
      const res = await api.get(`/campaigns/${id}`);
      setCampaign(res.data);
    } catch (err: any) {
      console.error("Failed to toggle campaign status", err);
      const errorMsg = err.response?.data?.detail || 'Failed to update status';
      toast.error(errorMsg);
      // Rollback on error
      setCampaign(prev => prev ? { ...prev, is_active: previousState } : null);
    } finally {
      setActivating(false);
    }
  };

  const handleNodeClick = (node: any) => {
    if (!node) return;
    setSelectedNode(node);
    setIsNodeDrawerOpen(true);
  };

  const updateWarmupField = (field: string, value: any) => {
    if (!campaign) return;
    setCampaign({
      ...campaign,
      warmup_config: {
        ...campaign.warmup_config,
        [field]: value
      }
    });
  };

  if (loading) {
    return (
      <Layout title="Campaign Details">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
        </div>
      </Layout>
    );
  }

  if (!campaign) {
    return (
      <Layout title="Campaign Details">
        <div className="text-center py-20">
          <h2 className="text-2xl font-bold">Campaign not found</h2>
          <Link to="/campaigns" className="text-indigo-400 mt-4 block">Back to Campaigns</Link>
        </div>
      </Layout>
    );
  }

  // Enhanced stat cards with real data
  const enhancedStats = analyticsData ? [
    {
      title: "Emails Sent",
      value: analyticsData.metrics.sent,
      icon: <Send className="w-5 h-5" />,
      description: "Total emails dispatched",
      variant: 'default' as const,
      trend: analyticsData.metrics.sent_trend ? {
        value: analyticsData.metrics.sent_trend,
        direction: analyticsData.metrics.sent_trend > 0 ? 'up' as const : 'down' as const
      } : undefined,
      tooltip: "Total number of emails sent from this campaign"
    },
    {
      title: "Delivered",
      value: analyticsData.metrics.delivered,
      icon: <CheckCircle2 className="w-5 h-5" />,
      description: `${analyticsData.metrics.delivery_rate.toFixed(1)}% Delivery Rate`,
      variant: 'success' as const,
      format: 'number' as const,
      tooltip: "Emails successfully delivered (sent - bounced)"
    },
    {
      title: "Opened",
      value: analyticsData.metrics.opened,
      icon: <Mail className="w-5 h-5" />,
      description: `${analyticsData.metrics.open_rate.toFixed(1)}% Open Rate`,
      variant: 'info' as const,
      trend: analyticsData.metrics.opened_trend ? {
        value: analyticsData.metrics.opened_trend,
        direction: analyticsData.metrics.opened_trend > 0 ? 'up' as const : 'down' as const
      } : undefined,
      tooltip: "Unique recipients who opened the email"
    },
    {
      title: "Clicked",
      value: analyticsData.metrics.clicked,
      icon: <MousePointerClick className="w-5 h-5" />,
      description: `${analyticsData.metrics.click_rate.toFixed(1)}% Click Rate`,
      variant: 'info' as const,
      trend: analyticsData.metrics.clicked_trend ? {
        value: analyticsData.metrics.clicked_trend,
        direction: analyticsData.metrics.clicked_trend > 0 ? 'up' as const : 'down' as const
      } : undefined,
      tooltip: "Unique recipients who clicked a link"
    },
    {
      title: "Bounced",
      value: analyticsData.metrics.bounced,
      icon: <XCircle className="w-5 h-5" />,
      description: `${analyticsData.metrics.bounce_rate.toFixed(1)}% Bounce Rate`,
      variant: 'danger' as const,
      tooltip: "Emails that failed to deliver"
    },
    {
      title: "Unsubscribed",
      value: analyticsData.metrics.unsubscribed,
      icon: <UserMinus className="w-5 h-5" />,
      description: "Opted out",
      variant: 'warning' as const,
      tooltip: "Recipients who unsubscribed"
    },
    {
      title: "Replied",
      value: analyticsData.metrics.replied,
      icon: <Reply className="w-5 h-5" />,
      description: "Direct responses",
      variant: 'success' as const,
      tooltip: "Recipients who replied to the email"
    },
    {
      title: "Converted",
      value: analyticsData.metrics.converted,
      icon: <Target className="w-5 h-5" />,
      description: `${analyticsData.metrics.conversion_rate.toFixed(1)}% Conversion Rate`,
      variant: 'success' as const,
      tooltip: "Recipients who completed the desired action"
    },
  ] : [];

  return (
    <Layout title="Campaign Details">
      <div className="flex flex-col gap-6">
        {/* Enhanced Header */}
        <CampaignHeader
          campaign={campaign}
          workflow={workflow}
          contactList={selectedContactList ? {
            id: selectedContactList.id,
            name: selectedContactList.name,
            total_contacts: selectedContactList.contact_count
          } : null}
          progress={progress}
          onToggleActivation={handleToggleActivation}
          onUpdateDescription={handleUpdateDescription}
          onSendTestEmail={handleSendTestEmail}
          onDuplicate={handleDuplicate}
          onExport={handleExport}
          onArchive={handleArchive}
          isActivating={activating}
        />

        {/* Tabs */}
        <div className="border-b border-slate-700/50">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: "overview", label: "Overview", icon: TrendingUp },
              { id: "workflow", label: "Workflow", icon: Zap },
              { id: "recipients", label: "Recipients", icon: UserCheck },
              { id: "settings", label: "Campaign Controls", icon: SettingsIcon },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={classNames(
                  "pb-4 px-1 border-b-2 font-medium text-sm transition-all flex items-center gap-2",
                  activeTab === tab.id
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-300"
                )}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {/* Enhanced Stats Grid - 8 Cards */}
            {analyticsData && enhancedStats.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {enhancedStats.map((stat, index) => (
                  <EnhancedStatCard key={index} {...stat} />
                ))}
              </div>
            )}

            {/* Charts Row */}
            {analyticsData && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Time Series Chart */}
                <Card className="border-slate-700/30 bg-slate-800/40">
                  <CardHeader>
                    <CardTitle>Performance Over Time</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <TimeSeriesChart
                      data={analyticsData.time_series || []}
                      height={300}
                    />
                  </CardContent>
                </Card>

                {/* Engagement Heatmap */}
                <Card className="border-slate-700/30 bg-slate-800/40">
                  <CardHeader>
                    <CardTitle>Engagement Heatmap</CardTitle>
                    <p className="text-sm text-slate-400">Best times to send emails</p>
                  </CardHeader>
                  <CardContent>
                    <EngagementHeatmap data={analyticsData.heatmap || []} />
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Workflow Visualization & Activity Feed */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Workflow Visualization */}
              {workflowViz && (
                <WorkflowVisualizationCard
                  workflowId={workflowViz.workflow_id}
                  workflowName={workflowViz.workflow_name}
                  isActive={workflowViz.is_active}
                  nodes={workflowViz.nodes}
                  nodeStats={workflowViz.node_stats.map((ns: any) => ({
                    ...ns,
                    avg_duration: (analyticsData as any)?.node_performance?.[ns.node_id] || 0
                  }))}
                  totalInstances={workflowViz.total_instances}
                  activeInstances={workflowViz.active_instances}
                  completedInstances={workflowViz.completed_instances}
                  onNodeClick={handleNodeClick}
                />
              )}

              {/* Recent Activity Feed */}
              <RecentActivityFeed
                events={recentActivity}
                maxItems={10}
              />
            </div>

            {/* Real-time Execution Health */}
            <Card className="border-slate-700/50 bg-slate-800/30 backdrop-blur-sm shadow-xl">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-indigo-400" />
                  Real-time Execution Health
                </CardTitle>
              </CardHeader>
              <CardContent>
                {warmupStatus.enabled ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8 py-4">
                    <div className="space-y-4">
                      <div className="flex justify-between items-end">
                        <div className="space-y-1">
                          <p className="text-sm text-slate-400 uppercase tracking-wider font-semibold">Reputation Warm-up Phase</p>
                          <p className="text-xs text-slate-500">Gradual volume scaling is active</p>
                        </div>
                        <span className="text-indigo-400 font-bold text-lg">{warmupStatus.sent_today} / {warmupStatus.current_limit}</span>
                      </div>
                      <div className="h-4 bg-slate-700/50 rounded-full overflow-hidden border border-slate-600/30">
                        <div className="h-full bg-gradient-to-r from-indigo-600 to-indigo-400 rounded-full transition-all duration-1000 shadow-[0_0_10px_rgba(99,102,241,0.5)]" style={{ width: `${warmupStatus.progress_pct}%` }}></div>
                      </div>
                      <div className="flex justify-between items-center text-[10px] text-slate-500 uppercase tracking-widest font-bold">
                        <span>Daily Starting Line</span>
                        <span>Capacity Target</span>
                      </div>
                    </div>
                    <div className="bg-indigo-500/5 border border-indigo-500/10 rounded-2xl p-5 flex items-start gap-5 relative overflow-hidden group">
                      <div className="absolute top-0 right-0 p-8 bg-indigo-500/5 rounded-full -mr-10 -mt-10 group-hover:scale-110 transition-transform duration-500"></div>
                      <div className="bg-indigo-500/20 p-3 rounded-xl">
                        <Zap className="w-8 h-8 text-indigo-400" />
                      </div>
                      <div className="relative z-10">
                        <h4 className="text-slate-100 font-bold mb-1">Domain Health Forecast</h4>
                        <p className="text-sm text-slate-300 leading-relaxed">
                          Your current daily growth is set to <b>{campaign.warmup_config.daily_increase_pct}%</b>.
                          At this rate, you will hit your target reach of <b>{campaign.warmup_config.max_volume}</b> in {Math.ceil(Math.log(campaign.warmup_config.max_volume / warmupStatus.current_limit) / Math.log(1 + campaign.warmup_config.daily_increase_pct / 100))} days.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center p-8 text-sm text-slate-400 rounded-2xl bg-slate-800/50 border border-slate-700 border-dashed justify-center text-center">
                    <div className="max-w-xs space-y-3">
                      <Zap className="w-10 h-10 mx-auto text-slate-600 opacity-50" />
                      <p className="text-slate-300 font-medium">Warm-up mode is currently bypassed.</p>
                      <p className="text-xs text-slate-500 leading-relaxed">System is processing leads immediately. Recommended for established domains only.</p>
                      <Button variant="ghost" size="sm" onClick={() => setActiveTab("settings")} className="text-indigo-400">Activate Scaled Delivery</Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Workflow Tab */}
        {activeTab === "workflow" && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {/* Workflow Header Stats */}
            {workflowViz && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="bg-slate-800/40 border-slate-700/30 p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-500/10 rounded-lg">
                      <UserCheck className="w-5 h-5 text-indigo-400" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Active Leads</p>
                      <p className="text-2xl font-black text-slate-100">{workflowViz.active_instances}</p>
                    </div>
                  </div>
                </Card>
                <Card className="bg-slate-800/40 border-slate-700/30 p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-500/10 rounded-lg">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Completed</p>
                      <p className="text-2xl font-black text-slate-100">{workflowViz.completed_instances}</p>
                    </div>
                  </div>
                </Card>
                <Card className="bg-slate-800/40 border-slate-700/30 p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-500/10 rounded-lg">
                      <Layers className="w-5 h-5 text-slate-400" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Total Throughput</p>
                      <p className="text-2xl font-black text-slate-100">{workflowViz.total_instances}</p>
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {/* Main Workflow Visualization & Selector */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <div className="xl:col-span-2 space-y-6">
                {workflowViz ? (
                  <WorkflowVisualizationCard
                    workflowId={workflowViz.workflow_id}
                    workflowName={workflowViz.workflow_name}
                    isActive={workflowViz.is_active}
                    nodes={workflowViz.nodes}
                    nodeStats={workflowViz.node_stats}
                    totalInstances={workflowViz.total_instances}
                    activeInstances={workflowViz.active_instances}
                    completedInstances={workflowViz.completed_instances}
                    onOpenEditor={() => window.open(`/workflows/${workflowViz.workflow_id}/edit`, '_blank')}
                    onNodeClick={handleNodeClick}
                  />
                ) : (
                  <Card className="h-[400px] flex items-center justify-center bg-slate-800/20 border-dashed border-slate-700">
                    <div className="text-center text-slate-500">
                      <Zap className="w-12 h-12 mx-auto mb-4 opacity-10" />
                      <p>No workflow visualization available</p>
                    </div>
                  </Card>
                )}
              </div>

              <div className="space-y-6">
                <Card className="border-indigo-500/20 bg-slate-800/40 shadow-xl overflow-hidden relative">
                  <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500 shadow-[0_0_15px_rgba(99,102,241,0.5)]"></div>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <SettingsIcon className="w-5 h-5 text-indigo-400" />
                        Workflow Swap
                      </div>
                      <Badge variant="outline" className="bg-indigo-500/10 text-indigo-400 border-indigo-500/30 uppercase tracking-tighter font-black text-[10px]">
                        Advanced
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-sm text-slate-400 leading-relaxed">
                      Need to pivot your strategy? You can swap the underlying workflow at any time. New leads will follow the new journey immediately.
                    </p>
                    <Button
                      className="w-full bg-indigo-600 hover:bg-indigo-500 shadow-[0_0_20px_rgba(79,70,229,0.3)] gap-2 py-6 text-lg font-bold"
                      onClick={() => setWorkflowSelectionOpen(true)}
                    >
                      <Layers className="w-5 h-5" />
                      Change Workflow
                    </Button>
                    <div className="p-3 bg-red-500/5 rounded-xl border border-red-500/10 mt-4">
                      <div className="flex gap-3">
                        <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                        <p className="text-[10px] text-red-300 font-medium">
                          Existing leads will continue on their current workflow version. Only new leads entering after the swap will use the new sequence.
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Micro Feed for this tab */}
                <Card className="border-slate-800 bg-slate-900/30 overflow-hidden">
                  <div className="p-3 border-b border-slate-800 bg-slate-950/20 flex items-center justify-between">
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Workflow Execution Logs</span>
                  </div>
                  <div className="max-h-[300px] overflow-y-auto">
                    <RecentActivityFeed
                      events={recentActivity.filter(e => e.event_type === 'WORKFLOW_NODE_ENTER' || e.event_type === 'campaign_config_updated')}
                      maxItems={5}
                    />
                  </div>
                </Card>
              </div>
            </div>

            {/* Workflow Selection Drawer/Overlay */}
            {workflowSelectionOpen && (
              <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-300">
                <div
                  className="absolute inset-0"
                  onClick={() => setWorkflowSelectionOpen(false)}
                ></div>
                <Card className="w-full max-w-4xl max-h-[80vh] bg-slate-900 border-slate-700 shadow-2xl relative z-10 flex flex-col overflow-hidden">
                  <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/30">
                    <div>
                      <h3 className="text-xl font-black text-slate-100">Select Workflow</h3>
                      <p className="text-sm text-slate-400">Choose a sequence to drive this campaign</p>
                    </div>
                    <Button
                      variant="ghost"
                      onClick={() => setWorkflowSelectionOpen(false)}
                      className="text-slate-400 hover:text-white"
                    >
                      <Search className="w-5 h-5 rotate-45" />
                    </Button>
                  </div>

                  <div className="flex-1 overflow-y-auto p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {availableWorkflows.length > 0 ? (
                        availableWorkflows.map((wf: any) => (
                          <div
                            key={wf.id}
                            className={classNames(
                              "p-5 rounded-2xl border transition-all cursor-pointer group relative overflow-hidden",
                              "bg-slate-800/40 border-slate-700/50 hover:border-indigo-500/50 hover:bg-slate-800/80"
                            )}
                            onClick={() => handleSwapWorkflow(wf.id)}
                          >
                            <div className="absolute top-0 right-0 p-10 bg-indigo-500/5 rounded-full -mr-12 -mt-12 group-hover:scale-125 transition-transform duration-500"></div>
                            <div className="flex justify-between items-start mb-4 relative z-10">
                              <div className="p-2.5 bg-indigo-500/10 rounded-xl">
                                <Zap className="w-5 h-5 text-indigo-400" />
                              </div>
                              {swappingWorkflow && (
                                <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                              )}
                            </div>
                            <h4 className="font-bold text-slate-100 group-hover:text-indigo-400 transition-colors relative z-10">{wf.name}</h4>
                            <p className="text-xs text-slate-400 mt-2 line-clamp-2 relative z-10">{wf.description || 'No description provided.'}</p>
                            <div className="mt-4 flex items-center gap-3 relative z-10">
                              <Badge variant="outline" className="bg-slate-950/50 text-slate-500 border-slate-800 text-[10px] uppercase font-bold">
                                {wf.nodes?.length || 0} Nodes
                              </Badge>
                              {wf.is_active && (
                                <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px] uppercase font-bold">
                                  Currently Active
                                </Badge>
                              )}
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="col-span-2 py-12 text-center text-slate-500">
                          <Layers className="w-12 h-12 mx-auto mb-4 opacity-10" />
                          <p>No other workflows available.</p>
                          <Button variant="link" className="text-indigo-400 mt-2" onClick={() => window.open('/workflows', '_blank')}>Create a new workflow</Button>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="p-4 border-t border-slate-800 bg-slate-950/20 flex justify-end">
                    <Button variant="ghost" onClick={() => setWorkflowSelectionOpen(false)} className="text-slate-400 font-bold uppercase tracking-widest text-xs">Cancel</Button>
                  </div>
                </Card>
              </div>
            )}
          </div>
        )}

        {activeTab === "recipients" && (
          <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {/* Filters & Actions Bar */}
            <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center bg-slate-800/30 p-4 rounded-lg border border-slate-700/30 backdrop-blur-sm">
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <div className="relative w-full sm:w-64">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
                  <Input
                    type="text"
                    placeholder="Search by email or name..."
                    className="pl-9 bg-slate-900/50 border-slate-700 focus:border-indigo-500 w-full"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="border-slate-700 bg-slate-800 text-slate-300 gap-2">
                      <Filter className="w-4 h-4" />
                      {statusFilter === 'all' ? 'All Status' : statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="bg-slate-800 border-slate-700 text-slate-200">
                    <DropdownMenuItem onClick={() => setStatusFilter("all")}>All Status</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter("sent")}>Sent</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter("opened")}>Opened</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter("clicked")}>Clicked</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter("bounced")}>Bounced</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter("unsubscribed")}>Unsubscribed</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              <div className="flex items-center gap-2">
                {selection.size > 0 && (
                  <div className="flex items-center gap-2 mr-2 animate-in fade-in slide-in-from-right-4">
                    <span className="text-sm text-slate-400 hidden md:inline">{selection.size} selected</span>
                    <Button size="sm" variant="danger" onClick={() => handleBulkAction('remove')} className="gap-2">
                      <Trash2 className="w-4 h-4" /> <span className="hidden sm:inline">Remove</span>
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => handleBulkAction('tag')} className="gap-2 bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border-indigo-500/20">
                      <Tag className="w-4 h-4" /> <span className="hidden sm:inline">Tag</span>
                    </Button>
                  </div>
                )}
                <Button variant="outline" className="border-slate-700 bg-slate-800 text-slate-300 gap-2" onClick={handleRecipientsExport}>
                  <Download className="w-4 h-4" /> Export
                </Button>
              </div>
            </div>

            {/* Data Table */}
            <DataTable
              data={recipients}
              columns={[
                {
                  key: "email",
                  header: "Recipient",
                  sortable: true,
                  cell: (item) => (
                    <div>
                      <div className="font-medium text-slate-200">{item.name || "Unknown"}</div>
                      <div className="text-sm text-slate-400">{item.email}</div>
                    </div>
                  )
                },
                {
                  key: "status",
                  header: "Status",
                  sortable: true,
                  cell: (item) => {
                    const colors: any = {
                      sent: "bg-blue-500/10 text-blue-400 border-blue-500/20",
                      opened: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
                      clicked: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
                      bounced: "bg-red-500/10 text-red-400 border-red-500/20",
                      unsubscribed: "bg-slate-500/10 text-slate-400 border-slate-500/20"
                    };
                    return (
                      <Badge variant="outline" className={colors[item.status] || "bg-slate-500/10 text-slate-400"}>
                        {item.status.toUpperCase()}
                      </Badge>
                    );
                  }
                },
                {
                  key: "engagement_score",
                  header: "Score",
                  sortable: true,
                  cell: (item) => (
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-indigo-500 to-purple-500"
                          style={{ width: `${item.engagement_score}%` }}
                        ></div>
                      </div>
                      <span className="text-xs text-slate-400">{item.engagement_score}</span>
                    </div>
                  )
                },
                {
                  key: "sent_at",
                  header: "Sent",
                  sortable: true,
                  cell: (item) => (
                    <span className="text-sm text-slate-400">
                      {item.sent_at ? new Date(item.sent_at).toLocaleDateString() : "-"}
                    </span>
                  )
                },
                {
                  key: "actions",
                  header: "",
                  cell: (item) => (
                    <Button variant="ghost" size="sm" onClick={() => handleRecipientClick(item)}>
                      <MoreHorizontal className="w-4 h-4 text-slate-400" />
                    </Button>
                  )
                }
              ]}
              keyField="email" // Should use ID if available, using email for unique key
              selection={selection}
              onToggleSelection={toggleSelection}
              onToggleAll={toggleAll}
              sortConfig={sortConfig}
              onSort={handleSort}
              page={page}
              pageSize={pageSize}
              total={total}
              onPageChange={setPage}
              isLoading={recipientsLoading}
              emptyMessage={
                <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                  <UserCheck className="w-12 h-12 mb-4 opacity-10" />
                  <p>No recipients found matching your filters.</p>
                </div>
              }
            />

            <ContactDrawer
              isOpen={drawerOpen}
              onClose={() => setDrawerOpen(false)}
              recipient={drawerRecipient}
              loading={drawerLoading}
            />
          </div>
        )}

        {activeTab === "settings" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="lg:col-span-8 space-y-8">
              {/* Campaign Targeting */}
              <Card className="border-indigo-500/20 bg-slate-800/40 shadow-xl overflow-hidden backdrop-blur-md relative">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 opacity-50"></div>
                <CardHeader className="pb-4">
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-3 text-xl">
                      <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
                        <Target className="w-5 h-5 text-indigo-400" />
                      </div>
                      Audience Targeting
                    </CardTitle>
                    <Badge variant="outline" className="bg-indigo-500/5 text-indigo-300 border-indigo-500/20">
                      Primary Pipeline
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="p-6 bg-slate-900/40 rounded-2xl border border-slate-700/30">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-bold text-slate-300 uppercase tracking-widest flex items-center gap-2">
                          <UserCheck className="w-4 h-4 text-emerald-400" />
                          Master Contact List
                        </label>
                        <span className="text-[10px] text-slate-500 font-mono">ID: {campaign.contact_list_id || "UNASSIGNED"}</span>
                      </div>
                      <div className="relative group">
                        <select
                          value={campaign.contact_list_id || ""}
                          onChange={(e) => setCampaign({ ...campaign, contact_list_id: e.target.value })}
                          className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-3.5 focus:ring-2 focus:ring-indigo-500 outline-none appearance-none transition-all group-hover:border-slate-500 cursor-pointer text-slate-100"
                        >
                          <option value="">-- No list selected --</option>
                          {contactLists.map(list => (
                            <option key={list.id} value={list.id}>
                              {list.name} — {list.contact_count} Professional Leads
                            </option>
                          ))}
                        </select>
                        <div className="absolute right-4 top-4 pointer-events-none text-slate-500 group-hover:text-indigo-400 transition-colors">
                          <ChevronRight className="w-5 h-5 rotate-90" />
                        </div>
                      </div>
                      <div className="flex items-start gap-3 bg-indigo-500/5 p-4 rounded-lg border border-indigo-500/10">
                        <Info className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                        <p className="text-xs text-slate-400 leading-relaxed">
                          By linking this list, the campaign will monitor for new entries.
                          <span className="text-indigo-300 ml-1">Automated sync is currently LIVE.</span> Any contact added to this list will immediately enter step 1 of your workflow.
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Warm-up Configuration */}
              <Card className="border-emerald-500/20 bg-slate-800/40 shadow-xl overflow-hidden backdrop-blur-md">
                <CardHeader>
                  <CardTitle className="flex items-center gap-3 text-xl text-slate-100">
                    <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                      <Zap className="w-5 h-5 text-amber-400" />
                    </div>
                    Growth & Reputation Strategy
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-10">
                    <div className="flex items-center justify-between p-6 bg-gradient-to-r from-slate-900/60 to-slate-900/20 rounded-2xl border border-slate-700/50">
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-500 ${campaign.warmup_config.enabled ? 'bg-indigo-500 shadow-[0_0_20px_rgba(99,102,241,0.4)]' : 'bg-slate-700 opacity-50'}`}>
                          <TrendingUp className={`w-6 h-6 ${campaign.warmup_config.enabled ? 'text-white' : 'text-slate-400'}`} />
                        </div>
                        <div>
                          <h4 className="font-bold text-slate-100 text-lg">Intelligent Throttle System</h4>
                          <p className="text-sm text-slate-400">Protects your sender score with gradual volume scaling.</p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => updateWarmupField("enabled", !campaign.warmup_config.enabled)}
                        className={classNames(
                          "relative inline-flex h-8 w-14 items-center rounded-full transition-all focus:outline-none ring-offset-2 ring-offset-slate-900 focus:ring-2 focus:ring-indigo-500",
                          campaign.warmup_config.enabled ? "bg-indigo-600" : "bg-slate-700"
                        )}
                      >
                        <span className={classNames(
                          "inline-block h-6 w-6 transform rounded-full bg-white transition-all shadow-xl",
                          campaign.warmup_config.enabled ? "translate-x-7" : "translate-x-1"
                        )} />
                      </button>
                    </div>

                    <div className={classNames("grid grid-cols-1 md:grid-cols-3 gap-8 transition-all duration-700", !campaign.warmup_config.enabled && "opacity-30 grayscale pointer-events-none blur-[1px]")}>
                      <div className="space-y-4">
                        <div className="flex justify-between items-end">
                          <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">Base Flow</label>
                          <span className="text-indigo-400 font-mono text-sm">{campaign.warmup_config.initial_volume}</span>
                        </div>
                        <input
                          type="range"
                          min="1"
                          max="100"
                          value={campaign.warmup_config.initial_volume}
                          onChange={(e) => updateWarmupField("initial_volume", parseInt(e.target.value))}
                          className="w-full accent-indigo-500 bg-slate-700 rounded-lg appearance-none h-1.5 cursor-pointer"
                        />
                        <p className="text-[10px] text-slate-500 italic">Initial leads per day on launch.</p>
                      </div>

                      <div className="space-y-4">
                        <div className="flex justify-between items-end">
                          <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">Growth Surge</label>
                          <span className="text-indigo-400 font-mono text-sm">+{campaign.warmup_config.daily_increase_pct}%</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="50"
                          step="0.5"
                          value={campaign.warmup_config.daily_increase_pct}
                          onChange={(e) => updateWarmupField("daily_increase_pct", parseFloat(e.target.value))}
                          className="w-full accent-indigo-500 bg-slate-700 rounded-lg appearance-none h-1.5 cursor-pointer"
                        />
                        <p className="text-[10px] text-slate-500 italic">Daily increase in volume throughput.</p>
                      </div>

                      <div className="space-y-4">
                        <div className="flex justify-between items-end">
                          <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">Peak Cap</label>
                          <span className="text-indigo-400 font-mono text-sm">{campaign.warmup_config.max_volume}</span>
                        </div>
                        <input
                          type="range"
                          min="100"
                          max="10000"
                          step="100"
                          value={campaign.warmup_config.max_volume}
                          onChange={(e) => updateWarmupField("max_volume", parseInt(e.target.value))}
                          className="w-full accent-indigo-500 bg-slate-700 rounded-lg appearance-none h-1.5 cursor-pointer"
                        />
                        <p className="text-[10px] text-slate-500 italic">Maximum sustained daily volume.</p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-8 border-t border-slate-700/50">
                      <div className="flex items-center gap-3 text-slate-400 text-xs">
                        <Activity className="w-4 h-4 text-emerald-500 animate-pulse" />
                        <span>Real-time persistence active</span>
                      </div>
                      <Button
                        onClick={() => handleUpdateCampaign()}
                        isLoading={saving}
                        leftIcon={<Save className="w-4 h-4" />}
                        className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-xl shadow-indigo-500/20 px-10 h-12 rounded-xl text-md font-bold"
                      >
                        Push Updates to Cloud
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-4 space-y-6">
              <Card className="bg-slate-900/60 border-slate-700/50 shadow-2xl relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2 text-slate-300 uppercase tracking-tighter">
                    <HistoryIcon className="w-4 h-4 text-slate-500" />
                    Operational Health
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/30 space-y-3">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-400">Throttling Status:</span>
                      <span className={classNames("px-2 py-0.5 rounded text-[10px] font-bold uppercase", campaign.warmup_config.enabled ? "bg-emerald-500/10 text-emerald-400" : "bg-slate-700/50 text-slate-500")}>
                        {campaign.warmup_config.enabled ? "Active" : "Disabled"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-400">Current Ceiling:</span>
                      <span className="text-slate-100 font-mono">{warmupStatus.current_limit} / day</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-emerald-500 to-indigo-500"
                        style={{ width: `${(warmupStatus.sent_today / (warmupStatus.current_limit || 1)) * 100}%` }}
                      ></div>
                    </div>
                    <p className="text-[10px] text-slate-500 text-right font-mono">
                      {warmupStatus.sent_today} sent today
                    </p>
                  </div>

                  <div className="space-y-3">
                    <h5 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                      <CheckCircle2 className="w-3 h-3 text-indigo-400" />
                      Safety Protocol
                    </h5>
                    <ul className="space-y-2">
                      {[
                        "Protects domain reputation from spikes.",
                        "Intelligent bounce-rate monitoring.",
                        "Distributed processing clusters."
                      ].map((item, i) => (
                        <li key={i} className="flex items-start gap-2 text-[11px] text-slate-400">
                          <span className="text-indigo-500 mt-1">●</span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-emerald-500/5 border-emerald-500/20 shadow-lg border-dashed">
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center text-center space-y-3">
                    <div className="p-3 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                      <Mail className="w-6 h-6 text-emerald-400" />
                    </div>
                    <h4 className="text-sm font-bold text-slate-100 italic">Advanced Testing Suite</h4>
                    <p className="text-[10px] text-slate-400 leading-relaxed px-4">
                      Simulate individual contact journeys before going live. Verified leads ensure 100% workflow accuracy.
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full border-emerald-500/20 hover:bg-emerald-500/10 text-emerald-400 text-xs"
                      onClick={handleSendTestEmail}
                    >
                      Trigger Test Simulation
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Prominent Launch Button - Quick Access */}
              {!campaign.is_active && (
                <div className="pt-4 animate-in fade-in slide-in-from-top-4 duration-1000">
                  <Button
                    onClick={handleToggleActivation}
                    isLoading={activating}
                    className="w-full bg-emerald-600 hover:bg-emerald-500 shadow-2xl shadow-emerald-500/30 py-8 rounded-2xl text-lg font-black italic tracking-tighter gap-3 border-t border-white/20"
                  >
                    <PlayCircle className="w-8 h-8" />
                    GO LIVE NOW
                  </Button>
                  <p className="text-[10px] text-emerald-500/60 text-center mt-3 font-bold uppercase tracking-widest">
                    Campaign ready for immediate dispatch
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Node Inspector Drawer */}
        <div className={classNames(
          "fixed inset-y-0 right-0 w-96 bg-slate-900 border-l border-slate-700 shadow-2xl z-50 transform transition-transform duration-300 backdrop-blur-xl bg-opacity-95",
          isNodeDrawerOpen ? "translate-x-0" : "translate-x-full"
        )}>
          {selectedNode && (
            <div className="flex flex-col h-full">
              <div className="p-6 border-b border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-indigo-500/20">
                    <Layers className="w-5 h-5 text-indigo-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-100">{selectedNode.label}</h3>
                    <p className="text-[10px] text-slate-500 uppercase tracking-widest">{selectedNode.type}</p>
                  </div>
                </div>
                <button onClick={() => setIsNodeDrawerOpen(false)} className="text-slate-500 hover:text-white transition-colors">
                  <XCircle className="w-6 h-6" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-8">
                <section className="space-y-4">
                  <h4 className="text-xs font-bold text-indigo-400 uppercase">Real-time Performance</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700">
                      <p className="text-[10px] text-slate-500 uppercase">Leads Processing</p>
                      <p className="text-2xl font-bold text-slate-100">{selectedNode.stats?.leads_active || 0}</p>
                    </div>
                    <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700">
                      <p className="text-[10px] text-slate-500 uppercase">Success Rate</p>
                      <p className="text-2xl font-bold text-emerald-400">{selectedNode.stats?.success_rate?.toFixed(1) || 0}%</p>
                    </div>
                  </div>
                </section>

                <section className="space-y-4">
                  <h4 className="text-xs font-bold text-indigo-400 uppercase">Node Configuration</h4>
                  <div className="space-y-3 p-4 rounded-xl bg-slate-800/30 border border-slate-700/50">
                    {Object.entries(selectedNode.config || {}).map(([key, value]: [string, any]) => (
                      <div key={key} className="flex justify-between text-xs">
                        <span className="text-slate-500 capitalize">{key}:</span>
                        <span className="text-slate-300 font-mono">{JSON.stringify(value)}</span>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="space-y-4">
                  <h4 className="text-xs font-bold text-indigo-400 uppercase">Recent Activity</h4>
                  <div className="space-y-2">
                    <div className="p-3 rounded-lg bg-slate-800/20 border border-slate-700/20 text-[10px] text-slate-500 italic text-center">
                      Detailed event streaming for this node is coming soon.
                    </div>
                  </div>
                </section>
              </div>

              <div className="p-6 border-t border-slate-700">
                <Button variant="outline" className="w-full border-slate-700 text-slate-400" onClick={() => setIsNodeDrawerOpen(false)}>
                  Close Inspector
                </Button>
              </div>
            </div>
          )}
        </div>
        {isNodeDrawerOpen && <div className="fixed inset-0 bg-black/40 z-40" onClick={() => setIsNodeDrawerOpen(false)}></div>}

        {/* Test Flow Drawer */}
        <div className={classNames(
          "fixed inset-y-0 right-0 w-[500px] bg-slate-950 border-l border-emerald-500/20 shadow-2xl z-50 transform transition-transform duration-500 backdrop-blur-2xl bg-opacity-95",
          isTestDrawerOpen ? "translate-x-0" : "translate-x-full"
        )}>
          <div className="flex flex-col h-full">
            <div className="p-8 border-b border-white/5 flex items-center justify-between">
              <div>
                <h3 className="text-xl font-black text-slate-100 italic tracking-tight">LeadPulse™ Simulator</h3>
                <p className="text-xs text-emerald-500 font-bold uppercase tracking-widest mt-1">Ready for Dry-Run</p>
              </div>
              <button onClick={() => setIsTestDrawerOpen(false)} className="text-slate-600 hover:text-white transition-colors">
                <XCircle className="w-8 h-8" />
              </button>
            </div>

            <div className="flex-1 p-8 space-y-8 overflow-y-auto">
              <div className="space-y-4">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] block">Target Simulation Subject</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                    <Mail className="w-5 h-5 text-slate-600 group-focus-within:text-emerald-400 transition-colors" />
                  </div>
                  <input
                    value={testEmail}
                    onChange={(e) => setTestEmail(e.target.value)}
                    placeholder="e.g. prospect@fortune500.com"
                    className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500/50 rounded-2xl pl-12 pr-4 py-4 text-slate-100 placeholder:text-slate-700 outline-none transition-all ring-0 focus:ring-4 focus:ring-emerald-500/5"
                  />
                </div>
                <p className="text-[10px] text-slate-600 italic leading-relaxed">
                  Simulation will run the selected contact through your current workflow logic in real-time mode.
                </p>
              </div>

              {testResult && (
                <div className="space-y-6 animate-in fade-in duration-500">
                  <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Execution Trace</h4>
                  <div className="space-y-3">
                    {workflowViz?.nodes?.map((node: any, i: number) => {
                      const isHit = testResult.hits.includes(node.id);
                      const isCurrent = testResult.current === node.id;
                      return (
                        <div
                          key={node.id}
                          className={classNames(
                            "flex items-center gap-4 p-4 rounded-2xl border transition-all duration-300",
                            isCurrent ? "bg-emerald-500/10 border-emerald-500/50 scale-[1.02] shadow-lg shadow-emerald-500/10" :
                              isHit ? "bg-slate-800/40 border-slate-700/50 opacity-60" : "bg-slate-900/40 border-slate-800/40 opacity-20"
                          )}
                        >
                          <div className={classNames(
                            "w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs",
                            isHit ? "bg-emerald-500 text-slate-950" : "bg-slate-800 text-slate-500"
                          )}>
                            {isHit ? <CheckCircle2 className="w-4 h-4" /> : i + 1}
                          </div>
                          <div className="flex-1">
                            <p className="text-sm font-bold text-slate-200">{node.label}</p>
                            <p className="text-[10px] text-slate-500 uppercase">{node.type}</p>
                          </div>
                          {isCurrent && (
                            <div className="flex items-center gap-1 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-black animate-pulse">
                              <Zap className="w-3 h-3" />
                              PULSE
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            <div className="p-8 border-t border-white/5 bg-slate-900/30">
              <Button
                className="w-full h-14 bg-emerald-600 hover:bg-emerald-500 text-lg font-bold rounded-2xl shadow-xl shadow-emerald-900/20 gap-3"
                onClick={handleRunSimulation}
                disabled={isSimulating}
                isLoading={isSimulating}
                leftIcon={<PlayCircle className="w-6 h-6" />}
              >
                Initiate dry-run simulation
              </Button>
            </div>
          </div>
        </div>
        {isTestDrawerOpen && <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity" onClick={() => setIsTestDrawerOpen(false)}></div>}
      </div>
    </Layout >
  );
};

export default CampaignDetail;
