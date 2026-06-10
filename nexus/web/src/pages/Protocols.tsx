import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

interface Protocol { id: string; title: string; category: string; version: string; status: string; last_reviewed_at: string; stale: "ok" | "review" | "outdated"; content_html: string; }

const STALE_BANNER: Record<string, { label: string; cls: string } | null> = {
  ok: null,
  review: { label: "Review due (>12 months)", cls: "bg-warning/20 text-warning" },
  outdated: { label: "Potentially outdated (>24 months)", cls: "bg-critical/20 text-critical" },
};

export function Protocols() {
  const { data, isLoading } = useQuery({ queryKey: ["protocols"], queryFn: () => api.get<Protocol[]>("/protocols") });
  if (isLoading) return <p className="text-text-secondary">Loading…</p>;
  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight mb-4">Hospital Protocols</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {(data ?? []).map((p) => {
          const banner = STALE_BANNER[p.stale];
          return (
            <div key={p.id} className="bg-surface border border-border-subtle rounded-lg p-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">{p.title}</h3>
                <span className="text-[11px] font-mono text-text-muted">v{p.version}</span>
              </div>
              <div className="text-[12px] text-text-secondary">{p.category} · {p.status}</div>
              {banner && <div className={`mt-2 text-[11px] px-2 py-1 rounded ${banner.cls}`}>{banner.label}</div>}
              <div className="text-[13px] text-text-secondary mt-2" dangerouslySetInnerHTML={{ __html: p.content_html }} />
              <div className="text-[11px] text-text-muted mt-2">Last reviewed {new Date(p.last_reviewed_at).toLocaleDateString()}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
