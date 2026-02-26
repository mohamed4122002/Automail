import React from "react";
import Layout from "../components/layout/Layout";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Table, Column } from "../components/ui/TableCustom";
import { Badge } from "../components/ui/Badge";
import { Plus, Eye, Trash2, MoreHorizontal, Activity, TrendingUp, Users, Send } from "lucide-react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { LiveActivityFeed } from "../components/dashboard/LiveActivityFeed";
import api from "../lib/api";

interface Campaign {
  id: string;
  name: string;
  description?: string;
  date: string;
  status: string;
  is_active: boolean;
  stats?: {
    sent: number;
    open_rate: string;
    click_rate: string;
  }
}

const Campaigns: React.FC = () => {
  const { data: campaigns, isLoading } = useQuery<Campaign[]>({
    queryKey: ['campaigns'],
    queryFn: async () => {
      const res = await api.get("/campaigns");
      return res.data;
    }
  });

  const getStatusBadge = (campaign: Campaign) => {
    if (!campaign.is_active) return <Badge variant="warning" className="bg-orange-500/10 text-orange-400 border-orange-500/20">Paused</Badge>;

    switch (campaign.status) {
      case "active": return <Badge variant="success" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">Active</Badge>;
      case "completed": return <Badge variant="info" className="bg-indigo-500/10 text-indigo-400 border-indigo-500/20">Completed</Badge>;
      case "draft": return <Badge variant="neutral" className="bg-slate-500/10 text-slate-400 border-slate-500/20">Draft</Badge>;
      default: return <Badge>Unknown</Badge>;
    }
  };

  const columns: Column<Campaign>[] = [
    {
      header: "Campaign",
      accessor: (item) => (
        <div className="flex flex-col">
          <span className="font-bold text-slate-100 text-sm">{item.name}</span>
          <span className="text-xs text-slate-500 truncate max-w-[200px]">{item.description || 'No description'}</span>
        </div>
      )
    },
    {
      header: "Status",
      accessor: (item) => getStatusBadge(item)
    },
    {
      header: "Reach",
      accessor: (item) => (
        <div className="flex items-center gap-2">
          <Users className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-sm font-medium text-slate-300">{item.stats?.sent || 0}</span>
        </div>
      )
    },
    {
      header: "Engagement",
      accessor: (item) => (
        <div className="flex items-center gap-4">
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-500 uppercase font-bold">Open</span>
            <span className="text-sm text-emerald-400 font-bold">{item.stats?.open_rate || '0%'}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-500 uppercase font-bold">Click</span>
            <span className="text-sm text-blue-400 font-bold">{item.stats?.click_rate || '0%'}</span>
          </div>
        </div>
      )
    },
    {
      header: "Actions",
      accessor: (item) => (
        <div className="flex items-center gap-2">
          <Link to={`/campaigns/${item.id}`}>
            <Button variant="secondary" size="sm" className="bg-slate-800 border-slate-700 hover:bg-slate-700 h-8 px-3">
              Manage
            </Button>
          </Link>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-500 hover:text-slate-300">
            <MoreHorizontal className="w-4 h-4" />
          </Button>
        </div>
      )
    },
  ];

  return (
    <Layout title="Campaigns Management">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-slate-100 tracking-tight">Active Campaigns</h2>
              <p className="text-slate-500 text-sm">Monitor and optimize your outreach performance in real-time.</p>
            </div>
            <Link to="/campaigns/new">
              <Button
                variant="primary"
                className="bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-500/20"
                leftIcon={<Plus className="w-4 h-4 shadow-sm" />}
              >
                Create Campaign
              </Button>
            </Link>
          </div>

          <Card className="border-slate-800 bg-slate-900/50 backdrop-blur-xl p-0 overflow-hidden shadow-2xl">
            <Table
              data={campaigns || []}
              columns={columns}
              keyExtractor={(item) => item.id}
              isLoading={isLoading}
              pagination={{
                currentPage: 1,
                totalPages: 1,
                onPageChange: () => { }
              }}
            />
          </Card>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="bg-slate-900/40 border-slate-800 p-4 flex items-center gap-4">
              <div className="p-3 bg-emerald-500/10 rounded-xl">
                <TrendingUp className="w-6 h-6 text-emerald-400" />
              </div>
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider text-dense">Avg Open Rate</p>
                <p className="text-2xl font-black text-slate-100">32.4%</p>
              </div>
            </Card>
            <Card className="bg-slate-900/40 border-slate-800 p-4 flex items-center gap-4">
              <div className="p-3 bg-blue-500/10 rounded-xl">
                <Activity className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider text-dense">Avg Click Rate</p>
                <p className="text-2xl font-black text-slate-100">8.1%</p>
              </div>
            </Card>
            <Card className="bg-slate-900/40 border-slate-800 p-4 flex items-center gap-4">
              <div className="p-3 bg-indigo-500/10 rounded-xl">
                <Send className="w-6 h-6 text-indigo-400" />
              </div>
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider text-dense">Monthly Sent</p>
                <p className="text-2xl font-black text-slate-100">12.5k</p>
              </div>
            </Card>
          </div>
        </div>

        <div className="lg:col-span-1">
          <LiveActivityFeed />
        </div>
      </div>
    </Layout>
  );
};

export default Campaigns;
