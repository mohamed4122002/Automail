import React, { useState, useEffect } from 'react';
import Layout from '../components/layout/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import {
    monitoringService,
    HealthStatus,
    DbPoolStats,
    SecurityStatus,
    IndexHealth,
} from '../services/monitoring';
import {
    Database, Zap, Cpu, Server, Activity, RefreshCw,
    AlertCircle, CheckCircle2, Shield, BarChart2, Lock,
    AlertTriangle, Info
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { toast } from 'sonner';

// ── Helpers ───────────────────────────────────────────────────────────────────

const StatusIcon: React.FC<{ status: string; size?: string }> = ({ status, size = 'w-5 h-5' }) => {
    const s = typeof status === 'string' ? status.toLowerCase() : '';
    if (['healthy', 'ok', 'up', 'online', 'exists'].some(v => s.includes(v)))
        return <CheckCircle2 className={`${size} text-emerald-500`} />;
    if (['unhealthy', 'error', 'offline', 'missing', 'insecure', 'issues_found', 'weak', 'unencrypted'].some(v => s.includes(v)))
        return <AlertCircle className={`${size} text-red-500`} />;
    return <AlertCircle className={`${size} text-amber-500`} />;
};

const PoolBar: React.FC<{ pct: number }> = ({ pct }) => {
    const color = pct > 80 ? 'bg-red-500' : pct > 60 ? 'bg-amber-500' : 'bg-emerald-500';
    return (
        <div className="w-full bg-slate-700/50 rounded-full h-2 mt-1">
            <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${Math.min(pct, 100)}%` }} />
        </div>
    );
};

// ── Main Component ────────────────────────────────────────────────────────────

const SystemStatus: React.FC = () => {
    const [health, setHealth] = useState<HealthStatus | null>(null);
    const [infra, setInfra] = useState<any>(null);
    const [wfHealth, setWfHealth] = useState<any>(null);
    const [poolStats, setPoolStats] = useState<DbPoolStats | null>(null);
    const [secStatus, setSecStatus] = useState<SecurityStatus | null>(null);
    const [indexHealth, setIndexHealth] = useState<IndexHealth | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [repairing, setRepairing] = useState(false);

    const fetchData = async () => {
        setRefreshing(true);
        try {
            const [healthData, infraData, wfData, poolData, secData, idxData] = await Promise.allSettled([
                monitoringService.getHealth(),
                monitoringService.getInfrastructureStats(),
                monitoringService.getWorkflowHealth(),
                monitoringService.getDbPoolStats(),
                monitoringService.getSecurityStatus(),
                monitoringService.getIndexHealth(),
            ]);

            if (healthData.status === 'fulfilled') setHealth(healthData.value);
            if (infraData.status === 'fulfilled') setInfra(infraData.value);
            if (wfData.status === 'fulfilled') setWfHealth(wfData.value);
            if (poolData.status === 'fulfilled') setPoolStats(poolData.value);
            if (secData.status === 'fulfilled') setSecStatus(secData.value);
            if (idxData.status === 'fulfilled') setIndexHealth(idxData.value);
        } catch (err) {
            console.error('Failed to fetch system status', err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 60000);
        return () => clearInterval(interval);
    }, []);

    const handleRepair = async () => {
        setRepairing(true);
        try {
            const res = await monitoringService.repairWorkflows();
            toast.success(`Recovery complete: ${res.repaired_count} instances re-queued.`);
            fetchData();
        } catch (err) {
            toast.error('Failed to trigger recovery script.');
        } finally {
            setRepairing(false);
        }
    };

    const getServiceStatus = (svc: any): string => {
        if (typeof svc === 'string') return svc;
        return svc?.status ?? 'unknown';
    };

    if (loading) {
        return (
            <Layout title="System Status">
                <div className="flex items-center justify-center h-64">
                    <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
                </div>
            </Layout>
        );
    }

    return (
        <Layout title="System Status">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
                        <Activity className="w-6 h-6 text-indigo-400" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-bold text-slate-100">Infrastructure Monitoring</h2>
                        <p className="text-sm text-slate-400">Real-time status of services, security, and database health</p>
                    </div>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={fetchData}
                    disabled={refreshing}
                    leftIcon={<RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />}
                >
                    Refresh
                </Button>
            </div>

            {/* ── Row 1: Service Health Cards ── */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                {/* PostgreSQL */}
                <Card className="bg-slate-900/50 border-slate-800">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-slate-400">Database</CardTitle>
                        <Database className="w-4 h-4 text-slate-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-xl font-bold text-slate-100">PostgreSQL</span>
                            <StatusIcon status={getServiceStatus(health?.services.postgres)} />
                        </div>
                        <div className="space-y-2">
                            <div className="flex justify-between text-xs">
                                <span className="text-slate-500">Status</span>
                                <span className="text-emerald-400 font-medium capitalize">
                                    {getServiceStatus(health?.services.postgres)}
                                </span>
                            </div>
                            <div className="flex justify-between text-xs">
                                <span className="text-slate-500">Pool Utilization</span>
                                <span className={`font-medium ${(poolStats?.utilization_pct ?? 0) > 80 ? 'text-red-400' : 'text-slate-300'}`}>
                                    {poolStats?.utilization_pct ?? '—'}%
                                </span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Redis */}
                <Card className="bg-slate-900/50 border-slate-800">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-slate-400">Cache / Broker</CardTitle>
                        <Zap className="w-4 h-4 text-slate-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-xl font-bold text-slate-100">Redis</span>
                            <StatusIcon status={getServiceStatus(health?.services.redis)} />
                        </div>
                        <div className="space-y-2">
                            <div className="flex justify-between text-xs">
                                <span className="text-slate-500">Memory</span>
                                <span className="text-slate-300 font-medium">{infra?.redis?.memory_usage_mb ?? '—'} MB</span>
                            </div>
                            <div className="flex justify-between text-xs">
                                <span className="text-slate-500">Clients</span>
                                <span className="text-slate-300">{infra?.redis?.connected_clients ?? '—'}</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Celery */}
                <Card className="bg-slate-900/50 border-slate-800">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-slate-400">Background Tasks</CardTitle>
                        <Cpu className="w-4 h-4 text-slate-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-xl font-bold text-slate-100">Celery</span>
                            <StatusIcon status={getServiceStatus(health?.services.celery)} />
                        </div>
                        <div className="space-y-2">
                            <div className="flex justify-between text-xs">
                                <span className="text-slate-500">Workers</span>
                                <span className="text-slate-300 font-medium">{infra?.celery?.workers?.length ?? '—'}</span>
                            </div>
                            <div className="flex justify-between text-xs">
                                <span className="text-slate-500">Active Tasks</span>
                                <span className="text-indigo-400 font-medium">{infra?.celery?.total_active ?? '—'}</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* ── Row 2: DB Pool + Security Status ── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                {/* Connection Pool Panel */}
                <Card className="bg-slate-900/50 border-slate-800">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                            <BarChart2 className="w-5 h-5 text-indigo-400" />
                            Connection Pool
                        </CardTitle>
                        {poolStats && (
                            <span className={`text-xs font-bold px-2 py-1 rounded-full ${poolStats.utilization_pct > 80
                                    ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                                    : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                }`}>
                                {poolStats.utilization_pct}% used
                            </span>
                        )}
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {poolStats ? (
                            <>
                                <div>
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="text-slate-500">Connections in use</span>
                                        <span className="text-slate-300">{poolStats.pool.checked_out} / {poolStats.config.pool_size + poolStats.config.max_overflow}</span>
                                    </div>
                                    <PoolBar pct={poolStats.utilization_pct} />
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    {[
                                        { label: 'Pool Size', value: poolStats.config.pool_size },
                                        { label: 'Max Overflow', value: poolStats.config.max_overflow },
                                        { label: 'Checked In', value: poolStats.pool.checked_in },
                                        { label: 'Checked Out', value: poolStats.pool.checked_out },
                                        { label: 'Stmt Timeout', value: `${poolStats.config.statement_timeout_ms / 1000}s` },
                                        { label: 'Lock Timeout', value: `${poolStats.config.lock_timeout_ms / 1000}s` },
                                    ].map(({ label, value }) => (
                                        <div key={label} className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/30">
                                            <p className="text-[10px] uppercase text-slate-500 tracking-wider">{label}</p>
                                            <p className="text-sm font-bold text-slate-200 mt-0.5">{value}</p>
                                        </div>
                                    ))}
                                </div>
                                {poolStats.warnings.map((w, i) => (
                                    <div key={i} className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                                        <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                                        <span className="text-xs text-amber-300">{w}</span>
                                    </div>
                                ))}
                            </>
                        ) : (
                            <p className="text-sm text-slate-500 text-center py-6">Pool stats unavailable</p>
                        )}
                    </CardContent>
                </Card>

                {/* Security Status Panel */}
                <Card className={`border ${secStatus?.overall_status === 'ISSUES_FOUND' ? 'bg-red-950/20 border-red-500/30' : 'bg-slate-900/50 border-slate-800'}`}>
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                            <Shield className="w-5 h-5 text-indigo-400" />
                            Security Status
                        </CardTitle>
                        {secStatus && (
                            <span className={`text-xs font-bold px-2 py-1 rounded-full ${secStatus.overall_status === 'OK'
                                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                    : 'bg-red-500/10 text-red-400 border border-red-500/20'
                                }`}>
                                {secStatus.overall_status === 'OK' ? '✓ Secure' : `${secStatus.issue_count} Issues`}
                            </span>
                        )}
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {secStatus ? (
                            <>
                                {secStatus.issues.length > 0 && (
                                    <div className="space-y-2">
                                        {secStatus.issues.map((issue, i) => (
                                            <div key={i} className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                                                <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                                                <span className="text-xs text-red-300">{issue}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                                <div className="space-y-2">
                                    {Object.entries(secStatus.checks).map(([key, value]) => (
                                        <div key={key} className="flex items-center justify-between py-1.5 border-b border-slate-800/50 last:border-0">
                                            <span className="text-xs text-slate-500 font-mono">{key}</span>
                                            <div className="flex items-center gap-1.5">
                                                <StatusIcon status={value} size="w-3.5 h-3.5" />
                                                <span className="text-xs text-slate-300 max-w-[160px] truncate text-right">{value}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </>
                        ) : (
                            <p className="text-sm text-slate-500 text-center py-6">Security status unavailable</p>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* ── Row 3: Index Health ── */}
            <Card className="bg-slate-900/50 border-slate-800 mb-6">
                <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                        <Database className="w-5 h-5 text-indigo-400" />
                        Database Index Health
                    </CardTitle>
                    {indexHealth && (
                        <span className={`text-xs font-bold px-2 py-1 rounded-full ${indexHealth.missing_indexes === 0
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            }`}>
                            {indexHealth.missing_indexes === 0 ? 'All indexes present' : `${indexHealth.missing_indexes} missing`}
                        </span>
                    )}
                </CardHeader>
                <CardContent>
                    {indexHealth ? (
                        <div className="space-y-4">
                            {indexHealth.action_needed && (
                                <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                                    <Info className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                                    <span className="text-xs text-amber-300 font-mono">{indexHealth.action_needed}</span>
                                </div>
                            )}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                {Object.entries(indexHealth.indexes).map(([name, status]) => (
                                    <div key={name} className="flex items-center justify-between p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                                        <span className="text-xs font-mono text-slate-400 truncate mr-2">{name}</span>
                                        <div className="flex items-center gap-1 flex-shrink-0">
                                            <StatusIcon status={status} size="w-3.5 h-3.5" />
                                            <span className={`text-[10px] font-bold ${status.includes('EXISTS') ? 'text-emerald-400' : 'text-red-400'}`}>
                                                {status.includes('EXISTS') ? 'OK' : 'MISSING'}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            {/* Table Sizes */}
                            {Object.keys(indexHealth.table_sizes).length > 0 && (
                                <div>
                                    <h4 className="text-xs uppercase text-slate-500 tracking-wider mb-2">Table Sizes</h4>
                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                                        {Object.entries(indexHealth.table_sizes).map(([table, info]) => (
                                            <div key={table} className="p-3 rounded-lg bg-slate-800/30 border border-slate-700/30">
                                                <p className="text-[10px] uppercase text-slate-500 font-mono">{table}</p>
                                                <p className="text-sm font-bold text-slate-200">{info.total_size}</p>
                                                <p className="text-[10px] text-slate-500">{info.row_estimate?.toLocaleString()} rows</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {indexHealth.seq_scan_warnings.length > 0 && (
                                <div className="space-y-1">
                                    {indexHealth.seq_scan_warnings.map((w, i) => (
                                        <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                                            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
                                            <span className="text-xs text-amber-300">{w}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ) : (
                        <p className="text-sm text-slate-500 text-center py-6">Index health unavailable</p>
                    )}
                </CardContent>
            </Card>

            {/* ── Row 4: Workflow Health Recovery ── */}
            <Card className="bg-indigo-950/20 border-indigo-500/30 mb-6 overflow-hidden">
                <div className="bg-indigo-500/10 px-6 py-4 border-b border-indigo-500/20 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <Zap className="w-5 h-5 text-indigo-400" />
                        <div>
                            <h3 className="text-lg font-bold text-slate-100">Workflow Health Recovery</h3>
                            <p className="text-xs text-slate-400 font-mono italic">Engineered for Reliability</p>
                        </div>
                    </div>
                    <Button
                        size="sm"
                        className="bg-indigo-600 hover:bg-indigo-500 text-white border-transparent"
                        onClick={handleRepair}
                        disabled={repairing || wfHealth?.stalled_count === 0}
                        isLoading={repairing}
                    >
                        Repair Stalled Workflows
                    </Button>
                </div>
                <CardContent className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <div className="space-y-1">
                            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Engine Status</span>
                            <div className="flex items-center gap-2">
                                <span className={wfHealth?.is_healthy ? 'text-emerald-400 font-bold' : 'text-amber-400 font-bold'}>
                                    {wfHealth?.is_healthy ? 'OPTIMAL' : 'STALLED LEADS DETECTED'}
                                </span>
                            </div>
                        </div>
                        <div className="space-y-1">
                            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Stalled Instances</span>
                            <div className="text-2xl font-black text-slate-100 leading-none">{wfHealth?.stalled_count || 0}</div>
                        </div>
                        <div className="space-y-1 md:col-span-2">
                            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Instance Distribution</span>
                            <div className="flex gap-2 mt-1 flex-wrap">
                                {Object.entries(wfHealth?.stats || {}).map(([status, count]) => (
                                    <div key={status} className="px-3 py-1 rounded-lg bg-slate-800/50 border border-slate-700/50">
                                        <span className="text-[10px] text-slate-500 block leading-tight uppercase font-mono">{status}</span>
                                        <span className="text-sm font-bold text-slate-200">{count as number}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* ── Row 5: Worker Registry ── */}
            <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader>
                    <CardTitle className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                        <Server className="w-5 h-5 text-indigo-400" />
                        Worker Node Registry
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {infra?.celery?.workers?.length > 0 ? infra.celery.workers.map((worker: any, idx: number) => (
                            <div key={idx} className="p-4 rounded-xl bg-slate-800/30 border border-slate-700/30">
                                <div className="flex justify-between items-start mb-3">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                        <span className="font-mono text-sm text-slate-200">{worker.name}</span>
                                    </div>
                                    <div className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                                        ONLINE
                                    </div>
                                </div>
                                <div className="grid grid-cols-3 gap-4">
                                    {[
                                        { label: 'Active', value: worker.active_tasks },
                                        { label: 'Scheduled', value: worker.scheduled_tasks },
                                        { label: 'Registered', value: worker.registered_tasks },
                                    ].map(({ label, value }) => (
                                        <div key={label}>
                                            <p className="text-[10px] uppercase text-slate-500 tracking-wider">{label}</p>
                                            <p className="text-lg font-bold text-slate-100">{value}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )) : (
                            <p className="text-sm text-slate-500 text-center py-8">No workers online</p>
                        )}
                    </div>
                </CardContent>
            </Card>
        </Layout>
    );
};

export default SystemStatus;
