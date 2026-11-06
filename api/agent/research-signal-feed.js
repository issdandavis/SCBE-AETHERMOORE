'use strict';

const CACHE_SECONDS = 600;
const FETCH_TIMEOUT_MS = 6500;
const MAX_BODY_BYTES = 1_500_000;
const USER_AGENT = 'AetherMoore-Research-Signal/1.0 (https://aethermoore.com/research-signal)';

const NAMED_ENTITIES = {
  amp: '&',
  apos: "'",
  gt: '>',
  lt: '<',
  nbsp: ' ',
  quot: '"',
};

function decodeEntities(value) {
  return String(value || '').replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (match, entity) => {
    if (entity[0] === '#') {
      const radix = entity[1].toLowerCase() === 'x' ? 16 : 10;
      const digits = radix === 16 ? entity.slice(2) : entity.slice(1);
      const codePoint = Number.parseInt(digits, radix);
      return Number.isFinite(codePoint) ? String.fromCodePoint(codePoint) : match;
    }
    return Object.prototype.hasOwnProperty.call(NAMED_ENTITIES, entity.toLowerCase())
      ? NAMED_ENTITIES[entity.toLowerCase()]
      : match;
  });
}

function cleanText(value, maxLength = 360) {
  const withoutCdata = String(value || '').replace(/^\s*<!\[CDATA\[|\]\]>\s*$/g, '');
  const withoutActiveContent = withoutCdata.replace(
    /<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi,
    ' '
  );
  const text = decodeEntities(withoutActiveContent.replace(/<[^>]*>/g, ' '))
    .replace(/\s+/g, ' ')
    .trim();
  return text.length > maxLength ? `${text.slice(0, maxLength - 1).trim()}…` : text;
}

function safeUrl(value) {
  try {
    const url = new URL(decodeEntities(String(value || '').trim()));
    if (url.protocol === 'http:' && /(^|\.)arxiv\.org$/i.test(url.hostname)) {
      url.protocol = 'https:';
    }
    if (url.protocol !== 'https:') return '';
    return url.toString();
  } catch (_error) {
    return '';
  }
}

function tagValue(block, tagName) {
  const escaped = tagName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = String(block).match(
    new RegExp(`<${escaped}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${escaped}>`, 'i')
  );
  return match ? match[1] : '';
}

function tagBlocks(xml, tagName) {
  const escaped = tagName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return [
    ...String(xml).matchAll(
      new RegExp(`<${escaped}(?:\\s[^>]*)?>[\\s\\S]*?<\\/${escaped}>`, 'gi')
    ),
  ].map((match) => match[0]);
}

function attributeValue(tag, attribute) {
  const escaped = attribute.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = String(tag).match(new RegExp(`${escaped}=["']([^"']+)["']`, 'i'));
  return match ? decodeEntities(match[1]) : '';
}

function normalizeDate(value) {
  const parsed = Date.parse(String(value || ''));
  return Number.isFinite(parsed) ? new Date(parsed).toISOString() : '';
}

function parseRss(xml) {
  return tagBlocks(xml, 'item')
    .map((block) => {
      const title = cleanText(tagValue(block, 'title'), 220);
      const link = safeUrl(tagValue(block, 'link') || tagValue(block, 'guid'));
      return {
        title,
        url: link,
        published_at: normalizeDate(
          tagValue(block, 'pubDate') || tagValue(block, 'dc:date') || tagValue(block, 'date')
        ),
        summary: cleanText(
          tagValue(block, 'description') ||
            tagValue(block, 'content:encoded') ||
            tagValue(block, 'summary')
        ),
      };
    })
    .filter((item) => item.title && item.url);
}

function parseAtom(xml) {
  return tagBlocks(xml, 'entry')
    .map((block) => {
      const linkTags = [...block.matchAll(/<link(?:\s[^>]*)?\/?\s*>/gi)].map(
        (match) => match[0]
      );
      const alternate =
        linkTags.find((tag) => !attributeValue(tag, 'rel') || attributeValue(tag, 'rel') === 'alternate') ||
        linkTags[0] ||
        '';
      const author = cleanText(tagValue(tagValue(block, 'author'), 'name'), 100);
      return {
        title: cleanText(tagValue(block, 'title'), 220),
        url: safeUrl(attributeValue(alternate, 'href') || tagValue(block, 'id')),
        published_at: normalizeDate(tagValue(block, 'published') || tagValue(block, 'updated')),
        summary: cleanText(tagValue(block, 'summary') || tagValue(block, 'content')),
        byline: author,
      };
    })
    .filter((item) => item.title && item.url && item.title.toLowerCase() !== 'error');
}

