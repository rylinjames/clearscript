import { type LucideIcon } from "lucide-react";

interface MetricCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  trend?: string;
  trendUp?: boolean;
  color?: "blue" | "green" | "red" | "amber";
}

const colorMap = {
  blue: {
    bg: "bg-blue-50",
    icon: "bg-blue-100 text-blue-600",
    trend: "text-blue-600",
  },
  green: {
    bg: "bg-emerald-50",
    icon: "bg-emerald-100 text-emerald-600",
    trend: "text-emerald-600",
  },
  red: {
    bg: "bg-red-50",
    icon: "bg-red-100 text-red-600",
    trend: "text-red-600",
  },
  amber: {
    bg: "bg-amber-50",
    icon: "bg-amber-100 text-amber-600",
    trend: "text-amber-600",
  },
};

export default function MetricCard({
  icon: Icon,
  label,
  value,
  trend,
  trendUp,
  color = "blue",
}: MetricCardProps) {
  const c = colorMap[color];

  return (
    <div className={`rounded-xl border border-gray-200 ${c.bg} p-6`}>
      <div className="flex items-center justify-between">
        <div className={`rounded-lg p-2.5 ${c.icon}`}>
          <Icon className="w-5 h-5" />
        </div>
        {trend && (
          <span
            className={`text-sm font-medium ${
              trendUp ? "text-emerald-600" : "text-red-500"
            }`}
          >
            {trendUp ? "\u2191" : "\u2193"} {trend}
          </span>
        )}
      </div>
      <p className="mt-4 text-2xl font-bold text-gray-900">{value}</p>
      <p className="mt-1 text-sm text-gray-500">{label}</p>
    </div>
  );
}
