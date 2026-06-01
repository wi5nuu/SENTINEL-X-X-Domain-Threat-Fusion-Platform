import { useEffect, useState, useRef } from "react";

type Alert = {
  alert_id: string;
  timestamp_utc: string;
  threat_class: string;
  confidence: number;
  domain: string;
  description: string;
  acknowledged: boolean;
};

const THREAT_COLORS: Record<string, string> = {
  INFORMATIONAL: "#6B7280",
  SUSPICIOUS: "#F59E0B",
  ELEVATED: "#EF4444",
  CRITICAL: "#DC2626",
  CATASTROPHIC: "#7F1D1D",
};

function App() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [threatScore, setThreatScore] = useState(0);
  const [sensorStatus, setSensorStatus] = useState<Record<string, boolean>>({});
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws");
    ws.onopen = () => console.log("WS connected");
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "new_alert") {
          setAlerts((prev) => [msg.payload, ...prev].slice(0, 100));
        }
      } catch {}
    };
    ws.onclose = () => setTimeout(() => (window.location.reload()), 5000);
    wsRef.current = ws;
    return () => ws.close();
  }, []);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const resp = await fetch("/api/v1/alerts?limit=20");
        if (resp.ok) setAlerts(await resp.json());
      } catch {}
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#0A0E1A] text-[#00D4FF] p-4">
      {/* Header */}
      <header className="border-b border-[#00D4FF]/20 pb-2 mb-4 flex justify-between items-center">
        <h1 className="text-xl font-bold tracking-widest">SENTINEL</h1>
        <div className="flex gap-4 text-xs">
          <span>Threat Score: <span className="text-lg font-bold">{threatScore}</span></span>
          <span>Alerts: <span className="text-lg font-bold">{alerts.length}</span></span>
        </div>
      </header>

      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-4 h-[calc(100vh-100px)]">
        {/* Map Panel */}
        <div className="col-span-8 bg-[#111827] border border-[#00D4FF]/20 rounded p-2">
          <div className="text-xs text-gray-500 mb-2">GLOBAL MAP</div>
          <div className="bg-[#0A0E1A] h-[80%] rounded flex items-center justify-center text-gray-600 text-sm">
            Map View — Requires CesiumJS or Leaflet tiles
          </div>
        </div>

        {/* Alert Panel */}
        <div className="col-span-4 bg-[#111827] border border-[#00D4FF]/20 rounded p-2 overflow-y-auto">
          <div className="text-xs text-gray-500 mb-2">LIVE ALERTS</div>
          {alerts.map((a) => (
            <div
              key={a.alert_id}
              className="border-l-4 mb-2 pl-2 py-1 text-xs"
              style={{ borderColor: THREAT_COLORS[a.threat_class] || "#6B7280" }}
            >
              <div className="flex justify-between">
                <span style={{ color: THREAT_COLORS[a.threat_class] }}>
                  {a.threat_class}
                </span>
                <span className="text-gray-500">{a.confidence.toFixed(2)}</span>
              </div>
              <div className="text-gray-300 truncate">{a.description}</div>
              <div className="text-gray-600">{a.domain}</div>
            </div>
          ))}
        </div>

        {/* Domain Toggles */}
        <div className="col-span-12 bg-[#111827] border border-[#00D4FF]/20 rounded p-2 flex gap-4 text-xs">
          {["Air", "Maritime", "Seismic", "RF", "Cyber"].map((d) => (
            <label key={d} className="flex items-center gap-1 cursor-pointer">
              <input type="checkbox" defaultChecked className="accent-[#00D4FF]" />
              {d}
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
