import { create } from "zustand";
import { api, type LoginResponse, type Permission, type SessionUser } from "../lib/api";

interface AuthState {
  user: SessionUser | null;
  permissions: Record<string, Permission>;
  login: (email: string, password: string) => Promise<void>;
  demoSwitch: (email: string) => Promise<void>;
  logout: () => void;
  can: (action: string) => boolean;
  restore: () => void;
}

function apply(set: (p: Partial<AuthState>) => void, r: LoginResponse) {
  localStorage.setItem("nexus_token", r.token);
  localStorage.setItem("nexus_user", JSON.stringify({ user: r.user, permissions: r.permissions }));
  set({ user: r.user, permissions: r.permissions });
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  permissions: {},
  login: async (email, password) => {
    const r = await api.post<LoginResponse>("/auth/login", { email, password });
    apply(set, r);
  },
  demoSwitch: async (email) => {
    const r = await api.post<LoginResponse>("/auth/demo-switch", { email });
    apply(set, r);
  },
  logout: () => {
    localStorage.removeItem("nexus_token");
    localStorage.removeItem("nexus_user");
    set({ user: null, permissions: {} });
  },
  can: (action) => {
    const p = get().permissions[action];
    return p !== undefined && p !== false;
  },
  restore: () => {
    const raw = localStorage.getItem("nexus_user");
    if (raw) {
      try {
        const { user, permissions } = JSON.parse(raw);
        set({ user, permissions });
      } catch {
        /* ignore */
      }
    }
  },
}));
