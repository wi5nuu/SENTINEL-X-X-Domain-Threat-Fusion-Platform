

import { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import GlobalMap from "./components/GlobalMap";
import AlertTimeline from "./components/AlertTimeline";
import ThreatPanel from "./components/ThreatPanel";
import DomainActivityPanel from "./components/DomainActivityPanel";
import SensorStatusPanel from "./components/SensorStatusPanel";
import DomainToggle from "./components/DomainToggle";
import ThreatScoreGauge from "./components/ThreatScoreGauge";
import AlertVolumeChart from "./components/AlertVolumeChart";
import StatsPage from "./StatsPage";
import GlobalStatusPage from "./GlobalStatusPage";
import Globe3D from "./components/Globe3D";

import SituationalTicker from "./components/SituationalTicker";
import TacticalAnalyst from "./components/TacticalAnalyst";
import TacticalDataStrip from "./components/TacticalDataStrip";

export type Alert = {
  alert_id: string;
  timestamp_utc: string;
  threat_class: string;
  confidence: number;
  domain: string;
  description: string;
  ipfs_hash?: string;
};

export type Track = {
  lat: number; lon: number; label?: string; color?: string;
  domain?: string; classification?: string; velocity?: number;
  is_threat?: boolean; squawk?: string; altitude?: number;
  heading?: number; is_missile?: boolean;
  missile_type?: string; missile_id?: string;
  origin_lat?: number; origin_lon?: number; origin_name?: string;
  target_lat?: number; target_lon?: number; target_name?: string;
  speed_mach?: number; accuracy_cep_m?: number;
  launch_time?: string; eta_seconds?: number;
  distance_km?: number; flight_progress_pct?: number;
  origin_country?: string;
};

export type DashboardData = {
  events_per_hour: number;
  active_tracks: { air: number; maritime: number; total: number };
  alerts_24h: number;
  recent_alerts: Alert[];
  threat_score: number;
  sensors: Record<string, boolean>;
  blockchain_synced: boolean;
  tracks: Track[];
  domain_counts: Record<string, number>;
};

export const SEVERITY_ORDER = ["CATASTROPHIC", "CRITICAL", "ELEVATED", "SUSPICIOUS", "INFORMATIONAL"];
const MAX_TRACK_HISTORY = 30;

function playSiren(audioCtx: AudioContext | null) {
  if (!audioCtx) return;
  try {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sawtooth";
    gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    const t = audioCtx.currentTime;
    osc.frequency.setValueAtTime(800, t);
    osc.frequency.linearRampToValueAtTime(1600, t + 0.3);
    osc.frequency.linearRampToValueAtTime(800, t + 0.6);
    osc.frequency.linearRampToValueAtTime(1600, t + 0.9);
    osc.frequency.linearRampToValueAtTime(800, t + 1.2);
    osc.start(t);
    osc.stop(t + 1.5);
  } catch { }
}

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [threatScore, setThreatScore] = useState(0);
  const [sensorStatus, setSensorStatus] = useState<Record<string, boolean>>({});
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [actionFeedback, setActionFeedback] = useState("");
  const [emergencyFlash, setEmergencyFlash] = useState(false);
  const [emergencyMsg, setEmergencyMsg] = useState("");
  const [showChainModal, setShowChainModal] = useState(false);
  const [chainHash, setChainHash] = useState("");
  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [entityFilter, setEntityFilter] = useState<string>("all");
  const [domainFilters, setDomainFilters] = useState<Record<string, boolean>>({ air: true, maritime: true, seismic: true, rf: true, cyber: true });
  const [sidebarWidth, setSidebarWidth] = useState(300);
  const isDragging = useRef(false);
  const hudRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const newWidth = Math.max(150, Math.min(e.clientX, 600));
      setSidebarWidth(newWidth);
    };
    const handleMouseUp = () => { isDragging.current = false; };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);
  const notifiedRef = useRef<Set<string>>(new Set());
  const audioCtxRef = useRef<AudioContext | null>(null);
  const trackHistoryRef = useRef<Map<string, Track[]>>(new Map());

  useEffect(() => {
    audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    return () => { audioCtxRef.current?.close(); };
  }, []);

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout>;
    const connect = () => {
      const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${wsProto}//${window.location.host}/ws`;
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => setWsConnected(true);
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "new_alert") {
            const alert: Alert = msg.payload;
            setAlerts((prev) => [alert, ...prev].slice(0, 100));
            if ((alert.threat_class === "CATASTROPHIC" || alert.threat_class === "CRITICAL") && !notifiedRef.current.has(alert.alert_id)) {
              notifiedRef.current.add(alert.alert_id);
              if (alert.threat_class === "CATASTROPHIC") {
                setEmergencyMsg(alert.description);
                setEmergencyFlash(true);
                setTimeout(() => setEmergencyFlash(false), 7000);
                playSiren(audioCtxRef.current);
              }
              if ("Notification" in window && Notification.permission === "granted") {
                new Notification(`[${alert.threat_class}] ${alert.domain} alert`, { body: alert.description });
              }
            }
          }
        } catch { }
      };
      ws.onclose = () => { setWsConnected(false); reconnectTimer = setTimeout(connect, 3000); };
      ws.onerror = () => ws.close();
      wsRef.current = ws;
    };
    connect();
    if ("Notification" in window && Notification.permission === "default") Notification.requestPermission();
    return () => { clearTimeout(reconnectTimer); wsRef.current?.close(); };
  }, []);

  const fetchDashboard = useCallback(async () => {
    try {
      const resp = await fetch("/api/v1/dashboard");
      if (!resp.ok) return;
      const data: DashboardData = await resp.json();
      setDashboard(data);
      setThreatScore(data.threat_score);
      setSensorStatus(data.sensors);
      setTracks(data.tracks);
      console.log("Tracks updated:", data.tracks.length, data.tracks.slice(0, 5));

      const hist = trackHistoryRef.current;
      for (const t of data.tracks) {
        const key = t.label || `${t.lat}_${t.lon}`;
        if (!hist.has(key)) hist.set(key, []);
        const arr = hist.get(key)!;
        arr.push(t);
        if (arr.length > MAX_TRACK_HISTORY) arr.shift();
      }
      for (const [k, arr] of hist) {
        const stillExists = data.tracks.some((t: Track) => (t.label || `${t.lat}_${t.lon}`) === k);
        if (!stillExists && arr.length > 0) { if (Date.now() - new Date().getTime() > 30000) hist.delete(k); }
      }
      if (data.recent_alerts.length > 0) {
        setAlerts((prev) => {
          const existing = new Set(prev.map((a) => a.alert_id));
          const newOnes = data.recent_alerts.filter((a) => !existing.has(a.alert_id));
          return newOnes.length > 0 ? [...newOnes, ...prev].slice(0, 100) : prev;
        });
        for (const a of data.recent_alerts) {
          if ((a.threat_class === "CATASTROPHIC" || a.threat_class === "CRITICAL") && !notifiedRef.current.has(a.alert_id)) {
            notifiedRef.current.add(a.alert_id);
            if (a.threat_class === "CATASTROPHIC") {
              setEmergencyMsg(a.description);
              setEmergencyFlash(true);
              setTimeout(() => setEmergencyFlash(false), 7000);
              playSiren(audioCtxRef.current);
            }
          }
        }
      }
    } catch { }
  }, []);

  useEffect(() => { fetchDashboard(); const iv = setInterval(fetchDashboard, 5000); return () => clearInterval(iv); }, [fetchDashboard]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement || e.target instanceof HTMLTextAreaElement) return;
      switch (e.key.toLowerCase()) {
        case "f": document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen(); break;
        case "escape": setEmergencyFlash(false); break;
        case "1": setActiveNav("overview"); break;
        case "2": setActiveNav("map"); break;
        case "3": setActiveNav("threats"); break;
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const doAction = async (endpoint: string, label: string) => {
    setActionFeedback(`${label}...`);
    try { const resp = await fetch(endpoint, { method: "POST" }); setActionFeedback(resp.ok ? `${label}: OK` : `${label}: failed`); }
    catch { setActionFeedback(`${label}: error`); }
    setTimeout(() => setActionFeedback(""), 3000);
  };

  const viewBlockchain = (hash: string) => { setChainHash(hash); setShowChainModal(true); };
  const toggleAcknowledge = (id: string) => { setAcknowledgedAlerts((prev) => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next; }); };

  const eventsPerHr = dashboard?.events_per_hour.toLocaleString() ?? "—";
  const activeTracks = dashboard?.active_tracks.total ?? 0;
  const alerts24h = dashboard?.alerts_24h ?? 0;
  const sensorsOnline = Object.values(sensorStatus).filter(Boolean).length;
  const sensorsTotal = Object.keys(sensorStatus).length || 8;
  const catCount = alerts.filter((a) => a.threat_class === "CATASTROPHIC").length;
  const critCount = alerts.filter((a) => a.threat_class === "CRITICAL").length;
  const highCount = alerts.filter((a) => a.threat_class === "ELEVATED").length;

  const filteredTracks = tracks.filter((t) => {
    if (entityFilter === "all") return true;
    if (entityFilter === "missiles") return !!t.is_missile;
    if (entityFilter === "threats") return !!t.is_threat;
    if (entityFilter === "military") return t.classification === "military" && !t.is_missile;
    if (entityFilter === "aircraft") return t.classification === "commercial" || t.classification === "private";
    if (entityFilter === "drones") return t.classification === "uav";
    if (entityFilter === "unidentified") return t.classification === "unidentified";
    if (entityFilter === "warships") return t.domain === "maritime" || (t.classification === "military" && t.domain === "maritime");
    return true;
  });

  const trackHistory = Array.from(trackHistoryRef.current.values()).filter((arr) => {
    return filteredTracks.some((t) => (t.label || `${t.lat}_${t.lon}`) === (arr[0]?.label || ""));
  });

  const [activeNav, setActiveNav] = useState("overview");
  const [clock, setClock] = useState("");
  const [mapMode, setMapMode] = useState<"2d" | "3d">("2d");

  useEffect(() => {
    const updateClock = () => {
      setClock(new Date().toISOString().slice(11, 19) + " UTC");
    };
    updateClock();
    const iv = setInterval(updateClock, 1000);
    return () => clearInterval(iv);
  }, []);

  if (location.pathname === "/statistik") {
    return <StatsPage alerts={alerts} tracks={tracks} dashboard={dashboard} eventsPerHr={eventsPerHr} threatScore={threatScore} onClose={() => navigate("/")} />;
  }
  if (location.pathname === "/global-status") {
    return <GlobalStatusPage alerts={alerts} tracks={tracks} dashboard={dashboard} eventsPerHr={eventsPerHr} threatScore={threatScore} onClose={() => navigate("/")} />;
  }

  return (
    <div ref={hudRef} className="h-screen flex flex-col overflow-hidden" style={{ background: "#0A0E1A", color: "#94A3B8", fontFamily: "monospace" }}>

      {emergencyFlash && (
        <div className="fixed inset-0 z-[9999] pointer-events-none flex items-center justify-center">
          <div className="absolute inset-0" style={{ backgroundColor: "rgba(127,29,29,0.3)", animation: "pulse 1s infinite" }} />
          <div className="relative z-10 p-4 text-center" style={{ background: "#1A0A0A", border: "2px solid #7F1D1D", borderRadius: 8 }}>
            <div className="text-red-400 font-bold text-lg">CATASTROPHIC THREAT</div>
            <div className="text-yellow-400 text-xs">{emergencyMsg}</div>
          </div>
        </div>
      )}

      {showChainModal && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center" style={{ backgroundColor: "rgba(0,0,0,0.6)" }} onClick={() => setShowChainModal(false)}>
          <div className="p-4 rounded border max-w-md w-[90%]" style={{ background: "#0A0E1A", borderColor: "rgba(0,212,255,0.2)" }} onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-3">
              <span className="text-[#A855F7] text-xs font-bold tracking-wider">BLOCKCHAIN EVIDENCE</span>
              <button onClick={() => setShowChainModal(false)} className="text-gray-600 hover:text-white">✕</button>
            </div>
            <div className="bg-[#050B14] border border-gray-800 rounded p-2 text-xs text-gray-400 break-all font-mono mb-3">{chainHash}</div>
            <a href={`http://localhost:8081/ipfs/${chainHash}`} target="_blank" rel="noopener noreferrer"
              className="block text-center text-xs py-2 rounded border" style={{ color: "#A855F7", borderColor: "rgba(168,85,247,0.3)" }}>
              View on IPFS
            </a>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between px-2 py-1 shrink-0 border-b" style={{ borderColor: "#1E3A5F" }}>
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold tracking-widest" style={{ color: "#00D4FF" }}>SENTINEL-X</span>
          <span className="text-gray-600">|</span>
          <span className="text-xs" style={{ color: threatScore === 0 ? "#22C55E" : threatScore < 30 ? "#22C55E" : threatScore < 60 ? "#F59E0B" : "#EF4444" }}>
            THREAT {threatScore}%
          </span>
          <span className={`w-2 h-2 rounded-full ${wsConnected ? "bg-green-400" : "bg-red-500 animate-pulse"}`} />
          <span className="text-[10px] text-gray-600">{clock}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-600">SENSORS {sensorsOnline}/{sensorsTotal}</span>
          <span className="text-gray-700">|</span>
          <button onClick={() => navigate("/statistik")} className="text-[10px] px-2 py-0.5 rounded border" style={{ color: "#00D4FF", borderColor: "rgba(0,212,255,0.3)" }}>STATS</button>
          <button onClick={() => navigate("/global-status")} className="text-[10px] px-2 py-0.5 rounded border" style={{ color: "#F59E0B", borderColor: "rgba(245,158,11,0.3)" }}>GLOBAL</button>
          <button
            onClick={() => setMapMode(m => m === "2d" ? "3d" : "2d")}
            className="text-[10px] px-2 py-0.5 rounded border font-bold"
            style={{
              color: mapMode === "3d" ? "#A855F7" : "#6E7B91",
              borderColor: mapMode === "3d" ? "rgba(168,85,247,0.5)" : "rgba(110,123,145,0.3)",
              background: mapMode === "3d" ? "rgba(168,85,247,0.1)" : "transparent"
            }}
          >{mapMode === "3d" ? "3D GLOBE" : "2D MAP"}</button>
        </div>
      </div>

      <TacticalDataStrip dashboard={dashboard} activeFilter={entityFilter} onFilterChange={setEntityFilter} />

      <SituationalTicker />

      <div className="flex-1 flex min-h-0">
        {/* LEFT SIDEBAR: ALERTS */}
        <div className="flex flex-col p-1 gap-1 overflow-y-auto shrink-0 border-r relative" style={{ width: `${sidebarWidth}px`, borderColor: "#1E3A5F", background: "#050B14" }}>
          <div 
            className="absolute right-0 top-0 w-1 h-full cursor-col-resize hover:bg-[#00D4FF] z-[100]"
            onMouseDown={() => { isDragging.current = true; }}
          />
          <div className="flex-1 min-h-0 rounded border overflow-hidden" style={{ background: "#0A0E1A", borderColor: "rgba(0,212,255,0.1)" }}>
            <div className="flex items-center justify-between px-2 py-1 border-b text-[10px]" style={{ borderColor: "#1E3A5F" }}>
              <span className="text-gray-500 font-bold">ALERTS</span>
              <div className="flex items-center gap-2">
                <span className="text-gray-600">{alerts.length}</span>
                <button onClick={() => { const s = new Set(acknowledgedAlerts); alerts.forEach(a => s.add(a.alert_id)); setAcknowledgedAlerts(s); }}
                  className="text-gray-600 hover:text-gray-400 text-[9px]">ACK ALL</button>
              </div>
            </div>
            <AlertTimeline alerts={alerts} severityFilter="" onViewBlockchain={viewBlockchain} acknowledgedAlerts={acknowledgedAlerts} onToggleAcknowledge={toggleAcknowledge} />
          </div>
        </div>

        {/* MAP */}
        <div className="flex-1 flex flex-col min-w-0 p-1">
          <div className="flex-1 min-h-0 rounded overflow-hidden border" style={{ borderColor: "rgba(0,212,255,0.1)", position: "relative" }}>
            {mapMode === "2d"
              ? <GlobalMap tracks={filteredTracks} trackHistory={trackHistory} searchQuery={searchQuery} entityFilter={entityFilter} onFilterByType={setEntityFilter} />
              : <Globe3D tracks={filteredTracks} />
            }
          </div>
          <div className="flex items-center gap-2 mt-1 shrink-0">
            <DomainToggle active={domainFilters} onToggle={(id) => setDomainFilters((p) => ({ ...p, [id]: !p[id] }))} />
            <input type="text" placeholder="Search bases, sectors..."
              value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1 px-2 py-1 text-xs rounded border" style={{ background: "#0A0E1A", borderColor: "#1E3A5F", color: "#94A3B8", outline: "none" }}
            />
            <span className="text-[10px] text-gray-600">{tracks.length} tracks</span>
            <span className="text-[10px] text-gray-600">{eventsPerHr} ev/h</span>
          </div>
        </div>

        <div className="w-[340px] flex flex-col p-1 gap-1 overflow-y-auto shrink-0 border-l" style={{ borderColor: "#1E3A5F" }}>
          <div className="rounded border p-2" style={{ background: "#0A0E1A", borderColor: "rgba(0,212,255,0.1)" }}>
            <ThreatScoreGauge score={threatScore} />
          </div>

          <div className="rounded border p-2" style={{ background: "#0A0E1A", borderColor: "rgba(0,212,255,0.1)" }}>
            <DomainActivityPanel counts={dashboard?.domain_counts || {}} />
          </div>

          <div className="rounded border p-2" style={{ background: "#0A0E1A", borderColor: "rgba(0,212,255,0.1)" }}>
            <SensorStatusPanel status={sensorStatus} activeFilter={entityFilter} onFilterChange={setEntityFilter} />
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between px-2 py-1 shrink-0 border-t text-[10px]" style={{ borderColor: "#1E3A5F" }}>
        <div className="flex items-center gap-2">
          <button onClick={() => doAction("/api/v1/actions/emergency", "EMERGENCY")}
            className="px-2 py-0.5 rounded font-bold text-red-400 border" style={{ borderColor: "rgba(239,68,68,0.4)", background: "rgba(239,68,68,0.1)" }}>
            EMERGENCY
          </button>
          <button onClick={() => doAction("/api/v1/actions/acknowledge_all", "ACK ALL")}
            className="px-2 py-0.5 rounded border text-gray-400" style={{ borderColor: "#1E3A5F" }}>
            ACK ALL
          </button>
          <button onClick={() => doAction("/api/v1/actions/generate_report", "REPORT")}
            className="px-2 py-0.5 rounded border text-gray-400" style={{ borderColor: "#1E3A5F" }}>
            REPORT
          </button>
          {actionFeedback && <span className="text-gray-500">{actionFeedback}</span>}
        </div>
        <span className="text-gray-700">{activeTracks} tracks · {catCount + critCount + highCount} alerts</span>
      </div>
      <TacticalAnalyst />
    </div>
  );
}

export default App;