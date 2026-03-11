import React, { useState, useEffect, useRef } from 'react';
import { Card } from '../ui/Card';
import { useGlobalWebSocket } from '../../context/WebSocketContext';
import { Activity, Mail, MousePointer, AlertCircle, Volume2, Layers, Settings } from 'lucide-react';

interface ActivityEvent {
    type: string;
    event_type: string;
    user_email: string;
    user_id: string;
    timestamp: string;
    is_hot_lead?: boolean;
    campaign_id?: string;
    campaign_name?: string;
    detail?: string; // New field for detailed system events
}

export const LiveActivityFeed: React.FC = () => {
    const [events, setEvents] = useState<ActivityEvent[]>([]);
    const [soundEnabled, setSoundEnabled] = useState(true);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    const { isConnected, lastMessage } = useGlobalWebSocket();

    useEffect(() => {
        if (!lastMessage) return;

        if (lastMessage.type === 'event') {
            const event = lastMessage as ActivityEvent;

            // Add to events list (keep last 20)
            setEvents(prev => [event, ...prev].slice(0, 20));

            // Play sound for hot leads (clicks)
            if (event.is_hot_lead && soundEnabled && audioRef.current) {
                audioRef.current.play().catch(e => console.log('Audio play failed:', e));
            }
        }
    }, [lastMessage, soundEnabled]);

    // Initialize audio element
    useEffect(() => {
        // Create a simple beep sound using Web Audio API
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();

        // Store for later use
        audioRef.current = {
            play: async () => {
                const osc = audioContext.createOscillator();
                const gain = audioContext.createGain();
                osc.connect(gain);
                gain.connect(audioContext.destination);
                osc.frequency.value = 800;
                gain.gain.value = 0.3;
                osc.start();
                gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
                osc.stop(audioContext.currentTime + 0.3);
            }
        } as any;
    }, []);

    const getEventIcon = (eventType: string) => {
        switch (eventType) {
            case 'clicked':
                return <MousePointer className="w-4 h-4 text-red-400" />;
            case 'opened':
                return <Mail className="w-4 h-4 text-yellow-400" />;
            case 'sent':
                return <Mail className="w-4 h-4 text-blue-400" />;
            case 'campaign_activated':
            case 'campaign_resumed':
                return <Activity className="w-4 h-4 text-emerald-400" />;
            case 'campaign_paused':
                return <AlertCircle className="w-4 h-4 text-orange-400" />;
            case 'campaign_completed':
                return <Activity className="w-4 h-4 text-indigo-400" />;
            case 'WORKFLOW_NODE_ENTER':
                return <Layers className="w-4 h-4 text-slate-400" />;
            case 'campaign_config_updated':
                return <Settings className="w-4 h-4 text-indigo-400" />;
            default:
                return <Activity className="w-4 h-4 text-slate-400" />;
        }
    };

    const getEventColor = (eventType: string) => {
        switch (eventType) {
            case 'clicked':
                return 'border-l-red-500 bg-red-500/5';
            case 'opened':
                return 'border-l-yellow-500 bg-yellow-500/5';
            case 'sent':
                return 'border-l-blue-500 bg-blue-500/5';
            case 'campaign_activated':
            case 'campaign_resumed':
                return 'border-l-emerald-500 bg-emerald-500/5';
            case 'campaign_paused':
                return 'border-l-orange-500 bg-orange-500/5';
            case 'campaign_completed':
                return 'border-l-indigo-500 bg-indigo-500/5';
            case 'campaign_config_updated':
                return 'border-l-indigo-500 bg-indigo-500/5';
            default:
                return 'border-l-slate-500 bg-slate-500/5';
        }
    };

    const formatTimestamp = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now.getTime() - date.getTime();

        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleTimeString();
    };

    const getEventMessage = (event: ActivityEvent) => {
        switch (event.event_type) {
            case 'clicked': return 'Clicked a link';
            case 'opened': return 'Opened an email';
            case 'sent': return 'Email sent';
            case 'campaign_activated': return `Campaign "${event.campaign_name || 'System'}" Activated`;
            case 'campaign_paused': return `Campaign "${event.campaign_name || 'System'}" Paused`;
            case 'campaign_completed': return `Campaign "${event.campaign_name || 'System'}" Completed`;
            case 'campaign_config_updated': return event.detail || `Campaign "${event.campaign_name || 'System'}" configuration updated`;
            case 'WORKFLOW_NODE_ENTER': return 'Advancing in workflow';
            default: return 'System event';
        }
    };

    return (
        <Card className="p-0 overflow-hidden border-slate-800 bg-slate-900/50 backdrop-blur-xl shadow-2xl">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/20">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-500/10 rounded-lg">
                        <Activity className="w-5 h-5 text-indigo-400" />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">Live Activity</h3>
                        <div className="flex items-center gap-2">
                            {isConnected ? (
                                <span className="flex items-center gap-1.5 text-[10px] font-bold text-emerald-400 uppercase tracking-tighter">
                                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.5)]"></span>
                                    Streaming
                                </span>
                            ) : (
                                <span className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-tighter">
                                    <span className="w-1.5 h-1.5 bg-slate-500 rounded-full"></span>
                                    Offline
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                <button
                    onClick={() => setSoundEnabled(!soundEnabled)}
                    className={`p-2 rounded-xl transition-all duration-300 ${soundEnabled
                        ? 'bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20'
                        : 'bg-slate-800/50 text-slate-500 hover:bg-slate-800'
                        }`}
                    title={soundEnabled ? 'Mute alerts' : 'Enable alerts'}
                >
                    <Volume2 className="w-4 h-4" />
                </button>
            </div>

            <div className="space-y-px overflow-y-auto max-h-[500px]">
                {events.length === 0 ? (
                    <div className="text-center py-12 text-slate-500">
                        <div className="w-16 h-16 bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-4 border border-slate-700">
                            <Activity className="w-8 h-8 opacity-20" />
                        </div>
                        <p className="font-medium">Waiting for activity...</p>
                        <p className="text-xs mt-1 text-slate-600">Events will appear here in real-time</p>
                    </div>
                ) : (
                    events.map((event, index) => (
                        <div
                            key={`${event.timestamp}-${index}`}
                            className={`p-4 border-l-4 ${getEventColor(event.event_type)} border-b border-slate-800/50 transition-all hover:bg-slate-800/20 ${event.is_hot_lead ? 'bg-red-500/5' : ''
                                }`}
                        >
                            <div className="flex items-start justify-between gap-4">
                                <div className="flex items-start gap-4 flex-1">
                                    <div className="mt-1">
                                        {getEventIcon(event.event_type)}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center flex-wrap gap-2 mb-1">
                                            <span className="font-bold text-slate-200 text-sm truncate max-w-[150px]">
                                                {event.user_email || 'System'}
                                            </span>
                                            {event.is_hot_lead && (
                                                <span className="px-1.5 py-0.5 text-[10px] font-black bg-red-500 text-white rounded shadow-lg shadow-red-500/20 animate-pulse">
                                                    HOT LEAD
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-xs text-slate-400 font-medium">
                                            {getEventMessage(event)}
                                        </p>
                                    </div>
                                </div>
                                <span className="text-[10px] font-bold text-slate-500 uppercase whitespace-nowrap pt-1">
                                    {formatTimestamp(event.timestamp)}
                                </span>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </Card>
    );
};