function datePartsToIso(parts) {
  if (!Array.isArray(parts) || !parts.length) return '';
  const [year, month = 1, day = 1] = parts.map(Number);
  if (!year) return '';
  return normalizeDate(`${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}T00:00:00Z`);
}

function parseCrossref(payload) {
  const items = payload && payload.message && Array.isArray(payload.message.items)
    ? payload.message.items
    : [];
  return items
    .map((item) => {
      const authors = Array.isArray(item.author)
        ? item.author
            .slice(0, 3)
            .map((author) => [author.given, author.family].filter(Boolean).join(' '))
            .filter(Boolean)
            .join(', ')
        : '';
      const venue = Array.isArray(item['container-title']) ? item['container-title'][0] : '';
      return {
        title: cleanText(Array.isArray(item.title) ? item.title[0] : item.title, 220),
        url: safeUrl(item.URL || (item.DOI ? `https://doi.org/${item.DOI}` : '')),
        published_at:
          datePartsToIso(item.published && item.published['date-parts'] && item.published['date-parts'][0]) ||
          normalizeDate(item.indexed && item.indexed['date-time']),
        summary: cleanText([venue, authors].filter(Boolean).join(' · '), 280),
        byline: authors,
      };
    })
    .filter((item) => item.title && item.url);
}

function sourceDefinitions(now = new Date()) {
  const fromDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10);
  const arxivQuery = new URL('https://export.arxiv.org/api/query');
  arxivQuery.searchParams.set('search_query', 'cat:cs.AI OR cat:cs.CR OR cat:cs.RO');
  arxivQuery.searchParams.set('start', '0');
  arxivQuery.searchParams.set('max_results', '16');
  arxivQuery.searchParams.set('sortBy', 'submittedDate');
  arxivQuery.searchParams.set('sortOrder', 'descending');

  const crossrefQuery = new URL('https://api.crossref.org/v1/works');
  crossrefQuery.searchParams.set(
    'query.bibliographic',
    'artificial intelligence governance cybersecurity robotics space materials'
  );
  crossrefQuery.searchParams.set('filter', `from-pub-date:${fromDate}`);
  crossrefQuery.searchParams.set('rows', '40');
  crossrefQuery.searchParams.set(
    'select',
    'DOI,title,author,URL,published,container-title,indexed'
  );

  return [
    {
      id: 'bbc-world',
      name: 'BBC World',
      region: 'Global desk · United Kingdom',
      channel: 'world',
      url: 'https://feeds.bbci.co.uk/news/world/rss.xml',
      parse: parseRss,
    },
    {
      id: 'al-jazeera',
      name: 'Al Jazeera',
      region: 'Global desk · Qatar',
      channel: 'world',
      url: 'https://www.aljazeera.com/xml/rss/all.xml',
      parse: parseRss,
    },
    {
      id: 'le-monde',
      name: 'Le Monde International',
      region: 'International desk · France',
      channel: 'world',
      url: 'https://www.lemonde.fr/en/international/rss_full.xml',
      parse: parseRss,
    },
    {
      id: 'npr-world',
      name: 'NPR World',
      region: 'Global desk · United States',
      channel: 'world',
      url: 'https://feeds.npr.org/1004/rss.xml',
      parse: parseRss,
    },
    {
      id: 'nasa',
      name: 'NASA',
      region: 'Primary source · Space',
      channel: 'space',
      url: 'https://www.nasa.gov/feed/',
      parse: parseRss,
    },
    {
      id: 'arxiv',
      name: 'arXiv',
      region: 'Preprints · AI, security, robotics',
      channel: 'research',
      url: arxivQuery.toString(),
      parse: parseAtom,
    },
    {
      id: 'crossref',
      name: 'Crossref',
      region: 'Scholarly metadata · Worldwide',
      channel: 'research',
      url: crossrefQuery.toString(),
      parse: parseCrossref,
      json: true,
      published_after: `${fromDate}T00:00:00Z`,
      published_before: new Date(now.getTime() + 2 * 24 * 60 * 60 * 1000).toISOString(),
    },
  ];
}

