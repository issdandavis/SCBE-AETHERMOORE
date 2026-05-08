const DEFAULT_SOURCES = [
  'duckduckgo',
  'wikipedia',
  'openalex',
  'crossref',
  'arxiv',
  'pubmed',
  'github',
  'npm',
  'hackernews',
];
const MAX_QUERY_LENGTH = 600;
const DEFAULT_LIMIT = 18;
const MAX_LIMIT = 30;
const FETCH_TIMEOUT_MS = 4500;
const USER_AGENT = 'SCBE-AETHERMOORE-agent-search/1.0 (https://aethermoore.com)';

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ ok: false, error: 'POST only' });

  let body;
  try {
    body = await readJsonBody(req);
  } catch (err) {
    return res
      .status(400)
      .json({ ok: false, error: 'invalid JSON body', detail: String(err.message || err) });
  }

  const query = String(body?.query || '').trim();
  if (!query) return res.status(400).json({ ok: false, error: 'query required' });
  if (query.length > MAX_QUERY_LENGTH) {
    return res
      .status(400)
      .json({ ok: false, error: `query exceeds ${MAX_QUERY_LENGTH} characters` });
  }

  const requestedSources = normalizeSources(body?.sources);
  const limit = clampLimit(body?.limit);
  const perSourceLimit = Math.max(
    2,
    Math.min(6, Math.ceil(limit / Math.max(1, requestedSources.length)) + 1)
  );

  const startedAt = Date.now();
  const settled = await Promise.allSettled(
    requestedSources.map(async (source) => {
      const searcher = SEARCHERS[source];
      if (!searcher) return { source, ok: false, results: [], error: 'unknown source' };
      try {
        const results = await searcher(query, perSourceLimit);
        return { source, ok: true, results };
      } catch (err) {
        return { source, ok: false, results: [], error: String(err.message || err).slice(0, 300) };
      }
    })
  );

  const sourceReports = settled.map((item, index) => {
    if (item.status === 'fulfilled') return item.value;
    return {
      source: requestedSources[index],
      ok: false,
      results: [],
      error: String(item.reason).slice(0, 300),
    };
  });
  const results = dedupeResults(sourceReports.flatMap((report) => report.results)).slice(0, limit);

  return res.status(200).json({
    ok: true,
    query,
    cost: 'zero-credit-public-sources',
    source_count: requestedSources.length,
    sources: sourceReports.map((report) => ({
      source: report.source,
      ok: report.ok,
      count: report.results.length,
      error: report.error || null,
    })),
    result_count: results.length,
    elapsed_ms: Date.now() - startedAt,
    results,
  });
};

const SEARCHERS = {
  arxiv: searchArxiv,
  crossref: searchCrossref,
  duckduckgo: searchDuckDuckGo,
  github: searchGitHub,
  hackernews: searchHackerNews,
  npm: searchNpm,
  openalex: searchOpenAlex,
  pubmed: searchPubMed,
  wikipedia: searchWikipedia,
};

function normalizeSources(value) {
  if (!value) return DEFAULT_SOURCES;
  const raw = Array.isArray(value) ? value : String(value).split(',');
  const selected = raw.map((item) => String(item).trim().toLowerCase()).filter(Boolean);
  const known = selected.filter((source) => Object.hasOwn(SEARCHERS, source));
  return known.length ? Array.from(new Set(known)) : DEFAULT_SOURCES;
}

function clampLimit(value) {
  const parsed = Number(value || DEFAULT_LIMIT);
  if (!Number.isFinite(parsed)) return DEFAULT_LIMIT;
  return Math.max(1, Math.min(MAX_LIMIT, Math.floor(parsed)));
}

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Access-Control-Max-Age', '86400');
}

async function readJsonBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  if (typeof req.body === 'string') return req.body.trim() ? JSON.parse(req.body) : {};

  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', (chunk) => {
      raw += chunk;
      if (raw.length > 4096) {
        reject(new Error('request body too large'));
        req.destroy();
      }
    });
    req.on('end', () => {
      if (!raw.trim()) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch (err) {
        reject(err);
      }
    });
    req.on('error', reject);
  });
}

async function fetchJson(url, source) {
  const response = await fetchWithTimeout(url, {
    headers: {
      Accept: 'application/json',
      'User-Agent': USER_AGENT,
    },
  });
  if (!response.ok) throw new Error(`${source} returned ${response.status}`);
  return response.json();
}

async function fetchText(url, source) {
  const response = await fetchWithTimeout(url, {
    headers: {
      Accept: 'application/atom+xml, application/xml, text/xml, text/plain',
      'User-Agent': USER_AGENT,
    },
  });
  if (!response.ok) throw new Error(`${source} returned ${response.status}`);
  return response.text();
}

