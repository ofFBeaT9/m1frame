import { Router, type Request } from "express";
import { db, audit, authorizePatientAccess, latestVitals, vitalsHistory } from "../db/store.js";
import { requireAuth, requirePermission } from "../middleware/auth.js";
import { recordVitals, staleState } from "../services/vitalsService.js";
import { news2Colour } from "../domain/news2.js";

export const patientsRouter = Router();
patientsRouter.use(requireAuth);

// Helper: load patient + enforce the data-layer RLS choke-point, with audit.
function loadAuthorized(req: Request, patientId: string) {
  const patient = db.patients.find((p) => p.id === patientId);
  if (!patient) return { error: 404 as const };
  const decision = authorizePatientAccess(req.user!, patientId);
  if (!decision.allowed) return { error: 403 as const };
  // If access is via Code Blue, record the section access on the override session + audit.
  if (decision.via === "code_blue") {
    const session = db.code_blue_sessions.find(
      (s) => s.user_id === req.user!.id && s.patient_id === patientId && s.end_time === null,
    );
    const section = req.path.includes("/vitals") ? "vitals" : "chart";
    if (session && !session.accessed_sections.includes(section)) session.accessed_sections.push(section);
    audit({
      user_id: req.user!.id, role: req.user!.role, action_type: "chart_access",
      resource_type: "patient", resource_id: patientId, patient_id: patientId,
      changes: { via: "code_blue" }, ip_address: req.ip ?? null,
      user_agent: req.headers["user-agent"] ?? null, code_blue_override: true, override_reason: "code_blue_session",
    });
  }
  return { patient, via: decision.via };
}

// GET /api/patients — list (scoped to what the role may see).
patientsRouter.get("/", requirePermission("read_chart"), (req, res) => {
  const u = req.user!;
  const list = db.patients.filter((p) => authorizePatientAccess(u, p.id).allowed);
  res.json(
    list.map((p) => {
      const lv = latestVitals(p.id);
      const enc = db.encounters.find((e) => e.patient_id === p.id && !e.discharged_at);
      return {
        id: p.id, mrn: p.mrn, full_name: p.full_name, category: p.category,
        primary_diagnosis: p.primary_diagnosis, unit_id: enc?.unit_id ?? null,
        bed_id: enc?.bed_id ?? null,
        news2: lv?.news2_score ?? null, news2_colour: lv ? news2Colour(lv.news2_score) : null,
        stale: staleState(p.id),
      };
    }),
  );
});

// GET /api/patients/:id — full chart header.
patientsRouter.get("/:id", requirePermission("read_chart"), (req, res) => {
  const r = loadAuthorized(req, req.params.id);
  if (r.error === 404) return res.status(404).json({ error: "Patient not found" });
  if (r.error === 403) return res.status(403).json({ error: "Access denied (not on care team)" });
  const enc = db.encounters.find((e) => e.patient_id === r.patient.id && !e.discharged_at);
  res.json({ patient: r.patient, encounter: enc ?? null, access_via: r.via });
});

// GET /api/patients/:id/vitals — history + latest.
patientsRouter.get("/:id/vitals", requirePermission("read_chart"), (req, res) => {
  const r = loadAuthorized(req, req.params.id);
  if (r.error) return res.status(r.error).json({ error: r.error === 404 ? "Not found" : "Access denied" });
  res.json({ latest: latestVitals(r.patient.id) ?? null, history: vitalsHistory(r.patient.id), stale: staleState(r.patient.id) });
});

// POST /api/patients/:id/vitals — record vitals (auto NEWS2/qSOFA + alerts).
patientsRouter.post("/:id/vitals", requirePermission("write_vitals"), (req, res) => {
  const patient = db.patients.find((p) => p.id === req.params.id);
  if (!patient) return res.status(404).json({ error: "Patient not found" });
  const decision = authorizePatientAccess(req.user!, patient.id);
  if (!decision.allowed) return res.status(403).json({ error: "Access denied" });
  const enc = db.encounters.find((e) => e.patient_id === patient.id && !e.discharged_at);
  const { vitals, alerts } = recordVitals(patient, enc?.id ?? "", req.user!.id, req.body ?? {});
  audit({
    user_id: req.user!.id, role: req.user!.role, action_type: "record_vitals",
    resource_type: "vitals", resource_id: vitals.id, patient_id: patient.id,
    changes: { news2: vitals.news2_score, qsofa: vitals.qsofa_score }, ip_address: req.ip ?? null,
    user_agent: req.headers["user-agent"] ?? null, code_blue_override: decision.via === "code_blue", override_reason: null,
  });
  res.status(201).json({ vitals, alerts_raised: alerts });
});

// GET /api/monitoring — physician board (assigned patients) (spec §8.1).
patientsRouter.get("/monitoring/board", requirePermission("read_chart"), (req, res) => {
  const u = req.user!;
  // Single choke-point: same authorize() as every other patient route (no bypass).
  const list = db.patients.filter((p) => authorizePatientAccess(u, p.id).allowed);
  res.json(
    list.map((p) => {
      const lv = latestVitals(p.id);
      const enc = db.encounters.find((e) => e.patient_id === p.id && !e.discharged_at);
      const spark = vitalsHistory(p.id).slice(-12).map((v) => v.news2_score);
      const unack = db.alerts.filter((a) => a.patient_id === p.id && !a.acknowledged_by_id).length;
      return {
        id: p.id, mrn: p.mrn, full_name: p.full_name, category: p.category,
        primary_diagnosis: p.primary_diagnosis, unit_id: enc?.unit_id ?? null, bed_id: enc?.bed_id ?? null,
        news2: lv?.news2_score ?? null, news2_band: lv?.news2_band ?? null,
        news2_colour: lv ? news2Colour(lv.news2_score) : null,
        last_vitals: lv ? { hr: lv.hr, bp: lv.bp_sys && lv.bp_dia ? `${lv.bp_sys}/${lv.bp_dia}` : null, spo2: lv.spo2, rr: lv.rr, temp: lv.temp, recorded_at: lv.recorded_at } : null,
        sparkline: spark, unack_alerts: unack, stale: staleState(p.id),
      };
    }),
  );
});
