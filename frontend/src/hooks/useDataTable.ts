import { useState, useMemo } from 'react';

export interface SortConfig {
    key: string;
    direction: 'asc' | 'desc';
}

export function useDataTable<T>(initialData: T[] = []) {
    const [data, setData] = useState<T[]>(initialData);
    const [selection, setSelection] = useState<Set<string>>(new Set());
    const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'created_at', direction: 'desc' });
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(50);
    const [total, setTotal] = useState(0);

    const toggleSelection = (id: string) => {
        const newSelection = new Set(selection);
        if (newSelection.has(id)) {
            newSelection.delete(id);
        } else {
            newSelection.add(id);
        }
        setSelection(newSelection);
    };

    const toggleAll = (ids: string[]) => {
        if (selection.size === ids.length && ids.length > 0) {
            setSelection(new Set());
        } else {
            setSelection(new Set(ids));
        }
    };

    const handleSort = (key: string) => {
        setSortConfig(current => ({
            key,
            direction: current.key === key && current.direction === 'desc' ? 'asc' : 'desc'
        }));
    };

    return {
        data,
        setData,
        selection,
        setSelection,
        toggleSelection,
        toggleAll,
        sortConfig,
        handleSort,
        page,
        setPage,
        pageSize,
        setPageSize,
        total,
        setTotal
    };
}
