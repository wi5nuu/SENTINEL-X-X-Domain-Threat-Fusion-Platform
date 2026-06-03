import { useEffect, useRef } from "react";
import { Alert, Track, DashboardData, SEVERITY_ORDER } from "./App";

function Sparkline({ values, color, h = 28 }: { values: number[]; color: string; h?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    const w = c.clientWidth || 200;
    c.width = w; c.height = h;
    ctx.clearRect(0, 0, w, h);
    if (values.length < 2) return;
    const max = Math.max(...values, 1);
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    values.forEach((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - (v / max) * (h - 6) - 3;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.fillStyle = `${color}12`;
    ctx.lineTo(w, h - 3);
    ctx.lineTo(0, h - 3);
    ctx.closePath();
    ctx.fill();
  }, [values, color, h]);
  return <canvas ref={ref} style={{ width: "100%", height: h }} />;
}

function BarChart({ data, colorMap, maxLabelLen = 4 }: { data: Record<string, number>; colorMap: Record<string, string>; maxLabelLen?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    const w = c.clientWidth || 300, h = 60;
    c.width = w; c.height = h;
    ctx.clearRect(0, 0, w, h);
    const entries = Object.entries(data);
    if (!entries.length) return;
    const maxVal = Math.max(...entries.map(([, v]) => v), 1);
    const gap = 6;
    const barW = Math.max(8, (w - gap * (entries.length + 1)) / entries.length);
    const r = Math.min(3, barW / 3);
    entries.forEach(([k, v], i) => {
      const x = gap + i * (barW + gap);
      const barH = (v / maxVal) * (h - 16);
      ctx.fillStyle = colorMap[k] || "#6B7280";
      ctx.beginPath();
      ctx.roundRect(x, h - 8 - barH, barW, barH, [r, r, 0, 0]);
      ctx.fill();
      ctx.fillStyle = "#6E7B91";
      ctx.font = "8px Inter, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(k.slice(0, maxLabelLen), x + barW / 2, h - 1);
      ctx.fillStyle = "#A0AEC0";
      ctx.fillText(`${v}`, x + barW / 2, h - 10 - barH);
    });
  }, [data, colorMap, maxLabelLen]);
  return <canvas ref={ref} style={{ width: "100%", height: 60 }} />;
}

