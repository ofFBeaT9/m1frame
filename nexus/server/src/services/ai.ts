// AI engine (spec §7) with MANDATORY graceful degraded mode (spec §1.3, §21).
// The app must never block on AI. With no ANTHROPIC_API_KEY the service returns
// a structured offline result instead of throwing.
import { config } from "../config.js";

export interface AiResult {
  offline: boolean;
  model: string;
  text: string;
  cached: boolean;
  generated_at: string;
  disclaimer: string;
}

const DISCLAIMER =
  "You are a clinical decision support AI. Output is advisory only. Clinical judgment supersedes all AI output.";

// Tiny per-process cache so degraded mode can show "last cached result".
const cache = new Map<string, AiResult>();

let lastHealthy = false;
export function aiOnline(): boolean {
  return config.anthropic.apiKey.length > 0;
}

export interface AiRequest {
  feature: "trajectory" | "diagnostic" | "guideline" | "interaction" | "scribe" | "education";
  patientCategory?: string;
  context: string;
  cacheKey?: string;
}

export async function runAi(req: AiRequest): Promise<AiResult> {
  const model = config.anthropic.model;
  const key = req.cacheKey ?? `${req.feature}:${req.context.slice(0, 64)}`;

  if (!aiOnline()) {
    const prior = cache.get(key);
    return prior
      ? { ...prior, offline: true, cached: true }
      : {
          offline: true, model, cached: false, generated_at: new Date().toISOString(),
          disclaimer: DISCLAIMER,
          text: "AI Offline — no cached result. All non-AI workflows remain fully available.",
        };
  }

  // Live path: call Anthropic. Kept defensive — any failure degrades, never throws.
  try {
    const sys = `${DISCLAIMER}\nPatient category: ${req.patientCategory ?? "unknown"}.`;
    const resp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": config.anthropic.apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model,
        max_tokens: config.anthropic.maxTokens,
        system: sys,
        messages: [{ role: "user", content: req.context }],
      }),
    });
    if (!resp.ok) throw new Error(`Anthropic ${resp.status}`);
    const data = (await resp.json()) as { content?: { text?: string }[] };
    const text = data.content?.map((c) => c.text ?? "").join("") ?? "";
    const result: AiResult = {
      offline: false, model, cached: false, text,
      generated_at: new Date().toISOString(), disclaimer: DISCLAIMER,
    };
    cache.set(key, result);
    lastHealthy = true;
    return result;
  } catch {
    lastHealthy = false; // L2: clear stale-good health on a live failure
    const prior = cache.get(key);
    return prior
      ? { ...prior, offline: true, cached: true }
      : {
          offline: true, model, cached: false, generated_at: new Date().toISOString(),
          disclaimer: DISCLAIMER,
          text: "AI temporarily unreachable — degraded mode. Non-AI workflows unaffected.",
        };
  }
}

export function aiHealth() {
  return { online: aiOnline(), lastHealthy, model: config.anthropic.model };
}
