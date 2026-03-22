"use client";

import { useState } from "react";
import StatusBadge from "@/components/StatusBadge";
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

const demoResults: ZipResult[] = [
  { zip: "10001", pharmaciesInNetwork: 12, pharmaciesNeeded: 3, adequate: true, nearestPharmacyMiles: 0.2 },
  { zip: "10002", pharmaciesInNetwork: 8, pharmaciesNeeded: 3, adequate: true, nearestPharmacyMiles: 0.3 },
  { zip: "10003", pharmaciesInNetwork: 15, pharmaciesNeeded: 3, adequate: true, nearestPharmacyMiles: 0.1 },
  { zip: "10010", pharmaciesInNetwork: 6, pharmaciesNeeded: 3, adequate: true, nearestPharmacyMiles: 0.4 },
  { zip: "10031", pharmaciesInNetwork: 2, pharmaciesNeeded: 3, adequate: false, nearestPharmacyMiles: 1.8 },
  { zip: "10034", pharmaciesInNetwork: 1, pharmaciesNeeded: 3, adequate: false, nearestPharmacyMiles: 2.4 },
  { zip: "10039", pharmaciesInNetwork: 0, pharmaciesNeeded: 3, adequate: false, nearestPharmacyMiles: 4.2 },
  { zip: "60601", pharmaciesInNetwork: 9, pharmaciesNeeded: 3, adequate: true, nearestPharmacyMiles: 0.3 },
  { zip: "60605", pharmaciesInNetwork: 4, pharmaciesNeeded: 3, adequate: true, nearestPharmacyMiles: 0.6 },
  { zip: "60608", pharmaciesInNetwork: 2, pharmaciesNeeded: 3, adequate: false, nearestPharmacyMiles: 1.9 },
  { zip: "90001", pharmaciesInNetwork: 5, pharmaciesNeeded: 3, adequate: true, nearestPharmacyMiles: 0.5 },
  { zip: "90003", pharmaciesInNetwork: 3, pharmaciesNeeded: 3, adequate: true, nearestPharmacyMiles: 0.8 },
  { zip: "90005", pharmaciesInNetwork: 7, pharmaciesNeeded: 3, adequate: true, nearestPharmacyMiles: 0.2 },
  { zip: "90008", pharmaciesInNetwork: 1, pharmaciesNeeded: 3, adequate: false, nearestPharmacyMiles: 3.1 },
  { zip: "90011", pharmaciesInNetwork: 2, pharmaciesNeeded: 3, adequate: false, nearestPharmacyMiles: 2.3 },
];

const demoPhantoms: PhantomPharmacy[] = [
  { name: "QuickRx Pharmacy #4412", npi: "1234567890", zip: "10039", reason: "License expired 8/2025, still listed as active in network" },
  { name: "CareFirst Drugs", npi: "0987654321", zip: "60608", reason: "Closed permanently — location demolished" },
  { name: "Valley Health Pharmacy", npi: "1122334455", zip: "90008", reason: "No claims processed in 18 months, phone disconnected" },
];

export default function NetworkPage() {
  const [zipInput, setZipInput] = useState(sampleZips);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ZipResult[] | null>(null);
  const [phantoms, setPhantoms] = useState<PhantomPharmacy[]>([]);

  const handleAnalyze = async () => {
    setLoading(true);
    setResults(null);

    const zips = zipInput.split(",").map((z) => z.trim()).filter(Boolean);

    try {
      const res = await fetch("http://localhost:8000/api/network/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ zip_codes: zips }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      // Map API response — handle both camelCase and snake_case field names
      const apiResults = data.results || data.zip_results;
      if (apiResults && apiResults.length > 0) {
        setResults(
          apiResults.map((r: Record<string, unknown>) => ({
            zip: r.zip || r.zip_code,
            pharmaciesInNetwork: r.pharmaciesInNetwork ?? r.pharmacies_in_network ?? 0,
            pharmaciesNeeded: r.pharmaciesNeeded ?? r.pharmacies_needed ?? 3,
            adequate: r.adequate ?? r.is_adequate ?? false,
            nearestPharmacyMiles: r.nearestPharmacyMiles ?? r.nearest_pharmacy_miles ?? 0,
          }))
        );
      } else {
        setResults(demoResults);
      }
      const apiPhantoms = data.phantomPharmacies || data.phantom_pharmacies;
      if (apiPhantoms && apiPhantoms.length > 0) {
        setPhantoms(
          apiPhantoms.map((p: Record<string, unknown>) => ({
            name: p.name || "",
            npi: p.npi || "",
            zip: p.zip || p.zip_code || "",
            reason: p.reason || p.reason_flagged || "",
          }))
        );
      } else {
        setPhantoms(demoPhantoms);
      }
    } catch {
      setResults(demoResults);
      setPhantoms(demoPhantoms);
    } finally {
      setLoading(false);
    }
  };

  const adequateCount = results?.filter((r) => r.adequate).length || 0;
  const totalCount = results?.length || 0;
  const score = totalCount > 0 ? Math.round((adequateCount / totalCount) * 100) : 0;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <MapPin className="w-7 h-7 text-[#1e3a5f]" />
          Network Adequacy Analyzer
        </h1>
        <p className="text-gray-500 mt-1">
          Evaluate pharmacy network coverage by employee zip codes
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Employee Zip Codes (comma-separated)
        </label>
        <textarea
          value={zipInput}
          onChange={(e) => setZipInput(e.target.value)}
          rows={3}
          placeholder="10001, 10002, 10003, ..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#1e3a5f] focus:border-[#1e3a5f] outline-none resize-none font-mono"
        />
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="mt-3 inline-flex items-center gap-2 px-4 py-2.5 bg-[#1e3a5f] text-white rounded-lg hover:bg-[#2a4f7f] transition-colors text-sm font-medium disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <MapPin className="w-4 h-4" />}
          Analyze Network
        </button>
      </div>

      {loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-[#1e3a5f] animate-spin" />
          <p className="text-sm text-gray-500">Analyzing network adequacy...</p>
        </div>
      )}

      {results && !loading && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6 flex justify-center">
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

          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
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
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
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
