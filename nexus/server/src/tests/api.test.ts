import { describe, it, expect, beforeAll } from "vitest";
import request from "supertest";
import { createApp } from "../app.js";
import { seed } from "../db/seed.js";
import { db } from "../db/store.js";

const app = createApp();

async function login(email: string) {
  const r = await request(app).post("/api/auth/login").send({ email, password: "Demo1234!" });
  return r.body.token as string;
}

beforeAll(() => seed());

describe("Auth", () => {
  it("rejects bad credentials", async () => {
    const r = await request(app).post("/api/auth/login").send({ email: "physician@nexus.demo", password: "wrong" });
    expect(r.status).toBe(401);
  });
  it("logs in and returns a permission matrix", async () => {
    const r = await request(app).post("/api/auth/login").send({ email: "physician@nexus.demo", password: "Demo1234!" });
    expect(r.status).toBe(200);
    expect(r.body.token).toBeTruthy();
    expect(r.body.permissions.read_chart).toBe(true);
  });
  it("blocks unauthenticated access", async () => {
    const r = await request(app).get("/api/patients");
    expect(r.status).toBe(401);
  });
});

describe("Three-layer RBAC + care-team scoping", () => {
  it("physician sees all patients", async () => {
    const t = await login("physician@nexus.demo");
    const r = await request(app).get("/api/patients").set("Authorization", `Bearer ${t}`);
    expect(r.status).toBe(200);
    expect(r.body.length).toBe(12);
  });

  it("nurse only sees assigned patients", async () => {
    const t = await login("nurse@nexus.demo");
    const r = await request(app).get("/api/patients").set("Authorization", `Bearer ${t}`);
    expect(r.status).toBe(200);
    // nurse assigned to ICU-01 and ICU-02 only
    expect(r.body.length).toBe(2);
  });

  it("nurse is denied an unassigned chart at the data layer", async () => {
    const t = await login("nurse@nexus.demo");
    // patient-5 (GM-01) is not on the nurse's care team
    const r = await request(app).get("/api/patients/patient-5").set("Authorization", `Bearer ${t}`);
    expect(r.status).toBe(403);
  });

  it("med_tech lacks read_chart entirely (middleware layer)", async () => {
    const t = await login("medtech@nexus.demo");
    const r = await request(app).get("/api/patients").set("Authorization", `Bearer ${t}`);
    expect(r.status).toBe(403);
  });

  it("H3: monitoring board is guarded by read_chart (med_tech blocked)", async () => {
    const t = await login("medtech@nexus.demo");
    const r = await request(app).get("/api/patients/monitoring/board").set("Authorization", `Bearer ${t}`);
    expect(r.status).toBe(403);
  });
});

describe("Code Blue override (spec §2.3)", () => {
  it("grants a nurse access to an unassigned chart, and audits it", async () => {
    const t = await login("nurse@nexus.demo");
    // Pre-check: denied
    const before = await request(app).get("/api/patients/patient-5").set("Authorization", `Bearer ${t}`);
    expect(before.status).toBe(403);

    // Activate
    const cb = await request(app).post("/api/codeblue").set("Authorization", `Bearer ${t}`)
      .send({ patient_id: "patient-5", reason_code: "Acute Deterioration", reason_text: "Patient unresponsive, peri-arrest" });
    expect(cb.status).toBe(201);

    // Now allowed via code_blue
    const after = await request(app).get("/api/patients/patient-5").set("Authorization", `Bearer ${t}`);
    expect(after.status).toBe(200);
    expect(after.body.access_via).toBe("code_blue");

    // Audited as override
    const overrideRows = db.audit_log.filter((a) => a.action_type === "code_blue_override");
    expect(overrideRows.length).toBeGreaterThan(0);
    expect(overrideRows[overrideRows.length - 1].code_blue_override).toBe(true);
  });

  it("rejects a too-short reason note", async () => {
    const t = await login("physician@nexus.demo");
    const r = await request(app).post("/api/codeblue").set("Authorization", `Bearer ${t}`)
      .send({ patient_id: "patient-6", reason_code: "Other", reason_text: "short" });
    expect(r.status).toBe(400);
  });

  it("forbids med_tech (privilege < 6) from invoking", async () => {
    const t = await login("medtech@nexus.demo");
    const r = await request(app).post("/api/codeblue").set("Authorization", `Bearer ${t}`)
      .send({ patient_id: "patient-6", reason_code: "Other", reason_text: "attempting override here" });
    expect(r.status).toBe(403);
  });
});

describe("Vitals write path raises sepsis alert", () => {
  it("records vitals and triggers qSOFA sepsis alert", async () => {
    const t = await login("physician@nexus.demo");
    const r = await request(app).post("/api/patients/patient-4/vitals").set("Authorization", `Bearer ${t}`)
      .send({ hr: 130, bp_sys: 88, bp_dia: 50, rr: 28, spo2: 90, temp: 39.1, on_oxygen: true, consciousness_new_confusion: true });
    expect(r.status).toBe(201);
    expect(r.body.vitals.news2_score).toBeGreaterThanOrEqual(7);
    expect(r.body.alerts_raised).toContain("sepsis_qsofa");
  });
});

describe("FHIR R4 export (spec §21)", () => {
  it("returns a valid Patient resource", async () => {
    const t = await login("physician@nexus.demo");
    const r = await request(app).get("/api/fhir/r4/Patient/patient-1").set("Authorization", `Bearer ${t}`);
    expect(r.status).toBe(200);
    expect(r.body.resourceType).toBe("Patient");
    expect(r.body.identifier[0].value).toMatch(/^MRN/);
  });
  it("exports a full patient Bundle", async () => {
    const t = await login("physician@nexus.demo");
    const r = await request(app).get("/api/fhir/r4/Patient/patient-1/everything").set("Authorization", `Bearer ${t}`);
    expect(r.status).toBe(200);
    expect(r.body.resourceType).toBe("Bundle");
    expect(r.body.total).toBeGreaterThan(1);
  });
});

describe("Calculators (spec §4)", () => {
  it("computes Cockcroft-Gault CrCl", async () => {
    const t = await login("physician@nexus.demo");
    const r = await request(app).post("/api/calculators/cockcroft_gault").set("Authorization", `Bearer ${t}`)
      .send({ inputs: { age: 70, weight: 70, creatinine: 1.2, sex: "male" } });
    expect(r.status).toBe(200);
    // ((140-70)*70)/(72*1.2) = 56.7 -> 57
    expect(r.body.output.value).toBe("57 mL/min");
  });

  it("denies calculators to social_worker", async () => {
    const t = await login("socialworker@nexus.demo");
    const r = await request(app).get("/api/calculators").set("Authorization", `Bearer ${t}`);
    expect(r.status).toBe(403);
  });
});

describe("Admin audit + AI degraded mode", () => {
  it("admin reads the audit log", async () => {
    const t = await login("admin@nexus.demo");
    const r = await request(app).get("/api/admin/audit").set("Authorization", `Bearer ${t}`);
    expect(r.status).toBe(200);
    expect(Array.isArray(r.body)).toBe(true);
  });
  it("AI trajectory returns offline (degraded) without a key, never errors", async () => {
    const t = await login("physician@nexus.demo");
    const r = await request(app).post("/api/ai/trajectory").set("Authorization", `Bearer ${t}`).send({ patient_id: "patient-1" });
    expect(r.status).toBe(200);
    expect(r.body.offline).toBe(true);
    expect(r.body.disclaimer).toContain("advisory only");
  });
});
