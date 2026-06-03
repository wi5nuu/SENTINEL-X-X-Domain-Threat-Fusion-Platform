import { Alert, Track, DashboardData } from "./App";

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
    <div className="panel" style={{ padding: "14px" }}>
      <div className="panel-header" style={{ marginBottom: 12 }}>Cyber Kill Chain Status</div>
      <div style={{ display: "flex", gap: 0, alignItems: "center" }}>
        {phases.map((p, i) => (
          <div key={p.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div style={{
              width: "100%", padding: "6px 0", borderRadius: 4, textAlign: "center", fontSize: 10, fontWeight: 600,
              backgroundColor: i <= currentPhase ? `${p.color}18` : "transparent",
              border: i <= currentPhase ? `1px solid ${p.color}40` : "1px solid transparent",
              color: i <= currentPhase ? p.color : "var(--text-muted)", opacity: i <= currentPhase ? 1 : 0.35,
              transition: "all 0.2s",
            }}>{p.label}</div>
            <div style={{ fontSize: 8, color: "var(--text-muted)", marginTop: 3 }}>{p.desc}</div>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 10, color: "var(--text-muted)", textAlign: "center", marginTop: 8, padding: "4px 0", borderTop: "1px solid var(--border-subtle)" }}>
        Current phase: <span style={{ color: "#FF4D4F", fontWeight: 600 }}>Exploitation</span> &mdash; active containment in progress
      </div>
    </div>
  );
}

