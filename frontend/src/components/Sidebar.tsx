"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  Search,
  Mail,
  CalendarClock,
  ShieldCheck,
  ScrollText,
  ChevronDown,
  Menu,
  X,
} from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

// Product 1: Contract Reader
const navGroups: NavGroup[] = [
  {
    label: "Analyze",
    items: [
      { href: "/contracts", label: "Plan Intelligence", icon: FileText },
      { href: "/disclosure", label: "Disclosure Analyzer", icon: Search },
      { href: "/spc", label: "Plan Doc Parser", icon: ScrollText },
    ],
  },
  {
    label: "Act",
    items: [
      { href: "/audit", label: "Audit Letter", icon: Mail },
      { href: "/compliance", label: "Compliance Tracker", icon: CalendarClock },
    ],
  },
];

// Future products — uncomment when shipping
// const auditGroup: NavGroup = {
//   label: "Audit",
//   items: [
//     { href: "/audit-timeline", label: "Audit Timeline", icon: Clock },
//     { href: "/reports", label: "Report Auditor", icon: ClipboardList },
//   ],
// };
// const analyticsGroup: NavGroup = { ... };
// const benchmarkingGroup: NavGroup = { ... };
// const dataGroup: NavGroup = { ... };

function NavSection({
  group,
  pathname,
  onNavigate,
}: {
  group: NavGroup;
  pathname: string;
  onNavigate?: () => void;
}) {
  const hasActive = group.items.some((item) => item.href === pathname);
  const [open, setOpen] = useState(true); // Always open — only 5 items total

  return (
    <div className="mb-0.5">
      <button
        onClick={() => setOpen(!open)}
        className={`flex items-center justify-between w-full px-5 py-2 text-xs font-semibold uppercase tracking-wider transition-colors ${
          hasActive ? "text-blue-200" : "text-blue-300/50 hover:text-blue-200"
        }`}
      >
        {group.label}
        <ChevronDown
          className={`w-3 h-3 transition-transform duration-200 ${open ? "" : "-rotate-90"}`}
        />
      </button>
      <div
        className={`overflow-hidden transition-all duration-200 ${
          open ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        {group.items.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              aria-current={isActive ? "page" : undefined}
              className={`flex items-center gap-3 px-5 py-2 text-sm transition-all duration-150 ${
                isActive
                  ? "bg-white/12 text-white font-medium border-l-2 border-emerald-400 ml-1 rounded-r-md"
                  : "text-blue-100/60 hover:bg-white/6 hover:text-blue-50"
              }`}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

export default function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="p-5 border-b border-white/10">
        <Link href="/dashboard" className="flex items-center gap-3" onClick={() => setMobileOpen(false)}>
          <ShieldCheck className="w-7 h-7 text-emerald-400" />
          <div>
            <h1 className="text-lg font-bold tracking-tight">ClearScript</h1>
            <p className="text-[11px] text-blue-200/60 mt-0.5">Plan Intelligence</p>
          </div>
        </Link>
      </div>

      {/* Search trigger */}
      <div className="px-3 pt-3 pb-1">
        <button
          onClick={() => {
            setMobileOpen(false);
            document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
          }}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-blue-200/50 hover:text-blue-100 hover:bg-white/8 transition-colors"
        >
          <Search className="w-4 h-4 flex-shrink-0" />
          <span className="flex-1 text-left">Search...</span>
          <kbd className="text-[10px] text-blue-300/40 bg-white/10 px-1.5 py-0.5 rounded">⌘K</kbd>
        </button>
      </div>

      {/* Dashboard link */}
      <div className="px-3 pb-1">
        <Link
          href="/dashboard"
          onClick={() => setMobileOpen(false)}
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
            pathname === "/dashboard"
              ? "bg-white/15 text-white font-medium"
              : "text-blue-100/70 hover:bg-white/8 hover:text-white"
          }`}
        >
          <LayoutDashboard className="w-4 h-4 flex-shrink-0" />
          Dashboard
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2 overflow-y-auto scrollbar-thin">
        {navGroups.map((group) => (
          <NavSection
            key={group.label}
            group={group}
            pathname={pathname}
            onNavigate={() => setMobileOpen(false)}
          />
        ))}
      </nav>

      {/* User */}
      <div className="px-4 py-3 border-t border-white/10 flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-300 text-sm font-bold flex-shrink-0">
          R
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-white truncate">Romir Jain</p>
          <p className="text-[11px] text-blue-200/40">Contract Reader</p>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-50 bg-primary-600 text-white p-2 rounded-lg shadow-lg"
        aria-label="Open menu"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={`lg:hidden fixed left-0 top-0 z-50 w-64 bg-primary-600 text-white flex flex-col h-screen transform transition-transform duration-300 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <button
          onClick={() => setMobileOpen(false)}
          className="absolute top-4 right-4 text-white/50 hover:text-white"
          aria-label="Close menu"
        >
          <X className="w-5 h-5" />
        </button>
        {sidebarContent}
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-64 bg-primary-600 text-white flex-col min-h-screen fixed left-0 top-0 z-40">
        {sidebarContent}
      </aside>
    </>
  );
}
