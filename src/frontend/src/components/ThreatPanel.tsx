import { useEffect, useState } from "react";

type Alert = {
  alert_id: string;
  threat_class: string;
  domain: string;
  description?: string;
  confidence?: number;
};

export default function ThreatPanel({
  score,
  alerts,
  domainCounts,
}: {
  score: number;
  alerts: Alert[];
  domainCounts: Record<string, number>;
}) {
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    if (score >= 60) {
      const t = setInterval(() => setPulse((p) => !p), 1000);
      return () => clearInterval(t);
    }
    setPulse(false);
  }, [score]);

  const r = 38;
  const circumference = 2 * Math.PI * r;
  const progress = Math.min(score / 100, 1);
  const offset = circumference * (1 - progress);

  const color =
    score < 25 ? "#22C55E"
    : score < 50 ? "#F59E0B"
    : score < 75 ? "#F97316"
    : "#EF4444";

  const level =
    score < 10 ? "NOMINAL"
    : score < 25 ? "LOW"
    : score < 50 ? "ELEVATED"
    : score < 75 ? "HIGH"
    : "CRITICAL";

  const criticalCount = alerts.filter((a) => a.threat_class === "CATASTROPHIC" || a.threat_class === "CRITICAL").length;
  const topDomain = [...new Set(alerts.filter((a) => a.threat_class === "CATASTROPHIC" || a.threat_class === "CRITICAL").map((a) => a.domain))].slice(0, 3);
  const totalEvents = Object.values(domainCounts).reduce((s, v) => s + v, 0);

  return (
    <div className="flex flex-col items-center gap-2 w-full">
      <div className="relative">
        <svg width="100" height="100" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r={r} fill="none" stroke="#1F2937" strokeWidth="6" />
          <circle
            cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="6"
            strokeDasharray={circumference} strokeDashoffset={offset}
            strokeLinecap="round" transform="rotate(-90 50 50)"
            className="transition-all duration-1000"
          />
          <text x="50" y="42" textAnchor="middle" dominantBaseline="central" fill={color} fontSize="22" fontFamily="monospace" fontWeight="bold">
            {Math.round(score)}
          </text>
          <text x="50" y="62" textAnchor="middle" dominantBaseline="central" fill="#9CA3AF" fontSize="8" fontFamily="monospace">
            {level}
          </text>
        </svg>
        {pulse && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-full h-full rounded-full animate-ping border-2" style={{ borderColor: color, opacity: 0.25 }} />
          </div>
        )}
      </div>

      <div className="text-[10px] text-gray-500 font-bold tracking-wider">THREAT SCORE</div>

      <div className="w-full pt-1.5 space-y-1.5">
        <div className="flex items-center justify-between text-[10px]">
          <span className="text-gray-500">Critical</span>
          <span className="text-red-400 font-mono font-bold">{criticalCount}</span>
        </div>

        {topDomain.length > 0 && (
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-gray-500">Top Threat</span>
            <span className="text-[#F97316] font-mono uppercase">{topDomain[0]}</span>
          </div>
        )}

        <div className="flex items-center justify-between text-[10px]">
          <span className="text-gray-500">Events</span>
          <span className="text-[#00D4FF] font-mono">{totalEvents.toLocaleString()}</span>
        </div>

        <div className="flex items-center justify-between text-[10px]">
          <span className="text-gray-500">Level</span>
          <span className="font-mono font-bold" style={{ color }}>{level}</span>
        </div>
      </div>
    </div>
  );
}
