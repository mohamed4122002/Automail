import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Mail, CheckCircle, XCircle, Loader2 } from 'lucide-react';

const Unsubscribe: React.FC = () => {
    const { token } = useParams<{ token: string }>();
    const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'already_unsubscribed'>('loading');
    const [message, setMessage] = useState('');
    const [email, setEmail] = useState('');

    useEffect(() => {
        const performUnsubscribe = async () => {
            try {
                // Determine API URL - using the relative proxy or direct URL depending on setup
                // Assuming the base URL is handled by the api lib or axios defaults
                const response = await axios.post(`/api/unsubscribe/${token}`);
                const data = response.data;

                if (data.status === 'success') {
                    setStatus('success');
                    setMessage(data.message);
                    setEmail(data.email);
                } else if (data.status === 'already_unsubscribed') {
                    setStatus('already_unsubscribed');
                    setEmail(data.email);
                }
            } catch (error: any) {
                console.error('Unsubscribe error:', error);
                setStatus('error');
                setMessage(error.response?.data?.detail || 'An error occurred while processing your request. The link may be invalid or expired.');
            }
        };

        if (token) {
            performUnsubscribe();
        } else {
            setStatus('error');
            setMessage('Invalid unsubscribe link.');
        }
    }, [token]);

    return (
        <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-md">
                <div className="flex justify-center mb-8">
                    <div className="flex items-center gap-2">
                        <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center">
                            <Mail className="text-white w-6 h-6" />
                        </div>
                        <span className="text-xl font-bold text-white tracking-tight">Antigravity</span>
                    </div>
                </div>

                <Card className="border-slate-800 bg-slate-900 shadow-xl">
                    <CardHeader className="text-center">
                        <CardTitle className="text-2xl font-bold text-white">
                            {status === 'loading' && 'Processing...'}
                            {status === 'success' && 'Unsubscribed Successfully'}
                            {status === 'already_unsubscribed' && 'Already Unsubscribed'}
                            {status === 'error' && 'Unsubscribe Failed'}
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6 pt-2">
                        {status === 'loading' && (
                            <div className="flex flex-col items-center py-8">
                                <Loader2 className="w-12 h-12 text-indigo-500 animate-spin mb-4" />
                                <p className="text-slate-400">Verifying your request...</p>
                            </div>
                        )}

                        {status === 'success' && (
                            <div className="text-center space-y-4 py-4">
                                <div className="flex justify-center">
                                    <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center">
                                        <CheckCircle className="w-10 h-10 text-emerald-500" />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <p className="text-lg text-slate-200">
                                        You have been removed from our list.
                                    </p>
                                    <p className="text-sm text-slate-400">
                                        Email: <span className="text-slate-300 font-medium">{email}</span>
                                    </p>
                                </div>
                                <p className="text-sm text-slate-500 pt-4">
                                    You will no longer receive marketing emails from this specific campaign.
                                </p>
                            </div>
                        )}

                        {status === 'already_unsubscribed' && (
                            <div className="text-center space-y-4 py-4">
                                <div className="flex justify-center">
                                    <div className="w-16 h-16 bg-blue-500/10 rounded-full flex items-center justify-center">
                                        <CheckCircle className="w-10 h-10 text-blue-500" />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <p className="text-lg text-slate-200">
                                        You are already unsubscribed.
                                    </p>
                                    <p className="text-sm text-slate-400">
                                        Email: <span className="text-slate-300 font-medium">{email}</span>
                                    </p>
                                </div>
                            </div>
                        )}

                        {status === 'error' && (
                            <div className="text-center space-y-4 py-4">
                                <div className="flex justify-center">
                                    <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center">
                                        <XCircle className="w-10 h-10 text-red-500" />
                                    </div>
                                </div>
                                <p className="text-slate-300 font-medium">
                                    {message}
                                </p>
                                <p className="text-sm text-slate-500">
                                    If you continue to receive emails, please contact support.
                                </p>
                            </div>
                        )}
                    </CardContent>
                </Card>

                <p className="mt-8 text-center text-slate-600 text-xs">
                    &copy; 2024 Antigravity Marketing Platform. All rights reserved.
                </p>
            </div>
        </div>
    );
};

export default Unsubscribe;
