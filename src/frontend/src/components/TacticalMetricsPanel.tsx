import { useEffect, useState } from "react";

interface Metric {
  label: string;
  value: string | number;
  color: string;
  trend: "up" | "down" | "flat";
  progress: number; // 0-100
  category: "SYSTEM" | "TACTICAL";
}

export default function TacticalMetricsPanel({ activeFilter, onFilterChange }: { activeFilter: string, onFilterChange: (f: string) => void }) {
  const [metrics, setMetrics] = useState<Metric[]>([
    { label: "COMM LINK", value: "12.4 MB/s", color: "#00D4FF", trend: "up", progress: 45, category: "SYSTEM" },
    { label: "AI LOAD", value: "42%", color: "#A855F7", trend: "flat", progress: 42, category: "SYSTEM" },
    { label: "CYBER", value: "156", color: "#EF4444", trend: "up", progress: 75, category: "SYSTEM" },
    { label: "RF SNR", value: "18.2 dB", color: "#EAB308", trend: "down", progress: 60, category: "SYSTEM" },
    { label: "THREATS", value: "23", color: "#FF3300", trend: "up", progress: 85, category: "TACTICAL" },
    { label: "NAVAL", value: "142 v/h", color: "#22C55E", trend: "flat", progress: 30, category: "TACTICAL" },
    { label: "UAV OPS", value: "89%", color: "#F59E0B", trend: "down", progress: 89, category: "TACTICAL" },
    { label: "LEDGER", value: "124 TPS", color: "#22C55E", trend: "up", progress: 55, category: "TACTICAL" },
  ]);

  const [logs, setLogs] = useState<string[]>([
    "> UAV ENGAGED: SECTOR 7",
    "> RF JAMMING DETECTED: SECTOR 4",
    "> SATELLITE LINK: STABLE"
  ]);

  useEffect(() => {
    const iv = setInterval(() => {
      setMetrics(prev => prev.map(m => ({
        ...m,
        value: m.label === "THREATS" ? (Math.floor(20 + Math.random() * 10)).toString() : m.value,
        progress: Math.min(100, Math.max(0, m.progress + (Math.random() - 0.5) * 10)),
        trend: Math.random() > 0.5 ? "up" : "down"
      })));
      
      const newLog = Math.random() > 0.6 ? "> SENSOR SYNC: SECTOR " + Math.floor(Math.random()*10) : "> DATA BURST: PACKET LOSS 0.02%";
      setLogs(prev => [newLog, ...prev.slice(0, 2)]);
    }, 3000);
    return () => clearInterval(iv);
  }, []);

  const getTrendIcon = (trend: string) => {
    if (trend === "up") return <span className="text-red-500">▲</span>;
    if (trend === "down") return <span className="text-green-500">▼</span>;
    return <span className="text-gray-600">—</span>;
  };

  return (
    <div className="grid grid-cols-4 gap-1 p-1">
      {metrics.map((m, i) => (
        <button 
          key={i} 
          onClick={() => onFilterChange(activeFilter === m.label.toLowerCase() ? "all" : m.label.toLowerCase())}
          className={`bg-[#0A0E1A] border p-1 rounded flex flex-col justify-between transition-all outline-none ${
            activeFilter === m.label.toLowerCase() ? "border-[#00D4FF] bg-[#1E3A5F]/20" : "border-[#1E3A5F]/40"
          }`}
        >
          <div className="flex justify-between items-center w-full">
            <span className="text-[7px] font-bold text-gray-500 uppercase">{m.label}</span>
            {getTrendIcon(m.trend)}
          </div>
          <span className="text-[10px] font-bold font-mono" style={{ color: m.color }}>{m.value}</span>
        </button>
      ))}
      
      {/* Tactical Event Log */}
      <div className="col-span-4 bg-[#050B14] border border-[#1E3A5F] p-1.5 rounded mt-1 overflow-hidden">
        <span className="text-[7px] font-bold text-gray-500 uppercase tracking-tighter block mb-1">TACTICAL EVENT LOG</span>
        <div className="flex flex-col gap-0.5 font-mono text-[8px] text-gray-400 h-12 overflow-hidden">
          {logs.map((log, i) => <div key={i}>{log}</div>)}
        </div>
      </div>

      {/* Operational Readiness */}
      <div className="col-span-4 bg-[#050B14] border border-[#1E3A5F] p-1.5 rounded mt-1">
        <span className="text-[7px] font-bold text-gray-500 uppercase tracking-tighter block mb-1">OPERATIONAL READINESS</span>
        <div className="grid grid-cols-3 gap-1 text-[8px] font-mono text-gray-400">
          <div className="bg-[#0A0E1A] p-1 border border-[#1E3A5F] text-center">DEFCON: <span className="text-red-500 font-bold">3</span></div>
          <div className="bg-[#0A0E1A] p-1 border border-[#1E3A5F] text-center">GEOPOL: <span className="text-yellow-500">STABLE</span></div>
          <div className="bg-[#0A0E1A] p-1 border border-[#1E3A5F] text-center">LOGIS: <span className="text-green-500">GOOD</span></div>
        </div>
      </div>
    </div>
  );
}