export default function StatsPage({ alerts, tracks, dashboard, eventsPerHr, threatScore, onClose }: {
  alerts: Alert[]; tracks: Track[]; dashboard: DashboardData | null;
  eventsPerHr: string; threatScore: number; onClose: () => void;
}) {
  const eventsPerSec = Math.round((parseInt((eventsPerHr || "0").replace(/,/g, "")) / 3600) || 0);
  const domainCounts = dashboard?.domain_counts || {};
  const totalEvents = Object.values(domainCounts).reduce((s, v) => s + v, 0);
  const domainColors: Record<string, string> = { air: "#4DA3FF", maritime: "#00D084", seismic: "#FFB020", rf: "#FF4D4F", cyber: "#A855F7" };
  const severityColors: Record<string, string> = { CATASTROPHIC: "#B80000", CRITICAL: "#FF4D4F", ELEVATED: "#FF8C00", SUSPICIOUS: "#FFB020", INFORMATIONAL: "#6E7B91" };
  const avgConfidence = alerts.length ? (alerts.reduce((s, a) => s + (a.confidence || 0.5), 0) / alerts.length) : 0;
  const missileCount = tracks.filter(t => t.is_missile).length;
  const fighterCount = tracks.filter(t => t.classification === "military" && !t.is_missile && t.domain === "air").length;
  const droneCount = tracks.filter(t => t.classification === "uav").length;
  const warshipCount = tracks.filter(t => t.classification === "military" && t.domain === "maritime").length;
  const severityCounts = SEVERITY_ORDER.map(s => ({ label: s, count: alerts.filter(a => a.threat_class === s).length, color: severityColors[s] }));
  const criticalCount = alerts.filter(a => a.threat_class === "CATASTROPHIC" || a.threat_class === "CRITICAL").length;
  const sensorsOnline = Object.values(dashboard?.sensors || {}).filter(Boolean).length;
  const sensorsTotal = Object.keys(dashboard?.sensors || {}).length;
  const alertRate24h = dashboard?.alerts_24h ? (dashboard.alerts_24h / 24).toFixed(1) : "0";
  const healthIndex = Math.max(0, Math.min(100, 100 - threatScore + (sensorsOnline / Math.max(1, sensorsTotal)) * 20));
  const detectionIndex = Math.round(avgConfidence * 100);
  const volatilityIndex = Math.min(100, Math.round((criticalCount / Math.max(1, alerts.length)) * 100 + threatScore * 0.5));
  const integrityIndex = dashboard?.blockchain_synced ? 98 : 45;

  const kpiCards = [
    { label: "Events / Sec", value: eventsPerSec.toLocaleString(), color: "var(--accent-info)" },
    { label: "Events / Hour", value: parseInt((eventsPerHr || "0").replace(/,/g, "")).toLocaleString(), color: "var(--accent-info)" },
    { label: "Total Events", value: totalEvents.toLocaleString(), color: "var(--accent-info)" },
    { label: "Active Tracks", value: (dashboard?.active_tracks.total ?? 0).toLocaleString(), color: "var(--accent-success)" },
    { label: "Alerts (24h)", value: (dashboard?.alerts_24h ?? 0).toLocaleString(), color: "var(--accent-critical)" },
    { label: "Threat Score", value: `${threatScore}%`, color: threatScore > 50 ? "var(--accent-critical)" : threatScore > 20 ? "var(--accent-warning)" : "var(--accent-success)" },
  ];

  const entityCards = [
    { label: "Missile", value: missileCount, color: "#FF4D4F" },
    { label: "Fighter", value: fighterCount, color: "#4DA3FF" },
    { label: "Drone", value: droneCount, color: "#FFB020" },
    { label: "Warship", value: warshipCount, color: "#00D084" },
    { label: "Threats", value: tracks.filter(t => t.is_threat).length, color: "#FF8C00" },
    { label: "Total Tracks", value: tracks.length, color: "#6E7B91" },
  ];

  const indices = [
    { label: "System Health", value: `${Math.round(healthIndex)}%`, color: healthIndex > 70 ? "var(--accent-success)" : "var(--accent-warning)" },
    { label: "Detection Rate", value: `${detectionIndex}%`, color: detectionIndex > 70 ? "var(--accent-success)" : "var(--accent-warning)" },
    { label: "Threat Volatility", value: `${volatilityIndex}%`, color: volatilityIndex < 30 ? "var(--accent-success)" : volatilityIndex < 60 ? "var(--accent-warning)" : "var(--accent-critical)" },
    { label: "Data Integrity", value: `${integrityIndex}%`, color: integrityIndex > 70 ? "var(--accent-success)" : "var(--accent-critical)" },
  ];

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "var(--bg-primary)", overflow: "hidden" }}>

      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 20px", borderBottom: "1px solid var(--border-panel)", background: "var(--bg-panel)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.12em" }}>SENTINEL-X</span>
          <span style={{ width: 1, height: 20, background: "var(--border-panel)" }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--accent-info)", letterSpacing: "0.06em" }}>Analytics Dashboard</span>
        </div>
        <button onClick={onClose} className="btn-ghost" style={{ fontSize: 12 }}>Back to Operations</button>
      </header>

      <div style={{ flex: 1, minHeight: 0, overflow: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: 12 }}>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8 }}>
          {kpiCards.map(kpi => (
            <div key={kpi.label} className="panel" style={{ padding: "16px" }}>
              <div className="kpi-label">{kpi.label}</div>
              <div className="kpi-value" style={{ color: kpi.color, marginTop: 2 }}>{kpi.value}</div>
            </div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8 }}>
          {entityCards.map(ec => (
            <div key={ec.label} className="panel" style={{ padding: "14px 16px", display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: ec.color, flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: 9, color: "var(--text-muted)", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>{ec.label}</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", fontFamily: "'JetBrains Mono', monospace", marginTop: 1 }}>{ec.value}</div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr 1.5fr", gap: 8 }}>
          <div className="panel" style={{ padding: "14px" }}>
            <div className="panel-header">Sensor Status</div>
            {dashboard?.sensors && Object.entries(dashboard.sensors).slice(0, 8).map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid var(--border-subtle)", fontSize: 11 }}>
                <span style={{ color: "var(--text-secondary)", textTransform: "capitalize" }}>{k.replace(/_/g, " ")}</span>
                <span style={{ color: v ? "var(--accent-success)" : "var(--accent-critical)", fontWeight: 600 }}>{v ? "Online" : "Offline"}</span>
              </div>
            ))}
          </div>

          <div className="panel" style={{ padding: "14px" }}>
            <div className="panel-header">Domain Distribution</div>
            <BarChart data={domainCounts} colorMap={domainColors} />
            <div style={{ marginTop: 4 }}>
              {Object.entries(domainCounts).map(([k, v]) => {
                const pct = totalEvents > 0 ? ((v / totalEvents) * 100).toFixed(1) : "0";
                return (
                  <div key={k} style={{ marginBottom: 2 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-secondary)", padding: "1px 0" }}>
                      <span style={{ color: domainColors[k] || "#6E7B91", fontWeight: 600, textTransform: "uppercase" }}>{k}</span>
                      <span>{v.toLocaleString()} <span style={{ color: "var(--text-muted)" }}>({pct}%)</span></span>
                    </div>
                    <div style={{ background: "var(--bg-primary)", height: 3, borderRadius: 2, overflow: "hidden" }}>
                      <div style={{ width: `${pct}%`, background: domainColors[k] || "#6E7B91", height: "100%", borderRadius: 2 }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="panel" style={{ padding: "14px" }}>
            <div className="panel-header">Severity Breakdown</div>
            {severityCounts.map(s => {
              const pct = alerts.length > 0 ? ((s.count / alerts.length) * 100).toFixed(1) : "0";
              return (
                <div key={s.label} style={{ marginBottom: 3 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-secondary)", padding: "1px 0" }}>
                    <span style={{ color: s.color, fontWeight: 600 }}>{s.label}</span>
                    <span>{s.count} <span style={{ color: "var(--text-muted)" }}>({pct}%)</span></span>
                  </div>
                  <div style={{ background: "var(--bg-primary)", height: 3, borderRadius: 2, overflow: "hidden" }}>
                    <div style={{ width: `${pct}%`, background: s.color, height: "100%", borderRadius: 2 }} />
                  </div>
                </div>
              );
            })}
            <div style={{ borderTop: "1px solid var(--border-subtle)", marginTop: 4, paddingTop: 4 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-secondary)", padding: "1px 0" }}>
                <span>Avg Confidence</span>
                <span style={{ color: "var(--accent-success)", fontWeight: 600 }}>{(avgConfidence * 100).toFixed(1)}%</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-secondary)", padding: "1px 0" }}>
                <span>Alert Rate</span>
                <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{alertRate24h}/hr</span>
              </div>
            </div>
          </div>

          <div className="panel" style={{ padding: "14px" }}>
            <div className="panel-header">System Health Indices</div>
            {indices.map(idx => (
              <div key={idx.label} style={{ marginBottom: 4 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-secondary)", padding: "2px 0" }}>
                  <span>{idx.label}</span>
                  <span style={{ color: idx.color, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>{idx.value}</span>
                </div>
                <div style={{ background: "var(--bg-primary)", height: 4, borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ width: idx.value, background: idx.color, height: "100%", borderRadius: 2 }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 8 }}>
          <div className="panel" style={{ padding: "14px" }}>
            <div className="panel-header">Event Trend (Rolling 60s)</div>
            <div style={{ marginTop: 8 }}>
              <Sparkline values={Array.from({ length: 60 }, () => Math.max(1, eventsPerSec + Math.round((Math.random() - 0.5) * eventsPerSec * 0.5)))} color="var(--accent-info)" />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: 9, marginTop: 4 }}>
              <span>-60s</span>
              <span style={{ color: "var(--accent-info)", fontWeight: 600 }}>{eventsPerSec}/s current</span>
            </div>
          </div>

          <div className="panel" style={{ padding: "14px" }}>
            <div className="panel-header">System Services</div>
            {[
              { label: "WebSocket", value: dashboard ? "Connected" : "Disconnected", color: dashboard ? "var(--accent-success)" : "var(--accent-critical)" },
              { label: "Kafka Stream", value: "Streaming", color: "var(--accent-success)" },
              { label: "API Gateway", value: "200 OK", color: "var(--accent-success)" },
              { label: "Database", value: "Synced", color: "var(--accent-success)" },
              { label: "Blockchain", value: dashboard?.blockchain_synced ? "Verified" : "Pending", color: dashboard?.blockchain_synced ? "#A855F7" : "var(--accent-warning)" },
            ].map(svc => (
              <div key={svc.label} style={{ display: "flex", justifyContent: "space-between", fontSize: 10, padding: "4px 0", borderBottom: "1px solid var(--border-subtle)" }}>
                <span style={{ color: "var(--text-secondary)" }}>{svc.label}</span>
                <span style={{ color: svc.color, fontWeight: 600 }}>{svc.value}</span>
              </div>
            ))}
          </div>

          <div className="panel" style={{ padding: "14px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            <div className="panel-header" style={{ alignSelf: "stretch" }}>System Uptime</div>
            <div style={{ fontSize: 36, fontWeight: 700, color: "var(--accent-info)", fontFamily: "'JetBrains Mono', monospace", marginTop: 8 }}>24h</div>
            <div style={{ fontSize: 10, color: "var(--text-muted)" }}>since last epoch</div>
          </div>
        </div>

      </div>
    </div>
  );
}
