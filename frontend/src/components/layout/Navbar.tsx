import React, { useState, useRef, useEffect } from "react";
import { Menu, Bell, User, Plus, LogOut, Settings } from "lucide-react";
import { Button } from "../ui/Button";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";

interface NavbarProps {
  onMenuClick: () => void;
  title?: string;
}

import { monitoringService, HealthStatus } from "../../services/monitoring";
import { Activity, Database, Zap, Cpu } from "lucide-react";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../ui/tooltip";

const HealthIndicator: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await monitoringService.getHealth();
        setHealth(data);
      } catch (err) {
        console.error("Health check failed", err);
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  if (loading && !health) return null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-emerald-500';
      case 'unhealthy': return 'bg-red-500';
      case 'degraded': return 'bg-amber-500';
      default: return 'bg-slate-500';
    }
  };

  return (
    <TooltipProvider>
      <div className="hidden lg:flex items-center gap-4 px-4 py-1.5 rounded-full bg-slate-800/40 border border-slate-700/50 backdrop-blur-sm mr-4">
        <Tooltip>
          <TooltipTrigger className="flex items-center gap-1.5 cursor-help">
            <Database className="w-3 h-3 text-slate-400" />
            <div className={`w-1.5 h-1.5 rounded-full ${getStatusColor(health?.services.postgres || 'unknown')} shadow-[0_0_8px_rgba(16,185,129,0.3)]`} />
            <span className="text-[10px] font-medium text-slate-400">DB</span>
          </TooltipTrigger>
          <TooltipContent>
            PostgreSQL: <span className="font-bold uppercase">{health?.services.postgres || 'unknown'}</span>
          </TooltipContent>
        </Tooltip>

        <div className="w-px h-3 bg-slate-700/50" />

        <Tooltip>
          <TooltipTrigger className="flex items-center gap-1.5 cursor-help">
            <Zap className="w-3 h-3 text-slate-400" />
            <div className={`w-1.5 h-1.5 rounded-full ${getStatusColor(health?.services.redis || 'unknown')} shadow-[0_0_8px_rgba(245,158,11,0.3)]`} />
            <span className="text-[10px] font-medium text-slate-400">Cache</span>
          </TooltipTrigger>
          <TooltipContent>
            Redis: <span className="font-bold uppercase">{health?.services.redis || 'unknown'}</span>
          </TooltipContent>
        </Tooltip>

        <div className="w-px h-3 bg-slate-700/50" />

        <Tooltip>
          <TooltipTrigger className="flex items-center gap-1.5 cursor-help">
            <Cpu className="w-3 h-3 text-slate-400" />
            <div className={`w-1.5 h-1.5 rounded-full ${getStatusColor(health?.services.celery || 'unknown')} shadow-[0_0_8px_rgba(99,102,241,0.3)]`} />
            <span className="text-[10px] font-medium text-slate-400">Worker</span>
          </TooltipTrigger>
          <TooltipContent>
            Celery: <span className="font-bold uppercase">{health?.services.celery || 'unknown'}</span>
          </TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
};

export const Navbar: React.FC<NavbarProps> = ({ onMenuClick, title }) => {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [showProfile, setShowProfile] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  const profileRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setShowProfile(false);
      }
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between h-16 px-4 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 sm:px-6 lg:px-8">
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuClick}
          className="p-2 -ml-2 text-slate-400 rounded-lg hover:bg-slate-800 md:hidden focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
        >
          <Menu className="w-6 h-6" />
        </button>
        <h1 className="text-lg font-semibold text-slate-100">
          {title || "Dashboard"}
        </h1>
      </div>

      <div className="flex items-center gap-4">
        <HealthIndicator />
        <Link to="/campaigns/new">
          <Button size="sm" leftIcon={<Plus className="w-4 h-4" />}>
            New Campaign
          </Button>
        </Link>

        <div className="flex items-center gap-2 border-l border-slate-800 pl-4 ml-2">
          {/* Notifications */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className="p-2 text-slate-400 rounded-full hover:bg-slate-800 hover:text-slate-100 transition-colors relative"
            >
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-slate-900" />
            </button>

            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 bg-slate-900 border border-slate-800 rounded-lg shadow-xl py-2 animate-in fade-in slide-in-from-top-2">
                <div className="px-4 py-2 border-b border-slate-800">
                  <h3 className="text-sm font-semibold text-slate-100">Notifications</h3>
                </div>
                <div className="py-2">
                  <p className="px-4 py-3 text-sm text-slate-400 text-center">No new notifications</p>
                </div>
              </div>
            )}
          </div>

          {/* User Profile */}
          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setShowProfile(!showProfile)}
              className="flex items-center gap-2 p-1 pl-2 text-sm text-left rounded-full hover:bg-slate-800 transition-colors"
            >
              <div className="w-8 h-8 overflow-hidden rounded-full bg-slate-700 flex items-center justify-center">
                <User className="w-5 h-5 text-slate-400" />
              </div>
            </button>

            {showProfile && (
              <div className="absolute right-0 mt-2 w-48 bg-slate-900 border border-slate-800 rounded-lg shadow-xl py-1 animate-in fade-in slide-in-from-top-2">
                <Link to="/settings" className="flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white">
                  <Settings className="w-4 h-4" />
                  Settings
                </Link>
                <div className="border-t border-slate-800 my-1"></div>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-slate-800 hover:text-red-300"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
