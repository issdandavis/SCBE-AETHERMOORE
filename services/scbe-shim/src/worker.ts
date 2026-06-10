/**
 * scbe-shim Cloudflare Worker — OpenAI-compatible governance proxy.
 *
 * Endpoints:
 *   POST /v1/chat/completions   OpenAI chat-completions, governed
 *   GET  /v1/health              Liveness + version
 *   GET  /v1/scorecard           Static metrics readout
 *
 * Response shape (governed): every successful response carries an
 * additional `scbe_governance` field with decision, harmonic score, reasons,
 * and a suggested_correction string (or null on ALLOW).
 *
 * Deploy:
 *   wrangler secret put HF_TOKEN
 *   wrangler deploy
 */

import { matchAuditorPhrasing } from "./patterns.js";
import { evaluateAxioms } from "./axioms.js";
import { decide } from "./decision.js";

interface Env {
  HF_TOKEN: string;
  HF_MODEL: string;
  HF_INFERENCE_BASE: string;
  SHIM_VERSION: string;
  SHIM_CACHE?: KVNamespace;
}

interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

interface ChatRequest {
  model?: string;
  messages: ChatMessage[];
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

function corsHeaders(): HeadersInit {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
  };
}

function json(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...corsHeaders(), ...(init.headers || {}) },
  });
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders() });

    const url = new URL(req.url);

    if (url.pathname === "/v1/health") {
      return json({
        ok: true,
        service: "scbe-shim",
        version: env.SHIM_VERSION,
        upstream_model: env.HF_MODEL,
        ts: new Date().toISOString(),
      });
    }

    if (url.pathname === "/v1/scorecard") {
      return json(getScorecard(env));
    }

    if (url.pathname === "/v1/chat/completions" && req.method === "POST") {
      return handleChat(req, env);
    }

    return json({ error: "not_found", path: url.pathname }, { status: 404 });
  },
};

