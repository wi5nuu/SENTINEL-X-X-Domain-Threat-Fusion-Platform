import { useState, useEffect } from "react";
import MissilePanel from "./components/MissilePanel";
import MissileTrajectory from "./components/MissileTrajectory";
import Globe3D from "./components/Globe3D";

type MissilePageProps = {
  onClose: () => void;
};

export default function MissilePage({ onClose }: MissilePageProps) {
  const [tracks, setTracks] = useState([]);
  const [simPoints, setSimPoints] = useState<any[]>([]);

  useEffect(() => {
    // Fetch live tracks immediately for the globe
    const fetchLiveTracks = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/v1/missile/live-tracks');
        if (res.ok) {
          const events = await res.json();
          // Transform events to 'tracks' for the Globe
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
            flight_progress_pct: e.status === "impacted" || e.status === "intercepted" ? 100 : 50,
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

  const allTracks = [...tracks, ...simPoints];

  return (
    <div className="h-screen w-screen flex bg-black text-white overflow-hidden relative" style={{ fontFamily: "monospace" }}>
      {/* Background Globe Map */}
      <div className="absolute inset-0 z-0">
        <Globe3D tracks={allTracks} />
      </div>

      {/* Header */}
      <div className="absolute top-0 left-0 w-full p-4 z-20 flex justify-between items-center bg-gradient-to-b from-black/80 to-transparent pointer-events-none">
        <div className="text-red-500 font-bold tracking-widest text-xl">MISSILE COMMAND CENTER</div>
        <button onClick={onClose} className="px-4 py-1 border border-gray-600 rounded text-gray-400 hover:text-white hover:border-gray-400 pointer-events-auto bg-black/50 backdrop-blur">
          CLOSE
        </button>
      </div>

      {/* Left Panel - Missile Intel */}
      <div className="absolute top-16 left-4 bottom-4 w-80 bg-black/80 backdrop-blur border border-red-900/50 rounded flex flex-col overflow-hidden z-10 pointer-events-auto">
        <div className="overflow-y-auto flex-1">
          <MissilePanel />
        </div>
      </div>

      {/* Right Panel - Simulator */}
      <div className="absolute top-16 right-4 bottom-4 w-80 bg-black/80 backdrop-blur border border-purple-900/50 rounded flex flex-col overflow-hidden z-10 pointer-events-auto">
        <div className="overflow-y-auto flex-1">
          <MissileTrajectory 
            onSimulationComplete={(res) => {
              // Convert simulation points to Globe3D tracks
              const simTracks = res.points.map((p, i) => ({
                label: `sim_pt_${i}`,
                lat: p.lat,
                lon: p.lon,
                is_missile: true,
                is_threat: true,
                color: "#A855F7",
                altitude: p.altitude_km * 1000,
                heading: 0,
                flight_progress_pct: (i / res.points.length) * 100
              }));
              
              setSimPoints(simTracks);
            }} 
          />
        </div>
      </div>
    </div>
  );
}
