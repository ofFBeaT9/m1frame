import { Router } from "express";
import { db, vitalsHistory } from "../db/store.js";
import { requireAuth, requirePermission } from "../middleware/auth.js";
import {
  patientToFhir, vitalsToObservations, conditionToFhir,
  medicationRequestToFhir, diagnosticReportToFhir, bundle,
} from "../domain/fhir.js";

export const fhirRouter = Router();
fhirRouter.use(requireAuth, requirePermission("read_chart"));

// GET /api/fhir/r4/:resource/:id  (spec §1.2, §21)
fhirRouter.get("/r4/:resource/:id", (req, res) => {
  const { resource, id } = req.params;
  switch (resource) {
    case "Patient": {
      const p = db.patients.find((x) => x.id === id);
      return p ? res.json(patientToFhir(p)) : res.status(404).json({ error: "not found" });
    }
    case "Observation": {
      // id here is a patient id -> return latest vitals as observations
      const v = vitalsHistory(id).slice(-1)[0];
      return v ? res.json(bundle(vitalsToObservations(v))) : res.status(404).json({ error: "not found" });
    }
    case "Condition": {
      const enc = db.encounters.find((e) => e.patient_id === id && !e.discharged_at);
      const p = db.patients.find((x) => x.id === id);
      return enc && p ? res.json(conditionToFhir(enc, p)) : res.status(404).json({ error: "not found" });
    }
    case "MedicationRequest":
      return res.json(medicationRequestToFhir({ id: `med-${id}`, patient_id: id, drug: "See active medications", dose: "", route: "", authoredOn: new Date().toISOString() }));
    case "DiagnosticReport":
      return res.json(diagnosticReportToFhir({ id: `dr-${id}`, patient_id: id, panel: "Composite", issued: new Date().toISOString(), conclusion: "See lab results module" }));
    default:
      return res.status(400).json({ error: `Unsupported FHIR resource: ${resource}` });
  }
});

// GET /api/fhir/r4/Patient/:id/$everything — full patient Bundle (spec §12)
fhirRouter.get("/r4/Patient/:id/everything", (req, res) => {
  const id = req.params.id;
  const p = db.patients.find((x) => x.id === id);
  if (!p) return res.status(404).json({ error: "not found" });
  const enc = db.encounters.find((e) => e.patient_id === id && !e.discharged_at);
  const resources: unknown[] = [patientToFhir(p)];
  for (const v of vitalsHistory(id)) resources.push(...vitalsToObservations(v));
  if (enc) resources.push(conditionToFhir(enc, p));
  res.json(bundle(resources));
});
