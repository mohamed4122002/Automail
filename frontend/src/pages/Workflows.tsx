import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import api from '../lib/api';
import { Plus, Edit, Trash2, Play, Pause } from 'lucide-react';
import { toast } from 'sonner';

interface Workflow {
    id: string;
    name: string;
    description: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

const Workflows: React.FC = () => {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newWorkflow, setNewWorkflow] = useState({ name: '', description: '' });

    const { data: workflows, isLoading } = useQuery({
        queryKey: ['workflows'],
        queryFn: async () => {
            const response = await api.get<Workflow[]>('/workflows');
            return response.data;
        }
    });

    const createMutation = useMutation({
        mutationFn: async (data: { name: string; description: string }) => {
            const response = await api.post('/workflows', data);
            return response.data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['workflows'] });
            setShowCreateModal(false);
            setNewWorkflow({ name: '', description: '' });
            toast.success('Workflow created successfully!');
            // Navigate to workflow builder
            navigate(`/workflows/${data.id}/edit`);
        }
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            await api.delete(`/workflows/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['workflows'] });
            toast.success('Workflow deleted successfully!');
        }
    });

    const handleCreate = () => {
        if (!newWorkflow.name) {
            toast.error('Please enter a workflow name');
            return;
        }
        createMutation.mutate(newWorkflow);
    };

    return (
        <Layout title="Workflows">
            <div className="space-y-6">
                <div className="flex justify-between items-center">
                    <h2 className="text-2xl font-bold text-slate-200">Workflows</h2>
                    <Button
                        leftIcon={<Plus className="w-4 h-4" />}
                        onClick={() => setShowCreateModal(true)}
                    >
                        Create Workflow
                    </Button>
                </div>

                {isLoading ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {workflows?.map((workflow) => (
                            <Card key={workflow.id} className="p-6">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex-1">
                                        <h3 className="text-lg font-semibold text-slate-200">{workflow.name}</h3>
                                        {workflow.description && (
                                            <p className="text-sm text-slate-400 mt-1">{workflow.description}</p>
                                        )}
                                    </div>
                                    <span className={`px-2 py-1 text-xs rounded ${workflow.is_active
                                        ? 'bg-emerald-500/10 text-emerald-400'
                                        : 'bg-slate-500/10 text-slate-400'
                                        }`}>
                                        {workflow.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                </div>

                                <div className="text-xs text-slate-500 mb-4">
                                    Created: {new Date(workflow.created_at).toLocaleDateString()}
                                </div>

                                <div className="flex gap-2">
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        leftIcon={<Edit className="w-4 h-4" />}
                                        onClick={() => navigate(`/workflows/${workflow.id}/edit`)}
                                        className="flex-1"
                                    >
                                        Edit
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => {
                                            if (confirm('Are you sure you want to delete this workflow?')) {
                                                deleteMutation.mutate(workflow.id);
                                            }
                                        }}
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </Button>
                                </div>
                            </Card>
                        ))}

                        {workflows?.length === 0 && (
                            <div className="col-span-full text-center py-12 text-slate-500">
                                <p>No workflows yet. Create your first workflow to get started!</p>
                            </div>
                        )}
                    </div>
                )}

                {/* Create Modal */}
                <Modal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} title="Create New Workflow">
                    <div className="bg-slate-900 rounded-lg p-6 w-full max-w-md">
                        <h3 className="text-xl font-bold text-slate-200 mb-4">Create New Workflow</h3>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    Workflow Name *
                                </label>
                                <input
                                    type="text"
                                    value={newWorkflow.name}
                                    onChange={(e) => setNewWorkflow({ ...newWorkflow, name: e.target.value })}
                                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                                    placeholder="e.g., Welcome Series"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    Description
                                </label>
                                <textarea
                                    value={newWorkflow.description}
                                    onChange={(e) => setNewWorkflow({ ...newWorkflow, description: e.target.value })}
                                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                                    rows={3}
                                    placeholder="Describe this workflow..."
                                />
                            </div>

                            <div className="flex gap-3 pt-4">
                                <Button
                                    variant="secondary"
                                    onClick={() => setShowCreateModal(false)}
                                    className="flex-1"
                                >
                                    Cancel
                                </Button>
                                <Button
                                    onClick={handleCreate}
                                    disabled={createMutation.isPending}
                                    className="flex-1"
                                >
                                    {createMutation.isPending ? 'Creating...' : 'Create & Edit'}
                                </Button>
                            </div>
                        </div>
                    </div>
                </Modal>
            </div>
        </Layout>
    );
};

export default Workflows;
