import TacticalMetricsPanel from "./TacticalMetricsPanel";

const SENSORS = [
  { id: "opensky", label: "OpenSky Network", domain: "Air" },
  { id: "adsb", label: "ADS-B Exchange", domain: "Air" },
  { id: "ais", label: "AIS Stream", domain: "Maritime" },
  { id: "usgs", label: "USGS Earthquake", domain: "Seismic" },
  { id: "noaa", label: "NOAA SWPC", domain: "Seismic" },
  { id: "sdr", label: "SDR Scanner", domain: "RF" },
  { id: "honeypot", label: "ICS Honeypot", domain: "Cyber" },
  { id: "otx", label: "AlienVault OTX", domain: "Cyber" },
];

export default function SensorStatusPanel({
  status = {},
  activeFilter,
  onFilterChange
}: {
  status?: Record<string, boolean>;
  activeFilter: string;
  onFilterChange: (f: string) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-2 gap-1 text-[10px]">
        {SENSORS.map((s) => {
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
