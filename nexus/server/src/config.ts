// Environment configuration (spec §19). All optional with safe local defaults so
// the app boots and is testable with zero external services.
export const config = {
  port: Number(process.env.PORT ?? 4000),
  jwtSecret: process.env.SESSION_SECRET ?? "nexus-dev-secret-change-me-in-production-0000000000000000",
  jwtExpiry: "8h", // spec §1.2 — 8-hour session expiry
  frontendUrl: process.env.FRONTEND_URL ?? "http://localhost:3000",
  anthropic: {
    apiKey: process.env.ANTHROPIC_API_KEY ?? "",
    model: process.env.ANTHROPIC_MODEL ?? "claude-sonnet-4-20250514",
    maxTokens: Number(process.env.ANTHROPIC_MAX_TOKENS ?? 4096),
  },
  features: {
    triage: (process.env.ENABLE_TRIAGE_MODULE ?? "true") === "true",
    demoMode: (process.env.ENABLE_DEMO_MODE ?? "true") === "true",
    fhirExport: (process.env.ENABLE_FHIR_EXPORT ?? "true") === "true",
    rtl: (process.env.ENABLE_RTL ?? "false") === "true",
  },
  codeBlueSessionMinutes: 30,
  staleVitalsMultiplier: 2,
};
