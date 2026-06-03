import React, { useMemo } from 'react';
import DeckGL from '@deck.gl/react';
import { _GlobeView as GlobeView } from '@deck.gl/core';
import { GeoJsonLayer, ArcLayer, ScatterplotLayer } from '@deck.gl/layers';
import { TileLayer } from '@deck.gl/geo-layers';
import { BitmapLayer } from '@deck.gl/layers';

type Track = {
  lat: number; lon: number; label?: string; color?: string;
  domain?: string; classification?: string; velocity?: number;
  is_threat?: boolean; heading?: number; is_missile?: boolean;
  origin_lat?: number; origin_lon?: number;
  target_lat?: number; target_lon?: number;
};

interface Globe3DProps {
  tracks: Track[];
}

const INITIAL_VIEW_STATE = {
  longitude: 0,
  latitude: 20,
  zoom: 1,
  minZoom: 0,
  maxZoom: 20,
  pitch: 0,
  bearing: 0
};

export default function Globe3D({ tracks }: Globe3DProps) {
  const layers = useMemo(() => {
    return [
      // Base Map Tile Layer (using a dark theme)
      new TileLayer({
        id: 'base-map',
        data: 'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        minZoom: 0,
        maxZoom: 19,
        tileSize: 256,
        renderSubLayers: (props: any) => {
          const { bbox: { west, south, east, north } } = props.tile;
          return new BitmapLayer(props, {
            data: [] as any, 
            image: props.data,
            bounds: [west, south, east, north]
          });
        }
      }),

      // Tracks (Points)
      new ScatterplotLayer({
        id: 'tracks-layer',
        data: tracks,
        getPosition: (d: Track) => [d.lon, d.lat],
        getFillColor: (d: Track) => {
          const color = d.color || '#00D4FF';
          const r = parseInt(color.slice(1, 3), 16);
          const g = parseInt(color.slice(3, 5), 16);
          const b = parseInt(color.slice(5, 7), 16);
          return [r, g, b, 255];
        },
        getRadius: (d: Track) => d.is_threat ? 50000 : 30000,
        pickable: true,
      }),

      // Missile/Flight Arcs
      new ArcLayer({
        id: 'arcs-layer',
        data: tracks.filter(t => t.origin_lat && t.target_lat),
        getSourcePosition: (d: Track) => [d.origin_lon || 0, d.origin_lat || 0],
        getTargetPosition: (d: Track) => [d.target_lon || 0, d.target_lat || 0],
        getSourceColor: [255, 0, 0, 120],
        getTargetColor: [0, 212, 255, 200],
        getWidth: 3,
      })
    ];
  }, [tracks]);

  return (
    <div className="w-full h-full bg-[#050B14]">
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={layers}
        views={new GlobeView()}
      />
      <div className="absolute bottom-4 left-4 z-[100] pointer-events-none">
        <div className="text-[10px] font-bold text-[#00D4FF] bg-[#0A0E1A]/80 px-2 py-1 border border-[#1E3A5F]">
          3D GLOBAL SITUATIONAL AWARENESS ACTIVE
        </div>
      </div>
    </div>
  );
}