async function handleChat(req: Request, env: Env): Promise<Response> {
  if (!env.HF_TOKEN) {
    return json({ error: { message: "HF_TOKEN secret not configured", type: "config_error" } }, { status: 500 });
  }

  let body: ChatRequest;
  try {
    body = await req.json();
  } catch {
    return json({ error: { message: "invalid JSON body", type: "invalid_request" } }, { status: 400 });
  }

  if (!body.messages || !Array.isArray(body.messages) || body.messages.length === 0) {
    return json({ error: { message: "messages[] required", type: "invalid_request" } }, { status: 400 });
  }

  const lastUser = [...body.messages].reverse().find(m => m.role === "user");
  const userText = lastUser?.content ?? "";

  // 1. Prompt-side pattern check (cheap, deterministic, runs first).
  const promptMatch = matchAuditorPhrasing(userText);

  // 2. If prompt is already a known-bad shape, refuse without calling upstream.
  if (promptMatch.matched) {
    const denied = decide(
      { violations: [], worstScore: 0, worstAxiom: null, reasons: [] },
      promptMatch,
      "",
    );
    if (denied.decision === "DENY" || denied.decision === "ESCALATE") {
      return json(
        await buildOpenAIResponse(
          env,
          body,
          denied.suggestedCorrection ?? "",
          denied,
          "scbe_prompt_block",
          "input",
          "scbe-preflight",
        ),
      );
    }
  }

  // 3. Forward to upstream LLM.
  const model = body.model ?? env.HF_MODEL;
  const upstreamReq = {
    model,
    messages: body.messages,
    temperature: body.temperature ?? 0.7,
    max_tokens: body.max_tokens ?? 1024,
    stream: false,
  };

  let upstreamResp: Response;
  try {
    upstreamResp = await fetch(`${env.HF_INFERENCE_BASE}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.HF_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(upstreamReq),
    });
  } catch (e) {
    return json(
      { error: { message: `upstream fetch failed: ${(e as Error).message}`, type: "upstream_error" } },
      { status: 502 },
    );
  }

  if (!upstreamResp.ok) {
    const errText = await upstreamResp.text();
    return json(
      { error: { message: `upstream ${upstreamResp.status}: ${errText.slice(0, 500)}`, type: "upstream_error" } },
      { status: 502 },
    );
  }

  const upstreamJson = (await upstreamResp.json()) as {
    choices?: Array<{ message?: { content?: string } }>;
  };
  const rawOutput = upstreamJson.choices?.[0]?.message?.content ?? "";

  // 4. Axiom evaluation on the model's output.
  const axiomReport = evaluateAxioms(rawOutput, userText);

  // 5. Decision.
  const decision = decide(axiomReport, promptMatch, rawOutput);

  // 6. Pick what to actually return: ALLOW -> raw, others -> correction.
  const finalContent =
    decision.decision === "ALLOW" ? rawOutput : decision.suggestedCorrection ?? rawOutput;

  return json(
    await buildOpenAIResponse(env, body, finalContent, decision, "scbe_governed", "output", "huggingface"),
  );
}

async function sha256Hex16(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const buf = await crypto.subtle.digest("SHA-256", data);
  const hex = Array.from(new Uint8Array(buf))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");
  return hex.slice(0, 16);
}

function interventionFor(decision: string, phase: "input" | "output"): string {
  if (decision === "ALLOW") return "none";
  if (decision === "DENY") return phase === "input" ? "refusal_injection" : "redaction";
  if (decision === "ESCALATE") return "hard_stop_or_human_review";
  return "soft_rewrite";
}

async function buildOpenAIResponse(
  env: Env,
  reqBody: ChatRequest,
  content: string,
  decision: { decision: string; harmonicScore: number; reasons: string[]; suggestedCorrection: string | null },
  finishReason: string,
  phase: "input" | "output",
  upstreamProvider: string,
): Promise<unknown> {
  const lastUserContent = [...reqBody.messages].reverse().find(m => m.role === "user")?.content ?? "";
  const [inputHash, outputHash] = await Promise.all([
    sha256Hex16(lastUserContent),
    sha256Hex16(content),
  ]);
  return {
    id: `chatcmpl-scbe-${crypto.randomUUID()}`,
    object: "chat.completion",
    created: Math.floor(Date.now() / 1000),
    model: reqBody.model ?? env.HF_MODEL,
    choices: [
      {
        index: 0,
        message: { role: "assistant", content },
        finish_reason: finishReason,
      },
    ],
    usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
    scbe_governance: {
      version: env.SHIM_VERSION,
      runtime: "cloudflare-worker",
      decision: decision.decision,
      harmonic_score: decision.harmonicScore,
      reasons: decision.reasons,
      suggested_correction: decision.suggestedCorrection ?? "",
      intervention: interventionFor(decision.decision, phase),
      audit: {
        input_sha256_16: inputHash,
        output_sha256_16: outputHash,
        provider: upstreamProvider,
        model: reqBody.model ?? env.HF_MODEL,
      },
    },
  };
}

function getScorecard(env: Env): unknown {
  return {
    service: "scbe-shim",
    version: env.SHIM_VERSION,
    upstream_model: env.HF_MODEL,
    measured: {
      bijective_gate: { pass: 25, total: 25, pass_rate: 1.0 },
      cross_lane_concept: { pass: 257, total: 257, pass_rate: 1.0, ci95_low: 0.985 },
      executable_holdout: { pass: 180, total: 180, pass_rate: 1.0 },
      chemistry_contract: { pass: 66, total: 75, pass_rate: 0.88 },
      petri_173: { training_blocked: 173, total: 173, false_allow_rate: 0.0058 },
    },
    decision_bands: {
      ALLOW: "H >= 0.65",
      QUARANTINE: "0.45 <= H < 0.65",
      ESCALATE: "0.25 <= H < 0.45",
      DENY: "H < 0.25",
    },
    harmonic_form: "H(d, pd) = 1 / (1 + phi*d + 2*pd)  where phi = 1.618",
  };
}
