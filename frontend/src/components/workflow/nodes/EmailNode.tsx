import React, { memo } from 'react';
import { Handle, Position, useReactFlow } from '@xyflow/react';
import { Mail, Loader2, X as CloseIcon } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import api from '../../../lib/api';

export const EmailNode = memo(({ id, data, isConnectable, selected }: any) => {
    const { deleteElements } = useReactFlow();
    const { data: templates, isLoading } = useQuery({
        queryKey: ['templates'],
        queryFn: async () => {
            const response = await api.get('/templates');
            return response.data;
        }
    });

    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        data.template_id = e.target.value;
    };

    return (
        <div className={`group bg-slate-900 border ${selected ? 'border-indigo-500 ring-2 ring-indigo-500/20' : 'border-slate-700'} rounded-lg shadow-lg w-64 transition-all duration-200 relative`}>
            {/* Delete button */}
            <button
                onClick={() => deleteElements({ nodes: [{ id }] })}
                className="absolute -top-2 -right-2 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow-lg hover:bg-red-600 z-10"
            >
                <CloseIcon className="w-3 h-3" />
            </button>

            <Handle type="target" position={Position.Top} isConnectable={isConnectable} className="bg-indigo-500 !w-3 !h-3" />

            <div className="flex items-center px-4 py-2 border-b border-slate-800 bg-slate-800/50 rounded-t-lg">
                <div className="p-1.5 bg-indigo-500/10 rounded mr-3">
                    <Mail className="w-4 h-4 text-indigo-400" />
                </div>
                <span className="text-sm font-medium text-slate-200">Send Email</span>
            </div>

            <div className="p-4">
                <label className="block text-xs font-medium text-slate-500 mb-1">Template</label>
                {isLoading ? (
                    <div className="flex items-center gap-2 text-xs text-slate-500 py-1.5">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        Loading templates...
                    </div>
                ) : (
                    <select
                        className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-300 focus:ring-1 focus:ring-indigo-500 outline-none"
                        value={data.template_id || ""}
                        onChange={handleChange}
                    >
                        <option value="" disabled>Select a template...</option>
                        {templates?.map((t: any) => (
                            <option key={t.id} value={t.id}>{t.name}</option>
                        ))}
                        {data.template_id && !templates?.find((t: any) => t.id === data.template_id) && (
                            <option value={data.template_id}>{data.template_id}</option>
                        )}
                    </select>
                )}
            </div>

            <Handle type="source" position={Position.Bottom} isConnectable={isConnectable} className="bg-indigo-500 !w-3 !h-3" />
        </div>
    );
});
