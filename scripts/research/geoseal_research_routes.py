#!/usr/bin/env python3
"""GeoSeal governed research-source routes.

This is a routing layer, not a crawler. It gives agents compact source lanes,
evidence expectations, and safety gates for public research surfaces such as
arXiv, news, aviation telemetry, radio/broadcast archives, Starlink/public
space telemetry, Google-style search, and Tor-onion mirrors.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_REGISTRY_PATH = PROJECT_ROOT / "config" / "research" / "source_registry.json"
TRUSTED_ONION_PATH = PROJECT_ROOT / "config" / "security" / "trusted_onion_sites.json"
SCHEMA_VERSION = "scbe_geoseal_research_routes_v1"


@dataclass(frozen=True)
class ResearchSourceRoute:
    source_id: str
    title: str
    family: str
    lane: str
    access_mode: str
    authority_class: str
    safety_tier: str
    training_status: str
    redistribution_status: str
    source_url: str
    default_command: list[str]
    evidence_target: str
    gate: str
    tags: list[str]
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _registry_record(source_id: str) -> dict[str, Any]:
    records = _load_json(SOURCE_REGISTRY_PATH) or []
    for record in records:
        if record.get("source_id") == source_id:
            return record
    return {}


def _tor_tier_count() -> int:
    registry = _load_json(TRUSTED_ONION_PATH) or {}
    return len(registry.get("tiers", {}))


def build_research_routes() -> list[ResearchSourceRoute]:
    """Return governed, agent-readable research lanes."""

    arxiv = _registry_record("arxiv_public")
    return [
        ResearchSourceRoute(
            source_id="arxiv_public",
            title=arxiv.get("title", "arXiv Public Research Corpus"),
            family="academic_papers",
            lane="UM",
            access_mode="browser_or_fetch_metadata",
            authority_class=arxiv.get("authority_class", "exploratory"),
            safety_tier="ALLOW_WITH_CITATION",
            training_status=arxiv.get("training_status", "allowed_public_training"),
            redistribution_status=arxiv.get("redistribution_status", "publishable"),
            source_url=arxiv.get("source_url", "https://arxiv.org"),
            default_command=[
                "python",
                "scripts/system/browser_chain_dispatcher.py",
                "--domain",
                "arxiv.org",
                "--task",
                "research",
                "--engine",
                "playwriter",
            ],
            evidence_target="artifacts/research/arxiv/<topic>.json",
            gate="extract title, authors, abstract, categories, date, URL; cite arxiv id; prefer abs page before PDF",
            tags=["arxiv", "papers", "academic", "citation"],
            notes="Use for methods and literature review. Do not treat preprints as peer-reviewed fact.",
        ),
        ResearchSourceRoute(
            source_id="scbe_github_pages_site",
            title="SCBE-AETHERMOORE Public Website and GitHub Pages",
            family="first_party_site",
            lane="KO",
            access_mode="local_docs_or_public_site",
            authority_class="owned_public",
            safety_tier="ALLOW_OWNED_PUBLIC",
            training_status="allowed_owned_public_training",
            redistribution_status="owned_public",
            source_url="https://aethermoore.com;https://github.com/issdandavis/SCBE-AETHERMOORE/tree/main/docs",
            default_command=[
                "python",
                "scripts/system/verify_docs_publish_surface.py",
                "--root",
                "docs",
                "--require",
                "index.html",
                "--require",
                "support.html",
                "--require",
                "redteam.html",
            ],
            evidence_target="artifacts/research/scbe_site/<page>.json",
            gate="prefer local docs for exact source, then compare public site freshness; capture page path, git commit, canonical URL, and sitemap entry",
            tags=["aethermoore", "github-pages", "scbe", "website", "docs", "owned-source"],
            notes="First-party route for public product copy, demos, support, proof pages, and website-grounded RAG.",
        ),
        ResearchSourceRoute(
            source_id="public_news_clearnet",
            title="Public News Outlet Research",
            family="news",
            lane="RU",
            access_mode="browser_with_citation",
            authority_class="reported",
            safety_tier="ALLOW_WITH_CITATION",
            training_status="retrieval_summary_only",
            redistribution_status="quote_limited",
            source_url="https://www.reuters.com;https://apnews.com;https://www.bbc.com/news",
            default_command=[
                "python",
                "scripts/system/browser_chain_dispatcher.py",
                "--domain",
                "<news-domain>",
                "--task",
                "research",
                "--engine",
                "playwriter",
            ],
            evidence_target="artifacts/research/news/<story-slug>.json",
            gate="capture outlet, author if available, publication date, event date, URL, and one short compliant quote max",
            tags=["news", "reuters", "ap", "bbc", "current-events", "citation"],
            notes="Use multiple outlets for current events. Separate reported fact from analysis or opinion.",
        ),
        ResearchSourceRoute(
            source_id="flight_public_adsb",
            title="Public Flight Path and ADS-B Research",
            family="aviation",
            lane="CA",
            access_mode="public_api_or_browser",
            authority_class="telemetry",
            safety_tier="QUARANTINE_LIVE_OPERATIONS",
            training_status="retrieval_only",
            redistribution_status="restricted_context",
            source_url="https://opensky-network.org;https://globe.adsbexchange.com;https://www.flightradar24.com",
            default_command=[
                "python",
                "scripts/research/geoseal_research_routes.py",
                "--family",
                "aviation",
                "--json",
            ],
            evidence_target="artifacts/research/aviation/<query>.json",
            gate="historical/aggregate analysis allowed; do not assist evasion, interception, stalking, or live tactical tracking",
            tags=["adsb", "flight-paths", "aviation", "telemetry", "public-data"],
            notes="Route public aviation data as evidence, not instructions. Live operational exploitation is blocked.",
        ),
        ResearchSourceRoute(
            source_id="air_traffic_radio_public",
            title="Public Air Traffic Radio and Audio Research",
            family="audio_radio",
            lane="DR",
            access_mode="listen_or_transcribe_public_stream",
            authority_class="public_broadcast",
            safety_tier="QUARANTINE_LIVE_OPERATIONS",
            training_status="retrieval_summary_only",
            redistribution_status="quote_limited",
            source_url="https://www.liveatc.net;https://www.broadcastify.com",
            default_command=[
                "python",
                "scripts/research/geoseal_research_routes.py",
                "--source-id",
                "air_traffic_radio_public",
                "--json",
            ],
            evidence_target="artifacts/research/audio_radio/<station>.json",
            gate="public streams only; summarize metadata and timestamps; no live tactical assistance; route transcripts through audio governance",
            tags=["air-traffic-radio", "audio", "broadcast", "transcription", "L14"],
            notes="Designed to connect public audio into Layer 14 telemetry with strict live-operation limits.",
        ),
        ResearchSourceRoute(
            source_id="starlink_public_space_telemetry",
            title="Starlink and Public Space Telemetry",
            family="space_telemetry",
            lane="CA",
            access_mode="public_catalog",
            authority_class="telemetry",
            safety_tier="ALLOW_PUBLIC_AGGREGATE",
            training_status="allowed_public_training",
            redistribution_status="publishable_with_citation",
            source_url="https://celestrak.org;https://www.space-track.org;https://www.starlink.com",
            default_command=[
                "python",
                "scripts/research/geoseal_research_routes.py",
                "--family",
                "space_telemetry",
                "--json",
            ],
            evidence_target="artifacts/research/space_telemetry/<catalog>.json",
            gate="prefer public orbital catalogs and aggregate availability; no targeting, interference, or unauthorized access",
            tags=["starlink", "satellite", "tle", "celestrak", "space-track"],
            notes="Space-Track requires authorized account terms; CelesTrak is the public-first route.",
        ),
        ResearchSourceRoute(
            source_id="public_broadcast_archives",
            title="Public Broadcast and Archive Research",
            family="broadcast_archives",
            lane="AV",
            access_mode="browser_or_public_api",
            authority_class="public_archive",
            safety_tier="ALLOW_WITH_RIGHTS_CHECK",
            training_status="retrieval_summary_only",
            redistribution_status="rights_dependent",
            source_url="https://archive.org;https://publicfiles.fcc.gov;https://www.noaa.gov",
            default_command=[
                "python",
                "scripts/research/geoseal_research_routes.py",
                "--family",
                "broadcast_archives",
                "--json",
            ],
            evidence_target="artifacts/research/broadcast/<source>.json",
            gate="record source rights, date, station/program, and citation; do not copy full copyrighted broadcasts",
            tags=["broadcast", "internet-archive", "fcc", "noaa", "public-files"],
            notes="Useful for public communications, weather radio, regulatory filings, and media-history evidence.",
        ),
        ResearchSourceRoute(
            source_id="google_public_discovery",
            title="Google Public Discovery Lane",
            family="search",
            lane="KO",
            access_mode="manual_search_or_api",
            authority_class="discovery",
            safety_tier="DISCOVERY_ONLY",
            training_status="retrieval_only",
            redistribution_status="source_dependent",
            source_url="https://www.google.com;https://scholar.google.com;https://news.google.com",
            default_command=[
                "python",
                "scripts/research/geoseal_research_routes.py",
                "--family",
                "search",
                "--json",
            ],
            evidence_target="artifacts/research/search/<query>.json",
            gate="Google is a discovery index, not an authority; agents must open and cite primary sources",
            tags=["google", "scholar", "news", "discovery", "search"],
            notes="Use to find sources, then route the source itself through its proper lane.",
        ),
        ResearchSourceRoute(
            source_id="tor_trusted_onion_research",
            title="Trusted Tor Onion Research",
            family="tor",
            lane="RU",
            access_mode="tor_sweeper_double_sandbox",
            authority_class="quarantined",
            safety_tier="QUARANTINE_BY_DEFAULT",
            training_status="retrieval_only_until_allowed",
            redistribution_status="blocked_until_review",
            source_url="config/security/trusted_onion_sites.json",
            default_command=[
                "python",
                "scripts/apollo/tor_sweeper.py",
                "sweep",
                "--tier",
                "NEWS_AND_JOURNALISM",
            ],
            evidence_target="artifacts/tor_sweeps/*.json",
            gate=f"trusted registry only ({_tor_tier_count()} tiers); never access blocked categories; scrub secrets; owner ALLOW required before training",
            tags=["tor", "onion", "trusted-sites", "quarantine", "apollo"],
            notes="Do not search arbitrary onion links from agent output. Use the trusted registry and tor_sweeper dry-run/check first.",
        ),
        ResearchSourceRoute(
            source_id="official_public_data_apis",
            title="Official Public Data APIs",
            family="public_data_api",
            lane="UM",
            access_mode="api_with_terms",
            authority_class="operational",
            safety_tier="ALLOW_WITH_TERMS",
            training_status="allowed_public_training_if_license_allows",
            redistribution_status="license_dependent",
            source_url="https://www.data.gov;https://api.weather.gov;https://www.sec.gov/edgar/sec-api-documentation",
            default_command=[
                "python",
                "scripts/research/geoseal_research_routes.py",
                "--family",
                "public_data_api",
                "--json",
            ],
            evidence_target="artifacts/research/public_data/<dataset>.json",
            gate="verify terms, rate limits, schema, timestamp, and license before storing or training",
            tags=["data.gov", "noaa", "sec", "api", "public-data"],
            notes="Good default for low-risk factual grounding when an official source exists.",
        ),
    ]


def _matches(route: ResearchSourceRoute, query: str) -> bool:
    text = " ".join([route.source_id, route.title, route.family, *route.tags, route.notes]).lower()
    tokens = set(re.findall(r"[a-z0-9]+", text))
    terms = re.findall(r"[a-z0-9]+", query.lower())
    return all(term in tokens for term in terms)


def build_research_route_matrix(
    *,
    family: str | None = None,
    source_id: str | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    routes = build_research_routes()
    if family:
        routes = [route for route in routes if route.family == family]
    if source_id:
        routes = [route for route in routes if route.source_id == source_id]
    if query:
        routes = [route for route in routes if _matches(route, query)]

    families: dict[str, int] = {}
    safety_tiers: dict[str, int] = {}
    for route in routes:
        families[route.family] = families.get(route.family, 0) + 1
        safety_tiers[route.safety_tier] = safety_tiers.get(route.safety_tier, 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "route_count": len(routes),
        "families": families,
        "safety_tiers": safety_tiers,
        "routes": [route.to_dict() for route in routes],
        "global_policy": [
            "Prefer primary sources and official APIs when available.",
            "Current events require date/event-date capture and cross-source checks.",
            "Live aviation, radio, satellite, and Tor lanes are not training data until governance explicitly promotes them.",
            "Tor routes are trusted-registry only and QUARANTINE by default.",
            "Discovery engines such as Google route to primary sources; they are not authority sources themselves.",
        ],
    }


def render_routes_text(matrix: dict[str, Any]) -> str:
    lines = [
        "GeoSeal Research Source Routes",
        "=" * 34,
        f"Routes: {matrix['route_count']} | Families: {len(matrix['families'])}",
        "",
    ]
    for route in matrix["routes"]:
        command = " ".join(route["default_command"])
        if len(command) > 100:
            command = f"{command[:97]}..."
        lines.append(
            f"- {route['source_id']} [{route['family']}] lane={route['lane']} "
            f"safety={route['safety_tier']}"
        )
        lines.append(f"  gate: {route['gate']}")
        lines.append(f"  run:  {command}")
    lines.append("")
    lines.extend(f"- {note}" for note in matrix["global_policy"])
    return "\n".join(lines)


def route_families(routes: Iterable[ResearchSourceRoute] | None = None) -> list[str]:
    return sorted({route.family for route in (routes or build_research_routes())})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=route_families(), default=None)
    parser.add_argument("--source-id", default=None)
    parser.add_argument("--query", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    matrix = build_research_route_matrix(family=args.family, source_id=args.source_id, query=args.query)
    if args.json:
        print(json.dumps(matrix, indent=2, sort_keys=True))
    else:
        print(render_routes_text(matrix))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
