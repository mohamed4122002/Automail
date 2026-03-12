import React, { useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/layout/Layout";
import { StatsCard } from "../components/ui/StatsCard";
import { Button } from "../components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { LiveActivityFeed } from "../components/dashboard/LiveActivityFeed";
import { EmailQueueWidget } from "../components/dashboard/EmailQueueWidget";
import { ABTestingWidget } from "../components/dashboard/ABTestingWidget";
import { ReputationWidget } from "../components/dashboard/ReputationWidget";

import { WorkerStatusIndicator } from "../components/system/WorkerStatus";
import CRMTargetWidget from "../components/dashboard/CRMTargetWidget";
import RevenueForecast from "../components/admin/RevenueForecast";
import { Send, MousePointerClick, BookOpen, Clock, ArrowUpRight, Filter, Flame, X, BarChart3 } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useGlobalWebSocket } from "../context/WebSocketContext";
import api from "../lib/api";
import { monitoringService } from "../services/monitoring";
import { Skeleton } from "../components/ui/Skeleton";

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

  // Global WebSocket Context
  const { lastMessage } = useGlobalWebSocket();

  React.useEffect(() => {
    if (!lastMessage) return;

    // Handle Hot Lead Alerts globally on Dashboard
    if (lastMessage.is_hot_lead) {
      setHotLead(lastMessage);
      playPing();
      showBrowserNotification(lastMessage.user_email);

      // Auto-hide toast after 8 seconds
      setTimeout(() => setHotLead(null), 8000);
    }
  }, [lastMessage]);

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

  if (error) {
    return (
      <Layout title="Dashboard">
        <div className="text-red-500">Error loading dashboard data.</div>
      </Layout>
    )
  }

  const { stats, chart_data } = data || { stats: [], chart_data: [] };
  const metrics = stats[0] || {
    total_emails_sent: 0,
    open_rate: 0,
    click_rate: 0,
    pending_followups: 0,
    sent_trend: 0,
    open_rate_trend: 0,
    click_rate_trend: 0,
    pending_trend: 0
  };

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
      value: `${metrics.open_rate}% `,
      trend: { value: metrics.open_rate_trend, isPositive: metrics.open_rate_trend > 0 },
      icon: <BookOpen className="w-5 h-5" />,
      description: "Avg performance"
    },
    {
      title: "Click Rate",
      value: `${metrics.click_rate}% `,
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
        {isLoading ? (
          <>
            {[1, 2, 3, 4].map((i) => (
              <Card key={i} className="p-6">
                <Skeleton className="h-4 w-24 mb-4" />
                <Skeleton className="h-8 w-32 mb-2" />
                <Skeleton className="h-4 w-20" />
              </Card>
            ))}
          </>
        ) : (
          statCards.map((stat, index) => (
            <StatsCard key={index} {...stat} />
          ))
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 mt-8 lg:grid-cols-3">
        <RevenueForecast />
        <CRMTargetWidget />
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Performance Overview</CardTitle>
            <Link to="/analytics/performance">
              <Button variant="ghost" size="sm" className="text-indigo-400 font-bold hover:bg-indigo-500/10">
                <BarChart3 className="w-4 h-4 mr-2" />
                Full Stats
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              {isLoading ? (
                <div className="w-full h-full flex flex-col space-y-4">
                  <div className="flex-1 w-full bg-slate-800/20 rounded-lg overflow-hidden relative">
                    <Skeleton className="absolute inset-0 h-full w-full" />
                  </div>
                  <div className="h-4 w-full flex space-x-4">
                    {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} className="flex-1 h-2" />)}
                  </div>
                </div>
              ) : (
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
              )}
            </div>
          </CardContent>
        </Card>

        <ABTestingWidget />
        <ReputationWidget />
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
