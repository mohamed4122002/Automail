import React, { useEffect, useState } from "react";
import axios from "axios";
import { useAuth } from "../auth/AuthContext";
import Layout from "../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Calendar, CheckCircle2, XCircle, ExternalLink, RefreshCw } from "lucide-react";
import { toast } from "sonner";

interface IntegrationStatus {
    google_calendar: {
        connected: boolean;
        email: string | null;
    };
}

const CalendarIntegrations: React.FC = () => {
    const { token } = useAuth();
    const [status, setStatus] = useState<IntegrationStatus | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchStatus = async () => {
        try {
            const res = await axios.get("/api/integrations/status", {
                headers: { Authorization: `Bearer ${token}` }
            });
            setStatus(res.data);
        } catch (err) {
            console.error("Failed to fetch integration status", err);
            toast.error("Failed to load status");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
    }, [token]);

    const handleConnect = async () => {
        try {
            // In a real app, this would redirect to Google
            // Here we provide the auth URL
            const res = await axios.get("/api/integrations/google/auth", {
                params: { redirect_uri: `${window.location.origin}/auth/google/callback` },
                headers: { Authorization: `Bearer ${token}` }
            });
            window.location.href = res.data.auth_url;
        } catch (err) {
            toast.error("Failed to start OAuth flow");
        }
    };

    const handleDisconnect = async () => {
        if (!confirm("Are you sure you want to disconnect your Google Calendar?")) return;
        try {
            await axios.delete("/api/integrations/google", {
                headers: { Authorization: `Bearer ${token}` }
            });
            toast.success("Disconnected successfully");
            fetchStatus();
        } catch (err) {
            toast.error("Failed to disconnect");
        }
    };

    if (loading) return <div className="p-8 text-slate-400">Loading integrations...</div>;

    return (
        <Layout>
            <div className="max-w-4xl mx-auto space-y-6">
                <header>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Calendar Integrations</h1>
                    <p className="text-slate-400 mt-2">Connect your external calendars to sync meetings and schedule team activities.</p>
                </header>

                <Card className="bg-slate-900/50 border-slate-800 backdrop-blur-sm">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-blue-500/10 rounded-lg">
                                <Calendar className="w-6 h-6 text-blue-400" />
                            </div>
                            <div>
                                <CardTitle className="text-xl">Google Calendar</CardTitle>
                                <p className="text-sm text-slate-500 mt-1">Sync your schedule and allow team leaders to assign meetings.</p>
                            </div>
                        </div>
                        {status?.google_calendar.connected ? (
                            <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 gap-1.5 py-1 px-3">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                Connected
                            </Badge>
                        ) : (
                            <Badge className="bg-slate-500/10 text-slate-400 border-slate-500/20 gap-1.5 py-1 px-3">
                                <XCircle className="w-3.5 h-3.5" />
                                Disconnected
                            </Badge>
                        )}
                    </CardHeader>
                    <CardContent className="pt-4">
                        <div className="flex items-center justify-between p-4 bg-slate-950/50 rounded-xl border border-slate-800/50">
                            <div className="space-y-1">
                                <p className="text-sm font-medium text-slate-300">
                                    {status?.google_calendar.connected
                                        ? `Connected as: ${status.google_calendar.email || 'Authorized Account'}`
                                        : "Enhance your workflow by connecting your Google account."}
                                </p>
                                <p className="text-xs text-slate-500">
                                    {status?.google_calendar.connected
                                        ? "Your calendar is synced and ready for scheduling."
                                        : "Permissions: View and manage your primary Google Calendar events."}
                                </p>
                            </div>

                            <div className="flex gap-2">
                                {status?.google_calendar.connected ? (
                                    <>
                                        <Button variant="outline" size="sm" onClick={fetchStatus} title="Refresh sync status">
                                            <RefreshCw className="w-4 h-4" />
                                        </Button>
                                        <Button variant="danger" size="sm" onClick={handleDisconnect}>
                                            Disconnect
                                        </Button>
                                    </>
                                ) : (
                                    <Button className="bg-blue-600 hover:bg-blue-500 text-white gap-2 px-6" onClick={handleConnect}>
                                        <ExternalLink className="w-4 h-4" />
                                        Connect Google Calendar
                                    </Button>
                                )}
                            </div>
                        </div>

                        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="p-4 rounded-xl bg-slate-800/30 border border-slate-800/50">
                                <h3 className="text-sm font-semibold text-white">Automated Sync</h3>
                                <p className="text-xs text-slate-400 mt-1">All platform-generated meetings are automatically synced to your primary calendar.</p>
                            </div>
                            <div className="p-4 rounded-xl bg-slate-800/30 border border-slate-800/50">
                                <h3 className="text-sm font-semibold text-white">Role-Based Assignment</h3>
                                <p className="text-xs text-slate-400 mt-1">Super Admins and Managers can assign specific meeting slots to team members.</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <div className="p-4 bg-amber-500/5 border border-amber-500/10 rounded-xl">
                    <p className="text-xs text-amber-200/60 leading-relaxed">
                        <strong>Privacy Note:</strong> Our platform only requests access to manage events created within this platform or marked as "Marketing Automation". We do not read your private personal events.
                    </p>
                </div>
            </div>
        </Layout>
    );
};

export default CalendarIntegrations;
