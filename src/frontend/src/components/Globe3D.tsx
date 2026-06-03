import React, { useMemo, useEffect, useRef } from 'react';
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
};

/* ─── Global Military Bases Dataset ─────────────────────────────── */
type MilitaryBase = {
  name: string; country: string; lat: number; lon: number;
  type: 'nuclear' | 'naval' | 'airforce' | 'army' | 'icbm' | 'missile';
  weapons: string; size: number;
};

const MILITARY_BASES: MilitaryBase[] = [
  // === USA ===
  { name: 'Offutt AFB (STRATCOM)', country: 'USA', lat: 41.12, lon: -95.91, type: 'nuclear', weapons: 'B-2 Spirit, Minuteman III ICBM', size: 1.2 },
  { name: 'Malmstrom AFB', country: 'USA', lat: 47.51, lon: -111.18, type: 'icbm', weapons: '150× Minuteman III ICBM', size: 1.1 },
  { name: 'Warren AFB', country: 'USA', lat: 41.14, lon: -104.86, type: 'icbm', weapons: '150× Minuteman III ICBM', size: 1.1 },
  { name: 'Minot AFB', country: 'USA', lat: 48.42, lon: -101.36, type: 'icbm', weapons: '150× Minuteman III, B-52H', size: 1.1 },
  { name: 'Norfolk Naval Station', country: 'USA', lat: 36.94, lon: -76.31, type: 'naval', weapons: 'CVN-77 George H.W. Bush, Aegis Cruisers', size: 1.3 },
  { name: 'Pearl Harbor-Hickam', country: 'USA', lat: 21.35, lon: -157.97, type: 'naval', weapons: 'CVN-74 John C. Stennis, SSN Subs', size: 1.2 },
  { name: 'Langley AFB', country: 'USA', lat: 37.08, lon: -76.36, type: 'airforce', weapons: 'F-22 Raptor, F-35A', size: 1.0 },
  { name: 'Nellis AFB', country: 'USA', lat: 36.24, lon: -115.03, type: 'airforce', weapons: 'F-35A, F-16, A-10, B-2', size: 1.0 },
  { name: 'Guam (Andersen AFB)', country: 'USA', lat: 13.58, lon: 144.93, type: 'airforce', weapons: 'B-52H, B-1B Lancer, F-15', size: 1.1 },
  { name: 'Diego Garcia', country: 'USA/UK', lat: -7.31, lon: 72.41, type: 'naval', weapons: 'B-2, B-52, Tomahawk, SSBN', size: 1.2 },
  { name: 'Ramstein AB (Germany)', country: 'USA', lat: 49.44, lon: 7.60, type: 'airforce', weapons: 'F-35A, C-17, Nuclear B61 bombs', size: 1.0 },
  { name: 'Fort Liberty (Bragg)', country: 'USA', lat: 35.14, lon: -78.99, type: 'army', weapons: 'M1A2 Abrams, M109 Paladin, Delta Force', size: 1.0 },
  { name: 'Camp Humphreys', country: 'USA', lat: 36.96, lon: 127.03, type: 'army', weapons: 'THAAD, Patriot PAC-3, Apache', size: 1.1 },
  { name: 'Kadena AB (Japan)', country: 'USA', lat: 26.36, lon: 127.77, type: 'airforce', weapons: 'F-15C/D, RC-135, P-8 Poseidon', size: 1.1 },

  // === RUSSIA ===
  { name: 'Plesetsk Cosmodrome', country: 'RUS', lat: 62.96, lon: 40.69, type: 'icbm', weapons: 'RS-28 Sarmat, Angara Rocket', size: 1.3 },
  { name: 'Dombarovsky (60th Missile Army)', country: 'RUS', lat: 50.73, lon: 59.51, type: 'icbm', weapons: 'RS-18 Stiletto, RS-20 Voevoda', size: 1.2 },
  { name: 'Kozelsk (13th Missile Division)', country: 'RUS', lat: 54.04, lon: 35.78, type: 'icbm', weapons: 'RS-12M2 Topol-M', size: 1.1 },
  { name: 'Severomorsk (Northern Fleet HQ)', country: 'RUS', lat: 69.07, lon: 33.42, type: 'naval', weapons: 'Admiral Kuznetsov CVN, Oscar-II SSGN, Typhoon SSBN', size: 1.3 },
  { name: 'Vladivostok (Pacific Fleet)', country: 'RUS', lat: 43.11, lon: 131.88, type: 'naval', weapons: 'Slava-class cruiser, Kilo-class submarines', size: 1.1 },
  { name: 'Khmeimim AB (Syria)', country: 'RUS', lat: 35.40, lon: 35.95, type: 'airforce', weapons: 'Su-57, Su-35S, Tu-22M3, S-400', size: 1.2 },
  { name: 'Mozdok AB', country: 'RUS', lat: 43.78, lon: 44.60, type: 'airforce', weapons: 'Tu-95MS Bear, Tu-160 Blackjack', size: 1.1 },
  { name: 'Engels-2 AB', country: 'RUS', lat: 51.43, lon: 46.28, type: 'nuclear', weapons: 'Tu-160M2 Blackjack, Tu-95MS ALCM', size: 1.2 },
  { name: 'Armavir Radar (EW)', country: 'RUS', lat: 44.97, lon: 41.12, type: 'missile', weapons: 'Voronezh-DM BMEWS Radar', size: 0.9 },

  // === CHINA ===
  { name: 'Jilantai ICBM Base', country: 'CHN', lat: 39.38, lon: 105.72, type: 'icbm', weapons: 'DF-5B, DF-41 ICBM (300+ silos)', size: 1.3 },
  { name: 'Yumen ICBM Silo Field', country: 'CHN', lat: 40.13, lon: 97.36, type: 'icbm', weapons: 'DF-41 Mobile ICBM', size: 1.3 },
  { name: 'Hainan Island Naval Base', country: 'CHN', lat: 18.23, lon: 109.56, type: 'naval', weapons: 'Type 055 Destroyer, Type 094 SSBN, DF-21D ASBM', size: 1.3 },
  { name: 'Yulin Naval Base (SSN)', country: 'CHN', lat: 18.16, lon: 109.53, type: 'naval', weapons: 'Jin-class SSBN (JL-3 SLBM), Shang-class SSN', size: 1.2 },
  { name: 'Djibouti Naval Base', country: 'CHN', lat: 11.55, lon: 43.15, type: 'naval', weapons: 'Type 052D Destroyer, PLAN Marines', size: 1.0 },
  { name: 'Lhasa (Tibet) AB', country: 'CHN', lat: 29.69, lon: 91.13, type: 'airforce', weapons: 'J-20 Stealth, J-16, H-6K Bomber', size: 1.1 },
  { name: 'Subi Reef (SCS)', country: 'CHN', lat: 10.93, lon: 114.08, type: 'missile', weapons: 'YJ-12B ASBM, HQ-9 SAM, J-10', size: 1.1 },
  { name: 'Mischief Reef (SCS)', country: 'CHN', lat: 9.91, lon: 115.54, type: 'missile', weapons: 'YJ-12B, HQ-9, Radar Arrays', size: 1.0 },
  { name: 'Fiery Cross Reef (SCS)', country: 'CHN', lat: 9.55, lon: 112.89, type: 'airforce', weapons: 'J-11, J-10C, H-6 Bomber', size: 1.1 },

  // === NORTH KOREA ===
  { name: 'Sohae Launch Site', country: 'PRK', lat: 39.66, lon: 124.70, type: 'icbm', weapons: 'Hwasong-17 ICBM, Paektusan-1 rocket', size: 1.2 },
  { name: 'Punggye-ri Nuclear Test Site', country: 'PRK', lat: 41.27, lon: 129.08, type: 'nuclear', weapons: 'Underground Nuclear Test Facility', size: 1.1 },
  { name: 'Yangdok Missile Base', country: 'PRK', lat: 39.25, lon: 126.63, type: 'missile', weapons: 'Hwasong-15, KN-23 SRBM', size: 1.0 },
  { name: 'Sinpo Naval Base', country: 'PRK', lat: 40.02, lon: 128.19, type: 'naval', weapons: 'Gorae-class SSBS (SLBM-capable)', size: 1.0 },

  // === INDIA ===
  { name: 'Kalaikunda AB (Su-30MKI)', country: 'IND', lat: 22.35, lon: 87.20, type: 'airforce', weapons: 'Su-30MKI, Brahmos cruise missile', size: 1.0 },
  { name: 'INS Kadamba (Karwar)', country: 'IND', lat: 14.80, lon: 74.07, type: 'naval', weapons: 'INS Vikrant CVN, Arihant SSBN (K-15)', size: 1.2 },
  { name: 'Wheeler Island (APJ Abdul Kalam)', country: 'IND', lat: 20.74, lon: 87.09, type: 'missile', weapons: 'Agni-V ICBM, K-4 SLBM', size: 1.1 },

  // === PAKISTAN ===
  { name: 'Sargodha Air Base', country: 'PAK', lat: 32.05, lon: 72.67, type: 'nuclear', weapons: 'F-16, Shaheen-III MRBM (nuclear-capable)', size: 1.0 },
  { name: 'Masroor AB (Karachi)', country: 'PAK', lat: 24.90, lon: 66.94, type: 'airforce', weapons: 'F-16C/D Block 52, JF-17 Thunder', size: 1.0 },

  // === UK ===
  { name: 'Faslane (HMNB Clyde)', country: 'GBR', lat: 56.06, lon: -4.82, type: 'naval', weapons: 'Vanguard SSBN (Trident II D5), Astute SSN', size: 1.2 },
  { name: 'RAF Marham', country: 'GBR', lat: 52.65, lon: 0.55, type: 'airforce', weapons: 'F-35B Lightning II, Typhoon', size: 1.0 },

  // === FRANCE ===
  { name: 'Île Longue (MSBS)', country: 'FRA', lat: 48.31, lon: -4.42, type: 'nuclear', weapons: 'Le Triomphant SSBN (M51 SLBM)', size: 1.2 },
  { name: 'Saint-Dizier AB', country: 'FRA', lat: 48.64, lon: 5.00, type: 'nuclear', weapons: 'Rafale F3R (ASMP-A nuclear missile)', size: 1.0 },

  // === ISRAEL ===
  { name: 'Sdot Micha (Jericho)', country: 'ISR', lat: 31.73, lon: 34.87, type: 'icbm', weapons: 'Jericho III ICBM (assumed nuclear)', size: 1.1 },
  { name: 'Nevatim AB', country: 'ISR', lat: 31.20, lon: 35.01, type: 'airforce', weapons: 'F-35I Adir, F-15I Ra\'am', size: 1.0 },

  // === IRAN ===
  { name: 'Imam Ali Missile Base', country: 'IRN', lat: 34.05, lon: 48.35, type: 'missile', weapons: 'Shahab-3, Sejjil-2 MRBM (2000km)', size: 1.1 },
  { name: 'Shahrud Space Center', country: 'IRN', lat: 36.20, lon: 57.00, type: 'missile', weapons: 'Qadr MRBM, Safir/Simorgh rockets', size: 1.0 },

  // === SAUDI ARABIA ===
  { name: 'Prince Sultan AB', country: 'SAU', lat: 24.06, lon: 47.58, type: 'airforce', weapons: 'F-15SA Eagle, Typhoon, Patriot PAC-3', size: 1.0 },
  { name: 'Al-Watah MRBM Base', country: 'SAU', lat: 21.88, lon: 46.08, type: 'missile', weapons: 'DF-3A, DF-21 MRBM (from China)', size: 1.0 },

  // === TURKEY ===
  { name: 'Incirlik AB', country: 'TUR', lat: 37.00, lon: 35.43, type: 'nuclear', weapons: 'B61-12 Nuclear bombs (NATO share), F-16', size: 1.1 },

  // === JAPAN ===
  { name: 'JASDF Chitose AB', country: 'JPN', lat: 42.79, lon: 141.67, type: 'airforce', weapons: 'F-35A, F-15J, E-767 AWACS', size: 1.0 },
  { name: 'JMSDF Yokosuka', country: 'JPN', lat: 35.28, lon: 139.66, type: 'naval', weapons: 'JS Izumo (F-35B capable CVL), Aegis DDG', size: 1.1 },

  // === SOUTH KOREA ===
  { name: 'Osan AB', country: 'KOR', lat: 37.09, lon: 127.03, type: 'airforce', weapons: 'F-35A, A-10, THAAD', size: 1.0 },
  { name: 'ROKN Jinhae Naval Base', country: 'KOR', lat: 35.14, lon: 128.64, type: 'naval', weapons: 'KSS-III SSBN (Hyunmoo-4 SLBM), Sejong DDG', size: 1.1 },

  // === NATO ===
  { name: 'Kleine Brogel AB (Belgium)', country: 'NATO', lat: 51.17, lon: 5.47, type: 'nuclear', weapons: 'B61-12 nuclear bombs (NATO), F-16AM', size: 0.9 },
  { name: 'Aviano AB (Italy)', country: 'NATO', lat: 46.03, lon: 12.60, type: 'nuclear', weapons: 'B61-12 nuclear bombs (NATO), F-16', size: 0.9 },
  { name: 'Büchel AB (Germany)', country: 'NATO', lat: 50.17, lon: 7.07, type: 'nuclear', weapons: 'B61-12 nuclear bombs (NATO), Tornado IDS', size: 0.9 },
];

interface Globe3DProps {
  tracks: Track[];
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
export default function Globe3D({ tracks }: Globe3DProps) {
  const basesData = useMemo(() => MILITARY_BASES, []);

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
        getPosition: (d: Track) => [d.lon, d.lat],
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
    ];
  }, [tracks, basesData]);

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
        </div>
      </div>
    </div>
  );
}
