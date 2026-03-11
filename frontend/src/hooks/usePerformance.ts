import { useEffect, useRef } from "react";

/**
 * A hook to measure the render time and lifecycle events of a component.
 * Results are logged to the console in development mode.
 */
export function usePerformanceMeasure(componentName: string) {
    const renderCount = useRef(0);
    const startTime = useRef(performance.now());

    useEffect(() => {
        const duration = performance.now() - startTime.current;
        renderCount.current += 1;

        // Only log significant render times or every Nth render in dev
        if (process.env.NODE_ENV === "development") {
            console.debug(
                `[Perf] ${componentName} rendered in ${duration.toFixed(2)}ms (Count: ${renderCount.current})`
            );
        }

        // Reset start time for next potential re-render
        startTime.current = performance.now();
    });
}

/**
 * Utility to measure the execution time of an async function.
 */
export async function measureAsync<T>(name: string, fn: () => Promise<T>): Promise<T> {
    const start = performance.now();
    try {
        const result = await fn();
        const end = performance.now();
        console.debug(`[Perf] ${name} took ${(end - start).toFixed(2)}ms`);
        return result;
    } catch (error) {
        const end = performance.now();
        console.error(`[Perf] ${name} failed after ${(end - start).toFixed(2)}ms`);
        throw error;
    }
}
