import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import api from '../lib/api';
import { Plus, Edit, Trash2, FileText } from 'lucide-react';

interface Template {
    id: string;
    name: string;
    subject: string;
    html_body: string;
}

const Templates: React.FC = () => {
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const { data: templates, isLoading } = useQuery({
        queryKey: ['templates'],
        queryFn: async () => {
            const response = await api.get<Template[]>('/templates');
            return response.data;
        }
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            await api.delete(`/templates/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['templates'] });
        }
    });

    return (
        <Layout title="Email Templates">
            <div className="space-y-6">
                <div className="flex justify-between items-center">
                    <h2 className="text-2xl font-bold text-slate-200">Email Templates</h2>
                    <Button
                        leftIcon={<Plus className="w-4 h-4" />}
                        onClick={() => navigate('/templates/new')}
                    >
                        Create Template
                    </Button>
                </div>

                {isLoading ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {templates?.map((template) => (
                            <Card key={template.id} className="p-6 group hover:border-indigo-500/50 transition-colors">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="p-2 bg-indigo-500/10 rounded-lg">
                                        <FileText className="w-6 h-6 text-indigo-400" />
                                    </div>
                                    <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            onClick={() => navigate(`/templates/${template.id}/edit`)}
                                            className="p-1.5 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800"
                                        >
                                            <Edit className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={() => {
                                                if (confirm('Are you sure you want to delete this template?')) {
                                                    deleteMutation.mutate(template.id);
                                                }
                                            }}
                                            className="p-1.5 text-slate-400 hover:text-red-400 rounded-lg hover:bg-slate-800"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>

                                <h3 className="text-lg font-semibold text-slate-200 mb-1">{template.name}</h3>
                                <p className="text-sm text-slate-400 truncate mb-4">{template.subject}</p>

                                <div className="flex items-center justify-between pt-4 border-t border-slate-800/50">
                                    <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Liquid Enabled</span>
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => navigate(`/templates/${template.id}/edit`)}
                                    >
                                        Edit Content
                                    </Button>
                                </div>
                            </Card>
                        ))}

                        {templates?.length === 0 && (
                            <div className="col-span-full text-center py-20 border-2 border-dashed border-slate-800 rounded-2xl">
                                <FileText className="w-12 h-12 text-slate-700 mx-auto mb-4" />
                                <h3 className="text-lg font-medium text-slate-400">No templates found</h3>
                                <p className="text-sm text-slate-500 mt-1 mb-6">Start by creating your first reusable email template.</p>
                                <Button
                                    leftIcon={<Plus className="w-4 h-4" />}
                                    onClick={() => navigate('/templates/new')}
                                >
                                    Create Template
                                </Button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default Templates;
