import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../store/auth";

interface Vitals {
  id: string; hr: number | null; bp_sys: number | null; bp_dia: number | null; map: number | null;
  rr: number | null; spo2: number | null; temp: number | null; news2_score: number; news2_band: string;
  qsofa_score: number; recorded_at: string;
}
interface ChartResp { patient: { id: string; full_name: string; mrn: string; category: string; dob: string; primary_diagnosis: string; allergies: { allergen: string; severity: string }[] }; encounter: { unit_id: string; bed_id: string | null } | null; access_via: string; }
interface AiResp { offline: boolean; text: string; disclaimer: string; cached: boolean; news2_trend: { at: string; news2: number }[]; }

export function PatientConsole() {
  const { id } = useParams();
  const qc = useQueryClient();
  const { can } = useAuth();
  const [ai, setAi] = useState<AiResp | null>(null);

  const chart = useQuery({ queryKey: ["chart", id], queryFn: () => api.get<ChartResp>(`/patients/${id}`) });
  const vitals = useQuery({ queryKey: ["vitals", id], queryFn: () => api.get<{ latest: Vitals | null; history: Vitals[]; stale: string }>(`/patients/${id}/vitals`), refetchInterval: 15_000 });

  const aiMut = useMutation({
    mutationFn: () => api.post<AiResp>("/ai/trajectory", { patient_id: id }),
    onSuccess: (d) => setAi(d),
  });

  if (chart.isLoading) return <p className="text-text-secondary">Loading chart…</p>;
  if (chart.error) return <p className="text-critical">{(chart.error as Error).message}</p>;
  const c = chart.data!;
  const lv = vitals.data?.latest;

  return (
    <div>
      {/* Sticky patient context bar (spec §16.3) */}
      <div className="sticky top-0 bg-elevated border border-border-active rounded-lg px-4 py-3 mb-4 flex items-center gap-4">
        <div>
          <div className="font-semibold">{c.patient.full_name}</div>
          <div className="text-[12px] text-text-secondary font-mono">{c.patient.mrn} · {c.patient.category} · {c.encounter?.bed_id}</div>
        </div>
        <div className="flex gap-1">
          {c.patient.allergies.map((a) => (
            <span key={a.allergen} className="bg-critical/20 text-critical text-[11px] px-2 py-0.5 rounded">{a.allergen}</span>
          ))}
        </div>
        {c.access_via === "code_blue" && <span className="cb-dot bg-critical text-white text-[11px] px-2 py-0.5 rounded ml-auto">CODE BLUE ACCESS</span>}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* LEFT: live vitals */}
        <section className="bg-surface border border-border-subtle rounded-lg p-4">
          <h2 className="font-semibold mb-3">Live Vitals</h2>
          {lv ? (
            <div className="space-y-2 font-mono text-sm">
              <Row label="NEWS2" value={`${lv.news2_score} (${lv.news2_band})`} accent />
              <Row label="qSOFA" value={String(lv.qsofa_score)} />
              <Row label="HR" value={lv.hr} />
              <Row label="BP" value={lv.bp_sys && lv.bp_dia ? `${lv.bp_sys}/${lv.bp_dia}` : null} />
              <Row label="MAP" value={lv.map} />
              <Row label="RR" value={lv.rr} />
              <Row label="SpO₂" value={lv.spo2} />
              <Row label="Temp" value={lv.temp} />
              <div className="text-[11px] text-text-muted pt-2">Recorded {new Date(lv.recorded_at).toLocaleString()}</div>
            </div>
          ) : <p className="text-text-secondary text-sm">No vitals recorded.</p>}
        </section>

        {/* CENTRE: clinical summary */}
        <section className="bg-surface border border-border-subtle rounded-lg p-4">
          <h2 className="font-semibold mb-3">Clinical Summary</h2>
          <div className="text-sm text-text-secondary">Diagnosis</div>
          <div className="mb-3">{c.patient.primary_diagnosis}</div>
          <div className="text-sm text-text-secondary">NEWS2 history</div>
          <div className="font-mono text-xs mt-1">
            {(vitals.data?.history ?? []).map((v) => (
              <span key={v.id} className="inline-block mr-2">{v.news2_score}</span>
            ))}
          </div>
        </section>

        {/* RIGHT: AI trajectory */}
        <section className="bg-surface border border-border-subtle rounded-lg p-4">
          <h2 className="font-semibold mb-3 flex items-center gap-2">AI Trajectory <span className="text-info text-xs">advisory</span></h2>
          {can("ai_trajectory") ? (
            <>
              <button onClick={() => aiMut.mutate()} disabled={aiMut.isPending}
                className="bg-info/20 text-info px-3 py-1.5 rounded text-sm disabled:opacity-50">
                {aiMut.isPending ? "Analyzing…" : "Run Trajectory Analysis"}
              </button>
              {ai && (
                <div className="mt-3 text-sm">
                  {ai.offline && <div className="bg-text-muted/20 text-text-secondary text-xs px-2 py-1 rounded mb-2">AI Offline {ai.cached ? "(showing cached)" : ""}</div>}
                  <p className="text-text-secondary whitespace-pre-wrap">{ai.text}</p>
                  <p className="text-[11px] text-text-muted mt-3 italic">{ai.disclaimer}</p>
                </div>
              )}
            </>
          ) : <p className="text-text-secondary text-sm">Your role cannot run AI trajectory analysis.</p>}
        </section>
      </div>

      <p className="text-[11px] text-text-muted mt-4">Access path: {c.access_via}. All chart access is audited.</p>
      <button onClick={() => { qc.invalidateQueries({ queryKey: ["vitals", id] }); }} className="hidden" />
    </div>
  );
}

function Row({ label, value, accent }: { label: string; value: string | number | null; accent?: boolean }) {
  return (
    <div className="flex justify-between border-b border-border-subtle pb-1">
      <span className="text-text-secondary">{label}</span>
      <span className={accent ? "text-accent-primary font-semibold" : ""}>{value ?? "—"}</span>
    </div>
  );
}
