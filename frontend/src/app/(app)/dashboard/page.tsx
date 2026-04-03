"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import MetricCard from "@/components/MetricCard";
import StatusBadge from "@/components/StatusBadge";
import { SkeletonCard } from "@/components/Skeleton";
import Tooltip from "@/components/Tooltip";
import {
  ShieldCheck,
  FileText,
  Search,
  Mail,
  CalendarClock,
  CheckCircle2,
  Loader2,
  ArrowUpRight,
  ChevronDown,
  ScrollText,
} from "lucide-react";

interface DashboardStats {
  claims_loaded: boolean;
  claims_count: number;
  contracts_parsed: number;
  modules_active: number;
  data_source: string;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showExtras, setShowExtras] = useState(false);

  useEffect(() => {
    fetch("/api/dashboard/stats")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setStats(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const hasContracts = (stats?.contracts_parsed ?? 0) > 0;

  return (
    <div className="max-w-4xl mx-auto">
      {/* ─── New User: Onboarding ─── */}
      {!loading && !hasContracts && (
        <div className="pt-8 pb-8">
          <div className="mb-10 animate-fade-in">
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Welcome to ClearScript</h1>
            <p className="text-gray-400 mt-1">Follow these steps to analyze your PBM contract.</p>
          </div>

          {/* Onboarding Steps */}
          <div className="space-y-4 animate-fade-in-d1">
            {/* Step 1 */}
            <Link
              href="/contracts"
              className="group flex items-start gap-5 p-6 bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] hover:border-primary-300 hover:shadow-[var(--shadow-card-hover)] transition-all duration-200"
            >
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary-600 text-white flex items-center justify-center text-sm font-bold">
                1
              </div>
              <div className="flex-1">
                <h3 className="text-base font-semibold text-gray-900 mb-1 group-hover:text-primary-600 transition-colors">Upload your PBM contract</h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  Upload your PBM services agreement (PDF or text). AI will extract rebate terms, spread pricing, audit rights, formulary clauses, and termination provisions — scored as employer-favorable or PBM-favorable.
                </p>
              </div>
              <ArrowUpRight className="w-4 h-4 text-gray-200 group-hover:text-primary-500 transition-colors mt-1" />
            </Link>

            {/* Step 2 */}
            <Link
              href="/contracts"
              className="group flex items-start gap-5 p-6 bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] hover:border-primary-300 hover:shadow-[var(--shadow-card-hover)] transition-all duration-200"
            >
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-sm font-bold">
                2
              </div>
              <div className="flex-1">
                <h3 className="text-base font-semibold text-gray-900 mb-1 group-hover:text-primary-600 transition-colors">Add your plan document</h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  Upload your SBC, SPD, or EOC to cross-reference against the contract. The AI identifies gaps between what the contract promises and what the plan document says.
                </p>
              </div>
              <ArrowUpRight className="w-4 h-4 text-gray-200 group-hover:text-primary-500 transition-colors mt-1" />
            </Link>

            {/* Step 3 */}
            <Link
              href="/disclosure"
              className="group flex items-start gap-5 p-6 bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] hover:border-primary-300 hover:shadow-[var(--shadow-card-hover)] transition-all duration-200"
            >
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-sm font-bold">
                3
              </div>
              <div className="flex-1">
                <h3 className="text-base font-semibold text-gray-900 mb-1 group-hover:text-primary-600 transition-colors">Score your PBM disclosure</h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  Upload your PBM&apos;s semiannual disclosure document. AI checks it against 20 DOL-required items and generates a completeness score with a gap report.
                </p>
              </div>
              <ArrowUpRight className="w-4 h-4 text-gray-200 group-hover:text-primary-500 transition-colors mt-1" />
            </Link>

            {/* Step 4 */}
            <div className="flex items-start gap-5 p-6 bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)]">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-sm font-bold">
                4
              </div>
              <div className="flex-1">
                <h3 className="text-base font-semibold text-gray-900 mb-1">Export your report</h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  Download a branded PDF report with executive summary, risk score, audit rights scorecard, compliance flags, and a draft audit letter — ready for your CFO or board.
                </p>
              </div>
            </div>
          </div>

          {/* Extras */}
          <div className="mt-14 text-center animate-fade-in-d2">
            <button
              onClick={() => setShowExtras(!showExtras)}
              className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-500 transition-colors"
            >
              System details
              <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${showExtras ? "rotate-180" : ""}`} />
            </button>
          </div>

          {showExtras && (
            <div className="mt-5 grid grid-cols-1 lg:grid-cols-2 gap-4 animate-fade-in">
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5">
                <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Key PBM Terms</h3>
                <div className="grid grid-cols-2 gap-x-6 gap-y-1">
                  {["Spread Pricing", "NADAC", "Rebate Passthrough", "NDC", "J-code", "Prior Authorization", "Formulary", "ERISA", "408(b)(2)", "CAA 2026", "Fiduciary", "Self-Insured"].map((term) => (
                    <div key={term} className="py-0.5">
                      <Tooltip term={term}>
                        <span className="text-sm text-primary-600 font-medium border-b border-dashed border-primary-200 cursor-help">{term}</span>
                      </Tooltip>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5">
                <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">System Status</h3>
                <div className="space-y-2.5">
                  {[
                    { label: "Backend API", ok: !!stats },
                    { label: "AI Analysis (Gemini)", ok: true },
                    { label: "PDF Parser", ok: true },
                    { label: "Compliance Data", ok: true },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center gap-3">
                      {item.ok ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border-2 border-gray-200" />
                      )}
                      <span className="text-sm text-gray-500 flex-1">{item.label}</span>
                      <StatusBadge status={item.ok ? "good" : "warning"} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─── Returning User ─── */}
      {!loading && hasContracts && (
        <div className="pt-4 animate-fade-in">
          <div className="mb-10">
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Dashboard</h1>
            <p className="text-gray-400 mt-1">Your PBM contract analysis overview</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
            <MetricCard
              icon={FileText}
              label="Contracts Analyzed"
              value={String(stats?.contracts_parsed || 0)}
              trend="Analyzed"
              trendUp={true}
              color="green"
            />
            <MetricCard
              icon={ShieldCheck}
              label="Active Modules"
              value="7"
              trend="Contract Reader"
              trendUp={true}
              color="blue"
            />
            <MetricCard
              icon={CalendarClock}
              label="Compliance Items"
              value="7"
              trend="Tracked"
              trendUp={true}
              color="blue"
            />
          </div>

          <div className="mb-10">
            <h2 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Continue Working</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { href: "/contracts", icon: FileText, label: "Plan Intelligence", sub: "Contracts & plan docs" },
                { href: "/disclosure", icon: Search, label: "Disclosure Analyzer", sub: "DOL compliance scoring" },
                { href: "/audit", icon: Mail, label: "Audit Letter", sub: "Generate with citations" },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <Link key={item.href} href={item.href} className="group flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-card-hover)] hover:border-primary-200 transition-all duration-200">
                    <div className="bg-gray-50 rounded-lg p-2.5 group-hover:bg-primary-50 transition-colors duration-200">
                      <Icon className="w-4 h-4 text-gray-400 group-hover:text-primary-600 transition-colors duration-200" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{item.label}</p>
                      <p className="text-xs text-gray-400">{item.sub}</p>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] px-5 py-4">
            <div className="flex flex-wrap gap-x-8 gap-y-2">
              {[
                { label: "Backend API", ok: !!stats },
                { label: "AI Analysis", ok: true },
                { label: "PDF Parser", ok: true },
                { label: "Compliance Data", ok: true },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-2">
                  {item.ok ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  ) : (
                    <div className="w-3.5 h-3.5 rounded-full border-2 border-gray-200" />
                  )}
                  <span className="text-sm text-gray-500">{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─── Loading ─── */}
      {loading && (
        <div className="pt-12">
          <div className="text-center mb-14">
            <div className="h-10 w-64 bg-gray-100 rounded-lg animate-pulse mx-auto" />
            <div className="h-5 w-80 bg-gray-50 rounded-lg animate-pulse mt-4 mx-auto" />
          </div>
          <div className="max-w-md mx-auto">
            <SkeletonCard />
          </div>
        </div>
      )}
    </div>
  );
}
