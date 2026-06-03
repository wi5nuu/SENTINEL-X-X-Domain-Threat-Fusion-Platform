import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import Globe3D from "./Globe3D";

type Track = {
  lat: number; lon: number; label?: string;
  is_missile?: boolean;
  threat_status?: "PREDICTED" | "CONFIRMED";
  origin_lat?: number; origin_lon?: number; origin_name?: string;
  target_lat?: number; target_lon?: number; target_name?: string;
  flight_progress_pct?: number; // 0 to 100
  speed_mach?: number; heading?: number;
  missile_type?: string; missile_id?: string;
  domain?: string; classification?: string;
  launch_time?: string;
};

const STRATEGIC_BASES = [
  { name: "Natuna", lat: 3.9036, lon: 108.3886, country: "ID" },
  { name: "Guam", lat: 13.4443, lon: 144.7937, country: "US" },
  { name: "Norfolk", lat: 36.8911, lon: -76.2922, country: "US" },
  { name: "Sevastopol", lat: 44.6167, lon: 33.525, country: "RU" },
  { name: "Ramstein", lat: 49.4447, lon: 7.5889, country: "DE" },
  { name: "Yulin", lat: 18.2167, lon: 109.5167, country: "CN" },
];

const ICON_SVG = (color: string, size = 10, label = "") => L.divIcon({
  className: "",
  html: `<div style="width:${size}px;height:${size}px;background:${color};border:1px solid white;display:flex;align-items:center;justify-content:center;color:white;font-size:7px;font-weight:bold;border-radius:50%">${label}</div>`,
  iconSize: [size, size],
  iconAnchor: [size/2, size/2],
});

const ICONS = {
  military: ICON_SVG("#FF0000", 12, "⚔"),
  warship: ICON_SVG("#22C55E", 12, "⚓"),
  missile: ICON_SVG("#FF3300", 14, "M"),
  uav: ICON_SVG("#F59E0B", 10, "🛸"),
  base: ICON_SVG("#FF4444", 10, "★"),
};

function getIcon(t: Track): L.DivIcon {
  if (t.is_missile) return ICONS.missile;
  if (t.classification === "uav") return ICONS.uav;
  if (t.classification === "military") {
    return t.domain === "maritime" ? ICONS.warship : ICONS.military;
  }
  return ICON_SVG("#00D4FF", 8);
}

export default function GlobalMap({ tracks = [], center, zoom, entityFilter = "all" }: any) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerLayer = useRef<L.LayerGroup | null>(null);
  const trajectoryLayer = useRef<L.LayerGroup | null>(null);
  const [is3D, setIs3D] = useState(false);

  useEffect(() => {
    if (mapRef.current && center) {
        mapRef.current.flyTo(center, zoom || 6, { duration: 1.5 });
    }
  }, [center, zoom]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    
    const map = L.map(containerRef.current, { center: [20, 0], zoom: 3, attributionControl: false, worldCopyJump: true });
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png").addTo(map);
    
    mapRef.current = map;
    markerLayer.current = L.layerGroup().addTo(map);
    trajectoryLayer.current = L.layerGroup().addTo(map);

    return () => { map.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    if (!markerLayer.current || !trajectoryLayer.current) return;
    
    markerLayer.current.clearLayers();
    trajectoryLayer.current.clearLayers();

    if (entityFilter === "all" || entityFilter === "bases") {
      STRATEGIC_BASES.forEach(b => {
        L.circleMarker([b.lat, b.lon], { radius: 5, color: "red", fillColor: "red", fillOpacity: 1 })
         .bindPopup(`<b>${b.name}</b>`).addTo(markerLayer.current!);
      });
    }

    tracks.forEach((t: Track) => {
      // Trajectory Rendering for ALL tracks with origin/target
      if (t.origin_lat && t.target_lat) {
        let color = t.threat_status === "CONFIRMED" ? "red" : (t.missile_type === "Hypersonic" || t.missile_type === "ICBM" ? "purple" : "gold");

        // 1. Line
        L.polyline([[t.origin_lat, t.origin_lon!], [t.target_lat, t.target_lon!]], {
          color: color,
          weight: 2,
        }).addTo(trajectoryLayer.current!)
          .bindPopup(`
            <div style="font-family:monospace;font-size:10px">
              <b>${t.missile_id || "ASSET"}</b><br/>
              Type: ${t.missile_type || "N/A"}<br/>
              Status: ${t.threat_status || "ACTIVE"}<br/>
              Speed: ${(t.speed_mach! * 1235).toFixed(0)} km/h
            </div>
          `);

        // 2. Missile Icon + Telemetry Label
        const progress = (t.flight_progress_pct || 0) / 100;
        const curLat = t.origin_lat + (t.target_lat - t.origin_lat) * progress;
        const curLon = t.origin_lon! + (t.target_lon! - t.origin_lon!) * progress;
        
        const dy = t.target_lat - t.origin_lat;
        const dx = (t.target_lon! - t.origin_lon!) * Math.cos(t.origin_lat * Math.PI / 180);
        const heading = (Math.atan2(dy, dx) * 180 / Math.PI) - 90;
        
        const missileIcon = L.divIcon({
          className: "",
          html: `<div style="display:flex; flex-direction:column; align-items:center;">
                   <div style="transform:rotate(${heading}deg);">
                     <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                       <path d="M12 2L14 8V20L12 22L10 20V8L12 2Z"/>
                     </svg>
                   </div>
                   <div style="font-family:monospace; font-size:9px; background:rgba(0,0,0,0.8); color:white; padding:2px; border:1px solid ${color}; border-radius:3px; white-space:nowrap; font-style: normal; margin-top:2px;">
                     ${t.missile_id || "MSL"}<br/>
                     ${(t.speed_mach! * 1235).toFixed(0)} km/h
                   </div>
                 </div>`
        });
        L.marker([curLat, curLon], { icon: missileIcon }).addTo(trajectoryLayer.current!);
      }
      
      // Marker
      if (entityFilter !== "bases") {
        if (entityFilter === "warships" && (t.domain !== "maritime" || t.classification !== "military")) return;
        L.circleMarker([t.lat, t.lon], { radius: 3, color: "cyan" }).addTo(markerLayer.current!);
      }
    });
  }, [tracks, entityFilter]);

  return (
    <div className="w-full h-full relative">
      {!is3D ? <div ref={containerRef} className="w-full h-full" /> : <Globe3D tracks={tracks} />}
      <button className="absolute top-2 right-2 z-[1000] p-2 bg-black text-white text-[10px]" onClick={() => setIs3D(!is3D)}>{is3D ? "3D" : "2D"}</button>
    </div>
  );
}
