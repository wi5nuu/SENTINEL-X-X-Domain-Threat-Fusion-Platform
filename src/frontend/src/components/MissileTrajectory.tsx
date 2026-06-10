import { useState, useEffect } from "react";
import { Activity, Target, Shield, Zap, Globe } from "lucide-react";
import type { MissileTrail } from "./Globe3D";

type TrajectoryPoint = {
  time_s: number; lat: number; lon: number;
  altitude_km: number; speed_ms: number;
  phase: string; downrange_km: number;
};

type SimulationResult = {
  WARNING: string;
  missile: string;
  operator_country: string;
  missile_type?: string;
  total_range_km: number;
  total_flight_s: number;
  total_flight_min: number;
  points: TrajectoryPoint[];
  interception_analysis: {
    threatened_defense_systems: any[];
    estimated_intercept_probability: number;
  };
};

/** Missile color by type */
function missileColor(mtype: string): [number, number, number] {
  const t = (mtype || "").toLowerCase();
  if (t.includes("icbm")) return [255, 60, 60];
  if (t.includes("irbm") || t.includes("mrbm")) return [255, 140, 0];
  if (t.includes("hgv") || t.includes("hypersonic")) return [180, 60, 255];
  if (t.includes("cruise")) return [60, 200, 255];
  if (t.includes("slbm")) return [255, 220, 0];
  if (t.includes("srbm")) return [255, 100, 100];
  return [200, 200, 200];
}

interface MissileTrajectoryProps {
  onSimulationComplete: (res: SimulationResult) => void;
  onMissileTrailUpdate: (trails: MissileTrail[]) => void;
}

