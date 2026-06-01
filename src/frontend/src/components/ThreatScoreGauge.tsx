export default function ThreatScoreGauge({ score = 0 }: { score?: number }) {
  const r = 40;
  const circumference = 2 * Math.PI * r;
  const progress = Math.min(score / 100, 1);
  const offset = circumference * (1 - progress);

  const color =
    score < 25
      ? "#22C55E"
      : score < 50
      ? "#F59E0B"
      : score < 75
      ? "#EF4444"
      : "#7F1D1D";

  return (
    <div className="flex flex-col items-center">
      <svg width="100" height="100" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke="#1F2937"
          strokeWidth="8"
        />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          className="transition-all duration-1000"
        />
        <text
          x="50"
          y="50"
          textAnchor="middle"
          dominantBaseline="central"
          fill="#00D4FF"
          fontSize="24"
          fontFamily="monospace"
          fontWeight="bold"
        >
          {Math.round(score)}
        </text>
      </svg>
      <div className="text-[10px] text-gray-500 mt-1">THREAT SCORE</div>
    </div>
  );
}
