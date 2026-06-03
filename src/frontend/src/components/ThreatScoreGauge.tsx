import { useEffect, useState, useRef } from "react";

export default function ThreatScoreGauge({ score = 0 }: { score?: number }) {
  const [history, setHistory] = useState<number[]>(Array(20).fill(0));
  
  useEffect(() => {
    setHistory(prev => [...prev.slice(1), score]);
  }, [score]);

  const r = 35;
  const circumference = 2 * Math.PI * r;
  const progress = Math.min(score / 100, 1);
  const offset = circumference * (1 - progress);

  const color =
    score < 30
      ? "#22C55E"
      : score < 60
      ? "#F59E0B"
      : score < 80
      ? "#EF4444"
      : "#7F1D1D";

  // Generate sparkline path
  const width = 120;
  const height = 40;
  const points = history.map((val, i) => `${(i / 19) * width},${height - (val / 100) * height}`).join(" ");

  return (
    <div className="flex items-center gap-4 p-2 bg-[#0A0E1A] rounded border border-[#1E3A5F]">
      {/* Radial Gauge */}
      <div className="relative">
        <svg width="80" height="80" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r={r} fill="none" stroke="#1F2937" strokeWidth="6" />
          <circle
            cx="50"
            cy="50"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            transform="rotate(-90 50 50)"
            className="transition-all duration-500"
          />
          <text x="50" y="50" textAnchor="middle" dominantBaseline="central" fill="#00D4FF" fontSize="20" fontFamily="monospace" fontWeight="bold">
            {Math.round(score)}
          </text>
        </svg>
      </div>

      {/* Real-time Trend Sparkline */}
      <div className="flex-1">
        <div className="text-[9px] font-bold text-gray-500 uppercase tracking-widest mb-1">THREAT TREND (60s)</div>
        <svg width={width} height={height} className="stroke-[#00D4FF]" style={{ fill: "none", strokeWidth: 2 }}>
          <polyline points={points} className="transition-all duration-500" />
        </svg>
        <div className="flex justify-between mt-1 text-[8px] font-mono text-gray-600">
          <span>{Math.min(...history)}</span>
          <span>{Math.max(...history)}</span>
        </div>
      </div>
    </div>
  );
}
