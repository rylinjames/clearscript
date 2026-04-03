interface ScoreCircleProps {
  score: number;
  maxScore?: number;
  size?: number | "sm" | "md" | "lg";
  label?: string;
}

const SIZE_MAP: Record<string, number> = { sm: 100, md: 140, lg: 180 };

export default function ScoreCircle({
  score,
  maxScore = 100,
  size: rawSize = 140,
  label = "Score",
}: ScoreCircleProps) {
  const size = typeof rawSize === "string" ? (SIZE_MAP[rawSize] || 140) : rawSize;
  const pct = Math.min((score / maxScore) * 100, 100);
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;

  const color =
    pct >= 80
      ? "text-emerald-500"
      : pct >= 50
      ? "text-amber-500"
      : "text-red-500";

  const strokeColor =
    pct >= 80
      ? "stroke-emerald-500"
      : pct >= 50
      ? "stroke-amber-500"
      : "stroke-red-500";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          className="transform -rotate-90"
          width={size}
          height={size}
          role="img"
          aria-label={`${label}: ${score}%`}
        >
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="8"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            className={strokeColor}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 0.6s ease-out" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-2xl font-bold ${color}`}>{score}%</span>
        </div>
      </div>
      <span className="text-sm text-gray-500 font-medium">{label}</span>
    </div>
  );
}
