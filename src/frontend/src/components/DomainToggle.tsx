const DOMAINS = [
  { id: "air", label: "Air", color: "#00D4FF" },
  { id: "maritime", label: "Maritime", color: "#22C55E" },
  { id: "seismic", label: "Seismic", color: "#F59E0B" },
  { id: "rf", label: "RF/SIGINT", color: "#EF4444" },
  { id: "cyber", label: "Cyber", color: "#A855F7" },
];

export default function DomainToggle({
  active = {} as Record<string, boolean>,
  onToggle = (_id: string) => {},
}) {
  return (
    <div className="flex gap-3 text-xs">
      {DOMAINS.map((d) => {
        const isOn = active[d.id] !== false;
        return (
          <button
            key={d.id}
            onClick={() => onToggle(d.id)}
            className={`flex items-center gap-1.5 px-2 py-1 rounded border transition-colors ${
              isOn
                ? "border-[#00D4FF]/40 bg-[#00D4FF]/10"
                : "border-gray-700 text-gray-600"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isOn ? "bg-[#00D4FF]" : "bg-gray-700"
              }`}
              style={isOn ? { backgroundColor: d.color } : {}}
            />
            {d.label}
          </button>
        );
      })}
    </div>
  );
}
