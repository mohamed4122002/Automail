import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import api from '../../lib/api';
import { X } from 'lucide-react';
import { toast } from 'sonner';

interface AddUserModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export const AddUserModal: React.FC<AddUserModalProps> = ({ isOpen, onClose }) => {
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        first_name: '',
        last_name: ''
    });
    const [error, setError] = useState('');

    const queryClient = useQueryClient();

    const createUserMutation = useMutation({
        mutationFn: async (data: typeof formData) => {
            const response = await api.post('/auth/register', data);
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
            setFormData({ email: '', password: '', first_name: '', last_name: '' });
            setError('');
            onClose();
            toast.success('User created successfully!');
        },
        onError: (err: any) => {
            setError(err.response?.data?.detail || 'Failed to create user');
        }
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!formData.email || !formData.password || !formData.first_name || !formData.last_name) {
            setError('All fields are required');
            return;
        }

        createUserMutation.mutate(formData);
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData(prev => ({
            ...prev,
            [e.target.name]: e.target.value
        }));
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Add New User">
            <div className="bg-slate-900 rounded-lg p-6 w-full max-w-md">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-slate-200">Add New User</h2>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-slate-200 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {error && (
                        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 text-sm text-red-400">
                            {error}
                        </div>
                    )}

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Email *
                        </label>
                        <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                            placeholder="user@example.com"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Password *
                        </label>
                        <input
                            type="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                            placeholder="••••••••"
                            required
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                First Name *
                            </label>
                            <input
                                type="text"
                                name="first_name"
                                value={formData.first_name}
                                onChange={handleChange}
                                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                                placeholder="John"
                                required
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Last Name *
                            </label>
                            <input
                                type="text"
                                name="last_name"
                                value={formData.last_name}
                                onChange={handleChange}
                                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                                placeholder="Doe"
                                required
                            />
                        </div>
                    </div>

                    <div className="flex gap-3 pt-4">
                        <Button
                            type="button"
                            variant="secondary"
                            onClick={onClose}
                            className="flex-1"
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            className="flex-1"
                            disabled={createUserMutation.isPending}
                        >
                            {createUserMutation.isPending ? 'Creating...' : 'Create User'}
                        </Button>
                    </div>
                </form>
            </div>
        </Modal>
    );
};
