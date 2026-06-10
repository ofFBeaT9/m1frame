// In-memory data layer mirroring spec §17. This is the "RLS" choke-point:
// authorize() is the single data-layer gate. Reimplementing this interface
// against Supabase/Postgres is the only change needed to go hosted.
import { randomUUID } from "node:crypto";
import type {
  User, Patient, Encounter, Vitals, Alert, AuditEntry, CodeBlueSession,
  Protocol, Unit, CalculatorResult, Role,
} from "../domain/types.js";
import { ROLE_PRIVILEGE } from "../domain/rbac.js";

export interface Tables {
  users: User[];
  patients: Patient[];
  encounters: Encounter[];
  vitals: Vitals[];
  alerts: Alert[];
  audit_log: AuditEntry[];
  code_blue_sessions: CodeBlueSession[];
  protocols: Protocol[];
  units: Unit[];
  calculator_results: CalculatorResult[];
}

export const db: Tables = {
  users: [], patients: [], encounters: [], vitals: [], alerts: [],
  audit_log: [], code_blue_sessions: [], protocols: [], units: [],
  calculator_results: [],
};

// Demo linkage: patient-role user -> Patient record (own-records access).
export const patientUserLinks: Record<string, string> = {};

export function reset() {
  (Object.keys(db) as (keyof Tables)[]).forEach((k) => (db[k].length = 0));
  for (const k of Object.keys(patientUserLinks)) delete patientUserLinks[k];
}

export const uuid = () => randomUUID();
export const now = () => new Date().toISOString();

// --- Care team / assignment -------------------------------------------------
export function isOnCareTeam(userId: string, patientId: string): boolean {
  return db.encounters.some(
    (e) => e.patient_id === patientId && e.discharged_at === null && e.care_team_ids.includes(userId),
  );
}

export function activeCodeBlue(userId: string, patientId: string): CodeBlueSession | undefined {
  const t = Date.now();
  return db.code_blue_sessions.find(
    (s) => s.user_id === userId && s.patient_id === patientId && s.end_time === null && new Date(s.expires_at).getTime() > t,
  );
}

// --- The RLS choke-point ----------------------------------------------------
// Returns whether `user` may access `patientId`'s chart, and via what path.
export function authorizePatientAccess(
  user: { id: string; role: Role },
  patientId: string,
): { allowed: boolean; via: "role" | "care_team" | "code_blue" | "own" | "denied" } {
  // Full-clinical roles see any chart.
  if (["admin", "physician", "resident", "np_pa"].includes(user.role)) {
    return { allowed: true, via: "role" };
  }
  // Patient can read only their own record.
  if (user.role === "patient") {
    return patientUserLinks[user.id] === patientId
      ? { allowed: true, via: "own" }
      : { allowed: false, via: "denied" };
  }
  // Scoped roles (nurse etc.) require care-team assignment...
  if (isOnCareTeam(user.id, patientId)) return { allowed: true, via: "care_team" };
  // ...unless a live Code Blue override exists AND privilege >= 6 (spec §2.3).
  if (ROLE_PRIVILEGE[user.role] >= 6 && activeCodeBlue(user.id, patientId)) {
    return { allowed: true, via: "code_blue" };
  }
  return { allowed: false, via: "denied" };
}

export function linkPatientUser(userId: string, patientId: string) {
  patientUserLinks[userId] = patientId;
}

// --- Audit ------------------------------------------------------------------
export function audit(entry: Omit<AuditEntry, "id" | "timestamp">): AuditEntry {
  const row: AuditEntry = { id: uuid(), timestamp: now(), ...entry };
  db.audit_log.push(row);
  return row;
}

// --- Alerts -----------------------------------------------------------------
export function raiseAlert(a: Omit<Alert, "id" | "created_at" | "acknowledged_by_id" | "acknowledged_at" | "escalated_at">): Alert {
  const row: Alert = {
    id: uuid(), created_at: now(), acknowledged_by_id: null, acknowledged_at: null, escalated_at: null, ...a,
  };
  db.alerts.push(row);
  return row;
}

export function latestVitals(patientId: string): Vitals | undefined {
  return db.vitals
    .filter((v) => v.patient_id === patientId)
    .sort((a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime())[0];
}

export function vitalsHistory(patientId: string): Vitals[] {
  return db.vitals
    .filter((v) => v.patient_id === patientId)
    .sort((a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime());
}
