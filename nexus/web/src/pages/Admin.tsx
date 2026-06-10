import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

interface AuditRow { id: string; timestamp: string; user_id: string | null; role: string | null; action_type: string; resource_type: string; patient_id: string | null; code_blue_override: boolean; override_reason: string | null; }
interface Analytics { active_users: number; patients: number; encounters: number; audit_entries: number; code_blue_invocations: number; calculator_uses: number; alerts_by_type: Record<string, number>; }

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-surface border border-border-subtle rounded-lg p-4">
      <div className="text-[12px] text-text-secondary">{label}</div>
      <div className="font-mono text-2xl font-semibold text-accent-primary">{value}</div>
    </div>
  );
}

export function Admin() {
  const analytics = useQuery({ queryKey: ["analytics"], queryFn: () => api.get<Analytics>("/admin/analytics") });
  const audit = useQuery({ queryKey: ["audit"], queryFn: () => api.get<AuditRow[]>("/admin/audit") });

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight mb-4">Admin · System Analytics</h1>
      {analytics.data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Stat label="Active users" value={analytics.data.active_users} />
          <Stat label="Patients" value={analytics.data.patients} />
          <Stat label="Audit entries" value={analytics.data.audit_entries} />
          <Stat label="Code Blue invocations" value={analytics.data.code_blue_invocations} />
        </div>
      )}

      <div className="flex items-center justify-between mb-2">
        <h2 className="font-semibold">Audit Log</h2>
        <a href="/api/admin/audit.csv" className="text-accent-secondary text-[13px]">Export CSV</a>
      </div>
      <div className="bg-surface border border-border-subtle rounded-lg overflow-hidden">
        <table className="w-full text-[13px]">
          <thead className="bg-elevated text-text-secondary">
            <tr>
              <th className="text-left px-3 py-2">Time</th>
              <th className="text-left px-3 py-2">Role</th>
              <th className="text-left px-3 py-2">Action</th>
              <th className="text-left px-3 py-2">Resource</th>
              <th className="text-left px-3 py-2">Patient</th>
              <th className="text-left px-3 py-2">CB</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {(audit.data ?? []).slice(0, 100).map((r) => (
              <tr key={r.id} className={`border-t border-border-subtle ${r.code_blue_override ? "bg-critical/10" : ""}`}>
                <td className="px-3 py-1.5 text-text-muted">{new Date(r.timestamp).toLocaleTimeString()}</td>
                <td className="px-3 py-1.5">{r.role}</td>
                <td className="px-3 py-1.5 text-accent-primary">{r.action_type}</td>
                <td className="px-3 py-1.5 text-text-secondary">{r.resource_type}</td>
                <td className="px-3 py-1.5 text-text-secondary">{r.patient_id ?? "—"}</td>
                <td className="px-3 py-1.5">{r.code_blue_override ? "🔴" : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
