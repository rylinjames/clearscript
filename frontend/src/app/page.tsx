"use client";

import Link from "next/link";
import MetricCard from "@/components/MetricCard";
import StatusBadge from "@/components/StatusBadge";
import {
  DollarSign,
  ShieldCheck,
  ClipboardList,
  CalendarClock,
  FileText,
  Search,
  TrendingUp,
  Mail,
  MapPin,
  Pill,
  BarChart3,
  ArrowRight,
} from "lucide-react";

const quickActions = [
  { href: "/contracts", label: "Upload Contract", icon: FileText, color: "bg-blue-600" },
  { href: "/disclosure", label: "Analyze Disclosure", icon: Search, color: "bg-indigo-600" },
  { href: "/reports", label: "Audit Reports", icon: ClipboardList, color: "bg-violet-600" },
  { href: "/rebates", label: "Track Rebates", icon: DollarSign, color: "bg-emerald-600" },
  { href: "/spread", label: "Detect Spread", icon: TrendingUp, color: "bg-amber-600" },
  { href: "/audit", label: "Generate Audit", icon: Mail, color: "bg-rose-600" },
  { href: "/network", label: "Network Check", icon: MapPin, color: "bg-teal-600" },
  { href: "/formulary", label: "Formulary Scan", icon: Pill, color: "bg-purple-600" },
  { href: "/benchmarks", label: "Benchmarks", icon: BarChart3, color: "bg-cyan-600" },
  { href: "/compliance", label: "Compliance", icon: CalendarClock, color: "bg-orange-600" },
];

const recentActivity = [
  { time: "2 hours ago", text: "Contract audit completed for Acme Corp PBM agreement", type: "good" as const },
  { time: "5 hours ago", text: "Spread pricing alert: $1.2M excess spread detected in Q4 claims", type: "critical" as const },
  { time: "Yesterday", text: "Rebate passthrough analysis showed 12% leakage for OptumRx", type: "warning" as const },
  { time: "Yesterday", text: "Compliance deadline: CMS MLR reporting due in 28 days", type: "warning" as const },
  { time: "2 days ago", text: "Network adequacy scan passed for 94% of zip codes", type: "good" as const },
  { time: "3 days ago", text: "Formulary change detected: 14 brand-to-brand swaps flagged", type: "critical" as const },
];

export default function Dashboard() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">
          Overview of your PBM audit and compliance posture
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          icon={DollarSign}
          label="Total Savings Identified"
          value="$4.2M"
          trend="18% vs last quarter"
          trendUp={true}
          color="green"
        />
        <MetricCard
          icon={ShieldCheck}
          label="Compliance Score"
          value="87%"
          trend="3% improvement"
          trendUp={true}
          color="blue"
        />
        <MetricCard
          icon={ClipboardList}
          label="Active Audits"
          value="12"
          trend="4 new this month"
          trendUp={true}
          color="amber"
        />
        <MetricCard
          icon={CalendarClock}
          label="Upcoming Deadlines"
          value="5"
          trend="2 within 30 days"
          trendUp={false}
          color="red"
        />
      </div>

      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {quickActions.map((action) => {
            const Icon = action.icon;
            return (
              <Link
                key={action.href}
                href={action.href}
                className="flex flex-col items-center gap-2 p-4 bg-white rounded-xl border border-gray-200 hover:shadow-md hover:border-[#1e3a5f]/30 transition-all group"
              >
                <div
                  className={`${action.color} text-white rounded-lg p-2.5 group-hover:scale-110 transition-transform`}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <span className="text-xs font-medium text-gray-700 text-center">
                  {action.label}
                </span>
              </Link>
            );
          })}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Recent Activity
          </h2>
          <Link
            href="/reports"
            className="text-sm text-[#1e3a5f] hover:underline flex items-center gap-1"
          >
            View all <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        <div className="divide-y divide-gray-100">
          {recentActivity.map((item, i) => (
            <div key={i} className="flex items-start gap-4 py-3">
              <span className="text-xs text-gray-400 w-24 flex-shrink-0 pt-0.5">
                {item.time}
              </span>
              <p className="text-sm text-gray-700 flex-1">{item.text}</p>
              <StatusBadge status={item.type} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
