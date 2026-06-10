// Age-adjusted vital-sign reference ranges (spec §3.8) and category derivation.
import type { PatientCategory } from "./types.js";

export function categoryFromDob(dob: string, now = new Date()): PatientCategory {
  const birth = new Date(dob);
  const ms = now.getTime() - birth.getTime();
  const days = ms / (1000 * 60 * 60 * 24);
  const years = days / 365.25;
  if (days <= 28) return "neonatal";
  if (years < 1) return "infant"; // 29d–1y
  if (years < 18) return "pediatric";
  if (years < 65) return "adult";
  return "geriatric";
}

export interface Range {
  low: number;
  high: number;
}

type Param = "hr" | "rr" | "sbp" | "spo2" | "temp";

const RANGES: Record<Param, Record<PatientCategory, Range>> = {
  hr: {
    neonatal: { low: 120, high: 160 },
    infant: { low: 80, high: 150 },
    pediatric: { low: 70, high: 120 },
    adult: { low: 60, high: 100 },
    geriatric: { low: 60, high: 100 },
  },
  rr: {
    neonatal: { low: 40, high: 60 },
    infant: { low: 30, high: 60 },
    pediatric: { low: 20, high: 30 },
    adult: { low: 12, high: 20 },
    geriatric: { low: 12, high: 20 },
  },
  sbp: {
    neonatal: { low: 60, high: 76 },
    infant: { low: 70, high: 90 },
    pediatric: { low: 80, high: 110 },
    adult: { low: 90, high: 120 },
    geriatric: { low: 90, high: 140 },
  },
  spo2: {
    neonatal: { low: 95, high: 100 },
    infant: { low: 95, high: 100 },
    pediatric: { low: 95, high: 100 },
    adult: { low: 95, high: 100 },
    geriatric: { low: 93, high: 100 },
  },
  temp: {
    neonatal: { low: 36.5, high: 37.5 },
    infant: { low: 36.5, high: 37.5 },
    pediatric: { low: 36.5, high: 37.5 },
    adult: { low: 36.1, high: 37.2 },
    geriatric: { low: 36.0, high: 37.0 },
  },
};

export function rangeFor(param: Param, category: PatientCategory): Range {
  return RANGES[param][category];
}

export type VitalFlag = "normal" | "warning" | "critical";

// Colour band for a single value relative to its age-adjusted range.
export function flagFor(param: Param, value: number, category: PatientCategory): VitalFlag {
  const { low, high } = rangeFor(param, category);
  const span = high - low || 1;
  if (value >= low && value <= high) return "normal";
  // > 25% of the span outside the range, or SpO2 critically low, => critical.
  const below = low - value;
  const above = value - high;
  const dev = Math.max(below, above);
  if (param === "spo2" && value < low - 3) return "critical";
  if (dev > span * 0.4) return "critical";
  return "warning";
}

// Mean arterial pressure: (2*DBP + SBP)/3  (spec §3.8).
export function meanArterialPressure(sbp: number, dbp: number): number {
  return Math.round((2 * dbp + sbp) / 3);
}
