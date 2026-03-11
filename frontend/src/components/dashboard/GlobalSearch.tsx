import React, { useState, useEffect, useRef } from "react";
import { Search, Command, X, Users, Building2, UserCircle2, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../../lib/api";
import { cn } from "../../lib/utils";

interface SearchResult {
    id: string;
    type: 'lead' | 'contact' | 'organization';
    title: string;
    subtitle?: string;
    link: string;
}

const GlobalSearch: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const navigate = useNavigate();
    const inputRef = useRef<HTMLInputElement>(null);

    // Toggle logic
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "k") {
                e.preventDefault();
                setIsOpen(prev => !prev);
            }
            if (e.key === "Escape") {
                setIsOpen(false);
            }
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, []);

    // Focus treatment
    useEffect(() => {
        if (isOpen) {
            setTimeout(() => inputRef.current?.focus(), 10);
            setQuery("");
            setResults([]);
        }
    }, [isOpen]);

    // Search logic
    useEffect(() => {
        const fetchResults = async () => {
            if (query.length < 2) {
                setResults([]);
                return;
            }
            setIsLoading(true);
            try {
                const res = await api.get(`/search?q=${encodeURIComponent(query)}`);
                setResults(res.data);
                setSelectedIndex(0);
            } catch (err) {
                console.error("Search failed", err);
            } finally {
                setIsLoading(false);
            }
        };

        const timeoutId = setTimeout(fetchResults, 300);
        return () => clearTimeout(timeoutId);
    }, [query]);

    const handleSelect = (result: SearchResult) => {
        setIsOpen(false);
        navigate(result.link);
    };

    const onKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "ArrowDown") {
            e.preventDefault();
            setSelectedIndex(prev => (prev + 1) % results.length);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setSelectedIndex(prev => (prev - 1 + results.length) % results.length);
        } else if (e.key === "Enter" && results[selectedIndex]) {
            handleSelect(results[selectedIndex]);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] px-4 bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div
                className="w-full max-w-2xl bg-slate-900 border border-slate-800 shadow-2xl rounded-3xl overflow-hidden flex flex-col slide-in-from-top-4 animate-in duration-300"
                onClick={e => e.stopPropagation()}
            >
                {/* Search Input Area */}
                <div className="flex items-center px-6 py-5 border-b border-slate-800 gap-4 bg-slate-900/50">
                    <Search className="w-5 h-5 text-indigo-400" />
                    <input
                        ref={inputRef}
                        type="text"
                        placeholder="Search for leads, contacts, or organizations..."
                        className="flex-1 bg-transparent border-none outline-none text-slate-100 text-lg font-medium placeholder:text-slate-600"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        onKeyDown={onKeyDown}
                    />
                    <div className="flex items-center gap-1 px-2 py-1 bg-slate-800 rounded-lg border border-slate-700">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">ESC</span>
                    </div>
                </div>

                {/* Results Area */}
                <div className="max-h-[60vh] overflow-y-auto no-scrollbar py-2">
                    {isLoading ? (
                        <div className="px-8 py-12 text-center text-slate-500 font-medium">
                            Searching across intelligence layer...
                        </div>
                    ) : query.length < 2 ? (
                        <div className="px-8 py-12 text-center">
                            <div className="w-16 h-16 rounded-3xl bg-slate-800/50 flex items-center justify-center mx-auto mb-4 border border-slate-700/50">
                                <Command className="w-8 h-8 text-slate-500" />
                            </div>
                            <h3 className="text-slate-200 font-bold mb-1">Global Intelligence</h3>
                            <p className="text-slate-500 text-sm">Type to search across your entire workspace.</p>
                        </div>
                    ) : results.length === 0 ? (
                        <div className="px-8 py-12 text-center text-slate-500 font-medium">
                            No matching results found for "{query}"
                        </div>
                    ) : (
                        <div className="px-3 space-y-1">
                            {results.map((result, idx) => (
                                <button
                                    key={`${result.type}-${result.id}`}
                                    onClick={() => handleSelect(result)}
                                    className={cn(
                                        "w-full flex items-center justify-between p-3 rounded-2xl transition-all group",
                                        selectedIndex === idx ? "bg-indigo-500 shadow-lg shadow-indigo-500/20" : "hover:bg-slate-800/50"
                                    )}
                                >
                                    <div className="flex items-center gap-4">
                                        <div className={cn(
                                            "w-10 h-10 rounded-xl flex items-center justify-center transition-colors shadow-inner",
                                            selectedIndex === idx ? "bg-white/20" : "bg-slate-800 group-hover:bg-slate-700"
                                        )}>
                                            {result.type === 'lead' && <Users className={cn("w-5 h-5", selectedIndex === idx ? "text-white" : "text-indigo-400")} />}
                                            {result.type === 'contact' && <UserCircle2 className={cn("w-5 h-5", selectedIndex === idx ? "text-white" : "text-emerald-400")} />}
                                            {result.type === 'organization' && <Building2 className={cn("w-5 h-5", selectedIndex === idx ? "text-white" : "text-amber-400")} />}
                                        </div>
                                        <div className="text-left">
                                            <p className={cn("font-black text-sm transition-colors", selectedIndex === idx ? "text-white" : "text-slate-200")}>
                                                {result.title}
                                            </p>
                                            <p className={cn("text-[10px] font-bold transition-colors uppercase tracking-widest", selectedIndex === idx ? "text-white/70" : "text-slate-500")}>
                                                {result.type} • {result.subtitle}
                                            </p>
                                        </div>
                                    </div>
                                    <ArrowRight className={cn(
                                        "w-4 h-4 transition-all",
                                        selectedIndex === idx ? "text-white translate-x-0" : "text-slate-700 -translate-x-2 opacity-0 group-hover:opacity-100 group-hover:translate-x-0"
                                    )} />
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                <div className="px-6 py-4 bg-slate-900 border-t border-slate-800 flex items-center justify-between">
                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-2">
                            <div className="w-5 h-5 bg-slate-800 border border-slate-700 rounded flex items-center justify-center">
                                <span className="text-[10px] font-black text-slate-400">↵</span>
                            </div>
                            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Select</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-5 h-5 bg-slate-800 border border-slate-700 rounded flex items-center justify-center">
                                <span className="text-[10px] font-black text-slate-400">↑↓</span>
                            </div>
                            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Navigate</span>
                        </div>
                    </div>
                    <div className="text-[9px] font-black text-slate-700 uppercase tracking-[0.2em]">CRM INTELLIGENCE LAYER</div>
                </div>
            </div>

            {/* Click outside to close */}
            <div className="absolute inset-0 -z-10" onClick={() => setIsOpen(false)} />
        </div>
    );
};

export default GlobalSearch;
