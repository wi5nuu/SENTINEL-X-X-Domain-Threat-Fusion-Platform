import { useEffect, useRef } from "react";

type Track = { lat: number; lon: number; label?: string; color?: string };

export default function GlobalMap({ tracks = [] }: { tracks?: Track[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;

    ctx.fillStyle = "#0A0E1A";
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = "rgba(0,212,255,0.08)";
    ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    for (const t of tracks) {
      const x = ((t.lon + 180) / 360) * w;
      const y = ((90 - t.lat) / 180) * h;

      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fillStyle = t.color || "#00D4FF";
      ctx.fill();

      if (t.label) {
        ctx.fillStyle = "#00D4FF";
        ctx.font = "9px monospace";
        ctx.fillText(t.label, x + 5, y + 3);
      }
    }
  }, [tracks]);

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={500}
      className="w-full h-full rounded"
    />
  );
}
