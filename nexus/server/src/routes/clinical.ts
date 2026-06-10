import { Router } from "express";
import { db, uuid, now, audit, raiseAlert, authorizePatientAccess } from "../db/store.js";
import { requireAuth, requirePermission } from "../middleware/auth.js";
import { canInvokeCodeBlue } from "../domain/rbac.js";
import { getCalculator, calculatorIndex } from "../domain/calculators.js";
import { runAi, aiHealth } from "../services/ai.js";
import { latestVitals, vitalsHistory } from "../db/store.js";
import { config } from "../config.js";

export const clinicalRouter = Router();
clinicalRouter.use(requireAuth);

// --- Alerts (spec §8.3) -----------------------------------------------------
clinicalRouter.get("/alerts", (req, res) => {
  const alerts = [...db.alerts].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  res.json(alerts);
});

clinicalRouter.post("/alerts/:id/ack", (req, res) => {
  const a = db.alerts.find((x) => x.id === req.params.id);
  if (!a) return res.status(404).json({ error: "Alert not found" });
  a.acknowledged_by_id = req.user!.id;
  a.acknowledged_at = now();
  audit({ user_id: req.user!.id, role: req.user!.role, action_type: "ack_alert", resource_type: "alert", resource_id: a.id, patient_id: a.patient_id, changes: null, ip_address: req.ip ?? null, user_agent: req.headers["user-agent"] ?? null, code_blue_override: false, override_reason: null });
  res.json(a);
});

clinicalRouter.post("/alerts/:id/escalate", (req, res) => {
  const a = db.alerts.find((x) => x.id === req.params.id);
  if (!a) return res.status(404).json({ error: "Alert not found" });
  a.escalated_at = now();
  audit({ user_id: req.user!.id, role: req.user!.role, action_type: "escalate_alert", resource_type: "alert", resource_id: a.id, patient_id: a.patient_id, changes: null, ip_address: req.ip ?? null, user_agent: req.headers["user-agent"] ?? null, code_blue_override: false, override_reason: null });
  res.json(a);
});

// --- Code Blue override (spec §2.3) -----------------------------------------
const REASONS = ["Cardiac Arrest", "Respiratory Arrest", "Acute Deterioration", "Mass Casualty", "Other"];

clinicalRouter.post("/codeblue", requirePermission("code_blue_override"), (req, res) => {
  const { patient_id, reason_code, reason_text } = req.body ?? {};
  if (!canInvokeCodeBlue(req.user!.role)) return res.status(403).json({ error: "Privilege level < 6" });
  if (!REASONS.includes(reason_code)) return res.status(400).json({ error: "Invalid reason_code" });
  if (!reason_text || String(reason_text).trim().length < 10) {
    return res.status(400).json({ error: "reason_text must be at least 10 characters" });
  }
  if (!db.patients.find((p) => p.id === patient_id)) return res.status(404).json({ error: "Patient not found" });

  const start = now();
  const expires = new Date(Date.now() + config.codeBlueSessionMinutes * 60_000).toISOString();
  const session = { id: uuid(), user_id: req.user!.id, patient_id, reason_code, reason_text, accessed_sections: [] as string[], start_time: start, expires_at: expires, end_time: null };
  db.code_blue_sessions.push(session);

  // Permanent audit row + admin real-time notification (spec §2.3).
  audit({ user_id: req.user!.id, role: req.user!.role, action_type: "code_blue_override", resource_type: "patient", resource_id: patient_id, patient_id, changes: { reason_code, reason_text }, ip_address: req.ip ?? null, user_agent: req.headers["user-agent"] ?? null, code_blue_override: true, override_reason: reason_text });
  raiseAlert({ patient_id, alert_type: "code_blue_active", severity: "critical", message: `Code Blue override by ${req.user!.full_name} (${reason_code})`, trigger_value: reason_code });

  res.status(201).json({ session });
});

clinicalRouter.get("/codeblue/active", (req, res) => {
  const t = Date.now();
  res.json(db.code_blue_sessions.filter((s) => s.end_time === null && new Date(s.expires_at).getTime() > t));
});

const MAX_TOTAL_CODE_BLUE_MINUTES = 180; // cap unbounded extension (safety/audit)

clinicalRouter.post("/codeblue/:id/extend", (req, res) => {
  const s = db.code_blue_sessions.find((x) => x.id === req.params.id && x.user_id === req.user!.id);
  if (!s) return res.status(404).json({ error: "Session not found" });
  if (s.end_time) return res.status(400).json({ error: "Session already ended" });
  const totalMin = (new Date(s.expires_at).getTime() + 15 * 60_000 - new Date(s.start_time).getTime()) / 60_000;
  if (totalMin > MAX_TOTAL_CODE_BLUE_MINUTES) {
    return res.status(400).json({ error: `Cannot extend beyond ${MAX_TOTAL_CODE_BLUE_MINUTES} min total — re-invoke a new override` });
  }
  s.expires_at = new Date(new Date(s.expires_at).getTime() + 15 * 60_000).toISOString(); // 15-min increments
  audit({ user_id: req.user!.id, role: req.user!.role, action_type: "code_blue_extend", resource_type: "patient", resource_id: s.patient_id, patient_id: s.patient_id, changes: { new_expiry: s.expires_at }, ip_address: req.ip ?? null, user_agent: req.headers["user-agent"] ?? null, code_blue_override: true, override_reason: s.reason_text });
  res.json(s);
});

