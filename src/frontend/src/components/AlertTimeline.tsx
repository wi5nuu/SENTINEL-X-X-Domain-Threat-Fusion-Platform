import { useState } from "react";

type Alert = {
  alert_id: string;
  timestamp_utc: string;
  threat_class: string;
  confidence: number;
  domain: string;
  description: string;
  ipfs_hash?: string;
};

const THREAT_COLORS: Record<string, string> = {
  INFORMATIONAL: "#6E7B91",
  SUSPICIOUS: "var(--accent-warning)",
  ELEVATED: "#FF8C00",
  CRITICAL: "var(--accent-critical)",
  CATASTROPHIC: "var(--accent-catastrophic)",
};

export default function AlertTimeline({
  alerts = [],
  severityFilter = "",
  onViewBlockchain,
  acknowledgedAlerts,
  onToggleAcknowledge,
}: {
  alerts: Alert[];
  severityFilter?: string;
  onViewBlockchain?: (hash: string) => void;
  acknowledgedAlerts?: Set<string>;
  onToggleAcknowledge?: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = severityFilter
    ? alerts.filter((a) => a.threat_class === severityFilter)
    : alerts;

  return (
    <div style={{ height: "100%", overflowY: "auto", scrollbarWidth: "thin", scrollbarColor: "var(--border-panel) transparent" }}>
      {filtered.length === 0 && (
        <div style={{ color: "var(--text-muted)", fontSize: 11, textAlign: "center", padding: "24px 8px" }}>
          No alerts — systems nominal
        </div>
      )}
      {filtered.map((a) => {
        const isExpanded = expanded === a.alert_id;
        const isAcknowledged = acknowledgedAlerts?.has(a.alert_id);
        const color = a.threat_class === "INFORMATIONAL" ? "#6E7B91" : a.threat_class === "SUSPICIOUS" ? "var(--accent-warning)" : a.threat_class === "ELEVATED" ? "#FF8C00" : a.threat_class === "CRITICAL" ? "var(--accent-critical)" : "var(--accent-catastrophic)";
        return (
          <div key={a.alert_id} style={{
            borderLeft: `3px solid ${color}`,
            padding: "8px 10px",
            marginBottom: 4,
            fontSize: 11,
            cursor: "pointer",
            background: isExpanded ? "rgba(14,26,43,0.8)" : "transparent",
            opacity: isAcknowledged ? 0.5 : 1,
            borderRadius: "0 4px 4px 0",
            transition: "background 0.15s",
          }} onClick={() => setExpanded(isExpanded ? null : a.alert_id)}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 600, fontSize: 10, color, letterSpacing: "0.03em" }}>
                {isExpanded ? "▾" : "▸"} {a.threat_class}
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <button onClick={(e) => { e.stopPropagation(); onToggleAcknowledge?.(a.alert_id); }} style={{
                  fontSize: 9, padding: "2px 6px", borderRadius: 3, cursor: "pointer", border: "1px solid",
                  color: isAcknowledged ? "var(--accent-success)" : "var(--text-muted)",
                  borderColor: isAcknowledged ? "rgba(0,208,132,0.3)" : "var(--border-panel)",
                  background: isAcknowledged ? "rgba(0,208,132,0.08)" : "transparent",
                }} title={isAcknowledged ? "Mark unread" : "Acknowledge"}>
                  {isAcknowledged ? "✓" : "○"}
                </button>
                {(a.threat_class === "CRITICAL" || a.threat_class === "CATASTROPHIC") && (
                  <button onClick={(e) => { e.stopPropagation(); onViewBlockchain?.(a.ipfs_hash || a.alert_id); }} style={{
                    fontSize: 8, padding: "2px 6px", borderRadius: 3, cursor: "pointer",
                    border: "1px solid rgba(168,85,247,0.25)", color: "#A855F7",
                    background: "rgba(168,85,247,0.08)",
                  }} title="View on blockchain">
                    CHAIN
                  </button>
                )}
                <span style={{ color: "var(--text-muted)", fontSize: 10 }}>
                  {(a.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <div style={{ color: isExpanded ? "var(--text-primary)" : "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: isExpanded ? "normal" : "nowrap", marginTop: 1 }}>
              {a.description}
            </div>
            {isExpanded && (
              <div style={{ marginTop: 6, fontSize: 10, color: "var(--text-muted)", borderTop: "1px solid var(--border-subtle)", paddingTop: 4 }}>
                <div><span style={{ color: "var(--text-secondary)" }}>ID:</span> {a.alert_id}</div>
                <div><span style={{ color: "var(--text-secondary)" }}>Domain:</span> {a.domain}</div>
                <div><span style={{ color: "var(--text-secondary)" }}>Confidence:</span> {(a.confidence * 100).toFixed(1)}%</div>
                <div><span style={{ color: "var(--text-secondary)" }}>Timestamp:</span> {new Date(a.timestamp_utc).toLocaleString()}</div>
                <div><span style={{ color: "var(--text-secondary)" }}>Status:</span> <span style={{ color: isAcknowledged ? "var(--accent-success)" : "var(--accent-warning)" }}>{isAcknowledged ? "ACKNOWLEDGED" : "UNREAD"}</span></div>
                {a.ipfs_hash && <div><span style={{ color: "var(--text-secondary)" }}>IPFS:</span> <span style={{ color: "#A855F7" }}>{a.ipfs_hash.slice(0, 24)}...</span></div>}
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: 9, marginTop: 2 }}>
              <span>{a.domain}</span>
              <span>{new Date(a.timestamp_utc).toLocaleTimeString()}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
