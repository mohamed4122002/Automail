import React, { memo } from 'react';
import { Handle, Position, useReactFlow } from '@xyflow/react';
import { Zap, X as CloseIcon } from 'lucide-react';

export const TriggerNode = memo(({ id, data, isConnectable, selected }: any) => {
    const { deleteElements } = useReactFlow();

    return (
        <div className={`group bg-slate-900 border ${selected ? 'border-emerald-500 ring-2 ring-emerald-500/20' : 'border-emerald-700/50'} rounded-full shadow-lg min-w-[200px] transition-all duration-200 relative`}>
            {/* Delete button */}
            <button
                onClick={() => deleteElements({ nodes: [{ id }] })}
                className="absolute -top-1 -right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow-lg hover:bg-red-600 z-10"
            >
                <CloseIcon className="w-3 h-3" />
            </button>

            <div className="flex items-center px-4 py-3 bg-emerald-500/5 rounded-full">
                <div className="p-2 bg-emerald-500/10 rounded-full mr-3 border border-emerald-500/20">
                    <Zap className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                    <div className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Trigger</div>
                    <div className="text-sm font-medium text-slate-200 whitespace-nowrap">{data.label || "Contact Added"}</div>
                </div>
            </div>
            <Handle type="source" position={Position.Bottom} isConnectable={isConnectable} className="bg-emerald-500 !w-3 !h-3" />
        </div>
    );
});
