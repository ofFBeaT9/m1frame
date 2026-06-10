// Demo data seed (spec §20). 11 users (one per role), 3 wards, 12 patients with
// the spec's vitals trajectories, protocols, and pre-stored AI/calculator results.
import { db, reset, uuid, now, linkPatientUser } from "./store.js";
import { categoryFromDob } from "../domain/vitalRanges.js";
import { recordVitals } from "../services/vitalsService.js";
import type { Role, User, Patient, Encounter, Unit } from "../domain/types.js";

const DEMO_PASSWORD = "Demo1234!";

function dobForAge(years: number, extraDays = 0): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - years);
  d.setDate(d.getDate() - extraDays);
  return d.toISOString().slice(0, 10);
}
function dobForDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export function seed() {
  reset();

  // --- Units (spec §20) ---
  const units: Unit[] = [
    { id: "icu", name: "ICU", type: "ICU", bed_count: 8, charge_nurse_id: null, ai_refresh_interval_min: 5 },
    { id: "gm", name: "General Medicine", type: "General Medical", bed_count: 16, charge_nurse_id: null, ai_refresh_interval_min: 15 },
    { id: "paed", name: "Paediatrics", type: "Paediatrics", bed_count: 12, charge_nurse_id: null, ai_refresh_interval_min: 15 },
  ];
  db.units.push(...units);

  // --- Users (one per role) ---
  const roleEmails: [Role, string, string, string | null][] = [
    ["admin", "admin@nexus.demo", "Dr. Admin Okafor", null],
    ["physician", "physician@nexus.demo", "Dr. Elena Marchetti", "icu"],
    ["resident", "resident@nexus.demo", "Dr. Sam Patel", "icu"],
    ["np_pa", "np@nexus.demo", "Jordan Lee NP", "gm"],
    ["nurse", "nurse@nexus.demo", "Nurse Amina Yusuf", "icu"],
    ["med_tech", "medtech@nexus.demo", "Tech Rafael Cruz", null],
    ["pharmacist", "pharmacist@nexus.demo", "Pharm. Wei Chen", null],
    ["physio", "physio@nexus.demo", "PT Olga Petrova", null],
    ["nutritionist", "nutritionist@nexus.demo", "RD Hana Kim", null],
    ["social_worker", "socialworker@nexus.demo", "SW Tom Becker", null],
    ["patient", "patient@nexus.demo", "Ahmad Karimi", null],
  ];
  const users: User[] = roleEmails.map(([role, email, full_name, unit_id]) => ({
    id: `user-${role}`, email, role, full_name, unit_id,
    is_active: true, mfa_enabled: role !== "patient", password: DEMO_PASSWORD, created_at: now(),
  }));
  db.users.push(...users);
  const physician = users.find((u) => u.role === "physician")!;
  const nurse = users.find((u) => u.role === "nurse")!;
  units[0].charge_nurse_id = nurse.id;

  // --- Patients + encounters ---
  interface Spec {
    name: string; sex: Patient["sex"]; dob: string; dx: string; unit: string; bed: string;
    icd10?: string; allergies?: Patient["allergies"];
    trajectory?: { hr: number; sbp: number; dbp: number; rr: number; spo2: number; temp: number; o2?: boolean; altered?: boolean }[];
    careTeamNurse?: boolean;
  }
  const specs: Spec[] = [
    { name: "Ahmad Karimi", sex: "male", dob: dobForAge(58), dx: "Septic shock", unit: "icu", bed: "ICU-01", icd10: "A41.9",
      allergies: [{ allergen: "Penicillin", reaction: "Anaphylaxis", severity: "life-threatening", verification: "confirmed" }],
      careTeamNurse: true,
      trajectory: [
        { hr: 98, sbp: 100, dbp: 60, rr: 22, spo2: 95, temp: 38.4, o2: true },
        { hr: 112, sbp: 92, dbp: 54, rr: 26, spo2: 93, temp: 38.9, o2: true, altered: true },
        { hr: 128, sbp: 84, dbp: 48, rr: 30, spo2: 91, temp: 39.2, o2: true, altered: true },
      ] },
    { name: "Sara Hosseini", sex: "female", dob: dobForAge(72), dx: "ARDS post-pneumonia", unit: "icu", bed: "ICU-02", icd10: "J80",
      careTeamNurse: true,
      trajectory: [
        { hr: 88, sbp: 118, dbp: 70, rr: 18, spo2: 94, temp: 37.1, o2: true },
        { hr: 86, sbp: 120, dbp: 72, rr: 18, spo2: 95, temp: 37.0, o2: true },
      ] },
    { name: "Mohammad Rezaei", sex: "male", dob: dobForAge(41), dx: "Post-cardiac arrest", unit: "icu", bed: "ICU-03", icd10: "I46.9",
      trajectory: [{ hr: 76, sbp: 124, dbp: 78, rr: 16, spo2: 97, temp: 35.8, altered: true, o2: true }] },
    { name: "Fatimah Al-Zahra", sex: "female", dob: dobForAge(29), dx: "Post-op major surgery", unit: "icu", bed: "ICU-04",
      trajectory: [{ hr: 82, sbp: 116, dbp: 74, rr: 16, spo2: 98, temp: 36.8 }] },
    { name: "Reza Ahmadi", sex: "male", dob: dobForAge(67), dx: "ACS / NSTEMI", unit: "gm", bed: "GM-01", icd10: "I21.4",
      trajectory: [{ hr: 92, sbp: 138, dbp: 84, rr: 18, spo2: 96, temp: 36.9 }] },
    { name: "Maryam Jafari", sex: "female", dob: dobForAge(84), dx: "Hip fracture post-op", unit: "gm", bed: "GM-02", icd10: "S72.0",
      trajectory: [{ hr: 78, sbp: 132, dbp: 80, rr: 17, spo2: 95, temp: 36.7 }] },
    { name: "Dariush Tehrani", sex: "male", dob: dobForAge(52), dx: "Acute pancreatitis", unit: "gm", bed: "GM-03", icd10: "K85.9",
      trajectory: [{ hr: 104, sbp: 108, dbp: 66, rr: 22, spo2: 95, temp: 37.9 }] },
    { name: "Leila Shirazi", sex: "female", dob: dobForAge(39), dx: "DKA resolving", unit: "gm", bed: "GM-04", icd10: "E10.1",
      trajectory: [{ hr: 96, sbp: 118, dbp: 72, rr: 20, spo2: 98, temp: 36.8 }] },
    { name: "Arash Moradi", sex: "male", dob: dobForAge(8), dx: "Severe asthma exacerbation", unit: "paed", bed: "PAED-01", icd10: "J45.901",
      trajectory: [{ hr: 130, sbp: 100, dbp: 64, rr: 34, spo2: 92, temp: 37.2, o2: true }] },
    { name: "Negar Soleimani", sex: "female", dob: dobForAge(4), dx: "Bronchiolitis", unit: "paed", bed: "PAED-02", icd10: "J21.9",
      trajectory: [{ hr: 128, sbp: 96, dbp: 60, rr: 38, spo2: 92, temp: 37.6, o2: true }] },
    { name: "Baby of Zeinab Ghorbani", sex: "female", dob: dobForDays(3), dx: "Neonatal jaundice", unit: "paed", bed: "PAED-03", icd10: "P59.9",
      trajectory: [{ hr: 142, sbp: 68, dbp: 40, rr: 48, spo2: 98, temp: 37.0 }] },
    { name: "Amir Hosein Karimian", sex: "male", dob: dobForAge(14), dx: "Type 1 DM newly diagnosed", unit: "paed", bed: "PAED-04", icd10: "E10.9",
      trajectory: [{ hr: 96, sbp: 112, dbp: 70, rr: 18, spo2: 99, temp: 36.9 }] },
  ];

  const baseTime = Date.now() - 18 * 3_600_000;
  specs.forEach((s, idx) => {
    const patient: Patient = {
      id: `patient-${idx + 1}`, mrn: `MRN${String(100001 + idx)}`, full_name: s.name,
      dob: s.dob, sex: s.sex, category: categoryFromDob(s.dob), blood_type: ["O+", "A+", "B+", "AB+", "O-"][idx % 5],
      allergies: s.allergies ?? [], advance_directives: {}, primary_diagnosis: s.dx,
      created_at: now(), updated_at: now(),
    };
    db.patients.push(patient);

    const careTeam = [physician.id, ...(s.careTeamNurse ? [nurse.id] : [])];
    const enc: Encounter = {
      id: `enc-${idx + 1}`, patient_id: patient.id, admitting_physician_id: physician.id,
      unit_id: s.unit, bed_id: s.bed, admission_type: "emergency",
      admitting_diagnosis_icd10: s.icd10 ?? null, admitting_diagnosis_icd11: null,
      triage_score: null, triage_system: null, admitted_at: now(), discharged_at: null,
      discharge_disposition: null, care_team_ids: careTeam,
    };
    db.encounters.push(enc);

    // Link the patient-role demo user to ICU-01 (Ahmad Karimi).
    if (s.name === "Ahmad Karimi") linkPatientUser("user-patient", patient.id);

    const traj = s.trajectory ?? [{ hr: 80, sbp: 120, dbp: 78, rr: 16, spo2: 98, temp: 36.8 }];
    traj.forEach((t, ti) => {
      recordVitals(patient, enc.id, nurse.id, {
        hr: t.hr, bp_sys: t.sbp, bp_dia: t.dbp, rr: t.rr, spo2: t.spo2, temp: t.temp,
        on_oxygen: !!t.o2, consciousness_new_confusion: !!t.altered,
        recorded_at: new Date(baseTime + ti * 6 * 3_600_000).toISOString(),
      });
    });
  });

  // --- Protocols (sample across mandatory categories, spec §5) ---
  const protoCats = [
    "Emergency & Resuscitation", "Sepsis & Critical Care", "Cardiac Emergencies", "Stroke",
    "Infection Control", "Medication Safety", "Triage", "Patient Safety & Falls",
  ];
  protoCats.forEach((cat, i) => {
    db.protocols.push({
      id: `proto-${i + 1}`, title: `${cat} — Standard Operating Procedure`, category: cat,
      version: "1.2.0", status: "active",
      content_html: `<h2>${cat}</h2><p>Hospital protocol for ${cat.toLowerCase()}. Review cycle: 12 months.</p>`,
      last_reviewed_at: new Date(Date.now() - (i % 3) * 200 * 24 * 3_600_000).toISOString(),
      approved_by_id: physician.id, is_custom: false, created_at: now(), updated_at: now(),
    });
  });

  // --- Pre-saved calculator results ---
  db.calculator_results.push({
    id: uuid(), patient_id: "patient-1", user_id: physician.id, calculator_name: "qSOFA",
    inputs: { rr: 30, sbp: 84, altered: true }, result_value: "3",
    result_interpretation: "High risk of poor outcome — evaluate for sepsis, escalate",
    clinical_note: "Septic shock — sepsis bundle initiated.", created_at: now(),
  });

  return { users: db.users.length, patients: db.patients.length, units: db.units.length };
}

// Allow `npm run seed` to print a summary.
if (process.argv[1]?.endsWith("seed.ts") || process.argv[1]?.endsWith("seed.js")) {
  const r = seed();
  // eslint-disable-next-line no-console
  console.log("Seeded:", r);
}
