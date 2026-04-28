/**
 * Vercel serverless function: proxy search to DuckDuckGo.
 * Browser calls this, this calls DDG API (avoids CORS issues).
 *
 * POST /api/agent/search
 * Body: { query: "..." }
 * Returns: { results: [...], source: "duckduckgo" }
 */

const DDG_API = "https://api.duckduckgo.com/";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });

  const { query } = req.body || {};
  if (!query) return res.status(400).json({ error: "query required" });

  try {
    const url = `${DDG_API}?q=${encodeURIComponent(query)}&format=json&no_html=1&skip_disambig=1`;
    const resp = await fetch(url, {
      headers: { "User-Agent": "SCBE-Polly/1.0 (aethermoore.com)" },
    });
    const data = await resp.json();

    const results = [];

    if (data.AbstractURL) {
      results.push({
        title: data.Heading || query,
        url: data.AbstractURL,
        excerpt: (data.Abstract || "").substring(0, 250),
      });
    }

    (data.RelatedTopics || []).forEach((t) => {
      if (t?.FirstURL && !t.FirstURL.startsWith("https://duckduckgo.com/c/")) {
        results.push({
          title: (t.Text || "").substring(0, 100),
          url: t.FirstURL,
          excerpt: (t.Text || "").substring(0, 250),
        });
      }
      // Sub-topics
      if (t?.Topics) {
        t.Topics.forEach((sub) => {
          if (sub?.FirstURL && !sub.FirstURL.startsWith("https://duckduckgo.com/c/")) {
            results.push({
              title: (sub.Text || "").substring(0, 100),
              url: sub.FirstURL,
              excerpt: (sub.Text || "").substring(0, 250),
            });
          }
        });
      }
    });

    return res.status(200).json({
      results: results.slice(0, 8),
      source: "duckduckgo",
      query,
    });
  } catch (err) {
    return res.status(500).json({ error: String(err), source: "duckduckgo" });
  }
}
