import React, { useState } from "react";
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
  TrendingUp,
  X,
  LayoutGrid,
  List,
  ChevronDown,
  BarChart2,
  Megaphone
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const location = useLocation();
  const { logout, isAdmin } = useAuth();

  const isMarketingSection = location.pathname.startsWith('/campaigns') || location.pathname.startsWith('/workflows') || location.pathname.startsWith('/templates');
  const isLeadsSection = location.pathname.startsWith('/leads');
  const isAnalyticsSection = location.pathname.startsWith('/analytics');

  const [marketingOpen, setMarketingOpen] = useState(isMarketingSection);
  const [leadsOpen, setLeadsOpen] = useState(isLeadsSection);
  const [analyticsOpen, setAnalyticsOpen] = useState(isAnalyticsSection);


  const isActive = (path: string) => {
    if (path === "/" && location.pathname === "/") return true;
    if (path !== "/" && location.pathname === path) return true;
    return false;
  };

  const mainNav = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  if (isAdmin) {
    mainNav.push({ name: "Admin Portal", href: "/admin", icon: Users });
  }

  const leadsSubNav = [
    { name: "Pipeline Board", href: "/leads/pipeline", icon: LayoutGrid },
    { name: "Lead Directory", href: "/leads/list", icon: List },
  ];

  const marketingSubNav = [
    { name: "Campaigns", href: "/campaigns", icon: Send },
    { name: "Workflows", href: "/workflows", icon: GitBranch },
    { name: "Templates", href: "/templates", icon: FileText },
  ];

  const analyticsSubNav = [
    { name: "Team Performance", href: "/analytics/performance", icon: TrendingUp },
  ];
  if (isAdmin) {
    analyticsSubNav.push({ name: "System Health", href: "/analytics/system", icon: Activity });
  }

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

        <nav className="flex flex-col h-[calc(100vh-4rem)] p-4 space-y-1 overflow-y-auto">
          <div className="flex-1 space-y-0.5">
            {/* Top-level item: Dashboard */}
            {mainNav.slice(0, 1).map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={classNames(
                    "flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors group mb-2",
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

            {/* ── Marketing Accordion ── */}
            <div>
              <button
                onClick={() => setMarketingOpen(prev => !prev)}
                className={classNames(
                  "flex items-center w-full px-3 py-2 text-sm font-medium rounded-lg transition-colors group",
                  isMarketingSection
                    ? "bg-indigo-500/10 text-indigo-400"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <Megaphone className={classNames(
                  "w-5 h-5 mr-3 flex-shrink-0",
                  isMarketingSection ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-300"
                )} />
                <span className="flex-1 text-left">Marketing</span>
                <ChevronDown className={classNames(
                  "w-4 h-4 flex-shrink-0 transition-transform duration-200",
                  marketingOpen ? "rotate-180" : "",
                  isMarketingSection ? "text-indigo-400" : "text-slate-600"
                )} />
              </button>

              {marketingOpen && (
                <div className="ml-8 mt-0.5 space-y-0.5 border-l border-slate-800 pl-3">
                  {marketingSubNav.map((item) => {
                    const active = isActive(item.href);
                    return (
                      <Link
                        key={item.name}
                        to={item.href}
                        className={classNames(
                          "flex items-center px-3 py-2 text-xs font-semibold rounded-lg transition-colors group",
                          active
                            ? "bg-indigo-500/10 text-indigo-400"
                            : "text-slate-500 hover:bg-slate-800 hover:text-slate-100"
                        )}
                      >
                        <item.icon className={classNames(
                          "w-4 h-4 mr-2.5 flex-shrink-0",
                          active ? "text-indigo-400" : "text-slate-600 group-hover:text-slate-400"
                        )} />
                        {item.name}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>

            {/* ── Leads Accordion ── */}
            <div>
              <button
                onClick={() => setLeadsOpen(prev => !prev)}
                className={classNames(
                  "flex items-center w-full px-3 py-2 text-sm font-medium rounded-lg transition-colors group mt-0.5",
                  isLeadsSection
                    ? "bg-indigo-500/10 text-indigo-400"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <Users className={classNames(
                  "w-5 h-5 mr-3 flex-shrink-0",
                  isLeadsSection ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-300"
                )} />
                <span className="flex-1 text-left">CRM / Leads</span>
                <ChevronDown className={classNames(
                  "w-4 h-4 flex-shrink-0 transition-transform duration-200",
                  leadsOpen ? "rotate-180" : "",
                  isLeadsSection ? "text-indigo-400" : "text-slate-600"
                )} />
              </button>

              {leadsOpen && (
                <div className="ml-8 mt-0.5 space-y-0.5 border-l border-slate-800 pl-3">
                  {leadsSubNav.map((item) => {
                    const active = isActive(item.href);
                    return (
                      <Link
                        key={item.name}
                        to={item.href}
                        className={classNames(
                          "flex items-center px-3 py-2 text-xs font-semibold rounded-lg transition-colors group",
                          active
                            ? "bg-indigo-500/10 text-indigo-400"
                            : "text-slate-500 hover:bg-slate-800 hover:text-slate-100"
                        )}
                      >
                        <item.icon className={classNames(
                          "w-4 h-4 mr-2.5 flex-shrink-0",
                          active ? "text-indigo-400" : "text-slate-600 group-hover:text-slate-400"
                        )} />
                        {item.name}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>

            {/* ── Analytics Accordion ── */}
            <div>
              <button
                onClick={() => setAnalyticsOpen(prev => !prev)}
                className={classNames(
                  "flex items-center w-full px-3 py-2 text-sm font-medium rounded-lg transition-colors group mt-0.5",
                  isAnalyticsSection
                    ? "bg-indigo-500/10 text-indigo-400"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <BarChart2 className={classNames(
                  "w-5 h-5 mr-3 flex-shrink-0",
                  isAnalyticsSection ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-300"
                )} />
                <span className="flex-1 text-left">Analytics</span>
                <ChevronDown className={classNames(
                  "w-4 h-4 flex-shrink-0 transition-transform duration-200",
                  analyticsOpen ? "rotate-180" : "",
                  isAnalyticsSection ? "text-indigo-400" : "text-slate-600"
                )} />
              </button>

              {analyticsOpen && (
                <div className="ml-8 mt-0.5 space-y-0.5 border-l border-slate-800 pl-3 mb-0.5">
                  {analyticsSubNav.map((item) => {
                    const active = isActive(item.href);
                    return (
                      <Link
                        key={item.name}
                        to={item.href}
                        className={classNames(
                          "flex items-center px-3 py-2 text-xs font-semibold rounded-lg transition-colors group",
                          active
                            ? "bg-indigo-500/10 text-indigo-400"
                            : "text-slate-500 hover:bg-slate-800 hover:text-slate-100"
                        )}
                      >
                        <item.icon className={classNames(
                          "w-4 h-4 mr-2.5 flex-shrink-0",
                          active ? "text-indigo-400" : "text-slate-600 group-hover:text-slate-400"
                        )} />
                        {item.name}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>

            {mainNav.slice(1).map((item) => {

              const active = isActive(item.href);
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={classNames(
                    "flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors group mt-0.5",
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
