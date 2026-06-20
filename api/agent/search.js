'use strict';

const { readJsonBody, sendJson, setCors } = require('../_agent_common');

const DEFAULT_TIMEOUT_MS = 4500;
const MAX_RESULTS = 12;

function normalizeResult(row) {
  if (!row || !row.url) return null;
  const title = String(row.title || row.url).trim();
  const url = String(row.url || '').trim();
  const excerpt = String(row.excerpt || '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 500);
  const source = String(row.source || 'unknown').trim();
  if (!title || !url || !/^https?:\/\//i.test(url)) return null;
  return { title, url, excerpt, source };
}

function dedupeResults(rows, maxResults = MAX_RESULTS) {
  const seen = new Set();
  const out = [];
  for (const row of rows) {
    const normalized = normalizeResult(row);
    if (!normalized) continue;
    const key = normalized.url.replace(/#.*$/, '').replace(/\/+$/, '').toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(normalized);
    if (out.length >= maxResults) break;
  }
  return out;
}

async function fetchJson(url, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      headers: {
        Accept: 'application/json',
        'User-Agent': 'SCBE-Aethermoor-AgentSearch/1.0',
      },
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`http_${response.status}`);
    return response.json();
  } finally {
    clearTimeout(timer);
  }
}

async function fetchText(url, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      headers: {
        Accept: 'application/xml,text/xml,text/plain,*/*',
        'User-Agent': 'SCBE-Aethermoor-AgentSearch/1.0',
      },
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`http_${response.status}`);
    return response.text();
  } finally {
    clearTimeout(timer);
  }
}

