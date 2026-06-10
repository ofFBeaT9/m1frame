// FHIR R4 resource mappers (spec §1.2, §12, §21). Pure domain -> FHIR JSON.
// Covers the delivery-required resources: Patient, Observation, Condition,
// MedicationRequest, DiagnosticReport, plus Bundle export.
import type { Patient, Vitals, Encounter } from "./types.js";

export function patientToFhir(p: Patient) {
  const [given, ...family] = p.full_name.split(" ");
  return {
    resourceType: "Patient",
    id: p.id,
    identifier: [{ system: "urn:nexus:mrn", value: p.mrn }],
    name: [{ use: "official", family: family.join(" ") || given, given: [given] }],
    gender: p.sex === "intersex" ? "other" : p.sex,
    birthDate: p.dob,
    extension: [
      { url: "urn:nexus:category", valueString: p.category },
      { url: "urn:nexus:bloodType", valueString: p.blood_type },
    ],
  };
}

// One vitals row expands into multiple FHIR Observations (vital-signs category).
const LOINC: Record<string, { code: string; display: string; unit: string }> = {
  hr: { code: "8867-4", display: "Heart rate", unit: "/min" },
  rr: { code: "9279-1", display: "Respiratory rate", unit: "/min" },
  spo2: { code: "59408-5", display: "Oxygen saturation", unit: "%" },
  temp: { code: "8310-5", display: "Body temperature", unit: "Cel" },
  bp_sys: { code: "8480-6", display: "Systolic blood pressure", unit: "mm[Hg]" },
  bp_dia: { code: "8462-4", display: "Diastolic blood pressure", unit: "mm[Hg]" },
  news2_score: { code: "early-warning-score", display: "NEWS2 score", unit: "{score}" },
};

export function vitalsToObservations(v: Vitals) {
  const obs: unknown[] = [];
  const push = (key: keyof typeof LOINC, value: number) => {
    const meta = LOINC[key];
    obs.push({
      resourceType: "Observation",
      id: `${v.id}-${key}`,
      status: "final",
      category: [{ coding: [{ system: "http://terminology.hl7.org/CodeSystem/observation-category", code: "vital-signs" }] }],
      code: { coding: [{ system: "http://loinc.org", code: meta.code, display: meta.display }] },
      subject: { reference: `Patient/${v.patient_id}` },
      effectiveDateTime: v.recorded_at,
      valueQuantity: { value, unit: meta.unit, system: "http://unitsofmeasure.org", code: meta.unit },
    });
  };
  if (v.hr != null) push("hr", v.hr);
  if (v.rr != null) push("rr", v.rr);
  if (v.spo2 != null) push("spo2", v.spo2);
  if (v.temp != null) push("temp", v.temp);
  if (v.bp_sys != null) push("bp_sys", v.bp_sys);
  if (v.bp_dia != null) push("bp_dia", v.bp_dia);
  push("news2_score", v.news2_score);
  return obs;
}

export function conditionToFhir(encounter: Encounter, patient: Patient) {
  return {
    resourceType: "Condition",
    id: `cond-${encounter.id}`,
    clinicalStatus: { coding: [{ system: "http://terminology.hl7.org/CodeSystem/condition-clinical", code: "active" }] },
    code: {
      coding: [
        ...(encounter.admitting_diagnosis_icd10
          ? [{ system: "http://hl7.org/fhir/sid/icd-10-cm", code: encounter.admitting_diagnosis_icd10 }]
          : []),
        ...(encounter.admitting_diagnosis_icd11
          ? [{ system: "http://id.who.int/icd/release/11/mms", code: encounter.admitting_diagnosis_icd11 }]
          : []),
      ],
      text: patient.primary_diagnosis,
    },
    subject: { reference: `Patient/${patient.id}` },
    recordedDate: encounter.admitted_at,
  };
}

export function medicationRequestToFhir(opts: {
  id: string;
  patient_id: string;
  drug: string;
  dose: string;
  route: string;
  authoredOn: string;
}) {
  return {
    resourceType: "MedicationRequest",
    id: opts.id,
    status: "active",
    intent: "order",
    medicationCodeableConcept: { text: opts.drug },
    subject: { reference: `Patient/${opts.patient_id}` },
    authoredOn: opts.authoredOn,
    dosageInstruction: [{ text: `${opts.dose} ${opts.route}` }],
  };
}

export function diagnosticReportToFhir(opts: {
  id: string;
  patient_id: string;
  panel: string;
  issued: string;
  conclusion: string;
}) {
  return {
    resourceType: "DiagnosticReport",
    id: opts.id,
    status: "final",
    category: [{ coding: [{ system: "http://terminology.hl7.org/CodeSystem/v2-0074", code: "LAB" }] }],
    code: { text: opts.panel },
    subject: { reference: `Patient/${opts.patient_id}` },
    issued: opts.issued,
    conclusion: opts.conclusion,
  };
}

export function bundle(resources: unknown[]) {
  return {
    resourceType: "Bundle",
    type: "collection",
    timestamp: new Date().toISOString(),
    total: resources.length,
    entry: resources.map((r) => ({ resource: r })),
  };
}
