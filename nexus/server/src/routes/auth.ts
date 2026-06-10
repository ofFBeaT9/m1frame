import { Router } from "express";
import { db, audit } from "../db/store.js";
import { signToken, requireAuth } from "../middleware/auth.js";
import { clientPermissions, ROLE_PRIVILEGE } from "../domain/rbac.js";
import { config } from "../config.js";

export const authRouter = Router();

// POST /api/auth/login — demo credential check (bcrypt in production).
authRouter.post("/login", (req, res) => {
  const { email, password } = req.body ?? {};
  const user = db.users.find((u) => u.email === email && u.is_active);
  if (!user || user.password !== password) {
    return res.status(401).json({ error: "Invalid credentials" });
  }
  audit({
    user_id: user.id, role: user.role, action_type: "login", resource_type: "session",
    resource_id: user.id, patient_id: null, changes: null, ip_address: req.ip ?? null,
    user_agent: req.headers["user-agent"] ?? null, code_blue_override: false, override_reason: null,
  });
  res.json({
    token: signToken(user),
    user: { id: user.id, email: user.email, role: user.role, full_name: user.full_name, privilege: ROLE_PRIVILEGE[user.role] },
    permissions: clientPermissions(user.role),
    mfa_required: user.mfa_enabled, // 2FA enforced on clinical roles (spec §21)
  });
});

// POST /api/auth/demo-switch — instant role perspective switch (spec §21 demo mode).
authRouter.post("/demo-switch", (req, res) => {
  if (!config.features.demoMode) return res.status(403).json({ error: "Demo mode disabled" });
  const { email } = req.body ?? {};
  const user = db.users.find((u) => u.email === email && u.is_active);
  if (!user) return res.status(404).json({ error: "Demo user not found" });
  res.json({
    token: signToken(user),
    user: { id: user.id, email: user.email, role: user.role, full_name: user.full_name, privilege: ROLE_PRIVILEGE[user.role] },
    permissions: clientPermissions(user.role),
  });
});

// GET /api/auth/me — current identity + permission matrix for client guards.
authRouter.get("/me", requireAuth, (req, res) => {
  const u = req.user!;
  res.json({
    user: { ...u, privilege: ROLE_PRIVILEGE[u.role] },
    permissions: clientPermissions(u.role),
  });
});
