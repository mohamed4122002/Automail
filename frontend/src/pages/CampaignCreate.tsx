import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { ArrowLeft, Save, ChevronRight, ChevronLeft, Check, Layers, Users, Info } from "lucide-react";
import api from "../lib/api";
import { toast } from "sonner";

interface Workflow {
    id: string;
    name: string;
    description: string;
}

interface ContactList {
    id: string;
    name: string;
    contact_count: number;
}

const CampaignCreate: React.FC = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [step, setStep] = useState(1);
    const [workflows, setWorkflows] = useState<Workflow[]>([]);
    const [contactLists, setContactLists] = useState<ContactList[]>([]);

    const [formData, setFormData] = useState({
        name: "",
        description: "",
        workflow_id: "",
        contact_list_id: ""
    });

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [wfRes, clRes] = await Promise.all([
                    api.get("/workflows"),
                    api.get("/contacts/lists")
                ]);
                setWorkflows(wfRes.data);
                setContactLists(clRes.data);
            } catch (err) {
                console.error("Failed to fetch wizard data:", err);
                toast.error("Failed to load workflows or contact lists");
            }
        };
        fetchData();
    }, []);

    const handleNext = () => {
        if (step === 1 && !formData.name) {
            toast.error("Campaign name is required");
            return;
        }
        if (step === 2 && !formData.workflow_id) {
            toast.error("Please select a workflow");
            return;
        }
        setStep(prev => prev + 1);
    };

    const handleBack = () => setStep(prev => prev - 1);

    const handleSubmit = async () => {
        if (!formData.contact_list_id) {
            toast.error("Please select a contact list");
            return;
        }

        setLoading(true);
        try {
            const response = await api.post("/campaigns", {
                name: formData.name,
                description: formData.description,
                contact_list_id: formData.contact_list_id
            });

            const campaignId = response.data.id;

            // Link workflow if selected
            if (formData.workflow_id) {
                await api.patch(`/workflows/${formData.workflow_id}`, {
                    campaign_id: campaignId
                });
            }

            toast.success("Campaign created successfully!");
            navigate(`/campaigns/${campaignId}`);
        } catch (err: any) {
            console.error("Failed to create campaign:", err);
            toast.error(err.response?.data?.detail || "Failed to create campaign");
        } finally {
            setLoading(false);
        }
    };

    const steps = [
        { id: 1, title: "Basic Info", icon: <Info className="w-4 h-4" /> },
        { id: 2, title: "Select Workflow", icon: <Layers className="w-4 h-4" /> },
        { id: 3, title: "Choose Audience", icon: <Users className="w-4 h-4" /> }
    ];

    return (
        <Layout title="Create Campaign">
            <div className="max-w-4xl mx-auto px-4">
                <Button
                    variant="ghost"
                    className="mb-6 pl-0 hover:bg-transparent hover:text-indigo-400"
                    onClick={() => navigate("/campaigns")}
                >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Campaigns
                </Button>

                {/* Stepper */}
                <div className="flex items-center justify-between mb-8 relative">
                    <div className="absolute top-1/2 left-0 w-full h-0.5 bg-slate-800 -translate-y-1/2 z-0"></div>
                    {steps.map((s) => (
                        <div key={s.id} className="relative z-10 flex flex-col items-center">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${step >= s.id ? "bg-indigo-600 border-indigo-500 text-white" : "bg-slate-900 border-slate-700 text-slate-500"
                                }`}>
                                {step > s.id ? <Check className="w-5 h-5" /> : s.icon}
                            </div>
                            <span className={`text-xs mt-2 font-medium ${step >= s.id ? "text-indigo-400" : "text-slate-500"}`}>
                                {s.title}
                            </span>
                        </div>
                    ))}
                </div>

                <Card className="border-slate-800 bg-slate-900/50 backdrop-blur-xl shadow-2xl">
                    <CardHeader className="border-b border-slate-800 pb-6">
                        <CardTitle className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                            {steps.find(s => s.id === step)?.title}
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-8">
                        {step === 1 && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-300">Campaign Name *</label>
                                    <input
                                        type="text"
                                        className="w-full px-4 py-3 bg-slate-950/50 border border-slate-800 rounded-xl text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                                        placeholder="e.g. Q1 Global Outreach"
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-300">Description</label>
                                    <textarea
                                        className="w-full px-4 py-3 bg-slate-950/50 border border-slate-800 rounded-xl text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 min-h-[120px] transition-all"
                                        placeholder="Describe the goals of this campaign..."
                                        value={formData.description}
                                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    />
                                </div>
                            </div>
                        )}

                        {step === 2 && (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                {workflows.length === 0 ? (
                                    <div className="col-span-2 text-center py-12 bg-slate-950/30 rounded-2xl border border-dashed border-slate-800">
                                        <Layers className="w-12 h-12 mx-auto mb-3 text-slate-600" />
                                        <p className="text-slate-400">No workflows found.</p>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="mt-4"
                                            onClick={() => navigate("/workflows")}
                                        >
                                            Create one first
                                        </Button>
                                    </div>
                                ) : (
                                    workflows.map(wf => (
                                        <div
                                            key={wf.id}
                                            onClick={() => setFormData({ ...formData, workflow_id: wf.id })}
                                            className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${formData.workflow_id === wf.id
                                                ? "border-indigo-500 bg-indigo-500/10"
                                                : "border-slate-800 bg-slate-950/30 hover:border-slate-700"
                                                }`}
                                        >
                                            <div className="flex items-center gap-3 mb-2">
                                                <div className={`p-2 rounded-lg ${formData.workflow_id === wf.id ? "bg-indigo-500 text-white" : "bg-slate-800 text-slate-400"}`}>
                                                    <Layers className="w-4 h-4" />
                                                </div>
                                                <h4 className="font-semibold text-slate-200">{wf.name}</h4>
                                            </div>
                                            <p className="text-xs text-slate-500 line-clamp-2">{wf.description || "No description provided"}</p>
                                        </div>
                                    ))
                                )}
                            </div>
                        )}

                        {step === 3 && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <p className="text-sm text-slate-400 mb-4">Select the contact list you want to target with this campaign.</p>
                                <div className="grid grid-cols-1 gap-3">
                                    {contactLists.length === 0 ? (
                                        <div className="text-center py-12 bg-slate-950/30 rounded-2xl border border-dashed border-slate-800">
                                            <Users className="w-12 h-12 mx-auto mb-3 text-slate-600" />
                                            <p className="text-slate-400">No contact lists found.</p>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="mt-4"
                                                onClick={() => navigate("/contacts")}
                                            >
                                                Import contacts
                                            </Button>
                                        </div>
                                    ) : (
                                        contactLists.map(list => (
                                            <div
                                                key={list.id}
                                                onClick={() => setFormData({ ...formData, contact_list_id: list.id })}
                                                className={`p-4 rounded-xl border-2 flex items-center justify-between cursor-pointer transition-all ${formData.contact_list_id === list.id
                                                    ? "border-indigo-500 bg-indigo-500/10"
                                                    : "border-slate-800 bg-slate-950/30 hover:border-slate-700"
                                                    }`}
                                            >
                                                <div className="flex items-center gap-4">
                                                    <div className={`p-3 rounded-full ${formData.contact_list_id === list.id ? "bg-indigo-500 text-white" : "bg-slate-800 text-slate-500"}`}>
                                                        <Users className="w-5 h-5" />
                                                    </div>
                                                    <div>
                                                        <h4 className="font-semibold text-slate-200">{list.name}</h4>
                                                        <p className="text-xs text-slate-400">{list.contact_count} contacts</p>
                                                    </div>
                                                </div>
                                                {formData.contact_list_id === list.id && <Check className="text-indigo-500 w-5 h-5" />}
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        )}

                        <div className="flex justify-between mt-12 pt-6 border-t border-slate-800">
                            <Button
                                variant="ghost"
                                onClick={handleBack}
                                disabled={step === 1 || loading}
                                leftIcon={<ChevronLeft className="w-4 h-4" />}
                            >
                                Back
                            </Button>

                            {step < 3 ? (
                                <Button
                                    onClick={handleNext}
                                    rightIcon={<ChevronRight className="w-4 h-4" />}
                                >
                                    Next Step
                                </Button>
                            ) : (
                                <Button
                                    onClick={handleSubmit}
                                    isLoading={loading}
                                    leftIcon={<Save className="w-4 h-4" />}
                                >
                                    Finish & Launch
                                </Button>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </Layout>
    );
};

export default CampaignCreate;
