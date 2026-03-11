import React from 'react';
import Layout from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { CheckCircle2, XCircle, MinusCircle } from 'lucide-react';
import { cn } from '../lib/utils';

type Access = 'full' | 'own' | 'none';

interface Row {
    feature: string;
    category: string;
    super_admin: Access;
    admin: Access;
    manager: Access;
    team_member: Access;
}

const MATRIX: Row[] = [
    // CRM — Leads
    { category: 'CRM — Leads', feature: 'View all leads', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'own' },
    { category: 'CRM — Leads', feature: 'Create lead', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'full' },
    { category: 'CRM — Leads', feature: 'Edit lead', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'own' },
    { category: 'CRM — Leads', feature: 'Delete lead', super_admin: 'full', admin: 'full', manager: 'none', team_member: 'none' },
    { category: 'CRM — Leads', feature: 'Assign lead to user', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'none' },
    { category: 'CRM — Leads', feature: 'Claim lead from pool', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'full' },
    { category: 'CRM — Leads', feature: 'Mark lead as claimable', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'none' },

    // CRM — Activities
    { category: 'CRM — Activities', feature: 'Log call / meeting / note', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'own' },
    { category: 'CRM — Activities', feature: 'View all activity timelines', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'own' },
    { category: 'CRM — Activities', feature: 'Book Google Calendar meeting', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'full' },

    // CRM — Scoring
    { category: 'CRM — Scoring', feature: 'View lead score', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'own' },
    { category: 'CRM — Scoring', feature: 'Score is auto-calculated', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'full' },

    // Campaigns
    { category: 'Marketing', feature: 'View campaigns', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'none' },
    { category: 'Marketing', feature: 'Create/edit campaigns', super_admin: 'full', admin: 'full', manager: 'none', team_member: 'none' },
    { category: 'Marketing', feature: 'Send campaigns', super_admin: 'full', admin: 'full', manager: 'none', team_member: 'none' },

    // Analytics
    { category: 'Analytics', feature: 'Team performance report', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'none' },
    { category: 'Analytics', feature: 'System health monitor', super_admin: 'full', admin: 'full', manager: 'none', team_member: 'none' },
    { category: 'Analytics', feature: 'Personal dashboard', super_admin: 'full', admin: 'full', manager: 'full', team_member: 'full' },

    // Admin
    { category: 'Administration', feature: 'User management', super_admin: 'full', admin: 'full', manager: 'none', team_member: 'none' },
    { category: 'Administration', feature: 'Role assignment', super_admin: 'full', admin: 'none', manager: 'none', team_member: 'none' },
    { category: 'Administration', feature: 'Admin portal', super_admin: 'full', admin: 'full', manager: 'none', team_member: 'none' },
    { category: 'Administration', feature: 'Permissions matrix', super_admin: 'full', admin: 'full', manager: 'none', team_member: 'none' },
];

const ROLES: Array<keyof Omit<Row, 'feature' | 'category'>> = [
    'super_admin', 'admin', 'manager', 'team_member'
];
const ROLE_LABELS: Record<string, string> = {
    super_admin: 'Super Admin',
    admin: 'Admin',
    manager: 'Manager',
    team_member: 'Team Member',
};
const ROLE_COLOR: Record<string, string> = {
    super_admin: 'text-rose-400',
    admin: 'text-indigo-400',
    manager: 'text-violet-400',
    team_member: 'text-emerald-400',
};

const AccessIcon: React.FC<{ access: Access }> = ({ access }) => {
    if (access === 'full') return <CheckCircle2 className="w-5 h-5 text-emerald-400 mx-auto" />;
    if (access === 'own') return (
        <span className="flex flex-col items-center">
            <MinusCircle className="w-5 h-5 text-amber-400 mx-auto" />
            <span className="text-[8px] text-amber-500 font-black uppercase">Own only</span>
        </span>
    );
    return <XCircle className="w-5 h-5 text-slate-700 mx-auto" />;
};

const PermissionsMatrix: React.FC = () => {
    // Group rows by category
    const categories = Array.from(new Set(MATRIX.map(r => r.category)));

    return (
        <Layout>
            <div className="space-y-8 p-8 max-w-[1200px] mx-auto">
                {/* Header */}
                <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-rose-500 flex items-center justify-center shadow-lg shadow-rose-500/20">
                        <CheckCircle2 className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-black text-slate-100 italic tracking-tight uppercase">
                            Permissions <span className="text-rose-400">Matrix</span>
                        </h1>
                        <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-1">
                            What each role can and cannot do across the CRM
                        </p>
                    </div>
                </div>

                {/* Legend */}
                <div className="flex items-center gap-6 text-xs font-bold text-slate-400">
                    <div className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-400" /> Full access</div>
                    <div className="flex items-center gap-2"><MinusCircle className="w-4 h-4 text-amber-400" /> Own records only</div>
                    <div className="flex items-center gap-2"><XCircle className="w-4 h-4 text-slate-600" /> No access</div>
                </div>

                {/* Matrix Table */}
                <Card className="border-2 border-slate-800/60 bg-slate-950/40 backdrop-blur-md rounded-3xl overflow-hidden shadow-2xl">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-slate-800/60">
                                    <th className="text-left py-5 px-6 text-[10px] font-black text-slate-500 uppercase tracking-widest w-1/2">
                                        Feature / Action
                                    </th>
                                    {ROLES.map(role => (
                                        <th key={role} className={cn(
                                            "py-5 px-4 text-[10px] font-black uppercase tracking-widest text-center",
                                            ROLE_COLOR[role]
                                        )}>
                                            {ROLE_LABELS[role]}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {categories.map(category => {
                                    const rows = MATRIX.filter(r => r.category === category);
                                    return (
                                        <React.Fragment key={category}>
                                            <tr className="bg-slate-900/60">
                                                <td colSpan={ROLES.length + 1} className="px-6 py-2 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] border-t border-slate-800/40">
                                                    {category}
                                                </td>
                                            </tr>
                                            {rows.map((row, i) => (
                                                <tr
                                                    key={row.feature}
                                                    className={cn(
                                                        "border-b border-slate-800/30 transition-colors hover:bg-slate-800/20",
                                                        i % 2 === 0 ? "bg-transparent" : "bg-slate-900/20"
                                                    )}
                                                >
                                                    <td className="py-4 px-6 text-sm text-slate-300 font-semibold">{row.feature}</td>
                                                    {ROLES.map(role => (
                                                        <td key={role} className="py-4 px-4 text-center">
                                                            <AccessIcon access={row[role] as Access} />
                                                        </td>
                                                    ))}
                                                </tr>
                                            ))}
                                        </React.Fragment>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </Card>
            </div>
        </Layout>
    );
};

export default PermissionsMatrix;
