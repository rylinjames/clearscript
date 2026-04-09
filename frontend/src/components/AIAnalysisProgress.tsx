"use client";

import { useEffect, useState } from "react";
import {
  FileText,
  Search,
  Scale,
  ListChecks,
  Database,
  Sparkles,
  CheckCircle2,
  Loader2,
  Clock,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Long-running AI analysis progress component.
 *
 * The slow AI calls in ClearScript (contract analysis, audit letter,
 * disclosure, plan-doc parser) take 25-50 seconds because gpt-5.4-mini
 * is a reasoning model. A spinner with no context for that long feels
 * broken even when nothing is wrong, and beta testers were bouncing.
 *
 * This component:
 *   - Shows a five-stage pipeline with icons and a progress bar
 *   - Animates the bar on a logarithmic curve so it always feels like
 *     it's moving but never reaches 100% until the real response lands
 *   - Cycles educational tips every ~7 seconds so the user is learning
 *     about PBM economics while they wait
 *   - Displays elapsed time so the user knows the system is alive
 *
 * Usage:
 *   <AIAnalysisProgress
 *     variant="contract"
 *     filename={file.name}
 *     estimatedSeconds={30}
 *   />
 *
 * The component is purely presentational — it has no idea whether the
 * underlying AI call has finished. The parent unmounts it as soon as
 * the response arrives. Stages tied to elapsed time approximate the
 * real backend pipeline; if the AI call returns faster than the
 * estimate, the user just sees a fast progression with no harm done.
 */

type Variant = "contract" | "disclosure" | "audit_letter" | "plan_doc" | "cross_reference";

interface Stage {
  label: string;
  icon: LucideIcon;
  weight: number; // relative duration in arbitrary units
}

const STAGE_PIPELINES: Record<Variant, Stage[]> = {
  contract: [
    { label: "Extracting contract text", icon: FileText, weight: 1 },
    { label: "Identifying rebate, spread, and audit clauses", icon: Search, weight: 4 },
    { label: "Scoring against industry benchmarks", icon: Scale, weight: 4 },
    { label: "Building risk inventory and recommendations", icon: ListChecks, weight: 3 },
    { label: "Persisting analysis to your account", icon: Database, weight: 1 },
  ],
  disclosure: [
    { label: "Extracting disclosure text", icon: FileText, weight: 1 },
    { label: "Checking against DOL-required items", icon: Search, weight: 4 },
    { label: "Scoring completeness", icon: Scale, weight: 3 },
    { label: "Building gap report", icon: ListChecks, weight: 3 },
    { label: "Persisting analysis to your account", icon: Database, weight: 1 },
  ],
  audit_letter: [
    { label: "Loading contract findings", icon: FileText, weight: 1 },
    { label: "Drafting legal citations and demands", icon: Scale, weight: 4 },
    { label: "Building data request schedule", icon: ListChecks, weight: 3 },
    { label: "Composing the letter", icon: Sparkles, weight: 3 },
    { label: "Persisting to your account", icon: Database, weight: 1 },
  ],
  plan_doc: [
    { label: "Extracting plan document text", icon: FileText, weight: 1 },
    { label: "Identifying benefit categories", icon: Search, weight: 4 },
    { label: "Parsing copay, coinsurance, and tier structure", icon: Scale, weight: 4 },
    { label: "Building structured benefit schedule", icon: ListChecks, weight: 2 },
    { label: "Persisting to your account", icon: Database, weight: 1 },
  ],
  cross_reference: [
    { label: "Loading contract and plan document", icon: FileText, weight: 1 },
    { label: "Comparing terms side by side", icon: Search, weight: 4 },
    { label: "Flagging mismatches and gaps", icon: Scale, weight: 4 },
    { label: "Building action items", icon: ListChecks, weight: 2 },
    { label: "Persisting cross-reference to your account", icon: Database, weight: 1 },
  ],
};

// Educational tips that rotate during the wait. Goal: make the user
// smarter about PBMs while they wait. Keep each one to one sentence.
const TIPS = [
  "PBMs retain spread pricing on average 15-20% above pharmacy reimbursement — most contracts don't disclose it.",
  "The DOL transparency rule effective Jan 30, 2026 gives plan sponsors a 10-business-day window to demand audit data.",
  "HR 7148 (signed Feb 3, 2026) requires 100% rebate passthrough — every PBM contract executed before 2028 will need to be renegotiated.",
  "CAA 2021 Section 201 prohibits gag clauses, but most PBM contracts still contain language that arguably violates it.",
  "The average PBM-favorable contract leaks an estimated $420k per year for a 1,000-employee plan.",
  "Audit rights are the single most negotiable lever — most contracts limit them to 'claims data only,' which excludes rebate contracts and pharmacy reimbursement.",
  "MAC pricing transparency is rarely contractually guaranteed — PBMs typically reserve the right to update the MAC list without disclosure.",
  "Specialty pharmacy lock-in clauses force plan sponsors to use the PBM's owned specialty pharmacy, preventing price competition.",
  "ERISA Section 404(a)(1) makes plan fiduciaries personally liable for failing to negotiate prudent PBM contracts.",
  "Schedule C of ERISA Form 5500 requires disclosure of indirect PBM compensation including spread and rebate retention — most PBMs underreport this.",
  "Mid-year formulary changes correlated with rebate incentives are a documented FTC concern — track them carefully.",
  "The Big 3 PBMs (Express Scripts, CVS Caremark, Optum Rx) cover ~80% of US prescriptions — your leverage at renewal depends on credible alternatives.",
  "The FTC's interim PBM report documented spread pricing, rebate retention, and steering at every layer of the supply chain.",
  "Independent pharmacies have been advocating for PBM reform for two decades — the legal landscape is finally catching up with HR 7148.",
  "The 10-business-day audit response deadline from the DOL rule is enforceable — failure to respond is itself evidence of fiduciary breach.",
];

interface AIAnalysisProgressProps {
  variant: Variant;
  filename?: string | null;
  estimatedSeconds?: number;
}

export default function AIAnalysisProgress({
  variant,
  filename,
  estimatedSeconds = 30,
}: AIAnalysisProgressProps) {
  const stages = STAGE_PIPELINES[variant];
  const [elapsedMs, setElapsedMs] = useState(0);
  const [tipIndex, setTipIndex] = useState(() => Math.floor(Math.random() * TIPS.length));

  // Tick the elapsed clock every 100ms for smooth progress bar movement.
  useEffect(() => {
    const start = Date.now();
    const interval = window.setInterval(() => {
      setElapsedMs(Date.now() - start);
    }, 100);
    return () => window.clearInterval(interval);
  }, []);

  // Rotate the educational tip every 7 seconds.
  useEffect(() => {
    const interval = window.setInterval(() => {
      setTipIndex((i) => (i + 1) % TIPS.length);
    }, 7000);
    return () => window.clearInterval(interval);
  }, []);

  // Progress curve: starts fast, slows down asymptotically toward the
  // estimated finish time, never reaches 100% until parent unmounts.
  // Math: progress = 1 - exp(-elapsed / k) where k controls steepness.
  // We tune k so that at the estimated time, progress reaches ~85%.
  const elapsedSec = elapsedMs / 1000;
  const k = estimatedSeconds / 1.9; // -ln(0.15) ≈ 1.9
  const rawProgress = 1 - Math.exp(-elapsedSec / k);
  const cappedProgress = Math.min(rawProgress, 0.97); // never quite hit 100

  // Map progress through the weighted stages to find the active one
  const totalWeight = stages.reduce((sum, s) => sum + s.weight, 0);
  let cumulative = 0;
  let activeStageIndex = 0;
  for (let i = 0; i < stages.length; i++) {
    cumulative += stages[i].weight / totalWeight;
    if (cappedProgress < cumulative) {
      activeStageIndex = i;
      break;
    }
    activeStageIndex = i;
  }

  const elapsedDisplay = formatDuration(elapsedSec);
  const overEstimate = elapsedSec > estimatedSeconds + 5;

  return (
    <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-5">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <Loader2 className="w-5 h-5 text-primary-600 animate-spin flex-shrink-0 mt-0.5" />
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold text-gray-900">
              Analyzing your {variantLabel(variant)}
            </p>
            {filename && (
              <p className="text-sm text-gray-500 mt-0.5 truncate">{filename}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-gray-500 flex-shrink-0">
          <Clock className="w-3.5 h-3.5" />
          {elapsedDisplay}
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-emerald-500 transition-all duration-300 ease-out"
            style={{ width: `${Math.round(cappedProgress * 100)}%` }}
          />
        </div>
        {overEstimate && (
          <p className="text-[11px] text-gray-400 mt-2 italic">
            Taking a little longer than usual — gpt-5 reasoning runs vary by contract length.
          </p>
        )}
      </div>

      {/* Stage list */}
      <div className="space-y-2.5 mb-6">
        {stages.map((stage, i) => {
          const Icon = stage.icon;
          const isActive = i === activeStageIndex && cappedProgress < 0.97;
          const isDone = i < activeStageIndex || cappedProgress >= 0.97;
          return (
            <div
              key={stage.label}
              className={`flex items-center gap-3 transition-all duration-300 ${
                isActive ? "opacity-100" : isDone ? "opacity-100" : "opacity-40"
              }`}
            >
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                  isDone
                    ? "bg-emerald-100 text-emerald-700"
                    : isActive
                    ? "bg-primary-100 text-primary-700"
                    : "bg-gray-100 text-gray-400"
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : isActive ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Icon className="w-3.5 h-3.5" />
                )}
              </div>
              <p
                className={`text-sm flex-1 ${
                  isActive
                    ? "text-gray-900 font-medium"
                    : isDone
                    ? "text-gray-700"
                    : "text-gray-500"
                }`}
              >
                {stage.label}
              </p>
            </div>
          );
        })}
      </div>

      {/* Educational tip */}
      <div className="rounded-lg bg-blue-50 border border-blue-100 p-4">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-blue-700 mb-1 flex items-center gap-1.5">
          <Sparkles className="w-3 h-3" />
          While you wait
        </p>
        <p className="text-sm text-blue-900 leading-relaxed transition-opacity duration-500">
          {TIPS[tipIndex]}
        </p>
      </div>
    </div>
  );
}

function variantLabel(variant: Variant): string {
  switch (variant) {
    case "contract":
      return "PBM contract";
    case "disclosure":
      return "PBM disclosure";
    case "audit_letter":
      return "audit request letter";
    case "plan_doc":
      return "plan document";
    case "cross_reference":
      return "contract vs plan document comparison";
  }
}

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.floor(seconds)}s`;
  }
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s}s`;
}
