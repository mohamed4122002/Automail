import React, { useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/layout/Layout";
import { StatsCard } from "../components/ui/StatsCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { LiveActivityFeed } from "../components/dashboard/LiveActivityFeed";
import { EmailQueueWidget } from "../components/dashboard/EmailQueueWidget";
import { ABTestingWidget } from "../components/dashboard/ABTestingWidget";
import { ReputationWidget } from "../components/dashboard/ReputationWidget";
import { InfrastructureWidget } from "../components/dashboard/InfrastructureWidget";
import { WorkerStatusIndicator } from "../components/system/WorkerStatus";
import { Send, MousePointerClick, BookOpen, Clock, ArrowUpRight, Filter, Flame, X } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useWebSocket } from "../hooks/useWebSocket";
import api from "../lib/api";
import { monitoringService } from "../services/monitoring";

const Dashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>("");
  const [selectedCampaign, setSelectedCampaign] = useState<string>("");
  const [hotLead, setHotLead] = useState<any>(null);

  // Sound effect using Web Audio API
  const playPing = () => {
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();

      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); // A5
      oscillator.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.5);

      gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);

      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);

      oscillator.start();
      oscillator.stop(audioCtx.currentTime + 0.5);
    } catch (e) {
      console.error("Audio play failed", e);
    }
  };

  // Browser notification
  const showBrowserNotification = (userEmail: string) => {
    if (!("Notification" in window)) return;

    if (Notification.permission === "granted") {
      new Notification("🔥 Hot Lead Detected!", {
        body: `${userEmail} just clicked a link in your campaign!`,
        icon: "/favicon.ico"
      });
    } else if (Notification.permission !== "denied") {
      Notification.requestPermission().then(permission => {
        if (permission === "granted") {
          showBrowserNotification(userEmail);
        }
      });
    }
  };

  // WebSocket for real-time events
  const { isConnected, lastMessage } = useWebSocket(`ws://${window.location.host}/api/ws/dashboard`, {
    onMessage: (message) => {
      // 1. Refetch dashboard data on any outreach event
      if (message.type === 'event') {
        queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      }

      // 2. Handle Hot Lead Alerts
      if (message.is_hot_lead) {
        setHotLead(message);
        playPing();
        showBrowserNotification(message.user_email);

        // Auto-hide toast after 8 seconds
        setTimeout(() => setHotLead(null), 8000);
      }
    }
  });

  // Fetch workflows for filter dropdown
  const { data: workflows } = useQuery({
    queryKey: ['workflows'],
    queryFn: async () => {
      const response = await api.get("/workflows");
      return response.data;
    }
  });

  // Fetch campaigns for filter dropdown
  const { data: campaigns } = useQuery({
    queryKey: ['campaigns'],
    queryFn: async () => {
      const response = await api.get("/campaigns");
      return response.data;
    }
  });

  const { data: systemStats } = useQuery({
    queryKey: ['system-stats'],
    queryFn: () => monitoringService.getSystemStats(),
    refetchInterval: 60000 // Refresh every minute
  });

  const { data: infraStats } = useQuery({
    queryKey: ['infra-stats'],
    queryFn: () => monitoringService.getInfrastructureStats(),
    refetchInterval: 30000 // Refresh every 30s
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', selectedWorkflow, selectedCampaign],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedWorkflow) params.append('workflow_id', selectedWorkflow);
      if (selectedCampaign) params.append('campaign_id', selectedCampaign);

      const response = await api.get(`/analytics/dashboard?${params.toString()}`);
      return response.data;
    }
  });

  if (isLoading) {
    return (
      <Layout title="Dashboard">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout title="Dashboard">
        <div className="text-red-500">Error loading dashboard data.</div>
      </Layout>
    )
  }

  const { stats, chart_data, recent_activity } = data;

  // Transform API stats to match UI component
  // Note: API returns a list with one object potentially, based on service logic.
  // Let's assume the first item in stats list is what we need based on schema.
  const metrics = stats[0];

  const statCards = [
    {
      title: "Total Emails Sent",
      value: metrics.total_emails_sent.toLocaleString(),
      trend: { value: metrics.sent_trend, isPositive: metrics.sent_trend > 0 },
      icon: <Send className="w-5 h-5" />,
      description: "vs. last month"
    },
    {
      title: "Open Rate",
      value: `${metrics.open_rate}%`,
      trend: { value: metrics.open_rate_trend, isPositive: metrics.open_rate_trend > 0 },
      icon: <BookOpen className="w-5 h-5" />,
      description: "Avg performance"
    },
    {
      title: "Click Rate",
      value: `${metrics.click_rate}%`,
      trend: { value: metrics.click_rate_trend, isPositive: metrics.click_rate_trend > 0 },
      icon: <MousePointerClick className="w-5 h-5" />,
      description: "vs. last month"
    },
    {
      title: "Pending Follow-ups",
      value: metrics.pending_followups,
      trend: { value: metrics.pending_trend, isPositive: metrics.pending_trend < 0 }, // assuming down is good for pending?
      icon: <Clock className="w-5 h-5" />
    },
  ];

  return (
    <Layout title="Dashboard">
      {/* Worker Status Indicator */}
      <div className="mb-4">
        <WorkerStatusIndicator />
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat, index) => (
          <StatsCard key={index} {...stat} />
        ))}
        {systemStats && (
          <Card className="bg-slate-800/40 border-indigo-500/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">System Health</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-400">Emails Queued</span>
                  <span className="text-slate-100 font-mono">{systemStats.metrics.emails_queued}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-400">Active Workflows</span>
                  <span className="text-slate-100 font-mono">{systemStats.metrics.active_workflows}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-400">Events (24h)</span>
                  <span className="text-slate-100 font-mono">{systemStats.metrics.events_24h}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 mt-8 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Performance Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chart_data}>
                  <defs>
                    <linearGradient id="colorOpens" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorClicks" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke="#334155" strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                    itemStyle={{ color: '#f8fafc' }}
                  />
                  <Area type="monotone" dataKey="opens" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#colorOpens)" />
                  <Area type="monotone" dataKey="clicks" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorClicks)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <ABTestingWidget />
        <ReputationWidget />
        {infraStats && <InfrastructureWidget data={infraStats} />}
        <EmailQueueWidget />
        <LiveActivityFeed />
      </div>

      {/* Hot Lead Toast Overlay */}
      {hotLead && (
        <div className="fixed bottom-6 right-6 z-50 animate-in fade-in slide-in-from-right-10 duration-500">
          <Card className="bg-indigo-600 border-indigo-500 shadow-2xl shadow-indigo-500/20 w-80 overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-emerald-400"></div>
            <CardContent className="p-4">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center shrink-0">
                  <Flame className="text-white w-6 h-6 animate-pulse" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-white font-bold text-sm">HOT LEAD DETECTED</h4>
                  <p className="text-indigo-100 text-xs truncate mt-0.5">
                    {hotLead.user_email}
                  </p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-[10px] bg-emerald-400/20 text-emerald-300 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">
                      Just Clicked
                    </span>
                    <Link
                      to={`/users/${hotLead.user_id}`}
                      className="text-[10px] text-white underline hover:text-emerald-300 font-bold uppercase tracking-wider"
                    >
                      View Lead →
                    </Link>
                  </div>
                </div>
                <button
                  onClick={() => setHotLead(null)}
                  className="text-indigo-200 hover:text-white transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </Layout>
  );
};

export default Dashboard;