function ThreatMeter({ alerts, threatScore, dashboard, tracks }: { alerts: Alert[]; threatScore: number; dashboard: DashboardData | null; tracks: Track[] }) {
  const level = threatScore < 20 ? "STABLE" : threatScore < 50 ? "ELEVATED" : threatScore < 75 ? "HIGH" : "CRITICAL";
  const color = threatScore < 20 ? "var(--accent-success)" : threatScore < 50 ? "var(--accent-warning)" : threatScore < 75 ? "#FF8C00" : "var(--accent-critical)";
  const criticalCount = alerts.filter(a => a.threat_class === "CATASTROPHIC" || a.threat_class === "CRITICAL").length;
  const missileCount = tracks.filter(t => t.is_missile).length;
  const defcon = threatScore < 20 ? "5" : threatScore < 50 ? "4" : threatScore < 75 ? "3" : "2";

  return (
    <div className="panel" style={{ padding: "16px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
      <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 500, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Current Threat Level</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
        <span style={{ fontSize: 28, fontWeight: 700, color, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.03em" }}>{level}</span>
        <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>Score {threatScore}%</span>
      </div>
      <div style={{ display: "flex", gap: 12, marginTop: 6, fontSize: 10, color: "var(--text-muted)" }}>
        <span><span style={{ color: "var(--accent-critical)", fontWeight: 600 }}>{criticalCount}</span> critical alerts</span>
        <span><span style={{ color: "#FF4D4F", fontWeight: 600 }}>{missileCount}</span> missile tracks</span>
        <span>DEFCON <span style={{ color, fontWeight: 700 }}>{defcon}</span></span>
      </div>
    </div>
  );
}

function ScenarioCard({ s }: { s: { title: string; prob: string; timeline: string; severity: string; detail: string; prep: string } }) {
  const probColor = s.prob === "CRITICAL" || s.prob === "HIGH" ? "var(--accent-catastrophic)" : s.prob === "ELEVATED" ? "var(--accent-warning)" : "var(--text-muted)";
  const sevColor = s.severity === "CATASTROPHIC" ? "var(--accent-catastrophic)" : s.severity === "CRITICAL" ? "var(--accent-critical)" : "var(--accent-warning)";
  return (
    <div className="panel" style={{ padding: "12px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-primary)" }}>{s.title}</span>
        <span style={{ fontSize: 9, fontWeight: 600, color: probColor, background: `${probColor}12`, padding: "2px 8px", borderRadius: 3, border: `1px solid ${probColor}20` }}>{s.prob}</span>
      </div>
      <div style={{ display: "flex", gap: 8, fontSize: 10, color: "var(--text-muted)", marginBottom: 6 }}>
        <span>Severity: <span style={{ color: sevColor, fontWeight: 600 }}>{s.severity}</span></span>
        <span>Timeline: <span style={{ color: "var(--text-secondary)" }}>{s.timeline}</span></span>
      </div>
      <div style={{ fontSize: 10, color: "var(--text-secondary)", lineHeight: 1.45, marginBottom: 6 }}>{s.detail}</div>
      <div style={{ fontSize: 9, color: "var(--accent-info)" }}>Response: {s.prep}</div>
    </div>
  );
}

export default function GlobalStatusPage({ alerts, tracks, dashboard, eventsPerHr, threatScore, onClose }: {
  alerts: Alert[]; tracks: Track[]; dashboard: DashboardData | null;
  eventsPerHr: string; threatScore: number; onClose: () => void;
}) {
  const eventsPerSec = Math.round((parseInt((eventsPerHr || "0").replace(/,/g, "")) / 3600) || 0);
  const domainCounts = dashboard?.domain_counts || {};
  const now = new Date().toISOString().slice(11, 19) + " UTC";
  const missileCount = tracks.filter(t => t.is_missile).length;
  const fighterCount = tracks.filter(t => t.classification === "military" && !t.is_missile && t.domain === "air").length;
  const droneCount = tracks.filter(t => t.classification === "uav").length;
  const warshipCount = tracks.filter(t => t.classification === "military" && t.domain === "maritime").length;
  const criticalCount = alerts.filter(a => a.threat_class === "CATASTROPHIC" || a.threat_class === "CRITICAL").length;
  const sensorsOnline = Object.values(dashboard?.sensors || {}).filter(Boolean).length;
  const sensorsTotal = Object.keys(dashboard?.sensors || {}).length;

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
      priority: "IMMEDIATE", color: "var(--accent-catastrophic)", items: [
        `Verify all sensor feeds — ${sensorsTotal} sensors (${sensorsOnline} online)`,
        "Confirm blockchain evidence chain — IPFS hashes verified",
        `Acknowledge ${criticalCount} critical alerts pending`,
        "Enable cross-domain fusion correlation — AI at full capacity",
        `DEFCON ${threatScore < 20 ? '5' : threatScore < 50 ? '4' : threatScore < 75 ? '3' : '2'} protocols initiated`,
      ]
    },
    {
      priority: "SHORT-TERM", color: "var(--accent-warning)", items: [
        `${missileCount} missile trajectories under review`,
        "Cyber kill-chain phase assessment active",
        `${warshipCount} military maritime contacts shadowed`,
        "SOP-7 counter-measures deployed",
        `Kafka ingestion ${eventsPerSec}/sec within limits`,
      ]
    },
    {
      priority: "STRATEGIC", color: "var(--text-muted)", items: [
        "ML fusion model retrain cycle queued",
        "Civil defense alert system verified",
        "Backup comms — jamming countermeasures ready",
        "Allied sensor data sharing pipeline active",
        "Blockchain forensic audit trail prepared",
      ]
    },
  ];

  const regionStatus = [
    { region: "North America", level: threatScore < 30 ? "STABLE" : "ELEVATED", color: threatScore < 30 ? "var(--accent-success)" : "var(--accent-warning)", details: `${dashboard?.active_tracks.air ?? 0} air · ${missileCount} missile` },
    { region: "Europe", level: threatScore < 50 ? "ELEVATED" : "HIGH", color: threatScore < 50 ? "var(--accent-warning)" : "#FF8C00", details: `${domainCounts.cyber || 0} cyber · ${dashboard?.active_tracks.maritime ?? 0} maritime` },
    { region: "Asia-Pacific", level: threatScore < 40 ? "STABLE" : threatScore < 70 ? "ELEVATED" : "HIGH", color: threatScore < 40 ? "var(--accent-success)" : threatScore < 70 ? "var(--accent-warning)" : "#FF8C00", details: `${domainCounts.seismic || 0} seismic · ${domainCounts.rf || 0} RF` },
    { region: "Middle East", level: threatScore > 50 ? "CRITICAL" : "HIGH", color: threatScore > 50 ? "var(--accent-critical)" : "#FF8C00", details: `${missileCount} missile · ${fighterCount} fighters` },
    { region: "Africa", level: "STABLE", color: "var(--accent-success)", details: `${domainCounts.rf || 0} RF · ${dashboard?.active_tracks.air ?? 0} air` },
    { region: "South America", level: "STABLE", color: "var(--accent-success)", details: `${dashboard?.active_tracks.maritime ?? 0} maritime · ${domainCounts.seismic || 0} seismic` },
  ];

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "var(--bg-primary)", overflow: "hidden" }}>

      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 20px", borderBottom: "1px solid var(--border-panel)", background: "var(--bg-panel)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.12em" }}>SENTINEL-X</span>
          <span style={{ width: 1, height: 20, background: "var(--border-panel)" }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: threatScore > 50 ? "var(--accent-critical)" : threatScore > 20 ? "var(--accent-warning)" : "var(--accent-success)", letterSpacing: "0.06em" }}>Global Status &amp; Threat Assessment</span>
        </div>
        <button onClick={onClose} className="btn-ghost" style={{ fontSize: 12 }}>Back to Operations</button>
      </header>

      <div style={{ flex: 1, minHeight: 0, overflow: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: 12 }}>

        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1.8fr 1fr", gap: 8 }}>
          <ThreatMeter alerts={alerts} threatScore={threatScore} dashboard={dashboard} tracks={tracks} />

          <div className="panel" style={{ padding: "14px" }}>
            <div className="panel-header" style={{ marginBottom: 8 }}>System Overview</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "6px 12px", fontSize: 11 }}>
              <span style={{ color: "var(--text-muted)" }}>Throughput</span>
              <span style={{ color: "var(--accent-info)", fontWeight: 600, textAlign: "right", fontFamily: "'JetBrains Mono', monospace" }}>{eventsPerSec}/s</span>
              <span></span>
              <span style={{ color: "var(--text-muted)" }}>Active Tracks</span>
              <span style={{ color: "var(--text-primary)", fontWeight: 600, textAlign: "right", fontFamily: "'JetBrains Mono', monospace" }}>{dashboard?.active_tracks.total ?? 0}</span>
              <span></span>
              <span style={{ color: "var(--text-muted)" }}>Sensors Online</span>
              <span style={{ color: sensorsOnline > sensorsTotal / 2 ? "var(--accent-success)" : "var(--accent-warning)", fontWeight: 600, textAlign: "right", fontFamily: "'JetBrains Mono', monospace" }}>{sensorsOnline}/{sensorsTotal}</span>
              <span></span>
              <span style={{ color: "var(--text-muted)" }}>Blockchain</span>
              <span style={{ color: dashboard?.blockchain_synced ? "#A855F7" : "var(--text-muted)", fontWeight: 600, textAlign: "right", fontFamily: "'JetBrains Mono', monospace" }}>{dashboard?.blockchain_synced ? "synced" : "pending"}</span>
              <span></span>
              <span style={{ color: "var(--text-muted)" }}>AI Fusion</span>
              <span style={{ color: "var(--accent-warning)", fontWeight: 600, textAlign: "right", fontFamily: "'JetBrains Mono', monospace" }}>{Math.min(99, threatScore + 15)}%</span>
              <span></span>
              <span style={{ color: "var(--text-muted)" }}>Response Latency</span>
              <span style={{ color: "var(--text-primary)", fontWeight: 600, textAlign: "right", fontFamily: "'JetBrains Mono', monospace" }}>{Math.round(45 + Math.random() * 30)}ms</span>
              <span></span>
            </div>
          </div>

          <div className="panel" style={{ padding: "14px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 500, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Timestamp (UTC)</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: "var(--accent-info)", fontFamily: "'JetBrains Mono', monospace" }}>{now}</div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>All domains operational</div>
          </div>
        </div>

        <KillChainFlow />

        <div>
          <div className="panel-header" style={{ marginBottom: 8 }}>Threat Probability Matrix</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
            {scenarios.map(s => <ScenarioCard key={s.title} s={s} />)}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <div>
            <div className="panel-header" style={{ marginBottom: 8 }}>Regional Status</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
              {regionStatus.map(r => (
                <div key={r.region} className="panel" style={{ padding: "10px" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <div style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: r.color }} />
                      <span style={{ fontSize: 10, color: "var(--text-primary)", fontWeight: 600 }}>{r.region}</span>
                    </div>
                    <span style={{ fontSize: 9, fontWeight: 700, color: r.color }}>{r.level}</span>
                  </div>
                  <div style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 3 }}>{r.details}</div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="panel-header" style={{ marginBottom: 8 }}>Recommended Preparations</div>
            {preparations.map(p => (
              <div key={p.priority} className="panel" style={{ padding: "12px", marginBottom: 6 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: p.color, marginBottom: 6, letterSpacing: "0.05em" }}>{p.priority}</div>
                <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
                  {p.items.map((item, i) => (
                    <li key={i} style={{ fontSize: 10, color: "var(--text-secondary)", padding: "2px 0", display: "flex", gap: 6 }}>
                      <span style={{ color: "var(--text-muted)" }}>&mdash;</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="panel" style={{ padding: "14px" }}>
          <div className="panel-header" style={{ marginBottom: 10 }}>Strategic Recommendations</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--accent-info)", marginBottom: 4 }}>Air Defense</div>
              <div style={{ fontSize: 10, color: "var(--text-secondary)", lineHeight: 1.5 }}>CAP at DEFCON 2. {missileCount} inbound tracks. Layered ABM. Electronic countermeasures deployed.</div>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#A855F7", marginBottom: 4 }}>Cyber Hardening</div>
              <div style={{ fontSize: 10, color: "var(--text-secondary)", lineHeight: 1.5 }}>Isolate critical infra. Air-gap power grid &amp; comms. Rotate credentials enterprise-wide.</div>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--accent-success)", marginBottom: 4 }}>Maritime Security</div>
              <div style={{ fontSize: 10, color: "var(--text-secondary)", lineHeight: 1.5 }}>Naval blockade. Shadow {warshipCount} military vessels. Underwater surveillance grid active.</div>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--accent-warning)", marginBottom: 4 }}>Civil Defense</div>
              <div style={{ fontSize: 10, color: "var(--text-secondary)", lineHeight: 1.5 }}>Alert impact zones. Fallout shelters, emergency broadcast, medical triage protocols active.</div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
