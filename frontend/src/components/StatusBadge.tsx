interface StatusBadgeProps {
  status: string;
  label?: string;
}

const styles: Record<string, string> = {
  critical: "bg-red-50 text-red-600 border-red-100",
  warning: "bg-amber-50 text-amber-600 border-amber-100",
  info: "bg-blue-50 text-blue-600 border-blue-100",
  good: "bg-emerald-50 text-emerald-600 border-emerald-100",
  success: "bg-emerald-50 text-emerald-600 border-emerald-100",
};

const defaultLabels: Record<string, string> = {
  critical: "Critical",
  warning: "Warning",
  info: "Info",
  good: "Good",
  success: "Good",
};

export default function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium border ${styles[status] || styles.info}`}
    >
      {label || defaultLabels[status] || status}
    </span>
  );
}
