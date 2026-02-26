import React, { memo } from 'react';
import { Handle, Position, useReactFlow } from '@xyflow/react';
import { Square, X as CloseIcon } from 'lucide-react';

export const EndNode = memo(({ id, data, isConnectable, selected }: any) => {
    const { deleteElements } = useReactFlow();
    return (
        <div className={`group bg-slate-900 border ${selected ? 'border-red-500 ring-2 ring-red-500/20' : 'border-red-700/50'} rounded-full shadow-lg min-w-[120px] transition-all duration-200 relative`}>
            {/* Delete button */}
            <button
                onClick={() => deleteElements({ nodes: [{ id }] })}
                className="absolute -top-1 -right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow-lg hover:bg-red-600 z-10"
            >
                <CloseIcon className="w-3 h-3" />
            </button>

            <div className="flex items-center px-4 py-2 bg-red-500/5 rounded-full">
                <div className="p-1.5 bg-red-500/10 rounded-full mr-2 border border-red-500/20">
                    <Square className="w-3 h-3 text-red-400 fill-red-400" />
                </div>
                <div className="text-xs font-bold text-red-400 uppercase tracking-widest">End</div>
            </div>
            <Handle type="target" position={Position.Top} isConnectable={isConnectable} className="bg-red-500 !w-3 !h-3" />
        </div>
    );
});
