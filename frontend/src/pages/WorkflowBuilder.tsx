import React, { useState, useCallback, useEffect, useMemo } from 'react';
import dagre from 'dagre';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    ReactFlow,
    Node,
    Edge,
    Controls,
    Background,
    MiniMap,
    Panel,
    applyNodeChanges,
    applyEdgeChanges,
    addEdge,
    NodeChange,
    EdgeChange,
    Connection,
    BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import api from '../lib/api';
import { Save, Download, Upload, Zap, Play, Mail, Clock, GitBranch, Terminal, Square, Plus, Minus, Maximize, Trash2, HelpCircle, Layout as LayoutIcon } from 'lucide-react';
import { useReactFlow } from '@xyflow/react';
import { toast } from 'sonner';

// Custom Nodes
import { TriggerNode } from '../components/workflow/nodes/TriggerNode';
import { EmailNode } from '../components/workflow/nodes/EmailNode';
import { DelayNode } from '../components/workflow/nodes/DelayNode';
import { DecisionNode } from '../components/workflow/nodes/DecisionNode';
import { ActionNode } from '../components/workflow/nodes/ActionNode';
import { EndNode } from '../components/workflow/nodes/EndNode';
import { LEAD_STATUS } from '../lib/constants';
import { useGlobalWebSocket } from '../context/WebSocketContext';

const nodeTypes = {
    start: TriggerNode,
    email: EmailNode,
    delay: DelayNode,
    condition: DecisionNode,
    action: ActionNode,
    end: EndNode,
};

const defaultEdgeOptions = {
    animated: true,
    style: { strokeWidth: 2, stroke: '#6366f1' },
};

