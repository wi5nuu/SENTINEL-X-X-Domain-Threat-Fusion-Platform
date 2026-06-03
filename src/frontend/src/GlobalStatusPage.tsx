import { useEffect, useState } from "react";
import { Alert, Track, DashboardData } from "./App";

/* ─── Glass panel wrapper ─────────────────────────────────────── */
function GlassPanel({ children, style, accent, className }: { children: React.ReactNode; style?: React.CSSProperties; accent?: string; className?: string }) {
  return (
    <div className={className} style={{
      background: "linear-gradient(135deg, rgba(14,26,43,0.9), rgba(10,16,30,0.95))",
      border: `1px solid ${accent ? `${accent}20` : "rgba(255,255,255,0.07)"}`,
      borderRadius: 12,
      backdropFilter: "blur(12px)",
      boxShadow: accent
        ? `0 2px 12px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05), 0 0 20px ${accent}08`
        : "0 2px 12px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
      transition: "transform 0.2s, box-shadow 0.2s",
      ...style,
    }}>
      {children}
    </div>
  );
}

/* ─── Section label ───────────────────────────────────────────── */
function SectionLabel({ children, color = "var(--text-muted)" }: { children: React.ReactNode; color?: string; }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      fontSize: 11, fontWeight: 700, color,
      textTransform: "uppercase", letterSpacing: "0.1em",
      marginBottom: 12,
    }}>
      <span>{children}</span>
      <div style={{ flex: 1, height: 1, background: `linear-gradient(90deg, ${color}40, transparent)`, marginLeft: 6 }} />
    </div>
  );
}

