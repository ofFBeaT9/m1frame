import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../lib/api";

interface CalcMeta { id: string; name: string; category: string; population: string; citation: string; }
interface CalcField { key: string; label: string; type: "number" | "select" | "boolean"; unit?: string; options?: { value: string; label: string }[]; }
interface CalcDetail extends CalcMeta { fields: CalcField[]; }
interface CalcOutput { calculator: string; citation: string; output: { value: string; interpretation: string; band: string }; }

const POP_TAG: Record<string, string> = { pediatric: "🧒", adult: "👤", geriatric: "👴", all: "🌐" };
const BAND_COLOUR: Record<string, string> = { normal: "#10B981", low: "#3B82F6", moderate: "#F59E0B", high: "#EF4444", critical: "#EF4444", info: "#6366F1" };

function CalcRunner({ meta }: { meta: CalcMeta }) {
  const { data } = useQuery({ queryKey: ["calc", meta.id], queryFn: () => api.get<CalcDetail>(`/calculators/${meta.id}`) });
  const [inputs, setInputs] = useState<Record<string, number | string | boolean>>({});
  const [result, setResult] = useState<CalcOutput | null>(null);

  async function run() {
    const r = await api.post<CalcOutput>(`/calculators/${meta.id}`, { inputs });
    setResult(r);
  }

  if (!data) return <div className="text-text-secondary text-sm">Loading…</div>;
  return (
    <div className="bg-surface border border-border-subtle rounded-lg p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{POP_TAG[meta.population]} {meta.name}</h3>
      </div>
      <div className="text-[11px] text-text-muted mb-3">{meta.citation}</div>
      <div className="space-y-2">
        {data.fields.map((f) => (
          <div key={f.key} className="flex items-center gap-2">
            <label className="text-[13px] text-text-secondary flex-1">{f.label}{f.unit ? ` (${f.unit})` : ""}</label>
            {f.type === "boolean" ? (
              <input type="checkbox" onChange={(e) => setInputs({ ...inputs, [f.key]: e.target.checked })} />
            ) : f.type === "select" ? (
              <select onChange={(e) => setInputs({ ...inputs, [f.key]: e.target.value })}
                className="bg-input border border-border-active rounded px-2 py-1 text-sm">
                <option value="">—</option>
                {f.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            ) : (
              <input type="number" onChange={(e) => setInputs({ ...inputs, [f.key]: Number(e.target.value) })}
                className="bg-input border border-border-active rounded px-2 py-1 text-sm w-24 font-mono" />
            )}
          </div>
        ))}
      </div>
      <button onClick={run} className="mt-3 bg-accent-primary text-[#0A0E17] px-3 py-1.5 rounded text-sm font-medium">Calculate</button>
      {result && (
        <div className="mt-3 p-3 rounded" style={{ background: (BAND_COLOUR[result.output.band] ?? "#475569") + "22" }}>
          <div className="font-mono text-lg font-semibold" style={{ color: BAND_COLOUR[result.output.band] ?? "#F1F5F9" }}>{result.output.value}</div>
          <div className="text-[13px] text-text-secondary mt-1">{result.output.interpretation}</div>
        </div>
      )}
    </div>
  );
}

export function Calculators() {
  const { data, isLoading } = useQuery({ queryKey: ["calculators"], queryFn: () => api.get<CalcMeta[]>("/calculators") });
  if (isLoading) return <p className="text-text-secondary">Loading…</p>;
  const cats = Array.from(new Set((data ?? []).map((c) => c.category)));
  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight mb-4">Medical Calculators</h1>
      {cats.map((cat) => (
        <div key={cat} className="mb-6">
          <h2 className="text-sm uppercase text-text-muted mb-2">{cat}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {(data ?? []).filter((c) => c.category === cat).map((c) => <CalcRunner key={c.id} meta={c} />)}
          </div>
        </div>
      ))}
    </div>
  );
}
