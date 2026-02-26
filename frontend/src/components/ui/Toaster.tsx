import { Toaster as Sonner } from "sonner";

export const Toaster = () => {
    return (
        <Sonner
            theme="dark"
            className="toaster group"
            toastOptions={{
                classNames: {
                    toast: "group-[.toaster]:bg-slate-900 group-[.toaster]:text-slate-100 group-[.toaster]:border-2 group-[.toaster]:border-slate-800 group-[.toaster]:shadow-2xl group-[.toaster]:rounded-2xl group-[.toaster]:font-semibold group-[.toaster]:backdrop-blur-xl",
                    description: "group-[.toast]:text-slate-400",
                    actionButton: "group-[.toast]:bg-indigo-500 group-[.toast]:text-slate-100",
                    cancelButton: "group-[.toast]:bg-slate-800 group-[.toast]:text-slate-100",
                    success: "group-[.toaster]:border-emerald-500/50 group-[.toaster]:bg-emerald-500/5",
                    error: "group-[.toaster]:border-red-500/50 group-[.toaster]:bg-red-500/5",
                    info: "group-[.toaster]:border-indigo-500/50 group-[.toaster]:bg-indigo-500/5",
                    warning: "group-[.toaster]:border-amber-500/50 group-[.toaster]:bg-amber-500/5",
                },
            }}
        />
    );
};
