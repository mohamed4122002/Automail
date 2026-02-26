import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Loader2, Server } from 'lucide-react';

interface WorkerStatus {
    available: boolean;
    worker_count: number;
    workers: Record<string, any>;
    has_active_workers: boolean;
}

interface SystemHealth {
    status: 'healthy' | 'degraded' | 'unhealthy';
    components: {
        database?: { status: string };
        redis?: { status: string };
        celery_workers?: { status: string; worker_count: number };
    };
}

export function WorkerStatusIndicator() {
    const [workerStatus, setWorkerStatus] = useState<WorkerStatus | null>(null);
    const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const [workersRes, healthRes] = await Promise.all([
                    fetch('/api/system/workers'),
                    fetch('/api/system/health')
                ]);

                if (workersRes.ok) {
                    const data = await workersRes.json();
                    setWorkerStatus(data);
                }

                if (healthRes.ok) {
                    const data = await healthRes.json();
                    setSystemHealth(data);
                }
            } catch (error) {
                console.error('Failed to fetch worker status:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 30000); // Refresh every 30s

        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <div className="flex items-center gap-2 px-3 py-2 bg-gray-800 rounded-lg border border-gray-700">
                <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                <span className="text-sm text-gray-400">Checking workers...</span>
            </div>
        );
    }

    const hasWorkers = workerStatus?.has_active_workers ?? false;
    const workerCount = workerStatus?.worker_count ?? 0;

    return (
        <div
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${hasWorkers
                    ? 'bg-green-900/20 border-green-700/50'
                    : 'bg-amber-900/20 border-amber-700/50'
                }`}
        >
            <Server className={`w-4 h-4 ${hasWorkers ? 'text-green-400' : 'text-amber-400'}`} />
            <div className="flex flex-col">
                <div className="flex items-center gap-2">
                    {hasWorkers ? (
                        <CheckCircle className="w-3 h-3 text-green-400" />
                    ) : (
                        <AlertCircle className="w-3 h-3 text-amber-400" />
                    )}
                    <span className={`text-sm font-medium ${hasWorkers ? 'text-green-300' : 'text-amber-300'}`}>
                        {hasWorkers ? `${workerCount} Worker${workerCount > 1 ? 's' : ''} Active` : 'No Workers'}
                    </span>
                </div>
                {!hasWorkers && (
                    <span className="text-xs text-amber-400/80">
                        Tasks will queue but not execute
                    </span>
                )}
            </div>
        </div>
    );
}

export function SystemHealthBadge() {
    const [health, setHealth] = useState<SystemHealth | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchHealth = async () => {
            try {
                const res = await fetch('/api/system/health');
                if (res.ok) {
                    const data = await res.json();
                    setHealth(data);
                }
            } catch (error) {
                console.error('Failed to fetch system health:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchHealth();
        const interval = setInterval(fetchHealth, 60000); // Refresh every 60s

        return () => clearInterval(interval);
    }, []);

    if (loading || !health) return null;

    const statusColors = {
        healthy: 'bg-green-500',
        degraded: 'bg-amber-500',
        unhealthy: 'bg-red-500'
    };

    return (
        <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${statusColors[health.status]} animate-pulse`} />
            <span className="text-xs text-gray-400 capitalize">{health.status}</span>
        </div>
    );
}
