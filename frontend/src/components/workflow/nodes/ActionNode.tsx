import React, { memo } from 'react';
import { Handle, Position, useReactFlow } from '@xyflow/react';
import { Zap, X as CloseIcon } from 'lucide-react';

export const ActionNode = memo(({ id, data, isConnectable, selected }: any) => {
    const { deleteElements } = useReactFlow();
    return (
        <div className={`group bg-slate-900 border ${selected ? 'border-indigo-500 ring-2 ring-indigo-500/20' : 'border-indigo-700/50'} rounded-lg shadow-lg w-64 transition-all duration-200 relative`}>
            {/* Delete button */}
            <button
                onClick={() => deleteElements({ nodes: [{ id }] })}
                className="absolute -top-2 -right-2 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow-lg hover:bg-red-600 z-10"
            >
                <CloseIcon className="w-3 h-3" />
            </button>

            <Handle type="target" position={Position.Top} isConnectable={isConnectable} className="bg-indigo-500 !w-3 !h-3" />

            <div className="flex items-center px-4 py-2 border-b border-slate-800 bg-indigo-500/5 rounded-t-lg">
                <div className="p-1.5 bg-indigo-500/10 rounded mr-3">
                    <Zap className="w-4 h-4 text-indigo-400" />
                </div>
                <span className="text-sm font-medium text-slate-200">Automated Action</span>
            </div>

            <div className="p-4">
                <label className="block text-xs font-medium text-slate-500 mb-1">Action Type</label>
                <div className="bg-slate-950 px-3 py-2 rounded border border-slate-800 text-xs text-indigo-300 font-mono">
                    {data.action || "update_lead_status"}
                </div>
                {data.status && (
                    <div className="mt-2 flex items-center gap-2">
                        <span className="text-[10px] text-slate-500 uppercase font-bold">Value:</span>
                        <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 text-[10px] font-bold">
                            {data.status}
                        </span>
                    </div>
                )}
            </div>

            <Handle type="source" position={Position.Bottom} isConnectable={isConnectable} className="bg-indigo-500 !w-3 !h-3" />
        </div>
    );
});
