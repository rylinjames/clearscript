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
    icon: "bg-primary-50 text-primary-600",
    trend: "text-gray-400",
  },
  green: {
    icon: "bg-emerald-50 text-emerald-600",
    trend: "text-emerald-600",
  },
  red: {
    icon: "bg-red-50 text-red-600",
    trend: "text-red-500",
  },
  amber: {
    icon: "bg-amber-50 text-amber-600",
    trend: "text-gray-400",
  },
};

export default function MetricCard({
  icon: Icon,
  label,
  value,
  trend,
  color = "blue",
}: MetricCardProps) {
  const c = colorMap[color];

  return (
    <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-card-hover)] transition-shadow duration-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className={`rounded-lg p-2 ${c.icon}`}>
          <Icon className="w-4 h-4" />
        </div>
        {trend && (
          <span className={`text-xs font-medium ${c.trend}`}>
            {trend}
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-gray-900 tracking-tight">{value}</p>
      <p className="mt-0.5 text-sm text-gray-400">{label}</p>
    </div>
  );
}
