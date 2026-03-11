import { useState, useEffect } from 'react';

/**
 * Returns a debounced version of the value that only updates after
 * the specified delay has passed without the value changing.
 *
 * Useful for delaying expensive operations (API calls, filtering)
 * while the user is still typing.
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
    const [debounced, setDebounced] = useState<T>(value);

    useEffect(() => {
        const timer = setTimeout(() => setDebounced(value), delay);
        return () => clearTimeout(timer);
    }, [value, delay]);

    return debounced;
}
