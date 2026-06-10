// Single source of truth for Role-Based Access Control (spec §2).
// This module is consumed by:
//   1. the data layer (`store.authorize`)  — the "RLS" choke-point
//   2. Express middleware (`requirePermission`)
//   3. the React client (shipped via /api/auth/me -> permission matrix)
// Because all three layers read the SAME matrix, a privilege escalation at one
// layer cannot silently diverge from the others.

import type { Role } from "./types.js";

export const ROLE_PRIVILEGE: Record<Role, number> = {
  admin: 10,
  physician: 9,
  resident: 8,
  np_pa: 7,
  nurse: 6,
  med_tech: 5,
  pharmacist: 5,
  physio: 4,
  nutritionist: 4,
  social_worker: 3,
  patient: 1,
};

// Permission values: true = full, false = none, string = scoped/qualified.
export type Permission = boolean | string;

export type Action =
  | "read_chart"
  | "write_soap"
  | "write_vitals"
  | "write_orders"
  | "upload_labs"
  | "upload_imaging"
  | "ai_trajectory"
  | "ai_guideline_search"
  | "calculators"
  | "protocol_read"
  | "protocol_edit"
  | "video_outbound"
  | "video_inbound"
  | "chat"
  | "user_management"
  | "audit_read"
  | "release_results"
  | "code_blue_override";

// Full permission matrix — faithful to spec §2.2.
export const PERMISSION_MATRIX: Record<Action, Partial<Record<Role, Permission>>> = {
  read_chart: { admin: true, physician: true, resident: true, np_pa: true, nurse: "assigned", pharmacist: "med-only", physio: "PT-only", nutritionist: "diet-only", social_worker: "psych-only", patient: "own" },
  write_soap: { admin: true, physician: true, resident: true, np_pa: true, physio: "PT notes", nutritionist: "diet notes", social_worker: "SW notes" },
  write_vitals: { admin: true, physician: true, resident: true, np_pa: true, nurse: true },
  write_orders: { admin: true, physician: true, resident: "co-sign", np_pa: "limited" },
  upload_labs: { admin: true, physician: true, resident: true, np_pa: true, med_tech: true },
  upload_imaging: { admin: true, physician: true, resident: true, med_tech: true },
  ai_trajectory: { admin: true, physician: true, resident: true, np_pa: true },
  ai_guideline_search: { admin: true, physician: true, resident: true, np_pa: true, nurse: true, pharmacist: true, physio: true, nutritionist: true },
  calculators: { admin: true, physician: true, resident: true, np_pa: true, nurse: true, pharmacist: true, physio: true, nutritionist: true },
  protocol_read: { admin: true, physician: true, resident: true, np_pa: true, nurse: true, med_tech: true, pharmacist: true, physio: true, nutritionist: true, social_worker: true },
  protocol_edit: { admin: true, physician: "approved" },
  video_outbound: { admin: true, physician: true, resident: true, np_pa: true, nurse: true, pharmacist: true, physio: true, nutritionist: true, social_worker: true, patient: "own-team" },
  video_inbound: { admin: true, physician: true, resident: true, np_pa: true, nurse: true, pharmacist: true, physio: true, nutritionist: true, social_worker: true, patient: true },
  chat: { admin: true, physician: true, resident: true, np_pa: true, nurse: true, med_tech: true, pharmacist: true, physio: true, nutritionist: true, social_worker: true, patient: "own-team" },
  user_management: { admin: true },
  audit_read: { admin: true },
  release_results: { physician: true, resident: true, np_pa: true },
  // Code Blue override — patient-safety requirement, privilege >= 6 (spec §2.3).
  code_blue_override: { admin: true, physician: true, resident: true, np_pa: true, nurse: true },
};

export function permissionFor(role: Role, action: Action): Permission {
  return PERMISSION_MATRIX[action]?.[role] ?? false;
}

export function can(role: Role, action: Action): boolean {
  return permissionFor(role, action) !== false;
}

// Privilege level >= 6 may invoke Code Blue override (spec §2.3).
export function canInvokeCodeBlue(role: Role): boolean {
  return ROLE_PRIVILEGE[role] >= 6;
}

// Build the client-facing matrix (what the React element guards consume).
export function clientPermissions(role: Role): Record<Action, Permission> {
  const out = {} as Record<Action, Permission>;
  (Object.keys(PERMISSION_MATRIX) as Action[]).forEach((a) => {
    out[a] = permissionFor(role, a);
  });
  return out;
}
