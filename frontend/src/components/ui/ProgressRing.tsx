import React from 'react';
import classNames from 'classnames';

interface ProgressRingProps {
    current: number;
    total: number;
    size?: number;
    strokeWidth?: number;
    className?: string;
    showLabel?: boolean;
}

export const ProgressRing: React.FC<ProgressRingProps> = ({
    current,
    total,
    size = 80,
    strokeWidth = 8,
    className = '',
    showLabel = true
}) => {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const percentage = total > 0 ? (current / total) * 100 : 0;
    const offset = circumference - (percentage / 100) * circumference;

    return (
        <div className={classNames("relative inline-flex items-center justify-center", className)}>
            <svg
                width={size}
                height={size}
                className="transform -rotate-90"
            >
                {/* Background circle */}
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke="currentColor"
                    strokeWidth={strokeWidth}
                    fill="none"
                    className="text-slate-700"
                />
                {/* Progress circle */}
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke="currentColor"
                    strokeWidth={strokeWidth}
                    fill="none"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    className={classNames(
                        "transition-all duration-500 ease-out",
                        percentage >= 100 ? "text-emerald-500" :
                            percentage >= 75 ? "text-indigo-500" :
                                percentage >= 50 ? "text-blue-500" :
                                    percentage >= 25 ? "text-amber-500" :
                                        "text-slate-500"
                    )}
                />
            </svg>

            {showLabel && (
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-lg font-bold text-slate-100">
                        {Math.round(percentage)}%
                    </span>
                    <span className="text-xs text-slate-400">
                        {current}/{total}
                    </span>
                </div>
            )}
        </div>
    );
};

export default ProgressRing;
