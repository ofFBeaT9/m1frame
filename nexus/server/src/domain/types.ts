// Core domain types — mirror Section 17 data architecture so the in-memory
// store can be swapped for Supabase/Postgres without touching domain logic.

export type Role =
  | "admin"
  | "physician"
  | "resident"
  | "np_pa"
  | "nurse"
  | "med_tech"
  | "pharmacist"
  | "physio"
  | "nutritionist"
  | "social_worker"
  | "patient";

export type PatientCategory =
  | "neonatal"
  | "infant"
  | "pediatric"
  | "adult"
  | "geriatric";

export interface User {
  id: string;
  email: string;
  role: Role;
  full_name: string;
  unit_id: string | null;
  is_active: boolean;
  mfa_enabled: boolean;
  password: string; // demo only — bcrypt in production (spec §1.4 BCRYPT_ROUNDS)
  created_at: string;
}

export interface Allergy {
  allergen: string;
  reaction: string;
  severity: "mild" | "moderate" | "severe" | "life-threatening";
  verification: "reported" | "confirmed" | "refuted";
}

export interface Patient {
  id: string;
  mrn: string;
  full_name: string;
  dob: string; // ISO date
  sex: "male" | "female" | "intersex";
  category: PatientCategory;
  blood_type: string;
  allergies: Allergy[];
  advance_directives: { dnr?: string; organ_donor?: boolean };
  primary_diagnosis: string;
  created_at: string;
  updated_at: string;
}

export interface Encounter {
  id: string;
  patient_id: string;
  admitting_physician_id: string;
  unit_id: string;
  bed_id: string | null;
  admission_type: "elective" | "emergency" | "transfer-in" | "observation";
  admitting_diagnosis_icd10: string | null;
  admitting_diagnosis_icd11: string | null;
  triage_score: number | null;
  triage_system: "ESI" | "MTS" | null;
  admitted_at: string;
  discharged_at: string | null;
  discharge_disposition: string | null;
  care_team_ids: string[];
}

export interface Vitals {
  id: string;
  patient_id: string;
  encounter_id: string;
  entered_by_id: string;
  device_source: "manual" | "device";
  hr: number | null;
  hr_rhythm: "regular" | "irregular" | "paced" | null;
  bp_sys: number | null;
  bp_dia: number | null;
  map: number | null;
  rr: number | null;
  spo2: number | null;
  o2_delivery: string | null; // "room air" | "FiO2 X" | "L/min ..."
  on_oxygen: boolean;
  temp: number | null; // Celsius
  glucose: number | null;
  pain_score: number | null;
  loc_avpu: "A" | "V" | "P" | "U" | null;
  urine_output_ml: number | null;
  consciousness_new_confusion: boolean;
  news2_score: number;
  news2_band: "low" | "low-medium" | "medium" | "high";
  qsofa_score: number;
  sepsis_alert_triggered: boolean;
  recorded_at: string;
  created_at: string;
}

export type AlertType =
  | "critical_lab"
  | "vital_threshold"
  | "sepsis_qsofa"
  | "ai_deterioration"
  | "medication_interaction"
  | "stale_vitals"
  | "overdue_handover"
  | "code_blue_active";

export interface Alert {
  id: string;
  patient_id: string;
  alert_type: AlertType;
  severity: "info" | "warning" | "critical";
  message: string;
  trigger_value: string | null;
  created_at: string;
  acknowledged_by_id: string | null;
  acknowledged_at: string | null;
  escalated_at: string | null;
}

export interface AuditEntry {
  id: string;
  user_id: string | null;
  role: Role | null;
  action_type: string;
  resource_type: string;
  resource_id: string | null;
  patient_id: string | null;
  changes: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  timestamp: string;
  code_blue_override: boolean;
  override_reason: string | null;
}

export interface CodeBlueSession {
  id: string;
  user_id: string;
  patient_id: string;
  reason_code: string;
  reason_text: string;
  accessed_sections: string[];
  start_time: string;
  expires_at: string;
  end_time: string | null;
}

export interface Protocol {
  id: string;
  title: string;
  category: string;
  version: string;
  status: "active" | "draft" | "retired";
  content_html: string;
  last_reviewed_at: string;
  approved_by_id: string | null;
  is_custom: boolean;
  created_at: string;
  updated_at: string;
}

export interface Unit {
  id: string;
  name: string;
  type: string;
  bed_count: number;
  charge_nurse_id: string | null;
  ai_refresh_interval_min: number;
}

export interface CalculatorResult {
  id: string;
  patient_id: string | null;
  user_id: string;
  calculator_name: string;
  inputs: Record<string, unknown>;
  result_value: string;
  result_interpretation: string;
  clinical_note: string;
  created_at: string;
}
