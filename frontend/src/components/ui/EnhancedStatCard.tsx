import React from 'react';
import { TrendingUp, TrendingDown, Minus, Info } from 'lucide-react';
import classNames from 'classnames';

interface StatCardProps {
    title: string;
    value: number | string;
    icon: React.ReactNode;
    description?: string;
    trend?: {
        value: number; // Percentage change
        direction: 'up' | 'down' | 'neutral';
    };
    tooltip?: string;
    variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
    format?: 'number' | 'percentage' | 'currency';
}

export const EnhancedStatCard: React.FC<StatCardProps> = ({
    title,
    value,
    icon,
    description,
    trend,
    tooltip,
    variant = 'default',
    format = 'number'
}) => {
    const formatValue = (val: number | string): string => {
        if (typeof val === 'string') return val;

        switch (format) {
            case 'percentage':
                return `${val.toFixed(1)}%`;
            case 'currency':
                return `$${val.toLocaleString()}`;
            case 'number':
            default:
                return val.toLocaleString();
        }
    };

    const variantStyles = {
        default: 'from-slate-800/40 to-slate-900/40 border-slate-700/30',
        success: 'from-emerald-900/20 to-emerald-950/20 border-emerald-500/30',
        warning: 'from-amber-900/20 to-amber-950/20 border-amber-500/30',
        danger: 'from-red-900/20 to-red-950/20 border-red-500/30',
        info: 'from-indigo-900/20 to-indigo-950/20 border-indigo-500/30'
    };

    const iconColors = {
        default: 'text-slate-400',
        success: 'text-emerald-400',
        warning: 'text-amber-400',
        danger: 'text-red-400',
        info: 'text-indigo-400'
    };

    const getTrendIcon = () => {
        if (!trend) return null;

        switch (trend.direction) {
            case 'up':
                return <TrendingUp className="w-4 h-4" />;
            case 'down':
                return <TrendingDown className="w-4 h-4" />;
            case 'neutral':
                return <Minus className="w-4 h-4" />;
        }
    };

    const getTrendColor = () => {
        if (!trend) return '';

        // For metrics where up is good (opens, clicks, etc.)
        if (trend.direction === 'up') return 'text-emerald-400';
        if (trend.direction === 'down') return 'text-red-400';
        return 'text-slate-400';
    };

    return (
        <div
            className={classNames(
                "relative group p-6 rounded-xl border backdrop-blur-sm",
                "bg-gradient-to-br shadow-lg",
                "hover:shadow-xl hover:scale-[1.02] transition-all duration-300",
                variantStyles[variant]
            )}
        >
            {/* Tooltip */}
            {tooltip && (
                <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="relative group/tooltip">
                        <Info className="w-4 h-4 text-slate-500 cursor-help" />
                        <div className="absolute right-0 top-6 w-64 p-3 bg-slate-900 border border-slate-700 rounded-lg shadow-xl opacity-0 group-hover/tooltip:opacity-100 transition-opacity pointer-events-none z-10">
                            <p className="text-xs text-slate-300">{tooltip}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Icon */}
            <div className={classNames(
                "flex items-center justify-center w-12 h-12 rounded-lg mb-4",
                "bg-slate-800/50",
                iconColors[variant]
            )}>
                {icon}
            </div>

            {/* Title */}
            <h3 className="text-sm font-medium text-slate-400 mb-1">{title}</h3>

            {/* Value */}
            <div className="flex items-baseline gap-2 mb-2">
                <p className="text-3xl font-bold text-slate-100">
                    {formatValue(value)}
                </p>

                {/* Trend Indicator */}
                {trend && (
                    <div className={classNames(
                        "flex items-center gap-1 text-sm font-semibold",
                        getTrendColor()
                    )}>
                        {getTrendIcon()}
                        <span>{Math.abs(trend.value).toFixed(1)}%</span>
                    </div>
                )}
            </div>

            {/* Description */}
            {description && (
                <p className="text-xs text-slate-500">{description}</p>
            )}

            {/* Hover Glow Effect */}
            <div className={classNames(
                "absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity",
                "bg-gradient-to-br pointer-events-none",
                variant === 'success' && "from-emerald-500/5 to-transparent",
                variant === 'warning' && "from-amber-500/5 to-transparent",
                variant === 'danger' && "from-red-500/5 to-transparent",
                variant === 'info' && "from-indigo-500/5 to-transparent"
            )} />
        </div>
    );
};

export default EnhancedStatCard;
