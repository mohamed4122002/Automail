import React from "react";
import classNames from "classnames";

interface SkeletonProps {
    className?: string;
    variant?: "rectangle" | "circle" | "text";
    height?: string | number;
    width?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
    className,
    variant = "rectangle",
    height,
    width,
}) => {
    const baseClasses = "relative overflow-hidden bg-slate-800/50 before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_2s_infinite] before:bg-gradient-to-r before:from-transparent before:via-slate-700/30 before:to-transparent";

    const variantClasses = {
        rectangle: "rounded-lg",
        circle: "rounded-full",
        text: "rounded-md h-[1em] w-full mb-2",
    };

    return (
        <div
            className={classNames(baseClasses, variantClasses[variant], className)}
            style={{ height, width }}
        />
    );
};

export default Skeleton;
