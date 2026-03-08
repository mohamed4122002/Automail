import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import api from '../lib/api';
import { Mail, Globe, Workflow, Save, Eye, EyeOff, Target, Link, Check, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

type TabType = 'email' | 'email_limits' | 'system' | 'workflow' | 'crm' | 'integrations';

// Provider-specific form fields component
const ProviderFields: React.FC<{
    provider: string;
    settings: any;
    showSecrets: boolean;
    toggleSecrets: () => void;
}> = ({ provider, settings, showSecrets, toggleSecrets }) => {
    if (provider === 'smtp') {
        return (
            <div className="space-y-4 p-4 bg-slate-900/50 rounded-lg border border-slate-800">
                <h4 className="text-sm font-semibold text-slate-300">SMTP Configuration</h4>
                <p className="text-xs text-slate-500">Leave empty to use default Gmail SMTP settings</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">SMTP Host</label>
                        <input
                            type="text"
                            name="smtp_host"
                            defaultValue={settings?.smtp_host || ''}
                            placeholder="smtp.gmail.com (default)"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">SMTP Port</label>
                        <input
                            type="number"
                            name="smtp_port"
                            defaultValue={settings?.smtp_port || ''}
                            placeholder="587 (default)"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Username</label>
                        <input
                            type="text"
                            name="smtp_username"
                            defaultValue={settings?.smtp_username || ''}
                            placeholder="happymr412@gmail.com (default)"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Password / App Password</label>
                        <div className="relative">
                            <input
                                type={showSecrets ? 'text' : 'password'}
                                name="smtp_password"
                                defaultValue={settings?.smtp_password || ''}
                                placeholder="••••••••••••••••"
                                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 pr-10 text-slate-200 placeholder:text-slate-600"
                            />
                            <button
                                type="button"
                                onClick={toggleSecrets}
                                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                            >
                                {showSecrets ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">For Gmail, use an App Password. Default is pre-configured.</p>
                    </div>
                    <div className="md:col-span-2">
                        <label className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                name="use_tls"
                                defaultChecked={settings?.use_tls !== false}
                                className="w-4 h-4 bg-slate-900 border-slate-700 rounded"
                            />
                            <span className="text-sm text-slate-300">Use TLS Encryption (Recommended)</span>
                        </label>
                    </div>
                </div>
            </div>
        );
    }

    if (provider === 'sendgrid') {
        return (
            <div className="space-y-4 p-4 bg-slate-900/50 rounded-lg border border-slate-800">
                <h4 className="text-sm font-semibold text-slate-300">SendGrid Configuration</h4>
                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">API Key</label>
                    <div className="relative">
                        <input
                            type={showSecrets ? 'text' : 'password'}
                            name="api_key"
                            defaultValue={settings?.api_key || ''}
                            placeholder="SG...."
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 pr-10 text-slate-200"
                            required
                        />
                        <button
                            type="button"
                            onClick={toggleSecrets}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                        >
                            {showSecrets ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    if (provider === 'ses') {
        return (
            <div className="space-y-4 p-4 bg-slate-900/50 rounded-lg border border-slate-800">
                <h4 className="text-sm font-semibold text-slate-300">AWS SES Configuration</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">AWS Access Key</label>
                        <input
                            type="text"
                            name="aws_access_key"
                            defaultValue={settings?.aws_access_key || ''}
                            placeholder="AKIA..."
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">AWS Secret Key</label>
                        <div className="relative">
                            <input
                                type={showSecrets ? 'text' : 'password'}
                                name="aws_secret_key"
                                defaultValue={settings?.aws_secret_key || ''}
                                placeholder="••••••••••••••••"
                                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 pr-10 text-slate-200"
                                required
                            />
                            <button
                                type="button"
                                onClick={toggleSecrets}
                                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                            >
                                {showSecrets ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">AWS Region</label>
                        <select
                            name="aws_region"
                            defaultValue={settings?.aws_region || 'us-east-1'}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                        >
                            <option value="us-east-1">US East (N. Virginia)</option>
                            <option value="us-west-2">US West (Oregon)</option>
                            <option value="eu-west-1">EU (Ireland)</option>
                            <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
                        </select>
                    </div>
                </div>
            </div>
        );
    }

    return null;
};

const Settings: React.FC = () => {
    const [activeTab, setActiveTab] = useState<TabType>('email');
    const [showSecrets, setShowSecrets] = useState(false);
    const queryClient = useQueryClient();

    // Fetch settings
    const { data: emailSettings } = useQuery({
        queryKey: ['settings', 'email_provider'],
        queryFn: async () => {
            try {
                const res = await api.get('/settings/email_provider');
                return res.data.value;
            } catch {
                return null;
            }
        }
    });

    const { data: systemPrefs } = useQuery({
        queryKey: ['settings', 'system_preferences'],
        queryFn: async () => {
            try {
                const res = await api.get('/settings/system_preferences');
                return res.data.value;
            } catch {
                return { timezone: 'UTC', date_format: 'YYYY-MM-DD', language: 'en', enable_notifications: true };
            }
        }
    });

    const { data: workflowPrefs } = useQuery({
        queryKey: ['settings', 'workflow_preferences'],
        queryFn: async () => {
            try {
                const res = await api.get('/settings/workflow_preferences');
                return res.data.value;
            } catch {
                return { default_delay_hours: 24, max_retry_attempts: 3, execution_start_hour: 9, execution_end_hour: 17 };
            }
        }
    });

    const { data: crmPrefs } = useQuery({
        queryKey: ['settings', 'crm_preferences'],
        queryFn: async () => {
            try {
                const res = await api.get('/settings/crm_preferences');
                return res.data.value;
            } catch {
                return { inactivity_threshold_days: 3, enable_inactivity_alerts: true };
            }
        }
    });

    const { data: integrationStatus, refetch: refetchIntegrations } = useQuery({
        queryKey: ['settings', 'integrations_status'],
        queryFn: async () => {
            try {
                const res = await api.get('/integrations/status');
                return res.data;
            } catch {
                return { google_calendar: { connected: false } };
            }
        }
    });

    // Mutations
    const [testStatus, setTestStatus] = useState<string>('');

    const emailMutation = useMutation({
        mutationFn: (data: any) => api.post('/settings/email-provider', data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['settings', 'email_provider'] });
            toast.success('Email settings saved successfully!');
        }
    });

    const testConnectionMutation = useMutation({
        mutationFn: async (config: any) => {
            const response = await api.post('/settings/email-provider/test-config', config);
            return response.data;
        },
        onSuccess: (data) => {
            setTestStatus(data.status === 'success' ? `✓ ${data.message}` : `✗ ${data.message}`);
        },
        onError: (error: any) => {
            setTestStatus(`✗ Test failed: ${error.response?.data?.detail || error.message}`);
        }
    });

    const systemMutation = useMutation({
        mutationFn: (data: any) => api.post('/settings/system-preferences', data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['settings', 'system_preferences'] });
            toast.success('System preferences saved!');
        }
    });

    const workflowMutation = useMutation({
        mutationFn: (data: any) => api.post('/settings/workflow-preferences', data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['settings', 'workflow_preferences'] });
            toast.success('Workflow preferences saved!');
        }
    });

    const crmMutation = useMutation({
        mutationFn: (data: any) => api.post('/settings/crm-preferences', data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['settings', 'crm_preferences'] });
            toast.success('CRM preferences saved!');
        }
    });

    const handleEmailSubmit = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);
        const provider = formData.get('provider') as string;

        const data: any = {
            provider,
            from_email: formData.get('from_email') || 'happymr412@gmail.com',
            from_name: formData.get('from_name') || 'Marketing System',
        };

        // Add provider-specific fields with defaults
        if (provider === 'smtp') {
            data.smtp_host = formData.get('smtp_host') || 'smtp.gmail.com';
            data.smtp_port = formData.get('smtp_port') ? parseInt(formData.get('smtp_port') as string) : 587;
            data.smtp_username = formData.get('smtp_username') || 'happymr412@gmail.com';
            data.smtp_password = formData.get('smtp_password') || 'refhqkqekxxuiuci';
            data.use_tls = formData.get('use_tls') === 'on' || true;
        } else if (provider === 'sendgrid') {
            data.api_key = formData.get('api_key');
        } else if (provider === 'ses') {
            data.aws_access_key = formData.get('aws_access_key');
            data.aws_secret_key = formData.get('aws_secret_key');
            data.aws_region = formData.get('aws_region') || 'us-east-1';
        }

        emailMutation.mutate(data);
    };

    const handleSystemSubmit = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);
        const data = {
            timezone: formData.get('timezone'),
            date_format: formData.get('date_format'),
            language: formData.get('language'),
            enable_notifications: formData.get('enable_notifications') === 'on',
        };
        systemMutation.mutate(data);
    };

    const handleWorkflowSubmit = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);
        const data = {
            default_delay_hours: parseInt(formData.get('default_delay_hours') as string),
            max_retry_attempts: parseInt(formData.get('max_retry_attempts') as string),
            execution_start_hour: parseInt(formData.get('execution_start_hour') as string),
            execution_end_hour: parseInt(formData.get('execution_end_hour') as string),
        };
        workflowMutation.mutate(data);
    };

    const handleCrmSubmit = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);
        const data = {
            inactivity_threshold_days: parseInt(formData.get('inactivity_threshold_days') as string),
            enable_inactivity_alerts: formData.get('enable_inactivity_alerts') === 'on',
        };
        crmMutation.mutate(data);
    };

    const handleGoogleAuth = async () => {
        try {
            const redirectUri = `${window.location.host}/settings?tab=integrations`;
            const res = await api.get(`/integrations/google/auth?redirect_uri=${encodeURIComponent(redirectUri)}`);
            window.location.href = res.data.auth_url;
        } catch (error: any) {
            toast.error('Failed to start Google authentication');
        }
    };

    const handleDisconnectGoogle = async () => {
        try {
            await api.delete('/integrations/google');
            refetchIntegrations();
            toast.success('Google Calendar disconnected');
        } catch (error: any) {
            toast.error('Failed to disconnect');
        }
    };

    // Check for callback code in URL
    React.useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        if (code && activeTab === 'integrations') {
            const redirectUri = `${window.location.host}/settings?tab=integrations`;
            api.get(`/integrations/google/callback?code=${code}&redirect_uri=${encodeURIComponent(redirectUri)}`)
                .then(() => {
                    toast.success('Google Calendar connected!');
                    refetchIntegrations();
                    // Clean URL
                    window.history.replaceState({}, '', window.location.pathname + '?tab=integrations');
                })
                .catch(() => {
                    toast.error('Failed to complete Google connection');
                });
        }
    }, [activeTab]);

    const tabs = [
        { id: 'email' as TabType, label: 'Email Provider', icon: Mail },
        { id: 'system' as TabType, label: 'System', icon: Globe },
        { id: 'workflow' as TabType, label: 'Workflows', icon: Workflow },
        { id: 'crm' as TabType, label: 'CRM', icon: Target },
        { id: 'integrations' as TabType, label: 'Integrations', icon: Link },
    ];

    return (
        <Layout title="Settings" >
            <div className="flex flex-col gap-6">
                {/* Tabs */}
                <div className="flex gap-2 border-b border-slate-800">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors border-b-2 ${activeTab === tab.id
                                ? 'border-indigo-500 text-indigo-400'
                                : 'border-transparent text-slate-400 hover:text-slate-200'
                                }`}
                        >
                            <tab.icon className="w-4 h-4" />
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Email Provider Tab */}
                {activeTab === 'email' && (
                    <Card>
                        <form onSubmit={handleEmailSubmit} className="p-6 space-y-6">
                            <div>
                                <h3 className="text-lg font-semibold text-slate-200 mb-4">Email Provider Configuration</h3>
                                <p className="text-sm text-slate-400 mb-6">Configure your email sending service</p>

                                {/* Current Configuration Status */}
                                <div className="mb-6 p-4 bg-slate-900/50 rounded-lg border border-slate-800">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-sm font-medium text-slate-300">Current Provider</p>
                                            <p className="text-xs text-slate-500 mt-1">
                                                {emailSettings?.provider === 'smtp' && 'SMTP (Gmail, Outlook, etc.)'}
                                                {emailSettings?.provider === 'sendgrid' && 'SendGrid'}
                                                {emailSettings?.provider === 'ses' && 'AWS SES'}
                                                {!emailSettings?.provider && 'Using default SMTP configuration'}
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                                            <span className="text-xs text-emerald-400">Active</span>
                                        </div>
                                    </div>
                                    {emailSettings?.from_email && (
                                        <div className="mt-3 pt-3 border-t border-slate-800">
                                            <p className="text-xs text-slate-500">Sending from: <span className="text-slate-300">{emailSettings.from_email}</span></p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="space-y-4">
                                {/* Provider Selection */}
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Provider</label>
                                    <select
                                        name="provider"
                                        defaultValue={emailSettings?.provider || 'smtp'}
                                        onChange={(e) => {
                                            // Reset form when provider changes
                                            setTestStatus('');
                                        }}
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                                    >
                                        <option value="smtp">SMTP (Gmail, Outlook, etc.)</option>
                                        <option value="sendgrid">SendGrid</option>
                                        <option value="ses">AWS SES</option>
                                    </select>
                                    <p className="text-xs text-slate-500 mt-1">Leave fields empty to use default configuration</p>
                                </div>

                                {/* Common Fields */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-300 mb-2">From Email</label>
                                        <input
                                            type="email"
                                            name="from_email"
                                            defaultValue={emailSettings?.from_email || ''}
                                            placeholder="happymr412@gmail.com (default)"
                                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-slate-300 mb-2">From Name</label>
                                        <input
                                            type="text"
                                            name="from_name"
                                            defaultValue={emailSettings?.from_name || ''}
                                            placeholder="Marketing System (default)"
                                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600"
                                        />
                                    </div>
                                </div>

                                {/* Provider-Specific Fields */}
                                <ProviderFields
                                    provider={emailSettings?.provider || 'smtp'}
                                    settings={emailSettings}
                                    showSecrets={showSecrets}
                                    toggleSecrets={() => setShowSecrets(!showSecrets)}
                                />
                            </div>

                            {/* Test Connection Status */}
                            {testStatus && (
                                <div className={`p-3 rounded-lg ${testStatus.startsWith('✓')
                                    ? 'bg-emerald-500/10 text-emerald-400'
                                    : testStatus.startsWith('✗')
                                        ? 'bg-red-500/10 text-red-400'
                                        : 'bg-blue-500/10 text-blue-400'
                                    }`}>
                                    {testStatus}
                                </div>
                            )}

                            <div className="pt-4 border-t border-slate-800 flex gap-3">
                                <Button
                                    type="button"
                                    variant="secondary"
                                    onClick={() => {
                                        setTestStatus('Testing...');
                                        const formEl = document.querySelector('form') as HTMLFormElement;
                                        const formData = new FormData(formEl);
                                        const provider = formData.get('provider') as string;

                                        const config: any = {
                                            provider,
                                            from_email: formData.get('from_email') || 'happymr412@gmail.com',
                                            from_name: formData.get('from_name') || 'Marketing System',
                                        };

                                        if (provider === 'smtp') {
                                            config.smtp_host = formData.get('smtp_host') || 'smtp.gmail.com';
                                            config.smtp_port = formData.get('smtp_port') ? parseInt(formData.get('smtp_port') as string) : 587;
                                            config.smtp_username = formData.get('smtp_username') || 'happymr412@gmail.com';
                                            config.smtp_password = formData.get('smtp_password') || 'refhqkqekxxuiuci';
                                            config.use_tls = formData.get('use_tls') === 'on' || true;
                                        } else if (provider === 'sendgrid') {
                                            config.api_key = formData.get('api_key');
                                        } else if (provider === 'ses') {
                                            config.aws_access_key = formData.get('aws_access_key');
                                            config.aws_secret_key = formData.get('aws_secret_key');
                                            config.aws_region = formData.get('aws_region');
                                        }

                                        testConnectionMutation.mutate(config);
                                    }}
                                    disabled={testConnectionMutation.isPending}
                                    className="flex-1"
                                >
                                    {testConnectionMutation.isPending ? 'Testing...' : 'Test Connection'}
                                </Button>
                                <Button type="submit" leftIcon={<Save className="w-4 h-4" />} className="flex-1">
                                    Save Email Settings
                                </Button>
                            </div>
                        </form>
                    </Card>
                )}

                {/* System Preferences Tab */}
                {activeTab === 'system' && (
                    <Card>
                        <form onSubmit={handleSystemSubmit} className="p-6 space-y-6">
                            <div>
                                <h3 className="text-lg font-semibold text-slate-200 mb-4">System Preferences</h3>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Timezone</label>
                                    <select
                                        name="timezone"
                                        defaultValue={systemPrefs?.timezone || 'UTC'}
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                                    >
                                        <option value="UTC">UTC</option>
                                        <option value="America/New_York">Eastern Time</option>
                                        <option value="America/Los_Angeles">Pacific Time</option>
                                        <option value="Europe/London">London</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Date Format</label>
                                    <select
                                        name="date_format"
                                        defaultValue={systemPrefs?.date_format || 'YYYY-MM-DD'}
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                                    >
                                        <option value="YYYY-MM-DD">2024-01-31</option>
                                        <option value="MM/DD/YYYY">01/31/2024</option>
                                        <option value="DD/MM/YYYY">31/01/2024</option>
                                    </select>
                                </div>

                                <div className="md:col-span-2">
                                    <label className="flex items-center gap-2">
                                        <input
                                            type="checkbox"
                                            name="enable_notifications"
                                            defaultChecked={systemPrefs?.enable_notifications !== false}
                                            className="w-4 h-4 bg-slate-900 border-slate-700 rounded"
                                        />
                                        <span className="text-sm text-slate-300">Enable email notifications for system events</span>
                                    </label>
                                </div>
                            </div>

                            <div className="pt-4 border-t border-slate-800">
                                <Button type="submit" leftIcon={<Save className="w-4 h-4" />}>
                                    Save System Preferences
                                </Button>
                            </div>
                        </form>
                    </Card>
                )}

                {/* Workflow Preferences Tab */}
                {activeTab === 'workflow' && (
                    <Card>
                        <form onSubmit={handleWorkflowSubmit} className="p-6 space-y-6">
                            <div>
                                <h3 className="text-lg font-semibold text-slate-200 mb-4">Workflow Execution Settings</h3>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Default Delay (hours)</label>
                                    <input
                                        type="number"
                                        name="default_delay_hours"
                                        defaultValue={workflowPrefs?.default_delay_hours || 24}
                                        min="1"
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Max Retry Attempts</label>
                                    <input
                                        type="number"
                                        name="max_retry_attempts"
                                        defaultValue={workflowPrefs?.max_retry_attempts || 3}
                                        min="0"
                                        max="10"
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Execution Start Hour</label>
                                    <input
                                        type="number"
                                        name="execution_start_hour"
                                        defaultValue={workflowPrefs?.execution_start_hour || 9}
                                        min="0"
                                        max="23"
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                                    />
                                    <p className="text-xs text-slate-500 mt-1">Business hours start (24h format)</p>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Execution End Hour</label>
                                    <input
                                        type="number"
                                        name="execution_end_hour"
                                        defaultValue={workflowPrefs?.execution_end_hour || 17}
                                        min="0"
                                        max="23"
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                                    />
                                    <p className="text-xs text-slate-500 mt-1">Business hours end (24h format)</p>
                                </div>
                            </div>

                            <div className="pt-4 border-t border-slate-800">
                                <Button type="submit" leftIcon={<Save className="w-4 h-4" />}>
                                    Save Workflow Preferences
                                </Button>
                            </div>
                        </form>
                    </Card>
                )}
                {/* CRM Preferences Tab */}
                {activeTab === 'crm' && (
                    <Card>
                        <form onSubmit={handleCrmSubmit} className="p-6 space-y-6">
                            <div>
                                <h3 className="text-lg font-semibold text-slate-200 mb-4">CRM & Pipeline Automation</h3>
                                <p className="text-sm text-slate-400 mb-6">Configure inactivity alerts and automated pipeline management</p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Inactivity Threshold (days)</label>
                                    <input
                                        type="number"
                                        name="inactivity_threshold_days"
                                        defaultValue={crmPrefs?.inactivity_threshold_days || 3}
                                        min="1"
                                        max="30"
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                                    />
                                    <p className="text-xs text-slate-500 mt-1">Number of days without activity before alerting the lead owner</p>
                                </div>

                                <div className="md:col-span-2">
                                    <label className="flex items-center gap-2">
                                        <input
                                            type="checkbox"
                                            name="enable_inactivity_alerts"
                                            defaultChecked={crmPrefs?.enable_inactivity_alerts !== false}
                                            className="w-4 h-4 bg-slate-900 border-slate-700 rounded"
                                        />
                                        <span className="text-sm text-slate-300">Enable in-app alerts for inactive leads</span>
                                    </label>
                                </div>
                            </div>

                            <div className="pt-4 border-t border-slate-800">
                                <Button type="submit" leftIcon={<Save className="w-4 h-4" />}>
                                    Save CRM Preferences
                                </Button>
                            </div>
                        </form>
                    </Card>
                )}

                {activeTab === 'integrations' && (
                    <Card className="p-6 bg-slate-800/50 border-slate-700">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="p-2 bg-indigo-500/10 rounded-lg">
                                <Link className="w-5 h-5 text-indigo-400" />
                            </div>
                            <div>
                                <h3 className="text-lg font-semibold text-slate-100">External Integrations</h3>
                                <p className="text-sm text-slate-400">Connect external tools to your CRM workflow</p>
                            </div>
                        </div>

                        <div className="space-y-6">
                            {/* Google Calendar */}
                            <div className="flex flex-col md:flex-row md:items-center justify-between p-4 bg-slate-900/50 rounded-lg border border-slate-800 gap-4">
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center">
                                        <Globe className="w-6 h-6 text-blue-600" />
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-slate-100">Google Calendar</h4>
                                        <p className="text-xs text-slate-500">Sync meetings and book calls directly from leads</p>
                                    </div>
                                </div>
                                <div>
                                    {integrationStatus?.google_calendar?.connected ? (
                                        <div className="flex items-center gap-3">
                                            <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded-full border border-emerald-400/20">
                                                <Check className="w-3 h-3" /> Connected
                                            </span>
                                            <Button variant="outline" size="sm" onClick={handleDisconnectGoogle}>
                                                Disconnect
                                            </Button>
                                        </div>
                                    ) : (
                                        <Button variant="primary" size="sm" onClick={handleGoogleAuth}>
                                            Connect Calendar
                                        </Button>
                                    )}
                                </div>
                            </div>

                            {/* Inbound Forms */}
                            <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-800">
                                <div className="flex items-center gap-4 mb-4">
                                    <div className="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center">
                                        <ExternalLink className="w-6 h-6 text-indigo-400" />
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-slate-100">Inbound Webhooks (Forms)</h4>
                                        <p className="text-xs text-slate-500">Capture leads from external websites and landing pages</p>
                                    </div>
                                </div>
                                <div className="space-y-3">
                                    <div>
                                        <label className="block text-[10px] font-medium text-slate-500 uppercase mb-1">Webhook URL</label>
                                        <div className="flex gap-2">
                                            <input
                                                readOnly
                                                value={`${window.location.origin}/api/inbound/form`}
                                                className="flex-1 bg-slate-950 border border-slate-800 rounded-md px-3 py-1.5 text-xs text-slate-400 font-mono"
                                            />
                                            <Button size="sm" variant="outline" onClick={() => {
                                                navigator.clipboard.writeText(`${window.location.origin}/api/inbound/form`);
                                                toast.success('URL copied to clipboard');
                                            }}>Copy</Button>
                                        </div>
                                    </div>
                                    <div className="p-3 bg-amber-500/5 border border-amber-500/10 rounded-md">
                                        <p className="text-[10px] text-amber-500/80 leading-relaxed">
                                            Send a JSON POST request with fields: <code>email</code>, <code>first_name</code>, <code>last_name</code>, <code>company</code>, <code>message</code>.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </Card>
                )}
            </div>
        </Layout >
    );
};

export default Settings;
