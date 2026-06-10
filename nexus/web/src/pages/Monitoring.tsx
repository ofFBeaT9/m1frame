import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type BoardPatient } from "../lib/api";
import { Sparkline, NEWS2_COLOUR } from "../components/Sparkline";
import { useState } from "react";

function VitalChip({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="text-center">
      <div className="text-[10px] text-text-muted uppercase">{label}</div>
      <div className="font-mono text-sm">{value ?? "—"}</div>
    </div>
  );
}

function PatientCard({ p }: { p: BoardPatient }) {
  const colour = p.news2_colour ? NEWS2_COLOUR[p.news2_colour] : "#475569";
  return (
    <Link to={`/monitoring/${p.id}`}
      className="bg-surface border border-border-subtle rounded-lg p-4 hover:border-border-active block">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-medium">{p.full_name}</div>
          <div className="text-[12px] text-text-secondary">{p.bed_id} · {p.category} · {p.mrn}</div>
          <div className="text-[12px] text-text-secondary mt-0.5">{p.primary_diagnosis}</div>
        </div>
        <div className="text-right">
          <div className="px-2 py-0.5 rounded font-mono text-sm font-semibold" style={{ background: colour + "22", color: colour }}>
            NEWS2 {p.news2 ?? "—"}
          </div>
          {p.unack_alerts > 0 && <div className="mt-1 text-[11px] text-critical">⚠ {p.unack_alerts} alert{p.unack_alerts > 1 ? "s" : ""}</div>}
          {p.stale !== "ok" && <div className={`mt-1 text-[11px] ${p.stale === "red" ? "text-critical" : "text-warning"}`}>● stale vitals</div>}
        </div>
      </div>
      <div className="mt-3"><Sparkline data={p.sparkline} colour={colour} /></div>
      <div className="grid grid-cols-5 gap-1 mt-2">
        <VitalChip label="HR" value={p.last_vitals?.hr ?? null} />
        <VitalChip label="BP" value={p.last_vitals?.bp ?? null} />
        <VitalChip label="SpO₂" value={p.last_vitals?.spo2 ?? null} />
        <VitalChip label="RR" value={p.last_vitals?.rr ?? null} />
        <VitalChip label="Temp" value={p.last_vitals?.temp ?? null} />
      </div>
    </Link>
  );
}

export function Monitoring() {
  const [sort, setSort] = useState<"news2" | "name" | "bed">("news2");
  const { data, isLoading, error } = useQuery({
    queryKey: ["board"],
    queryFn: () => api.get<BoardPatient[]>("/patients/monitoring/board"),
    refetchInterval: 15_000,
  });

  if (isLoading) return <p className="text-text-secondary">Loading ward…</p>;
  if (error) return <p className="text-critical">{(error as Error).message}</p>;

  const sorted = [...(data ?? [])].sort((a, b) => {
    if (sort === "news2") return (b.news2 ?? -1) - (a.news2 ?? -1);
    if (sort === "name") return a.full_name.localeCompare(b.full_name);
    return (a.bed_id ?? "").localeCompare(b.bed_id ?? "");
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold tracking-tight">Patient Monitoring</h1>
        <div className="flex items-center gap-2 text-[13px]">
          <span className="text-text-muted">Sort</span>
          <select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}
            className="bg-input border border-border-active rounded px-2 py-1 text-xs">
            <option value="news2">NEWS2</option>
            <option value="name">Name</option>
            <option value="bed">Bed</option>
          </select>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {sorted.map((p) => <PatientCard key={p.id} p={p} />)}
      </div>
      {sorted.length === 0 && <p className="text-text-secondary">No assigned patients.</p>}
    </div>
  );
}
