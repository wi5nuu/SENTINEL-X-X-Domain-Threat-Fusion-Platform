import { useEffect, useRef } from "react";

const BARS = 60;
const BAR_W = 6;
const BAR_GAP = 2;

export default function AlertVolumeChart({ timestamps = [] }: { timestamps: string[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = (BAR_W + BAR_GAP) * BARS;
    const h = 40;
    canvas.width = w;
    canvas.height = h;

    ctx.clearRect(0, 0, w, h);

    const now = Date.now();
    const buckets = new Array(BARS).fill(0);

    for (const ts of timestamps) {
      const t = new Date(ts).getTime();
      const diffSec = (now - t) / 1000;
      const barIdx = Math.floor(diffSec / 60);
      if (barIdx >= 0 && barIdx < BARS) {
        buckets[BARS - 1 - barIdx]++;
      }
    }

    const maxVal = Math.max(...buckets, 1);
    for (let i = 0; i < BARS; i++) {
      const x = i * (BAR_W + BAR_GAP);
      const barH = (buckets[i] / maxVal) * (h - 4);
      const alpha = 0.3 + (buckets[i] / maxVal) * 0.7;
      ctx.fillStyle = `rgba(239, 68, 68, ${alpha})`;
      ctx.fillRect(x, h - 2 - barH, BAR_W, barH);
    }

    ctx.fillStyle = "rgba(255,255,255,0.3)";
    ctx.font = "6px monospace";
    ctx.fillText(`${Math.round(maxVal)}`, 2, 8);
    ctx.fillText("0", 2, h - 2);
    ctx.fillText("60m", w - 20, h - 2);
  }, [timestamps]);

  return (
    <div className="w-full flex items-center justify-center" style={{ minHeight: 40 }}>
      {timestamps.length === 0 ? (
        <span className="text-[8px] text-gray-600">no data</span>
      ) : (
        <canvas
          ref={canvasRef}
          width={(BAR_W + BAR_GAP) * BARS}
          height={40}
          className="rounded block"
          style={{ maxWidth: "100%" }}
        />
      )}
    </div>
  );
}