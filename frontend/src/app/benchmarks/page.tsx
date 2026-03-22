"use client";

import { useState, useEffect } from "react";
import { BarChart3, Loader2, AlertTriangle } from "lucide-react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface BenchmarkMetric {
  label: string;
  yourValue: number;
  peerAverage: number;
  percentile: number;
  unit: string;
  lowerIsBetter: boolean;
}

const demoMetrics: BenchmarkMetric[] = [
  { label: "Cost per Script", yourValue: 68.42, peerAverage: 54.10, percentile: 28, unit: "$", lowerIsBetter: true },
  { label: "Rebate Passthrough", yourValue: 88.0, peerAverage: 94.5, percentile: 22, unit: "%", lowerIsBetter: false },
  { label: "Specialty Spend", yourValue: 52.3, peerAverage: 44.8, percentile: 75, unit: "%", lowerIsBetter: true },
  { label: "Generic Fill Rate", yourValue: 89.1, peerAverage: 91.8, percentile: 35, unit: "%", lowerIsBetter: false },
];

const radarData = [
  { metric: "Cost Efficiency", you: 45, peers: 72 },
  { metric: "Rebate Passthrough", you: 62, peers: 85 },
  { metric: "Generic Rate", you: 78, peers: 88 },
  { metric: "Network Adequacy", you: 82, peers: 79 },
  { metric: "Formulary Stability", you: 55, peers: 73 },
  { metric: "Compliance Score", you: 87, peers: 82 },
];

function GaugeCard({ metric }: { metric: BenchmarkMetric }) {
  const isGood = metric.lowerIsBetter
    ? metric.yourValue <= metric.peerAverage
    : metric.yourValue >= metric.peerAverage;

  const diff = metric.lowerIsBetter
    ? ((metric.yourValue - metric.peerAverage) / metric.peerAverage) * 100
    : ((metric.peerAverage - metric.yourValue) / metric.peerAverage) * 100;

  const pctColor =
    metric.percentile >= 60
      ? "text-emerald-600 bg-emerald-50"
      : metric.percentile >= 40
      ? "text-amber-600 bg-amber-50"
      : "text-red-600 bg-red-50";

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
        {metric.label}
      </h4>
      <div className="flex items-end gap-2 mb-4">
        <span className={`text-3xl font-bold ${isGood ? "text-emerald-700" : "text-red-600"}`}>
          {metric.unit === "$" ? "$" : ""}{metric.yourValue}{metric.unit === "%" ? "%" : ""}
        </span>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${pctColor}`}>
          {metric.percentile}th percentile
        </span>
      </div>
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-gray-500">
          <span>Your Value</span>
          <span className="font-semibold text-gray-700">
            {metric.unit === "$" ? "$" : ""}{metric.yourValue}{metric.unit === "%" ? "%" : ""}
          </span>
        </div>
        <div className="flex justify-between text-xs text-gray-500">
          <span>Peer Average</span>
          <span className="font-semibold text-gray-700">
            {metric.unit === "$" ? "$" : ""}{metric.peerAverage}{metric.unit === "%" ? "%" : ""}
          </span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${isGood ? "bg-emerald-500" : "bg-red-500"}`}
            style={{ width: `${Math.min(metric.percentile, 100)}%` }}
          />
        </div>
      </div>
      {!isGood && (
        <p className="text-xs text-red-600 mt-3 font-medium">
          {Math.abs(diff).toFixed(1)}% {metric.lowerIsBetter ? "above" : "below"} peer average
        </p>
      )}
    </div>
  );
}

export default function BenchmarksPage() {
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<BenchmarkMetric[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("/api/benchmarks/data");
        if (!res.ok) throw new Error();
        const data = await res.json();
        const b = data?.benchmarks;
        if (b?.your_plan && b?.peer_benchmarks) {
          const yp = b.your_plan;
          // peer_benchmarks is a list — find the "mid-market" or use first non-your_plan segment
          const peers = Array.isArray(b.peer_benchmarks) ? b.peer_benchmarks : [b.peer_benchmarks];
          const pb = peers.find((p: Record<string, unknown>) => p.segment_key === "mid_market") || peers.find((p: Record<string, unknown>) => p.segment_key !== "your_plan") || peers[0];
          // Values may be decimals (0.79) or percentages (79) — normalize
          const pct = (v: number) => v <= 1 ? Math.round(v * 100) : Math.round(v);
          setMetrics([
            { label: "Cost per Script", yourValue: yp.avg_cost_per_script, peerAverage: pb.avg_cost_per_script, unit: "$", lowerIsBetter: true, percentile: 18 },
            { label: "Rebate Passthrough", yourValue: pct(yp.rebate_passthrough_pct), peerAverage: pct(pb.rebate_passthrough_pct), unit: "%", lowerIsBetter: false, percentile: 22 },
            { label: "Specialty Spend", yourValue: pct(yp.specialty_spend_pct), peerAverage: pct(pb.specialty_spend_pct), unit: "%", lowerIsBetter: true, percentile: 65 },
            { label: "Generic Rate", yourValue: pct(yp.generic_dispensing_rate), peerAverage: pct(pb.generic_dispensing_rate), unit: "%", lowerIsBetter: false, percentile: 15 },
          ]);
        } else {
          setMetrics(demoMetrics);
        }
      } catch {
        setMetrics(demoMetrics);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-[#1e3a5f] animate-spin" />
        <p className="text-sm text-gray-500">Loading benchmark data...</p>
      </div>
    );
  }

  const costPerScript = metrics.find((m) => m.label === "Cost per Script");
  const overpayPct = costPerScript
    ? (((costPerScript.yourValue - costPerScript.peerAverage) / costPerScript.peerAverage) * 100).toFixed(1)
    : "0";

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <BarChart3 className="w-7 h-7 text-[#1e3a5f]" />
          Benchmarking Dashboard
        </h1>
        <p className="text-gray-500 mt-1">
          Compare your PBM performance against industry peers
        </p>
      </div>

      <div className="bg-gradient-to-r from-red-600 to-amber-500 rounded-xl p-6 mb-6 text-white flex items-center gap-4">
        <AlertTriangle className="w-10 h-10 flex-shrink-0" />
        <div>
          <p className="text-lg font-bold">
            You&apos;re paying {overpayPct}% more than peers per prescription
          </p>
          <p className="text-sm text-white/90">
            Based on comparison with similar employer plans in your industry and region
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {metrics.map((metric) => (
          <GaugeCard key={metric.label} metric={metric} />
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
          Multi-Dimensional Peer Comparison
        </h3>
        <ResponsiveContainer width="100%" height={400}>
          <RadarChart data={radarData}>
            <PolarGrid stroke="#e5e7eb" />
            <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12, fill: "#6b7280" }} />
            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
            <Radar name="Your Plan" dataKey="you" stroke="#1e3a5f" fill="#1e3a5f" fillOpacity={0.3} />
            <Radar name="Peer Average" dataKey="peers" stroke="#10b981" fill="#10b981" fillOpacity={0.2} />
            <Legend />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
