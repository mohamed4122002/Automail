import api from '../lib/api';

const API_BASE_URL = '/v1/monitor';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface PoolStats {
    pool_size: number;
    checked_in: number;
    checked_out: number;
    overflow: number;
    invalid: number;
}

export interface HealthStatus {
    status: string;
    timestamp: string;
    services: {
        postgres: string | { status: string; error?: string };
        redis: { status: string; memory_mb?: number; error?: string };
        celery: { status: string; workers?: number; error?: string };
    };
    pool: PoolStats;
}

export interface SystemStats {
    status: string;
    timestamp: string;
    metrics: {
        campaigns: number;
        users: number;
        emails_sent: number;
        emails_queued: number;
        active_workflow_instances: number;
        events_24h: number;
    };
    pool: PoolStats;
}

export interface DbPoolStats {
    timestamp: string;
    pool: PoolStats;
    utilization_pct: number;
    config: {
        pool_size: number;
        max_overflow: number;
        pool_recycle_seconds: number;
        statement_timeout_ms: number;
        lock_timeout_ms: number;
    };
    warnings: string[];
}

export interface SecurityStatus {
    timestamp: string;
    overall_status: 'OK' | 'ISSUES_FOUND';
    issue_count: number;
    issues: string[];
    checks: Record<string, string>;
}

export interface IndexHealth {
    timestamp: string;
    indexes: Record<string, string>;
    missing_indexes: number;
    table_sizes: Record<string, {
        total_size: string;
        table_size: string;
        row_estimate: number;
    }>;
    seq_scan_warnings: string[];
    action_needed: string | null;
}

export interface CampaignMonitoring {
    campaign_id: string;
    name: string;
    is_active: boolean;
    recent_activity: Array<{
        id: string;
        type: string;
        created_at: string;
        data: any;
    }>;
    node_performance: Record<string, { avg_duration_seconds: number; executions: number }>;
}

// ── Service ───────────────────────────────────────────────────────────────────

export const monitoringService = {
    getHealth: async (): Promise<HealthStatus> => {
        const response = await api.get(`${API_BASE_URL}/health`);
        return response.data;
    },

    getSystemStats: async (): Promise<SystemStats> => {
        const response = await api.get(`${API_BASE_URL}/system`);
        return response.data;
    },

    getDbPoolStats: async (): Promise<DbPoolStats> => {
        const response = await api.get(`${API_BASE_URL}/db-pool`);
        return response.data;
    },

    getSecurityStatus: async (): Promise<SecurityStatus> => {
        const response = await api.get(`${API_BASE_URL}/security-status`);
        return response.data;
    },

    getIndexHealth: async (): Promise<IndexHealth> => {
        const response = await api.get(`${API_BASE_URL}/index-health`);
        return response.data;
    },

    getCampaignMonitoring: async (campaignId: string): Promise<CampaignMonitoring> => {
        const response = await api.get(`${API_BASE_URL}/campaign/${campaignId}`);
        return response.data;
    },

    getInfrastructureStats: async (): Promise<any> => {
        const response = await api.get(`${API_BASE_URL}/infrastructure`);
        return response.data;
    },

    getWorkflowHealth: async (): Promise<any> => {
        const response = await api.get(`${API_BASE_URL}/workflow/health`);
        return response.data;
    },

    repairWorkflows: async (): Promise<any> => {
        const response = await api.post(`${API_BASE_URL}/workflow/repair`);
        return response.data;
    },
};
