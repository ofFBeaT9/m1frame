// Vitals write path: compute NEWS2 + qSOFA, persist, and raise safety alerts
// (sepsis, critical thresholds). This is the operational heartbeat (spec §3.8).
import { db, uuid, now, raiseAlert, latestVitals } from "../db/store.js";
import { news2, qsofa } from "../domain/news2.js";
import { flagFor, meanArterialPressure } from "../domain/vitalRanges.js";
import type { Patient, Vitals } from "../domain/types.js";

export interface VitalsInput {
  hr?: number; hr_rhythm?: Vitals["hr_rhythm"];
  bp_sys?: number; bp_dia?: number;
  rr?: number; spo2?: number; on_oxygen?: boolean; o2_delivery?: string;
  temp?: number; glucose?: number; pain_score?: number;
  loc_avpu?: Vitals["loc_avpu"]; urine_output_ml?: number;
  consciousness_new_confusion?: boolean;
  recorded_at?: string;
}

export function recordVitals(
  patient: Patient,
  encounterId: string,
  enteredById: string,
  input: VitalsInput,
): { vitals: Vitals; alerts: string[] } {
  const altered =
    !!input.consciousness_new_confusion || (input.loc_avpu != null && input.loc_avpu !== "A");

  const score = news2({
    rr: input.rr ?? null,
    spo2: input.spo2 ?? null,
    on_oxygen: !!input.on_oxygen,
    sbp: input.bp_sys ?? null,
    hr: input.hr ?? null,
    temp: input.temp ?? null,
    altered_consciousness: altered,
  });

  const qs = qsofa({
    rr: input.rr ?? null,
    sbp: input.bp_sys ?? null,
    altered_mentation: altered,
  });

  const map =
    input.bp_sys != null && input.bp_dia != null
      ? meanArterialPressure(input.bp_sys, input.bp_dia)
      : null;

  const v: Vitals = {
    id: uuid(),
    patient_id: patient.id,
    encounter_id: encounterId,
    entered_by_id: enteredById,
    device_source: "manual",
    hr: input.hr ?? null,
    hr_rhythm: input.hr_rhythm ?? null,
    bp_sys: input.bp_sys ?? null,
    bp_dia: input.bp_dia ?? null,
    map,
    rr: input.rr ?? null,
    spo2: input.spo2 ?? null,
    o2_delivery: input.o2_delivery ?? null,
    on_oxygen: !!input.on_oxygen,
    temp: input.temp ?? null,
    glucose: input.glucose ?? null,
    pain_score: input.pain_score ?? null,
    loc_avpu: input.loc_avpu ?? null,
    urine_output_ml: input.urine_output_ml ?? null,
    consciousness_new_confusion: !!input.consciousness_new_confusion,
    news2_score: score.score,
    news2_band: score.band,
    qsofa_score: qs.score,
    sepsis_alert_triggered: qs.sepsis_alert,
    recorded_at: input.recorded_at ?? now(),
    created_at: now(),
  };
  db.vitals.push(v);

  const alerts: string[] = [];

  // Sepsis (qSOFA >= 2) — push to physician with one-click sepsis bundle (spec §3.8).
  if (qs.sepsis_alert) {
    raiseAlert({
      patient_id: patient.id, alert_type: "sepsis_qsofa", severity: "critical",
      message: `qSOFA ${qs.score} — evaluate for sepsis; consider Surviving Sepsis Bundle`,
      trigger_value: `qSOFA=${qs.score}`,
    });
    alerts.push("sepsis_qsofa");
  }

  // High NEWS2 -> vital threshold alert.
  if (score.band === "high") {
    raiseAlert({
      patient_id: patient.id, alert_type: "vital_threshold", severity: "critical",
      message: `NEWS2 ${score.score} (HIGH) — urgent clinical review`,
      trigger_value: `NEWS2=${score.score}`,
    });
    alerts.push("vital_threshold");
  }

  // Critical single-parameter flags (age-adjusted).
  const critParams: [string, number | null, "hr" | "rr" | "sbp" | "spo2" | "temp"][] = [
    ["HR", v.hr, "hr"], ["RR", v.rr, "rr"], ["SBP", v.bp_sys, "sbp"],
    ["SpO2", v.spo2, "spo2"], ["Temp", v.temp, "temp"],
  ];
  for (const [label, value, param] of critParams) {
    if (value != null && flagFor(param, value, patient.category) === "critical") {
      raiseAlert({
        patient_id: patient.id, alert_type: "vital_threshold", severity: "warning",
        message: `${label} ${value} outside critical range for ${patient.category}`,
        trigger_value: `${label}=${value}`,
      });
    }
  }

  return { vitals: v, alerts };
}

// Stale-vitals detection (spec §3.8). Returns "ok" | "yellow" | "red".
export function staleState(patientId: string, frequencyHours = 4, ref = Date.now()): "ok" | "yellow" | "red" {
  const last = latestVitals(patientId);
  if (!last) return "red";
  const ageHours = (ref - new Date(last.recorded_at).getTime()) / 3_600_000;
  if (ageHours > frequencyHours * 3) return "red";
  if (ageHours > frequencyHours * 2) return "yellow";
  return "ok";
}
