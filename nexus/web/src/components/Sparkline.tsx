// Signature design element (spec §16.4): a miniature heartbeat-style NEWS2
// sparkline. Flat at rest; pulses gently only when a new reading arrives.
import { useEffect, useState } from "react";

export function Sparkline({ data, colour = "#2DD4BF" }: { data: number[]; colour?: string }) {
  const [beat, setBeat] = useState(false);
  const last = data[data.length - 1];

  useEffect(() => {
    setBeat(true);
    const t = setTimeout(() => setBeat(false), 3200);
    return () => clearTimeout(t);
  }, [last, data.length]);

  if (data.length === 0) {
    return <div className="h-8 w-full text-text-muted text-[11px] flex items-center">no data</div>;
  }
  const w = 120;
  const h = 32;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const span = max - min || 1;
  const pts = data
    .map((v, i) => {
      const x = (i / Math.max(data.length - 1, 1)) * w;
      const y = h - ((v - min) / span) * (h - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={`w-full h-8 ${beat ? "heartbeat" : ""}`} aria-label="NEWS2 trend">
      <polyline points={pts} fill="none" stroke={colour} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

export const NEWS2_COLOUR: Record<string, string> = {
  green: "#10B981",
  amber: "#F59E0B",
  red: "#EF4444",
  darkred: "#991B1B",
};
