import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../store/auth";
import { api } from "../lib/api";
import { CodeBlueModal } from "./CodeBlueModal";

const NAV = [
  { to: "/monitoring", label: "Monitoring", icon: "🩺", perm: "read_chart" },
  { to: "/alerts", label: "Alerts", icon: "🔔", perm: "read_chart" },
  { to: "/patients", label: "Patients", icon: "👥", perm: "read_chart" },
  { to: "/calculators", label: "Calculators", icon: "🧮", perm: "calculators" },
  { to: "/protocols", label: "Protocols", icon: "📋", perm: "protocol_read" },
  { to: "/admin", label: "Admin", icon: "⚙️", perm: "audit_read" },
];

const DEMO_USERS = [
  ["admin@nexus.demo", "Admin"],
  ["physician@nexus.demo", "Physician"],
  ["resident@nexus.demo", "Resident"],
  ["nurse@nexus.demo", "Nurse"],
  ["medtech@nexus.demo", "Med Tech"],
  ["pharmacist@nexus.demo", "Pharmacist"],
  ["patient@nexus.demo", "Patient"],
];

export function Layout({ children }: { children: React.ReactNode }) {
  const { user, can, logout, demoSwitch } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [showCB, setShowCB] = useState(false);
  const [aiOnline, setAiOnline] = useState<boolean | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  // AI health poll every 60s (spec §7).
  useEffect(() => {
    let active = true;
    const check = () => api.get<{ online: boolean }>("/ai/health").then((h) => active && setAiOnline(h.online)).catch(() => active && setAiOnline(false));
    check();
    const t = setInterval(check, 60_000);
    return () => { active = false; clearInterval(t); };
  }, []);

  return (
    <div className="min-h-screen flex bg-base text-text-primary">
      {/* Sidebar */}
      <aside className={`${collapsed ? "w-16" : "w-60"} border-r border-border-subtle bg-surface flex flex-col transition-all`}>
        <div className="p-4 flex items-center justify-between">
          {!collapsed && <span className="font-bold text-accent-primary tracking-tight">NEXUS</span>}
          <button onClick={() => setCollapsed(!collapsed)} className="text-text-muted" aria-label="Toggle sidebar">≡</button>
        </div>
        <nav className="flex-1 px-2 space-y-1">
          {NAV.filter((n) => can(n.perm)).map((n) => (
            <Link key={n.to} to={n.to} title={n.label}
              className={`flex items-center gap-3 px-3 py-2 rounded text-sm ${loc.pathname.startsWith(n.to) ? "bg-elevated text-accent-primary" : "text-text-secondary hover:bg-elevated"}`}>
              <span>{n.icon}</span>{!collapsed && n.label}
            </Link>
          ))}
        </nav>
      </aside>

      {/* Main column */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 border-b border-border-subtle bg-surface flex items-center px-4 gap-4">
          <span className="font-bold text-accent-primary">Every patient. Every signal. Every second.</span>
          <div className="ml-auto flex items-center gap-3 text-[13px]">
            {/* AI status badge */}
            <span className={`px-2 py-1 rounded text-xs font-medium ${aiOnline ? "bg-info/20 text-info" : "bg-text-muted/20 text-text-secondary"}`}>
              {aiOnline === null ? "AI …" : aiOnline ? "AI Online" : "AI Offline"}
            </span>
            {/* Demo role switcher (spec §21) */}
            <select value={user?.email} onChange={(e) => demoSwitch(e.target.value)}
              className="bg-input border border-border-active rounded px-2 py-1 text-xs" aria-label="Demo role switch">
              {DEMO_USERS.map(([email, label]) => <option key={email} value={email}>{label}</option>)}
            </select>
            {/* Code Blue button — always visible (spec §16.3) */}
            {can("code_blue_override") && (
              <button onClick={() => setShowCB(true)}
                className="flex items-center gap-1.5 bg-critical text-white px-3 py-1.5 rounded font-medium text-xs">
                <span className="cb-dot inline-block w-2 h-2 rounded-full bg-white" /> Code Blue
              </button>
            )}
            <span className="text-text-secondary">{user?.full_name} · <span className="text-accent-primary">{user?.role}</span></span>
            <button onClick={() => { logout(); nav("/login"); }} className="text-text-muted hover:text-text-primary">Logout</button>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6 max-w-[1600px] w-full mx-auto">{children}</main>
      </div>

      {showCB && <CodeBlueModal onClose={() => setShowCB(false)} onActivated={() => { /* board refreshes on nav */ }} />}
    </div>
  );
}
