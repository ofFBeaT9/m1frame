// Medical calculator suite (spec §4). A generic engine + a library of real,
// cited calculators. Each calculator declares its inputs, computes a value, and
// returns an interpretation band + citation + population tag.

import { news2 as validatedNews2, qsofa as validatedQsofa } from "./news2.js";

export type Population = "pediatric" | "adult" | "geriatric" | "all";

export interface CalcField {
  key: string;
  label: string;
  type: "number" | "select" | "boolean";
  unit?: string;
  options?: { value: string; label: string }[];
}

export interface CalcOutput {
  value: string;
  interpretation: string;
  band: "normal" | "low" | "moderate" | "high" | "critical" | "info";
}

export interface Calculator {
  id: string;
  name: string;
  category: string;
  population: Population;
  citation: string;
  fields: CalcField[];
  compute: (i: Record<string, number | string | boolean>) => CalcOutput;
}

const n = (v: unknown): number => Number(v);
// Null-safe numeric: returns null for missing / non-finite inputs so validated
// scorers can apply their own null guards instead of scoring a coerced NaN.
const num = (v: unknown): number | null => {
  if (v === undefined || v === null || v === "") return null;
  const x = Number(v);
  return Number.isFinite(x) ? x : null;
};

export const CALCULATORS: Calculator[] = [
  {
    id: "news2",
    name: "NEWS2",
    category: "Critical Care & Scoring",
    population: "adult",
    citation: "Royal College of Physicians, NEWS2 (2017)",
    fields: [
      { key: "rr", label: "Respiratory rate", type: "number", unit: "br/min" },
      { key: "spo2", label: "SpO₂", type: "number", unit: "%" },
      { key: "on_oxygen", label: "On supplemental oxygen", type: "boolean" },
      { key: "sbp", label: "Systolic BP", type: "number", unit: "mmHg" },
      { key: "hr", label: "Heart rate", type: "number", unit: "bpm" },
      { key: "temp", label: "Temperature", type: "number", unit: "°C" },
      { key: "altered", label: "Altered consciousness (not Alert)", type: "boolean" },
    ],
    compute: (i) => {
      // Single source of truth: delegate to the validated news2() — preserves the
      // single-red-parameter (low-medium) escalation band and null-input guards.
      const r = validatedNews2({
        rr: num(i.rr), spo2: num(i.spo2), on_oxygen: !!i.on_oxygen,
        sbp: num(i.sbp), hr: num(i.hr), temp: num(i.temp), altered_consciousness: !!i.altered,
      });
      const band: CalcOutput["band"] =
        r.band === "high" ? "high" : r.band === "medium" ? "moderate"
        : r.band === "low-medium" ? "moderate" : r.score >= 1 ? "low" : "normal";
      const action =
        r.band === "high" ? "Urgent/emergency clinical review; consider critical care"
        : r.band === "medium" ? "Urgent review by clinician; min hourly obs"
        : r.red_score ? "Single red parameter — review by registered nurse, escalate if concerned"
        : r.score >= 1 ? "Routine monitoring per protocol"
        : "Continue routine 12-hourly monitoring";
      return { value: String(r.score), interpretation: action, band };
    },
  },
  {
    id: "qsofa",
    name: "qSOFA",
    category: "Critical Care & Scoring",
    population: "all",
    citation: "Sepsis-3, JAMA 2016;315(8):801-810",
    fields: [
      { key: "rr", label: "Respiratory rate", type: "number", unit: "br/min" },
      { key: "sbp", label: "Systolic BP", type: "number", unit: "mmHg" },
      { key: "altered", label: "Altered mentation (GCS<15)", type: "boolean" },
    ],
    compute: (i) => {
      const r = validatedQsofa({ rr: num(i.rr), sbp: num(i.sbp), altered_mentation: !!i.altered });
      return {
        value: String(r.score),
        interpretation: r.sepsis_alert ? "High risk of poor outcome — evaluate for sepsis, escalate" : "Lower risk — continue assessment",
        band: r.sepsis_alert ? "high" : "normal",
      };
    },
  },
  {
    id: "gcs",
    name: "Glasgow Coma Scale",
    category: "Critical Care & Scoring",
    population: "all",
    citation: "Teasdale & Jennett, Lancet 1974",
    fields: [
      { key: "eye", label: "Eye opening (1–4)", type: "number" },
      { key: "verbal", label: "Verbal response (1–5)", type: "number" },
      { key: "motor", label: "Motor response (1–6)", type: "number" },
    ],
    compute: (i) => {
      const s = n(i.eye) + n(i.verbal) + n(i.motor);
      const band = s <= 8 ? "critical" : s <= 12 ? "moderate" : "normal";
      const sev = s <= 8 ? "Severe brain injury — secure airway (consider intubation)"
        : s <= 12 ? "Moderate brain injury" : "Minor brain injury";
      return { value: `${s}/15`, interpretation: sev, band };
    },
  },
  {
    id: "map",
    name: "Mean Arterial Pressure",
    category: "Cardiology",
    population: "all",
    citation: "MAP = (2·DBP + SBP)/3",
    fields: [
      { key: "sbp", label: "Systolic BP", type: "number", unit: "mmHg" },
      { key: "dbp", label: "Diastolic BP", type: "number", unit: "mmHg" },
    ],
    compute: (i) => {
      const map = Math.round((2 * n(i.dbp) + n(i.sbp)) / 3);
      return {
        value: `${map} mmHg`,
        interpretation: map < 65 ? "Below 65 mmHg — organ perfusion at risk" : "Adequate perfusion pressure",
        band: map < 65 ? "critical" : "normal",
      };
    },
  },
  {
    id: "shock_index",
    name: "Shock Index",
    category: "Critical Care & Scoring",
    population: "all",
    citation: "Allgöwer & Burri, 1967 (HR/SBP)",
    fields: [
      { key: "hr", label: "Heart rate", type: "number", unit: "bpm" },
      { key: "sbp", label: "Systolic BP", type: "number", unit: "mmHg" },
    ],
    compute: (i) => {
      const si = n(i.hr) / n(i.sbp);
      return {
        value: si.toFixed(2),
        interpretation: si >= 1.0 ? "Elevated (≥1.0) — occult shock, haemodynamic instability" : "Normal (0.5–0.7 typical)",
        band: si >= 1.0 ? "high" : "normal",
      };
    },
  },
  {
    id: "cockcroft_gault",
    name: "Cockcroft-Gault CrCl",
    category: "Nephrology",
    population: "adult",
    citation: "Cockcroft & Gault, Nephron 1976",
    fields: [
      { key: "age", label: "Age", type: "number", unit: "years" },
      { key: "weight", label: "Weight", type: "number", unit: "kg" },
      { key: "creatinine", label: "Serum creatinine", type: "number", unit: "mg/dL" },
      { key: "sex", label: "Sex", type: "select", options: [{ value: "male", label: "Male" }, { value: "female", label: "Female" }] },
    ],
    compute: (i) => {
      let crcl = ((140 - n(i.age)) * n(i.weight)) / (72 * n(i.creatinine));
      if (i.sex === "female") crcl *= 0.85;
      const v = Math.round(crcl);
      const band = v < 30 ? "high" : v < 60 ? "moderate" : "normal";
      return { value: `${v} mL/min`, interpretation: v < 30 ? "Severe impairment — renal dose-adjust" : v < 60 ? "Moderate impairment — review dosing" : "Adequate clearance", band };
    },
  },
  {
    id: "ckd_epi",
    name: "CKD-EPI 2021 eGFR",
    category: "Nephrology",
    population: "adult",
    citation: "Inker et al, NEJM 2021 (race-free)",
    fields: [
      { key: "age", label: "Age", type: "number", unit: "years" },
      { key: "creatinine", label: "Serum creatinine", type: "number", unit: "mg/dL" },
      { key: "sex", label: "Sex", type: "select", options: [{ value: "male", label: "Male" }, { value: "female", label: "Female" }] },
    ],
    compute: (i) => {
      const female = i.sex === "female";
      const k = female ? 0.7 : 0.9;
      const a = female ? -0.241 : -0.302;
      const scr = n(i.creatinine);
      const egfr = 142 * Math.pow(Math.min(scr / k, 1), a) * Math.pow(Math.max(scr / k, 1), -1.2) * Math.pow(0.9938, n(i.age)) * (female ? 1.012 : 1);
      const v = Math.round(egfr);
      const stage = v >= 90 ? "G1" : v >= 60 ? "G2" : v >= 45 ? "G3a" : v >= 30 ? "G3b" : v >= 15 ? "G4" : "G5";
      return { value: `${v} mL/min/1.73m²`, interpretation: `KDIGO stage ${stage}`, band: v < 30 ? "high" : v < 60 ? "moderate" : "normal" };
    },
  },
  {
    id: "bmi",
    name: "BMI (WHO)",
    category: "Nutrition",
    population: "adult",
    citation: "WHO classification",
    fields: [
      { key: "weight", label: "Weight", type: "number", unit: "kg" },
      { key: "height", label: "Height", type: "number", unit: "cm" },
    ],
    compute: (i) => {
      const h = n(i.height) / 100;
      const bmi = n(i.weight) / (h * h);
      const cls = bmi < 18.5 ? "Underweight" : bmi < 25 ? "Normal weight" : bmi < 30 ? "Overweight" : "Obese";
      return { value: bmi.toFixed(1), interpretation: cls, band: bmi < 18.5 || bmi >= 30 ? "moderate" : "normal" };
    },
  },
  {
    id: "parkland",
    name: "Parkland Formula (burns)",
    category: "Fluids & Electrolytes",
    population: "all",
    citation: "Baxter & Shires, 1968",
    fields: [
      { key: "weight", label: "Weight", type: "number", unit: "kg" },
      { key: "tbsa", label: "TBSA burned", type: "number", unit: "%" },
    ],
    compute: (i) => {
      const total = 4 * n(i.weight) * n(i.tbsa);
      const first8 = Math.round(total / 2);
      return {
        value: `${Math.round(total)} mL / 24h`,
        interpretation: `Lactated Ringer's: ${first8} mL over first 8h, remainder over next 16h. Titrate to urine output 0.5 mL/kg/h.`,
        band: "info",
      };
    },
  },
  {
    id: "anion_gap",
    name: "Anion Gap",
    category: "Fluids & Electrolytes",
    population: "all",
    citation: "AG = Na − (Cl + HCO₃)",
    fields: [
      { key: "na", label: "Sodium", type: "number", unit: "mmol/L" },
      { key: "cl", label: "Chloride", type: "number", unit: "mmol/L" },
      { key: "hco3", label: "Bicarbonate", type: "number", unit: "mmol/L" },
    ],
    compute: (i) => {
      const ag = n(i.na) - (n(i.cl) + n(i.hco3));
      return { value: String(ag), interpretation: ag > 12 ? "High anion gap metabolic acidosis (MUDPILES)" : "Normal anion gap", band: ag > 12 ? "high" : "normal" };
    },
  },
  {
    id: "corrected_calcium",
    name: "Calcium Correction (albumin)",
    category: "Endocrinology & Metabolic",
    population: "all",
    citation: "Corrected Ca = Ca + 0.8·(4.0 − albumin g/dL)",
    fields: [
      { key: "calcium", label: "Measured calcium", type: "number", unit: "mg/dL" },
      { key: "albumin", label: "Albumin", type: "number", unit: "g/dL" },
    ],
    compute: (i) => {
      const cc = n(i.calcium) + 0.8 * (4.0 - n(i.albumin));
      return { value: `${cc.toFixed(1)} mg/dL`, interpretation: cc < 8.5 ? "Hypocalcaemia (corrected)" : cc > 10.5 ? "Hypercalcaemia (corrected)" : "Normal corrected calcium", band: cc < 8.5 || cc > 10.5 ? "moderate" : "normal" };
    },
  },
  {
    id: "chads_vasc",
    name: "CHA₂DS₂-VASc",
    category: "Cardiology",
    population: "adult",
    citation: "Lip et al, Chest 2010",
    fields: [
      { key: "chf", label: "Congestive heart failure", type: "boolean" },
      { key: "htn", label: "Hypertension", type: "boolean" },
      { key: "age", label: "Age", type: "number", unit: "years" },
      { key: "diabetes", label: "Diabetes", type: "boolean" },
      { key: "stroke", label: "Prior stroke/TIA/thromboembolism", type: "boolean" },
      { key: "vascular", label: "Vascular disease", type: "boolean" },
      { key: "female", label: "Female sex", type: "boolean" },
    ],
    compute: (i) => {
      let s = 0;
      let nonSexPoints = 0;
      const add = (cond: boolean, pts: number) => { if (cond) { s += pts; nonSexPoints += pts; } };
      add(!!i.chf, 1);
      add(!!i.htn, 1);
      const age = n(i.age);
      add(age >= 75, 2);
      add(age >= 65 && age < 75, 1);
      add(!!i.diabetes, 1);
      add(!!i.stroke, 2);
      add(!!i.vascular, 1);
      if (i.female) s += 1; // counted in total but NOT in nonSexPoints
      // A woman whose only point is female sex is LOW risk (ESC/AHA): do not over-treat.
      const risk =
        nonSexPoints === 0
          ? "Low — anticoagulation not recommended (sex point alone does not warrant it)"
          : nonSexPoints === 1
          ? "Consider anticoagulation (clinical judgement)"
          : "Anticoagulation recommended";
      const band: CalcOutput["band"] = nonSexPoints >= 2 ? "high" : nonSexPoints === 1 ? "moderate" : "normal";
      return { value: String(s), interpretation: risk, band };
    },
  },
  {
    id: "wells_pe",
    name: "Wells Score (PE)",
    category: "Pulmonology",
    population: "adult",
    citation: "Wells et al, Thromb Haemost 2000",
    fields: [
      { key: "dvt_signs", label: "Clinical signs of DVT", type: "boolean" },
      { key: "pe_likely", label: "PE most likely diagnosis", type: "boolean" },
      { key: "hr100", label: "Heart rate > 100", type: "boolean" },
      { key: "immobilization", label: "Immobilization/surgery (4 wks)", type: "boolean" },
      { key: "prior_vte", label: "Previous DVT/PE", type: "boolean" },
      { key: "hemoptysis", label: "Haemoptysis", type: "boolean" },
      { key: "malignancy", label: "Malignancy", type: "boolean" },
    ],
    compute: (i) => {
      let s = 0;
      if (i.dvt_signs) s += 3;
      if (i.pe_likely) s += 3;
      if (i.hr100) s += 1.5;
      if (i.immobilization) s += 1.5;
      if (i.prior_vte) s += 1.5;
      if (i.hemoptysis) s += 1;
      if (i.malignancy) s += 1;
      // Wells three-tier model (Wells 2000): <2 low, 2–6 moderate, >6 high.
      const band = s > 6 ? "high" : s >= 2 ? "moderate" : "low";
      const interp =
        s > 6 ? "High probability — proceed to CTPA (D-dimer not sufficient to exclude)"
        : s >= 2 ? "Moderate probability — age-adjusted D-dimer; CTPA if positive"
        : "Low probability — age-adjusted D-dimer to exclude";
      return { value: String(s), interpretation: interp, band };
    },
  },
];

export function getCalculator(id: string): Calculator | undefined {
  return CALCULATORS.find((c) => c.id === id);
}

export function calculatorIndex() {
  return CALCULATORS.map(({ id, name, category, population, citation }) => ({ id, name, category, population, citation }));
}
