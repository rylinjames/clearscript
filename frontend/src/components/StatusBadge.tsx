interface StatusBadgeProps {
  status: "critical" | "warning" | "info" | "good";
  label?: string;
}

const styles = {
  critical: "bg-red-100 text-red-700 border-red-200",
  warning: "bg-amber-100 text-amber-700 border-amber-200",
  info: "bg-blue-100 text-blue-700 border-blue-200",
  good: "bg-emerald-100 text-emerald-700 border-emerald-200",
};

const defaultLabels = {
  critical: "Critical",
  warning: "Warning",
  info: "Info",
  good: "Good",
};

export default function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles[status]}`}
    >
      {label || defaultLabels[status]}
    </span>
  );
}
