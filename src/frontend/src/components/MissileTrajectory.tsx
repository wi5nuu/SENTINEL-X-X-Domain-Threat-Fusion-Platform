import { useState } from "react";
import { Activity, Target, Shield, Crosshair } from "lucide-react";

type TrajectoryPoint = {
  time_s: number; lat: number; lon: number; altitude_km: number; speed_ms: number; phase: string; downrange_km: number;
};

type SimulationResult = {
  WARNING: string;
  missile: string;
  operator_country: string;
  total_range_km: number;
  total_flight_s: number;
  total_flight_min: number;
  points: TrajectoryPoint[];
  interception_analysis: {
    threatened_defense_systems: any[];
    estimated_intercept_probability: number;
  };
};

export default function MissileTrajectory({ onSimulationComplete }: { onSimulationComplete: (res: SimulationResult) => void }) {
  const [missileName, setMissileName] = useState("RS-28 Sarmat");
  const [launchLat, setLaunchLat] = useState("62.96");
  const [launchLon, setLaunchLon] = useState("40.69");
  const [targetLat, setTargetLat] = useState("38.89");
  const [targetLon, setTargetLon] = useState("-77.03");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);

  const runSimulation = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/missile/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          missile: missileName,
          launch_lat: parseFloat(launchLat),
          launch_lon: parseFloat(launchLon),
          target_lat: parseFloat(targetLat),
          target_lon: parseFloat(targetLon),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setResult(data);
        onSimulationComplete(data);
      } else {
        alert("Simulation failed or not found.");
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col gap-4 p-4 text-white">
      <div className="flex items-center gap-2 border-b border-gray-800 pb-2">
        <Target className="w-5 h-5 text-purple-500" />
        <h2 className="text-sm font-bold tracking-widest text-purple-500">WHAT-IF SIMULATOR</h2>
      </div>

      <div className="flex flex-col gap-2 font-mono text-xs">
        <label className="text-gray-400">Missile Model</label>
        <input type="text" value={missileName} onChange={(e) => setMissileName(e.target.value)} className="bg-gray-900 border border-gray-700 rounded px-2 py-1" />

        <div className="grid grid-cols-2 gap-2 mt-2">
          <div>
            <label className="text-gray-400 text-[10px]">Launch Lat</label>
            <input type="text" value={launchLat} onChange={(e) => setLaunchLat(e.target.value)} className="bg-gray-900 border border-gray-700 rounded px-2 py-1 w-full" />
          </div>
          <div>
            <label className="text-gray-400 text-[10px]">Launch Lon</label>
            <input type="text" value={launchLon} onChange={(e) => setLaunchLon(e.target.value)} className="bg-gray-900 border border-gray-700 rounded px-2 py-1 w-full" />
          </div>
          <div>
            <label className="text-gray-400 text-[10px]">Target Lat</label>
            <input type="text" value={targetLat} onChange={(e) => setTargetLat(e.target.value)} className="bg-gray-900 border border-gray-700 rounded px-2 py-1 w-full" />
          </div>
          <div>
            <label className="text-gray-400 text-[10px]">Target Lon</label>
            <input type="text" value={targetLon} onChange={(e) => setTargetLon(e.target.value)} className="bg-gray-900 border border-gray-700 rounded px-2 py-1 w-full" />
          </div>
        </div>

        <button onClick={runSimulation} disabled={loading} className="mt-4 bg-purple-900/50 hover:bg-purple-800 text-purple-300 font-bold border border-purple-700 rounded py-2 transition-colors">
          {loading ? "COMPUTING PHYSICS..." : "EXECUTE SIMULATION"}
        </button>
      </div>

      {result && (
        <div className="mt-4 bg-black/50 border border-gray-800 rounded p-3 font-mono text-xs">
          <div className="text-red-500 font-bold mb-2 blink">{result.WARNING}</div>
          <div className="text-gray-300 mb-1"><span className="text-gray-500">Weapon:</span> {result.missile}</div>
          <div className="text-gray-300 mb-1"><span className="text-gray-500">Range:</span> {result.total_range_km.toLocaleString()} km</div>
          <div className="text-gray-300 mb-1"><span className="text-gray-500">Flight Time:</span> {result.total_flight_min} min</div>
          
          <div className="mt-3 text-yellow-500 font-bold flex items-center gap-1">
            <Shield className="w-3 h-3" /> Interception Analysis
          </div>
          <div className="text-gray-300 mt-1">
            Probability: {(result.interception_analysis.estimated_intercept_probability * 100).toFixed(1)}%
          </div>
        </div>
      )}
    </div>
  );
}
