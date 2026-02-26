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
        <Card className="hover:border-indigo-500/50 transition-colors duration-300">
            <CardContent className="p-6">
                <div className="flex items-center justify-between space-x-4">
                    <div className="flex items-center justify-center w-12 h-12 rounded-full bg-slate-800 text-indigo-400 ring-1 ring-slate-700">
                        {icon}
                    </div>
                    {trend && (
                        <div className={classNames(
                            "flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                            trend.isPositive ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                        )}>
                            {trend.isPositive ? (
                                <ArrowUpRight className="w-3 h-3 mr-1" />
                            ) : (
                                <ArrowDownRight className="w-3 h-3 mr-1" />
                            )}
                            {Math.abs(trend.value)}%
                        </div>
                    )}
                </div>

                <div className="mt-4">
                    <h3 className="text-sm font-medium text-slate-400">{title}</h3>
                    <div className="mt-1 text-2xl font-bold text-slate-100">{value}</div>
                    {description && (
                        <p className="mt-1 text-xs text-slate-500">{description}</p>
                    )}
                </div>
            </CardContent>
        </Card>
    );
};
