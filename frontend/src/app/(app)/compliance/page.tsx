"use client";

import { useState, useEffect } from "react";
import { usePageTitle } from "@/components/PageTitle";
import StatusBadge from "@/components/StatusBadge";
import DataSourceBanner from "@/components/DataSourceBanner";
import { CalendarClock, Loader2, Bell, ChevronDown, ChevronUp } from "lucide-react";

interface Deadline {
  id: string;
  regulation: string;
  description: string;
  dueDate: string;
  daysUntilDue: number;
  status: "upcoming" | "soon" | "urgent";
  actionItems: string[];
  authority: string;
}

const demoDeadlines: Deadline[] = [
  {
    id: "1",
    regulation: "CMS MLR Reporting",
    description: "Medical Loss Ratio reporting for fully-insured plans must be filed with CMS annually.",
    dueDate: "2026-04-15",
    daysUntilDue: 24,
    status: "urgent",
    authority: "Centers for Medicare & Medicaid Services",
    actionItems: ["Compile claims data for reporting period", "Calculate rebate allocation by plan", "Submit via CMS HIOS portal", "Retain records for 10 years"],
  },
  {
    id: "2",
    regulation: "ERISA 5500 Filing",
    description: "Annual return/report of employee benefit plan covering PBM service arrangements.",
    dueDate: "2026-04-30",
    daysUntilDue: 39,
    status: "soon",
    authority: "Department of Labor",
    actionItems: ["Review Schedule A for PBM fees", "Verify Schedule C compensation disclosures", "Obtain PBM attestation letter", "File electronically via EFAST2"],
  },
  {
    id: "3",
    regulation: "PBM Transparency Report (State)",
    description: "State-level PBM transparency reporting requirements for drug pricing and rebate data.",
    dueDate: "2026-06-01",
    daysUntilDue: 71,
    status: "soon",
    authority: "State Department of Insurance",
    actionItems: ["Request data from PBM per state template", "Verify rebate and pricing accuracy", "Submit per state portal instructions"],
  },
  {
    id: "4",
    regulation: "Rx Drug Cost Transparency (CAA)",
    description: "Consolidated Appropriations Act prescription drug cost reporting for group health plans.",
    dueDate: "2026-06-01",
    daysUntilDue: 71,
    status: "soon",
    authority: "HHS / DOL / Treasury",
    actionItems: ["Gather top 50 drugs by cost and utilization", "Prepare D1/D2 data files", "Submit via CMS RxDC portal"],
  },
  {
    id: "5",
    regulation: "Gag Clause Attestation",
    description: "Annual attestation that PBM contract does not contain gag clauses preventing cost disclosure.",
    dueDate: "2026-12-31",
    daysUntilDue: 284,
    status: "upcoming",
    authority: "CMS",
    actionItems: ["Review PBM contract for gag clause provisions", "Confirm compliance with No Surprises Act", "Submit attestation via CMS portal"],
  },
  {
    id: "6",
    regulation: "Mental Health Parity Analysis",
    description: "Comparative analysis of NQTL application between MH/SUD and medical/surgical benefits.",
    dueDate: "2026-07-01",
    daysUntilDue: 101,
    status: "upcoming",
    authority: "Department of Labor",
    actionItems: ["Analyze prior auth rates by benefit classification", "Compare step therapy requirements", "Document quantitative and non-quantitative treatment limitations", "Prepare comparative analysis report"],
  },
  {
    id: "7",
    regulation: "ACA Preventive Services Update",
    description: "Review formulary compliance with updated USPSTF preventive service recommendations.",
    dueDate: "2027-01-01",
    daysUntilDue: 285,
    status: "upcoming",
    authority: "HHS",
    actionItems: ["Review USPSTF A and B recommendations", "Verify formulary covers required preventive drugs at $0 cost-sharing", "Update formulary if needed"],
  },
];

