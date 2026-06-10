// NEWS2 (National Early Warning Score 2, Royal College of Physicians 2017) and
// qSOFA (Sepsis-3, JAMA 2016). Safety-critical, deterministic, fully unit-tested.

export interface NEWS2Input {
  rr: number | null;
  spo2: number | null;
  on_oxygen: boolean;
  sbp: number | null;
  hr: number | null;
  temp: number | null;
  // Consciousness: true if anything other than Alert (new confusion / V / P / U).
  altered_consciousness: boolean;
}

export interface NEWS2Result {
  score: number;
  band: "low" | "low-medium" | "medium" | "high";
  /** A single parameter scoring 3 raises clinical concern even at a low aggregate. */
  red_score: boolean;
  components: Record<string, number>;
  /** NEWS2 is only valid as a complete 7-parameter set; partial sets are advisory. */
  complete: boolean;
  parameters_scored: number;
}

function scoreRR(rr: number): number {
  if (rr <= 8) return 3;
  if (rr <= 11) return 1;
  if (rr <= 20) return 0;
  if (rr <= 24) return 2;
  return 3;
}

// NEWS2 SpO2 Scale 1 (default — not the hypercapnic Scale 2).
function scoreSpO2(spo2: number): number {
  if (spo2 >= 96) return 0;
  if (spo2 >= 94) return 1;
  if (spo2 >= 92) return 2;
  return 3;
}

function scoreSBP(sbp: number): number {
  if (sbp <= 90) return 3;
  if (sbp <= 100) return 2;
  if (sbp <= 110) return 1;
  if (sbp <= 219) return 0;
  return 3;
}

function scoreHR(hr: number): number {
  if (hr <= 40) return 3;
  if (hr <= 50) return 1;
  if (hr <= 90) return 0;
  if (hr <= 110) return 1;
  if (hr <= 130) return 2;
  return 3;
}

function scoreTemp(temp: number): number {
  if (temp <= 35.0) return 3;
  if (temp <= 36.0) return 1;
  if (temp <= 38.0) return 0;
  if (temp <= 39.0) return 1;
  return 2;
}

export function news2(input: NEWS2Input): NEWS2Result {
  const components: Record<string, number> = {};
  if (input.rr != null) components.rr = scoreRR(input.rr);
  if (input.spo2 != null) components.spo2 = scoreSpO2(input.spo2);
  components.oxygen = input.on_oxygen ? 2 : 0;
  if (input.sbp != null) components.sbp = scoreSBP(input.sbp);
  if (input.hr != null) components.hr = scoreHR(input.hr);
  if (input.temp != null) components.temp = scoreTemp(input.temp);
  components.consciousness = input.altered_consciousness ? 3 : 0;

  const score = Object.values(components).reduce((a, b) => a + b, 0);
  const red_score = Object.values(components).some((c) => c === 3);

  let band: NEWS2Result["band"];
  if (score >= 7) band = "high";
  else if (score >= 5) band = "medium";
  else if (red_score) band = "low-medium"; // single red parameter
  else band = "low";

  // The 7 NEWS2 parameters: rr, spo2, oxygen, sbp, hr, temp, consciousness.
  // oxygen + consciousness are always present (boolean), so count the 5 measured vitals.
  const measured = ["rr", "spo2", "sbp", "hr", "temp"].filter((k) => k in components).length;
  const parameters_scored = measured + 2;
  const complete = measured === 5;

  return { score, band, red_score, components, complete, parameters_scored };
}

export interface QSOFAInput {
  rr: number | null;
  sbp: number | null;
  altered_mentation: boolean;
}

export interface QSOFAResult {
  score: number;
  sepsis_alert: boolean;
  components: { rr: number; sbp: number; mentation: number };
}

// qSOFA: RR>=22, SBP<=100, altered mentation — each 1 point. >=2 => high risk.
export function qsofa(input: QSOFAInput): QSOFAResult {
  const components = {
    rr: input.rr != null && input.rr >= 22 ? 1 : 0,
    sbp: input.sbp != null && input.sbp <= 100 ? 1 : 0,
    mentation: input.altered_mentation ? 1 : 0,
  };
  const score = components.rr + components.sbp + components.mentation;
  return { score, sepsis_alert: score >= 2, components };
}

// Map an aggregate NEWS2 score to a monitoring-board colour (spec §8.1).
export function news2Colour(score: number): "green" | "amber" | "red" | "darkred" {
  if (score >= 9) return "darkred";
  if (score >= 7) return "red";
  if (score >= 5) return "amber";
  return "green";
}
