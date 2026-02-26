import React from "react";
import { Link, useLocation } from "react-router-dom";
import classNames from "classnames";
import {
  LayoutDashboard,
  Send,
  Users,
  Settings,
  LogOut,
  FileText,
  GitBranch,
  Activity,
  X
} from "lucide-react";
import { useAuth } from "../../auth/AuthContext";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const location = useLocation();
  const { logout } = useAuth();

  const navigation = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Campaigns", href: "/campaigns", icon: Send },
    { name: "Workflows", href: "/workflows", icon: GitBranch },
    { name: "Leads", href: "/leads", icon: Users },
    { name: "Templates", href: "/templates", icon: FileText },
    { name: "System Status", href: "/system-status", icon: Activity },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  const isActive = (path: string) => {
    if (path === "/" && location.pathname === "/") return true;
    if (path !== "/" && location.pathname.startsWith(path)) return true;
    return false;
  };

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className={classNames(
          "fixed inset-0 z-40 bg-slate-950/80 backdrop-blur-sm transition-opacity md:hidden",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
      />

      {/* Sidebar panel */}
      <aside
        className={classNames(
          "fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 border-r border-slate-800 transition-transform duration-300 md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between h-16 px-6 border-b border-slate-800">
          <span className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
            AutoMail
          </span>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 rounded hover:bg-slate-800 md:hidden"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex flex-col h-[calc(100vh-4rem)] p-4 space-y-1">
          <div className="flex-1 space-y-1">
            {navigation.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={classNames(
                    "flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors group",
                    active
                      ? "bg-indigo-500/10 text-indigo-400"
                      : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                  )}
                >
                  <item.icon
                    className={classNames(
                      "w-5 h-5 mr-3 flex-shrink-0",
                      active ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-300"
                    )}
                  />
                  {item.name}
                </Link>
              );
            })}
          </div>

          <div className="pt-4 border-t border-slate-800">
            <button
              onClick={logout}
              className="flex items-center w-full px-3 py-2 text-sm font-medium text-slate-400 rounded-lg hover:bg-red-500/10 hover:text-red-400 transition-colors group"
            >
              <LogOut className="w-5 h-5 mr-3 text-slate-500 group-hover:text-red-400" />
              Sign Out
            </button>
          </div>
        </nav>
      </aside>
    </>
  );
};
