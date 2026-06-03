import { useEffect, useState } from "react";

interface Metric {
  label: string;
  value: string | number;
  color: string;
  trend: "up" | "down" | "flat";
  source: string;
}

export default function TacticalMetricsPanel({ activeFilter, onFilterChange }: { activeFilter: string, onFilterChange: (f: string) => void }) {
  const [metrics, setMetrics] = useState<Metric[]>([
    { label: "COMM LINK", value: "12.4 MB/s", color: "#00D4FF", trend: "up", source: "SAT" },
    { label: "AI LOAD", value: "42%", color: "#A855F7", trend: "flat", source: "CORE" },
    { label: "CYBER", value: "156", color: "#EF4444", trend: "up", source: "IDS" },
    { label: "RF SNR", value: "18.2 dB", color: "#EAB308", trend: "down", source: "SDR" },
    { label: "THREATS", value: "23", color: "#FF3300", trend: "up", source: "AI" },
    { label: "NAVAL", value: "142 v/h", color: "#22C55E", trend: "flat", source: "AIS" },
    { label: "UAV OPS", value: "89%", color: "#F59E0B", trend: "down", source: "ADSB" },
    { label: "LEDGER", value: "124 TPS", color: "#22C55E", trend: "up", source: "CHN" },
  ]);

  useEffect(() => {
    const iv = setInterval(() => {
      setMetrics(prev => prev.map(m => ({
        ...m,
        value: m.label === "THREATS" ? (Math.floor(20 + Math.random() * 10)).toString() : m.value,
        trend: Math.random() > 0.5 ? "up" : "down"
      })));
    }, 2000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div className="flex flex-col w-full bg-[#050B14]/80 border border-[#1E3A5F] rounded-sm overflow-hidden">
      {metrics.map((m, i) => (
        <button 
          key={i} 
          onClick={() => onFilterChange(activeFilter === m.label.toLowerCase() ? "all" : m.label.toLowerCase())}
          className={`group flex items-center justify-between px-3 py-1.5 border-b border-[#1E3A5F]/30 transition-all ${
            activeFilter === m.label.toLowerCase() ? "bg-[#1E3A5F]/40" : "hover:bg-[#1E3A5F]/20"
          }`}
        >
          <div className="flex flex-col items-start">
            <span className="text-[7px] font-bold text-gray-500 uppercase tracking-widest group-hover:text-gray-300 transition-colors">{m.label}</span>
            <span className="text-[6px] text-gray-600 font-mono tracking-wider">{m.source}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold font-mono" style={{ color: m.color }}>{m.value}</span>
            <span className={`text-[8px] ${m.trend === 'up' ? 'text-red-500' : 'text-green-500'}`}>
              {m.trend === 'up' ? '▲' : '▼'}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}
