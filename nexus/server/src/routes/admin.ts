import { Router } from "express";
import { db } from "../db/store.js";
import { requireAuth, requirePermission } from "../middleware/auth.js";

export const adminRouter = Router();
adminRouter.use(requireAuth);

// GET /api/admin/users (spec §15)
adminRouter.get("/users", requirePermission("user_management"), (_req, res) => {
  res.json(db.users.map((u) => ({ id: u.id, email: u.email, role: u.role, full_name: u.full_name, unit_id: u.unit_id, is_active: u.is_active, mfa_enabled: u.mfa_enabled })));
});

// GET /api/admin/audit — searchable audit log (spec §15)
adminRouter.get("/audit", requirePermission("audit_read"), (req, res) => {
  let rows = [...db.audit_log].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  const { user, patient, action, code_blue } = req.query;
  if (user) rows = rows.filter((r) => r.user_id === user);
  if (patient) rows = rows.filter((r) => r.patient_id === patient);
  if (action) rows = rows.filter((r) => r.action_type === action);
  if (code_blue === "true") rows = rows.filter((r) => r.code_blue_override);
  res.json(rows.slice(0, 500));
});

// GET /api/admin/audit.csv — CSV export (spec §15)
adminRouter.get("/audit.csv", requirePermission("audit_read"), (_req, res) => {
  const header = "timestamp,user_id,role,action_type,resource_type,resource_id,patient_id,code_blue_override,override_reason";
  const lines = db.audit_log.map((r) =>
    [r.timestamp, r.user_id, r.role, r.action_type, r.resource_type, r.resource_id, r.patient_id, r.code_blue_override, JSON.stringify(r.override_reason ?? "")].join(","),
  );
  res.setHeader("Content-Type", "text/csv");
  res.setHeader("Content-Disposition", "attachment; filename=audit_log.csv");
  res.send([header, ...lines].join("\n"));
});

// GET /api/admin/analytics — system dashboard (spec §15)
adminRouter.get("/analytics", requirePermission("audit_read"), (_req, res) => {
  const byType: Record<string, number> = {};
  for (const a of db.alerts) byType[a.alert_type] = (byType[a.alert_type] ?? 0) + 1;
  res.json({
    active_users: db.users.filter((u) => u.is_active).length,
    patients: db.patients.length,
    encounters: db.encounters.filter((e) => !e.discharged_at).length,
    alerts_by_type: byType,
    audit_entries: db.audit_log.length,
    code_blue_invocations: db.audit_log.filter((a) => a.action_type === "code_blue_override").length,
    calculator_uses: db.calculator_results.length,
  });
});

// GET /api/admin/units (spec §11)
adminRouter.get("/units", requireAuth, (_req, res) => {
  res.json(db.units);
});
