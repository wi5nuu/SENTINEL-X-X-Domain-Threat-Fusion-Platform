import { useEffect, useState, useRef } from "react";
import GlobalMap from "./components/GlobalMap";
import AlertTimeline from "./components/AlertTimeline";
import SensorStatusPanel from "./components/SensorStatusPanel";
import ThreatScoreGauge from "./components/ThreatScoreGauge";
import DomainToggle from "./components/DomainToggle";

type Alert = {
  alert_id: string;
  timestamp_utc: string;
  threat_class: string;
  confidence: number;
  domain: string;
  description: string;
};

function App() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [threatScore, setThreatScore] = useState(12);
  const [sensorStatus, setSensorStatus] = useState<Record<string, boolean>>({});
  const [activeDomains, setActiveDomains] = useState<Record<string, boolean>>({
    air: true,
    maritime: true,
    seismic: true,
    rf: true,
    cyber: true,
  });
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      const ws = new WebSocket("ws://localhost:8000/ws");
      ws.onopen = () => {
        setWsConnected(true);
        console.log("WS connected");
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "new_alert") {
            setAlerts((prev) => [msg.payload, ...prev].slice(0, 100));
          } else if (msg.type === "pong") {
            //
          }
        } catch {}
      };
      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimer = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
      wsRef.current = ws;
    };

    connect();
    return () => {
      clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const resp = await fetch("/api/v1/alerts?limit=20");
        if (resp.ok) {
          const data = await resp.json();
          if (Array.isArray(data)) setAlerts(data);
        }
      } catch {}
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 10000);
    return () => clearInterval(interval);
  }, []);

  const toggleDomain = (id: string) => {
    setActiveDomains((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="min-h-screen bg-[#0A0E1A] text-[#00D4FF] p-3 font-mono">
      {/* Header */}
      <header className="border-b border-[#00D4FF]/20 pb-2 mb-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold tracking-[0.2em]">SENTINEL-X</h1>
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded ${
              wsConnected
                ? "bg-green-900/50 text-green-400"
                : "bg-red-900/50 text-red-400"
            }`}
          >
            {wsConnected ? "LIVE" : "OFFLINE"}
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <DomainToggle active={activeDomains} onToggle={toggleDomain} />
        </div>
      </header>

      {/* Metrics Bar */}
      <div className="grid grid-cols-5 gap-3 mb-3">
        <div className="bg-[#111827] border border-[#00D4FF]/10 rounded p-2">
          <div className="text-[10px] text-gray-500">EVENTS/HR</div>
          <div className="text-lg font-bold">12,847</div>
        </div>
        <div className="bg-[#111827] border border-[#00D4FF]/10 rounded p-2">
          <div className="text-[10px] text-gray-500">ACTIVE TRACKS</div>
          <div className="text-lg font-bold">43</div>
        </div>
        <div className="bg-[#111827] border border-[#00D4FF]/10 rounded p-2">
          <div className="text-[10px] text-gray-500">ALERTS (24H)</div>
          <div className="text-lg font-bold">{alerts.filter(a => a.threat_class !== "INFORMATIONAL").length}</div>
        </div>
        <div className="bg-[#111827] border border-[#00D4FF]/10 rounded p-2">
          <div className="text-[10px] text-gray-500">SENSORS</div>
          <div className="text-lg font-bold text-green-400">8/8</div>
        </div>
        <div className="bg-[#111827] border border-[#00D4FF]/10 rounded p-2">
          <div className="text-[10px] text-gray-500">BLOCKCHAIN</div>
          <div className="text-lg font-bold text-[#A855F7]">SYNCED</div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-12 gap-3 h-[calc(100vh-260px)]">
        {/* Threat Gauge */}
        <div className="col-span-1 bg-[#111827] border border-[#00D4FF]/10 rounded p-2 flex flex-col items-center justify-center">
          <ThreatScoreGauge score={threatScore} />
        </div>

        {/* Global Map */}
        <div className="col-span-7 bg-[#111827] border border-[#00D4FF]/10 rounded p-2 overflow-hidden">
          <div className="text-[10px] text-gray-500 mb-1">GLOBAL SITUATIONAL MAP</div>
          <GlobalMap
            tracks={[
              { lat: -6.2, lon: 106.8, label: "GIA881", color: "#00D4FF" },
              { lat: -6.1, lon: 106.7, label: "LNI324", color: "#22C55E" },
              { lat: -5.9, lon: 106.9, label: "MV NUSANTARA", color: "#A855F7" },
            ]}
          />
        </div>

        {/* Alert Timeline */}
        <div className="col-span-4 bg-[#111827] border border-[#00D4FF]/10 rounded p-2 overflow-hidden">
          <div className="text-[10px] text-gray-500 mb-1 flex justify-between">
            <span>LIVE ALERT FEED</span>
            <span className="text-[#00D4FF]">{alerts.length} alerts</span>
          </div>
          <AlertTimeline alerts={alerts} />
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="mt-3 grid grid-cols-12 gap-3">
        <div className="col-span-4 bg-[#111827] border border-[#00D4FF]/10 rounded p-2">
          <div className="text-[10px] text-gray-500 mb-1">SENSOR STATUS</div>
          <SensorStatusPanel status={sensorStatus} />
        </div>
        <div className="col-span-4 bg-[#111827] border border-[#00D4FF]/10 rounded p-2 text-[10px] text-gray-500">
          <div className="text-[10px] text-gray-500 mb-1">SYSTEM LOG</div>
          <div className="space-y-0.5">
            <div className="text-green-400">[OK] Kafka connected (broker: kafka:9092)</div>
            <div className="text-green-400">[OK] TimescaleDB connected</div>
            <div className="text-gray-600">[INFO] AI Engine idle — no batch ready</div>
            <div className="text-gray-600">[INFO] WebSocket: {wsConnected ? 'connected' : 'disconnected'}</div>
          </div>
        </div>
        <div className="col-span-4 bg-[#111827] border border-[#00D4FF]/10 rounded p-2">
          <div className="text-[10px] text-gray-500 mb-1">QUICK ACTIONS</div>
          <div className="grid grid-cols-2 gap-1 text-[10px]">
            <button className="bg-[#00D4FF]/10 border border-[#00D4FF]/30 rounded px-2 py-1 hover:bg-[#00D4FF]/20 transition-colors">
              Acknowledge All
            </button>
            <button className="bg-[#EF4444]/10 border border-[#EF4444]/30 rounded px-2 py-1 hover:bg-[#EF4444]/20 transition-colors">
              Emergency Mode
            </button>
            <button className="bg-[#A855F7]/10 border border-[#A855F7]/30 rounded px-2 py-1 hover:bg-[#A855F7]/20 transition-colors">
              Generate Report
            </button>
            <button className="bg-gray-800 border border-gray-700 rounded px-2 py-1 hover:bg-gray-700 transition-colors">
              Playbook Test
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