async function fetchWithTimeout(url, init = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

async function searchDuckDuckGo(query, limit) {
  const url = `https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_html=1&skip_disambig=1`;
  const data = await fetchJson(url, 'duckduckgo');
  const results = [];
  if (data.AbstractURL) {
    results.push(
      normalizeResult({
        source: 'duckduckgo',
        title: data.Heading || query,
        url: data.AbstractURL,
        excerpt: data.Abstract || '',
      })
    );
  }
  flattenRelatedTopics(data.RelatedTopics || []).forEach((topic) => {
    if (topic?.FirstURL && !topic.FirstURL.startsWith('https://duckduckgo.com/c/')) {
      results.push(
        normalizeResult({
          source: 'duckduckgo',
          title: topic.Text || topic.FirstURL,
          url: topic.FirstURL,
          excerpt: topic.Text || '',
        })
      );
    }
  });
  return results.slice(0, limit);
}

async function searchWikipedia(query, limit) {
  const url = `https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(query)}&srlimit=${limit}&format=json&origin=*`;
  const data = await fetchJson(url, 'wikipedia');
  return (data.query?.search || []).map((item) =>
    normalizeResult({
      source: 'wikipedia',
      title: item.title,
      url: `https://en.wikipedia.org/wiki/${encodeURIComponent(String(item.title).replaceAll(' ', '_'))}`,
      excerpt: stripHtml(item.snippet || ''),
      published_at: null,
    })
  );
}

async function searchOpenAlex(query, limit) {
  const url = `https://api.openalex.org/works?search=${encodeURIComponent(query)}&per-page=${limit}&mailto=issdandavis@gmail.com`;
  const data = await fetchJson(url, 'openalex');
  return (data.results || []).map((work) =>
    normalizeResult({
      source: 'openalex',
      title: work.display_name,
      url: work.doi
        ? `https://doi.org/${String(work.doi).replace(/^https?:\/\/doi\.org\//, '')}`
        : work.id,
      excerpt: abstractFromInvertedIndex(work.abstract_inverted_index),
      published_at: work.publication_date || null,
      metadata: {
        cited_by_count: work.cited_by_count || 0,
        type: work.type || null,
      },
    })
  );
}

async function searchCrossref(query, limit) {
  const url = `https://api.crossref.org/works?query=${encodeURIComponent(query)}&rows=${limit}&mailto=issdandavis@gmail.com`;
  const data = await fetchJson(url, 'crossref');
  return (data.message?.items || []).map((item) =>
    normalizeResult({
      source: 'crossref',
      title: firstValue(item.title) || item.DOI || 'Crossref record',
      url: item.URL || (item.DOI ? `https://doi.org/${item.DOI}` : ''),
      excerpt: stripHtml(firstValue(item.abstract) || firstValue(item.subtitle) || ''),
      published_at: datePartsToIso(item.published?.['date-parts'] || item.created?.['date-parts']),
      metadata: {
        doi: item.DOI || null,
        publisher: item.publisher || null,
        type: item.type || null,
      },
    })
  );
}

async function searchArxiv(query, limit) {
  const url = `https://export.arxiv.org/api/query?search_query=all:${encodeURIComponent(query)}&start=0&max_results=${limit}`;
  const xml = await fetchText(url, 'arxiv');
  return xmlEntries(xml).map((entry) =>
    normalizeResult({
      source: 'arxiv',
      title: xmlValue(entry, 'title'),
      url: xmlValue(entry, 'id'),
      excerpt: xmlValue(entry, 'summary'),
      published_at: xmlValue(entry, 'published') || null,
      metadata: {
        authors: xmlAuthors(entry),
        categories: xmlCategories(entry),
      },
    })
  );
}

async function searchPubMed(query, limit) {
  const searchUrl = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=${encodeURIComponent(query)}&retmode=json&retmax=${limit}`;
  const search = await fetchJson(searchUrl, 'pubmed');
  const ids = search.esearchresult?.idlist || [];
  if (!ids.length) return [];

  const summaryUrl = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=${ids.join(',')}&retmode=json`;
  const summary = await fetchJson(summaryUrl, 'pubmed');
  return ids.map((id) => {
    const item = summary.result?.[id] || {};
    return normalizeResult({
      source: 'pubmed',
      title: item.title || `PubMed ${id}`,
      url: `https://pubmed.ncbi.nlm.nih.gov/${id}/`,
      excerpt: item.fulljournalname || item.source || '',
      published_at: item.pubdate || null,
      metadata: {
        uid: id,
        journal: item.fulljournalname || item.source || null,
      },
    });
  });
}

async function searchGitHub(query, limit) {
  const url = `https://api.github.com/search/repositories?q=${encodeURIComponent(query)}&per_page=${limit}`;
  const data = await fetchJson(url, 'github');
  return (data.items || []).map((repo) =>
    normalizeResult({
      source: 'github',
      title: repo.full_name,
      url: repo.html_url,
      excerpt: repo.description || '',
      published_at: repo.updated_at || null,
      metadata: {
        stars: repo.stargazers_count || 0,
        language: repo.language || null,
      },
    })
  );
}

async function searchNpm(query, limit) {
  const url = `https://registry.npmjs.org/-/v1/search?text=${encodeURIComponent(query)}&size=${limit}`;
  const data = await fetchJson(url, 'npm');
  return (data.objects || []).map((row) => {
    const pkg = row.package || {};
    return normalizeResult({
      source: 'npm',
      title: pkg.name,
      url: pkg.links?.npm || `https://www.npmjs.com/package/${encodeURIComponent(pkg.name || '')}`,
      excerpt: pkg.description || '',
      published_at: pkg.date || null,
      metadata: {
        version: pkg.version || null,
        score: row.score?.final || null,
      },
    });
  });
}

async function searchHackerNews(query, limit) {
  const url = `https://hn.algolia.com/api/v1/search?query=${encodeURIComponent(query)}&tags=story&hitsPerPage=${limit}`;
  const data = await fetchJson(url, 'hackernews');
  return (data.hits || []).map((hit) =>
    normalizeResult({
      source: 'hackernews',
      title: hit.title || hit.story_title || 'Hacker News item',
      url: hit.url || `https://news.ycombinator.com/item?id=${hit.objectID}`,
      excerpt: hit.author ? `by ${hit.author}` : '',
      published_at: hit.created_at || null,
      metadata: {
        points: hit.points || 0,
        comments: hit.num_comments || 0,
      },
    })
  );
}

function normalizeResult(input) {
  return {
    source: input.source,
    title: cleanText(input.title || 'Untitled').slice(0, 180),
    url: String(input.url || ''),
    excerpt: cleanText(input.excerpt || '').slice(0, 500),
    published_at: input.published_at || null,
    metadata: input.metadata || {},
  };
}

function dedupeResults(results) {
  const seen = new Set();
  const deduped = [];
  for (const result of results) {
    if (!result.url) continue;
    const key = result.url
      .toLowerCase()
      .replace(/^https?:\/\/(www\.)?/, '')
      .replace(/\/$/, '');
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(result);
  }
  return deduped;
}

function flattenRelatedTopics(topics) {
  const flat = [];
  for (const topic of topics) {
    if (Array.isArray(topic.Topics)) flat.push(...flattenRelatedTopics(topic.Topics));
    else flat.push(topic);
  }
  return flat;
}

function stripHtml(value) {
  return String(value).replace(/<[^>]*>/g, ' ');
}

function cleanText(value) {
  return stripHtml(value).replace(/\s+/g, ' ').trim();
}

function firstValue(value) {
  if (Array.isArray(value)) return value[0] || '';
  return value || '';
}

function abstractFromInvertedIndex(index) {
  if (!index || typeof index !== 'object') return '';
  const words = [];
  for (const [word, positions] of Object.entries(index)) {
    (positions || []).forEach((position) => {
      words[position] = word;
    });
  }
  return words.filter(Boolean).join(' ');
}

function datePartsToIso(parts) {
  const first = Array.isArray(parts) ? parts[0] : null;
  if (!Array.isArray(first) || !first.length) return null;
  const [year, month = 1, day = 1] = first;
  return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function xmlEntries(xml) {
  return [...String(xml).matchAll(/<entry>([\s\S]*?)<\/entry>/g)].map((match) => match[1]);
}

function xmlValue(entry, tag) {
  const match = String(entry).match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`));
  return match ? decodeXml(cleanText(match[1])) : '';
}

function xmlAuthors(entry) {
  return [...String(entry).matchAll(/<author>[\s\S]*?<name>([\s\S]*?)<\/name>[\s\S]*?<\/author>/g)]
    .map((match) => decodeXml(cleanText(match[1])))
    .filter(Boolean);
}

function xmlCategories(entry) {
  return [...String(entry).matchAll(/<category[^>]*term="([^"]+)"/g)].map((match) =>
    decodeXml(match[1])
  );
}

function decodeXml(value) {
  return String(value)
    .replaceAll('&amp;', '&')
    .replaceAll('&lt;', '<')
    .replaceAll('&gt;', '>')
    .replaceAll('&quot;', '"')
    .replaceAll('&apos;', "'");
}
