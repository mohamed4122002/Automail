/**
 * Lead Status Constants
 * Synchronized with backend LeadStatusEnum
 */
export const LEAD_STATUS = {
    HOT: 'hot',
    WARM: 'warm',
    COLD: 'cold',
    NEW: 'new',
    UNSUBSCRIBED: 'unsubscribed',
} as const;

export type LeadStatus = typeof LEAD_STATUS[keyof typeof LEAD_STATUS];

export const LEAD_STATUS_LABELS: Record<LeadStatus, string> = {
    [LEAD_STATUS.HOT]: 'Hot',
    [LEAD_STATUS.WARM]: 'Warm',
    [LEAD_STATUS.COLD]: 'Cold',
    [LEAD_STATUS.NEW]: 'New',
    [LEAD_STATUS.UNSUBSCRIBED]: 'Unsubscribed',
};

export const LEAD_STATUS_COLORS: Record<LeadStatus, string> = {
    [LEAD_STATUS.HOT]: 'bg-red-500/10 text-red-400 border-red-500/20',
    [LEAD_STATUS.WARM]: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    [LEAD_STATUS.COLD]: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    [LEAD_STATUS.NEW]: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    [LEAD_STATUS.UNSUBSCRIBED]: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
};
