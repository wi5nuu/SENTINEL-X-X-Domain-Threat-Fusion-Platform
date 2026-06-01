type Alert = {
  alert_id: string;
  timestamp_utc: string;
  threat_class: string;
  confidence: number;
  domain: string;
  description: string;
};

const THREAT_COLORS: Record<string, string> = {
  INFORMATIONAL: "#6B7280",
  SUSPICIOUS: "#F59E0B",
  ELEVATED: "#EF4444",
  CRITICAL: "#DC2626",
  CATASTROPHIC: "#7F1D1D",
};

export default function AlertTimeline({ alerts = [] }: { alerts: Alert[] }) {
  return (
    <div className="h-full overflow-y-auto space-y-1">
      {alerts.length === 0 && (
        <div className="text-gray-600 text-xs text-center py-8">
          No alerts — systems nominal
        </div>
      )}
      {alerts.map((a) => (
        <div
          key={a.alert_id}
          className="border-l-4 pl-2 py-1 text-xs hover:bg-[#0A0E1A]/50 transition-colors"
          style={{ borderColor: THREAT_COLORS[a.threat_class] || "#6B7280" }}
        >
          <div className="flex justify-between items-center">
            <span
              className="font-bold text-[10px] tracking-wider"
              style={{ color: THREAT_COLORS[a.threat_class] }}
            >
              {a.threat_class}
            </span>
            <span className="text-gray-500 text-[10px]">
              {(a.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="text-gray-300 truncate">{a.description}</div>
          <div className="text-gray-600 flex justify-between">
            <span>{a.domain}</span>
            <span>{new Date(a.timestamp_utc).toLocaleTimeString()}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
