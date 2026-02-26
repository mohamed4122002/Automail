import React, { useState, useRef, useEffect } from 'react';
import { MoreVertical, X } from 'lucide-react';
import classNames from 'classnames';

interface DropdownMenuItem {
    label: string;
    icon?: React.ReactNode;
    onClick: () => void;
    variant?: 'default' | 'danger';
    disabled?: boolean;
}

interface DropdownMenuProps {
    items: DropdownMenuItem[];
    trigger?: React.ReactNode;
    align?: 'left' | 'right';
}

export const DropdownMenu: React.FC<DropdownMenuProps> = ({
    items,
    trigger,
    align = 'right'
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen]);

    // Close on Escape key
    useEffect(() => {
        const handleEscape = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                setIsOpen(false);
            }
        };

        if (isOpen) {
            document.addEventListener('keydown', handleEscape);
        }

        return () => {
            document.removeEventListener('keydown', handleEscape);
        };
    }, [isOpen]);

    const handleItemClick = (item: DropdownMenuItem) => {
        if (!item.disabled) {
            item.onClick();
            setIsOpen(false);
        }
    };

    return (
        <div className="relative" ref={dropdownRef}>
            {/* Trigger Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={classNames(
                    "flex items-center justify-center p-2 rounded-lg transition-all",
                    "hover:bg-slate-700/50 active:bg-slate-700",
                    "border border-slate-700 hover:border-slate-600",
                    isOpen && "bg-slate-700/50 border-slate-600"
                )}
                aria-label="Open menu"
                aria-expanded={isOpen}
            >
                {trigger || <MoreVertical className="w-5 h-5 text-slate-300" />}
            </button>

            {/* Dropdown Menu */}
            {isOpen && (
                <div
                    className={classNames(
                        "absolute z-50 mt-2 min-w-[200px] rounded-xl",
                        "bg-slate-800 border border-slate-700 shadow-2xl",
                        "animate-in fade-in slide-in-from-top-2 duration-200",
                        align === 'right' ? 'right-0' : 'left-0'
                    )}
                >
                    <div className="p-2">
                        {items.map((item, index) => (
                            <button
                                key={index}
                                onClick={() => handleItemClick(item)}
                                disabled={item.disabled}
                                className={classNames(
                                    "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg",
                                    "text-sm font-medium transition-all",
                                    "disabled:opacity-50 disabled:cursor-not-allowed",
                                    item.variant === 'danger'
                                        ? "text-red-400 hover:bg-red-500/10 hover:text-red-300"
                                        : "text-slate-200 hover:bg-slate-700/50",
                                    !item.disabled && "active:scale-95"
                                )}
                            >
                                {item.icon && (
                                    <span className="flex-shrink-0">{item.icon}</span>
                                )}
                                <span className="flex-1 text-left">{item.label}</span>
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default DropdownMenu;
