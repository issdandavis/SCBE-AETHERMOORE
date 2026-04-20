"""Generate docs/research-feed.json — global news feed covering every time zone.

Sources (all free, no credit card required):
  No-key:  HackerNews · arXiv · Reddit · GDELT · Google News RSS (regional)
           BBC · Al Jazeera · Deutsche Welle · France 24 · NHK · Times of India
  Optional keys (env vars):
    SAM_GOV_API_KEY   → DARPA/SAM.gov opportunities
    GUARDIAN_API_KEY  → The Guardian (full-text, 5k calls/day free)
    NEWSDATA_API_KEY  → Newsdata.io  (200 credits/day free)
    WORLDNEWS_API_KEY → World News API (500 calls/day free)

Runs as GitHub Actions job (research-feed.yml) every hour.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

FEED_FILE = Path("docs/research-feed.json")
UA = "SCBE-AETHERMOORE/1.0 +https://aethermoore.com research-feed-bot"
TIMEOUT = 12

AI_KW = re.compile(
    r"(?i)\b(ai|llm|gpt|model|claude|gemini|openai|machine.?learn|neural|transformer|"
    r"govern|safety|align|crypto|hyperbolic|poincare|agent|rag|inference|training|"
    r"quantum|pqc|embedding|autonomous|multi.?agent|benchmark|robot|semiconductor|chip)\b"
)

# ── RSS helper ──────────────────────────────────────────────────────────────


def _parse_rss(text: str, source: str, region: str, n: int = 6) -> list[dict]:
    """Parse an RSS/Atom feed string into item dicts."""
    items: list[dict] = []
    try:
        root = ET.fromstring(text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        # RSS 2.0
        for item in root.iter("item"):
            if len(items) >= n:
                break
            title_el = item.find("title")
            link_el = item.find("link")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            link = link_el.text.strip() if link_el is not None and link_el.text else "#"
            if title:
                items.append({"title": title[:120], "url": link, "source": source, "region": region})
        # Atom
        if not items:
            for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
                if len(items) >= n:
                    break
                title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                link = (link_el.get("href") or "").strip() if link_el is not None else "#"
                if title:
                    items.append({"title": title[:120], "url": link, "source": source, "region": region})
    except Exception as exc:
        print(f"[RSS/{source}] Parse error: {exc}")
    return items


def _fetch_rss(url: str, source: str, region: str, n: int = 6) -> list[dict]:
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        if not resp.ok:
            print(f"[RSS/{source}] HTTP {resp.status_code}")
            return []
        return _parse_rss(resp.text, source, region, n)
    except Exception as exc:
        print(f"[RSS/{source}] Fetch error: {exc}")
        return []


# ── HackerNews ──────────────────────────────────────────────────────────────


def hn_top(n: int = 8) -> list[dict]:
    """Top AI-relevant HackerNews stories (no key, UTC-8 to UTC-5 audience)."""
    try:
        ids = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        ).json()[:40]
    except Exception as exc:
        print(f"[HN] Top stories failed: {exc}")
        return []
    items: list[dict] = []
    for story_id in ids:
        if len(items) >= n:
            break
        try:
            item = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                headers={"User-Agent": UA},
                timeout=TIMEOUT,
            ).json()
            title = item.get("title", "")
            if not title or not AI_KW.search(title):
                continue
            items.append(
                {
                    "title": title[:120],
                    "url": item.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                    "source": "hn",
                    "region": "us",
                }
            )
            time.sleep(0.08)
        except Exception:
            pass
    return items


# ── arXiv ───────────────────────────────────────────────────────────────────


def arxiv_recent(n: int = 8) -> list[dict]:
    """Recent AI/safety/crypto papers from arXiv RSS (no key, global)."""
    try:
        resp = requests.get(
            "https://rss.arxiv.org/rss/cs.AI+cs.LG+cs.CR+stat.ML",
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        )
        entries = re.findall(
            r"<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>",
            resp.text,
            re.DOTALL,
        )[:n]
        return [
            {
                "title": re.sub(r"\s+", " ", t.strip())[:120],
                "url": u.strip(),
                "source": "arxiv",
                "region": "global",
            }
            for t, u in entries
            if t.strip()
        ]
    except Exception as exc:
        print(f"[arXiv] Failed: {exc}")
        return []


# ── Reddit ──────────────────────────────────────────────────────────────────


def reddit_hot(n: int = 5) -> list[dict]:
    """Hot ML posts from public Reddit JSON endpoint (no key)."""
    results: list[dict] = []
    for sub in ("MachineLearning", "artificial", "LocalLLaMA"):
        if len(results) >= n:
            break
        try:
            data = requests.get(
                f"https://www.reddit.com/r/{sub}/hot.json?limit=5",
                headers={"User-Agent": UA},
                timeout=TIMEOUT,
            ).json()
            for post in data.get("data", {}).get("children", []):
                if len(results) >= n:
                    break
                d = post.get("data", {})
                if d.get("score", 0) < 20:
                    continue
                results.append(
                    {
                        "title": d.get("title", "")[:120],
                        "url": "https://www.reddit.com" + d.get("permalink", ""),
                        "source": "reddit",
                        "region": "us",
                    }
                )
            time.sleep(0.3)
        except Exception as exc:
            print(f"[Reddit/{sub}] Failed: {exc}")
    return results


# ── GDELT ───────────────────────────────────────────────────────────────────


def gdelt_global(n: int = 10) -> list[dict]:
    """Global news from GDELT v2 (no key, 65+ languages, every time zone)."""
    queries = [
        "artificial intelligence governance safety",
        "machine learning model deployment",
        "AI regulation policy",
    ]
    seen: set[str] = set()
    items: list[dict] = []
    for q in queries:
        if len(items) >= n:
            break
        try:
            resp = requests.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    "query": q,
                    "mode": "artlist",
                    "maxrecords": 10,
                    "format": "json",
                    "timespan": "6h",
                },
                headers={"User-Agent": UA},
                timeout=TIMEOUT,
            )
            if not resp.ok:
                continue
            for art in resp.json().get("articles", []):
                if len(items) >= n:
                    break
                url = art.get("url", "")
                title = art.get("title", "").strip()
                if not title or url in seen:
                    continue
                seen.add(url)
                items.append(
                    {
                        "title": title[:120],
                        "url": url,
                        "source": "gdelt",
                        "region": _gdelt_region(art.get("sourcecountry", "")),
                        "lang": art.get("language", ""),
                    }
                )
            time.sleep(0.4)
        except Exception as exc:
            print(f"[GDELT] Query '{q}' failed: {exc}")
    return items


def _gdelt_region(country: str) -> str:
    """Map GDELT sourcecountry to a region tag."""
    c = country.upper()
    americas = {"US", "CA", "MX", "BR", "AR", "CL", "CO", "PE", "VE"}
    europe = {"GB", "DE", "FR", "IT", "ES", "NL", "BE", "PL", "SE", "NO", "FI", "CH", "AT"}
    asia = {"CN", "JP", "KR", "IN", "SG", "TH", "VN", "ID", "PH", "MY", "PK", "BD", "LK", "NP"}
    me = {"SA", "AE", "QA", "KW", "BH", "OM", "YE", "IQ", "IR", "IL", "JO", "LB", "SY", "TR"}
    africa = {"NG", "ZA", "EG", "KE", "ET", "GH", "TZ", "UG", "RW", "SN", "CM", "CI", "MZ"}
    if c in americas:
        return "us"
    if c in europe:
        return "eu"
    if c in asia:
        return "asia"
    if c in me:
        return "me"
    if c in africa:
        return "africa"
    return "global"


# ── Google News RSS (regional) ───────────────────────────────────────────────


def gnews_regional(n: int = 4) -> list[dict]:
    """Google News RSS search feeds for each major region (no key)."""
    # (edition, source_tag, region, query)
    editions = [
        ("GB:en", "gnews-eu", "eu", "AI governance safety UK Europe"),
        ("IN:en", "gnews-asia", "asia", "artificial intelligence India Asia technology"),
        ("AE:ar", "gnews-me", "me", "الذكاء الاصطناعي"),  # Arabic: "artificial intelligence"
        ("ZA:en", "gnews-af", "africa", "AI technology Africa digital"),
        ("BR:pt-419", "gnews-latam", "us", "inteligência artificial Brasil"),
        ("JP:ja", "gnews-jp", "asia", "人工知能"),  # Japanese: "artificial intelligence"
    ]
    items: list[dict] = []
    for ceid, src, region, q in editions:
        try:
            resp = requests.get(
                "https://news.google.com/rss/search",
                params={"q": q, "hl": ceid.split(":")[1], "gl": ceid.split(":")[0], "ceid": ceid},
                headers={"User-Agent": UA},
                timeout=TIMEOUT,
            )
            if not resp.ok:
                continue
            parsed = _parse_rss(resp.text, src, region, n)
            items.extend(parsed[:n])
            time.sleep(0.3)
        except Exception as exc:
            print(f"[GNews/{ceid}] Failed: {exc}")
    return items


# ── Regional RSS: BBC, Al Jazeera, DW, France24, NHK, ToI ───────────────────


def regional_rss(n_each: int = 4) -> list[dict]:
    """Regional outlet RSS feeds — no API key, covers every major time zone."""
    feeds = [
        # (url, source_tag, region)
        ("https://feeds.bbci.co.uk/news/world/rss.xml", "bbc", "eu"),
        ("https://www.aljazeera.com/xml/rss/all.xml", "aje", "me"),
        ("https://rss.dw.com/rdf/rss-en-all", "dw", "eu"),
        ("https://www.france24.com/en/rss", "f24", "eu"),
        ("https://www3.nhk.or.jp/nhkworld/data/en/news/backstory/rss.xml", "nhk", "asia"),
        ("https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "toi", "asia"),
        # CGTN English (global China perspective)
        ("https://www.cgtn.com/subscribe/rss/section/world.do", "cgtn", "asia"),
    ]
    items: list[dict] = []
    for url, src, region in feeds:
        got = _fetch_rss(url, src, region, n_each)
        items.extend(got)
        time.sleep(0.25)
    return items


# ── DARPA / SAM.gov ─────────────────────────────────────────────────────────


def darpa_opportunities(n: int = 4) -> list[dict]:
    """DARPA contract opportunities via SAM.gov (requires SAM_GOV_API_KEY)."""
    key = os.environ.get("SAM_GOV_API_KEY", "")
    if not key:
        print("[DARPA] SAM_GOV_API_KEY not set — skipping")
        return []
    try:
        resp = requests.get(
            "https://api.sam.gov/opportunities/v2/search",
            params={
                "api_key": key,
                "orgName": "DARPA",
                "limit": n,
                "postedFrom": datetime.now(timezone.utc).strftime("%m/%d/%Y"),
                "sortBy": "postedDate",
                "order": "desc",
                "status": "active",
            },
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        ).json()
        items = []
        for opp in resp.get("opportunitiesData", [])[:n]:
            items.append(
                {
                    "title": opp.get("title", "")[:120],
                    "url": f"https://sam.gov/opp/{opp.get('noticeId', '')}/view",
                    "source": "darpa",
                    "region": "us",
                }
            )
        return items
    except Exception as exc:
        print(f"[DARPA] Failed: {exc}")
        return []


# ── Optional key APIs ────────────────────────────────────────────────────────


def guardian_news(n: int = 5) -> list[dict]:
    """The Guardian API — free developer key, 5k calls/day, full article text.
    Set GUARDIAN_API_KEY env var (register free at https://open-platform.theguardian.com/).
    """
    key = os.environ.get("GUARDIAN_API_KEY", "")
    if not key:
        return []
    try:
        resp = requests.get(
            "https://content.guardianapis.com/search",
            params={
                "api-key": key,
                "q": "artificial intelligence machine learning governance",
                "section": "technology|science|world",
                "order-by": "newest",
                "page-size": n,
                "show-fields": "headline",
            },
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        ).json()
        items = []
        for result in resp.get("response", {}).get("results", [])[:n]:
            items.append(
                {
                    "title": result.get("webTitle", "")[:120],
                    "url": result.get("webUrl", "#"),
                    "source": "guardian",
                    "region": "eu",
                }
            )
        return items
    except Exception as exc:
        print(f"[Guardian] Failed: {exc}")
        return []


def newsdata_intl(n: int = 6) -> list[dict]:
    """Newsdata.io — 200 credits/day free, 89+ languages, global.
    Set NEWSDATA_API_KEY env var (register free at https://newsdata.io/).
    """
    key = os.environ.get("NEWSDATA_API_KEY", "")
    if not key:
        return []
    try:
        # One call per region using the country filter
        all_items: list[dict] = []
        region_map = [
            (["gb", "de", "fr", "it", "es"], "eu"),
            (["jp", "kr", "cn", "in", "sg"], "asia"),
            (["ae", "sa", "eg", "il", "tr"], "me"),
            (["za", "ng", "ke", "gh", "et"], "africa"),
        ]
        for countries, region in region_map:
            if len(all_items) >= n:
                break
            resp = requests.get(
                "https://newsdata.io/api/1/news",
                params={
                    "apikey": key,
                    "q": "artificial intelligence technology",
                    "country": ",".join(countries),
                    "language": "en",
                    "size": 3,
                },
                headers={"User-Agent": UA},
                timeout=TIMEOUT,
            ).json()
            for art in resp.get("results", []):
                all_items.append(
                    {
                        "title": art.get("title", "")[:120],
                        "url": art.get("link", "#"),
                        "source": "newsdata",
                        "region": region,
                    }
                )
            time.sleep(0.3)
        return all_items[:n]
    except Exception as exc:
        print(f"[Newsdata] Failed: {exc}")
        return []


def worldnews_api(n: int = 6) -> list[dict]:
    """World News API — 500 calls/day free, 210+ countries.
    Set WORLDNEWS_API_KEY env var (register free at https://worldnewsapi.com/).
    """
    key = os.environ.get("WORLDNEWS_API_KEY", "")
    if not key:
        return []
    try:
        resp = requests.get(
            "https://api.worldnewsapi.com/search-news",
            params={
                "api-key": key,
                "text": "artificial intelligence governance",
                "number": n,
                "sort": "publish-time",
                "sort-direction": "DESC",
                "language": "en",
            },
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        ).json()
        items = []
        for art in resp.get("news", [])[:n]:
            country = art.get("publish_date", "")[:2]
            items.append(
                {
                    "title": art.get("title", "")[:120],
                    "url": art.get("url", "#"),
                    "source": "worldnews",
                    "region": "global",
                }
            )
        return items
    except Exception as exc:
        print(f"[WorldNews] Failed: {exc}")
        return []


# ── Market snapshots ─────────────────────────────────────────────────────────


def _yf_chart(symbol: str, yf_sym: str | None = None) -> dict | None:
    """Fetch price + % change via Yahoo Finance chart endpoint (free, no key)."""
    yf_sym = yf_sym or symbol
    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_sym}",
            params={"interval": "1d", "range": "1d"},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
            timeout=TIMEOUT,
        )
        if not resp.ok:
            return None
        meta = resp.json().get("chart", {}).get("result", [{}])[0].get("meta", {})
        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose")
        if price is None:
            return None
        chg = round((price - prev) / prev * 100, 2) if prev else 0.0
        return {"price": round(float(price), 2), "chg": chg}
    except Exception as exc:
        print(f"[Markets] {symbol} failed: {exc}")
        return None


def market_snapshots() -> dict:
    """SPY / QQQ / NVDA / BTC via Yahoo Finance chart + CoinGecko BTC fallback."""
    result: dict = {}
    for sym, yf_sym in {"SPY": "SPY", "QQQ": "QQQ", "NVDA": "NVDA", "BTC": "BTC-USD"}.items():
        snap = _yf_chart(sym, yf_sym)
        if snap:
            result[sym] = snap
        time.sleep(0.15)
    if "BTC" not in result:
        try:
            cg = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
                headers={"User-Agent": UA},
                timeout=TIMEOUT,
            ).json()
            btc = cg.get("bitcoin", {})
            if btc.get("usd"):
                result["BTC"] = {
                    "price": round(float(btc["usd"]), 2),
                    "chg": round(float(btc.get("usd_24h_change", 0)), 2),
                }
        except Exception as exc:
            print(f"[Markets] CoinGecko BTC fallback failed: {exc}")
    return result


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    print("=== research-feed generator ===")
    items: list[dict] = []

    def run(label: str, fn, *a, **kw) -> None:
        before = len(items)
        items.extend(fn(*a, **kw))
        print(f"  [{label}] +{len(items) - before} items  (total {len(items)})")

    # No-key sources
    run("HackerNews", hn_top, 8)
    run("arXiv", arxiv_recent, 8)
    run("Reddit", reddit_hot, 5)
    run("GDELT/global", gdelt_global, 10)
    run("Google News/regional", gnews_regional, 4)
    run("Regional RSS", regional_rss, 4)

    # Optional key sources
    run("DARPA/SAM.gov", darpa_opportunities, 4)
    run("Guardian", guardian_news, 5)
    run("Newsdata.io", newsdata_intl, 6)
    run("WorldNews API", worldnews_api, 6)

    print("\nFetching market snapshots...")
    markets = market_snapshots()
    print(f"  {len(markets)} symbols: {list(markets.keys())}")

    # Deduplicate by URL
    seen_urls: set[str] = set()
    deduped = []
    for it in items:
        url = it.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(it)

    # Count by region
    region_counts: dict[str, int] = {}
    for it in deduped:
        r = it.get("region", "global")
        region_counts[r] = region_counts.get(r, 0) + 1

    feed = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "count": len(deduped),
        "regions": region_counts,
        "items": deduped,
        "markets": markets,
    }

    FEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    FEED_FILE.write_text(json.dumps(feed, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {FEED_FILE}")
    print(f"  {len(deduped)} news items  |  regions: {region_counts}")
    print(f"  {len(markets)} market symbols: {list(markets.keys())}")


if __name__ == "__main__":
    main()
