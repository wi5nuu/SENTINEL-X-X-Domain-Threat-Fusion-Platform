import React, { useMemo, useEffect, useRef, useState, useCallback } from 'react';
import DeckGL from '@deck.gl/react';
import { _GlobeView as GlobeView } from '@deck.gl/core';
import { ArcLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import { TileLayer } from '@deck.gl/geo-layers';
import { BitmapLayer } from '@deck.gl/layers';

type Track = {
  lat: number; lon: number; label?: string; color?: string;
  domain?: string; classification?: string; velocity?: number;
  is_threat?: boolean; heading?: number; is_missile?: boolean;
  origin_lat?: number; origin_lon?: number;
  target_lat?: number; target_lon?: number;
  altitude?: number;
};

/** A full pre-computed trajectory for a live animated missile */
export type MissileTrail = {
  id: string;
  name: string;
  missile_type: string;          // 'ballistic' | 'cruise' | 'HGV' etc.
  color: [number, number, number];
  /** Array of [lon, lat, alt_km] waypoints from launch to impact */
  waypoints: [number, number, number][];
  total_duration_s: number;      // total flight time in seconds
  launched_at: number;           // Date.now() timestamp of simulated launch
};

/* ─── Global Military Bases Dataset ─────────────────────────────── */
type MilitaryBase = {
  name: string; country: string; lat: number; lon: number;
  type: 'nuclear' | 'naval' | 'airforce' | 'army' | 'icbm' | 'missile';
  weapons: string; size: number;
};

// Military bases are now fetched dynamically from the backend API.

interface Globe3DProps {
  tracks: Track[];
  missileTrails?: MissileTrail[];
}

const INITIAL_VIEW_STATE = {
  longitude: 20,
  latitude: 25,
  zoom: 1,
  minZoom: 0.5,
  maxZoom: 20,
  pitch: 0,
  bearing: 0,
};

/* ─── Color map for base types ───────────────────────────────────── */
const BASE_COLORS: Record<string, [number, number, number, number]> = {
  nuclear:  [220, 20,  20,  240],
  icbm:     [255, 80,  0,   240],
  missile:  [255, 165, 0,   220],
  naval:    [0,   150, 255, 220],
  airforce: [0,   210, 255, 210],
  army:     [50,  200, 100, 210],
};

/* ─── Animated Starfield Canvas ──────────────────────────────────── */
function SpaceBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = canvas.offsetWidth * (window.devicePixelRatio || 1);
      canvas.height = canvas.offsetHeight * (window.devicePixelRatio || 1);
      canvas.style.width = canvas.offsetWidth + 'px';
      canvas.style.height = canvas.offsetHeight + 'px';
      ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const W = () => canvas.offsetWidth;
    const H = () => canvas.offsetHeight;

    /* Stars */
    const STAR_COUNT = 700;
    const stars = Array.from({ length: STAR_COUNT }, () => ({
      x: Math.random(), y: Math.random(),
      r: Math.random() * 1.6 + 0.2,
      phase: Math.random() * Math.PI * 2,
      speed: Math.random() * 0.018 + 0.004,
      color: (() => {
        const r = Math.random();
        if (r < 0.12) return '#b3d9ff';
        if (r < 0.20) return '#ffe8b3';
        if (r < 0.26) return '#ffb3b3';
        return '#ffffff';
      })(),
    }));

    /* Shooting stars */
    type SS = { x: number; y: number; vx: number; vy: number; life: number; maxLife: number; };
    let shooting: SS[] = [];

    /* Nebulas */
    const nebulas = [
      { cx: 0.10, cy: 0.18, rx: 0.28, ry: 0.20, color: '40,10,100',  a: 0.45 },
      { cx: 0.82, cy: 0.12, rx: 0.22, ry: 0.18, color: '10,30,100',  a: 0.40 },
      { cx: 0.60, cy: 0.80, rx: 0.24, ry: 0.16, color: '0,70,50',    a: 0.32 },
      { cx: 0.92, cy: 0.68, rx: 0.18, ry: 0.22, color: '80,10,60',   a: 0.28 },
      { cx: 0.28, cy: 0.88, rx: 0.22, ry: 0.14, color: '30,20,100',  a: 0.30 },
      { cx: 0.50, cy: 0.40, rx: 0.35, ry: 0.25, color: '20,10,60',   a: 0.20 },
    ];

    let frame = 0;

    const draw = () => {
      const w = W(), h = H();
      ctx.clearRect(0, 0, w, h);

      /* Deep space bg — no visible seam, full coverage */
      ctx.fillStyle = '#010308';
      ctx.fillRect(0, 0, w, h);

      /* Radial depth gradient */
      const bgGrad = ctx.createRadialGradient(w * 0.5, h * 0.4, 0, w * 0.5, h * 0.5, Math.max(w, h) * 0.75);
      bgGrad.addColorStop(0, 'rgba(8,14,40,0.9)');
      bgGrad.addColorStop(0.6, 'rgba(3,6,18,0.8)');
      bgGrad.addColorStop(1, 'rgba(1,2,8,0.95)');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      /* Milky Way diagonal band */
      for (let i = 0; i < 3; i++) {
        const mw = ctx.createLinearGradient(w * (-0.1 + i * 0.3), 0, w * (0.4 + i * 0.3), h);
        mw.addColorStop(0, 'rgba(100,120,220,0)');
        mw.addColorStop(0.45, `rgba(90,110,210,${0.05 - i * 0.01})`);
        mw.addColorStop(0.55, `rgba(110,130,230,${0.09 - i * 0.015})`);
        mw.addColorStop(1, 'rgba(100,120,220,0)');
        ctx.fillStyle = mw;
        ctx.fillRect(0, 0, w, h);
      }

      /* Nebulas */
      nebulas.forEach(n => {
        const grd = ctx.createRadialGradient(n.cx * w, n.cy * h, 0, n.cx * w, n.cy * h, n.rx * w);
        grd.addColorStop(0, `rgba(${n.color},${n.a})`);
        grd.addColorStop(0.5, `rgba(${n.color},${n.a * 0.4})`);
        grd.addColorStop(1, `rgba(${n.color},0)`);
        ctx.fillStyle = grd;
        ctx.beginPath();
        ctx.ellipse(n.cx * w, n.cy * h, n.rx * w, n.ry * h, 0.4, 0, Math.PI * 2);
        ctx.fill();
      });

      /* Stars */
      frame++;
      stars.forEach(s => {
        s.phase += s.speed;
        const alpha = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(s.phase));
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.beginPath();
        ctx.arc(s.x * w, s.y * h, s.r, 0, Math.PI * 2);
        ctx.fillStyle = s.color;
        if (s.r > 1.0) { ctx.shadowBlur = 5; ctx.shadowColor = s.color; }
        ctx.fill();
        ctx.restore();
      });

      /* Shooting stars */
      if (frame % 100 === 0 && shooting.length < 4) {
        shooting.push({
          x: Math.random() * 0.9 * w,
          y: Math.random() * 0.5 * h,
          vx: (Math.random() * 8 + 5) * (Math.random() < 0.5 ? 1 : -1),
          vy: Math.random() * 4 + 2,
          life: 0,
          maxLife: Math.random() * 50 + 35,
        });
      }
      shooting = shooting.filter(ss => ss.life < ss.maxLife);
      shooting.forEach(ss => {
        ss.life++;
        const prog = ss.life / ss.maxLife;
        const alpha = prog < 0.3 ? prog / 0.3 : Math.max(0, 1 - (prog - 0.3) / 0.7);
        const len = 100 + Math.random() * 40;
        const nx = ss.vx / Math.hypot(ss.vx, ss.vy);
        const ny = ss.vy / Math.hypot(ss.vx, ss.vy);
        const g = ctx.createLinearGradient(ss.x - nx * len, ss.y - ny * len, ss.x, ss.y);
        g.addColorStop(0, 'rgba(200,230,255,0)');
        g.addColorStop(1, `rgba(220,240,255,${alpha * 0.95})`);
        ctx.save();
        ctx.strokeStyle = g;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(ss.x - nx * len, ss.y - ny * len);
        ctx.lineTo(ss.x, ss.y);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(ss.x, ss.y, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(220,240,255,${alpha})`;
        ctx.shadowBlur = 14;
        ctx.shadowColor = '#aadeff';
        ctx.fill();
        ctx.restore();
        ss.x += ss.vx;
        ss.y += ss.vy;
      });

      /* Aurora sweep at bottom */
      const ap = 0.18 + 0.10 * Math.sin(frame * 0.007);
      const aurora = ctx.createLinearGradient(0, h * 0.75, 0, h);
      aurora.addColorStop(0, `rgba(0,255,180,${ap * 0.3})`);
      aurora.addColorStop(0.4, `rgba(0,180,255,${ap * 0.18})`);
      aurora.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = aurora;
      ctx.fillRect(0, h * 0.75, w, h * 0.25);

      animRef.current = requestAnimationFrame(draw);
    };
    animRef.current = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(animRef.current); ro.disconnect(); };
  }, []);

  return (
    <canvas ref={canvasRef} style={{
      position: 'absolute', inset: 0,
      width: '100%', height: '100%',
      display: 'block', zIndex: 0,
    }} />
  );
}

/* ─── Main Globe3D ───────────────────────────────────────────────── */
export default function Globe3D({ tracks, missileTrails = [] }: Globe3DProps) {
  const [basesData, setBasesData] = useState<MilitaryBase[]>([]);

  useEffect(() => {
    const fetchBases = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/v1/missile/military-bases");
        if (res.ok) {
          const data = await res.json();
          setBasesData(data.bases || []);
        }
      } catch (err) {
        console.error("Failed to fetch military bases:", err);
      }
    };
    fetchBases();
  }, []);

  // ── Animated missile trail state ──────────────────────────────────
  // Each entry: { id, trailPts: [lon,lat,alt][], headPt: [lon,lat,alt], color }
  type AnimState = {
    id: string;
    color: [number, number, number];
    trail: { position: [number, number, number]; alpha: number }[];
    head: [number, number, number] | null;
    done: boolean;
  };
  const [animStates, setAnimStates] = useState<AnimState[]>([]);

  // Tick: advance every 150ms
  useEffect(() => {
    if (missileTrails.length === 0) { setAnimStates([]); return; }

    const TRAIL_LEN = 20; // how many historical waypoints to keep as "tail"

    const tick = () => {
      const now = Date.now();
      setAnimStates(missileTrails.map(mt => {
        const elapsed_s = (now - mt.launched_at) / 1000;
        const progress = Math.min(1.0, elapsed_s / mt.total_duration_s);
        const wpts = mt.waypoints;
        if (wpts.length === 0) return { id: mt.id, color: mt.color, trail: [], head: null, done: true };

        const headIdx = Math.min(wpts.length - 1, Math.floor(progress * (wpts.length - 1)));
        const head = wpts[headIdx];

        // Build fading trail from [headIdx-TRAIL_LEN .. headIdx]
        const trailStart = Math.max(0, headIdx - TRAIL_LEN);
        const trail = wpts.slice(trailStart, headIdx + 1).map((pt, i, arr) => ({
          position: pt as [number, number, number],
          alpha: Math.round(255 * ((i + 1) / arr.length) * 0.85),
        }));

        return { id: mt.id, color: mt.color, trail, head, done: progress >= 1.0 };
      }));
    };

    tick();
    const interval = setInterval(tick, 150);
    return () => clearInterval(interval);
  }, [missileTrails]);

  // Flatten trail points and head points for DeckGL layers
  const trailPoints = useMemo(() => animStates.flatMap(s =>
    s.trail.map(p => ({ position: p.position, color: s.color, alpha: p.alpha }))
  ), [animStates]);

  const headPoints = useMemo(() => animStates
    .filter(s => s.head && !s.done)
    .map(s => ({ position: s.head!, color: s.color })),
  [animStates]);

  const layers = useMemo(() => {
    return [
      /* Dark basemap tile */
      new TileLayer({
        id: 'base-map',
        data: 'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        minZoom: 0, maxZoom: 19, tileSize: 256,
        renderSubLayers: (props: any) => {
          const { bbox: { west, south, east, north } } = props.tile;
          return new BitmapLayer(props, {
            data: [] as any,
            image: props.data,
            bounds: [west, south, east, north],
          });
        },
      }),

      /* Military bases — outer glow ring */
      new ScatterplotLayer({
        id: 'bases-glow',
        data: basesData,
        getPosition: (d: MilitaryBase) => [d.lon, d.lat],
        getFillColor: (d: MilitaryBase) => {
          const c = BASE_COLORS[d.type];
          return [c[0], c[1], c[2], 40];
        },
        getRadius: (d: MilitaryBase) => d.size * 280000,
        pickable: false,
      }),

      /* Military bases — core dot */
      new ScatterplotLayer({
        id: 'bases-core',
        data: basesData,
        getPosition: (d: MilitaryBase) => [d.lon, d.lat],
        getFillColor: (d: MilitaryBase) => BASE_COLORS[d.type],
        getLineColor: [255, 255, 255, 180],
        lineWidthMinPixels: 1,
        stroked: true,
        getRadius: (d: MilitaryBase) => d.size * 120000,
        radiusMinPixels: 4,
        radiusMaxPixels: 14,
        pickable: true,
        autoHighlight: true,
        highlightColor: [255, 255, 255, 180],
        onClick: (info: any) => {
          if (info.object) {
            const b: MilitaryBase = info.object;
            alert(`${b.name}\n${b.country} — ${b.type.toUpperCase()}\n\nWeapons: ${b.weapons}`);
          }
        },
      }),

      /* Live tracks — scatter */
      new ScatterplotLayer({
        id: 'tracks-layer',
        data: tracks,
        getPosition: (d: Track) => [d.lon, d.lat, d.altitude || 0],
        getFillColor: (d: Track) => {
          const hex = d.color || '#00D4FF';
          return [parseInt(hex.slice(1,3),16), parseInt(hex.slice(3,5),16), parseInt(hex.slice(5,7),16), d.is_threat ? 255 : 200];
        },
        getRadius: (d: Track) => d.is_threat ? 90000 : 45000,
        radiusMinPixels: 3,
        radiusMaxPixels: 18,
        pickable: true,
      }),

      /* Missile arcs */
      new ArcLayer({
        id: 'arcs-layer',
        data: tracks.filter(t => t.origin_lat && t.target_lat),
        getSourcePosition: (d: Track) => [d.origin_lon || 0, d.origin_lat || 0],
        getTargetPosition: (d: Track) => [d.target_lon || 0, d.target_lat || 0],
        getSourceColor: [255, 60, 60, 200],
        getTargetColor: [0, 212, 255, 240],
        getWidth: 2.5,
        greatCircle: true,
      }),
      /* Missile trail — fading segments */
      new ScatterplotLayer({
        id: 'missile-trail',
        data: trailPoints,
        getPosition: (d: any) => d.position,
        getFillColor: (d: any) => [d.color[0], d.color[1], d.color[2], d.alpha],
        getRadius: 35000,
        radiusMinPixels: 1.5,
        radiusMaxPixels: 5,
        pickable: false,
        parameters: { depthTest: false },
      }),

      /* Missile head — bright pulsing dot */
      new ScatterplotLayer({
        id: 'missile-heads',
        data: headPoints,
        getPosition: (d: any) => d.position,
        getFillColor: (d: any) => [d.color[0], d.color[1], d.color[2], 255],
        getLineColor: [255, 255, 255, 200],
        stroked: true,
        lineWidthMinPixels: 1,
        getRadius: 100000,
        radiusMinPixels: 5,
        radiusMaxPixels: 16,
        pickable: false,
        parameters: { depthTest: false },
      }),
    ];
  }, [tracks, basesData, trailPoints, headPoints]);

  const activeBases = basesData.length;
  const nuclearCount = basesData.filter(b => b.type === 'nuclear' || b.type === 'icbm').length;

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', overflow: 'hidden', background: '#010308' }}>
      {/* Animated space canvas — seamless full-cover */}
      <SpaceBackground />

      {/* DeckGL Globe — transparent background */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 1 }}>
        <DeckGL
          initialViewState={INITIAL_VIEW_STATE}
          controller={true}
          layers={layers}
          views={new GlobeView()}
          onWebGLInitialized={(gl: WebGLRenderingContext) => { gl.clearColor(0, 0, 0, 0); }}
          style={{ background: 'transparent' }}
        />
      </div>

      {/* Corner accent glows */}
      <div style={{ position:'absolute', top:0, right:0, width:250, height:250,
        background:'radial-gradient(circle at top right, rgba(100,50,220,0.22), transparent 70%)',
        zIndex:2, pointerEvents:'none' }} />
      <div style={{ position:'absolute', bottom:0, left:0, width:320, height:200,
        background:'radial-gradient(circle at bottom left, rgba(0,180,255,0.15), transparent 70%)',
        zIndex:2, pointerEvents:'none' }} />

      {/* HUD: Legend */}
      <div style={{ position:'absolute', top:14, right:14, zIndex:10, pointerEvents:'none',
        display:'flex', flexDirection:'column', gap:5,
        background:'rgba(1,3,12,0.80)', backdropFilter:'blur(10px)',
        border:'1px solid rgba(0,212,255,0.2)', borderRadius:10, padding:'12px 16px' }}>
        <div style={{ fontSize:9, fontWeight:800, color:'#4DA3FF', letterSpacing:'0.18em', marginBottom:4 }}>MILITARY INSTALLATIONS</div>
        {Object.entries(BASE_COLORS).map(([type, color]) => (
          <div key={type} style={{ display:'flex', alignItems:'center', gap:7 }}>
            <div style={{ width:8, height:8, borderRadius:'50%',
              background:`rgb(${color[0]},${color[1]},${color[2]})`,
              boxShadow:`0 0 6px rgb(${color[0]},${color[1]},${color[2]})` }} />
            <span style={{ fontSize:9, color:'rgba(180,210,255,0.8)', fontFamily:"'JetBrains Mono', monospace",
              textTransform:'uppercase', letterSpacing:'0.1em' }}>{type}</span>
          </div>
        ))}
      </div>

      {/* HUD: Bottom bar */}
      <div style={{ position:'absolute', bottom:14, left:14, zIndex:10,
        pointerEvents:'none', display:'flex', flexDirection:'column', gap:6 }}>
        <div style={{ fontSize:10, fontWeight:800, letterSpacing:'0.18em',
          color:'#00D4FF', fontFamily:"'JetBrains Mono', monospace",
          background:'rgba(0,10,24,0.80)', backdropFilter:'blur(8px)',
          padding:'6px 14px', border:'1px solid rgba(0,212,255,0.3)',
          borderRadius:6, boxShadow:'0 0 16px rgba(0,212,255,0.25)',
          textShadow:'0 0 8px #00D4FF' }}>
          3D GLOBAL SITUATIONAL AWARENESS  ·  LIVE
        </div>
        <div style={{ display:'flex', gap:12, fontSize:9, color:'rgba(160,200,255,0.7)',
          fontFamily:"'JetBrains Mono', monospace", padding:'0 2px', letterSpacing:'0.1em' }}>
          <span>{tracks.length} LIVE TRACKS</span>
          <span style={{ color:'rgba(255,255,255,0.2)' }}>|</span>
          <span style={{ color:'rgba(255,120,120,0.9)' }}>{nuclearCount} NUCLEAR SITES</span>
          <span style={{ color:'rgba(255,255,255,0.2)' }}>|</span>
          <span>{activeBases} MILITARY INSTALLATIONS</span>
          {missileTrails.length > 0 && (
            <>
              <span style={{ color:'rgba(255,255,255,0.2)' }}>|</span>
              <span style={{ color:'rgba(255,80,80,1)', animation:'pulse 1s infinite' }}>
                🚀 {missileTrails.length} MISSILE{missileTrails.length > 1 ? 'S' : ''} IN FLIGHT
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
