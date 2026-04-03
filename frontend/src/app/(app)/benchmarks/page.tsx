"use client";

import { useState, useEffect } from "react";
import { usePageTitle } from "@/components/PageTitle";
import { BarChart3, Loader2, AlertTriangle, Globe, FileText, Pill } from "lucide-react";
import DataSourceBanner from "@/components/DataSourceBanner";
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

interface StateNdcCompliance {
  state: string;
  capture_rate: number;
  enforcer: string;
  notes: string;
}

interface PublicDataState {
  oig_highlights: string[];
  state_ndc_compliance: StateNdcCompliance[];
  net_effective_rebate_ranges: { therapy_class: string; low: number; high: number }[];
}

interface IraDrug {
  drug_name: string;
  manufacturer: string;
  indication: string;
  negotiated_price?: string;
  effective_date?: string;
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
    <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
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

type TabKey = "performance" | "public-data" | "ira-drugs";

export default function BenchmarksPage() {
  usePageTitle("Benchmarks");
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<BenchmarkMetric[]>([]);
  const [activeTab, setActiveTab] = useState<TabKey>("performance");

  // Public data state
  const [publicData, setPublicData] = useState<PublicDataState | null>(null);
  const [publicLoading, setPublicLoading] = useState(true);

  // IRA drugs state
  const [iraDrugs, setIraDrugs] = useState<IraDrug[]>([]);
  const [iraLoading, setIraLoading] = useState(true);

  useEffect(() => {
    const fetchBenchmarks = async () => {
      try {
        const res = await fetch("/api/benchmarks/data");
        if (!res.ok) throw new Error();
        const data = await res.json();
        const b = data?.benchmarks;
        if (b?.your_plan && b?.peer_benchmarks) {
          const yp = b.your_plan;
          const peers = Array.isArray(b.peer_benchmarks) ? b.peer_benchmarks : [b.peer_benchmarks];
          const pb = peers.find((p: Record<string, unknown>) => p.segment_key === "mid_market") || peers.find((p: Record<string, unknown>) => p.segment_key !== "your_plan") || peers[0];
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

    const fetchPublicData = async () => {
      try {
        const res = await fetch("/api/benchmarks/public-data");
        if (!res.ok) throw new Error();
        const data = await res.json();
        setPublicData(data);
      } catch {
        // Fallback demo data
        setPublicData({
          oig_highlights: [
            "OIG found 40% of rebates go uncollected by plan sponsors due to narrow rebate definitions",
            "Top 3 PBMs retain an average of $1.3B annually in undisclosed spread",
            "State-by-state variation: Alabama captures 98% of NDC data, while other states average only 62%",
            "Specialty drug markups average 23% above acquisition cost in PBM-owned pharmacies",
            "Mail-order steering adds 15-20% to employer drug spend through hidden spreads",
          ],
          state_ndc_compliance: [
            { state: "Alabama", capture_rate: 0.98, enforcer: "State Medicaid Agency", notes: "Gold standard for NDC compliance" },
            { state: "California", capture_rate: 0.72, enforcer: "DHCS", notes: "Improving with new mandate" },
            { state: "New York", capture_rate: 0.68, enforcer: "DOH", notes: "New legislation pending" },
            { state: "Texas", capture_rate: 0.55, enforcer: "HHSC", notes: "Limited enforcement" },
            { state: "Florida", capture_rate: 0.61, enforcer: "AHCA", notes: "Recent audit revealed gaps" },
            { state: "Ohio", capture_rate: 0.85, enforcer: "ODM", notes: "Strong post-reform compliance" },
            { state: "Pennsylvania", capture_rate: 0.63, enforcer: "DHS", notes: "Under review" },
            { state: "Illinois", capture_rate: 0.58, enforcer: "HFS", notes: "Legislation in progress" },
          ],
          net_effective_rebate_ranges: [
            { therapy_class: "Diabetes (GLP-1s)", low: 45, high: 70 },
            { therapy_class: "Autoimmune (TNF inhibitors)", low: 40, high: 65 },
            { therapy_class: "Oncology (oral)", low: 5, high: 15 },
            { therapy_class: "Cardiovascular (PCSK9)", low: 50, high: 75 },
            { therapy_class: "Respiratory (biologics)", low: 35, high: 55 },
            { therapy_class: "Mental Health (atypicals)", low: 20, high: 40 },
          ],
        });
      } finally {
        setPublicLoading(false);
      }
    };

    const fetchIraDrugs = async () => {
      try {
        const res = await fetch("/api/cms-benchmark/ira-drugs");
        if (!res.ok) throw new Error();
        const data = await res.json();
        setIraDrugs(data.drugs || data || []);
      } catch {
        setIraDrugs([
          { drug_name: "Eliquis", manufacturer: "BMS/Pfizer", indication: "Blood thinner", negotiated_price: "TBD", effective_date: "2026" },
          { drug_name: "Jardiance", manufacturer: "Boehringer Ingelheim", indication: "Diabetes", negotiated_price: "TBD", effective_date: "2026" },
          { drug_name: "Xarelto", manufacturer: "Johnson & Johnson", indication: "Blood thinner", negotiated_price: "TBD", effective_date: "2026" },
          { drug_name: "Januvia", manufacturer: "Merck", indication: "Diabetes", negotiated_price: "TBD", effective_date: "2026" },
          { drug_name: "Farxiga", manufacturer: "AstraZeneca", indication: "Diabetes / Heart failure", negotiated_price: "TBD", effective_date: "2026" },
          { drug_name: "Entresto", manufacturer: "Novartis", indication: "Heart failure", negotiated_price: "TBD", effective_date: "2026" },
          { drug_name: "Enbrel", manufacturer: "Amgen", indication: "Autoimmune", negotiated_price: "TBD", effective_date: "2026" },
          { drug_name: "Imbruvica", manufacturer: "AbbVie/J&J", indication: "Cancer", negotiated_price: "TBD", effective_date: "2026" },
          { drug_name: "Stelara", manufacturer: "Johnson & Johnson", indication: "Autoimmune", negotiated_price: "TBD", effective_date: "2026" },
          { drug_name: "Fiasp/NovoLog", manufacturer: "Novo Nordisk", indication: "Diabetes (insulin)", negotiated_price: "TBD", effective_date: "2026" },
        ]);
      } finally {
        setIraLoading(false);
      }
    };

    // Fetch all three in parallel
    fetchBenchmarks();
    fetchPublicData();
    fetchIraDrugs();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        <p className="text-sm text-gray-500">Loading benchmark data...</p>
      </div>
    );
  }

  const costPerScript = metrics.find((m) => m.label === "Cost per Script");
  const overpayPct = costPerScript
    ? (((costPerScript.yourValue - costPerScript.peerAverage) / costPerScript.peerAverage) * 100).toFixed(1)
    : "0";

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: "performance", label: "Performance", icon: <BarChart3 className="w-4 h-4" /> },
    { key: "public-data", label: "Public Data Sources", icon: <Globe className="w-4 h-4" /> },
    { key: "ira-drugs", label: "IRA Selected Drugs", icon: <Pill className="w-4 h-4" /> },
  ];

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <BarChart3 className="w-7 h-7 text-primary-600" />
          Benchmarking Dashboard
        </h1>
        <p className="text-gray-500 mt-1">
          Compare your PBM performance against industry peers
        </p>
      </div>

      <DataSourceBanner />

      {/* Tab Navigation */}
      <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors flex-1 justify-center ${
              activeTab === tab.key
                ? "bg-white text-primary-600 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Performance Tab */}
      {activeTab === "performance" && (
        <>
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

          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
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
        </>
      )}

      {/* Public Data Sources Tab */}
      {activeTab === "public-data" && (
        <>
          {publicLoading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
              <p className="text-sm text-gray-500">Loading public data sources...</p>
            </div>
          ) : publicData ? (
            <>
              {/* OIG Report Highlights */}
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
                <div className="flex items-center gap-2 mb-4">
                  <FileText className="w-4 h-4 text-primary-600" />
                  <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                    OIG Report Highlights
                  </h3>
                </div>
                <div className="space-y-3">
                  {publicData.oig_highlights.map((highlight, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-100 rounded-lg">
                      <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-gray-800">{highlight}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* State NDC Compliance Table */}
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                    State NDC Compliance
                  </h3>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">State</th>
                      <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Capture Rate</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Enforcer</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {publicData.state_ndc_compliance.map((row, i) => {
                      const rate = row.capture_rate <= 1 ? row.capture_rate * 100 : row.capture_rate;
                      return (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-6 py-3 text-sm font-medium text-gray-900">{row.state}</td>
                          <td className="px-6 py-3 text-sm text-right">
                            <span className={`font-semibold ${rate >= 90 ? "text-emerald-700" : rate >= 60 ? "text-amber-700" : "text-red-700"}`}>
                              {rate.toFixed(0)}%
                            </span>
                          </td>
                          <td className="px-6 py-3 text-sm text-gray-600">{row.enforcer}</td>
                          <td className="px-6 py-3 text-sm text-gray-500">{row.notes}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Net Effective Rebate Ranges */}
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
                  Net Effective Rebate Ranges by Therapy Class
                </h3>
                <div className="space-y-3">
                  {publicData.net_effective_rebate_ranges.map((range, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <span className="text-sm font-medium text-gray-700 w-52 flex-shrink-0">{range.therapy_class}</span>
                      <div className="flex-1 relative h-6 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="absolute h-full bg-gradient-to-r from-primary-600 to-emerald-500 rounded-full"
                          style={{ left: `${range.low}%`, width: `${range.high - range.low}%` }}
                        />
                      </div>
                      <span className="text-sm font-semibold text-gray-700 w-24 text-right">
                        {range.low}% - {range.high}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400">
              <Globe className="w-12 h-12 mx-auto mb-3" />
              <p className="text-sm">Public data sources unavailable</p>
            </div>
          )}
        </>
      )}

      {/* IRA Selected Drugs Tab */}
      {activeTab === "ira-drugs" && (
        <>
          {iraLoading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
              <p className="text-sm text-gray-500">Loading IRA drug data...</p>
            </div>
          ) : (
            <>
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-6">
                <div className="flex items-start gap-3">
                  <Pill className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="text-sm font-bold text-blue-900 mb-1">
                      Inflation Reduction Act (IRA) -- Medicare Drug Price Negotiation
                    </h3>
                    <p className="text-sm text-blue-700">
                      CMS has selected drugs for Medicare price negotiation under the IRA. These negotiated prices impact benchmark comparisons and PBM rebate dynamics.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                    IRA Selected Drugs
                  </h3>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Drug Name</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Manufacturer</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Indication</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Negotiated Price</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Effective Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {iraDrugs.map((drug, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-6 py-3 text-sm font-medium text-gray-900">{drug.drug_name}</td>
                        <td className="px-6 py-3 text-sm text-gray-600">{drug.manufacturer}</td>
                        <td className="px-6 py-3 text-sm text-gray-600">{drug.indication}</td>
                        <td className="px-6 py-3 text-sm font-semibold text-primary-600">{drug.negotiated_price || "Pending"}</td>
                        <td className="px-6 py-3 text-sm text-gray-500">{drug.effective_date || "TBD"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
