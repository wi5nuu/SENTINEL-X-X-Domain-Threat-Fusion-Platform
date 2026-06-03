import { useEffect, useRef, useState } from "react";
import { Alert, Track, DashboardData, SEVERITY_ORDER } from "./App";

/* ─── Animated arc gauge ─────────────────────────────────────── */
function ArcGauge({
  value, max = 100, label, sublabel, color, size = 120,
}: {
  value: number; max?: number; label: string; sublabel?: string; color: string; size?: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const safeValue = isNaN(value) ? 0 : value;
  const pct = Math.min(1, Math.max(0, safeValue / max));

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const s = size * dpr;
    canvas.width = s; canvas.height = s;
    canvas.style.width = `${size}px`; canvas.style.height = `${size}px`;
    ctx.scale(dpr, dpr);

    let current = 0;
    const target = pct;
    const cx = size / 2, cy = size / 2;
    const r = size * 0.38;
    const startAngle = Math.PI * 0.75;
    const totalArc = Math.PI * 1.5;

    const draw = () => {
      ctx.clearRect(0, 0, size, size);

      // Track ring
      ctx.beginPath();
      ctx.arc(cx, cy, r, startAngle, startAngle + totalArc);
      ctx.strokeStyle = "rgba(255,255,255,0.06)";
      ctx.lineWidth = size * 0.07;
      ctx.lineCap = "round";
      ctx.stroke();

      // Tick marks
      for (let i = 0; i <= 10; i++) {
        const angle = startAngle + (i / 10) * totalArc;
        const inner = r - size * 0.07;
        const outer = r - size * 0.1;
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(angle) * inner, cy + Math.sin(angle) * inner);
        ctx.lineTo(cx + Math.cos(angle) * outer, cy + Math.sin(angle) * outer);
        ctx.strokeStyle = i % 5 === 0 ? "rgba(255,255,255,0.18)" : "rgba(255,255,255,0.07)";
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      if (current > 0.002) {
        // Glow gradient arc
        const grad = ctx.createLinearGradient(
          cx + Math.cos(startAngle) * r, cy + Math.sin(startAngle) * r,
          cx + Math.cos(startAngle + totalArc) * r, cy + Math.sin(startAngle + totalArc) * r
        );
        grad.addColorStop(0, `${color}88`);
        grad.addColorStop(1, color);

        ctx.beginPath();
        ctx.arc(cx, cy, r, startAngle, startAngle + totalArc * current);
        ctx.strokeStyle = grad;
        ctx.lineWidth = size * 0.07;
        ctx.lineCap = "round";
        ctx.shadowBlur = size * 0.15;
        ctx.shadowColor = color;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Tip glow dot
        const tipAngle = startAngle + totalArc * current;
        const tx = cx + Math.cos(tipAngle) * r;
        const ty = cy + Math.sin(tipAngle) * r;
        ctx.beginPath();
        ctx.arc(tx, ty, size * 0.045, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.shadowBlur = size * 0.2;
        ctx.shadowColor = color;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      if (Math.abs(current - target) > 0.005) {
        current += (target - current) * 0.07;
        animRef.current = requestAnimationFrame(draw);
      } else if (current !== target) {
        current = target;
        animRef.current = requestAnimationFrame(draw);
      }
    };
    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, [pct, color, size]);

  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      <canvas ref={ref} />
      <div style={{
        position: "absolute", inset: 0, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", pointerEvents: "none",
        gap: 1,
      }}>
        <div style={{
          fontSize: size * 0.2, fontWeight: 700, color, lineHeight: 1,
          fontFamily: "'JetBrains Mono', monospace",
          textShadow: `0 0 12px ${color}88`,
        }}>{Math.round(value)}</div>
        <div style={{ fontSize: size * 0.09, color: "var(--text-muted)", fontWeight: 500, textAlign: "center", padding: "0 8px" }}>{label}</div>
        {sublabel && <div style={{ fontSize: size * 0.08, color, opacity: 0.7 }}>{sublabel}</div>}
      </div>
    </div>
  );
}

/* ─── Animated sparkline with gradient fill ──────────────────── */
function GlowSparkline({
  values, color, h = 60, label,
}: {
  values: number[]; color: string; h?: number; label?: string;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.parentElement?.clientWidth || 300;
    canvas.width = w * dpr; canvas.height = h * dpr;
    canvas.style.width = `${w}px`; canvas.style.height = `${h}px`;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);
    if (values.length < 2) return;
    const max = Math.max(...values, 1);
    const pad = 6;
    const pts = values.map((v, i) => ({
      x: (i / (values.length - 1)) * (w - 2 * pad) + pad,
      y: h - pad - (v / max) * (h - 2 * pad),
    }));

    // Gradient fill
    const fillGrad = ctx.createLinearGradient(0, 0, 0, h);
    fillGrad.addColorStop(0, `${color}35`);
    fillGrad.addColorStop(1, `${color}00`);

    ctx.beginPath();
    pts.forEach((p, i) => {
      if (i === 0) ctx.moveTo(p.x, p.y);
      else {
        const cp = pts[i - 1];
        ctx.bezierCurveTo(cp.x + (p.x - cp.x) / 2, cp.y, p.x - (p.x - cp.x) / 2, p.y, p.x, p.y);
      }
    });
    ctx.lineTo(pts[pts.length - 1].x, h);
    ctx.lineTo(pts[0].x, h);
    ctx.closePath();
    ctx.fillStyle = fillGrad;
    ctx.fill();

    // Glow line
    ctx.beginPath();
    pts.forEach((p, i) => {
      if (i === 0) ctx.moveTo(p.x, p.y);
      else {
        const cp = pts[i - 1];
        ctx.bezierCurveTo(cp.x + (p.x - cp.x) / 2, cp.y, p.x - (p.x - cp.x) / 2, p.y, p.x, p.y);
      }
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.8;
    ctx.shadowBlur = 8;
    ctx.shadowColor = color;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // End dot
    const last = pts[pts.length - 1];
    ctx.beginPath();
    ctx.arc(last.x, last.y, 3, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.shadowBlur = 10;
    ctx.shadowColor = color;
    ctx.fill();
    ctx.shadowBlur = 0;
  }, [values, color, h]);

  return (
    <div style={{ position: "relative" }}>
      {label && (
        <div style={{ fontSize: 9, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>{label}</div>
      )}
      <canvas ref={ref} style={{ display: "block", width: "100%" }} />
    </div>
  );
}

/* ─── Horizontal bar with glow ───────────────────────────────── */
function GlowBar({
  pct, color, label, value,
}: {
  pct: number; color: string; label: string; value: string;
}) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
        <span style={{ fontSize: 10, color: "var(--text-secondary)", fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: 10, color, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>{value}</span>
      </div>
      <div style={{ height: 3, background: "rgba(255,255,255,0.05)", borderRadius: 4, overflow: "hidden", position: "relative" }}>
        <div style={{
          position: "absolute", left: 0, top: 0, height: "100%",
          width: `${Math.min(100, pct)}%`,
          background: `linear-gradient(90deg, ${color}88, ${color})`,
          borderRadius: 4,
          boxShadow: `0 0 4px ${color}66`,
          transition: "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
        }} />
      </div>
    </div>
  );
}

/* ─── Hexagonal stat badge ────────────────────────────────────── */
function HexStat({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      padding: "8px 6px", gap: 2, position: "relative",
      background: `linear-gradient(135deg, ${color}0D, ${color}06)`,
      border: `1px solid ${color}25`,
      borderRadius: 8,
      transition: "all 0.2s ease",
    }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLDivElement).style.borderColor = `${color}55`;
        (e.currentTarget as HTMLDivElement).style.boxShadow = `0 0 10px ${color}18, inset 0 0 10px ${color}05`;
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.borderColor = `${color}25`;
        (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
      }}
    >
      <div style={{
        fontSize: 16, fontWeight: 700, color,
        fontFamily: "'JetBrains Mono', monospace", lineHeight: 1,
        textShadow: `0 0 6px ${color}66`,
      }}>{value}</div>
      <div style={{ fontSize: 8, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", textAlign: "center" }}>{label}</div>
    </div>
  );
}

/* ─── Live pulse indicator ────────────────────────────────────── */
function PulseDot({ color, label, value }: { color: string; label: string; value: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 0", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
      <div style={{ position: "relative", flexShrink: 0 }}>
        <div style={{
          width: 6, height: 6, borderRadius: "50%", background: color,
          boxShadow: `0 0 4px ${color}`,
        }} />
      </div>
      <span style={{ flex: 1, fontSize: 10, color: "var(--text-secondary)" }}>{label}</span>
      <span style={{ fontSize: 10, color, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>{value}</span>
    </div>
  );
}

/* ─── Glass panel wrapper ─────────────────────────────────────── */
function GlassPanel({
  children, style, accent,
}: {
  children: React.ReactNode; style?: React.CSSProperties; accent?: string;
}) {
  return (
    <div style={{
      background: "linear-gradient(135deg, rgba(14,26,43,0.9), rgba(10,16,30,0.95))",
      border: `1px solid ${accent ? `${accent}20` : "rgba(255,255,255,0.07)"}`,
      borderRadius: 12,
      backdropFilter: "blur(12px)",
      boxShadow: accent
        ? `0 2px 12px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05), 0 0 20px ${accent}08`
        : "0 2px 12px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
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
      display: "flex", alignItems: "center", gap: 6,
      fontSize: 9, fontWeight: 700, color,
      textTransform: "uppercase", letterSpacing: "0.1em",
      marginBottom: 8,
    }}>
      <span>{children}</span>
      <div style={{ flex: 1, height: 1, background: `linear-gradient(90deg, ${color}20, transparent)`, marginLeft: 4 }} />
    </div>
  );
}

/* ─── Main StatsPage ──────────────────────────────────────────── */
export default function StatsPage({ alerts, tracks, dashboard, eventsPerHr, threatScore, onClose }: {
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
  const totalEvents = Object.values(domainCounts).reduce((s, v) => s + v, 0);
  const domainColors: Record<string, string> = {
    air: "#4DA3FF", maritime: "#00D084", seismic: "#FFB020", rf: "#FF4D4F", cyber: "#A855F7",
  };
  const severityColors: Record<string, string> = {
    CATASTROPHIC: "#B80000", CRITICAL: "#FF4D4F", ELEVATED: "#FF8C00", SUSPICIOUS: "#FFB020", INFORMATIONAL: "#6E7B91",
  };
  const avgConfidence = alerts.length
    ? (alerts.reduce((s, a) => s + (a.confidence || 0.5), 0) / alerts.length) * 100
    : 0;
  const missileCount = tracks.filter(t => t.is_missile).length;
  const fighterCount = tracks.filter(t => t.classification === "military" && !t.is_missile && t.domain === "air").length;
  const droneCount = tracks.filter(t => t.classification === "uav").length;
  const warshipCount = tracks.filter(t => t.classification === "military" && t.domain === "maritime").length;
  const criticalCount = alerts.filter(a => a.threat_class === "CATASTROPHIC" || a.threat_class === "CRITICAL").length;
  const sensorsOnline = Object.values(dashboard?.sensors || {}).filter(Boolean).length;
  const sensorsTotal = Object.keys(dashboard?.sensors || {}).length || 1;
  const sensorPct = Math.round((sensorsOnline / sensorsTotal) * 100);
  const healthIndex = Math.max(0, Math.min(100, 100 - threatScore + (sensorPct * 0.2)));
  const detectionIndex = Math.round(avgConfidence);
  const volatilityIndex = Math.min(100, Math.round((criticalCount / Math.max(1, alerts.length)) * 100 + threatScore * 0.5));
  const integrityIndex = dashboard?.blockchain_synced ? 98 : 45;
  const alertRate24h = dashboard?.alerts_24h ? (dashboard.alerts_24h / 24).toFixed(1) : "0";

  const sparkBase = Array.from({ length: 60 }, (_, i) =>
    Math.max(1, eventsPerSec + Math.round((Math.sin(i * 0.4) + (Math.random() - 0.5)) * eventsPerSec * 0.4))
  );
  const threatTrend = Array.from({ length: 30 }, (_, i) =>
    Math.max(0, threatScore + Math.round((Math.sin(i * 0.5) * 15) + (Math.random() - 0.5) * 10))
  );

  const severityCounts = SEVERITY_ORDER.map(s => ({
    label: s, count: alerts.filter(a => a.threat_class === s).length,
    color: severityColors[s],
  }));

  const threatColor = threatScore < 20 ? "#00D084"
    : threatScore < 50 ? "#FFB020"
      : threatScore < 75 ? "#FF8C00"
        : "#FF4D4F";

  const services = [
    { label: "WebSocket Feed", status: dashboard ? "LIVE" : "DOWN", color: dashboard ? "#00D084" : "#FF4D4F" },
    { label: "Kafka Stream", status: "ACTIVE", color: "#00D084" },
    { label: "API Gateway", status: "200 OK", color: "#00D084" },
    { label: "Database", status: "SYNCED", color: "#00D084" },
    { label: "Blockchain", status: dashboard?.blockchain_synced ? "VERIFIED" : "PENDING", color: dashboard?.blockchain_synced ? "#A855F7" : "#FFB020" },
    { label: "ML Fusion Engine", status: "RUNNING", color: "#4DA3FF" },
  ];

  return (
    <div style={{
      height: "100vh", display: "flex", flexDirection: "column",
      background: "radial-gradient(ellipse at 20% 20%, rgba(77,163,255,0.04) 0%, transparent 60%), radial-gradient(ellipse at 80% 80%, rgba(168,85,247,0.04) 0%, transparent 60%), #07111F",
      overflow: "hidden", fontFamily: "'Inter', -apple-system, sans-serif",
    }}>
      <style>{`
        @keyframes pulse-ring {
          0% { transform: scale(1); opacity: 1; }
          100% { transform: scale(2.5); opacity: 0; }
        }
        @keyframes stat-glow {
          0%, 100% { opacity: 0.7; }
          50% { opacity: 1; }
        }
        @keyframes slide-in {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .stats-animate { animation: slide-in 0.4s ease both; }
      `}</style>

      {/* ── Navbar ── */}
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 16px", flexShrink: 0,
        background: "linear-gradient(180deg, rgba(14,26,43,0.98), rgba(10,20,36,0.95))",
        borderBottom: "1px solid rgba(77,163,255,0.12)",
        backdropFilter: "blur(20px)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{
            padding: "4px 8px", borderRadius: 6,
            background: "linear-gradient(135deg, #4DA3FF11, #4DA3FF05)",
            border: "1px solid rgba(77,163,255,0.2)",
            display: "flex", alignItems: "center", gap: 8
          }}>
            <span style={{ fontSize: 11, fontWeight: 900, color: "#fff", letterSpacing: "0.1em" }}>SENTINEL-X</span>
            <span style={{ color: "rgba(255,255,255,0.1)" }}>|</span>
            <span style={{ fontSize: 10, color: threatColor, fontWeight: 700 }}>THREAT {threatScore}%</span>
          </div>
          <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "'JetBrains Mono', monospace" }}>{clock}</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 10, color: "var(--text-muted)" }}>SENSORS {sensorsOnline}/{sensorsTotal}</span>
          <button onClick={onClose} style={{
            padding: "4px 12px", borderRadius: 6,
            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
            color: "var(--text-secondary)", fontSize: 10, fontWeight: 600, cursor: "pointer",
          }}>← RETURN</button>
        </div>
      </header>

      {/* ── Main content ── */}
      <div style={{ flex: 1, minHeight: 0, overflow: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>

        {/* ── Row 1 ── */}
        <div className="stats-animate" style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 16, alignItems: "start" }}>
          <GlassPanel accent="#FF4D4F" style={{ padding: "16px", display: "flex", gap: 12, alignItems: "center" }}>
            <ArcGauge value={threatScore} label="Threat" sublabel="SCORE" color={threatColor} size={90} />
            <div style={{ width: 1, height: 60, background: "rgba(255,255,255,0.06)" }} />
            <ArcGauge value={healthIndex} label="Health" sublabel="INDEX" color={healthIndex > 70 ? "#00D084" : "#FFB020"} size={90} />
          </GlassPanel>

          <GlassPanel style={{ padding: "16px" }}>
            <SectionLabel color="var(--text-muted)">Active Threat Entities</SectionLabel>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6 }}>
              <HexStat label="Missiles" value={missileCount} color="#FF4D4F" />
              <HexStat label="Fighters" value={fighterCount} color="#4DA3FF" />
              <HexStat label="Drones" value={droneCount} color="#FFB020" />
              <HexStat label="Warships" value={warshipCount} color="#00D084" />
              <HexStat label="Hot Threats" value={tracks.filter(t => t.is_threat).length} color="#FF8C00" />
              <HexStat label="Total Tracks" value={tracks.length} color="#A855F7" />
            </div>
          </GlassPanel>

          <GlassPanel accent="#4DA3FF" style={{ padding: "16px", display: "flex", gap: 12, alignItems: "center" }}>
            <ArcGauge value={detectionIndex} label="Detection" sublabel="RATE" color="#4DA3FF" size={90} />
            <div style={{ width: 1, height: 60, background: "rgba(255,255,255,0.06)" }} />
            <ArcGauge value={volatilityIndex} label="Volatility" sublabel="INDEX" color={volatilityIndex < 30 ? "#00D084" : volatilityIndex < 60 ? "#FFB020" : "#FF4D4F"} size={90} />
          </GlassPanel>
        </div>

        {/* ── Row 2: KPI strip ── */}
        <div className="stats-animate" style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
          {[
            { label: "Events / Second", value: eventsPerSec.toLocaleString(), color: "#4DA3FF" },
            { label: "Events / Hour", value: parseInt((eventsPerHr || "0").replace(/,/g, "")).toLocaleString(), color: "#4DA3FF" },
            { label: "Total Domain Events", value: totalEvents.toLocaleString(), color: "#A855F7" },
            { label: "Active Tracks", value: (dashboard?.active_tracks.total ?? 0).toLocaleString(), color: "#00D084" },
            { label: "Alerts (24h)", value: (dashboard?.alerts_24h ?? 0).toLocaleString(), color: "#FF4D4F" },
            { label: "Alert Rate", value: `${alertRate24h}/hr`, color: "#FFB020" },
          ].map((kpi, idx) => (
            <GlassPanel key={kpi.label} accent={kpi.color} style={{ padding: "12px", animationDelay: `${idx * 0.02}s` }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: kpi.color, fontFamily: "'JetBrains Mono', monospace" }}>{kpi.value}</div>
              <div style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 2, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>{kpi.label}</div>
            </GlassPanel>
          ))}
        </div>

        {/* ── Row 3 ── */}
        <div className="stats-animate" style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 16 }}>
          <GlassPanel accent="#4DA3FF" style={{ padding: "16px" }}>
            <SectionLabel color="#4DA3FF">Event Throughput — Rolling 60s</SectionLabel>
            <GlowSparkline values={sparkBase} color="#4DA3FF" h={60} />
          </GlassPanel>
          <GlassPanel accent="#A855F7" style={{ padding: "16px" }}>
            <SectionLabel color="#A855F7">Domain Distribution</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {Object.entries(domainCounts).sort((a, b) => b[1] - a[1]).map(([k, v]) => {
                const pct = totalEvents > 0 ? (v / totalEvents) * 100 : 0;
                return <GlowBar key={k} label={k.toUpperCase()} value={`${pct.toFixed(0)}%`} pct={pct} color={domainColors[k] || "#6E7B91"} />;
              })}
            </div>
          </GlassPanel>
          <GlassPanel accent="#FF4D4F" style={{ padding: "16px" }}>
            <SectionLabel color="#FF4D4F">Severity Breakdown</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {severityCounts.map(s => {
                const pct = alerts.length > 0 ? (s.count / alerts.length) * 100 : 0;
                return <GlowBar key={s.label} label={s.label} value={`${pct.toFixed(0)}%`} pct={pct} color={s.color} />;
              })}
            </div>
          </GlassPanel>
        </div>

      </div>
    </div>
  );
}
