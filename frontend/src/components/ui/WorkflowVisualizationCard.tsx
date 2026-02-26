import React from 'react';
import { Link } from 'react-router-dom';
import { Workflow as WorkflowIcon, Edit, Play, Pause, TrendingUp } from 'lucide-react';
import { Button } from './Button';
import classNames from 'classnames';

interface WorkflowNode {
    id: string;
    type: string;
    label: string;
    position: any;
    config: any;
}

interface NodeStats {
    node_id: string;
    node_type: string;
    node_label: string;
    leads_active: number;
    leads_completed: number;
    leads_failed: number;
    success_rate: number;
    avg_duration?: number;
}

interface WorkflowVisualizationCardProps {
    workflowId: string;
    workflowName: string;
    isActive: boolean;
    nodes: WorkflowNode[];
    nodeStats: NodeStats[];
    totalInstances: number;
    activeInstances: number;
    completedInstances: number;
    onOpenEditor?: () => void;
    onNodeClick?: (node: any) => void;
}

export const WorkflowVisualizationCard: React.FC<WorkflowVisualizationCardProps> = ({
    workflowId,
    workflowName,
    isActive,
    nodes,
    nodeStats,
    totalInstances,
    activeInstances,
    completedInstances,
    onOpenEditor,
    onNodeClick
}) => {
    // Calculate completion rate
    const completionRate = totalInstances > 0
        ? (completedInstances / totalInstances * 100).toFixed(1)
        : '0.0';

    // Get top 3 nodes by activity
    const topNodes = [...nodeStats]
        .sort((a, b) => b.leads_active - a.leads_active)
        .slice(0, 3);

    return (
        <div className="bg-gradient-to-br from-slate-800/40 to-slate-900/40 p-6 rounded-xl border border-slate-700/30 backdrop-blur-sm shadow-lg">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-indigo-500/10">
                        <WorkflowIcon className="w-5 h-5 text-indigo-400" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-slate-100">
                            Workflow Execution
                        </h3>
                        <p className="text-sm text-slate-400">{workflowName}</p>
                    </div>
                </div>

                {onOpenEditor ? (
                    <Button variant="outline" size="sm" leftIcon={<Edit className="w-4 h-4" />} onClick={onOpenEditor}>
                        Edit Workflow
                    </Button>
                ) : (
                    <Link to={`/workflows/${workflowId}`}>
                        <Button variant="outline" size="sm" leftIcon={<Edit className="w-4 h-4" />}>
                            Edit Workflow
                        </Button>
                    </Link>
                )}
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700/50">
                    <p className="text-xs text-slate-500 mb-1">Total Instances</p>
                    <p className="text-2xl font-bold text-slate-100">{totalInstances.toLocaleString()}</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700/50">
                    <div className="flex items-center gap-2 mb-1">
                        <Play className="w-3 h-3 text-emerald-400" />
                        <p className="text-xs text-slate-500">Active Now</p>
                    </div>
                    <p className="text-2xl font-bold text-emerald-400">{activeInstances.toLocaleString()}</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700/50">
                    <p className="text-xs text-slate-500 mb-1">Completion Rate</p>
                    <p className="text-2xl font-bold text-indigo-400">{completionRate}%</p>
                </div>
            </div>

            {/* Node Activity */}
            <div>
                <h4 className="text-sm font-semibold text-slate-300 mb-3">Active Nodes</h4>
                <div className="space-y-2">
                    {topNodes.length > 0 ? (
                        topNodes.map((node) => (
                            <div
                                key={node.node_id}
                                onClick={() => onNodeClick?.(nodes.find(n => n.id === node.node_id))}
                                className={classNames(
                                    "flex items-center justify-between p-3 rounded-lg bg-slate-800/30 border border-slate-700/30 transition-colors",
                                    onNodeClick ? "hover:bg-slate-800/50 cursor-pointer" : ""
                                )}
                            >
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-slate-200 truncate">
                                        {node.node_label}
                                    </p>
                                    <p className="text-xs text-slate-500">{node.node_type}</p>
                                </div>
                                <div className="flex items-center gap-4">
                                    <div className="text-right">
                                        <p className="text-sm font-semibold text-emerald-400">
                                            {node.leads_active}
                                        </p>
                                        <p className="text-xs text-slate-500">active</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-sm font-semibold text-slate-300">
                                            {node.avg_duration ? `${node.avg_duration.toFixed(1)}s` : '--'}
                                        </p>
                                        <p className="text-xs text-slate-500">avg speed</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-sm font-semibold text-slate-300">
                                            {node.success_rate.toFixed(0)}%
                                        </p>
                                        <p className="text-xs text-slate-500">success</p>
                                    </div>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="text-center py-8 text-slate-500">
                            <WorkflowIcon className="w-12 h-12 mx-auto mb-2 opacity-30" />
                            <p className="text-sm">No active workflow instances</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Mini Canvas Preview (Simplified) */}
            <div className="mt-6 p-4 rounded-lg bg-slate-900/50 border border-slate-700/30">
                <div className="flex items-center justify-center gap-2 text-xs text-slate-500">
                    <div className="flex items-center gap-1">
                        {nodes.slice(0, 5).map((node, idx) => (
                            <React.Fragment key={node.id}>
                                <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/50 flex items-center justify-center">
                                    <span className="text-[10px] text-indigo-300">{idx + 1}</span>
                                </div>
                                {idx < Math.min(4, nodes.length - 1) && (
                                    <div className="w-4 h-0.5 bg-slate-600" />
                                )}
                            </React.Fragment>
                        ))}
                        {nodes.length > 5 && (
                            <span className="ml-2 text-slate-600">+{nodes.length - 5} more</span>
                        )}
                    </div>
                </div>
                <p className="text-center text-xs text-slate-500 mt-2">
                    {nodes.length} nodes • Click "Edit Workflow" for full canvas
                </p>
            </div>
        </div>
    );
};

export default WorkflowVisualizationCard;