clinicalRouter.post("/codeblue/:id/end", (req, res) => {
  const s = db.code_blue_sessions.find((x) => x.id === req.params.id && x.user_id === req.user!.id);
  if (!s) return res.status(404).json({ error: "Session not found" });
  s.end_time = now();
  audit({ user_id: req.user!.id, role: req.user!.role, action_type: "code_blue_end", resource_type: "patient", resource_id: s.patient_id, patient_id: s.patient_id, changes: { accessed_sections: s.accessed_sections }, ip_address: req.ip ?? null, user_agent: req.headers["user-agent"] ?? null, code_blue_override: true, override_reason: s.reason_text });
  res.json(s);
});

// --- Calculators (spec §4) --------------------------------------------------
clinicalRouter.get("/calculators", requirePermission("calculators"), (_req, res) => {
  res.json(calculatorIndex());
});

clinicalRouter.get("/calculators/:id", requirePermission("calculators"), (req, res) => {
  const c = getCalculator(req.params.id);
  if (!c) return res.status(404).json({ error: "Calculator not found" });
  res.json({ id: c.id, name: c.name, category: c.category, population: c.population, citation: c.citation, fields: c.fields });
});

clinicalRouter.post("/calculators/:id", requirePermission("calculators"), (req, res) => {
  const c = getCalculator(req.params.id);
  if (!c) return res.status(404).json({ error: "Calculator not found" });
  const { inputs = {}, save = false, patient_id = null, clinical_note = "" } = req.body ?? {};
  // L3: reject non-finite numeric inputs rather than silently producing NaN/Infinity.
  for (const f of c.fields) {
    if (f.type === "number" && inputs[f.key] !== undefined && inputs[f.key] !== "" && !Number.isFinite(Number(inputs[f.key]))) {
      return res.status(400).json({ error: `Invalid numeric input: ${f.key}` });
    }
  }
  let output;
  try {
    output = c.compute(inputs);
  } catch {
    return res.status(400).json({ error: "Invalid inputs" });
  }
  if (save && patient_id) {
    // M4: saving to a chart requires patient-level authorization (not just feature access).
    const decision = authorizePatientAccess(req.user!, patient_id);
    if (!decision.allowed) return res.status(403).json({ error: "Not authorized to save to this patient" });
  }
  if (save) {
    const row = { id: uuid(), patient_id, user_id: req.user!.id, calculator_name: c.name, inputs, result_value: output.value, result_interpretation: output.interpretation, clinical_note, created_at: now() };
    db.calculator_results.push(row);
    audit({ user_id: req.user!.id, role: req.user!.role, action_type: "save_calculator", resource_type: "calculator_result", resource_id: row.id, patient_id, changes: { calculator: c.name, result: output.value }, ip_address: req.ip ?? null, user_agent: req.headers["user-agent"] ?? null, code_blue_override: false, override_reason: null });
  }
  res.json({ calculator: c.name, citation: c.citation, output });
});

// --- Protocols (spec §5) ----------------------------------------------------
clinicalRouter.get("/protocols", requirePermission("protocol_read"), (_req, res) => {
  res.json(db.protocols.map((p) => ({ ...p, stale: staleBand(p.last_reviewed_at) })));
});

clinicalRouter.get("/protocols/:id", requirePermission("protocol_read"), (req, res) => {
  const p = db.protocols.find((x) => x.id === req.params.id);
  if (!p) return res.status(404).json({ error: "Protocol not found" });
  res.json({ ...p, stale: staleBand(p.last_reviewed_at) });
});

function staleBand(lastReviewed: string): "ok" | "review" | "outdated" {
  const months = (Date.now() - new Date(lastReviewed).getTime()) / (30 * 24 * 3_600_000);
  if (months > 24) return "outdated";
  if (months > 12) return "review";
  return "ok";
}

// --- AI engine (spec §7) ----------------------------------------------------
clinicalRouter.get("/ai/health", (_req, res) => res.json(aiHealth()));

clinicalRouter.post("/ai/trajectory", requirePermission("ai_trajectory"), async (req, res) => {
  const { patient_id } = req.body ?? {};
  const patient = db.patients.find((p) => p.id === patient_id);
  if (!patient) return res.status(404).json({ error: "Patient not found" });
  const hist = vitalsHistory(patient_id).slice(-18);
  const lv = latestVitals(patient_id);
  const context = `Patient ${patient.full_name} (${patient.category}), dx: ${patient.primary_diagnosis}. ` +
    `Latest NEWS2 ${lv?.news2_score ?? "n/a"}. Vitals trend (NEWS2): ${hist.map((v) => v.news2_score).join(",")}.`;
  const result = await runAi({ feature: "trajectory", patientCategory: patient.category, context, cacheKey: `trajectory:${patient_id}` });
  res.json({ ...result, news2_trend: hist.map((v) => ({ at: v.recorded_at, news2: v.news2_score })) });
});