async function fetchBody(url, fetchImpl = fetch) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const response = await fetchImpl(url, {
      headers: { Accept: 'application/json, application/atom+xml, application/rss+xml, text/xml', 'User-Agent': USER_AGENT },
      redirect: 'follow',
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`upstream_${response.status}`);
    const buffer = Buffer.from(await response.arrayBuffer());
    if (buffer.length > MAX_BODY_BYTES) throw new Error('upstream_body_too_large');
    return buffer.toString('utf8');
  } finally {
    clearTimeout(timer);
  }
}

async function fetchSource(source, fetchImpl = fetch) {
  const body = await fetchBody(source.url, fetchImpl);
  const parsed = source.json ? source.parse(JSON.parse(body)) : source.parse(body);
  const bounded = parsed.filter((item) => {
    const published = Date.parse(item.published_at || '');
    if (source.published_after && (!Number.isFinite(published) || published < Date.parse(source.published_after))) {
      return false;
    }
    if (source.published_before && (!Number.isFinite(published) || published > Date.parse(source.published_before))) {
      return false;
    }
    return true;
  });
  return bounded.slice(0, 16).map((item, index) => ({
    id: `${source.id}-${index}-${Buffer.from(item.url).toString('base64url').slice(0, 14)}`,
    source_id: source.id,
    source: source.name,
    source_context: source.region,
    channel: source.channel,
    title: item.title,
    url: item.url,
    published_at: item.published_at,
    summary: item.summary || '',
    byline: item.byline || '',
  }));
}

function deduplicate(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = item.title.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function xmlEscape(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function renderRss(items, generatedAt) {
  const rows = items
    .slice(0, 60)
    .map(
      (item) => `    <item>\n      <title>${xmlEscape(item.title)}</title>\n      <link>${xmlEscape(item.url)}</link>\n      <guid isPermaLink="false">${xmlEscape(item.id)}</guid>\n      <pubDate>${xmlEscape(item.published_at ? new Date(item.published_at).toUTCString() : generatedAt)}</pubDate>\n      <category>${xmlEscape(item.channel)}</category>\n      <source>${xmlEscape(item.source)}</source>\n      <description>${xmlEscape(item.summary)}</description>\n    </item>`
    )
    .join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n  <channel>\n    <title>AetherMoore Research Signal</title>\n    <link>https://aethermoore.com/research-signal</link>\n    <description>World reporting, primary research metadata, and space updates. Every item links to its original source.</description>\n    <lastBuildDate>${xmlEscape(new Date(generatedAt).toUTCString())}</lastBuildDate>\n${rows}\n  </channel>\n</rss>\n`;
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.setHeader('Allow', 'GET, HEAD');
    return res.status(405).json({ ok: false, error: 'method_not_allowed' });
  }

  const sources = sourceDefinitions();
  const settled = await Promise.allSettled(sources.map((source) => fetchSource(source)));
  const status = settled.map((result, index) => ({
    id: sources[index].id,
    name: sources[index].name,
    channel: sources[index].channel,
    ok: result.status === 'fulfilled',
    count: result.status === 'fulfilled' ? result.value.length : 0,
    error:
      result.status === 'rejected'
        ? cleanText(result.reason && result.reason.message ? result.reason.message : 'unavailable', 80)
        : '',
  }));
  const items = deduplicate(
    settled.flatMap((result) => (result.status === 'fulfilled' ? result.value : []))
  )
    .sort((a, b) => Date.parse(b.published_at || 0) - Date.parse(a.published_at || 0));
  const generatedAt = new Date().toISOString();
  const queryFormat = Array.isArray(req.query && req.query.format)
    ? req.query.format[0]
    : req.query && req.query.format;

  res.setHeader('Cache-Control', `public, max-age=60, s-maxage=${CACHE_SECONDS}, stale-while-revalidate=3600`);
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (String(queryFormat || '').toLowerCase() === 'rss') {
    res.setHeader('Content-Type', 'application/rss+xml; charset=utf-8');
    return res.status(200).send(req.method === 'HEAD' ? '' : renderRss(items, generatedAt));
  }

  return res.status(200).json(
    req.method === 'HEAD'
      ? {}
      : {
          ok: items.length > 0,
          schema: 'aethermoore-research-signal-v1',
          generated_at: generatedAt,
          refresh_after_seconds: CACHE_SECONDS,
          status,
          total: items.length,
          items,
        }
  );
};

module.exports._test = {
  cleanText,
  parseAtom,
  parseCrossref,
  parseRss,
  renderRss,
  safeUrl,
  sourceDefinitions,
};
