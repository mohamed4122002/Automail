import React, { useState } from "react";
import axios from "axios";
import { useAuth } from "../../auth/AuthContext";
import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";
import { Input } from "../ui/input";
import { toast } from "sonner";
import { Calendar, Clock, AlignLeft, Users as UsersIcon } from "lucide-react";

interface ScheduleMeetingModalProps {
    isOpen: boolean;
    onClose: () => void;
    assignee: {
        id: string;
        email: string;
        name: string;
    } | null;
}

export const ScheduleMeetingModal: React.FC<ScheduleMeetingModalProps> = ({ isOpen, onClose, assignee }) => {
    const { token } = useAuth();
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        summary: "",
        description: "",
        date: new Date().toISOString().split('T')[0],
        startTime: "09:00",
        duration: "30"
    });

    if (!assignee) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            const startDateTime = new Date(`${formData.date}T${formData.startTime}:00`);
            const endDateTime = new Date(startDateTime.getTime() + parseInt(formData.duration) * 60000);

            await axios.post("/api/meetings/assign", {
                assignee_id: assignee.id,
                summary: formData.summary,
                description: formData.description,
                start_time: startDateTime.toISOString(),
                end_time: endDateTime.toISOString()
            }, {
                headers: { Authorization: `Bearer ${token}` }
            });

            toast.success("Meeting scheduled and synced to Google Calendar");
            onClose();
        } catch (err: any) {
            const msg = err.response?.data?.detail || "Failed to schedule meeting";
            toast.error(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Schedule Meeting">
            <form onSubmit={handleSubmit} className="space-y-4">
                <div className="p-3 bg-blue-500/5 border border-blue-500/10 rounded-lg flex items-center gap-3 mb-4">
                    <UsersIcon className="w-5 h-5 text-blue-400" />
                    <div>
                        <p className="text-xs text-slate-500 uppercase font-bold tracking-wider">Assignee</p>
                        <p className="text-sm font-medium text-white">{assignee.name} ({assignee.email})</p>
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-slate-500" />
                        Meeting Title
                    </label>
                    <Input
                        required
                        placeholder="e.g., Weekly Pipeline Sync"
                        value={formData.summary}
                        onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
                        className="bg-slate-950 border-slate-800"
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                            <Clock className="w-4 h-4 text-slate-500" />
                            Date
                        </label>
                        <Input
                            type="date"
                            required
                            value={formData.date}
                            onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                            className="bg-slate-950 border-slate-800"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                            <Clock className="w-4 h-4 text-slate-500" />
                            Start Time
                        </label>
                        <Input
                            type="time"
                            required
                            value={formData.startTime}
                            onChange={(e) => setFormData({ ...formData, startTime: e.target.value })}
                            className="bg-slate-950 border-slate-800"
                        />
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-300">Duration (Minutes)</label>
                    <select
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-300 focus:ring-2 focus:ring-blue-500 outline-none"
                        value={formData.duration}
                        onChange={(e) => setFormData({ ...formData, duration: e.target.value })}
                    >
                        <option value="15">15 Minutes</option>
                        <option value="30">30 Minutes</option>
                        <option value="60">1 Hour</option>
                        <option value="90">1.5 Hours</option>
                    </select>
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                        <AlignLeft className="w-4 h-4 text-slate-500" />
                        Agenda / Description
                    </label>
                    <textarea
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-300 focus:ring-2 focus:ring-blue-500 outline-none min-h-[100px]"
                        placeholder="Topics to cover..."
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    />
                </div>

                <div className="flex gap-3 pt-4 border-t border-slate-800">
                    <Button type="button" variant="outline" className="flex-1" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button type="submit" className="flex-1 bg-blue-600 hover:bg-blue-500 text-white" disabled={loading}>
                        {loading ? "Scheduling..." : "Schedule Meeting"}
                    </Button>
                </div>
            </form>
        </Modal>
    );
};
