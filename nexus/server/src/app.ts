import express from "express";
import cors from "cors";
import { authRouter } from "./routes/auth.js";
import { patientsRouter } from "./routes/patients.js";
import { clinicalRouter } from "./routes/clinical.js";
import { adminRouter } from "./routes/admin.js";
import { fhirRouter } from "./routes/fhir.js";
import { aiHealth } from "./services/ai.js";
import { config } from "./config.js";

export function createApp() {
  const app = express();
  app.use(cors());
  app.use(express.json({ limit: "10mb" }));

  app.get("/api/health", (_req, res) =>
    res.json({ status: "ok", ai: aiHealth(), features: config.features, ts: new Date().toISOString() }),
  );

  app.use("/api/auth", authRouter);
  app.use("/api/patients", patientsRouter);
  app.use("/api", clinicalRouter); // alerts, codeblue, calculators, protocols, ai
  app.use("/api/admin", adminRouter);
  app.use("/api/fhir", fhirRouter);

  app.use((_req, res) => res.status(404).json({ error: "Not found" }));
  return app;
}
