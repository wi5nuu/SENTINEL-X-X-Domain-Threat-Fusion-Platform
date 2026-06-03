import { useEffect, useState } from "react";

interface TelemetryData {
  comm_status: string;
  ai_load: string;
  threat_count: number;
  naval_flow: string;
  uav_density: string;
  cyber_probes: number;
  rf_snr: string;
  ledger_tps: string;
}

export default function TacticalDataStrip({ 
  dashboard, 
  activeFilter, 
  onFilterChange 
}: { 
  dashboard: any, 
  activeFilter: string, 
  onFilterChange: (filter: string) => void 
}) {
  const [data, setData] = useState<TelemetryData>({
    comm_status: "NOMINAL",
    ai_load: "42%",
    threat_count: 23,
    naval_flow: "142 v/h",
    uav_density: "89%",
    cyber_probes: 156,
    rf_snr: "18.2 dB",
    ledger_tps: "124 TPS"
  });

  useEffect(() => {
    const iv = setInterval(() => {
      setData({
        comm_status: Math.random() > 0.95 ? "DEGRADED" : "NOMINAL",
        ai_load: (30 + Math.random() * 40).toFixed(0) + "%",
        threat_count: Math.floor(20 + Math.random() * 10),
        naval_flow: Math.floor(130 + Math.random() * 20) + " v/h",
        uav_density: (80 + Math.random() * 15).toFixed(0) + "%",
        cyber_probes: Math.floor(100 + Math.random() * 100),
        rf_snr: (15 + Math.random() * 5).toFixed(1) + " dB",
        ledger_tps: Math.floor(100 + Math.random() * 50) + " TPS"
      });
    }, 2000);
    return () => clearInterval(iv);
  }, []);

  const cards = [
    { id: "all", label: "COMM STATUS", value: data.comm_status, color: "#22C55E" },
    { id: "threats", label: "AI ENGINE LOAD", value: data.ai_load, color: "#A855F7" },
    { id: "missiles", label: "ACTIVE THREATS", value: data.threat_count.toString(), color: "#FF3300" },
    { id: "warships", label: "NAVAL TRAFFIC", value: data.naval_flow, color: "#00D4FF" },
    { id: "drones", label: "UAV DENSITY", value: data.uav_density, color: "#F59E0B" },
    { id: "cyber", label: "CYBER PROBES", value: data.cyber_probes.toString(), color: "#FF4444" },
    { id: "rf", label: "RF SNR", value: data.rf_snr, color: "#EAB308" },
    { id: "ledger", label: "LEDGER TPS", value: data.ledger_tps, color: "#22C55E" },
  ];

  return (
    <div className="grid grid-cols-8 gap-1 px-1 py-1 bg-[#050B14] border-t border-[#1E3A5F] shrink-0">
      {cards.map((c, i) => (
        <button 
          key={i} 
          onClick={() => onFilterChange(activeFilter === c.id ? "all" : c.id)}
          className={`bg-[#0A0E1A] border p-1 rounded flex flex-col items-center justify-center transition-all outline-none ${
            activeFilter === c.id 
            ? "border-[#00D4FF] bg-[#1E3A5F]/20" 
            : "border-[#1E3A5F]/40 hover:border-[#00D4FF]/40"
          }`}
        >
          <span className="text-[7px] font-bold text-gray-500 uppercase tracking-tighter w-full text-center">{c.label}</span>
          <span className="text-[11px] font-bold font-mono mt-0.5" style={{ color: c.color }}>{c.value}</span>
        </button>
      ))}
    </div>
  );
}
