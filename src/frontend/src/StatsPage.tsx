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
        <div style={{ fontSize: size * 0.09, color: "var(--text-muted)", fontWeight: 500, textAlign: "center", padding: "0 8px", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
        {sublabel && <div style={{ fontSize: size * 0.08, color, opacity: 0.7, letterSpacing: "0.05em" }}>{sublabel}</div>}
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
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <span style={{ fontSize: 10, color: "var(--text-secondary)", fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" }}>{label}</span>
        <span style={{ fontSize: 11, color, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>{value}</span>
      </div>
      <div style={{ height: 4, background: "rgba(255,255,255,0.04)", borderRadius: 4, overflow: "hidden", position: "relative", boxShadow: "inset 0 1px 2px rgba(0,0,0,0.5)" }}>
        <div style={{
          position: "absolute", left: 0, top: 0, height: "100%",
          width: `${Math.min(100, pct)}%`,
          background: `linear-gradient(90deg, ${color}66, ${color})`,
          borderRadius: 4,
          boxShadow: `0 0 8px ${color}88`,
          transition: "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
        }} />
      </div>
    </div>
  );
}

/* ─── Hexagonal stat badge ────────────────────────────────────── */
function HexStat({ label, value, color, icon }: { label: string; value: string | number; color: string; icon?: string }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      padding: "12px 6px", gap: 4, position: "relative",
      background: `linear-gradient(135deg, ${color}11, ${color}05)`,
      border: `1px solid ${color}30`,
      borderRadius: 10,
      transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
      cursor: "default"
    }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLDivElement).style.borderColor = `${color}66`;
        (e.currentTarget as HTMLDivElement).style.boxShadow = `0 0 15px ${color}25, inset 0 0 10px ${color}10`;
        (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)";
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.borderColor = `${color}30`;
        (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
        (e.currentTarget as HTMLDivElement).style.transform = "none";
      }}
    >
      <div style={{
        fontSize: 20, fontWeight: 800, color,
        fontFamily: "'JetBrains Mono', monospace", lineHeight: 1,
        textShadow: `0 0 8px ${color}66`,
      }}>{value}</div>
      <div style={{ fontSize: 9, color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", textAlign: "center" }}>{label}</div>
    </div>
  );
}

/* ─── Glass panel wrapper ─────────────────────────────────────── */
function GlassPanel({
  children, style, accent, className
}: {
  children: React.ReactNode; style?: React.CSSProperties; accent?: string; className?: string;
}) {
  return (
    <div className={className} style={{
      background: "linear-gradient(145deg, rgba(16,28,45,0.95), rgba(10,18,32,0.98))",
      border: `1px solid ${accent ? `${accent}30` : "rgba(255,255,255,0.08)"}`,
      borderRadius: 16,
      backdropFilter: "blur(16px)",
      boxShadow: accent
        ? `0 4px 20px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1), 0 0 25px ${accent}15`
        : "0 4px 20px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05)",
      transition: "all 0.3s ease",
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
      fontSize: 10, fontWeight: 800, color,
      textTransform: "uppercase", letterSpacing: "0.15em",
      marginBottom: 16,
    }}>
      <span>{children}</span>
      <div style={{ flex: 1, height: 1, background: `linear-gradient(90deg, ${color}30, transparent)`, marginLeft: 4 }} />
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
  const unknownCount = tracks.filter(t => t.classification === "unknown").length;
  const cbrnCount = alerts.filter(a => a.domain === "cyber" || a.domain === "rf").length; // Simulated
  
  const criticalCount = alerts.filter(a => a.threat_class === "CATASTROPHIC" || a.threat_class === "CRITICAL").length;
  const sensorsOnline = Object.values(dashboard?.sensors || {}).filter(Boolean).length;
  const sensorsTotal = Object.keys(dashboard?.sensors || {}).length || 1;
  const sensorPct = Math.round((sensorsOnline / sensorsTotal) * 100);
  const healthIndex = Math.max(0, Math.min(100, 100 - threatScore + (sensorPct * 0.2)));
  const detectionIndex = Math.round(avgConfidence) || 88;
  const volatilityIndex = Math.min(100, Math.round((criticalCount / Math.max(1, alerts.length)) * 100 + threatScore * 0.5));
  
  const alertRate24h = dashboard?.alerts_24h ? (dashboard.alerts_24h / 24).toFixed(1) : "0";

  const sparkBase = Array.from({ length: 60 }, (_, i) =>
    Math.max(1, eventsPerSec + Math.round((Math.sin(i * 0.4) + (Math.random() - 0.5)) * eventsPerSec * 0.4))
  );

  const severityCounts = SEVERITY_ORDER.map(s => ({
    label: s, count: alerts.filter(a => a.threat_class === s).length,
    color: severityColors[s],
  }));

  const threatColor = threatScore < 20 ? "#00D084"
    : threatScore < 50 ? "#FFB020"
      : threatScore < 75 ? "#FF8C00"
        : "#FF4D4F";

  return (
    <div style={{
      height: "100vh", display: "flex", flexDirection: "column",
      background: "radial-gradient(circle at 50% 0%, rgba(14,35,65,1) 0%, rgba(5,10,20,1) 100%)",
      overflow: "hidden", fontFamily: "'Inter', -apple-system, sans-serif",
    }}>
      <style>{`
        @keyframes slide-in {
          from { opacity: 0; transform: translateY(15px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .stats-animate { animation: slide-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) both; }
        
        /* Custom scrollbar */
        .stats-scroll::-webkit-scrollbar { width: 6px; }
        .stats-scroll::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
        .stats-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }
        .stats-scroll::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.3); }

        .kpi-card {
          padding: 16px;
          border-radius: 12px;
          background: rgba(255,255,255,0.02);
          border: 1px solid rgba(255,255,255,0.05);
          transition: all 0.3s ease;
        }
        .kpi-card:hover {
          background: rgba(255,255,255,0.04);
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
      `}</style>

      {/* ── Navbar ── */}
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "16px 24px", flexShrink: 0,
        background: "linear-gradient(180deg, rgba(8,14,24,0.98), rgba(6,10,18,0.95))",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        backdropFilter: "blur(20px)",
        boxShadow: "0 4px 24px rgba(0,0,0,0.4)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div style={{
            padding: "8px 16px", borderRadius: 8,
            background: `linear-gradient(135deg, ${threatColor}22, ${threatColor}05)`,
            border: `1px solid ${threatColor}40`,
            display: "flex", alignItems: "center", gap: 12,
            boxShadow: `0 0 20px ${threatColor}22`
          }}>
            <span style={{ fontSize: 13, fontWeight: 900, color: "#fff", letterSpacing: "0.2em" }}>SENTINEL-X</span>
            <span style={{ color: "rgba(255,255,255,0.2)" }}>|</span>
            <span style={{ fontSize: 12, color: threatColor, fontWeight: 800, letterSpacing: "0.1em" }}>THREAT {threatScore}%</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: 9, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.15em" }}>Master Clock</span>
            <span style={{ fontSize: 13, color: "var(--text-primary)", fontFamily: "'JetBrains Mono', monospace", fontWeight: 700 }}>{clock}</span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
            <span style={{ fontSize: 9, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.15em" }}>Global Sensors</span>
            <span style={{ fontSize: 13, color: sensorsOnline === sensorsTotal ? "#00D084" : "#FFB020", fontWeight: 800, fontFamily: "'JetBrains Mono', monospace" }}>{sensorsOnline} / {sensorsTotal} ONLINE</span>
          </div>
          <button onClick={onClose} style={{
            padding: "8px 20px", borderRadius: 8,
            background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.15)",
            color: "var(--text-primary)", fontSize: 11, fontWeight: 700, cursor: "pointer",
            textTransform: "uppercase", letterSpacing: "0.1em",
            transition: "all 0.2s"
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.1)"; }}
          onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.06)"; }}
          >Return to Core</button>
        </div>
      </header>

      {/* ── Main content ── */}
      <div className="stats-scroll" style={{ flex: 1, overflow: "auto", padding: "24px", display: "flex", flexDirection: "column", gap: 24 }}>

        {/* ── Top Level Gauges & Entities ── */}
        <div className="stats-animate" style={{ display: "grid", gridTemplateColumns: "1fr 2fr 1fr", gap: 24, alignItems: "stretch" }}>
          
          <GlassPanel accent={threatColor} style={{ padding: "24px", display: "flex", gap: 16, alignItems: "center", justifyContent: "space-around" }}>
            <ArcGauge value={threatScore} label="Threat" sublabel="SCORE" color={threatColor} size={110} />
            <div style={{ width: 1, height: 80, background: "rgba(255,255,255,0.08)" }} />
            <ArcGauge value={healthIndex} label="Health" sublabel="INDEX" color={healthIndex > 70 ? "#00D084" : "#FFB020"} size={110} />
          </GlassPanel>

          <GlassPanel style={{ padding: "24px" }}>
            <SectionLabel color="var(--text-primary)">Active Threat Entities</SectionLabel>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginTop: 16 }}>
              <HexStat label="Missiles" value={missileCount} color="#FF4D4F" />
              <HexStat label="Fighters" value={fighterCount} color="#4DA3FF" />
              <HexStat label="Drones" value={droneCount} color="#FFB020" />
              <HexStat label="Warships" value={warshipCount} color="#00D084" />
              <HexStat label="Cyber/RF" value={cbrnCount} color="#A855F7" />
              <HexStat label="Unknowns" value={unknownCount} color="#6E7B91" />
              <HexStat label="Hot Threats" value={tracks.filter(t => t.is_threat).length} color="#FF8C00" />
              <HexStat label="Total Tracks" value={tracks.length} color="#fff" />
            </div>
          </GlassPanel>

          <GlassPanel accent="#4DA3FF" style={{ padding: "24px", display: "flex", gap: 16, alignItems: "center", justifyContent: "space-around" }}>
            <ArcGauge value={detectionIndex} label="Detection" sublabel="CONFIDENCE" color="#4DA3FF" size={110} />
            <div style={{ width: 1, height: 80, background: "rgba(255,255,255,0.08)" }} />
            <ArcGauge value={volatilityIndex} label="Volatility" sublabel="INDEX" color={volatilityIndex < 30 ? "#00D084" : volatilityIndex < 60 ? "#FFB020" : "#FF4D4F"} size={110} />
          </GlassPanel>
        </div>

        {/* ── KPI Strip ── */}
        <div className="stats-animate" style={{ animationDelay: "0.1s" }}>
          <GlassPanel style={{ padding: "20px" }}>
            <SectionLabel color="var(--text-primary)">System Telemetry & Rates</SectionLabel>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 16 }}>
              {[
                { label: "Events / Sec", value: eventsPerSec.toLocaleString(), color: "#4DA3FF" },
                { label: "Events / Hour", value: parseInt((eventsPerHr || "0").replace(/,/g, "")).toLocaleString(), color: "#4DA3FF" },
                { label: "Total Domain Evts", value: totalEvents.toLocaleString(), color: "#A855F7" },
                { label: "Active Tracks", value: (dashboard?.active_tracks.total ?? 0).toLocaleString(), color: "#00D084" },
                { label: "Alerts (24h)", value: (dashboard?.alerts_24h ?? 0).toLocaleString(), color: "#FF4D4F" },
                { label: "Alert Rate", value: `${alertRate24h}/hr`, color: "#FFB020" },
                { label: "Blockchain Sync", value: dashboard?.blockchain_synced ? "VERIFIED" : "SYNCING", color: dashboard?.blockchain_synced ? "#A855F7" : "#FFB020" },
                { label: "AI Fusion", value: `${detectionIndex}%`, color: "#4DA3FF" },
              ].map((kpi, idx) => (
                <div key={idx} className="kpi-card" style={{ borderLeft: `3px solid ${kpi.color}` }}>
                  <div style={{ fontSize: 18, fontWeight: 800, color: kpi.color, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.05em" }}>{kpi.value}</div>
                  <div style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 6, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>{kpi.label}</div>
                </div>
              ))}
            </div>
          </GlassPanel>
        </div>

        {/* ── Breakdown & Sparklines ── */}
        <div className="stats-animate" style={{ animationDelay: "0.2s", display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 24 }}>
          
          <GlassPanel accent="#4DA3FF" style={{ padding: "24px", display: "flex", flexDirection: "column" }}>
            <SectionLabel color="#4DA3FF">Event Throughput — Rolling 60s</SectionLabel>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
              <GlowSparkline values={sparkBase} color="#4DA3FF" h={120} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16, borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 16 }}>
              <div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>Peak Rate</div>
                <div style={{ fontSize: 16, color: "#fff", fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>{Math.max(...sparkBase).toLocaleString()} eps</div>
              </div>
              <div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>Average Rate</div>
                <div style={{ fontSize: 16, color: "#4DA3FF", fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>{eventsPerSec.toLocaleString()} eps</div>
              </div>
              <div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>Data Ingest</div>
                <div style={{ fontSize: 16, color: "#00D084", fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>STABLE</div>
              </div>
            </div>
          </GlassPanel>

          <GlassPanel accent="#A855F7" style={{ padding: "24px" }}>
            <SectionLabel color="#A855F7">Domain Distribution</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 16 }}>
              {Object.entries(domainCounts).sort((a, b) => b[1] - a[1]).map(([k, v]) => {
                const pct = totalEvents > 0 ? (v / totalEvents) * 100 : 0;
                return <GlowBar key={k} label={k} value={`${pct.toFixed(0)}%`} pct={pct} color={domainColors[k] || "#6E7B91"} />;
              })}
            </div>
          </GlassPanel>

          <GlassPanel accent="#FF4D4F" style={{ padding: "24px" }}>
            <SectionLabel color="#FF4D4F">Severity Breakdown</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 16 }}>
              {severityCounts.map(s => {
                const pct = alerts.length > 0 ? (s.count / alerts.length) * 100 : 0;
                return <GlowBar key={s.label} label={s.label} value={`${pct.toFixed(0)}%`} pct={pct} color={s.color} />;
              })}
            </div>
          </GlassPanel>

        </div>

        {/* ── Recent Critical Alerts & Sensor Health ── */}
        <div className="stats-animate" style={{ animationDelay: "0.3s", display: "grid", gridTemplateColumns: "2fr 1fr", gap: 24 }}>
          
          <GlassPanel accent="#FFB020" style={{ padding: "24px" }}>
            <SectionLabel color="#FFB020">Recent Critical / Elevated Alerts</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 16, maxHeight: "250px", overflowY: "auto", paddingRight: 8 }} className="stats-scroll">
              {alerts.filter(a => a.threat_class === "CRITICAL" || a.threat_class === "CATASTROPHIC" || a.threat_class === "ELEVATED").slice(0, 8).map((alert, i) => (
                <div key={i} style={{ 
                  display: "flex", alignItems: "center", justifyContent: "space-between", 
                  padding: "12px 16px", background: "rgba(255,255,255,0.03)", borderRadius: 8,
                  borderLeft: `4px solid ${severityColors[alert.threat_class]}` 
                }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{alert.description.length > 40 ? alert.description.substring(0, 40) + '...' : alert.description}</span>
                    <div style={{ display: "flex", gap: 12, fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                      <span>Domain: <span style={{ color: domainColors[alert.domain] || "#fff" }}>{alert.domain}</span></span>
                      <span>Conf: {(alert.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <div style={{ 
                    padding: "4px 10px", borderRadius: 6, fontSize: 10, fontWeight: 800, letterSpacing: "0.1em",
                    background: `${severityColors[alert.threat_class]}15`, color: severityColors[alert.threat_class],
                    border: `1px solid ${severityColors[alert.threat_class]}40`
                  }}>
                    {alert.threat_class}
                  </div>
                </div>
              ))}
              {alerts.filter(a => a.threat_class === "CRITICAL" || a.threat_class === "CATASTROPHIC" || a.threat_class === "ELEVATED").length === 0 && (
                <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>No critical alerts active.</div>
              )}
            </div>
          </GlassPanel>

          <GlassPanel style={{ padding: "24px" }}>
            <SectionLabel color="var(--text-primary)">Sensor Node Status</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 16 }}>
              {["ADS-B Air", "AIS Maritime", "USGS Seismic", "SDR Radio", "Cyber Honeypot", "NASA Satellite", "Threat Intel", "Blockchain Node"].map((sensor, idx) => {
                const isOnline = idx < sensorsOnline;
                return (
                  <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 12px", background: "rgba(255,255,255,0.02)", borderRadius: 8, border: "1px solid rgba(255,255,255,0.05)" }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-primary)" }}>{sensor}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 10, color: isOnline ? "#00D084" : "#FF4D4F", fontWeight: 700, letterSpacing: "0.1em" }}>{isOnline ? "ONLINE" : "OFFLINE"}</span>
                      <div style={{ width: 8, height: 8, borderRadius: "50%", background: isOnline ? "#00D084" : "#FF4D4F", boxShadow: `0 0 8px ${isOnline ? "#00D084" : "#FF4D4F"}` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </GlassPanel>

        </div>

      </div>
    </div>
  );
}
