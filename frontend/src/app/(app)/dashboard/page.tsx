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
  latest_analysis?: {
    filename?: string | null;
    analysis_date?: string | null;
    deal_score?: number | null;
    weighted_risk_score?: number | null;
    risk_level?: string | null;
    deal_diagnosis?: string | null;
    financial_exposure_summary?: string | null;
    financial_exposure_mode?: string | null;
    spread_exposure_estimate?: string | null;
    top_risks?: { title?: string; severity?: string; tier?: number }[];
    immediate_actions?: string[];
  };
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
  const latest = stats?.latest_analysis;

  return (
    <div className="max-w-4xl mx-auto">
      {/* ─── New User: Onboarding ─── */}
      {!loading && !hasContracts && (
        <div className="pt-8 pb-8">
          <div className="mb-10 animate-fade-in">
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Welcome to ClearScript</h1>
            <p className="text-gray-400 mt-1">Start with the contract, then move into deal quality, plan gaps, and audit recovery.</p>
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
                <h3 className="text-base font-semibold text-gray-900 mb-1 group-hover:text-primary-600 transition-colors">Analyze the PBM deal</h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  Upload the PBM services agreement. ClearScript will identify the economic and control terms that matter most: rebate structure, spread pricing, specialty control, and audit rights.
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
                <h3 className="text-base font-semibold text-gray-900 mb-1 group-hover:text-primary-600 transition-colors">Find contract vs plan gaps</h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  Upload the SBC, SPD, or EOC to compare what the contract says against what the plan document actually communicates to members.
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
                <h3 className="text-base font-semibold text-gray-900 mb-1 group-hover:text-primary-600 transition-colors">Pressure test disclosure and recovery</h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  Check the PBM&apos;s disclosures against DOL-required items so missing pricing, rebate, and spread data is visible before an audit cycle.
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
                <h3 className="text-base font-semibold text-gray-900 mb-1">Export an executive readout</h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  Download a report that leads with deal diagnosis, financial exposure, control gaps, and immediate actions for procurement, legal, or finance review.
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
            <p className="text-gray-400 mt-1">Decision-first view of your PBM deal quality, exposure, and next actions</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-10">
            <MetricCard
              icon={ShieldCheck}
              label="PBM Deal Score"
              value={hasContracts && latest?.deal_score != null ? String(latest.deal_score) : "—"}
              trend={hasContracts && latest?.risk_level ? `${latest.risk_level} risk` : "Run analysis"}
              trendUp={!hasContracts}
              color="blue"
            />
            <MetricCard
              icon={ScrollText}
              label="Estimated Financial Exposure"
              value={hasContracts ? (latest?.spread_exposure_estimate || "Directional") : "—"}
              trend={hasContracts ? (latest?.financial_exposure_mode === "claims_backed" ? "Claims-backed" : "Directional") : "Awaiting deal data"}
              trendUp={false}
              color="green"
            />
            <MetricCard
              icon={FileText}
              label="Deals Reviewed"
              value={String(stats?.contracts_parsed || 0)}
              trend="Contracts analyzed"
              trendUp={true}
              color="blue"
            />
            <MetricCard
              icon={CalendarClock}
              label="Immediate Actions"
              value={hasContracts ? String(latest?.immediate_actions?.length || 3) : "0"}
              trend={hasContracts ? "Ready" : "No contract yet"}
              trendUp={hasContracts}
              color="green"
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-10">
            <div className="xl:col-span-2 bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5">
              <h2 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Executive View</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  { title: "Deal Diagnosis", body: latest?.deal_diagnosis || "Run a contract analysis to generate a one-line diagnosis of the PBM structure." },
                  { title: "Exposure", body: latest?.financial_exposure_summary || "Financial exposure will summarize rebate leakage, spread pricing, and specialty control once a contract is analyzed." },
                  { title: "Priority", body: latest?.top_risks?.[0]?.title ? `Top live risk: ${latest.top_risks[0].title}.` : "Lead every review with rebate structure, spread, specialty control, and audit scope before administrative terms." },
                ].map((item) => (
                  <div key={item.title} className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                    <p className="text-sm font-semibold text-gray-900">{item.title}</p>
                    <p className="text-sm text-gray-600 mt-2 leading-relaxed">{item.body}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5">
              <h2 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Immediate Actions</h2>
              <div className="space-y-3">
                {(latest?.immediate_actions && latest.immediate_actions.length > 0 ? latest.immediate_actions : [
                  "Review rebate definitions before relying on passthrough guarantees.",
                  "Validate whether spread is prohibited, capped, or simply undisclosed.",
                  "Check specialty routing and audit scope before renewal negotiations.",
                ]).map((item, index) => (
                  <div key={item} className="flex gap-3">
                    <div className="w-6 h-6 rounded-full bg-primary-50 text-primary-600 text-xs font-bold flex items-center justify-center flex-shrink-0">{index + 1}</div>
                    <p className="text-sm text-gray-600">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mb-10">
            <h2 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Decision Workflows</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { href: "/contracts", icon: FileText, label: "Deal Analysis", sub: "Contract economics and governance" },
                { href: "/contracts", icon: Search, label: "Contract vs Plan Gaps", sub: "Cross-reference plan documents" },
                { href: "/audit", icon: Mail, label: "Audit & Recovery", sub: "Generate letters and support follow-up" },
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
