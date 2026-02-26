import React from 'react';
import classNames from 'classnames';

interface HeatmapData {
    hour: number;
    day: string;
    opens: number;
    clicks: number;
}

interface EngagementHeatmapProps {
    data: HeatmapData[];
}

export const EngagementHeatmap: React.FC<EngagementHeatmapProps> = ({ data }) => {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const hours = Array.from({ length: 24 }, (_, i) => i);

    // Calculate max value for color scaling
    const maxEngagement = Math.max(
        ...data.map(d => d.opens + d.clicks),
        1
    );

    const getEngagement = (hour: number, day: string): number => {
        const cell = data.find(d => d.hour === hour && d.day === day);
        return cell ? cell.opens + cell.clicks : 0;
    };

    const getColor = (engagement: number): string => {
        if (engagement === 0) return 'bg-slate-800/30';

        const intensity = engagement / maxEngagement;

        if (intensity > 0.75) return 'bg-emerald-500';
        if (intensity > 0.5) return 'bg-emerald-600';
        if (intensity > 0.25) return 'bg-indigo-500';
        if (intensity > 0.1) return 'bg-indigo-600';
        return 'bg-slate-700';
    };

    const formatHour = (hour: number): string => {
        if (hour === 0) return '12a';
        if (hour < 12) return `${hour}a`;
        if (hour === 12) return '12p';
        return `${hour - 12}p`;
    };

    return (
        <div className="w-full overflow-x-auto">
            <div className="inline-block min-w-full">
                {/* Hour labels */}
                <div className="flex mb-2">
                    <div className="w-12" /> {/* Spacer for day labels */}
                    {hours.filter(h => h % 3 === 0).map(hour => (
                        <div
                            key={hour}
                            className="flex-1 text-center text-xs text-slate-500"
                            style={{ minWidth: '40px' }}
                        >
                            {formatHour(hour)}
                        </div>
                    ))}
                </div>

                {/* Heatmap grid */}
                {days.map(day => (
                    <div key={day} className="flex items-center mb-1">
                        {/* Day label */}
                        <div className="w-12 text-xs font-medium text-slate-400">
                            {day}
                        </div>

                        {/* Hour cells */}
                        <div className="flex gap-1 flex-1">
                            {hours.map(hour => {
                                const engagement = getEngagement(hour, day);
                                const colorClass = getColor(engagement);

                                return (
                                    <div
                                        key={hour}
                                        className={classNames(
                                            "group relative rounded transition-all duration-200",
                                            "hover:scale-110 hover:z-10 cursor-pointer",
                                            colorClass
                                        )}
                                        style={{
                                            width: '100%',
                                            minWidth: '12px',
                                            height: '24px',
                                            flex: 1
                                        }}
                                        title={`${day} ${formatHour(hour)}: ${engagement} engagements`}
                                    >
                                        {/* Tooltip on hover */}
                                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20">
                                            <div className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 shadow-xl whitespace-nowrap">
                                                <p className="text-xs font-semibold text-slate-200">
                                                    {day} {formatHour(hour)}
                                                </p>
                                                <p className="text-xs text-slate-400">
                                                    {engagement} engagements
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ))}

                {/* Legend */}
                <div className="flex items-center justify-center gap-2 mt-4">
                    <span className="text-xs text-slate-500">Less</span>
                    <div className="flex gap-1">
                        <div className="w-4 h-4 rounded bg-slate-800/30" />
                        <div className="w-4 h-4 rounded bg-slate-700" />
                        <div className="w-4 h-4 rounded bg-indigo-600" />
                        <div className="w-4 h-4 rounded bg-indigo-500" />
                        <div className="w-4 h-4 rounded bg-emerald-600" />
                        <div className="w-4 h-4 rounded bg-emerald-500" />
                    </div>
                    <span className="text-xs text-slate-500">More</span>
                </div>
            </div>
        </div>
    );
};

export default EngagementHeatmap;
