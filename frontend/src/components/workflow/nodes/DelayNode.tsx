import React, { memo } from 'react';
import { Handle, Position, useReactFlow } from '@xyflow/react';
import { Clock, X as CloseIcon } from 'lucide-react';

export const DelayNode = memo(({ id, data, isConnectable, selected }: any) => {
    const { deleteElements } = useReactFlow();
    return (
        <div className={`group bg-slate-900 border ${selected ? 'border-yellow-500 ring-2 ring-yellow-500/20' : 'border-yellow-700/50'} rounded-lg shadow-lg w-48 transition-all duration-200 relative`}>
            {/* Delete button */}
            <button
                onClick={() => deleteElements({ nodes: [{ id }] })}
                className="absolute -top-2 -right-2 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow-lg hover:bg-red-600 z-10"
            >
                <CloseIcon className="w-3 h-3" />
            </button>

            <Handle type="target" position={Position.Top} isConnectable={isConnectable} className="bg-yellow-500 !w-3 !h-3" />

            <div className="flex items-center px-4 py-2 border-b border-slate-800 bg-yellow-500/5 rounded-t-lg">
                <div className="p-1.5 bg-yellow-500/10 rounded mr-3">
                    <Clock className="w-4 h-4 text-yellow-500" />
                </div>
                <span className="text-sm font-medium text-slate-200">Time Delay</span>
            </div>

            <div className="p-4 flex flex-col gap-2">
                <label className="text-[10px] text-slate-500">Wait Duration (Hours)</label>
                <input
                    type="number"
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-300 text-center"
                    defaultValue={data.hours || 1}
                    onChange={(e) => data.hours = parseInt(e.target.value)}
                />
            </div>

            <Handle type="source" position={Position.Bottom} isConnectable={isConnectable} className="bg-yellow-500 !w-3 !h-3" />
        </div>
    );
});
