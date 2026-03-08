import React from "react";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import { Card, CardContent } from "./Card";
import classNames from "classnames";

interface StatsCardProps {
    title: string;
    value: string | number;
    trend?: {
        value: number;
        isPositive: boolean;
    };
    icon?: React.ReactNode;
    description?: string;
}

export const StatsCard: React.FC<StatsCardProps> = ({ title, value, trend, icon, description }) => {
    return (
        <Card className="bg-slate-900/50 border border-slate-800/60 overflow-hidden relative group hover:bg-slate-900/80 transition-all duration-300">
            {/* Subtle top glow line */}
            <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-slate-700/50 to-transparent group-hover:via-slate-500/50 transition-colors duration-500" />

            <CardContent className="p-5 flex flex-col justify-center h-full">
                <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-2">
                        {/* Status Dot */}
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                        <h3 className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400">{title}</h3>
                    </div>
                    <div className="p-2 rounded-lg bg-slate-800/40 text-slate-300 border border-slate-700/30 group-hover:scale-110 transition-transform duration-300">
                        {icon}
                    </div>
                </div>

                <div className="flex items-baseline gap-2 mt-auto">
                    <p className="text-3xl font-black text-slate-100 italic tracking-tight">{value}</p>

                    {trend && (
                        <div className={classNames(
                            "flex items-center ml-2 px-1.5 py-0.5 rounded-md text-[10px] font-bold tracking-wider",
                            trend.isPositive ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        )}>
                            {trend.isPositive ? <ArrowUpRight className="w-3 h-3 mr-0.5" /> : <ArrowDownRight className="w-3 h-3 mr-0.5" />}
                            {Math.abs(trend.value)}%
                        </div>
                    )}
                </div>

                {description && (
                    <p className="text-[10px] font-semibold text-slate-500 mt-2 uppercase tracking-wider">{description}</p>
                )}
            </CardContent>
        </Card>
    );
};
