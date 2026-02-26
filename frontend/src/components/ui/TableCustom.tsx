import React from "react";
import classNames from "classnames";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./Button";

export interface Column<T> {
    header: string;
    accessor: keyof T | ((item: T) => React.ReactNode);
    className?: string;
}

export interface TableProps<T> {
    data: T[];
    columns: Column<T>[];
    keyExtractor: (item: T) => string | number;
    onRowClick?: (item: T) => void;
    isLoading?: boolean;
    pagination?: {
        currentPage: number;
        totalPages: number;
        onPageChange: (page: number) => void;
    };
}

export function Table<T>({ data, columns, keyExtractor, onRowClick, isLoading, pagination }: TableProps<T>) {
    return (
        <div className="w-full overflow-hidden rounded-xl border border-slate-700 bg-slate-900">
            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead className="text-xs text-slate-400 uppercase bg-slate-800/50 border-b border-slate-700">
                        <tr>
                            {columns.map((col, index) => (
                                <th key={index} className={classNames("px-6 py-4 font-medium", col.className)}>
                                    {col.header}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        {isLoading ? (
                            <tr>
                                <td colSpan={columns.length} className="px-6 py-8 text-center text-slate-500">
                                    Loading data...
                                </td>
                            </tr>
                        ) : data.length === 0 ? (
                            <tr>
                                <td colSpan={columns.length} className="px-6 py-8 text-center text-slate-500">
                                    No data available
                                </td>
                            </tr>
                        ) : (
                            data.map((item, rowIndex) => (
                                <tr
                                    key={keyExtractor(item)}
                                    onClick={() => onRowClick && onRowClick(item)}
                                    className={classNames(
                                        "bg-slate-900/50 hover:bg-slate-800/50 transition-colors",
                                        { "cursor-pointer": !!onRowClick }
                                    )}
                                >
                                    {columns.map((col, colIndex) => (
                                        <td key={colIndex} className={classNames("px-6 py-4 whitespace-nowrap text-slate-300", col.className)}>
                                            {typeof col.accessor === "function" ? col.accessor(item) : (item[col.accessor] as React.ReactNode)}
                                        </td>
                                    ))}
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {pagination && (
                <div className="flex items-center justify-between px-6 py-4 border-t border-slate-700">
                    <span className="text-sm text-slate-400">
                        Page {pagination.currentPage} of {pagination.totalPages}
                    </span>
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={pagination.currentPage <= 1}
                            onClick={() => pagination.onPageChange(pagination.currentPage - 1)}
                            aria-label="Previous page"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={pagination.currentPage >= pagination.totalPages}
                            onClick={() => pagination.onPageChange(pagination.currentPage + 1)}
                            aria-label="Next page"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
