import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import api from '../lib/api';
import { Save, ArrowLeft, Eye, Code, FileJson, AlertCircle, ShieldAlert, ShieldCheck, Shield } from 'lucide-react';
import { useSpamCheck } from '../hooks/useSpamCheck';
import { toast } from 'sonner';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';

interface Template {
    id: string;
    name: string;
    subject: string;
    html_body: string;
}

const modules = {
    toolbar: [
        [{ 'header': [1, 2, 3, false] }],
        ['bold', 'italic', 'underline', 'strike'],
        [{ 'list': 'ordered' }, { 'list': 'bullet' }],
        ['link', 'clean'],
        ['blockquote', 'code-block']
    ],
};

const TemplateEditor: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const isNew = !id || id === 'new' || id === 'undefined';

    const [name, setName] = useState('');
    const [subject, setSubject] = useState('');
    const [htmlBody, setHtmlBody] = useState('');
    const [testData, setTestData] = useState('{\n  "first_name": "John",\n  "company": "Antigravity"\n}');
    const [renderedHtml, setRenderedHtml] = useState('');
    const [renderError, setRenderError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'edit' | 'preview'>('edit');
    const [activeMode, setActiveMode] = useState<'visual' | 'source'>('visual');
    const [showJsonEditor, setShowJsonEditor] = useState(false);

    // Spam Check
    const { report: subjectSpamReport, isLoading: isSubjectSpamLoading } = useSpamCheck(subject);
    const { report: bodySpamReport, isLoading: isBodySpamLoading } = useSpamCheck(htmlBody);

    // Fetch template if editing
    const { data: template, isLoading } = useQuery({
        queryKey: ['template', id],
        queryFn: async () => {
            if (isNew) return null;
            const response = await api.get<Template>(`/templates/${id}`);
            return response.data;
        },
        enabled: !!id && id !== 'new' && id !== 'undefined'
    });

    // Populate state when template loads
    useEffect(() => {
        if (template) {
            setName(template.name);
            setSubject(template.subject);
            setHtmlBody(template.html_body);
        }
    }, [template]);

    // Save mutation
    const saveMutation = useMutation({
        mutationFn: async () => {
            const data = { name, subject, html_body: htmlBody };
            if (isNew) {
                return api.post('/templates', data);
            } else {
                return api.patch(`/templates/${id}`, data);
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['templates'] });
            toast.success(isNew ? 'Template created successfully!' : 'Template updated successfully!');
            navigate('/templates');
        },
        onError: (error: any) => {
            console.error('Save error:', error);
            const detail = error.response?.data?.detail;
            toast.error(typeof detail === 'string' ? detail : 'Failed to save template');
        }
    });

    // Debounced Preview Rendering
    useEffect(() => {
        const timer = setTimeout(async () => {
            if (!htmlBody) {
                setRenderedHtml('');
                return;
            }
            try {
                let parsedData = {};
                try {
                    parsedData = JSON.parse(testData);
                } catch (e) {
                    // Ignore JSON parse errors for now
                }

                const response = await api.post('/templates/preview', {
                    html_body: htmlBody,
                    test_data: parsedData
                });
                setRenderedHtml(response.data.rendered_html);
                setRenderError(null);
            } catch (err: any) {
                setRenderError(err.response?.data?.detail || 'Rendering error');
            }
        }, 500); // 500ms debounce

        return () => clearTimeout(timer);
    }, [htmlBody, testData]);

    if (isLoading && !isNew) {
        return (
            <Layout title="Template Editor">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 w-1/4 bg-slate-800 rounded"></div>
                    <div className="h-64 bg-slate-800 rounded"></div>
                </div>
            </Layout>
        );
    }

    return (
        <Layout title={isNew ? "New Template" : `Edit Template: ${name}`}>
            <div className="flex flex-col h-full space-y-4">
                {/* Header Actions */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => navigate('/templates')}
                            className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg"
                        >
                            <ArrowLeft className="w-5 h-5" />
                        </button>
                        <h2 className="text-xl font-bold text-slate-200">
                            {isNew ? "Create New Template" : "Template Settings"}
                        </h2>
                    </div>
                    <Button
                        leftIcon={<Save className="w-4 h-4" />}
                        onClick={() => saveMutation.mutate()}
                        isLoading={saveMutation.isPending}
                    >
                        Save Template
                    </Button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-200px)]">
                    {/* Left: Editor Pane */}
                    <div className="flex flex-col space-y-4">
                        <Card className="p-6 space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Template Name</label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="e.g. Welcome Email #1"
                                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Subject Line</label>
                                <input
                                    type="text"
                                    value={subject}
                                    onChange={(e) => setSubject(e.target.value)}
                                    placeholder="Enter subject..."
                                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                                />
                                {subjectSpamReport && (
                                    <div className={`mt-2 p-2 rounded-lg border flex items-start gap-3 transition-colors ${subjectSpamReport.score > 0.6 ? 'bg-red-500/10 border-red-500/30' :
                                        subjectSpamReport.score > 0.3 ? 'bg-yellow-500/10 border-yellow-500/30' :
                                            'bg-emerald-500/10 border-emerald-500/30'
                                        }`}>
                                        <div className="mt-0.5">
                                            {subjectSpamReport.score > 0.6 ? <ShieldAlert className="w-4 h-4 text-red-400" /> :
                                                subjectSpamReport.score > 0.3 ? <Shield className="w-4 h-4 text-yellow-400" /> :
                                                    <ShieldCheck className="w-4 h-4 text-emerald-400" />}
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Spam Risk Score:</span>
                                                <span className={`text-xs font-bold ${subjectSpamReport.score > 0.6 ? 'text-red-400' :
                                                    subjectSpamReport.score > 0.3 ? 'text-yellow-400' :
                                                        'text-emerald-400'
                                                    }`}>
                                                    {Math.round(subjectSpamReport.score * 100)}%
                                                </span>
                                            </div>
                                            {subjectSpamReport.triggers.length > 0 && (
                                                <p className="text-[10px] text-slate-500 mt-0.5 leading-relaxed">
                                                    Triggers found: <span className="text-slate-300">{subjectSpamReport.triggers.join(', ')}</span>
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </Card>

                        <div className="flex-1 flex flex-col relative min-h-0">
                            <div className="flex items-center justify-between mb-2 px-1">
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => setActiveMode('visual')}
                                        className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-widest transition-all ${activeMode === 'visual'
                                            ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20'
                                            : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                                            }`}
                                    >
                                        Visual Editor
                                    </button>
                                    <button
                                        onClick={() => setActiveMode('source')}
                                        className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-widest transition-all ${activeMode === 'source'
                                            ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/20'
                                            : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                                            }`}
                                    >
                                        Source HTML
                                    </button>
                                </div>
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => setShowJsonEditor(!showJsonEditor)}
                                    leftIcon={<FileJson className="w-3 h-3" />}
                                    className="text-[10px] h-7"
                                >
                                    {showJsonEditor ? "Hide Test Data" : "Edit Test Data"}
                                </Button>
                            </div>

                            {showJsonEditor && (
                                <div className="absolute top-10 right-0 z-10 w-64 shadow-2xl">
                                    <Card className="p-4 bg-slate-900 border-indigo-500/30">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase">Test Data (JSON)</span>
                                        </div>
                                        <textarea
                                            value={testData}
                                            onChange={(e) => setTestData(e.target.value)}
                                            className="w-full h-40 bg-slate-950 border border-slate-700 rounded p-2 text-xs font-mono text-emerald-400 focus:ring-1 focus:ring-indigo-500 outline-none"
                                        />
                                    </Card>
                                </div>
                            )}

                            <div className="flex-1 flex flex-col min-h-0 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-inner">
                                {activeMode === 'visual' ? (
                                    <ReactQuill
                                        theme="snow"
                                        value={htmlBody}
                                        onChange={setHtmlBody}
                                        placeholder="Type your email content here... (Use {{variable_name}} for personalization)"
                                        modules={modules}
                                        className="flex-1 flex flex-col h-full quill-dark"
                                    />
                                ) : (
                                    <textarea
                                        value={htmlBody}
                                        onChange={(e) => setHtmlBody(e.target.value)}
                                        placeholder="Write your HTML with {{variables}}..."
                                        className="flex-1 w-full bg-slate-900 border-none p-6 text-sm font-mono text-slate-300 focus:ring-0 outline-none resize-none"
                                    />
                                )}
                            </div>

                            {bodySpamReport && bodySpamReport.score > 0 && (
                                <div className={`mt-2 p-3 rounded-lg border flex items-start gap-3 transition-colors ${bodySpamReport.score > 0.6 ? 'bg-red-500/10 border-red-500/30' :
                                    bodySpamReport.score > 0.3 ? 'bg-yellow-500/10 border-yellow-500/30' :
                                        'bg-emerald-500/10 border-emerald-500/30'
                                    }`}>
                                    <div className="mt-0.5">
                                        {bodySpamReport.score > 0.6 ? <ShieldAlert className="w-4 h-4 text-red-400" /> :
                                            bodySpamReport.score > 0.3 ? <Shield className="w-4 h-4 text-yellow-400" /> :
                                                <ShieldCheck className="w-4 h-4 text-emerald-400" />}
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Content Spam Risk:</span>
                                                <span className={`text-xs font-bold ${bodySpamReport.score > 0.6 ? 'text-red-400' :
                                                    bodySpamReport.score > 0.3 ? 'text-yellow-400' :
                                                        'text-emerald-400'
                                                    }`}>
                                                    {Math.round(bodySpamReport.score * 100)}%
                                                </span>
                                            </div>
                                            {bodySpamReport.is_spam && (
                                                <span className="text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded font-bold uppercase">High Risk</span>
                                            )}
                                        </div>
                                        {bodySpamReport.triggers.length > 0 && (
                                            <p className="text-[10px] text-slate-500 mt-1 leading-relaxed">
                                                Issues: <span className="text-slate-300">{bodySpamReport.triggers.join(', ')}</span>
                                            </p>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Right: Preview Pane */}
                    <div className="flex flex-col">
                        <div className="flex items-center gap-2 mb-2 px-1">
                            <div className="p-1 px-2 rounded-md bg-emerald-500/10 text-emerald-400 text-[10px] font-bold uppercase tracking-widest">
                                Live Preview
                            </div>
                            {renderError && (
                                <div className="flex items-center gap-1.5 text-[10px] text-red-400 font-medium">
                                    <AlertCircle className="w-3 h-3" />
                                    {renderError}
                                </div>
                            )}
                        </div>
                        <div className="flex-1 bg-white rounded-xl overflow-hidden shadow-2xl border border-slate-800">
                            {renderedHtml ? (
                                <iframe
                                    srcDoc={renderedHtml}
                                    title="Preview"
                                    className="w-full h-full border-none"
                                />
                            ) : (
                                <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 bg-slate-950">
                                    <Eye className="w-12 h-12 mb-4 opacity-20" />
                                    <p className="text-sm">Start typing to see live preview...</p>
                                    <p className="text-xs mt-2 opacity-50">Liquid syntax supported: {"{{ first_name }}"}</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default TemplateEditor;
