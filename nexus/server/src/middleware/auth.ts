import type { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { config } from "../config.js";
import { db, audit } from "../db/store.js";
import { can, type Action } from "../domain/rbac.js";
import type { Role, User } from "../domain/types.js";

export interface AuthUser {
  id: string;
  role: Role;
  email: string;
  full_name: string;
}

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface Request {
      user?: AuthUser;
    }
  }
}

export function signToken(user: User): string {
  const options: jwt.SignOptions = { expiresIn: config.jwtExpiry as jwt.SignOptions["expiresIn"] };
  return jwt.sign(
    { id: user.id, role: user.role, email: user.email, full_name: user.full_name },
    config.jwtSecret,
    options,
  );
}

export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const header = req.headers.authorization;
  const token = header?.startsWith("Bearer ") ? header.slice(7) : null;
  if (!token) return res.status(401).json({ error: "Authentication required" });
  try {
    const payload = jwt.verify(token, config.jwtSecret) as AuthUser & { exp: number };
    const live = db.users.find((u) => u.id === payload.id && u.is_active);
    if (!live) return res.status(401).json({ error: "User inactive or not found" });
    req.user = { id: live.id, role: live.role, email: live.email, full_name: live.full_name };
    next();
  } catch {
    return res.status(401).json({ error: "Invalid or expired token" });
  }
}

// Express-layer RBAC gate (layer 2 of 3). Reads the SAME matrix as the client.
export function requirePermission(action: Action) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!req.user) return res.status(401).json({ error: "Authentication required" });
    if (!can(req.user.role, action)) {
      audit({
        user_id: req.user.id, role: req.user.role, action_type: "access_denied",
        resource_type: "permission", resource_id: action, patient_id: null,
        changes: { action }, ip_address: req.ip ?? null,
        user_agent: req.headers["user-agent"] ?? null, code_blue_override: false, override_reason: null,
      });
      return res.status(403).json({ error: `Forbidden: ${req.user.role} lacks '${action}'` });
    }
    next();
  };
}

// Audit middleware factory — logs the action after a successful mutating call.
export function withAudit(action_type: string, resource_type: string) {
  return (req: Request, res: Response, next: NextFunction) => {
    res.on("finish", () => {
      if (res.statusCode < 400 && req.user) {
        audit({
          user_id: req.user.id, role: req.user.role, action_type, resource_type,
          resource_id: req.params.id ?? null, patient_id: req.params.id ?? req.body?.patient_id ?? null,
          changes: req.method === "GET" ? null : sanitize(req.body),
          ip_address: req.ip ?? null, user_agent: req.headers["user-agent"] ?? null,
          code_blue_override: false, override_reason: null,
        });
      }
    });
    next();
  };
}

function sanitize(body: unknown): Record<string, unknown> | null {
  if (!body || typeof body !== "object") return null;
  const clone = { ...(body as Record<string, unknown>) };
  delete clone.password;
  return clone;
}