const WorkflowBuilder: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const [nodes, setNodes] = useState<Node[]>([]);
    const [edges, setEdges] = useState<Edge[]>([]);
    const [workflowName, setWorkflowName] = useState('New Workflow');
    const [activeNodes, setActiveNodes] = useState<Set<string>>(new Set());

    const { getNodes, getEdges, setNodes: setRfNodes, setEdges: setRfEdges, fitView: rfFitView } = useReactFlow();

    const getLayoutedElements = useCallback((nodes: Node[], edges: Edge[], direction = 'TB') => {
        const dagreGraph = new dagre.graphlib.Graph();
        dagreGraph.setDefaultEdgeLabel(() => ({}));

        const isHorizontal = direction === 'LR';
        dagreGraph.setGraph({ rankdir: direction });

        nodes.forEach((node) => {
            dagreGraph.setNode(node.id, { width: 250, height: 100 });
        });

        edges.forEach((edge) => {
            dagreGraph.setEdge(edge.source, edge.target);
        });

        dagre.layout(dagreGraph);

        const layoutedNodes = nodes.map((node) => {
            const nodeWithPosition = dagreGraph.node(node.id);
            return {
                ...node,
                position: {
                    x: nodeWithPosition.x - 125,
                    y: nodeWithPosition.y - 50,
                },
            };
        });

        return { nodes: layoutedNodes, edges };
    }, []);

    const onLayout = useCallback((direction: string) => {
        const layouted = getLayoutedElements(nodes, edges, direction);
        setNodes([...layouted.nodes]);
        setEdges([...layouted.edges]);
        setTimeout(() => rfFitView({ padding: 0.2 }), 100);
    }, [nodes, edges, getLayoutedElements, rfFitView]);

    // WebSocket for live node animations
    const { isConnected, lastMessage } = useGlobalWebSocket();

    useEffect(() => {
        if (!lastMessage) return;
        const message = lastMessage;
        if (message.type === 'event' && message.event_type === 'WORKFLOW_NODE_ENTER') {
            // Ensure it's for this workflow
            if (message.workflow_id === id) {
                const nodeId = message.node_id;

                // Add to active set
                setActiveNodes(prev => {
                    const next = new Set(prev);
                    next.add(nodeId);
                    return next;
                });

                // Remove after 3 seconds
                setTimeout(() => {
                    setActiveNodes(prev => {
                        const next = new Set(prev);
                        next.delete(nodeId);
                        return next;
                    });
                }, 3000);
            }
        }
    }, [lastMessage, id]);

    // Update node classes based on active state
    useEffect(() => {
        setNodes(nds => nds.map(node => ({
            ...node,
            className: activeNodes.has(node.id) ? 'node-active' : ''
        })));
    }, [activeNodes]);

    // Load workflow graph from backend
    const { data: graphData, isLoading } = useQuery({
        queryKey: ['workflow-graph', id],
        queryFn: async () => {
            if (!id) return null;
            const response = await api.get(`/workflows/${id}/graph`);
            return response.data;
        },
        enabled: !!id
    });

    // Load workflow metadata
    const { data: workflowData } = useQuery({
        queryKey: ['workflow', id],
        queryFn: async () => {
            if (!id) return null;
            const response = await api.get(`/workflows/${id}`);
            return response.data;
        },
        enabled: !!id
    });

    // Save workflow graph mutation
    const saveGraphMutation = useMutation({
        mutationFn: async () => {
            if (!id) throw new Error('No workflow ID');

            const response = await api.post(`/workflows/${id}/graph`, {
                nodes: nodes.map(node => {
                    // Sanitize data: remove 'type' if it exists to avoid discriminator conflicts
                    const { type: _type, ...cleanData } = node.data;
                    return {
                        id: node.id,
                        type: node.type || 'default',
                        position: node.position,
                        data: cleanData
                    };
                }),
                edges: edges.map(edge => ({
                    id: edge.id,
                    source: edge.source,
                    target: edge.target,
                    sourceHandle: edge.sourceHandle,
                    targetHandle: edge.targetHandle,
                    data: {
                        ...(edge.data || {}),
                        // Ensure sourceHandle/targetHandle are in data if needed by backend, 
                        // but usually they are top-level in ReactFlowEdge
                    }
                }))
            });

            return response.data;
        },
        onSuccess: () => {
            toast.success('Workflow saved successfully!');
            queryClient.invalidateQueries({ queryKey: ['workflow-graph', id] });
        },
        onError: (error: any) => {
            toast.error(`Failed to save workflow: ${error.response?.data?.detail || error.message}`);
        }
    });

    // Load graph data when available
    useEffect(() => {
        if (graphData) {
            const graphNodes = graphData.nodes || [];
            const graphEdges = graphData.edges || [];

            // Check if nodes are clustered (all at 0,0 or similar)
            const isStacked = graphNodes.length > 1 && graphNodes.every((n: any) => n.position?.x === graphNodes[0].position?.x && n.position?.y === graphNodes[0].position?.y);

            if (isStacked || (graphNodes.length > 0 && graphNodes[0].position?.x === 0 && graphNodes[0].position?.y === 0)) {
                const layouted = getLayoutedElements(graphNodes, graphEdges);
                setNodes(layouted.nodes);
                setEdges(layouted.edges);
            } else {
                setNodes(graphNodes);
                setEdges(graphEdges);
            }
        }
    }, [graphData, getLayoutedElements]);

    // Update workflow name
    useEffect(() => {
        if (workflowData) {
            setWorkflowName(workflowData.name);
        }
    }, [workflowData]);

    const onNodesChange = useCallback(
        (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
        []
    );

    const onEdgesChange = useCallback(
        (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
        []
    );

    const onConnect = useCallback(
        (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
        []
    );

    const addNode = (type: string) => {
        const newNode: Node = {
            id: `${type}-${Date.now()}`,
            type: type,
            position: { x: 100, y: 100 },
            data: {
                label: type.charAt(0).toUpperCase() + type.slice(1),
                // Initial configurations for backend validation
                ...(type === 'email' && { template_id: "" }),
                ...(type === 'delay' && { hours: 1 }),
                ...(type === 'action' && { action: "update_lead_status", status: LEAD_STATUS.WARM }),
                ...(type === 'condition' && { conditionLabel: "User opened email?", condition: { type: "email_open" } }),
            },
        };
        setNodes((nds) => [...nds, newNode]);
    };

    const clearAll = useCallback(() => {
        if (confirm('Are you sure you want to clear the entire workflow?')) {
            setNodes([]);
            setEdges([]);
        }
    }, [setNodes, setEdges]);

    const handleSave = () => {
        saveGraphMutation.mutate();
    };

    const handleExport = () => {
        const data = { nodes, edges };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `workflow-${id || 'new'}.json`;
        a.click();
    };

    const translateLogicalToVisual = (logical: any) => {
        const nodes: Node[] = [];
        const edges: Edge[] = [];
        let yOffset = 50;

        // 1. Create Start Node from trigger
        const startNodeId = 'trigger-start';
        const { type: triggerType, ...triggerData } = logical.trigger || {};
        nodes.push({
            id: startNodeId,
            type: 'start',
            position: { x: 300, y: yOffset },
            data: {
                label: triggerType?.replace(/_/g, ' ').toUpperCase() || 'TRIGGER',
                ...triggerData,
                trigger_type: triggerType // Store original type under a different name
            }
        });
        yOffset += 150;

        // 2. Map Steps to Nodes
        logical.steps?.forEach((step: any) => {
            const { type: stepType, id: stepInternalId, ...stepData } = step;
            const nodeType = (stepType === 'action' && stepData.action === 'end') ? 'end' :
                stepType === 'condition' ? 'condition' :
                    stepType === 'wait' ? 'delay' :
                        stepType === 'action' ? 'action' :
                            stepType === 'send_email' ? 'email' : 'action';

            nodes.push({
                id: stepInternalId,
                type: nodeType,
                position: { x: 300, y: yOffset },
                data: {
                    label: stepInternalId.replace(/_/g, ' ').toUpperCase(),
                    ...stepData,
                    // Map legacy or logical fields to expected visual fields
                    ...(stepData.template_id && { template_id: stepData.template_id }),
                    ...(stepData.template && !stepData.template_id && { template_id: stepData.template }), // Fallback
                    ...(stepData.hours && { hours: stepData.hours }),
                    ...(stepData.duration && !stepData.hours && { hours: parseInt(stepData.duration) || 0 }),
                    ...(nodeType === 'condition' && { condition: { type: stepData.condition || 'default' } })
                }
            });
            yOffset += 150;
        });

        // 3. Create Edges
        if (logical.steps && logical.steps.length > 0) {
            // Trigger to first step
            edges.push({
                id: `edge-${startNodeId}-${logical.steps[0].id}`,
                source: startNodeId,
                target: logical.steps[0].id
            });

            logical.steps.forEach((step: any, index: number) => {
                if (step.branches) {
                    // Handle branching logic
                    if (step.branches.yes) {
                        edges.push({
                            id: `edge-${step.id}-yes`,
                            source: step.id,
                            target: step.branches.yes,
                            sourceHandle: 'true', // Matches DecisionNode.tsx
                            label: 'Yes',
                            animated: true,
                            data: { label: 'Yes' }
                        });
                    }
                    if (step.branches.no) {
                        edges.push({
                            id: `edge-${step.id}-no`,
                            source: step.id,
                            target: step.branches.no,
                            sourceHandle: 'false', // Matches DecisionNode.tsx
                            label: 'No',
                            animated: true,
                            data: { label: 'No' }
                        });
                    }
                } else if (index < logical.steps.length - 1) {
                    // Linear sequence for non-branching nodes
                    edges.push({
                        id: `edge-${step.id}-${logical.steps[index + 1].id}`,
                        source: step.id,
                        target: logical.steps[index + 1].id
                    });
                }
            });
        }

        return { nodes, edges };
    };

    const [rfInstance, setRfInstance] = useState<any>(null);
    const { zoomIn, zoomOut, fitView } = useReactFlow();

    const handleImport = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const content = e.target?.result as string;
                const data = JSON.parse(content);

                // Check for logical format (trigger + steps) vs visual format (nodes + edges)
                if (data.trigger && data.steps) {
                    const result = translateLogicalToVisual(data);
                    setNodes(result.nodes);
                    setEdges(result.edges);
                    if (data.workflow_name) setWorkflowName(data.workflow_name);

                    toast.success(`Import successful: ${result.nodes.length} nodes created.`);
                    if (rfInstance) {
                        setTimeout(() => rfInstance.fitView({ padding: 0.2 }), 100);
                    }
                } else {
                    // Standard visual format
                    setNodes(data.nodes || []);
                    setEdges(data.edges || []);
                    toast.success(`Import successful: ${data.nodes?.length || 0} nodes created.`);
                    if (rfInstance) {
                        setTimeout(() => rfInstance.fitView({ padding: 0.2 }), 100);
                    }
                }
            } catch (error) {
                console.error('Import failed:', error);
                toast.error('Failed to import workflow. Please ensure the file is valid JSON.');
            }
        };
        reader.readAsText(file);
    };

    if (isLoading) {
        return (
            <Layout title="Workflow Builder">
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
                </div>
            </Layout>
        );
    }

    return (
        <Layout title={`Workflow Builder - ${workflowName}`}>
            <div className="space-y-4">
                {/* Toolbar */}
                <div className="bg-slate-900/50 backdrop-blur-md border border-slate-700/50 rounded-2xl p-2 shadow-2xl">
                    <div className="flex flex-wrap items-center justify-between gap-4 p-2">
                        <div className="flex items-center gap-1.5 bg-slate-950/40 p-1 rounded-xl border border-slate-800/50">
                            <Button size="sm" variant="secondary" className="h-9 gap-2 px-3 hover:bg-emerald-500/10 hover:text-emerald-400 border-none" onClick={() => addNode('start')}>
                                <Play className="w-4 h-4" /> <span className="hidden sm:inline">Start</span>
                            </Button>
                            <Button size="sm" variant="secondary" className="h-9 gap-2 px-3 hover:bg-blue-500/10 hover:text-blue-400 border-none" onClick={() => addNode('email')}>
                                <Mail className="w-4 h-4" /> <span className="hidden sm:inline">Email</span>
                            </Button>
                            <Button size="sm" variant="secondary" className="h-9 gap-2 px-3 hover:bg-amber-500/10 hover:text-amber-400 border-none" onClick={() => addNode('delay')}>
                                <Clock className="w-4 h-4" /> <span className="hidden sm:inline">Delay</span>
                            </Button>
                            <Button size="sm" variant="secondary" className="h-9 gap-2 px-3 hover:bg-purple-500/10 hover:text-purple-400 border-none" onClick={() => addNode('condition')}>
                                <GitBranch className="w-4 h-4" /> <span className="hidden sm:inline">Condition</span>
                            </Button>
                            <Button size="sm" variant="secondary" className="h-9 gap-2 px-3 hover:bg-cyan-500/10 hover:text-cyan-400 border-none" onClick={() => addNode('action')}>
                                <Terminal className="w-4 h-4" /> <span className="hidden sm:inline">Action</span>
                            </Button>
                            <Button size="sm" variant="secondary" className="h-9 gap-2 px-3 hover:bg-red-500/10 hover:text-red-400 border-none" onClick={() => addNode('end')}>
                                <Square className="w-4 h-4" /> <span className="hidden sm:inline">End</span>
                            </Button>
                        </div>

                        <div className="flex items-center gap-1.5 bg-slate-950/40 p-1 rounded-xl border border-slate-800/50">
                            <Button size="sm" variant="ghost" className="h-9 w-9 p-0 hover:bg-red-500/10 hover:text-red-400" onClick={clearAll} title="Clear All">
                                <Trash2 className="w-4 h-4" />
                            </Button>
                            <Button size="sm" variant="ghost" className="h-9 w-9 p-0 hover:bg-indigo-500/10 hover:text-indigo-400" onClick={() => onLayout('TB')} title="Auto Layout">
                                <LayoutIcon className="w-4 h-4" />
                            </Button>
                        </div>

                        <div className="flex items-center gap-2">
                            {/* Zoom Controls */}
                            <div className="flex items-center gap-1 bg-slate-950/40 p-1 rounded-xl border border-slate-800/50 mr-2">
                                <Button size="sm" variant="secondary" className="h-8 w-8 p-0 border-none hover:bg-slate-800" onClick={() => zoomIn()}>
                                    <Plus className="w-4 h-4" />
                                </Button>
                                <Button size="sm" variant="secondary" className="h-8 w-8 p-0 border-none hover:bg-slate-800" onClick={() => zoomOut()}>
                                    <Minus className="w-4 h-4" />
                                </Button>
                                <Button size="sm" variant="secondary" className="h-8 w-8 p-0 border-none hover:bg-slate-800" onClick={() => fitView()}>
                                    <Maximize className="w-4 h-4" />
                                </Button>
                            </div>

                            <label className="cursor-pointer">
                                <input
                                    type="file"
                                    accept=".json"
                                    onChange={handleImport}
                                    className="hidden"
                                />
                                <span className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-slate-300 bg-slate-800/50 hover:bg-slate-700/50 hover:text-white rounded-xl transition-all border border-slate-700/50">
                                    <Upload className="w-4 h-4" />
                                    Import
                                </span>
                            </label>

                            <Button
                                size="sm"
                                variant="secondary"
                                leftIcon={<Download className="w-4 h-4" />}
                                onClick={handleExport}
                                className="h-10 px-4 font-semibold border-slate-700/50 rounded-xl"
                            >
                                Export
                            </Button>

                            <Button
                                size="sm"
                                leftIcon={<Save className="w-4 h-4" />}
                                onClick={handleSave}
                                disabled={saveGraphMutation.isPending || !id}
                                className="h-10 px-6 font-bold rounded-xl shadow-lg shadow-indigo-500/20 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 border-none"
                            >
                                {saveGraphMutation.isPending ? 'Saving...' : 'Save Workflow'}
                            </Button>
                        </div>
                    </div>
                </div>

                {/* Canvas */}
                <Card className="p-0" style={{ height: '600px' }}>
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        onConnect={onConnect}
                        nodeTypes={nodeTypes}
                        defaultEdgeOptions={defaultEdgeOptions}
                        onInit={setRfInstance}
                        fitView
                    >
                        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
                        <Controls />
                        <MiniMap
                            nodeStrokeColor={(n) => {
                                if (n.type === 'start') return '#10b981';
                                if (n.type === 'end') return '#ef4444';
                                return '#6366f1';
                            }}
                            nodeColor={(n) => {
                                return '#0f172a';
                            }}
                            maskColor="rgba(0, 0, 0, 0.3)"
                            className="!bg-slate-900 !border-slate-800 rounded-lg overflow-hidden"
                        />
                        <Panel position="bottom-right" className="bg-slate-900/80 backdrop-blur-sm border border-slate-800 p-2 rounded-lg text-[10px] text-slate-400 flex flex-col gap-1 shadow-xl">
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Start Node
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-indigo-500"></span> Workflow Step
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-red-500"></span> End Node
                            </div>
                        </Panel>
                    </ReactFlow>
                </Card>

                {/* Info */}
                <Card className="p-4">
                    <div className="text-sm text-slate-400">
                        <p><strong>Nodes:</strong> {nodes.length} | <strong>Edges:</strong> {edges.length}</p>
                        <p className="mt-2">
                            Drag nodes to reposition, click and drag from node edges to create connections.
                            {!id && <span className="text-yellow-400 ml-2">⚠️ Create a workflow first to enable saving</span>}
                        </p>
                    </div>
                </Card>
            </div>
        </Layout>
    );
};

import { ReactFlowProvider } from '@xyflow/react';

const WorkflowBuilderWrapper: React.FC = () => (
    <ReactFlowProvider>
        <WorkflowBuilder />
    </ReactFlowProvider>
);

export default WorkflowBuilderWrapper;
