"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  FileText,
  Search,
  Mail,
  CalendarClock,
  ArrowUpRight,
  CheckCircle2,
  AlertTriangle,
  Clock,
  DollarSign,
  BookOpen,
} from "lucide-react";

interface ContractStatus {
  id: number;
  filename: string;
  analysis_date: string | null;
  deal_score: number | null;
  risk_level: string | null;
  has_claims: boolean;
  has_plan_doc: boolean;
  has_cross_ref: boolean;
  notice_deadline: string | null;
}

interface DashboardData {
  contracts_parsed: number;
  contracts: ContractStatus[];
  latest_analysis: {
    filename: string | null;
    analysis_date: string | null;
    deal_score: number | null;
    risk_level: string | null;
    deal_diagnosis: string | null;
    control_posture_label: string | null;
    control_posture_summary: string | null;
  } | null;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso.includes("T") ? iso : iso + "T00:00:00");
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return iso;
  }
}

function daysUntil(iso: string | null): number | null {
  if (!iso) return null;
  try {
    const d = new Date(iso + "T00:00:00");
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    return Math.round((d.getTime() - now.getTime()) / 86400000);
  } catch {
    return null;
  }
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/dashboard/stats")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setData(d))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const hasContracts = (data?.contracts_parsed ?? 0) > 0;
  const latest = data?.latest_analysis;

  // Find the nearest notice deadline across all contracts
  const nearestDeadline = (() => {
    if (!data?.contracts) return null;
    let nearest: { contract: ContractStatus; days: number } | null = null;
    for (const c of data.contracts) {
      const days = daysUntil(c.notice_deadline);
      if (days !== null && (nearest === null || days < nearest.days)) {
        nearest = { contract: c, days };
      }
    }
    return nearest;
  })();

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto pt-12">
        <div className="text-center mb-14">
          <div className="h-10 w-64 bg-gray-100 rounded-lg animate-pulse mx-auto" />
          <div className="h-5 w-80 bg-gray-50 rounded-lg animate-pulse mt-4 mx-auto" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* ─── New User: Onboarding ─── */}
      {!hasContracts && (
        <div className="pt-8 pb-8 animate-fade-in">
          <div className="mb-10">
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Welcome to ClearScript</h1>
            <p className="text-gray-400 mt-1">Upload a PBM contract to get started.</p>
          </div>

          <div className="space-y-4">
            <Link
              href="/contracts"
              className="group flex items-start gap-5 p-6 bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] hover:border-primary-300 hover:shadow-[var(--shadow-card-hover)] transition-all duration-200"
            >
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary-600 text-white flex items-center justify-center">
                <FileText className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <h3 className="text-base font-semibold text-gray-900 mb-1 group-hover:text-primary-600 transition-colors">Upload a PBM contract</h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  ClearScript will analyze the economic and governance terms, score the deal, and generate specific redline language for renegotiation.
                </p>
              </div>
              <ArrowUpRight className="w-4 h-4 text-gray-200 group-hover:text-primary-500 transition-colors mt-1" />
            </Link>

            <Link
              href="/disclosure"
              className="group flex items-start gap-5 p-6 bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] hover:border-primary-300 hover:shadow-[var(--shadow-card-hover)] transition-all duration-200"
            >
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center">
                <Search className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <h3 className="text-base font-semibold text-gray-900 mb-1 group-hover:text-primary-600 transition-colors">Review a PBM disclosure</h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  Check the PBM&apos;s semiannual disclosure against DOL requirements and cross-reference against your contract terms.
                </p>
              </div>
              <ArrowUpRight className="w-4 h-4 text-gray-200 group-hover:text-primary-500 transition-colors mt-1" />
            </Link>
          </div>
        </div>
      )}

      {/* ─── Returning User: Real Data ─── */}
      {hasContracts && (
        <div className="pt-4 animate-fade-in">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Dashboard</h1>
            <p className="text-gray-400 mt-1">{data!.contracts_parsed} contract{data!.contracts_parsed === 1 ? "" : "s"} analyzed</p>
          </div>

          {/* Nearest deadline alert */}
          {nearestDeadline && nearestDeadline.days <= 90 && (
            <div className={`rounded-xl border p-4 mb-6 flex items-start gap-3 ${
              nearestDeadline.days < 0
                ? "bg-red-50 border-red-200"
                : nearestDeadline.days <= 30
                ? "bg-amber-50 border-amber-200"
                : "bg-blue-50 border-blue-200"
            }`}>
              <AlertTriangle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                nearestDeadline.days < 0 ? "text-red-600" : nearestDeadline.days <= 30 ? "text-amber-600" : "text-blue-600"
              }`} />
              <div>
                <p className={`text-sm font-semibold ${
                  nearestDeadline.days < 0 ? "text-red-900" : nearestDeadline.days <= 30 ? "text-amber-900" : "text-blue-900"
                }`}>
                  {nearestDeadline.days < 0
                    ? `Notice deadline passed ${Math.abs(nearestDeadline.days)} days ago`
                    : nearestDeadline.days === 0
                    ? "Notice deadline is today"
                    : `Notice deadline in ${nearestDeadline.days} days`}
                </p>
                <p className={`text-xs mt-0.5 ${
                  nearestDeadline.days < 0 ? "text-red-800" : nearestDeadline.days <= 30 ? "text-amber-800" : "text-blue-800"
                }`}>
                  {nearestDeadline.contract.filename} — {formatDate(nearestDeadline.contract.notice_deadline)}
                </p>
              </div>
              <Link
                href={`/compliance`}
                className="ml-auto flex-shrink-0 text-xs font-semibold underline"
              >
                View in Compliance Tracker
              </Link>
            </div>
          )}

          {/* Latest analysis summary */}
          {latest && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5 mb-6">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Latest Analysis</p>
                  <p className="text-sm font-semibold text-gray-900 mt-1">{latest.filename}</p>
                  <p className="text-xs text-gray-500">{formatDate(latest.analysis_date)}</p>
                </div>
                {latest.deal_score !== null && (
                  <div className={`text-center px-4 py-2 rounded-lg ${
                    latest.deal_score >= 60 ? "bg-emerald-50 text-emerald-700"
                    : latest.deal_score >= 30 ? "bg-amber-50 text-amber-700"
                    : "bg-red-50 text-red-700"
                  }`}>
                    <p className="text-2xl font-bold">{latest.deal_score}</p>
                    <p className="text-[10px] font-semibold uppercase">Deal Score</p>
                  </div>
                )}
              </div>
              {latest.deal_diagnosis && (
                <p className="text-sm text-gray-700 leading-relaxed">{latest.deal_diagnosis}</p>
              )}
              {latest.control_posture_label && (
                <p className="text-xs text-gray-500 mt-2">
                  {latest.control_posture_label} — {latest.control_posture_summary}
                </p>
              )}
              <div className="mt-3">
                <Link href="/contracts" className="text-xs font-semibold text-primary-600 hover:text-primary-800">
                  Open in Plan Intelligence →
                </Link>
              </div>
            </div>
          )}

          {/* All contracts with enrichment status */}
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
            <div className="px-5 py-3 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Your Contracts</h2>
            </div>
            <div className="divide-y divide-gray-100">
              {data!.contracts.map((c) => {
                const deadlineDays = daysUntil(c.notice_deadline);
                return (
                  <Link
                    key={c.id}
                    href={`/contracts?contract_id=${c.id}`}
                    className="flex items-center gap-4 px-5 py-3 hover:bg-gray-50 transition-colors"
                  >
                    <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{c.filename}</p>
                      <div className="flex items-center gap-3 mt-0.5 text-[11px] text-gray-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" />
                          {formatDate(c.analysis_date)}
                        </span>
                        {c.notice_deadline && deadlineDays !== null && (
                          <span className={`font-semibold ${
                            deadlineDays < 0 ? "text-red-600" : deadlineDays <= 30 ? "text-amber-600" : "text-gray-500"
                          }`}>
                            Notice: {formatDate(c.notice_deadline)}
                          </span>
                        )}
                      </div>
                    </div>
                    {/* Enrichment status chips */}
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      {c.has_claims && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200" title="Claims uploaded">
                          <DollarSign className="w-2.5 h-2.5" />
                        </span>
                      )}
                      {c.has_plan_doc && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200" title="Plan document uploaded">
                          <BookOpen className="w-2.5 h-2.5" />
                        </span>
                      )}
                      {c.has_cross_ref && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-purple-50 text-purple-700 border border-purple-200" title="Cross-reference complete">
                          <CheckCircle2 className="w-2.5 h-2.5" />
                        </span>
                      )}
                    </div>
                    {c.deal_score !== null && (
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold flex-shrink-0 ${
                        c.deal_score >= 60 ? "bg-emerald-100 text-emerald-700"
                        : c.deal_score >= 30 ? "bg-amber-100 text-amber-700"
                        : "bg-red-100 text-red-700"
                      }`}>
                        {c.deal_score}/100
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Quick links */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { href: "/contracts", icon: FileText, label: "Plan Intelligence" },
              { href: "/disclosure", icon: Search, label: "Disclosure Review" },
              { href: "/audit", icon: Mail, label: "Audit Letter" },
              { href: "/compliance", icon: CalendarClock, label: "Compliance Tracker" },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href} className="group flex items-center gap-3 p-3 bg-white rounded-xl border border-gray-200/60 hover:border-primary-200 transition-colors">
                  <Icon className="w-4 h-4 text-gray-400 group-hover:text-primary-600 transition-colors" />
                  <p className="text-xs font-medium text-gray-700">{item.label}</p>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
