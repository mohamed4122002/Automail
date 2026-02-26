import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Send, User, Trash2, Clock } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import api from '../../lib/api';

interface Note {
    id: string;
    content: string;
    user_id: string;
    created_by_id: string | null;
    created_at: string;
}

interface NotesSidebarProps {
    userId: string;
    userName: string;
    onClose: () => void;
}

const NotesSidebar: React.FC<NotesSidebarProps> = ({ userId, userName, onClose }) => {
    const [content, setContent] = useState('');
    const queryClient = useQueryClient();

    // Fetch notes for this user
    const { data: notes, isLoading } = useQuery<Note[]>({
        queryKey: ['user-notes', userId],
        queryFn: async () => {
            const response = await api.get(`/users/${userId}/notes`);
            return response.data;
        },
        enabled: !!userId
    });

    // Add note mutation
    const addNoteMutation = useMutation({
        mutationFn: async (newContent: string) => {
            const response = await api.post(`/users/${userId}/notes`, { content: newContent });
            return response.data;
        },
        onSuccess: () => {
            setContent('');
            queryClient.invalidateQueries({ queryKey: ['user-notes', userId] });
        }
    });

    // Real-time listener
    React.useEffect(() => {
        const ws = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws/dashboard`);

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'new_note' && data.user_id === userId) {
                    queryClient.invalidateQueries({ queryKey: ['user-notes', userId] });
                }
                if (data.type === 'delete_note' && data.user_id === userId) {
                    queryClient.invalidateQueries({ queryKey: ['user-notes', userId] });
                }
            } catch (err) {
                console.error("WS parse error:", err);
            }
        };

        return () => ws.close();
    }, [userId, queryClient]);

    // Delete note mutation
    const deleteNoteMutation = useMutation({
        mutationFn: async (noteId: string) => {
            await api.delete(`/notes/${noteId}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['user-notes', userId] });
        }
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (content.trim()) {
            addNoteMutation.mutate(content.trim());
        }
    };

    return (
        <div className="fixed inset-y-0 right-0 w-96 bg-slate-900 border-l border-slate-800 shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50 backdrop-blur-sm">
                <div>
                    <h2 className="text-lg font-bold text-slate-100">Collaboration Notes</h2>
                    <p className="text-xs text-slate-400 mt-0.5">{userName}</p>
                </div>
                <button
                    onClick={onClose}
                    className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-100 transition-colors"
                >
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* Notes List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {isLoading ? (
                    <div className="flex justify-center py-8">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-500"></div>
                    </div>
                ) : notes?.length === 0 ? (
                    <div className="text-center py-12">
                        <User className="w-12 h-12 text-slate-700 mx-auto mb-3" />
                        <p className="text-slate-500 text-sm">No notes yet. Start the conversation!</p>
                    </div>
                ) : (
                    notes?.map((note) => (
                        <Card key={note.id} className="p-3 bg-slate-800/50 border-slate-700/50 group">
                            <div className="flex justify-between items-start mb-2">
                                <div className="flex items-center gap-2">
                                    <div className="w-6 h-6 rounded-full bg-indigo-500/20 flex items-center justify-center">
                                        <User className="w-3 h-3 text-indigo-400" />
                                    </div>
                                    <span className="text-xs font-medium text-slate-300">
                                        {note.created_by_id ? 'Team Member' : 'System'}
                                    </span>
                                </div>
                                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button
                                        onClick={() => deleteNoteMutation.mutate(note.id)}
                                        className="p-1 hover:text-red-400 text-slate-500"
                                    >
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                            <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                                {note.content}
                            </p>
                            <div className="mt-2 flex items-center gap-1.5 text-[10px] text-slate-500">
                                <Clock className="w-3 h-3" />
                                {new Date(note.created_at).toLocaleString()}
                            </div>
                        </Card>
                    ))
                )}
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-slate-800 bg-slate-900/80 backdrop-blur-sm">
                <form onSubmit={handleSubmit} className="relative">
                    <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        placeholder="Add a collaboration note..."
                        className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 pr-12 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500 transition-all resize-none min-h-[100px]"
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSubmit(e);
                            }
                        }}
                    />
                    <button
                        type="submit"
                        disabled={!content.trim() || addNoteMutation.isPending}
                        className="absolute bottom-3 right-3 p-2 bg-indigo-500 hover:bg-indigo-600 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg transition-all shadow-lg shadow-indigo-500/20"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </form>
                <p className="text-[10px] text-slate-500 mt-2 text-center">
                    Press Enter to send, Shift+Enter for new line
                </p>
            </div>
        </div>
    );
};

export default NotesSidebar;
