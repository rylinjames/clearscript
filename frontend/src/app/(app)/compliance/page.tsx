"use client";

import { useState, useEffect, useMemo } from "react";
import { usePageTitle } from "@/components/PageTitle";
import {
  CalendarClock,
  Loader2,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Scale,
  Users,
  ListChecks,
  CalendarDays,
  List as ListIcon,
  ChevronLeft,
  ChevronRight,
  FileText,
  Clock,
} from "lucide-react";

interface ContractListItem {
  id: number;
  filename: string;
  analysis_date: string | null;
  deal_score: number | null;
  risk_level: string | null;
}

interface ComplianceItem {
  id: string;
  name: string;
  category: string;
  due_date: string;
  recurrence?: string;
  what_it_is?: string;
  why_it_matters?: string;
  when_it_applies?: string;
  who_acts?: string;
  statutory_basis?: string;
  action_items?: string[];
  educational_summary?: string;
  contract_derived?: boolean;
  source_contract_filename?: string | null;
  source_contract_analysis_date?: string | null;
  days_until?: number | null;
  timing_phase?:
    | "past"
    | "today"
    | "this_week"
    | "this_month"
    | "next_quarter"
    | "this_year"
    | "future"
    | "unknown";
  timing_label?: string;
}

const PHASE_STYLES: Record<string, { ring: string; dot: string; text: string }> = {
  past: { ring: "border-amber-200", dot: "bg-amber-500", text: "text-amber-700" },
  today: { ring: "border-blue-300", dot: "bg-blue-600", text: "text-blue-700" },
  this_week: { ring: "border-blue-200", dot: "bg-blue-500", text: "text-blue-700" },
  this_month: { ring: "border-blue-200", dot: "bg-blue-400", text: "text-blue-600" },
  next_quarter: { ring: "border-emerald-200", dot: "bg-emerald-500", text: "text-emerald-700" },
  this_year: { ring: "border-emerald-200", dot: "bg-emerald-400", text: "text-emerald-700" },
  future: { ring: "border-gray-200", dot: "bg-gray-400", text: "text-gray-600" },
  unknown: { ring: "border-gray-200", dot: "bg-gray-300", text: "text-gray-500" },
};

