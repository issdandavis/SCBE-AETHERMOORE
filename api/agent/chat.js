/**
 * Vercel serverless function: proxy chat to HuggingFace Inference API.
 * Solves CORS — browser calls this, this calls HF.
 *
 * POST /api/agent/chat
 * Body: { message: "...", history: [...] }
 * Returns: { text: "...", model: "...", provider: "huggingface" }
 */

const HF_MODEL = "Qwen/Qwen2.5-72B-Instruct";
const HF_URL = `https://router.huggingface.co/hf-inference/models/${HF_MODEL}/v1/chat/completions`;
const HF_TOKEN = process.env.HF_TOKEN || "";

const SYSTEM_PROMPT =
  "You are Polly, the AI assistant for AetherMoore — an AI safety and governance framework " +
  "using hyperbolic geometry with a 14-layer security pipeline. The framework makes adversarial " +
  "AI behavior exponentially expensive using Poincaré ball geometry. Be helpful, concise, and " +
  "accurate. If asked about SCBE, explain the core innovation: adversarial intent costs " +
  "exponentially more the further it drifts from safe operation.";

export default async function handler(req, res) {
  // CORS
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "POST only" });
  }

  const { message, history } = req.body || {};
  if (!message) {
    return res.status(400).json({ error: "message required" });
  }

  const messages = [{ role: "system", content: SYSTEM_PROMPT }];

  if (Array.isArray(history)) {
    history.slice(-6).forEach((h) => {
      if (h.role && h.content) {
        messages.push({ role: h.role, content: h.content });
      }
    });
  }

  messages.push({ role: "user", content: message });

  const headers = { "Content-Type": "application/json" };
  if (HF_TOKEN) {
    headers["Authorization"] = `Bearer ${HF_TOKEN}`;
  }

  try {
    const hfResp = await fetch(HF_URL, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: HF_MODEL,
        messages,
        max_tokens: 512,
      }),
    });

    if (!hfResp.ok) {
      const errText = await hfResp.text();
      return res.status(502).json({
        error: "HuggingFace error",
        detail: errText.substring(0, 200),
        provider: "huggingface",
      });
    }

    const data = await hfResp.json();
    const text =
      data.choices?.[0]?.message?.content || "No response from model.";

    return res.status(200).json({
      text,
      model: HF_MODEL,
      provider: "huggingface",
    });
  } catch (err) {
    return res.status(500).json({
      error: String(err),
      provider: "huggingface",
    });
  }
}