function stripTags(value) {
  return String(value || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

async function searchDuckDuckGo(query) {
  const data = await fetchJson(
    `https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_html=1&skip_disambig=1`
  );
  const rows = [];
  if (data.AbstractURL) {
    rows.push({
      title: data.Heading || query,
      url: data.AbstractURL,
      excerpt: data.Abstract || '',
      source: 'duckduckgo',
    });
  }
  for (const topic of data.RelatedTopics || []) {
    if (
      topic &&
      topic.FirstURL &&
      !String(topic.FirstURL).startsWith('https://duckduckgo.com/c/')
    ) {
      rows.push({
        title: String(topic.Text || '').slice(0, 120) || topic.FirstURL,
        url: topic.FirstURL,
        excerpt: topic.Text || '',
        source: 'duckduckgo',
      });
    }
  }
  return rows;
}

async function searchWikipedia(query) {
  const data = await fetchJson(
    `https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=4&srsearch=${encodeURIComponent(
      query
    )}`
  );
  return ((data.query && data.query.search) || []).map((row) => ({
    title: row.title,
    url: `https://en.wikipedia.org/wiki/${encodeURIComponent(String(row.title || '').replace(/\s+/g, '_'))}`,
    excerpt: stripTags(row.snippet),
    source: 'wikipedia',
  }));
}

async function searchOpenAlex(query) {
  const data = await fetchJson(
    `https://api.openalex.org/works?per-page=4&search=${encodeURIComponent(query)}`
  );
  return (data.results || []).map((row) => ({
    title: row.display_name,
    url: row.doi
      ? `https://doi.org/${String(row.doi).replace(/^https?:\/\/doi.org\//i, '')}`
      : row.id,
    excerpt: row.publication_year ? `Publication year: ${row.publication_year}` : '',
    source: 'openalex',
  }));
}

async function searchCrossref(query) {
  const data = await fetchJson(
    `https://api.crossref.org/works?rows=4&query=${encodeURIComponent(query)}`
  );
  return ((data.message || {}).items || []).map((row) => ({
    title: Array.isArray(row.title) ? row.title[0] : row.title,
    url: row.URL || (row.DOI ? `https://doi.org/${row.DOI}` : ''),
    excerpt: row.publisher || '',
    source: 'crossref',
  }));
}

async function searchNpm(query) {
  const data = await fetchJson(
    `https://registry.npmjs.org/-/v1/search?size=4&text=${encodeURIComponent(query)}`
  );
  return (data.objects || []).map((row) => {
    const pkg = row.package || {};
    return {
      title: pkg.name,
      url: pkg.links && (pkg.links.npm || pkg.links.repository),
      excerpt: pkg.description || '',
      source: 'npm',
    };
  });
}

async function searchHackerNews(query) {
  const data = await fetchJson(
    `https://hn.algolia.com/api/v1/search?hitsPerPage=4&query=${encodeURIComponent(query)}`
  );
  return (data.hits || []).map((row) => ({
    title: row.title || row.story_title,
    url: row.url || (row.objectID ? `https://news.ycombinator.com/item?id=${row.objectID}` : ''),
    excerpt: row.author ? `HN by ${row.author}` : '',
    source: 'hackernews',
  }));
}

async function searchArxiv(query) {
  const xml = await fetchText(
    `https://export.arxiv.org/api/query?max_results=4&search_query=all:${encodeURIComponent(query)}`
  );
  const entries = xml.split('<entry>').slice(1);
  return entries.map((entry) => {
    const title = stripTags((entry.match(/<title>([\s\S]*?)<\/title>/) || [])[1]);
    const id = stripTags((entry.match(/<id>([\s\S]*?)<\/id>/) || [])[1]);
    const summary = stripTags((entry.match(/<summary>([\s\S]*?)<\/summary>/) || [])[1]);
    return { title, url: id, excerpt: summary, source: 'arxiv' };
  });
}

async function searchPubMed(query) {
  const search = await fetchJson(
    `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=4&term=${encodeURIComponent(
      query
    )}`
  );
  const ids = ((search.esearchresult || {}).idlist || []).filter(Boolean);
  if (!ids.length) return [];
  const summary = await fetchJson(
    `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=${ids.join(',')}`
  );
  const result = (summary && summary.result) || {};
  return ids.map((id) => {
    const row = result[id] || {};
    return {
      title: row.title || `PubMed ${id}`,
      url: `https://pubmed.ncbi.nlm.nih.gov/${id}/`,
      excerpt: row.fulljournalname ? `${row.fulljournalname} ${row.pubdate || ''}`.trim() : '',
      source: 'pubmed',
    };
  });
}

async function searchGitHub(query) {
  const data = await fetchJson(
    `https://api.github.com/search/repositories?per_page=4&q=${encodeURIComponent(query)}`
  );
  return (data.items || []).map((row) => ({
    title: row.full_name || row.name,
    url: row.html_url,
    excerpt: row.description || '',
    source: 'github',
  }));
}

const SOURCE_FNS = {
  duckduckgo: searchDuckDuckGo,
  wikipedia: searchWikipedia,
  openalex: searchOpenAlex,
  crossref: searchCrossref,
  arxiv: searchArxiv,
  pubmed: searchPubMed,
  github: searchGitHub,
  npm: searchNpm,
  hackernews: searchHackerNews,
};

async function searchAll(query, options = {}) {
  const sources =
    Array.isArray(options.sources) && options.sources.length
      ? options.sources
      : Object.keys(SOURCE_FNS);
  const settled = await Promise.allSettled(
    sources
      .filter((name) => SOURCE_FNS[name])
      .map(async (name) => ({ source: name, results: await SOURCE_FNS[name](query) }))
  );
  const sourceStatus = {};
  const rows = [];
  for (const item of settled) {
    if (item.status === 'fulfilled') {
      sourceStatus[item.value.source] = { ok: true, count: item.value.results.length };
      rows.push(...item.value.results);
    } else {
      const reason = String(
        item.reason && item.reason.message ? item.reason.message : item.reason
      ).slice(0, 160);
      sourceStatus.unknown = sourceStatus.unknown || [];
      sourceStatus.unknown.push({ ok: false, error: reason });
    }
  }
  const results = dedupeResults(rows, Number(options.maxResults || MAX_RESULTS));
  const okSourceCount = Object.values(sourceStatus).filter(
    (status) => status && status.ok === true
  ).length;
  return {
    query,
    cost: 'zero-credit-public-sources',
    source_count: okSourceCount,
    result_count: results.length,
    source_status: sourceStatus,
    results,
  };
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();

  let body = {};
  if (req.method === 'GET') {
    body = {
      query: req.query && (req.query.query || req.query.q),
      max_results: req.query && (req.query.max_results || req.query.maxResults),
      sources:
        req.query && typeof req.query.sources === 'string'
          ? req.query.sources.split(',').map((item) => item.trim())
          : undefined,
    };
  } else if (req.method === 'POST') {
    try {
      body = await readJsonBody(req);
    } catch (error) {
      return sendJson(res, 400, {
        ok: false,
        error: 'invalid JSON body',
        detail: String(error.message || error),
      });
    }
  } else {
    return sendJson(res, 405, { ok: false, error: 'GET or POST only' });
  }

  const query = String((body && body.query) || '').trim();
  if (!query) return sendJson(res, 400, { ok: false, error: 'query required' });
  if (query.length > 300) return sendJson(res, 400, { ok: false, error: 'query too long' });

  const data = await searchAll(query, {
    sources: Array.isArray(body.sources) ? body.sources : undefined,
    maxResults: body.max_results || body.maxResults,
  });
  return sendJson(res, 200, { ok: true, ...data });
};

module.exports._private = {
  dedupeResults,
  normalizeResult,
  searchAll,
  stripTags,
};
