"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { usePageTitle } from "@/components/PageTitle";
import StatusBadge from "@/components/StatusBadge";
import { useToast } from "@/components/Toast";
import {
  Loader2,
  Search,
  Pill,
  DollarSign,
  Tag,
  ArrowLeft,
  Beaker,
  ShieldCheck,
} from "lucide-react";

interface DrugSearchResult {
  drugName: string;
  ndc: string;
  drugClass: string;
  nadacPrice: number;
  awpPrice: number;
  isGeneric: boolean;
  rebatePercent: number;
  iraStatus: string;
}

interface DrugProfile {
  drugName: string;
  ndc: string;
  drugClass: string;
  manufacturer: string;
  strength: string;
  dosageForm: string;
  nadacPrice: number;
  awpPrice: number;
  wacPrice: number;
  isGeneric: boolean;
  genericAvailable: boolean;
  rebatePercent: number;
  iraStatus: string;
  therapeuticAlternatives: string[];
  formularyTier: string;
  paRequired: boolean;
  qlApplied: boolean;
  stRequired: boolean;
}

export default function DrugLookupPage() {
  const { toast } = useToast();
  usePageTitle("Drug Lookup");
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<DrugSearchResult[]>([]);
  const [profile, setProfile] = useState<DrugProfile | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const searchDrugs = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      return;
    }
    setSearching(true);
    try {
      const res = await fetch(`/api/drug-lookup/search?q=${encodeURIComponent(q)}`);
      if (res.ok) setResults(await res.json());
    } catch {
      /* silent */
    }
    setSearching(false);
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => searchDrugs(query), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, searchDrugs]);

  const loadProfile = async (ndc: string) => {
    setLoadingProfile(true);
    try {
      const res = await fetch(`/api/drug-lookup/profile/${ndc}`);
      if (res.ok) {
        setProfile(await res.json());
      } else {
        toast("Failed to load drug profile", "error");
      }
    } catch {
      toast("Failed to load drug profile", "error");
    }
    setLoadingProfile(false);
  };

  if (loadingProfile) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        <p className="text-sm text-gray-500">Loading drug profile...</p>
      </div>
    );
  }

  if (profile) {
    return (
      <div className="animate-fade-in">
        <button
          onClick={() => setProfile(null)}
          className="inline-flex items-center gap-2 text-sm text-primary-600 hover:underline mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Back to search
        </button>
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <Pill className="w-7 h-7 text-primary-600" />
            {profile.drugName}
          </h1>
          <p className="text-gray-500 mt-1">
            NDC: {profile.ndc} &middot; {profile.manufacturer} &middot; {profile.strength} {profile.dosageForm}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <div className="bg-blue-50 rounded-xl border border-blue-200 p-6 text-center">
            <p className="text-2xl font-bold text-primary-600">${profile.nadacPrice.toFixed(2)}</p>
            <p className="text-xs text-gray-600 mt-1">NADAC Price</p>
          </div>
          <div className="bg-amber-50 rounded-xl border border-amber-200 p-6 text-center">
            <p className="text-2xl font-bold text-amber-700">${profile.awpPrice.toFixed(2)}</p>
            <p className="text-xs text-gray-600 mt-1">AWP Price</p>
          </div>
          <div className="bg-gray-50 rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 text-center">
            <p className="text-2xl font-bold text-gray-900">${profile.wacPrice.toFixed(2)}</p>
            <p className="text-xs text-gray-600 mt-1">WAC Price</p>
          </div>
          <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-6 text-center">
            <p className="text-2xl font-bold text-emerald-700">{profile.rebatePercent}%</p>
            <p className="text-xs text-gray-600 mt-1">Est. Rebate</p>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">Drug Details</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-gray-500">Drug Class</p>
              <p className="text-sm font-medium text-gray-900">{profile.drugClass}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Formulary Tier</p>
              <p className="text-sm font-medium text-gray-900">{profile.formularyTier}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Generic Status</p>
              <StatusBadge status={profile.isGeneric ? "good" : "info"} label={profile.isGeneric ? "Generic" : "Brand"} />
            </div>
            <div>
              <p className="text-xs text-gray-500">Prior Auth</p>
              <StatusBadge status={profile.paRequired ? "warning" : "good"} label={profile.paRequired ? "Required" : "Not Required"} />
            </div>
            <div>
              <p className="text-xs text-gray-500">Quantity Limit</p>
              <StatusBadge status={profile.qlApplied ? "warning" : "good"} label={profile.qlApplied ? "Applied" : "None"} />
            </div>
            <div>
              <p className="text-xs text-gray-500">IRA Status</p>
              <StatusBadge status={profile.iraStatus === "Selected" ? "info" : "good"} label={profile.iraStatus} />
            </div>
          </div>
        </div>

        {profile.therapeuticAlternatives.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wider">
              Therapeutic Alternatives
            </h3>
            <div className="flex flex-wrap gap-2">
              {profile.therapeuticAlternatives.map((alt, i) => (
                <span key={i} className="inline-block bg-blue-50 text-primary-600 text-sm px-3 py-1 rounded-lg border border-blue-200">
                  {alt}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Search className="w-7 h-7 text-primary-600" />
          Drug Lookup
        </h1>
        <p className="text-gray-500 mt-1">
          Search for drugs by name to view pricing, rebate estimates, and IRA status
        </p>
      </div>

      {/* Search Bar */}
      <div className="relative mb-6">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by drug name (e.g., Humira, atorvastatin, Eliquis)..."
          className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent"
        />
        {searching && <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-primary-600 animate-spin" />}
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {results.map((drug, i) => (
            <button
              key={i}
              onClick={() => loadProfile(drug.ndc)}
              className="bg-white rounded-xl border border-gray-200 p-5 text-left hover:border-primary-600 hover:shadow-md transition-all"
            >
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-semibold text-gray-900">{drug.drugName}</h4>
                <StatusBadge status={drug.isGeneric ? "good" : "info"} label={drug.isGeneric ? "Generic" : "Brand"} />
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                <div className="flex items-center gap-1">
                  <Tag className="w-3 h-3" /> NDC: {drug.ndc}
                </div>
                <div className="flex items-center gap-1">
                  <Beaker className="w-3 h-3" /> {drug.drugClass}
                </div>
                <div className="flex items-center gap-1">
                  <DollarSign className="w-3 h-3" /> NADAC: ${drug.nadacPrice.toFixed(2)}
                </div>
                <div className="flex items-center gap-1">
                  <DollarSign className="w-3 h-3" /> AWP: ${drug.awpPrice.toFixed(2)}
                </div>
                <div className="flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Rebate: {drug.rebatePercent}%
                </div>
                <div className="flex items-center gap-1">
                  <Pill className="w-3 h-3" /> IRA: {drug.iraStatus}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {query.length >= 2 && !searching && results.length === 0 && (
        <div className="text-center py-12">
          <Search className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No drugs found matching &quot;{query}&quot;</p>
        </div>
      )}
    </div>
  );
}
