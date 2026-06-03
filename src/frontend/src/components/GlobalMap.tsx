import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import Globe3D from "./Globe3D";

type Track = {
  lat: number; lon: number; label?: string;
  is_missile?: boolean; threat_status?: "PREDICTED" | "CONFIRMED";
  origin_lat?: number; origin_lon?: number; origin_name?: string;
  target_lat?: number; target_lon?: number; target_name?: string;
  flight_progress_pct?: number; speed_mach?: number; heading?: number;
  missile_type?: string; missile_id?: string; domain?: string; classification?: string;
};

// PRECISE GLOBAL MILITARY DATASET (Representing major nations)
const GLOBAL_BASES = [
  { name: "Halim Perdanakusuma", lat: -6.26, lon: 106.88, country: "ID" },
  { name: "Pentagon", lat: 38.87, lon: -77.05, country: "US" },
  { name: "Znamensky", lat: 55.75, lon: 37.61, country: "RU" },
  { name: "Bayi Building", lat: 39.90, lon: 116.39, country: "CN" },
  { name: "Northwood HQ", lat: 51.60, lon: -0.42, country: "UK" },
  { name: "Balard", lat: 48.83, lon: 2.27, country: "FR" },
  { name: "New Delhi HQ", lat: 28.61, lon: 77.20, country: "IN" },
  { name: "Ichigaya", lat: 35.69, lon: 139.72, country: "JP" },
  { name: "Seoul HQ", lat: 37.56, lon: 126.97, country: "KR" },
  { name: "Brasilia HQ", lat: -15.79, lon: -47.88, country: "BR" },
  { name: "Cairo HQ", lat: 30.04, lon: 31.23, country: "EG" },
  { name: "Canberra HQ", lat: -35.28, lon: 149.13, country: "AU" },
  { name: "Pretoria HQ", lat: -25.74, lon: 28.18, country: "ZA" },
];

// Professional SVG Bunker Icon
const BUNKER_ICON_SVG = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FF4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22V10l8-8 8 8v12M12 22V10"/></svg>`;

const ICONS = {
  base: L.divIcon({ className: "", html: `<div style="color:red;">${BUNKER_ICON_SVG}</div>`, iconSize: [18, 18], iconAnchor: [9, 9] }),
  missile: L.divIcon({ className: "", html: `<div style="color:red; font-size:14px;">M</div>`, iconSize: [14, 14] }),
  military: L.divIcon({ className: "", html: `<div style="color:red; font-size:12px;">⚔</div>`, iconSize: [12, 12] }),
  warship: L.divIcon({ className: "", html: `<div style="color:green; font-size:12px;">⚓</div>`, iconSize: [12, 12] }),
  uav: L.divIcon({ className: "", html: `<div style="color:orange; font-size:10px;">🛸</div>`, iconSize: [10, 10] }),
};

export default function GlobalMap({ tracks = [], center, zoom, entityFilter = "all" }: any) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerLayer = useRef<L.LayerGroup | null>(null);
  const baseLayer = useRef<L.LayerGroup | null>(null);
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
    baseLayer.current = L.layerGroup().addTo(map);
    trajectoryLayer.current = L.layerGroup().addTo(map);
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    if (!markerLayer.current || !baseLayer.current || !trajectoryLayer.current) return;
    markerLayer.current.clearLayers();
    baseLayer.current.clearLayers();
    trajectoryLayer.current.clearLayers();

    // Render Accurate Bases
    if (entityFilter === "all" || entityFilter === "bases") {
      GLOBAL_BASES.forEach(b => {
        L.marker([b.lat, b.lon], { icon: ICONS.base })
         .bindPopup(`<div style="font-family:monospace;font-size:10px"><b>${b.name}</b><br/>HQ: ${b.country}</div>`)
         .addTo(baseLayer.current!);
      });
    }

    // Render Tracks
    tracks.forEach((t: Track) => {
      if (t.is_missile && t.origin_lat && t.target_lat) {
        const color = t.threat_status === "CONFIRMED" ? "red" : (t.missile_type === "Hypersonic" || t.missile_type === "ICBM" ? "purple" : "gold");
        L.polyline([[t.origin_lat, t.origin_lon!], [t.target_lat, t.target_lon!]], { color, weight: 2 }).addTo(trajectoryLayer.current!);
        
        const progress = (t.flight_progress_pct || 0) / 100;
        const curLat = t.origin_lat + (t.target_lat - t.origin_lat) * progress;
        const curLon = t.origin_lon! + (t.target_lon! - t.origin_lon!) * progress;
        const dy = t.target_lat - t.origin_lat;
        const dx = (t.target_lon! - t.origin_lon!) * Math.cos(t.origin_lat * Math.PI / 180);
        const heading = (Math.atan2(dy, dx) * 180 / Math.PI) - 90;
        
        const missileIcon = L.divIcon({
          className: "",
          html: `<div style="display:flex; flex-direction:column; align-items:center;">
                   <div style="transform:rotate(${heading}deg);"><svg width="16" height="16" viewBox="0 0 24 24" fill="white"><path d="M12 2L14 8V20L12 22L10 20V8L12 2Z"/></svg></div>
                   <div style="font-family:monospace; font-size:9px; background:rgba(0,0,0,0.8); color:white; padding:2px; border:1px solid ${color}; border-radius:3px; font-style: normal;">${t.missile_id}</div>
                 </div>`
        });
        L.marker([curLat, curLon], { icon: missileIcon }).addTo(trajectoryLayer.current!);
      }
      
      if (entityFilter !== "bases" && !(entityFilter === "warships" && t.domain !== "maritime")) {
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
