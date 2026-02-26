import React, { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import api from '../../lib/api';
import {
    Upload, FileText, Check, AlertCircle, Loader2,
    ArrowRight, Tag, Info, List, Trash2, Zap,
    Mail, User, Sparkles, Table2, PlusCircle
} from 'lucide-react';

interface ImportWizardProps {
    onComplete?: () => void;
}

const SYSTEM_FIELDS = [
    { key: "Email", label: "Email Address", required: true, icon: Mail },
    { key: "First Name", label: "First Name", required: false, icon: User },
    { key: "Last Name", label: "Last Name", required: false, icon: User }
];

export const ImportWizard: React.FC<ImportWizardProps> = ({ onComplete }) => {
    const [step, setStep] = useState(1);
    const [file, setFile] = useState<File | null>(null);
    const [fileId, setFileId] = useState<string | null>(null);
    const [headers, setHeaders] = useState<string[]>([]);
    const [sample, setSample] = useState<any[]>([]);
    const [mapping, setMapping] = useState<Record<string, string>>({});
    const [selectedListId, setSelectedListId] = useState<string>('');
    const [taskId, setTaskId] = useState<string | null>(null);
    const [status, setStatus] = useState<string>('');
    const [progress, setProgress] = useState(0);
    const [stats, setStats] = useState({ imported: 0, skipped: 0, duplicates: 0 });
    const [error, setError] = useState<string>('');
    const [showNewListModal, setShowNewListModal] = useState(false);
    const [newListName, setNewListName] = useState('');

    const queryClient = useQueryClient();

    const { data: contactLists } = useQuery({
        queryKey: ['contact-lists'],
        queryFn: async () => {
            const response = await api.get('/contacts/lists');
            return response.data;
        }
    });

    const uploadMutation = useMutation({
        mutationFn: async (uploadFile: File) => {
            const formData = new FormData();
            formData.append('file', uploadFile);
            const response = await api.post('/contacts/import/headers', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            return response.data;
        },
        onSuccess: (data) => {
            setFileId(data.file_id);
            setHeaders(data.headers);
            setSample(data.sample);

            const initialMapping: Record<string, string> = {};
            SYSTEM_FIELDS.forEach(field => {
                const match = data.headers.find((h: string) =>
                    h.toLowerCase().includes(field.key.toLowerCase().replace(" ", "")) ||
                    field.key.toLowerCase().includes(h.toLowerCase()) ||
                    h.toLowerCase() === field.label.toLowerCase()
                );
                if (match) {
                    initialMapping[field.key] = match;
                }
            });
            setMapping(initialMapping);
            setStep(2);
        }
    });

    const startImportMutation = useMutation({
        mutationFn: async () => {
            const response = await api.post('/contacts/import/confirm', {
                contact_list_id: selectedListId,
                file_id: fileId,
                mapping,
                skip_invalid: true,
                skip_duplicates: true
            });
            return response.data;
        },
        onSuccess: (data) => {
            setTaskId(data.task_id);
            setStep(3);
        }
    });

    const createListMutation = useMutation({
        mutationFn: async (name: string) => {
            const response = await api.post('/contacts/lists', { name });
            return response.data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['contact-lists'] });
            setSelectedListId(data.id);
            setShowNewListModal(false);
            setNewListName('');
        }
    });

    useEffect(() => {
        let interval: any;
        if (taskId && step === 3) {
            interval = setInterval(async () => {
                try {
                    const response = await api.get(`/contacts/import/status/${taskId}`);
                    const data = response.data;
                    if (data.progress !== undefined) setProgress(data.progress);
                    if (data.status) setStatus(data.status);
                    setStats({
                        imported: data.imported || 0,
                        skipped: data.skipped || 0,
                        duplicates: data.duplicates || 0
                    });

                    if (data.status === 'completed') {
                        clearInterval(interval);
                        setTimeout(() => onComplete?.(), 2500);
                    } else if (data.status === 'failed') {
                        setError(data.error || 'Unknown error occurred during import.');
                        clearInterval(interval);
                    }
                } catch (err) {
                    console.error("Polling error:", err);
                }
            }, 1000);
        }
        return () => clearInterval(interval);
    }, [taskId, step, onComplete]);

    const handleFileDrop = (e: React.DragEvent) => {
        e.preventDefault();
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile?.name.endsWith('.csv')) {
            setFile(droppedFile);
            uploadMutation.mutate(droppedFile);
        }
    };

    return (
        <Card className="max-w-4xl mx-auto overflow-hidden bg-slate-900/40 border-slate-800/60 backdrop-blur-xl">
            <div className="flex border-b border-white/5 bg-slate-950/20">
                {[1, 2, 3].map((s) => (
                    <div
                        key={s}
                        className={`flex-1 px-6 py-5 flex items-center justify-center gap-3 text-sm font-semibold transition-all ${step === s ? 'text-indigo-400 bg-indigo-500/5 border-b-2 border-indigo-500 shadow-[inset_0_-10px_20px_-15px_rgba(99,102,241,0.3)]' : 'text-slate-500'
                            }`}
                    >
                        <span className={`w-7 h-7 rounded-full flex items-center justify-center border-2 text-[10px] sm:text-xs tracking-tighter transition-all ${step === s ? 'border-indigo-500/50 bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 scale-110' : 'border-slate-800 text-slate-600'
                            }`}>
                            {step > s ? <Check className="w-4 h-4" /> : s}
                        </span>
                        <span className="hidden sm:inline">
                            {s === 1 && "Upload CSV"}
                            {s === 2 && "Map Columns"}
                            {s === 3 && "Processing"}
                        </span>
                    </div>
                ))}
            </div>

            <div className="p-8">
                {step === 1 && (
                    <div className="space-y-6">
                        <div
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={handleFileDrop}
                            className="group relative border-2 border-dashed border-slate-800 rounded-3xl p-16 flex flex-col items-center justify-center gap-6 hover:border-indigo-500/50 hover:bg-indigo-500/5 transition-all duration-500 cursor-pointer overflow-hidden"
                            onClick={() => document.getElementById('csv-upload')?.click()}
                        >
                            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-transparent to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                            <div className="w-20 h-20 rounded-2xl bg-slate-800/50 group-hover:bg-indigo-500/10 flex items-center justify-center group-hover:rotate-6 transition-all duration-500">
                                <Upload className="w-10 h-10 text-slate-500 group-hover:text-indigo-400" />
                            </div>
                            <div className="text-center relative z-10">
                                <p className="text-xl font-bold text-slate-200">Select Contact Database</p>
                                <p className="text-slate-500 text-sm mt-2 max-w-xs">Upload your CSV file to begin our high-performance mapping process.</p>
                            </div>
                            <input
                                type="file"
                                accept=".csv"
                                className="hidden"
                                id="csv-upload"
                                onChange={(e) => {
                                    const f = e.target.files?.[0];
                                    if (f) {
                                        setFile(f);
                                        uploadMutation.mutate(f);
                                    }
                                }}
                            />
                            <Button variant="secondary" className="px-8 rounded-full border-slate-700 bg-slate-800/50">
                                Browse Files
                            </Button>
                        </div>
                        {uploadMutation.isPending && (
                            <div className="flex flex-col items-center justify-center gap-3 text-indigo-400 py-4">
                                <Loader2 className="w-6 h-6 animate-spin" />
                                <span className="text-sm font-medium tracking-wide animate-pulse uppercase">Analyzing Structure...</span>
                            </div>
                        )}
                    </div>
                )}

                {step === 2 && (
                    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <div className="flex flex-col lg:flex-row items-start justify-between gap-8">
                            <div className="flex-1">
                                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-bold uppercase tracking-widest mb-4">
                                    <Sparkles className="w-3 h-3" /> Smart Mapping Active
                                </div>
                                <h4 className="text-3xl font-black text-slate-100 italic tracking-tight leading-none">Configure Import</h4>
                                <p className="text-slate-500 text-sm mt-3 font-medium">Map your CSV columns to system fields for optimal sync.</p>
                            </div>
                            <div className="w-full lg:w-96 space-y-3">
                                <div className="flex items-center justify-between px-1">
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Audience Destination</label>
                                    <button
                                        onClick={() => setShowNewListModal(true)}
                                        className="text-[10px] text-indigo-400 hover:text-indigo-300 font-black flex items-center gap-1.5 transition-colors"
                                    >
                                        <PlusCircle className="w-3.5 h-3.5" /> NEW LIST
                                    </button>
                                </div>
                                <select
                                    value={selectedListId}
                                    onChange={(e) => setSelectedListId(e.target.value)}
                                    className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all shadow-2xl appearance-none font-semibold"
                                >
                                    <option value="">Choose global destination...</option>
                                    {contactLists?.map((l: any) => (
                                        <option key={l.id} value={l.id}>{l.name}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                            <div className="space-y-5">
                                <div className="flex items-center justify-between px-1">
                                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                        <Mail className="w-3 h-3" /> Core Identity Fields
                                    </span>
                                </div>
                                <div className="space-y-3">
                                    {SYSTEM_FIELDS.map(field => {
                                        const isMapped = !!mapping[field.key];
                                        return (
                                            <div key={field.key} className={`group p-5 rounded-3xl bg-slate-900/40 border-2 transition-all duration-500 ${isMapped ? 'border-indigo-500/30 bg-indigo-500/5' : 'border-slate-800/40'}`}>
                                                <div className="flex items-center justify-between gap-4">
                                                    <div className="flex items-center gap-4">
                                                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-500 ${isMapped ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'bg-slate-800 text-slate-500'}`}>
                                                            <field.icon className="w-6 h-6" />
                                                        </div>
                                                        <div>
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-base font-bold text-slate-100 tracking-tight">{field.label}</span>
                                                                {field.required && <span className="text-red-500 font-black">*</span>}
                                                            </div>
                                                            <span className="text-xs text-slate-500 font-medium">{isMapped ? `Mapped to ${mapping[field.key]}` : 'Required'}</span>
                                                        </div>
                                                    </div>
                                                    <select
                                                        value={mapping[field.key] || ""}
                                                        onChange={(e) => setMapping({ ...mapping, [field.key]: e.target.value })}
                                                        className="bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-300 focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-bold"
                                                    >
                                                        <option value="">Select column</option>
                                                        {headers.map(h => (
                                                            <option key={h} value={h}>{h}</option>
                                                        ))}
                                                    </select>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="space-y-5">
                                <div className="flex items-center justify-between px-1">
                                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                        <Tag className="w-3 h-3" /> Extended Metadata
                                    </span>
                                    <button
                                        className="text-[10px] font-black text-indigo-400 hover:text-indigo-300 transition-colors uppercase"
                                        onClick={() => {
                                            const newMapping = { ...mapping };
                                            headers.forEach(h => {
                                                if (!Object.values(mapping).includes(h)) newMapping[h] = h;
                                            });
                                            setMapping(newMapping);
                                        }}
                                    >Map All Remaining</button>
                                </div>
                                <div className="bg-slate-950/40 border-2 border-slate-800/40 rounded-3xl p-3 max-h-[400px] overflow-y-auto space-y-2 scrollbar-hide">
                                    {headers.map(h => {
                                        const isSystemMapped = Object.keys(mapping).some(k => SYSTEM_FIELDS.some(sf => sf.key === k) && mapping[k] === h);
                                        if (isSystemMapped) return null;
                                        const isMapped = !!mapping[h];
                                        return (
                                            <div key={h} className={`item flex items-center justify-between p-4 rounded-2xl border transition-all duration-300 ${isMapped ? 'bg-slate-800/30 border-indigo-500/20' : 'bg-transparent border-slate-800/40'}`}>
                                                <div className="flex items-center gap-3">
                                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${isMapped ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-900 text-slate-600'}`}>
                                                        <Table2 className="w-4 h-4" />
                                                    </div>
                                                    <span className="text-xs font-bold text-slate-400">{h}</span>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <ArrowRight className={`w-3 h-3 transition-colors ${isMapped ? 'text-indigo-500' : 'text-slate-700'}`} />
                                                    <select
                                                        value={mapping[h] || ""}
                                                        onChange={(e) => setMapping({ ...mapping, [h]: e.target.value })}
                                                        className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-2 text-[10px] text-slate-400 font-black focus:ring-2 focus:ring-indigo-500 outline-none"
                                                    >
                                                        <option value="">Skip</option>
                                                        <option value={h}>Import as {h}</option>
                                                    </select>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>

                        <div className="flex flex-col sm:flex-row items-center justify-between gap-6 pt-10 border-t border-slate-800/60">
                            <div className="flex items-center gap-3 px-5 py-3 bg-indigo-500/5 border border-indigo-500/10 rounded-2xl text-indigo-400/80 text-[11px] font-semibold italic">
                                <Info className="w-4 h-4" />
                                Our engine will automatically normalize emails and remove duplicates.
                            </div>
                            <div className="flex gap-4 w-full sm:w-auto">
                                <Button variant="secondary" onClick={() => setStep(1)} className="flex-1 sm:flex-none py-6 rounded-2xl border-slate-800">Back</Button>
                                <Button
                                    onClick={() => startImportMutation.mutate()}
                                    disabled={!selectedListId || !mapping["Email"] || startImportMutation.isPending}
                                    className="flex-1 sm:flex-none min-w-[200px] py-6 rounded-2xl bg-indigo-500 hover:bg-indigo-400 font-bold tracking-tight shadow-2xl shadow-indigo-500/20"
                                    rightIcon={<ArrowRight className="w-5 h-5 ml-1" />}
                                >
                                    {startImportMutation.isPending ? "INITIALIZING..." : "START GLOBAL IMPORT"}
                                </Button>
                            </div>
                        </div>
                    </div>
                )}

                {step === 3 && (
                    <div className="py-16 flex flex-col items-center justify-center gap-12">
                        {status === 'completed' ? (
                            <div className="flex flex-col items-center gap-8 text-center animate-in fade-in zoom-in duration-700">
                                <div className="relative">
                                    <div className="w-24 h-24 rounded-full bg-emerald-500/10 border-2 border-emerald-500/20 flex items-center justify-center shadow-[0_0_50px_-12px_rgba(16,185,129,0.3)]">
                                        <Check className="w-12 h-12 text-emerald-500" />
                                    </div>
                                    <div className="absolute -inset-4 bg-emerald-500/20 blur-2xl rounded-full -z-10 animate-pulse" />
                                </div>
                                <div>
                                    <h4 className="text-4xl font-black text-slate-100 italic tracking-tighter leading-none">IMPORT SYNCED!</h4>
                                    <p className="text-slate-500 mt-3 font-semibold text-lg tracking-tight">Your contact database is now live and secured.</p>
                                </div>
                                <div className="grid grid-cols-3 gap-6 w-full max-w-lg mt-4">
                                    <div className="bg-slate-900/60 border-2 border-slate-800/60 rounded-3xl p-6 shadow-2xl">
                                        <div className="text-4xl font-black text-emerald-400 tabular-nums">{stats.imported}</div>
                                        <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-black mt-2">Imported</div>
                                    </div>
                                    <div className="bg-slate-900/60 border-2 border-slate-800/60 rounded-3xl p-6 shadow-2xl">
                                        <div className="text-4xl font-black text-amber-400 tabular-nums">{stats.skipped}</div>
                                        <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-black mt-2">Skipped</div>
                                    </div>
                                    <div className="bg-slate-900/60 border-2 border-slate-800/60 rounded-3xl p-6 shadow-2xl">
                                        <div className="text-4xl font-black text-slate-400 tabular-nums">{stats.duplicates}</div>
                                        <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-black mt-2">Duplicates</div>
                                    </div>
                                </div>
                            </div>
                        ) : status === 'failed' ? (
                            <div className="flex flex-col items-center gap-8 text-center animate-in fade-in zoom-in duration-700">
                                <div className="w-24 h-24 rounded-full bg-red-500/10 border-2 border-red-500/20 flex items-center justify-center">
                                    <AlertCircle className="w-12 h-12 text-red-500" />
                                </div>
                                <div>
                                    <h4 className="text-3xl font-black text-slate-100 tracking-tight">ENCRYPTED FAIL</h4>
                                    <p className="text-red-400/80 mt-2 font-bold max-w-sm">{error || 'The system encounterted a fatal error. Check CSV integrity.'}</p>
                                </div>
                                <Button variant="secondary" onClick={() => setStep(2)} className="rounded-2xl px-10 py-6 border-slate-800">RESTART ENGINE</Button>
                            </div>
                        ) : (
                            <div className="w-full max-w-2xl space-y-16 animate-in fade-in duration-1000">
                                <div className="flex flex-col items-center gap-8 text-center">
                                    <div className="relative group">
                                        <div className="w-32 h-32 rounded-3xl bg-indigo-500/5 border-2 border-indigo-500/10 flex items-center justify-center group-hover:rotate-12 transition-transform duration-700">
                                            <Loader2 className="w-16 h-16 text-indigo-400 animate-spin" />
                                        </div>
                                        <div className="absolute -top-3 -right-3">
                                            <div className="flex items-center justify-center w-12 h-12 rounded-2xl bg-indigo-500 text-lg font-black text-white shadow-2xl shadow-indigo-500/50">
                                                {progress}%
                                            </div>
                                        </div>
                                    </div>
                                    <div>
                                        <h4 className="text-4xl font-black text-slate-100 italic tracking-tighter leading-none">SYNCING DATA...</h4>
                                        <p className="text-slate-500 text-lg mt-3 font-semibold tracking-tight">Utilizing high-performance engine for secure ingestion.</p>
                                    </div>
                                </div>

                                <div className="space-y-6">
                                    <div className="flex items-center justify-between text-[11px] font-black uppercase tracking-[0.3em] text-slate-500 px-2">
                                        <span>Engine Status: ACTIVE</span>
                                        <span className="text-indigo-400">{progress}% Optimized</span>
                                    </div>
                                    <div className="h-6 bg-slate-950/80 rounded-full border-2 border-slate-800/60 overflow-hidden p-1 relative shadow-2xl shadow-black">
                                        <div
                                            className="h-full bg-gradient-to-r from-indigo-700 via-violet-600 to-indigo-500 rounded-full transition-all duration-1000 ease-out relative"
                                            style={{ width: `${progress}%` }}
                                        >
                                            <div className="absolute inset-0 bg-[linear-gradient(45deg,rgba(255,255,255,0.15)_25%,transparent_25%,transparent_50%,rgba(255,255,255,0.15)_50%,rgba(255,255,255,0.15)_75%,transparent_75%,transparent)] bg-[length:32px_32px] animate-[progress-shimmer_1.5s_linear_infinite]" />
                                            <div className="absolute top-0 right-0 h-full w-12 bg-white/20 blur-xl -skew-x-12 animate-pulse" />
                                        </div>
                                    </div>
                                </div>

                                <div className="grid grid-cols-3 gap-8">
                                    <div className="bg-slate-950/60 border-2 border-slate-800/60 rounded-3xl p-6 text-center group hover:border-emerald-500/30 transition-all duration-500">
                                        <div className="text-4xl font-black text-slate-100 group-hover:text-emerald-400 transition-colors">{stats.imported}</div>
                                        <div className="text-[10px] uppercase font-black text-slate-600 tracking-[0.2em] mt-3">SYNCED</div>
                                    </div>
                                    <div className="bg-slate-950/60 border-2 border-slate-800/60 rounded-3xl p-6 text-center group hover:border-amber-500/30 transition-all duration-500">
                                        <div className="text-4xl font-black text-slate-100 group-hover:text-amber-400 transition-colors">{stats.skipped}</div>
                                        <div className="text-[10px] uppercase font-black text-slate-600 tracking-[0.2em] mt-3">CLEANED</div>
                                    </div>
                                    <div className="bg-slate-950/60 border-2 border-slate-800/60 rounded-3xl p-6 text-center group hover:border-slate-500/30 transition-all duration-500">
                                        <div className="text-4xl font-black text-slate-100 group-hover:text-slate-400 transition-colors">{stats.duplicates}</div>
                                        <div className="text-[10px] uppercase font-black text-slate-600 tracking-[0.2em] mt-3">IGNORED</div>
                                    </div>
                                </div>

                                <div className="flex items-center justify-center gap-3 text-xs text-slate-600 font-black uppercase tracking-widest bg-slate-950/50 py-4 border-2 border-slate-800/40 rounded-3xl">
                                    <Zap className="w-4 h-4 text-amber-500 animate-bounce" />
                                    Parallel Batch Ingestion Active
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>

            <Modal
                isOpen={showNewListModal}
                onClose={() => setShowNewListModal(false)}
                title="Create Global Audience"
            >
                <div className="space-y-6 py-4 px-2">
                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">New List Identifier</label>
                        <input
                            type="text"
                            placeholder="e.g. VIP_CUSTOMERS_2024"
                            value={newListName}
                            onChange={(e) => setNewListName(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-4 text-sm text-slate-300 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-bold"
                            autoFocus
                        />
                    </div>
                    <div className="flex justify-end gap-4 pt-4">
                        <Button variant="ghost" onClick={() => setShowNewListModal(false)} className="rounded-xl font-bold">CANCEL</Button>
                        <Button
                            disabled={!newListName.trim() || createListMutation.isPending}
                            onClick={() => createListMutation.mutate(newListName)}
                            className="rounded-xl px-8 bg-indigo-500 hover:bg-indigo-400 font-black shadow-xl shadow-indigo-500/20"
                        >
                            {createListMutation.isPending ? "INITIALIZING..." : "CREATE LIST"}
                        </Button>
                    </div>
                </div>
            </Modal>
        </Card>
    );
};
