import React from 'react';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/Button";
import {
    ChevronLeft,
    ChevronRight,
    ChevronsLeft,
    ChevronsRight,
    ArrowUpDown,
    ArrowUp,
    ArrowDown
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Column<T> {
    key: string;
    header: string | React.ReactNode;
    cell: (item: T) => React.ReactNode;
    sortable?: boolean;
    className?: string;
}

interface DataTableProps<T> {
    data: T[];
    columns: Column<T>[];
    keyField: keyof T;
    selection: Set<string>;
    onToggleSelection: (id: string) => void;
    onToggleAll: (ids: string[]) => void;
    sortConfig: { key: string; direction: 'asc' | 'desc' };
    onSort: (key: string) => void;
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
    isLoading?: boolean;
    emptyMessage?: React.ReactNode;
}

export function DataTable<T extends Record<string, any>>({
    data,
    columns,
    keyField,
    selection,
    onToggleSelection,
    onToggleAll,
    sortConfig,
    onSort,
    page,
    pageSize,
    total,
    onPageChange,
    isLoading = false,
    emptyMessage = "No data found"
}: DataTableProps<T>) {

    const totalPages = Math.ceil(total / pageSize);
    const allIds = data.map(item => String(item[keyField]));
    const allSelected = data.length > 0 && allIds.every(id => selection.has(id));
    const someSelected = data.length > 0 && allIds.some(id => selection.has(id));

    return (
        <div className="space-y-4">
            <div className="rounded-md border border-slate-700/50 overflow-hidden">
                <Table>
                    <TableHeader className="bg-slate-800/50">
                        <TableRow className="hover:bg-transparent border-slate-700/50">
                            <TableHead className="w-[40px] px-4">
                                <Checkbox
                                    checked={allSelected}
                                    onCheckedChange={() => onToggleAll(allIds)}
                                    className="border-slate-600 data-[state=checked]:bg-indigo-600 data-[state=checked]:border-indigo-600"
                                />
                            </TableHead>
                            {columns.map((col) => (
                                <TableHead
                                    key={col.key}
                                    className={cn(
                                        "h-10 text-slate-400 font-medium",
                                        col.sortable && "cursor-pointer hover:text-slate-200 select-none",
                                        col.className
                                    )}
                                    onClick={() => col.sortable && onSort(col.key)}
                                >
                                    <div className="flex items-center gap-2">
                                        {col.header}
                                        {col.sortable && (
                                            <div className="w-4 h-4 flex items-center justify-center">
                                                {sortConfig.key === col.key ? (
                                                    sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3 text-indigo-400" /> : <ArrowDown className="w-3 h-3 text-indigo-400" />
                                                ) : (
                                                    <ArrowUpDown className="w-3 h-3 opacity-30" />
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </TableHead>
                            ))}
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            Array.from({ length: 5 }).map((_, i) => (
                                <TableRow key={i} className="border-slate-700/30">
                                    <TableCell colSpan={columns.length + 1} className="h-16">
                                        <div className="w-full h-4 bg-slate-800/50 animate-pulse rounded"></div>
                                    </TableCell>
                                </TableRow>
                            ))
                        ) : data.length === 0 ? (
                            <TableRow className="border-slate-700/30">
                                <TableCell colSpan={columns.length + 1} className="h-32 text-center text-slate-500">
                                    {emptyMessage}
                                </TableCell>
                            </TableRow>
                        ) : (
                            data.map((item) => {
                                const id = String(item[keyField]);
                                const isSelected = selection.has(id);

                                return (
                                    <TableRow
                                        key={id}
                                        className={cn(
                                            "border-slate-700/30 transition-colors hover:bg-slate-800/30 group",
                                            isSelected && "bg-indigo-500/5 hover:bg-indigo-500/10"
                                        )}
                                    >
                                        <TableCell className="px-4">
                                            <Checkbox
                                                checked={isSelected}
                                                onCheckedChange={() => onToggleSelection(id)}
                                                className="border-slate-600 data-[state=checked]:bg-indigo-600 data-[state=checked]:border-indigo-600 opacity-50 group-hover:opacity-100 transition-opacity"
                                            />
                                        </TableCell>
                                        {columns.map((col) => (
                                            <TableCell key={col.key} className={cn("py-3", col.className)}>
                                                {col.cell(item)}
                                            </TableCell>
                                        ))}
                                    </TableRow>
                                );
                            })
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-2">
                <div className="text-sm text-slate-500">
                    Showing {data.length > 0 ? (page - 1) * pageSize + 1 : 0} to {Math.min(page * pageSize, total)} of {total} results
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 border-slate-700 bg-slate-800 text-slate-400 hover:text-white"
                        onClick={() => onPageChange(1)}
                        disabled={page === 1}
                    >
                        <ChevronsLeft className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 border-slate-700 bg-slate-800 text-slate-400 hover:text-white"
                        onClick={() => onPageChange(page - 1)}
                        disabled={page === 1}
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <div className="flex items-center gap-1 mx-2">
                        <span className="text-sm font-medium text-slate-300">Page {page} of {Math.max(1, totalPages)}</span>
                    </div>
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 border-slate-700 bg-slate-800 text-slate-400 hover:text-white"
                        onClick={() => onPageChange(page + 1)}
                        disabled={page >= totalPages}
                    >
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 border-slate-700 bg-slate-800 text-slate-400 hover:text-white"
                        onClick={() => onPageChange(totalPages)}
                        disabled={page >= totalPages}
                    >
                        <ChevronsRight className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
    );
}