export default function CompliancePage() {
  usePageTitle("Compliance Tracker");
  const [loading, setLoading] = useState(true);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("/api/compliance/deadlines");
        if (!res.ok) throw new Error();
        const data = await res.json();
        if (data?.deadlines?.length && data.deadlines[0].deadline) {
          setDeadlines(data.deadlines.map((d: Record<string, unknown>) => ({
            id: d.id as string,
            regulation: (d.name || d.regulation) as string,
            description: d.description as string,
            dueDate: d.deadline as string,
            daysUntilDue: d.days_until as number,
            status: (d.days_until as number) < 30 ? "urgent" : (d.days_until as number) < 90 ? "soon" : "upcoming",
            authority: d.authority as string,
            actionItems: typeof d.action_required === "string" ? [d.action_required as string] : (d.actionItems || []) as string[],
          })));
        } else {
          setDeadlines(data?.deadlines || demoDeadlines);
        }
      } catch {
        setDeadlines(demoDeadlines);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        <p className="text-sm text-gray-500">Loading compliance deadlines...</p>
      </div>
    );
  }

  const urgent = deadlines.filter((d) => d.daysUntilDue < 30);
  const soon = deadlines.filter((d) => d.daysUntilDue >= 30 && d.daysUntilDue <= 90);
  const upcoming = deadlines.filter((d) => d.daysUntilDue > 90);

  function getStatusColor(days: number) {
    if (days < 30) return { bg: "bg-red-50 border-red-200", dot: "bg-red-500", text: "text-red-700" };
    if (days <= 90) return { bg: "bg-amber-50 border-amber-200", dot: "bg-amber-500", text: "text-amber-700" };
    return { bg: "bg-emerald-50 border-emerald-200", dot: "bg-emerald-500", text: "text-emerald-700" };
  }

  function DeadlineCard({ deadline }: { deadline: Deadline }) {
    const colors = getStatusColor(deadline.daysUntilDue);
    const isExpanded = expandedId === deadline.id;

    return (
      <div className={`rounded-xl border ${colors.bg} overflow-hidden`}>
        <button
          onClick={() => setExpandedId(isExpanded ? null : deadline.id)}
          className="w-full p-5 text-left flex items-start justify-between gap-4"
        >
          <div className="flex items-start gap-3">
            <div className={`w-3 h-3 rounded-full ${colors.dot} mt-1 flex-shrink-0`} />
            <div>
              <h4 className="text-sm font-semibold text-gray-900">{deadline.regulation}</h4>
              <p className="text-xs text-gray-500 mt-0.5">{deadline.authority}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="text-right">
              <p className={`text-sm font-bold ${colors.text}`}>
                {deadline.daysUntilDue} days
              </p>
              <p className="text-xs text-gray-500">Due {deadline.dueDate}</p>
            </div>
            {deadline.daysUntilDue < 30 && (
              <Bell className="w-4 h-4 text-red-500 animate-pulse" />
            )}
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </div>
        </button>

        {isExpanded && (
          <div className="px-5 pb-5 border-t border-gray-200/50">
            <p className="text-sm text-gray-600 mt-4 mb-3">{deadline.description}</p>
            <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Action Items
            </h5>
            <ul className="space-y-1.5">
              {deadline.actionItems.map((item, i) => (
                <li key={i} className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-gray-400 mt-1.5 flex-shrink-0" />
                  <span className="text-sm text-gray-700">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <CalendarClock className="w-7 h-7 text-primary-600" />
          Compliance Deadline Tracker
        </h1>
        <p className="text-gray-500 mt-1">
          Track regulatory filing deadlines and compliance requirements
        </p>
      </div>

      <DataSourceBanner />

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-red-700">{urgent.length}</p>
          <p className="text-sm text-red-600">Urgent (&lt;30 days)</p>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-amber-700">{soon.length}</p>
          <p className="text-sm text-amber-600">Soon (30-90 days)</p>
        </div>
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-emerald-700">{upcoming.length}</p>
          <p className="text-sm text-emerald-600">Upcoming (&gt;90 days)</p>
        </div>
      </div>

      {urgent.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-red-700 mb-3 uppercase tracking-wider flex items-center gap-2">
            <Bell className="w-4 h-4" /> Urgent — Due Within 30 Days
          </h3>
          <div className="space-y-3">
            {urgent.map((d) => <DeadlineCard key={d.id} deadline={d} />)}
          </div>
        </div>
      )}

      {soon.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-amber-700 mb-3 uppercase tracking-wider">
            Due Within 30-90 Days
          </h3>
          <div className="space-y-3">
            {soon.map((d) => <DeadlineCard key={d.id} deadline={d} />)}
          </div>
        </div>
      )}

      {upcoming.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-emerald-700 mb-3 uppercase tracking-wider">
            Upcoming — More Than 90 Days
          </h3>
          <div className="space-y-3">
            {upcoming.map((d) => <DeadlineCard key={d.id} deadline={d} />)}
          </div>
        </div>
      )}
    </div>
  );
}
