import { useEffect, useState } from "react";
import { Clock, ShieldAlert, Crosshair, Map, Activity } from "lucide-react";

type MissileEvent = {
  event_id: string;
  launch_time: string;
  origin_country: string;
  target_country: string;
  missile_type: string;
  status: string;
  headline: string;
  validation_status: string;
};

type MissileStats = {
  total_events: number;
  verified_events: number;
  total_missile_specs: number;
  total_defense_systems: number;
  events_by_status: Record<string, number>;
};

export default function MissilePanel() {
  const [liveTracks, setLiveTracks] = useState<MissileEvent[]>([]);
  const [stats, setStats] = useState<MissileStats | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [liveRes, statsRes] = await Promise.all([
          fetch('http://localhost:8000/api/v1/missile/live-tracks'),
          fetch('http://localhost:8000/api/v1/missile/stats')
        ]);
        if (liveRes.ok) setLiveTracks(await liveRes.json());
        if (statsRes.ok) setStats(await statsRes.json());
      } catch (e) {
        console.error("Failed to fetch missile intel", e);
      }
    };
    fetchStats();
    const t = setInterval(fetchStats, 10000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex flex-col gap-4 p-4 text-white">
      <div className="flex items-center gap-2 border-b border-gray-800 pb-2">
        <Activity className="w-5 h-5 text-red-500" />
        <h2 className="text-sm font-bold tracking-widest text-red-500">MISSILE INTELLIGENCE</h2>
      </div>

      {stats && (
        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
          <div className="bg-gray-900/50 p-2 border border-gray-800 rounded flex flex-col">
            <span className="text-gray-500">Total Specs</span>
            <span className="text-[#00D4FF] text-sm">{stats.total_missile_specs}</span>
          </div>
          <div className="bg-gray-900/50 p-2 border border-gray-800 rounded flex flex-col">
            <span className="text-gray-500">Defense Systems</span>
            <span className="text-[#00D4FF] text-sm">{stats.total_defense_systems}</span>
          </div>
          <div className="bg-gray-900/50 p-2 border border-gray-800 rounded flex flex-col">
            <span className="text-gray-500">Tracked Events</span>
            <span className="text-[#00D4FF] text-sm">{stats.total_events}</span>
          </div>
          <div className="bg-gray-900/50 p-2 border border-gray-800 rounded flex flex-col">
            <span className="text-gray-500">Verified Events</span>
            <span className="text-[#22C55E] text-sm">{stats.verified_events}</span>
          </div>
        </div>
      )}

      <div>
        <h3 className="text-xs font-bold text-gray-400 mb-2 flex items-center gap-1">
          <ShieldAlert className="w-3 h-3 text-red-400" /> LIVE TRACKS ({liveTracks.length})
        </h3>
        {liveTracks.length === 0 ? (
          <div className="text-[10px] text-gray-600 font-mono italic">No active missile events.</div>
        ) : (
          <div className="flex flex-col gap-2">
            {liveTracks.map(t => (
              <div key={t.event_id} className="bg-red-950/30 border border-red-900/50 p-2 rounded text-[10px] font-mono">
                <div className="flex justify-between text-red-400 mb-1">
                  <span>{t.origin_country} → {t.target_country}</span>
                  <span className="uppercase">{t.status}</span>
                </div>
                <div className="text-white font-sans text-[11px] mb-1">{t.headline}</div>
                <div className="flex justify-between text-gray-500">
                  <span>{t.missile_type || 'Unknown Type'}</span>
                  <span>{new Date(t.launch_time).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
