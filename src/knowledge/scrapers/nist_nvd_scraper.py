"""
NIST NVD Scraper — pulls CVE vulnerability data from the National Vulnerability Database.

Free API, key optional (higher rate limit with key). Rate limit: 5 req/30sec without key.
"""

import time
import json
from urllib.request import urlopen, Request
from urllib.parse import urlencode

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from src.knowledge.funnel import KnowledgeChunk

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
RATE_LIMIT = 6.5  # 5 requests per 30 sec without API key


def search_cves(keyword: str, limit: int = 20) -> list[KnowledgeChunk]:
    """Search NVD for CVEs by keyword."""
    params = {
        "keywordSearch": keyword,
        "resultsPerPage": limit,
    }
    url = f"{NVD_API}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "AetherBrowser/1.0 (SCBE-AETHERMOORE research)"})

    with urlopen(req, timeout=60) as response:
        data = json.loads(response.read())

    chunks = []
    for vuln in data.get("vulnerabilities", []):
        cve = vuln.get("cve", {})
        cve_id = cve.get("id", "Unknown")
        published = cve.get("published", "")

        descriptions = cve.get("descriptions", [])
        en_desc = ""
        for d in descriptions:
            if d.get("lang") == "en":
                en_desc = d.get("value", "")
                break

        # Extract CVSS score
        metrics = cve.get("metrics", {})
        cvss_score = 0.0
        severity = "UNKNOWN"
        for metric_version in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
            metric_list = metrics.get(metric_version, [])
            if metric_list:
                cvss_data = metric_list[0].get("cvssData", {})
                cvss_score = cvss_data.get("baseScore", 0.0)
                severity = cvss_data.get("baseSeverity", "UNKNOWN")
                break

        # Extract references
        refs = cve.get("references", [])
        ref_urls = [r.get("url", "") for r in refs[:3]]

        # Extract weaknesses (CWE)
        weaknesses = cve.get("weaknesses", [])
        cwes = []
        for w in weaknesses:
            for d in w.get("description", []):
                if d.get("lang") == "en":
                    cwes.append(d.get("value", ""))

        chunk = KnowledgeChunk(
            id="",
            source="nist_nvd",
            category="security",
            title=f"{cve_id} — CVSS {cvss_score} ({severity})",
            content=f"# {cve_id}\n\nCVSS Score: {cvss_score} ({severity})\nPublished: {published}\nCWEs: {', '.join(cwes)}\n\n{en_desc}\n\nReferences: {', '.join(ref_urls)}",
            url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            metadata={
                "cve_id": cve_id,
                "cvss_score": cvss_score,
                "severity": severity,
                "cwes": cwes,
                "published": published,
            },
        )
        chunks.append(chunk)

    return chunks


NVD_RESEARCH_QUERIES = [
    "cryptographic",
    "post-quantum",
    "machine learning adversarial",
    "browser remote code execution",
    "authentication bypass",
    "blockchain vulnerability",
    "AI model injection",
    "supply chain",
]


def scrape_all_queries(max_per_query: int = 10) -> list[KnowledgeChunk]:
    """Run all SCBE-relevant NVD queries."""
    all_chunks = []
    for query in NVD_RESEARCH_QUERIES:
        print(f"  Searching NIST NVD for '{query}'...")
        try:
            chunks = search_cves(query, limit=max_per_query)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(RATE_LIMIT)
    return all_chunks


if __name__ == "__main__":
    chunks = scrape_all_queries(max_per_query=5)
    print(f"\nFound {len(chunks)} CVEs from NIST NVD")
    for c in chunks[:5]:
        print(f"  [{c.category}] {c.title[:80]}")
