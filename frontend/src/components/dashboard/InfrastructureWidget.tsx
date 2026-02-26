import React from 'react';
import { Database, Zap, Cpu, Server, Activity } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

interface InfrastructureWidgetProps {
    data: {
        redis: {
            status: string;
            memory_usage_mb: number;
            connected_clients: number;
            version?: string;
        };
        celery: {
            workers: Array<{
                name: string;
                active_tasks: number;
                scheduled_tasks: number;
                registered_tasks: number;
            }>;
            total_active: number;
            total_scheduled: number;
        };
    };
}

export const InfrastructureWidget: React.FC<InfrastructureWidgetProps> = ({ data }) => {
    return (
        <Card className="bg-slate-900/40 border-slate-800 backdrop-blur-sm">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                    <Server className="w-4 h-4 text-indigo-400" />
                    Infrastructure Status
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Redis Section */}
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Zap className="w-4 h-4 text-amber-400" />
                            <span className="text-sm font-medium text-slate-200">Redis Cache</span>
                        </div>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${data.redis.status === 'healthy' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                            }`}>
                            {data.redis.status}
                        </span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/30">
                            <p className="text-[10px] text-slate-500 uppercase">Memory Usage</p>
                            <p className="text-lg font-bold text-slate-100">{data.redis.memory_usage_mb} MB</p>
                        </div>
                        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/30">
                            <p className="text-[10px] text-slate-500 uppercase">Clients</p>
                            <p className="text-lg font-bold text-slate-100">{data.redis.connected_clients}</p>
                        </div>
                    </div>
                </div>

                {/* Celery Section */}
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Cpu className="w-4 h-4 text-indigo-400" />
                            <span className="text-sm font-medium text-slate-200">Celery Workers</span>
                        </div>
                        <span className="text-[10px] bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded-full font-bold uppercase">
                            {data.celery.workers.length} Global Nodes
                        </span>
                    </div>

                    <div className="space-y-2">
                        {data.celery.workers.map((worker, idx) => (
                            <div key={idx} className="bg-slate-800/30 p-3 rounded-lg border border-slate-700/20">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs font-mono text-slate-400 truncate max-w-[150px]">
                                        {worker.name.split('@')[1] || worker.name}
                                    </span>
                                    <div className="flex items-center gap-1">
                                        <Activity className="w-3 h-3 text-emerald-400 animate-pulse" />
                                        <span className="text-[10px] text-emerald-400 font-bold">ACTIVE</span>
                                    </div>
                                </div>
                                <div className="flex gap-4">
                                    <div>
                                        <p className="text-[10px] text-slate-500">Active</p>
                                        <p className="text-sm font-bold text-slate-200">{worker.active_tasks}</p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] text-slate-500">Scheduled</p>
                                        <p className="text-sm font-bold text-slate-200">{worker.scheduled_tasks}</p>
                                    </div>
                                    <div className="flex-1 text-right">
                                        <p className="text-[10px] text-slate-500">Load</p>
                                        <div className="mt-1 w-full h-1 bg-slate-700 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-indigo-500 rounded-full"
                                                style={{ width: `${Math.min((worker.active_tasks / 10) * 100, 100)}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};
