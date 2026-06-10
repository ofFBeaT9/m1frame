import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

interface Alert {
  id: string; patient_id: string; alert_type: string; severity: "info" | "warning" | "critical";
  message: string; created_at: string; acknowledged_by_id: string | null; escalated_at: string | null;
}

const SEV: Record<string, string> = { critical: "#EF4444", warning: "#F59E0B", info: "#6366F1" };

export function Alerts() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["alerts"], queryFn: () => api.get<Alert[]>("/alerts"), refetchInterval: 10_000 });
  const ack = useMutation({ mutationFn: (id: string) => api.post(`/alerts/${id}/ack`), onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }) });
  const esc = useMutation({ mutationFn: (id: string) => api.post(`/alerts/${id}/escalate`), onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }) });

  if (isLoading) return <p className="text-text-secondary">Loading…</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight mb-4">Alert Centre</h1>
      <div className="space-y-2">
        {(data ?? []).map((a) => (
          <div key={a.id} className="bg-surface border border-border-subtle rounded-lg p-3 flex items-center gap-3"
            style={{ borderLeft: `3px solid ${SEV[a.severity]}` }}>
            <div className="flex-1">
              <div className="text-sm">{a.message}</div>
              <div className="text-[11px] text-text-muted font-mono">{a.alert_type} · {a.patient_id} · {new Date(a.created_at).toLocaleString()}</div>
            </div>
            {a.acknowledged_by_id ? (
              <span className="text-success text-[12px]">✓ acknowledged</span>
            ) : (
              <div className="flex gap-2">
                <button onClick={() => ack.mutate(a.id)} className="text-[12px] px-2 py-1 rounded bg-success/20 text-success">Acknowledge</button>
                <button onClick={() => esc.mutate(a.id)} className="text-[12px] px-2 py-1 rounded bg-warning/20 text-warning">Escalate</button>
              </div>
            )}
          </div>
        ))}
        {(data ?? []).length === 0 && <p className="text-text-secondary">No active alerts.</p>}
      </div>
    </div>
  );
}
