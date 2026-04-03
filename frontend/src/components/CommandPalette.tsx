"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  FileText,
  Mail,
  CalendarClock,
  ScrollText,
  LayoutDashboard,
} from "lucide-react";

interface Command {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  keywords: string;
  group: string;
}

// Product 1: Contract Reader only
const commands: Command[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, keywords: "home overview", group: "Navigate" },
  { label: "Plan Intelligence", href: "/contracts", icon: FileText, keywords: "plan intelligence upload pbm contract sbc spd eoc", group: "Analyze" },
  { label: "Disclosure Analyzer", href: "/disclosure", icon: Search, keywords: "dol compliance gap score disclosure", group: "Analyze" },
  { label: "Plan Doc Parser", href: "/spc", icon: ScrollText, keywords: "sbc spd eoc coc benefits summary plan", group: "Analyze" },
  { label: "Audit Letter", href: "/audit", icon: Mail, keywords: "letter request erisa dol audit generate", group: "Act" },
  { label: "Compliance Tracker", href: "/compliance", icon: CalendarClock, keywords: "deadlines hr7148 state bills compliance", group: "Act" },
];

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const filtered = query.trim()
    ? commands.filter(
        (c) =>
          c.label.toLowerCase().includes(query.toLowerCase()) ||
          c.keywords.toLowerCase().includes(query.toLowerCase())
      )
    : commands;

  // Group filtered results
  const groups = filtered.reduce<Record<string, Command[]>>((acc, cmd) => {
    if (!acc[cmd.group]) acc[cmd.group] = [];
    acc[cmd.group].push(cmd);
    return acc;
  }, {});

  const flatFiltered = Object.values(groups).flat();

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
        setQuery("");
        setSelected(0);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    },
    []
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const navigate = (href: string) => {
    setOpen(false);
    setQuery("");
    router.push(href);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, flatFiltered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter" && flatFiltered[selected]) {
      navigate(flatFiltered[selected].href);
    }
  };

  if (!open) return null;

  let flatIndex = -1;

  return (
    <div className="fixed inset-0 z-[100]" onClick={() => setOpen(false)}>
      {/* Backdrop — subtle blur like Linear */}
      <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]" />

      {/* Modal */}
      <div className="relative flex justify-center pt-[20vh]">
        <div
          className="w-full max-w-xl bg-white rounded-xl shadow-[var(--shadow-modal)] border border-gray-200/60 overflow-hidden animate-scale-up"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Search input */}
          <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100">
            <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelected(0);
              }}
              onKeyDown={handleInputKeyDown}
              placeholder="Search modules..."
              className="flex-1 text-sm text-gray-900 placeholder-gray-400 outline-none bg-transparent"
            />
            <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium text-gray-400 bg-gray-100 border border-gray-200">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-80 overflow-y-auto py-2">
            {flatFiltered.length === 0 && (
              <div className="px-5 py-8 text-center">
                <p className="text-sm text-gray-400">No results for &ldquo;{query}&rdquo;</p>
              </div>
            )}

            {Object.entries(groups).map(([groupName, items]) => (
              <div key={groupName}>
                <p className="px-5 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
                  {groupName}
                </p>
                {items.map((cmd) => {
                  flatIndex++;
                  const idx = flatIndex;
                  const Icon = cmd.icon;
                  const isSelected = idx === selected;
                  return (
                    <button
                      key={cmd.href}
                      onClick={() => navigate(cmd.href)}
                      onMouseEnter={() => setSelected(idx)}
                      className={`flex items-center gap-3 w-full px-5 py-2.5 text-left transition-colors ${
                        isSelected
                          ? "bg-primary-50 text-primary-700"
                          : "text-gray-700 hover:bg-gray-50"
                      }`}
                    >
                      <Icon className={`w-4 h-4 flex-shrink-0 ${isSelected ? "text-primary-500" : "text-gray-400"}`} />
                      <span className="text-sm font-medium">{cmd.label}</span>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          {/* Footer hint */}
          <div className="px-5 py-2.5 border-t border-gray-100 flex items-center gap-4 text-[10px] text-gray-400">
            <span><kbd className="font-medium text-gray-500">↑↓</kbd> navigate</span>
            <span><kbd className="font-medium text-gray-500">↵</kbd> open</span>
            <span><kbd className="font-medium text-gray-500">esc</kbd> close</span>
          </div>
        </div>
      </div>
    </div>
  );
}