export default function MissileTrajectory({
  onSimulationComplete,
  onMissileTrailUpdate,
}: MissileTrajectoryProps) {
  const [countryPresets, setCountryPresets] = useState<Record<string, any>>({});
  const [targetPresets, setTargetPresets] = useState<Record<string, any>>({});
  
  useEffect(() => {
    const fetchPresets = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/v1/ui-presets");
        if (res.ok) {
          const data = await res.json();
          setCountryPresets(data.country_presets || {});
          setTargetPresets(data.target_presets || {});
        }
      } catch (err) {
        console.error("Failed to load presets:", err);
      }
    };
    fetchPresets();
  }, []);

  const [missileName, setMissileName] = useState("RS-28 Sarmat");
  const [launchLat, setLaunchLat] = useState("62.96");
  const [launchLon, setLaunchLon] = useState("40.69");
  const [targetLat, setTargetLat] = useState("38.89");
  const [targetLon, setTargetLon] = useState("-77.03");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [activeTrails, setActiveTrails] = useState<MissileTrail[]>([]);

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
        const data: SimulationResult = await res.json();
        setResult(data);
        onSimulationComplete(data);

        // Build a MissileTrail from the returned waypoints
        const waypoints: [number, number, number][] = data.points.map((p) => [
          p.lon, p.lat, p.altitude_km * 1000, // DeckGL expects meters for 3D
        ]);

        const trail: MissileTrail = {
          id: `sim-${Date.now()}`,
          name: data.missile,
          missile_type: data.missile_type || "ballistic",
          color: missileColor(data.missile_type || ""),
          waypoints,
          total_duration_s: data.total_flight_s,
          launched_at: Date.now(),
        };

        // Replace existing trails (or append if you want multi-launch)
        const newTrails = [...activeTrails, trail].slice(-8); // max 8 simultaneous
        setActiveTrails(newTrails);
        onMissileTrailUpdate(newTrails);

        // Auto-clear trail after flight + 30s
        setTimeout(() => {
          setActiveTrails((prev) => {
            const updated = prev.filter((t) => t.id !== trail.id);
            onMissileTrailUpdate(updated);
            return updated;
          });
        }, (data.total_flight_s + 30) * 1000);
      } else {
        alert("Simulation failed: missile not found in database.");
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const clearTrails = () => {
    setActiveTrails([]);
    onMissileTrailUpdate([]);
    setResult(null);
  };

  const inputStyle: React.CSSProperties = {
    background: 'rgba(0,5,20,0.8)',
    border: '1px solid rgba(120,80,200,0.3)',
    borderRadius: 6,
    padding: '6px 10px',
    color: '#c084fc',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 11,
    width: '100%',
    outline: 'none',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 9,
    color: 'rgba(180,150,255,0.6)',
    fontFamily: "'JetBrains Mono', monospace",
    textTransform: 'uppercase',
    letterSpacing: '0.1em',
    marginBottom: 3,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: 16, color: 'white', fontFamily: "'JetBrains Mono', monospace" }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid rgba(120,80,200,0.3)', paddingBottom: 10 }}>
        <Target size={16} color="#a855f7" />
        <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.2em', color: '#a855f7' }}>WHAT-IF SIMULATOR</span>
        {activeTrails.length > 0 && (
          <span style={{ marginLeft: 'auto', background: 'rgba(255,60,60,0.2)', border: '1px solid rgba(255,60,60,0.5)', borderRadius: 4, padding: '2px 8px', fontSize: 9, color: '#ff6060', animation: 'pulse 1s infinite' }}>
            🚀 {activeTrails.length} IN FLIGHT
          </span>
        )}
      </div>

      {/* Launch origin preset */}
      <div>
        <div style={labelStyle}>Launch Origin</div>
        <select
          style={{ ...inputStyle, cursor: 'pointer' }}
          onChange={(e) => {
            const p = countryPresets[e.target.value];
            if (p) { setLaunchLat(p.lat); setLaunchLon(p.lon); }
          }}
          defaultValue=""
        >
          <option value="" disabled>— Select country preset —</option>
          {Object.entries(countryPresets).map(([k, v]: [string, any]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 6 }}>
          <div>
            <div style={labelStyle}>Launch Lat</div>
            <input type="text" value={launchLat} onChange={(e) => setLaunchLat(e.target.value)} style={inputStyle} />
          </div>
          <div>
            <div style={labelStyle}>Launch Lon</div>
            <input type="text" value={launchLon} onChange={(e) => setLaunchLon(e.target.value)} style={inputStyle} />
          </div>
        </div>
      </div>

      {/* Target preset */}
      <div>
        <div style={labelStyle}>Target</div>
        <select
          style={{ ...inputStyle, cursor: 'pointer' }}
          onChange={(e) => {
            const p = targetPresets[e.target.value];
            if (p) { setTargetLat(p.lat); setTargetLon(p.lon); }
          }}
          defaultValue=""
        >
          <option value="" disabled>— Select target preset —</option>
          {Object.entries(targetPresets).map(([k, v]: [string, any]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 6 }}>
          <div>
            <div style={labelStyle}>Target Lat</div>
            <input type="text" value={targetLat} onChange={(e) => setTargetLat(e.target.value)} style={inputStyle} />
          </div>
          <div>
            <div style={labelStyle}>Target Lon</div>
            <input type="text" value={targetLon} onChange={(e) => setTargetLon(e.target.value)} style={inputStyle} />
          </div>
        </div>
      </div>

      {/* Missile model */}
      <div>
        <div style={labelStyle}>Missile Model</div>
        <input
          type="text"
          value={missileName}
          onChange={(e) => setMissileName(e.target.value)}
          placeholder="e.g. RS-28 Sarmat, Tomahawk BGM-109C, BrahMos NG (IDN Order)"
          style={inputStyle}
        />
      </div>

      {/* Buttons */}
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={runSimulation}
          disabled={loading}
          style={{
            flex: 1,
            background: loading ? 'rgba(120,40,200,0.3)' : 'rgba(168,85,247,0.2)',
            border: '1px solid rgba(168,85,247,0.6)',
            borderRadius: 6,
            color: '#d8b4fe',
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 800,
            fontSize: 10,
            letterSpacing: '0.12em',
            padding: '9px 0',
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s',
          }}
        >
          {loading ? '⏳ COMPUTING PHYSICS...' : '🚀 LAUNCH SIMULATION'}
        </button>
        {activeTrails.length > 0 && (
          <button
            onClick={clearTrails}
            style={{
              background: 'rgba(200,40,40,0.15)',
              border: '1px solid rgba(255,60,60,0.4)',
              borderRadius: 6,
              color: '#f87171',
              fontFamily: "'JetBrains Mono', monospace",
              fontWeight: 700,
              fontSize: 10,
              padding: '9px 12px',
              cursor: 'pointer',
            }}
          >
            ✕ CLEAR
          </button>
        )}
      </div>

      {/* Result panel */}
      {result && (
        <div style={{
          background: 'rgba(0,0,0,0.6)',
          border: '1px solid rgba(168,85,247,0.25)',
          borderRadius: 8,
          padding: 12,
          fontSize: 10,
          color: '#c4b5fd',
        }}>
          <div style={{ color: '#f87171', fontWeight: 800, marginBottom: 8, fontSize: 10 }}>
            ⚠ {result.WARNING}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
            <div><span style={{ color: 'rgba(180,150,255,0.5)' }}>WEAPON</span><br />{result.missile}</div>
            <div><span style={{ color: 'rgba(180,150,255,0.5)' }}>OPERATOR</span><br />{result.operator_country}</div>
            <div><span style={{ color: 'rgba(180,150,255,0.5)' }}>RANGE</span><br />{result.total_range_km.toLocaleString()} km</div>
            <div><span style={{ color: 'rgba(180,150,255,0.5)' }}>FLIGHT TIME</span><br />{result.total_flight_min} min</div>
          </div>
          <div style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid rgba(120,80,200,0.2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#fbbf24', fontWeight: 800, marginBottom: 4 }}>
              <Shield size={12} /> INTERCEPTION ANALYSIS
            </div>
            <div>
              Pk: <span style={{ color: result.interception_analysis.estimated_intercept_probability > 0.5 ? '#4ade80' : '#f87171', fontWeight: 800 }}>
                {(result.interception_analysis.estimated_intercept_probability * 100).toFixed(1)}%
              </span>
            </div>
            {result.interception_analysis.threatened_defense_systems.length > 0 && (
              <div style={{ marginTop: 4 }}>
                Systems engaged:{' '}
                <span style={{ color: '#fcd34d' }}>
                  {result.interception_analysis.threatened_defense_systems.join(', ')}
                </span>
              </div>
            )}
          </div>
          <div style={{ marginTop: 8, color: 'rgba(180,150,255,0.4)', fontSize: 9 }}>
            Trail animating on globe — {result.points.length} waypoints computed
          </div>
        </div>
      )}
    </div>
  );
}
