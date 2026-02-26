import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
    ArrowLeft,
    Zap,
    AlertCircle,
    Mail,
    Copy,
    Download,
    Archive,
    Workflow as WorkflowIcon,
    Users,
    Clock,
    MoreVertical
} from 'lucide-react';
import { Button } from './Button';
import { Badge } from './Badge';
import { DropdownMenu } from './DropdownMenuCustom';
import { InlineEdit } from './InlineEdit';
import { ProgressRing } from './ProgressRing';
import classNames from 'classnames';
import { toast } from 'sonner';

interface CampaignHeaderProps {
    campaign: {
        id: string;
        name: string;
        description?: string;
        is_active: boolean;
        contact_list_id?: string | null;
        created_at: string;
        updated_at: string;
    };
    workflow?: {
        id: string;
        name: string;
        is_active: boolean;
    } | null;
    contactList?: {
        id: string;
        name: string;
        total_contacts: number;
    } | null;
    progress?: {
        processed: number;
        total: number;
    };
    onToggleActivation: () => void;
    onUpdateDescription: (description: string) => Promise<void>;
    onSendTestEmail: () => void;
    onDuplicate: () => void;
    onExport: () => void;
    onArchive: () => void;
    isActivating?: boolean;
}

export const CampaignHeader: React.FC<CampaignHeaderProps> = ({
    campaign,
    workflow,
    contactList,
    progress,
    onToggleActivation,
    onUpdateDescription,
    onSendTestEmail,
    onDuplicate,
    onExport,
    onArchive,
    isActivating = false
}) => {
    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
        });
    };

    const quickActions = [
        {
            label: 'Send Test Email',
            icon: <Mail className="w-4 h-4" />,
            onClick: onSendTestEmail
        },
        {
            label: 'Duplicate Campaign',
            icon: <Copy className="w-4 h-4" />,
            onClick: onDuplicate
        },
        {
            label: 'Export Data',
            icon: <Download className="w-4 h-4" />,
            onClick: onExport
        },
        {
            label: 'Archive Campaign',
            icon: <Archive className="w-4 h-4" />,
            onClick: onArchive,
            variant: 'danger' as const
        }
    ];

    return (
        <div className="bg-gradient-to-br from-slate-800/40 to-slate-900/40 p-6 rounded-2xl border border-slate-700/30 backdrop-blur-sm shadow-xl">
            {/* Top Row: Back Button, Title, Actions */}
            <div className="flex items-start justify-between gap-4 mb-6">
                <div className="flex items-start gap-4 flex-1">
                    {/* Back Button */}
                    <Link to="/campaigns">
                        <Button variant="outline" size="icon" className="mt-1">
                            <ArrowLeft className="w-4 h-4" />
                        </Button>
                    </Link>

                    {/* Title & Status */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                            <h1 className="text-3xl font-bold text-slate-100 truncate">
                                {campaign.name}
                            </h1>
                            <Badge variant={campaign.is_active ? "success" : "neutral"}>
                                {campaign.is_active ? "Active" : "Paused"}
                            </Badge>
                        </div>

                        {/* Editable Description */}
                        <div className="max-w-2xl">
                            <InlineEdit
                                value={campaign.description || ''}
                                onSave={onUpdateDescription}
                                placeholder="Add campaign description..."
                                multiline
                                displayClassName="text-sm text-slate-400"
                            />
                        </div>
                    </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-2">
                    {!campaign.is_active ? (
                        <Button
                            variant="primary"
                            onClick={onToggleActivation}
                            isLoading={isActivating}
                            disabled={!campaign.contact_list_id || !workflow}
                            title={!campaign.contact_list_id ? "Select a contact list to start" : !workflow ? "Assign a workflow to start" : "Launch campaign"}
                            leftIcon={<Zap className="w-4 h-4" />}
                            className="bg-emerald-600 hover:bg-emerald-500 border-emerald-500/50 shadow-lg shadow-emerald-500/20"
                        >
                            Start Campaign
                        </Button>
                    ) : (
                        <Button
                            variant="secondary"
                            onClick={onToggleActivation}
                            isLoading={isActivating}
                            leftIcon={<AlertCircle className="w-4 h-4" />}
                            className="bg-amber-600/20 text-amber-500 border-amber-500/30 hover:bg-amber-600/30"
                        >
                            Pause Campaign
                        </Button>
                    )}

                    {/* Quick Actions Dropdown */}
                    <DropdownMenu items={quickActions} align="right" />
                </div>
            </div>

            {/* Metadata Row */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* Workflow Info */}
                {workflow ? (
                    <Link
                        to={`/workflows/${workflow.id}`}
                        className="group flex items-center gap-3 p-3 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-indigo-500/50 hover:bg-slate-800/70 transition-all"
                    >
                        <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-500/20 transition-colors">
                            <WorkflowIcon className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-xs text-slate-500 font-medium">Workflow</p>
                            <p className="text-sm font-semibold text-slate-200 truncate group-hover:text-indigo-300 transition-colors">
                                {workflow.name}
                            </p>
                        </div>
                    </Link>
                ) : (
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/30 border border-slate-700/30">
                        <div className="p-2 rounded-lg bg-slate-700/50 text-slate-500">
                            <WorkflowIcon className="w-5 h-5" />
                        </div>
                        <div className="flex-1">
                            <p className="text-xs text-slate-500 font-medium">Workflow</p>
                            <p className="text-sm text-slate-400 italic">No workflow linked</p>
                        </div>
                    </div>
                )}

                {/* Contact List Info */}
                {contactList ? (
                    <Link
                        to={`/contacts?list=${contactList.id}`}
                        className="group flex items-center gap-3 p-3 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-emerald-500/50 hover:bg-slate-800/70 transition-all"
                    >
                        <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20 transition-colors">
                            <Users className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-xs text-slate-500 font-medium">Contact List</p>
                            <p className="text-sm font-semibold text-slate-200 truncate group-hover:text-emerald-300 transition-colors">
                                {contactList.name}
                            </p>
                            <p className="text-xs text-slate-400">
                                {contactList.total_contacts.toLocaleString()} contacts
                            </p>
                        </div>
                    </Link>
                ) : (
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/30 border border-slate-700/30">
                        <div className="p-2 rounded-lg bg-slate-700/50 text-slate-500">
                            <Users className="w-5 h-5" />
                        </div>
                        <div className="flex-1">
                            <p className="text-xs text-slate-500 font-medium">Contact List</p>
                            <p className="text-sm text-slate-400 italic">No list assigned</p>
                        </div>
                    </div>
                )}

                {/* Progress Indicator */}
                {progress && progress.total > 0 ? (
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/50 border border-slate-700/50">
                        <ProgressRing
                            current={progress.processed}
                            total={progress.total}
                            size={48}
                            strokeWidth={4}
                            showLabel={false}
                        />
                        <div className="flex-1">
                            <p className="text-xs text-slate-500 font-medium">Progress</p>
                            <p className="text-sm font-semibold text-slate-200">
                                {progress.processed.toLocaleString()} / {progress.total.toLocaleString()}
                            </p>
                            <p className="text-xs text-slate-400">
                                {Math.round((progress.processed / progress.total) * 100)}% complete
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/30 border border-slate-700/30">
                        <div className="w-12 h-12 rounded-full bg-slate-700/50 flex items-center justify-center">
                            <span className="text-lg font-bold text-slate-500">0%</span>
                        </div>
                        <div className="flex-1">
                            <p className="text-xs text-slate-500 font-medium">Progress</p>
                            <p className="text-sm text-slate-400 italic">Not started</p>
                        </div>
                    </div>
                )}

                {/* Last Updated */}
                <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/50 border border-slate-700/50">
                    <div className="p-2 rounded-lg bg-slate-700/50 text-slate-400">
                        <Clock className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                        <p className="text-xs text-slate-500 font-medium">Last Updated</p>
                        <p className="text-sm font-semibold text-slate-200">
                            {formatDate(campaign.updated_at)}
                        </p>
                        <p className="text-xs text-slate-400">
                            Created {formatDate(campaign.created_at)}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CampaignHeader;