function formatLongDate(iso: string): string {
  try {
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString(undefined, {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function CompliancePage() {
  usePageTitle("Compliance Tracker");
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<ComplianceItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [view, setView] = useState<"list" | "calendar">("list");

  // Contract picker state
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);

  // Fetch contract list on mount for the picker
  useEffect(() => {
    const fetchContracts = async () => {
      try {
        const res = await fetch("/api/contracts/list");
        if (!res.ok) return;
        const data = await res.json();
        const list: ContractListItem[] = Array.isArray(data?.contracts) ? data.contracts : [];
        setContracts(list);
        // Auto-select the most recent contract if available
        if (list.length > 0 && selectedContractId === null) {
          setSelectedContractId(list[0].id);
        }
      } catch { /* optional */ }
    };
    fetchContracts();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch deadlines whenever the selected contract changes
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const url = selectedContractId
          ? `/api/compliance/deadlines?contract_id=${selectedContractId}`
          : "/api/compliance/deadlines";
        const res = await fetch(url);
        if (!res.ok) {
          let detail = `Compliance deadlines failed with status ${res.status}`;
          try {
            const errJson = await res.json();
            if (errJson?.detail) detail = String(errJson.detail);
          } catch { /* not JSON */ }
          throw new Error(detail);
        }
        const data = await res.json();
        const raw: ComplianceItem[] = Array.isArray(data?.deadlines) ? data.deadlines : [];
        setItems(raw);
      } catch (e) {
        setItems([]);
        setError(e instanceof Error ? e.message : "Failed to load compliance items");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [selectedContractId]);

  // Group items by category for the list view so the user sees them by
  // *type* (federal annual filing, contract-derived, etc.) instead of
  // by stress level.
  const grouped = useMemo(() => {
    const out: Record<string, ComplianceItem[]> = {};
    for (const item of items) {
      const key = item.category || "Other";
      if (!out[key]) out[key] = [];
      out[key].push(item);
    }
    return out;
  }, [items]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        <p className="text-sm text-gray-500">Loading compliance items...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="animate-fade-in">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <CalendarClock className="w-7 h-7 text-primary-600" />
            Compliance Tracker
          </h1>
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-5">
          <p className="text-sm font-semibold text-amber-900">Could not load compliance items</p>
          <p className="text-sm text-amber-800 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <CalendarClock className="w-7 h-7 text-primary-600" />
            Compliance Tracker
          </h1>
          <p className="text-gray-500 mt-1 max-w-2xl">
            Federal obligations every self-insured plan sponsor needs to track, plus
            contract-specific deadlines from the contract you select below.
          </p>
        </div>
        <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1 shadow-sm self-start">
          <button
            onClick={() => setView("list")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              view === "list" ? "bg-primary-600 text-white" : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <ListIcon className="w-4 h-4" />
            List
          </button>
          <button
            onClick={() => setView("calendar")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              view === "calendar" ? "bg-primary-600 text-white" : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <CalendarDays className="w-4 h-4" />
            Calendar
          </button>
        </div>
      </div>

      {/* Contract picker — select which contract's deadlines to show */}
      {contracts.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-4 mb-6">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2 flex-shrink-0">
              <FileText className="w-4 h-4 text-primary-600" />
              <label className="text-sm font-semibold text-gray-900">Contract</label>
            </div>
            <select
              value={selectedContractId ?? ""}
              onChange={(e) => setSelectedContractId(e.target.value ? Number(e.target.value) : null)}
              className="flex-1 min-w-[200px] px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-600 focus:border-primary-600 outline-none bg-white"
            >
              <option value="">Federal deadlines only (no contract selected)</option>
              {contracts.map((c) => {
                const dateStr = c.analysis_date ? c.analysis_date.split(" ")[0] : "";
                return (
                  <option key={c.id} value={c.id}>
                    {c.filename} ({dateStr}{c.deal_score !== null ? ` · score ${c.deal_score}` : ""})
                  </option>
                );
              })}
            </select>
            {selectedContractId && (
              <p className="text-xs text-gray-500 w-full mt-1">
                Showing this contract&apos;s notice deadline, RFP start date, and term expiration alongside federal deadlines.
              </p>
            )}
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
          <p className="text-sm text-gray-500">Loading compliance deadlines...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
          No compliance items to display.
        </div>
      ) : view === "list" ? (
        <ListView
          grouped={grouped}
          expandedId={expandedId}
          setExpandedId={setExpandedId}
        />
      ) : (
        <CalendarView items={items} />
      )}
    </div>
  );
}

// ─── List View ───────────────────────────────────────────────────────────────

function ListView({
  grouped,
  expandedId,
  setExpandedId,
}: {
  grouped: Record<string, ComplianceItem[]>;
  expandedId: string | null;
  setExpandedId: (id: string | null) => void;
}) {
  const categoryOrder = Object.keys(grouped).sort();
  return (
    <div className="space-y-8">
      {categoryOrder.map((cat) => (
        <div key={cat}>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
            {cat}
          </h3>
          <div className="space-y-3">
            {grouped[cat].map((item) => (
              <ItemCard
                key={item.id}
                item={item}
                expanded={expandedId === item.id}
                onToggle={() => setExpandedId(expandedId === item.id ? null : item.id)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ItemCard({
  item,
  expanded,
  onToggle,
}: {
  item: ComplianceItem;
  expanded: boolean;
  onToggle: () => void;
}) {
  const phase = item.timing_phase || "unknown";
  const styles = PHASE_STYLES[phase] || PHASE_STYLES.unknown;
  return (
    <div className={`rounded-xl border ${styles.ring} bg-white overflow-hidden`}>
      <button
        onClick={onToggle}
        className="w-full text-left p-5 flex items-start justify-between gap-4"
      >
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <div className={`w-2.5 h-2.5 rounded-full ${styles.dot} mt-2 flex-shrink-0`} />
          <div className="min-w-0 flex-1">
            <h4 className="text-base font-semibold text-gray-900">{item.name}</h4>
            <p className={`text-sm font-medium mt-1 ${styles.text}`}>
              {item.timing_label || formatLongDate(item.due_date)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {formatLongDate(item.due_date)}
              {item.recurrence ? ` · ${item.recurrence}` : ""}
            </p>
          </div>
        </div>
        <div className="flex-shrink-0">
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {expanded && <ItemDetail item={item} />}
    </div>
  );
}

function ItemDetail({ item }: { item: ComplianceItem }) {
  return (
    <div className="border-t border-gray-100 px-5 py-5 space-y-5">
      {item.what_it_is && (
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <BookOpen className="w-4 h-4 text-gray-400" />
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">What this is</p>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">{item.what_it_is}</p>
        </div>
      )}

      {item.why_it_matters && (
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Scale className="w-4 h-4 text-gray-400" />
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Why it matters</p>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">{item.why_it_matters}</p>
        </div>
      )}

      {item.when_it_applies && (
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <CalendarClock className="w-4 h-4 text-gray-400" />
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">When it applies</p>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">{item.when_it_applies}</p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {item.who_acts && (
          <div className="rounded-lg bg-gray-50 border border-gray-100 p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <Users className="w-3.5 h-3.5 text-gray-400" />
              <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">Who acts</p>
            </div>
            <p className="text-sm text-gray-800">{item.who_acts}</p>
          </div>
        )}
        {item.statutory_basis && (
          <div className="rounded-lg bg-gray-50 border border-gray-100 p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 mb-1">Statutory basis</p>
            <p className="text-sm text-gray-800 font-mono">{item.statutory_basis}</p>
          </div>
        )}
      </div>

      {item.action_items && item.action_items.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <ListChecks className="w-4 h-4 text-gray-400" />
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Action items</p>
          </div>
          <ol className="space-y-2">
            {item.action_items.map((act, i) => (
              <li key={i} className="flex gap-3">
                <span className="flex-shrink-0 inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary-50 text-primary-700 text-[11px] font-bold">
                  {i + 1}
                </span>
                <p className="text-sm text-gray-700 leading-relaxed">{act}</p>
              </li>
            ))}
          </ol>
        </div>
      )}

      {item.educational_summary && (
        <div className="rounded-lg bg-blue-50 border border-blue-100 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-blue-700 mb-1">Context</p>
          <p className="text-sm text-blue-900 leading-relaxed">{item.educational_summary}</p>
        </div>
      )}

      {item.contract_derived && item.source_contract_filename && (
        <div className="rounded-lg bg-emerald-50 border border-emerald-100 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-700 mb-1">Derived from your uploaded contract</p>
          <p className="text-sm text-emerald-900">
            {item.source_contract_filename}
            {item.source_contract_analysis_date ? ` · analyzed ${item.source_contract_analysis_date.split(" ")[0]}` : ""}
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Calendar View ───────────────────────────────────────────────────────────

function CalendarView({ items }: { items: ComplianceItem[] }) {
  const today = new Date();
  const [cursor, setCursor] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [pickedDate, setPickedDate] = useState<string | null>(null);

  const itemsByDate = useMemo(() => {
    const map: Record<string, ComplianceItem[]> = {};
    for (const item of items) {
      if (!item.due_date) continue;
      if (!map[item.due_date]) map[item.due_date] = [];
      map[item.due_date].push(item);
    }
    return map;
  }, [items]);

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstOfMonth = new Date(year, month, 1);
  const lastOfMonth = new Date(year, month + 1, 0);
  const startWeekday = firstOfMonth.getDay(); // 0 = Sunday

  // Build a 6-week grid (42 cells) for consistent layout
  const cells: Array<{ date: Date; iso: string; inMonth: boolean }> = [];
  const start = new Date(year, month, 1 - startWeekday);
  for (let i = 0; i < 42; i++) {
    const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
    const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    cells.push({ date: d, iso, inMonth: d.getMonth() === month });
  }

  const monthLabel = cursor.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  const isoToday = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

  const pickedItems = pickedDate ? itemsByDate[pickedDate] || [] : [];

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <div className="xl:col-span-2 bg-white rounded-xl border border-gray-200/60 shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
          <button
            onClick={() => setCursor(new Date(year, month - 1, 1))}
            className="p-1.5 rounded-md hover:bg-gray-100 text-gray-600"
            aria-label="Previous month"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <h3 className="text-sm font-semibold text-gray-900">{monthLabel}</h3>
          <button
            onClick={() => setCursor(new Date(year, month + 1, 1))}
            className="p-1.5 rounded-md hover:bg-gray-100 text-gray-600"
            aria-label="Next month"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
        <div className="grid grid-cols-7 text-xs font-medium text-gray-500 border-b border-gray-100">
          {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
            <div key={d} className="px-2 py-2 text-center">{d}</div>
          ))}
        </div>
        <div className="grid grid-cols-7">
          {cells.map((cell) => {
            const dayItems = itemsByDate[cell.iso] || [];
            const isToday = cell.iso === isoToday;
            const isPicked = cell.iso === pickedDate;
            return (
              <button
                key={cell.iso}
                onClick={() => setPickedDate(cell.iso)}
                className={`min-h-[78px] border-r border-b border-gray-100 px-2 py-1.5 text-left transition-colors hover:bg-gray-50 ${
                  cell.inMonth ? "" : "bg-gray-50/40"
                } ${isPicked ? "bg-primary-50 ring-1 ring-primary-300" : ""}`}
              >
                <div className="flex items-center justify-between">
                  <span className={`text-xs ${
                    cell.inMonth ? "text-gray-700" : "text-gray-300"
                  } ${isToday ? "font-bold text-primary-700" : ""}`}>
                    {cell.date.getDate()}
                  </span>
                </div>
                <div className="mt-1 space-y-0.5">
                  {dayItems.slice(0, 2).map((it) => {
                    const styles = PHASE_STYLES[it.timing_phase || "unknown"];
                    return (
                      <div
                        key={it.id}
                        className={`text-[10px] truncate rounded px-1 py-0.5 text-white ${styles.dot}`}
                        title={it.name}
                      >
                        {it.name}
                      </div>
                    );
                  })}
                  {dayItems.length > 2 && (
                    <div className="text-[10px] text-gray-500">+{dayItems.length - 2} more</div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200/60 shadow-sm p-5 max-h-[640px] overflow-y-auto">
        <h3 className="text-sm font-semibold text-gray-900 mb-1">
          {pickedDate ? formatLongDate(pickedDate) : "Pick a date"}
        </h3>
        <p className="text-xs text-gray-500 mb-4">
          {pickedDate
            ? pickedItems.length === 0
              ? "Nothing scheduled for this date."
              : `${pickedItems.length} item${pickedItems.length === 1 ? "" : "s"} on this date`
            : "Click any day in the calendar to see the items due on that date."}
        </p>
        {pickedItems.length > 0 && (
          <div className="space-y-4">
            {pickedItems.map((item) => (
              <div key={item.id} className="rounded-lg border border-gray-200 p-4">
                <h4 className="text-sm font-semibold text-gray-900">{item.name}</h4>
                <p className="text-xs text-gray-500 mt-0.5">{item.category}</p>
                {item.what_it_is && (
                  <p className="text-sm text-gray-700 mt-2 leading-relaxed">{item.what_it_is}</p>
                )}
                {item.action_items && item.action_items.length > 0 && (
                  <div className="mt-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 mb-1.5">Action items</p>
                    <ul className="space-y-1">
                      {item.action_items.map((act, i) => (
                        <li key={i} className="text-xs text-gray-700 flex gap-2">
                          <span className="text-gray-400">{i + 1}.</span>
                          <span>{act}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
