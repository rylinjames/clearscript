"use client";

import Link from "next/link";
import { Show, SignInButton, SignUpButton } from "@clerk/nextjs";
import {
  ShieldCheck,
  FileText,
  Search,
  CheckCircle2,
  ArrowRight,
  Zap,
  Lock,
  BarChart3,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* ─── Nav ─── */}
      <nav className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="w-7 h-7 text-emerald-500" />
          <span className="text-lg font-bold text-gray-900 tracking-tight">ClearScript</span>
        </div>
        <div className="flex items-center gap-3">
          <Show when="signed-out">
            <SignInButton mode="modal">
              <button className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors px-4 py-2">
                Sign in
              </button>
            </SignInButton>
            <SignUpButton mode="modal">
              <button className="text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 transition-colors px-4 py-2 rounded-lg">
                Get Started
              </button>
            </SignUpButton>
          </Show>
          <Show when="signed-in">
            <Link
              href="/dashboard"
              className="text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 transition-colors px-4 py-2 rounded-lg"
            >
              Open Dashboard
            </Link>
          </Show>
        </div>
      </nav>

      {/* ─── Hero ─── */}
      <section className="max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium mb-6">
          <Zap className="w-3 h-3" />
          HR 7148 compliance tools — ready for July 2026
        </div>

        <h1 className="text-5xl sm:text-6xl font-bold text-gray-900 tracking-tight leading-[1.1]">
          PBM audit,<br />simplified.
        </h1>

        <p className="text-lg text-gray-500 mt-6 max-w-xl mx-auto leading-relaxed">
          Upload your PBM contract. Get an AI-powered compliance analysis with risk scoring, audit rights grading, and a ready-to-send audit letter — in under 60 seconds.
        </p>

        <div className="flex items-center justify-center gap-4 mt-10">
          <Show when="signed-out">
            <SignUpButton mode="modal">
              <button className="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors shadow-sm">
                Start Free
                <ArrowRight className="w-4 h-4" />
              </button>
            </SignUpButton>
          </Show>
          <Show when="signed-in">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors shadow-sm"
            >
              Open Dashboard
              <ArrowRight className="w-4 h-4" />
            </Link>
          </Show>
          <Link
            href="#how-it-works"
            className="px-6 py-3 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
          >
            See how it works
          </Link>
        </div>
      </section>

      {/* ─── Social Proof ─── */}
      <section className="max-w-4xl mx-auto px-6 pb-16">
        <div className="flex items-center justify-center gap-8 text-sm text-gray-400">
          <span>Built on real CMS data</span>
          <span className="w-1 h-1 rounded-full bg-gray-300" />
          <span>388K+ drug prices</span>
          <span className="w-1 h-1 rounded-full bg-gray-300" />
          <span>Powered by Gemini AI</span>
        </div>
      </section>

      {/* ─── How it Works ─── */}
      <section id="how-it-works" className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-gray-900 text-center tracking-tight mb-4">
          Three steps to a defensible audit
        </h2>
        <p className="text-gray-500 text-center max-w-lg mx-auto mb-14">
          Upload your documents. AI does the analysis. You get a report your CFO can act on.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {[
            {
              step: "1",
              icon: FileText,
              title: "Upload Contract",
              desc: "Upload your PBM contract PDF. AI extracts rebate terms, spread pricing, audit rights, MAC pricing, termination provisions, and gag clauses.",
            },
            {
              step: "2",
              icon: Search,
              title: "AI Analysis",
              desc: "Get a risk score (0-100), 11-point audit rights scorecard, compliance flags by severity, and identification of narrow rebate definitions.",
            },
            {
              step: "3",
              icon: BarChart3,
              title: "Export Report",
              desc: "Download a branded PDF report with executive summary, findings, and a draft audit letter citing ERISA, CAA, and DOL provisions.",
            },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.step}
                className="relative flex flex-col p-7 bg-white rounded-2xl border border-gray-200/60 shadow-[var(--shadow-card)]"
              >
                <div className="flex items-center gap-3 mb-4">
                  <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-primary-50 text-primary-600 text-sm font-bold">
                    {item.step}
                  </span>
                  <Icon className="w-5 h-5 text-gray-400" />
                </div>
                <h3 className="text-base font-semibold text-gray-900 mb-2">{item.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ─── What You Get ─── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-gray-900 text-center tracking-tight mb-14">
          What the report covers
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            "Rebate passthrough percentage and definition analysis",
            "Spread pricing detection and prohibition status",
            "11-point audit rights scorecard (FOUND / MISSING)",
            "Formulary change notification terms",
            "MAC pricing transparency assessment",
            "Termination provisions and early exit fees",
            "Gag clause and confidentiality restrictions",
            "Compliance flags with severity (HIGH / MEDIUM / LOW)",
            "Plan document cross-reference (SBC/SPD/EOC)",
            "Draft audit request letter with legal citations",
            "Compliance deadline tracker (HR 7148, DOL, state bills)",
            "Downloadable PDF report for board presentation",
          ].map((item) => (
            <div key={item} className="flex items-start gap-3 py-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
              <span className="text-sm text-gray-700">{item}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Trust ─── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <div className="bg-white rounded-2xl border border-gray-200/60 shadow-[var(--shadow-card)] p-10 text-center">
          <Lock className="w-8 h-8 text-gray-300 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-gray-900 mb-2">Your data stays yours</h3>
          <p className="text-sm text-gray-500 max-w-md mx-auto leading-relaxed">
            ClearScript works from publicly available CMS data sources. Your uploaded contracts are processed by AI and never stored beyond your session. We don&apos;t use confidential client data unless you upload it yourself.
          </p>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-3xl font-bold text-gray-900 tracking-tight mb-4">
          Ready to audit your PBM contract?
        </h2>
        <p className="text-gray-500 mb-8">
          Free to start. No credit card required.
        </p>
        <Show when="signed-out">
          <SignUpButton mode="modal">
            <button className="inline-flex items-center gap-2 px-8 py-3.5 bg-primary-600 text-white rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors shadow-sm">
              Get Started Free
              <ArrowRight className="w-4 h-4" />
            </button>
          </SignUpButton>
        </Show>
        <Show when="signed-in">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-8 py-3.5 bg-primary-600 text-white rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors shadow-sm"
          >
            Open Dashboard
            <ArrowRight className="w-4 h-4" />
          </Link>
        </Show>
      </section>

      {/* ─── Footer ─── */}
      <footer className="max-w-6xl mx-auto px-6 py-8 border-t border-gray-200/60">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            <span>ClearScript</span>
          </div>
          <span>&copy; 2026 Hikaflow, Inc.</span>
        </div>
      </footer>
    </div>
  );
}
