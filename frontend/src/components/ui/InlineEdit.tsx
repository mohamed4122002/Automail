import React, { useState, useRef, useEffect } from 'react';
import { Check, X, Edit2 } from 'lucide-react';
import classNames from 'classnames';

interface InlineEditProps {
    value: string;
    onSave: (newValue: string) => Promise<void> | void;
    placeholder?: string;
    multiline?: boolean;
    className?: string;
    editClassName?: string;
    displayClassName?: string;
}

export const InlineEdit: React.FC<InlineEditProps> = ({
    value,
    onSave,
    placeholder = 'Click to edit',
    multiline = false,
    className = '',
    editClassName = '',
    displayClassName = ''
}) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState(value);
    const [isSaving, setIsSaving] = useState(false);
    const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

    useEffect(() => {
        setEditValue(value);
    }, [value]);

    useEffect(() => {
        if (isEditing && inputRef.current) {
            inputRef.current.focus();
            inputRef.current.select();
        }
    }, [isEditing]);

    const handleSave = async () => {
        if (editValue.trim() === value.trim()) {
            setIsEditing(false);
            return;
        }

        setIsSaving(true);
        try {
            await onSave(editValue.trim());
            setIsEditing(false);
        } catch (error) {
            console.error('Failed to save:', error);
            setEditValue(value); // Revert on error
        } finally {
            setIsSaving(false);
        }
    };

    const handleCancel = () => {
        setEditValue(value);
        setIsEditing(false);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !multiline) {
            e.preventDefault();
            handleSave();
        } else if (e.key === 'Escape') {
            handleCancel();
        } else if (e.key === 'Enter' && multiline && e.ctrlKey) {
            e.preventDefault();
            handleSave();
        }
    };

    if (!isEditing) {
        return (
            <div
                onClick={() => setIsEditing(true)}
                className={classNames(
                    "group relative cursor-pointer rounded-lg transition-all",
                    "hover:bg-slate-800/50 px-2 py-1 -mx-2 -my-1",
                    className,
                    displayClassName
                )}
            >
                <span className={classNames(
                    value ? "text-slate-100" : "text-slate-500 italic"
                )}>
                    {value || placeholder}
                </span>
                <Edit2 className="w-3 h-3 text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity absolute right-2 top-1/2 -translate-y-1/2" />
            </div>
        );
    }

    const InputComponent = multiline ? 'textarea' : 'input';

    return (
        <div className={classNames("relative flex items-center gap-2", className)}>
            <InputComponent
                ref={inputRef as any}
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={handleSave}
                disabled={isSaving}
                placeholder={placeholder}
                className={classNames(
                    "flex-1 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2",
                    "text-slate-100 placeholder:text-slate-500",
                    "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
                    "disabled:opacity-50 disabled:cursor-not-allowed",
                    multiline && "resize-none min-h-[80px]",
                    editClassName
                )}
                {...(multiline ? { rows: 3 } : {})}
            />

            <div className="flex gap-1">
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        handleSave();
                    }}
                    disabled={isSaving}
                    className={classNames(
                        "p-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500",
                        "text-white transition-all active:scale-95",
                        "disabled:opacity-50 disabled:cursor-not-allowed"
                    )}
                    title="Save (Enter)"
                >
                    <Check className="w-4 h-4" />
                </button>
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        handleCancel();
                    }}
                    disabled={isSaving}
                    className={classNames(
                        "p-1.5 rounded-lg bg-slate-700 hover:bg-slate-600",
                        "text-slate-300 transition-all active:scale-95",
                        "disabled:opacity-50 disabled:cursor-not-allowed"
                    )}
                    title="Cancel (Esc)"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
};

export default InlineEdit;
