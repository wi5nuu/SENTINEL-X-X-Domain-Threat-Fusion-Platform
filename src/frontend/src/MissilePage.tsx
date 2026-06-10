import { useState, useEffect } from "react";
import MissilePanel from "./components/MissilePanel";
import MissileTrajectory from "./components/MissileTrajectory";
import Globe3D from "./components/Globe3D";
import type { MissileTrail } from "./components/Globe3D";

type MissilePageProps = {
  onClose: () => void;
};

export default function MissilePage({ onClose }: MissilePageProps) {
  const [tracks, setTracks] = useState<any[]>([]);
  const [missileTrails, setMissileTrails] = useState<MissileTrail[]>([]);

  // Poll live OSINT missile events from backend every 5s
  useEffect(() => {
    const fetchLiveTracks = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/v1/missile/live-tracks');
        if (res.ok) {
          const events = await res.json();
          const mappedTracks = events.map((e: any) => ({
            label: e.event_id,
            lat: e.target_lat || 0,
            lon: e.target_lon || 0,
            origin_lat: e.launch_lat,
            origin_lon: e.launch_lon,
            target_lat: e.target_lat,
            target_lon: e.target_lon,
            is_missile: true,
            is_threat: true,
            color: "#EF4444",
            missile_type: e.missile_type,
            heading: 0,
          }));
          setTracks(mappedTracks);
        }
      } catch (e) {
        console.error(e);
      }
    };
    fetchLiveTracks();
    const iv = setInterval(fetchLiveTracks, 5000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div
      style={{
        height: '100vh', width: '100vw', display: 'flex',
        background: '#010308', color: 'white', overflow: 'hidden',
        position: 'relative', fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      {/* Background Globe */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
        <Globe3D tracks={tracks} missileTrails={missileTrails} />
      </div>

      {/* Top Header bar */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, zIndex: 20,
        padding: '12px 20px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: 'linear-gradient(to bottom, rgba(0,0,0,0.9), transparent)',
        pointerEvents: 'none',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 10, height: 10, borderRadius: '50%',
            background: '#ef4444',
            boxShadow: '0 0 12px #ef4444',
            animation: 'pulse 1.4s infinite',
          }} />
          <span style={{
            fontSize: 16, fontWeight: 900, letterSpacing: '0.2em',
            color: '#ef4444', textShadow: '0 0 20px rgba(239,68,68,0.5)',
          }}>
            MISSILE COMMAND CENTER
          </span>
          {missileTrails.length > 0 && (
            <span style={{
              background: 'rgba(239,68,68,0.15)',
              border: '1px solid rgba(239,68,68,0.4)',
              borderRadius: 4, padding: '2px 10px',
              fontSize: 10, color: '#fca5a5',
              animation: 'pulse 1s infinite',
            }}>
              🚀 {missileTrails.length} MISSILE{missileTrails.length > 1 ? 'S' : ''} IN FLIGHT
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'rgba(0,0,0,0.6)', border: '1px solid rgba(150,150,150,0.4)',
            borderRadius: 6, color: '#9ca3af', padding: '6px 16px',
            fontSize: 10, letterSpacing: '0.1em', cursor: 'pointer',
            pointerEvents: 'auto',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => { (e.target as HTMLElement).style.color = 'white'; }}
          onMouseLeave={(e) => { (e.target as HTMLElement).style.color = '#9ca3af'; }}
        >
          ✕ CLOSE
        </button>
      </div>

      {/* Left Panel — OSINT Intel Feed */}
      <div style={{
        position: 'absolute', top: 60, left: 16, bottom: 16, width: 320,
        background: 'rgba(0,3,15,0.88)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(239,68,68,0.2)',
        borderRadius: 10,
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
        zIndex: 10, pointerEvents: 'auto',
        boxShadow: '0 0 30px rgba(239,68,68,0.07)',
      }}>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          <MissilePanel />
        </div>
      </div>

      {/* Right Panel — What-If Simulator */}
      <div style={{
        position: 'absolute', top: 60, right: 16, bottom: 16, width: 330,
        background: 'rgba(0,3,15,0.88)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(168,85,247,0.2)',
        borderRadius: 10,
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
        zIndex: 10, pointerEvents: 'auto',
        boxShadow: '0 0 30px rgba(168,85,247,0.07)',
      }}>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          <MissileTrajectory
            onSimulationComplete={(res) => {
              // nothing extra needed — trail is handled in MissileTrajectory itself
            }}
            onMissileTrailUpdate={(trails) => {
              setMissileTrails(trails);
            }}
          />
        </div>
      </div>
    </div>
  );
}
