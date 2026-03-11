import React, { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../auth/AuthContext";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

const GoogleCallback: React.FC = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { token } = useAuth();
    const processed = useRef(false);

    useEffect(() => {
        const handleCallback = async () => {
            if (processed.current) return;
            processed.current = true;

            const code = searchParams.get("code");
            const state = searchParams.get("state");

            if (!code || !state) {
                toast.error("Invalid callback parameters");
                navigate("/calendar");
                return;
            }

            try {
                await axios.get("/api/integrations/google/callback", {
                    params: { code, state },
                    headers: { Authorization: `Bearer ${token}` }
                });
                toast.success("Google Calendar connected successfully!");
            } catch (err: any) {
                console.error("OAuth callback failed", err);
                const errorDetail = err.response?.data?.detail || "Connection failed";
                toast.error(`OAuth failed: ${errorDetail}`);
            } finally {
                navigate("/calendar");
            }
        };

        if (token) {
            handleCallback();
        }
    }, [searchParams, navigate, token]);

    return (
        <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
            <div className="text-center space-y-4">
                <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto" />
                <h2 className="text-xl font-semibold text-white">Finalizing Connection</h2>
                <p className="text-slate-400">Please wait while we sync your Google Calendar access...</p>
            </div>
        </div>
    );
};

export default GoogleCallback;
