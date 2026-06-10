import { useState } from "react";
import { api } from "../lib/api";

const REASONS = ["Cardiac Arrest", "Respiratory Arrest", "Acute Deterioration", "Mass Casualty", "Other"];

export function CodeBlueModal({ onClose, onActivated }: { onClose: () => void; onActivated: () => void }) {
  const [patientId, setPatientId] = useState("");
  const [reason, setReason] = useState(REASONS[0]);
  const [note, setNote] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function activate() {
    setErr(null);
    setBusy(true);
    try {
      await api.post("/codeblue", { patient_id: patientId, reason_code: reason, reason_text: note });
      onActivated();
      onClose();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50" role="dialog" aria-modal="true">
      <div className="bg-elevated border border-critical rounded-lg p-6 w-[440px] max-w-[90vw]">
        <h2 className="text-critical font-bold text-lg flex items-center gap-2">
          <span className="cb-dot inline-block w-3 h-3 rounded-full bg-critical" /> Code Blue Override
        </h2>
        <p className="text-text-secondary text-[13px] mt-1">
          Emergency access to any patient chart. Every invocation is permanently audited and the administrator is notified.
        </p>
        <label className="block mt-4 text-[13px] text-text-secondary">Patient ID</label>
        <input value={patientId} onChange={(e) => setPatientId(e.target.value)} placeholder="patient-5"
          className="w-full mt-1 bg-input border border-border-active rounded px-3 py-2 font-mono text-sm" />
        <label className="block mt-3 text-[13px] text-text-secondary">Reason</label>
        <select value={reason} onChange={(e) => setReason(e.target.value)}
          className="w-full mt-1 bg-input border border-border-active rounded px-3 py-2 text-sm">
          {REASONS.map((r) => <option key={r}>{r}</option>)}
        </select>
        <label className="block mt-3 text-[13px] text-text-secondary">Justification (min 10 chars)</label>
        <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2}
          className="w-full mt-1 bg-input border border-border-active rounded px-3 py-2 text-sm" />
        {err && <p className="text-critical text-[13px] mt-2">{err}</p>}
        <div className="flex gap-2 mt-4 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded border border-border-active text-text-secondary">Cancel</button>
          <button onClick={activate} disabled={busy || note.trim().length < 10 || !patientId}
            className="px-4 py-2 text-sm rounded bg-critical text-white font-medium disabled:opacity-40">
            {busy ? "Activating…" : "Activate Override"}
          </button>
        </div>
      </div>
    </div>
  );
}
