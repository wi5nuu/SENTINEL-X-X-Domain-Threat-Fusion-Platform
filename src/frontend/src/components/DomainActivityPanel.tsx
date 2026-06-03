import { useEffect, useState, useRef } from "react";

const DOMAIN_META: Record<string, { label: string; color: string; icon: string }> = {
  air: { label: "AIR", color: "#00D4FF", icon: "✈" },
  maritime: { label: "MARITIME", color: "#22C55E", icon: "⚓" },
  seismic: { label: "SEISMIC", color: "#F59E0B", icon: "〰" },
  rf: { label: "RF", color: "#EF4444", icon: "📡" },
  cyber: { label: "CYBER", color: "#A855F7", icon: "🖥" },
};

function AnimatedNumber({ value, color }: { value: number; color: string }) {
  const [display, setDisplay] = useState(value);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const start = display;
    const diff = value - start;
    const duration = 400;
    const startTime = performance.now();

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(start + diff * eased));
      if (progress < 1) animRef.current = requestAnimationFrame(tick);
    };

    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <span style={{ color }}>
      {display.toLocaleString()}
    </span>
  );
}

export default function DomainActivityPanel({ counts = {} }: { counts: Record<string, number> }) {
  const maxVal = Math.max(...Object.values(counts), 1);

  const domains = Object.keys(DOMAIN_META);
  const timeStr = new Date().toLocaleTimeString();

  return (
    <div className="h-full flex flex-col gap-1">
      <div className="flex justify-between text-[9px] text-gray-600 shrink-0">
        <span>LIVE</span>
        <span>{timeStr}</span>
      </div>
      <div className="flex-1 flex flex-col justify-around">
        {domains.map((d) => {
          const meta = DOMAIN_META[d];
          const val = counts[d] || 0;
          const pct = (val / maxVal) * 100;
          return (
            <div key={d}>
              <div className="flex items-center gap-1.5 text-[10px]">
                <span className="w-3 text-center">{meta.icon}</span>
                <span className="w-14 text-gray-400 font-bold tracking-wider" style={{ color: meta.color }}>
                  {meta.label}
                </span>
                <div className="flex-1 h-2 bg-gray-900 rounded overflow-hidden">
                  <div
                    className="h-full rounded transition-all duration-500 ease-out"
                    style={{
                      width: `${Math.max(pct, 2)}%`,
                      backgroundColor: meta.color,
                      boxShadow: `0 0 6px ${meta.color}`,
                    }}
                  />
                </div>
                <div className="w-16 text-right font-mono text-gray-300">
                  <AnimatedNumber value={val} color={meta.color} />
                </div>
              </div>
              <div className="text-[8px] text-gray-600 ml-[4.5rem] mt-0.5">{((val / (Object.values(counts).reduce((a, b) => a + b, 0) || 1)) * 100).toFixed(1)}% of total</div>
            </div>
          );
        })}
      </div>
      <div className="text-[9px] text-gray-600 pt-1 shrink-0" style={{ borderTop: "1px solid rgba(128,128,128,0.12)" }}>
        Total: {Object.values(counts).reduce((a, b) => a + b, 0).toLocaleString()} events
      </div>
    </div>
  );
}
