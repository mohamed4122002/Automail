import React, { memo } from 'react';
import { Handle, Position, useReactFlow } from '@xyflow/react';
import { GitFork, X as CloseIcon } from 'lucide-react';

export const DecisionNode = memo(({ id, data, isConnectable, selected }: any) => {
    const { deleteElements } = useReactFlow();
    return (
        <div className={`group bg-slate-900 border ${selected ? 'border-indigo-500 ring-2 ring-indigo-500/20' : 'border-slate-700'} rounded-lg shadow-lg w-64 transition-all duration-200 relative transform rotate-0`}>
            {/* Delete button */}
            <button
                onClick={() => deleteElements({ nodes: [{ id }] })}
                className="absolute -top-2 -right-2 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow-lg hover:bg-red-600 z-10"
            >
                <CloseIcon className="w-3 h-3" />
            </button>

            <Handle type="target" position={Position.Top} isConnectable={isConnectable} className="bg-slate-400 !w-3 !h-3" />

            <div className="flex items-center px-4 py-2 border-b border-slate-800 bg-slate-800/50 rounded-t-lg">
                <div className="p-1.5 bg-slate-700/50 rounded mr-3">
                    <GitFork className="w-4 h-4 text-slate-300" />
                </div>
                <span className="text-sm font-medium text-slate-200">Condition Check</span>
            </div>

            <div className="p-4">
                <div className="text-xs text-slate-400 mb-2">Check if user has:</div>
                <div className="bg-slate-950 px-3 py-2 rounded border border-slate-800 text-xs text-indigo-300 font-mono">
                    {data.conditionLabel || "Opened Email"}
                </div>
            </div>

            <div className="flex justify-between px-4 pb-4">
                <div className="relative">
                    <span className="absolute -top-6 left-0 text-[10px] text-emerald-500 font-bold">YES</span>
                    <Handle type="source" position={Position.Bottom} id="true" isConnectable={isConnectable} className="bg-emerald-500 !w-3 !h-3 !-bottom-1.5" style={{ left: '20%' }} />
                </div>
                <div className="relative">
                    <span className="absolute -top-6 right-0 text-[10px] text-red-500 font-bold">NO</span>
                    <Handle type="source" position={Position.Bottom} id="false" isConnectable={isConnectable} className="bg-red-500 !w-3 !h-3 !-bottom-1.5" style={{ left: '80%' }} />
                </div>
            </div>
        </div>
    );
});
