"use client";

import { useState, useEffect, useCallback } from "react";
import { usePageTitle } from "@/components/PageTitle";
import MetricCard from "@/components/MetricCard";
import StatusBadge from "@/components/StatusBadge";
import { useToast } from "@/components/Toast";
import {
  Loader2,
  CalendarClock,
  Milestone,
  AlertTriangle,
  Shield,
  Clock,
  Send,
} from "lucide-react";

interface TimelineMilestone {
  name: string;
  date: string;
  description: string;
  delayTactics: string[];
  riskLevel: "critical" | "warning" | "info" | "good";
}

interface TemplateData {
  milestones: TimelineMilestone[];
  riskFactors: { label: string; status: string }[];
  totalDurationDays: number;
  criticalDeadlines: number;
}

interface FormValues {
  planYearEndDate: string;
  pbmResponseDeadline: string;
  noticePeriod: string;
}

function normalizeTimelinePayload(payload: unknown): TemplateData | null {
  const source = payload && typeof payload === "object" && "timeline" in payload
    ? (payload as { timeline?: Record<string, unknown> }).timeline
    : payload;

  if (!source || typeof source !== "object") {
    return null;
  }

  const timeline = source as Record<string, unknown>;
  const milestones = Array.isArray(timeline.milestones)
    ? timeline.milestones.map((item) => {
        const milestone = item as Record<string, unknown>;
        const riskLevel = milestone.risk_level;
        return {
          name: String(milestone.name || ""),
          date: String(milestone.date || ""),
          description: String(milestone.description || ""),
          delayTactics: Array.isArray(milestone.delay_tactics)
            ? milestone.delay_tactics.map((tactic) => String(tactic))
            : [],
          riskLevel: (riskLevel === "critical" || riskLevel === "warning" || riskLevel === "good"
            ? riskLevel
            : "info") as TimelineMilestone["riskLevel"],
        };
      })
    : [];
  const riskFactors = Array.isArray(timeline.risk_factors)
    ? timeline.risk_factors.map((item) => {
        const factor = item as Record<string, unknown>;
        return {
          label: String(factor.label || ""),
          status: String(factor.status || "info"),
        };
      })
    : [];

  return {
    milestones,
    riskFactors,
    totalDurationDays: Number(timeline.total_duration_days || 0),
    criticalDeadlines: milestones.filter((milestone) => milestone.riskLevel === "critical").length,
  };
}

export default function AuditTimelinePage() {
  const { toast } = useToast();
  usePageTitle("Audit Timeline");
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<TemplateData | null>(null);
  const [generating, setGenerating] = useState(false);
  const [form, setForm] = useState<FormValues>({
    planYearEndDate: "",
    pbmResponseDeadline: "",
    noticePeriod: "90",
  });

  const fetchTemplate = useCallback(async () => {
    try {
      const res = await fetch("/api/audit-timeline/template");
      if (res.ok) {
        setData(normalizeTimelinePayload(await res.json()));
      }
    } catch {
      /* silent */
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const planYearEnd = form.planYearEndDate || "2025-12-31";
      const responseDeadlineDays = form.pbmResponseDeadline && form.planYearEndDate
        ? Math.max(
            1,
            Math.round(
              (new Date(form.pbmResponseDeadline).getTime() - new Date(form.planYearEndDate).getTime()) /
                (1000 * 60 * 60 * 24)
            )
          )
        : 30;
      const res = await fetch("/api/audit-timeline/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan_year_end: planYearEnd,
          notice_requirement_days: Number(form.noticePeriod) || 90,
          response_deadline_days: responseDeadlineDays,
        }),
      });
      if (res.ok) {
        setData(normalizeTimelinePayload(await res.json()));
        toast("Custom timeline generated", "success");
      } else {
        toast("Failed to generate timeline", "error");
      }
    } catch {
      toast("Failed to generate timeline", "error");
    }
    setGenerating(false);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        <p className="text-sm text-gray-500">Loading audit timeline...</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <CalendarClock className="w-7 h-7 text-primary-600" />
          Audit Timeline Planner
        </h1>
        <p className="text-gray-500 mt-1">
          Plan your PBM audit milestones and identify delay tactics to watch for
        </p>
      </div>

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <MetricCard icon={Milestone} label="Total Milestones" value={String(data.milestones.length)} color="blue" />
          <MetricCard icon={Clock} label="Total Duration (Days)" value={String(data.totalDurationDays)} color="amber" />
          <MetricCard icon={AlertTriangle} label="Critical Deadlines" value={String(data.criticalDeadlines)} color="red" />
        </div>
      )}

      {/* Customize Form */}
      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
          Customize Timeline
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Plan Year End Date</label>
            <input
              type="date"
              value={form.planYearEndDate}
              onChange={(e) => setForm({ ...form, planYearEndDate: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">PBM Response Deadline</label>
            <input
              type="date"
              value={form.pbmResponseDeadline}
              onChange={(e) => setForm({ ...form, pbmResponseDeadline: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notice Period (days)</label>
            <input
              type="number"
              value={form.noticePeriod}
              onChange={(e) => setForm({ ...form, noticePeriod: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
            />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium disabled:opacity-50"
          >
            {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Generate Custom Timeline
          </button>
        </div>
      </div>

      {/* Risk Factors */}
      {data?.riskFactors && data.riskFactors.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary-600" />
            Risk Factors
          </h3>
          <div className="flex flex-wrap gap-2">
            {data.riskFactors.map((rf, i) => (
              <StatusBadge key={i} status={rf.status} label={rf.label} />
            ))}
          </div>
        </div>
      )}

      {/* Vertical Timeline */}
      {data?.milestones && (
        <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-6 uppercase tracking-wider">
            Milestone Timeline
          </h3>
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />
            <div className="space-y-6">
              {data.milestones.map((ms, i) => (
                <div key={i} className="relative pl-10">
                  <div
                    className={`absolute left-2.5 top-1.5 w-3 h-3 rounded-full border-2 border-white ${
                      ms.riskLevel === "critical"
                        ? "bg-red-500"
                        : ms.riskLevel === "warning"
                        ? "bg-amber-500"
                        : ms.riskLevel === "good"
                        ? "bg-emerald-500"
                        : "bg-blue-500"
                    }`}
                  />
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-semibold text-gray-900">{ms.name}</span>
                      <span className="text-xs font-mono text-gray-400">{ms.date}</span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{ms.description}</p>
                    {ms.delayTactics.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-amber-700 mb-1">Delay Tactics to Watch:</p>
                        <ul className="text-xs text-amber-600 list-disc list-inside space-y-0.5">
                          {ms.delayTactics.map((tactic, j) => (
                            <li key={j}>{tactic}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