/* ─── Cyber Kill Chain ────────────────────────────────────────── */
function KillChainFlow() {
  const phases = [
    { label: "Reconnaissance", color: "#6E7B91", desc: "surveillance & footprint" },
    { label: "Weaponization", color: "#FFB020", desc: "payload preparation" },
    { label: "Delivery", color: "#FF8C00", desc: "vector deployment" },
    { label: "Exploitation", color: "#FF4D4F", desc: "breach in progress" },
    { label: "Installation", color: "#B80000", desc: "persistence established" },
    { label: "C2", color: "#A855F7", desc: "command channel active" },
    { label: "Actions", color: "#7C3AED", desc: "objective execution" },
  ];
  const currentPhase = 3;

  return (
    <GlassPanel className="stats-animate" style={{ padding: "16px", animationDelay: "0.1s" }} accent="#FF4D4F">
      <SectionLabel color="#FF4D4F">Active Cyber Kill Chain Status</SectionLabel>
      <div style={{ display: "flex", gap: 12, alignItems: "stretch", marginTop: 12 }}>
        {phases.map((p, i) => {
          const isActive = i === currentPhase;
          const isPast = i < currentPhase;
          const isFuture = i > currentPhase;
          const opacity = isFuture ? 0.4 : isActive ? 1 : 0.85;
          
          return (
            <div key={p.label} style={{ flex: 1, display: "flex", flexDirection: "column", opacity, position: "relative" }}>
              <div style={{
                padding: "16px 8px", borderRadius: 12, textAlign: "center",
                background: isActive ? `linear-gradient(180deg, ${p.color}22, ${p.color}0A)` : isPast ? `${p.color}11` : "rgba(255,255,255,0.02)",
                border: isActive ? `1px solid ${p.color}66` : `1px solid ${isPast ? p.color + '33' : 'rgba(255,255,255,0.04)'}`,
                boxShadow: isActive ? `0 0 24px ${p.color}33, inset 0 0 12px ${p.color}22` : "none",
                display: "flex", flexDirection: "column", gap: 8,
                height: "100%", justifyContent: "center",
                position: "relative", zIndex: 2
              }}>
                {isActive && (
                  <div style={{ position: "absolute", top: -1, left: "50%", transform: "translateX(-50%)", width: 40, height: 2, background: p.color, boxShadow: `0 0 12px ${p.color}` }} />
                )}
                <div style={{ fontSize: 11, fontWeight: 800, color: isActive || isPast ? p.color : "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{p.label}</div>
                <div style={{ fontSize: 10, color: "var(--text-secondary)", lineHeight: 1.3 }}>{p.desc}</div>
              </div>
              
              {/* Connector lines between blocks */}
              {i < phases.length - 1 && (
                <div style={{ 
                  position: "absolute", top: "50%", right: -12, width: 12, height: 2, 
                  background: isPast ? `linear-gradient(90deg, ${p.color}, ${phases[i+1].color})` : "rgba(255,255,255,0.08)", 
                  zIndex: 1 
                }} />
              )}
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 24, padding: "14px 20px", background: "rgba(255,77,79,0.05)", borderRadius: 12, border: "1px solid rgba(255,77,79,0.2)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#FF4D4F", boxShadow: "0 0 12px #FF4D4F", animation: "stat-glow 1.5s ease infinite" }} />
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Current Phase: <span style={{ color: "#FF4D4F", fontWeight: 800, letterSpacing: "0.05em" }}>EXPLOITATION</span></span>
        </div>
        <span style={{ fontSize: 12, color: "#FF4D4F", fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.05em" }}>CONTAINMENT PROTOCOL INITIATED — STANDBY</span>
      </div>
    </GlassPanel>
  );
}

/* ─── Scenario Card ───────────────────────────────────────────── */
function ScenarioCard({ s, delay }: { s: any; delay: number }) {
  const probColor = s.prob === "CRITICAL" || s.prob === "HIGH" ? "#FF4D4F" : s.prob === "ELEVATED" ? "#FFB020" : "var(--text-muted)";
  const sevColor = s.severity === "CATASTROPHIC" ? "#B80000" : s.severity === "CRITICAL" ? "#FF4D4F" : "#FF8C00";
  return (
    <GlassPanel className="stats-animate" style={{ padding: "16px", animationDelay: `${delay}s`, display: "flex", flexDirection: "column" }} accent={probColor}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.05em" }}>{s.title}</span>
        <span style={{ fontSize: 10, fontWeight: 800, color: probColor, background: `${probColor}15`, padding: "4px 10px", borderRadius: 6, border: `1px solid ${probColor}30`, letterSpacing: "0.1em" }}>{s.prob}</span>
      </div>
      <div style={{ display: "flex", gap: 20, fontSize: 12, color: "var(--text-muted)", marginBottom: 16, paddingBottom: 16, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", opacity: 0.8 }}>Severity</span>
          <span style={{ color: sevColor, fontWeight: 800, fontFamily: "'JetBrains Mono', monospace", textShadow: `0 0 10px ${sevColor}55` }}>{s.severity}</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", opacity: 0.8 }}>Timeline</span>
          <span style={{ color: "var(--text-primary)", fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>{s.timeline}</span>
        </div>
      </div>
      <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: 20, flex: 1 }}>{s.detail}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 10px", background: "rgba(77,163,255,0.04)", borderRadius: 8, border: "1px solid rgba(77,163,255,0.15)" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={{ fontSize: 9, color: "#4DA3FF", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.1em" }}>Response Plan</span>
          <span style={{ fontSize: 12, color: "var(--text-primary)", fontWeight: 500 }}>{s.prep}</span>
        </div>
      </div>
    </GlassPanel>
  );
}

/* ─── Main GlobalStatusPage ───────────────────────────────────── */
export default function GlobalStatusPage({ alerts, tracks, dashboard, eventsPerHr, threatScore, onClose }: {
  alerts: Alert[]; tracks: Track[]; dashboard: DashboardData | null;
  eventsPerHr: string; threatScore: number; onClose: () => void;
}) {
  const [clock, setClock] = useState(new Date().toISOString().slice(11, 19) + " UTC");
  useEffect(() => {
    const iv = setInterval(() => setClock(new Date().toISOString().slice(11, 19) + " UTC"), 1000);
    return () => clearInterval(iv);
  }, []);

  const eventsPerSec = Math.round((parseInt((eventsPerHr || "0").replace(/,/g, "")) / 3600) || 0);
  const domainCounts = dashboard?.domain_counts || {};
  const missileCount = tracks.filter(t => t.is_missile).length;
  const fighterCount = tracks.filter(t => t.classification === "military" && !t.is_missile && t.domain === "air").length;
  const droneCount = tracks.filter(t => t.classification === "uav").length;
  const warshipCount = tracks.filter(t => t.classification === "military" && t.domain === "maritime").length;
  const criticalCount = alerts.filter(a => a.threat_class === "CATASTROPHIC" || a.threat_class === "CRITICAL").length;
  const sensorsOnline = Object.values(dashboard?.sensors || {}).filter(Boolean).length;
  const sensorsTotal = Object.keys(dashboard?.sensors || {}).length || 1;

  const threatColor = threatScore < 20 ? "#00D084" : threatScore < 50 ? "#FFB020" : threatScore < 75 ? "#FF8C00" : "#FF4D4F";
  const defcon = threatScore < 20 ? "5" : threatScore < 50 ? "4" : threatScore < 75 ? "3" : "2";
  const threatLevel = threatScore < 20 ? "STABLE" : threatScore < 50 ? "ELEVATED" : threatScore < 75 ? "HIGH" : "CRITICAL";

  const scenarios = [
    {
      title: "Missile Volley", prob: "HIGH", timeline: "2-15 min", severity: "CATASTROPHIC",
      detail: `${missileCount} active ballistic/hypersonic tracks — ${missileCount > 3 ? "saturation attack imminent." : "standard interdiction profile."}`,
      prep: "Activate ABM, scramble CAP, prepare CIWS"
    },
    {
      title: "Cyber Breach Cascade", prob: criticalCount > 5 ? "CRITICAL" : "ELEVATED", timeline: "5-30 min", severity: "CRITICAL",
      detail: `${domainCounts.cyber || 0} cyber events — ${criticalCount > 5 ? "lateral movement confirmed." : "monitoring indicators."}`,
      prep: "Isolate networks, activate air-gap"
    },
    {
      title: "Maritime Blockade", prob: "MEDIUM", timeline: "1-6 hr", severity: "ELEVATED",
      detail: `${dashboard?.active_tracks.maritime ?? 0} vessels — ${warshipCount} military contacts.`,
      prep: "Deploy naval drones, enforce zone"
    },
    {
      title: "Airspace Incursion", prob: "ELEVATED", timeline: "0-60 min", severity: "ELEVATED",
      detail: `${dashboard?.active_tracks.air ?? 0} air tracks — ${missileCount + fighterCount + droneCount} military.`,
      prep: "IDENT/INTERCEPT protocol active"
    },
    {
      title: "EMP / Spectrum Attack", prob: domainCounts.rf && domainCounts.rf > 50 ? "ELEVATED" : "LOW", timeline: "0-15 min", severity: "CRITICAL",
      detail: `${domainCounts.rf || 0} RF anomalies — ${domainCounts.rf > 100 ? "jamming suspected." : "nominal."}`,
      prep: "Hardened comms, spectrum watch"
    },
    {
      title: "Seismic Event", prob: domainCounts.seismic && domainCounts.seismic > 20 ? "WATCH" : "LOW", timeline: "2-60 min", severity: "SUSPICIOUS",
      detail: `${domainCounts.seismic || 0} events — ${domainCounts.seismic > 50 ? "swarm sequence." : "normal."}`,
      prep: "Tsunami advisory if M>7"
    },
  ];

  const preparations = [
    {
      priority: "IMMEDIATE", color: "#FF4D4F", items: [
        `Verify all sensor feeds — ${sensorsTotal} sensors (${sensorsOnline} online)`,
        "Confirm blockchain evidence chain — IPFS hashes verified",
        `Acknowledge ${criticalCount} critical alerts pending`,
        "Enable cross-domain fusion correlation — AI at full capacity",
        `DEFCON ${defcon} protocols initiated`,
      ]
    },
    {
      priority: "SHORT-TERM", color: "#FFB020", items: [
        `${missileCount} missile trajectories under review`,
        "Cyber kill-chain phase assessment active",
        `${warshipCount} military maritime contacts shadowed`,
        "SOP-7 counter-measures deployed",
        `Kafka ingestion ${eventsPerSec}/sec within limits`,
      ]
    },
    {
      priority: "STRATEGIC", color: "#4DA3FF", items: [
        "ML fusion model retrain cycle queued",
        "Civil defense alert system verified",
        "Backup comms — jamming countermeasures ready",
        "Allied sensor data sharing pipeline active",
        "Blockchain forensic audit trail prepared",
      ]
    },
  ];

  const regionStatus = [
    { region: "North America", level: threatScore < 30 ? "STABLE" : "ELEVATED", color: threatScore < 30 ? "#00D084" : "#FFB020", details: `${dashboard?.active_tracks.air ?? 0} air · ${missileCount} missile` },
    { region: "Europe", level: threatScore < 50 ? "ELEVATED" : "HIGH", color: threatScore < 50 ? "#FFB020" : "#FF8C00", details: `${domainCounts.cyber || 0} cyber · ${dashboard?.active_tracks.maritime ?? 0} maritime` },
    { region: "Asia-Pacific", level: threatScore < 40 ? "STABLE" : threatScore < 70 ? "ELEVATED" : "HIGH", color: threatScore < 40 ? "#00D084" : threatScore < 70 ? "#FFB020" : "#FF8C00", details: `${domainCounts.seismic || 0} seismic · ${domainCounts.rf || 0} RF` },
    { region: "Middle East", level: threatScore > 50 ? "CRITICAL" : "HIGH", color: threatScore > 50 ? "#FF4D4F" : "#FF8C00", details: `${missileCount} missile · ${fighterCount} fighters` },
    { region: "Africa", level: "STABLE", color: "#00D084", details: `${domainCounts.rf || 0} RF · ${dashboard?.active_tracks.air ?? 0} air` },
    { region: "South America", level: "STABLE", color: "#00D084", details: `${dashboard?.active_tracks.maritime ?? 0} maritime · ${domainCounts.seismic || 0} seismic` },
  ];

  return (
    <div style={{
      height: "100vh", display: "flex", flexDirection: "column",
      background: "radial-gradient(ellipse at 20% 20%, rgba(77,163,255,0.04) 0%, transparent 60%), radial-gradient(ellipse at 80% 80%, rgba(168,85,247,0.04) 0%, transparent 60%), #07111F",
      overflow: "hidden", fontFamily: "'Inter', -apple-system, sans-serif",
    }}>
      <style>{`
        @keyframes stat-glow {
          0%, 100% { opacity: 0.7; }
          50% { opacity: 1; }
        }
        @keyframes slide-in {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .stats-animate { animation: slide-in 0.5s cubic-bezier(0.16, 1, 0.3, 1) both; }
        
        /* Custom scrollbar for this page */
        .global-scroll::-webkit-scrollbar { width: 8px; }
        .global-scroll::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
        .global-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
        .global-scroll::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
      `}</style>

      {/* ── Header ── */}
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "12px 28px", flexShrink: 0,
        background: "linear-gradient(180deg, rgba(14,26,43,0.98), rgba(10,20,36,0.95))",
        borderBottom: "1px solid rgba(77,163,255,0.15)",
        backdropFilter: "blur(24px)",
        zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          {/* Logo area */}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: "linear-gradient(135deg, #4DA3FF22, #4DA3FF11)",
              border: "1px solid rgba(77,163,255,0.4)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, boxShadow: "0 0 16px rgba(77,163,255,0.2)"
            }}>G</div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 900, color: "#fff", letterSpacing: "0.15em" }}>SENTINEL-X</div>
              <div style={{ fontSize: 10, color: "var(--accent-info)", fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase" }}>Global Intelligence Library</div>
            </div>
          </div>

          <div style={{ width: 1, height: 36, background: "rgba(255,255,255,0.1)" }} />

          {/* Master Clock */}
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ fontSize: 9, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: 2 }}>Zulu Time / Master Clock</div>
            <div style={{ fontSize: 16, color: "var(--text-primary)", fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.05em" }}>{clock}</div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <button onClick={onClose} style={{
            padding: "8px 20px", borderRadius: 12,
            background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)",
            color: "var(--text-primary)", fontSize: 12, fontWeight: 600, cursor: "pointer",
            transition: "all 0.2s cubic-bezier(0.4,0,0.2,1)", letterSpacing: "0.05em"
          }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.1)"; (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-1px)"; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.05)"; (e.currentTarget as HTMLButtonElement).style.transform = "none"; }}
          >← Return to Operations</button>
        </div>
      </header>

      {/* ── Main content area ── */}
      <div className="global-scroll" style={{ flex: 1, overflowY: "auto", overflowX: "hidden", padding: "28px", display: "flex", flexDirection: "column", gap: 20 }}>

        {/* ── Top Level System Status Grid ── */}
        <div className="stats-animate" style={{ display: "grid", gridTemplateColumns: "1.2fr 2fr", gap: 20 }}>
          
          {/* DEFCON & Threat Meter */}
          <GlassPanel accent={threatColor} style={{ padding: "20px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 700, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.1em" }}>Global Threat Level</div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
                  <span style={{ fontSize: 32, fontWeight: 900, color: threatColor, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.05em", textShadow: `0 0 20px ${threatColor}66` }}>
                    {threatLevel}
                  </span>
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 700, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.1em" }}>Defcon</div>
                <div style={{ fontSize: 32, fontWeight: 900, color: threatColor, fontFamily: "'JetBrains Mono', monospace", textShadow: `0 0 20px ${threatColor}66` }}>
                  {defcon}
                </div>
              </div>
            </div>
            
            <div style={{ height: 1, background: "rgba(255,255,255,0.06)", margin: "20px 0" }} />
            
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
              <div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>Threat Score</div>
                <div style={{ fontSize: 18, fontWeight: 800, color: threatColor, fontFamily: "'JetBrains Mono', monospace" }}>{threatScore}%</div>
              </div>
              <div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>Critical Alerts</div>
                <div style={{ fontSize: 18, fontWeight: 800, color: "#FF4D4F", fontFamily: "'JetBrains Mono', monospace" }}>{criticalCount}</div>
              </div>
              <div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>Missile Tracks</div>
                <div style={{ fontSize: 18, fontWeight: 800, color: "#FF8C00", fontFamily: "'JetBrains Mono', monospace" }}>{missileCount}</div>
              </div>
            </div>
          </GlassPanel>

          {/* System Overview Details */}
          <GlassPanel accent="#4DA3FF" style={{ padding: "20px" }}>
            <SectionLabel color="#4DA3FF">Core Infrastructure Telemetry</SectionLabel>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px 20px" }}>
              {[
                { label: "Data Throughput", value: `${eventsPerSec}/s`, desc: "Global sensor firehose ingestion rate" },
                { label: "Active Entities", value: (dashboard?.active_tracks.total ?? 0).toLocaleString(), desc: "Total live tracks across all domains" },
                { label: "Sensor Health", value: `${sensorsOnline}/${sensorsTotal}`, desc: "Global array operational status", valueColor: sensorsOnline > sensorsTotal / 2 ? "#00D084" : "#FFB020" },
                { label: "Ledger State", value: dashboard?.blockchain_synced ? "SYNCED" : "PENDING", desc: "Cryptographic evidence chain validation", valueColor: dashboard?.blockchain_synced ? "#A855F7" : "#FFB020" },
                { label: "AI Confidence", value: `${Math.min(99, threatScore + 15)}%`, desc: "Neural fusion prediction certainty", valueColor: "#FFB020" },
                { label: "Network Latency", value: `${Math.round(45 + Math.random() * 30)}ms`, desc: "Global backbone response time" },
              ].map(stat => (
                <div key={stat.label} style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 2 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.05em" }}>{stat.label}</span>
                      <span style={{ fontSize: 12, fontWeight: 800, color: stat.valueColor || "#4DA3FF", fontFamily: "'JetBrains Mono', monospace" }}>{stat.value}</span>
                    </div>
                    <div style={{ fontSize: 9, color: "var(--text-muted)" }}>{stat.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </GlassPanel>
        </div>

        {/* ── Cyber Kill Chain ── */}
        <KillChainFlow />

        {/* ── Threat Probability Matrix ── */}
        <div className="stats-animate" style={{ animationDelay: "0.15s" }}>
          <SectionLabel color="#FFB020">Threat Probability & Scenario Matrix</SectionLabel>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
            {scenarios.map((s, i) => <ScenarioCard key={s.title} s={s} delay={0.2 + (i * 0.05)} />)}
          </div>
        </div>

        {/* ── Bottom Section: Regions & Preparations & Strategy ── */}
        <div className="stats-animate" style={{ animationDelay: "0.4s", display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 20 }}>
          
          {/* Regional Status Grid */}
          <GlassPanel style={{ padding: "20px" }}>
            <SectionLabel color="var(--text-primary)">Theater Command Status</SectionLabel>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {regionStatus.map(r => (
                <div key={r.region} style={{ padding: "12px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, transition: "background 0.2s" }}
                  onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.04)"; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.02)"; }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: r.color, boxShadow: `0 0 10px ${r.color}` }} />
                      <span style={{ fontSize: 12, color: "var(--text-primary)", fontWeight: 700, letterSpacing: "0.05em" }}>{r.region}</span>
                    </div>
                    <span style={{ fontSize: 9, fontWeight: 800, color: r.color, background: `${r.color}15`, padding: "2px 6px", borderRadius: 4, letterSpacing: "0.05em" }}>{r.level}</span>
                  </div>
                  <div style={{ fontSize: 10, color: "var(--text-muted)", display: "flex", gap: 6, alignItems: "center" }}>
                    <span style={{ opacity: 0.6 }}>↳</span> {r.details}
                  </div>
                </div>
              ))}
            </div>
          </GlassPanel>

          {/* Action Preparations */}
          <GlassPanel accent="#A855F7" style={{ padding: "20px" }}>
            <SectionLabel color="#A855F7">Automated Response Protocols</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {preparations.map(p => (
                <div key={p.priority}>
                  <div style={{ fontSize: 10, fontWeight: 800, color: p.color, marginBottom: 8, letterSpacing: "0.1em", display: "flex", alignItems: "center", gap: 6 }}>
                    <div style={{ width: 3, height: 10, background: p.color, borderRadius: 2 }} />
                    {p.priority} PHASE
                  </div>
                  <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 6 }}>
                    {p.items.map((item, i) => (
                      <li key={i} style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", gap: 8, alignItems: "flex-start" }}>
                        <span style={{ color: p.color, opacity: 0.8, marginTop: 1 }}>◈</span>
                        <span style={{ lineHeight: 1.3 }}>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </GlassPanel>

        </div>

      </div>
    </div>
  );
}
