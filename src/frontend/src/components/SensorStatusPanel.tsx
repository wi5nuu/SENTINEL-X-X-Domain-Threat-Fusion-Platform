import { useEffect, useState } from "react";
import TacticalMetricsPanel from "./TacticalMetricsPanel";

export default function SensorStatusPanel({
  status = {},
  activeFilter,
  onFilterChange
}: {
  status?: Record<string, boolean>;
  activeFilter: string;
  onFilterChange: (f: string) => void;
}) {
  const [sensors, setSensors] = useState<any[]>([]);

  useEffect(() => {
    const fetchPresets = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/v1/ui-presets");
        if (res.ok) {
          const data = await res.json();
          setSensors(data.sensors || []);
        }
      } catch (err) {
        console.error("Failed to load sensors:", err);
      }
    };
    fetchPresets();
  }, []);

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-2 gap-1 text-[10px]">
        {sensors.map((s) => {
          const online = status[s.id] !== false;
          return (
            <div key={s.id} className="flex items-center gap-1">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  online ? "bg-green-400" : "bg-red-500"
                }`}
              />
              <span className={online ? "text-gray-300" : "text-gray-600"}>
                {s.label}
              </span>
            </div>
          );
        })}
      </div>
      <TacticalMetricsPanel activeFilter={activeFilter} onFilterChange={onFilterChange} />
    </div>
  );
}
