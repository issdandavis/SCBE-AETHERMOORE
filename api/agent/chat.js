const HF_MODEL = "Qwen/Qwen2.5-72B-Instruct";
const HF_URL = `https://router.huggingface.co/hf-inference/models/${HF_MODEL}/v1/chat/completions`;

const SYSTEM_PROMPT =
  "You are Polly, the AI assistant for AetherMoore — an AI safety and governance framework " +
  "using hyperbolic geometry with a 14-layer security pipeline. The framework makes adversarial " +
  "AI behavior exponentially expensive using Poincare ball geometry. Be helpful, concise, and " +
  "accurate. If asked about SCBE, explain the core innovation: adversarial intent costs " +
  "exponentially more the further it drifts from safe operation.";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });

  let body;
  try {
    body = await readJsonBody(req);
  } catch (err) {
    return res.status(400).json({ error: "invalid JSON body", detail: String(err.message || err) });
  }
  const { message, history } = body || {};
  if (!message) return res.status(400).json({ error: "message required" });

  const messages = [{ role: "system", content: SYSTEM_PROMPT }];
  if (Array.isArray(history)) {
    history.slice(-6).forEach((h) => {
      if (h.role && h.content) messages.push({ role: h.role, content: h.content });
    });
  }
  messages.push({ role: "user", content: message });

  const headers = { "Content-Type": "application/json" };
  if (process.env.HF_TOKEN) headers["Authorization"] = `Bearer ${process.env.HF_TOKEN}`;

  try {
    const hfResp = await fetch(HF_URL, {
      method: "POST", headers,
      body: JSON.stringify({ model: HF_MODEL, messages, max_tokens: 512 }),
    });
    if (!hfResp.ok) {
      return res.status(502).json({ error: "HF error", detail: (await hfResp.text()).substring(0, 200) });
    }
    const data = await hfResp.json();
    return res.status(200).json({
      text: data.choices?.[0]?.message?.content || "No response.",
      model: HF_MODEL, provider: "huggingface",
    });
  } catch (err) {
    return res.status(500).json({ error: String(err) });
  }
}

async function readJsonBody(req) {
  if (req.body && typeof req.body === "object") return req.body;
  if (typeof req.body === "string") return req.body.trim() ? JSON.parse(req.body) : {};

  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
      if (raw.length > 8192) {
        reject(new Error("request body too large"));
        req.destroy();
      }
    });
    req.on("end", () => {
      if (!raw.trim()) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch (err) {
        reject(err);
      }
    });
    req.on("error", reject);
  });
}
