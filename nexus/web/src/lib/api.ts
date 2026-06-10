// Thin API client. Reads the JWT from the auth store.
export type Permission = boolean | string;

const BASE = "/api";

function token(): string | null {
  return localStorage.getItem("nexus_token");
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token() ? { Authorization: `Bearer ${token()}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T,>(p: string) => req<T>("GET", p),
  post: <T,>(p: string, b?: unknown) => req<T>("POST", p, b),
};

export interface SessionUser {
  id: string;
  email: string;
  role: string;
  full_name: string;
  privilege: number;
}

export interface LoginResponse {
  token: string;
  user: SessionUser;
  permissions: Record<string, Permission>;
}

export interface BoardPatient {
  id: string;
  mrn: string;
  full_name: string;
  category: string;
  primary_diagnosis: string;
  unit_id: string | null;
  bed_id: string | null;
  news2: number | null;
  news2_band: string | null;
  news2_colour: "green" | "amber" | "red" | "darkred" | null;
  last_vitals: { hr: number | null; bp: string | null; spo2: number | null; rr: number | null; temp: number | null; recorded_at: string } | null;
  sparkline: number[];
  unack_alerts: number;
  stale: "ok" | "yellow" | "red";
}
