"use client";
import { Download } from "lucide-react";

interface ExportButtonProps {
  data: Record<string, unknown>[] | string;
  filename: string;
  label?: string;
}

export default function ExportButton({ data, filename, label = "Export CSV" }: ExportButtonProps) {
  const handleExport = () => {
    let csv: string;
    if (typeof data === "string") {
      csv = data;
    } else if (Array.isArray(data) && data.length > 0) {
      const headers = Object.keys(data[0]);
      const rows = data.map(row => headers.map(h => {
        const val = String(row[h] ?? "");
        return val.includes(",") || val.includes('"') ? `"${val.replace(/"/g, '""')}"` : val;
      }).join(","));
      csv = [headers.join(","), ...rows].join("\n");
    } else {
      return;
    }
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <button onClick={handleExport} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
      <Download className="w-3.5 h-3.5" />
      {label}
    </button>
  );
}
