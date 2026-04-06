"use client";

import { useState, useEffect, useRef } from "react";
import { usePageTitle } from "@/components/PageTitle";
import StatusBadge from "@/components/StatusBadge";
import DataSourceBanner from "@/components/DataSourceBanner";
import ScoreCircle from "@/components/ScoreCircle";
import { MapPin, Loader2, AlertTriangle } from "lucide-react";

interface ZipResult {
  zip: string;
  pharmaciesInNetwork: number;
  pharmaciesNeeded: number;
  adequate: boolean;
  nearestPharmacyMiles: number;
}

interface PhantomPharmacy {
  name: string;
  npi: string;
  zip: string;
  reason: string;
}

const sampleZips = "10001, 10002, 10003, 10010, 10011, 10012, 10013, 10014, 10016, 10017, 10019, 10021, 10022, 10023, 10024, 10025, 10028, 10029, 10030, 10031, 10032, 10033, 10034, 10035, 10036, 10037, 10038, 10039, 10040, 60601, 60602, 60604, 60605, 60606, 60607, 60608, 60610, 60611, 60614, 60615, 90001, 90002, 90003, 90004, 90005, 90006, 90007, 90008, 90010, 90011";

export default function NetworkPage() {
  usePageTitle("Network Adequacy");
  const [zipInput, setZipInput] = useState(sampleZips);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ZipResult[] | null>(null);
  const [phantoms, setPhantoms] = useState<PhantomPharmacy[]>([]);
  const [error, setError] = useState<string | null>(null);

  const hasAutoLoaded = useRef(false);
  useEffect(() => {
    if (!hasAutoLoaded.current) {
      hasAutoLoaded.current = true;
      handleAnalyze();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAnalyze = async () => {
    setLoading(true);
    setResults(null);
    setError(null);

    const zips = zipInput.split(",").map((z) => z.trim()).filter(Boolean);

    try {
      const res = await fetch("/api/network/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ zip_codes: zips }),
      });
      if (!res.ok) {
        let detail = `Network analysis failed with status ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = String(errJson.detail);
        } catch { /* not JSON */ }
        throw new Error(detail);
      }
      const data = await res.json();
      const na = data?.network_analysis;
      setResults(
        (na?.coverage_areas || []).map((r: Record<string, unknown>) => ({
          zip: (r.zip_code || r.zip) as string,
          pharmaciesInNetwork: (r.pharmacies_within_5mi || r.pharmacies_in_network || 0) as number,
          pharmaciesNeeded: 3,
          adequate: (r.adequacy_met ?? r.adequate ?? false) as boolean,
          nearestPharmacyMiles: (r.nearest_pharmacy_miles || (r.pharmacies_within_5mi ? 2.5 : 8.0)) as number,
        }))
      );
      setPhantoms(
        (na?.phantom_details || []).map((p: Record<string, unknown>) => ({
          name: (p.name || "") as string,
          npi: (p.npi || "") as string,
          zip: (p.zip || p.zip_code || "") as string,
          reason: (p.reason || p.reason_flagged || "") as string,
        }))
      );
    } catch (e) {
      setResults([]);
      setPhantoms([]);
      setError(e instanceof Error ? e.message : "Network analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const adequateCount = results?.filter((r) => r.adequate).length || 0;
  const totalCount = results?.length || 0;
  const score = totalCount > 0 ? Math.round((adequateCount / totalCount) * 100) : 0;

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <MapPin className="w-7 h-7 text-primary-600" />
          Network Adequacy Analyzer
        </h1>
        <p className="text-gray-500 mt-1">
          Evaluate pharmacy network coverage by employee zip codes
        </p>
      </div>

      <DataSourceBanner />

      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Employee Zip Codes (comma-separated)
        </label>
        <textarea
          value={zipInput}
          onChange={(e) => setZipInput(e.target.value)}
          rows={3}
          placeholder="10001, 10002, 10003, ..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-600 focus:border-primary-600 outline-none resize-none font-mono"
        />
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="mt-3 inline-flex items-center gap-2 px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <MapPin className="w-4 h-4" />}
          Analyze Network
        </button>
      </div>

      {loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
          <p className="text-sm text-gray-500">Analyzing network adequacy...</p>
        </div>
      )}

      {results && !loading && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 flex justify-center">
              <ScoreCircle score={score} label="Adequacy Score" />
            </div>
            <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-6 text-center flex flex-col justify-center">
              <p className="text-3xl font-bold text-emerald-700">{adequateCount}</p>
              <p className="text-sm text-emerald-600 mt-1">Adequate Zip Codes</p>
            </div>
            <div className="bg-red-50 rounded-xl border border-red-200 p-6 text-center flex flex-col justify-center">
              <p className="text-3xl font-bold text-red-700">{totalCount - adequateCount}</p>
              <p className="text-sm text-red-600 mt-1">Inadequate Zip Codes</p>
            </div>
            <div className="bg-amber-50 rounded-xl border border-amber-200 p-6 text-center flex flex-col justify-center">
              <p className="text-3xl font-bold text-amber-700">{phantoms.length}</p>
              <p className="text-sm text-amber-600 mt-1">Phantom Pharmacies</p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
              Coverage by Zip Code
            </h3>
            <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-8 gap-2">
              {results.map((r) => (
                <div
                  key={r.zip}
                  className={`p-3 rounded-lg text-center text-sm font-mono ${
                    r.adequate
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : "bg-red-50 text-red-700 border border-red-200"
                  }`}
                >
                  <p className="font-bold">{r.zip}</p>
                  <p className="text-[10px] mt-0.5">{r.pharmaciesInNetwork} pharmacies</p>
                  <p className="text-[10px]">{r.nearestPharmacyMiles} mi</p>
                </div>
              ))}
            </div>
          </div>

          {phantoms.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                  Flagged Phantom Pharmacies
                </h3>
              </div>
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Pharmacy</th>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">NPI</th>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Zip</th>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Reason Flagged</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {phantoms.map((p, i) => (
                    <tr key={i} className="hover:bg-red-50/50">
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">{p.name}</td>
                      <td className="px-6 py-4 text-sm text-gray-600 font-mono">{p.npi}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{p.zip}</td>
                      <td className="px-6 py-4 text-sm text-red-600">{p.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
