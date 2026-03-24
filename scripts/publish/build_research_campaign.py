#!/usr/bin/env python3
"""Build a code-backed research article campaign for SCBE publishing lanes."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTICLE_PLATFORM_ROOT = REPO_ROOT / "content" / "articles" / "platforms" / "generated"
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "publish_campaigns"
DEFAULT_NOTE_PATH = REPO_ROOT / "notes" / "round-table" / "2026-03-21-research-publishing-campaign.md"
CANONICAL_REPO_URL = "https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main"

PLATFORM_CADENCE_MINUTES = {
    "github": 240,
    "huggingface": 240,
    "devto": 240,
    "linkedin": 180,
    "medium": 360,
    "substack": 720,
    "reddit": 180,
    "bluesky": 120,
    "mastodon": 120,
}


@dataclass(frozen=True)
class ClaimSpec:
    text: str
    source: str
    anchor: str


@dataclass(frozen=True)
class ArticleSpec:
    slug: str
    path: str
    tags: tuple[str, ...]
    series: str
    code_refs: tuple[str, ...]
    claims: tuple[ClaimSpec, ...]


DEFAULT_ARTICLES: tuple[ArticleSpec, ...] = (
    ArticleSpec(
        slug="governed-cli-product-surface",
        path="content/articles/research/2026-03-21-governed-cli-product-surface.md",
        tags=("ai", "cli", "governance", "multiagent"),
        series="SCBE Research Notes",
        code_refs=(
            "scbe.py",
            "scripts/scbe-system-cli.py",
            "docs/FAST_ACCESS_GUIDE.md",
            "docs/guides/CORE_SYSTEM_MAP.md",
        ),
        claims=(
            ClaimSpec(
                text="The live stack already documents the CLI as the fastest path into the system.",
                source="docs/FAST_ACCESS_GUIDE.md",
                anchor="Use this first when you want the fastest path to the right command or guide.",
            ),
            ClaimSpec(
                text="Flow planning is already exposed as a first-class operator command.",
                source="docs/FAST_ACCESS_GUIDE.md",
                anchor='python scripts/scbe-system-cli.py flow plan --task "..."',
            ),
            ClaimSpec(
                text="The core map already treats the control plane as a canonical runtime lane.",
                source="docs/guides/CORE_SYSTEM_MAP.md",
                anchor="Control plane | Local operator shell, unified CLI, npm entrypoints",
            ),
        ),
    ),
    ArticleSpec(
        slug="protected-corpus-before-training",
        path="content/articles/research/2026-03-21-protected-corpus-before-training.md",
        tags=("privacy", "syntheticdata", "security", "huggingface"),
        series="SCBE Research Notes",
        code_refs=(
            "docs/research/2026-03-21-synthetic-data-privacy-blueprint.md",
            "scripts/build_protected_corpus.py",
            "scripts/privacy_leakage_audit.py",
            "src/security/privacy_token_vault.py",
        ),
        claims=(
            ClaimSpec(
                text="The repo already states that keyed reversibility is pseudonymization, not de-identification.",
                source="docs/research/2026-03-21-synthetic-data-privacy-blueprint.md",
                anchor="If the data can be decoded with a key, it is not de-identified. It is pseudonymized or tokenized.",
            ),
            ClaimSpec(
                text="The protected-corpus builder is intentionally bounded and includes a non-productive loop exit.",
                source="scripts/build_protected_corpus.py",
                anchor="The pipeline is intentionally bounded: it keeps a novelty-aware cycle guard so",
            ),
            ClaimSpec(
                text="The token vault is implemented as a Windows-first reversible pseudonymization layer.",
                source="src/security/privacy_token_vault.py",
                anchor="Windows-first reversible token vault for privacy-preserving pseudonymization.",
            ),
        ),
    ),
    ArticleSpec(
        slug="programmatic-hf-training-lane",
        path="content/articles/research/2026-03-21-programmatic-hf-training-lane.md",
        tags=("huggingface", "training", "datasets", "mlops"),
        series="SCBE Research Notes",
        code_refs=(
            "scripts/programmatic_hf_training.py",
            "scripts/build_offload_sft_records.py",
            "src/training/auto_ledger.py",
            "training/ledgered/sft_ledgered_clean.jsonl",
        ),
        claims=(
            ClaimSpec(
                text="The repo already has a single governed entrypoint for local build, audit, packaging, and optional publish.",
                source="scripts/programmatic_hf_training.py",
                anchor="This script consolidates the current training surfaces into one governed lane:",
            ),
            ClaimSpec(
                text="The HF training orchestrator already emits a deterministic dataset package before any remote publish.",
                source="scripts/programmatic_hf_training.py",
                anchor="Emit a deterministic Hugging Face dataset package.",
            ),
            ClaimSpec(
                text="The offload merger already produces a deduplicated SFT staging file.",
                source="scripts/build_offload_sft_records.py",
                anchor="Build a deduplicated SFT staging file from multi-agent offload training rows.",
            ),
            ClaimSpec(
                text="The ledger pipeline already audits, tags, and emits clean training data with metadata.",
                source="src/training/auto_ledger.py",
                anchor="Takes raw SFT pairs, audits them, encodes through the 21D PHDM embedding,",
            ),
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a multi-site research publishing campaign.")
    parser.add_argument("--campaign-id", default="", help="Optional explicit campaign id")
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--platform-root", default=str(ARTICLE_PLATFORM_ROOT))
    parser.add_argument("--note-path", default=str(DEFAULT_NOTE_PATH))
    return parser.parse_args()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip()
    return text


def _extract_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled Article"


def _extract_abstract(text: str) -> str:
    body = _strip_frontmatter(text)
    lines = body.splitlines()
    in_abstract = False
    chunks: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if stripped.lower() == "## abstract":
                in_abstract = True
                continue
            if in_abstract:
                break
        if in_abstract:
            if stripped:
                chunks.append(stripped)
    if chunks:
        return " ".join(chunks)

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    for paragraph in paragraphs:
        if not paragraph.startswith("#"):
            return re.sub(r"\s+", " ", paragraph).strip()
    return ""


def _relative_string(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _repo_url(relative_path: str) -> str:
    return f"{CANONICAL_REPO_URL}/{relative_path}"


def _command_block(article_slug: str) -> str:
    commands = {
        "governed-cli-product-surface": [
            "python scbe.py doctor --json",
            'python scbe.py flow plan --task "ship a governed browser workflow"',
            'python scbe.py workflow styleize --name nightly-ops --trigger workflow_dispatch --step "Smoke::python scbe.py selftest"',
        ],
        "protected-corpus-before-training": [
            "python scripts/build_protected_corpus.py --help",
            "python scripts/privacy_leakage_audit.py --help",
            "python scbe.py colab review --json",
        ],
        "programmatic-hf-training-lane": [
            "python scripts/programmatic_hf_training.py --dry-run",
            "python scripts/programmatic_hf_training.py --dry-run --publish-dataset",
            "python -m src.training.auto_ledger",
        ],
    }
    rows = commands.get(article_slug, [])
    if not rows:
        return ""
    return "```bash\n" + "\n".join(rows) + "\n```"


def _render_code_refs(code_refs: tuple[str, ...]) -> str:
    lines = ["## Code References", ""]
    for relative_path in code_refs:
        lines.append(f"- `{relative_path}`")
        lines.append(f"  Public repo link: {_repo_url(relative_path)}")
    return "\n".join(lines)


def _render_longform(article_text: str, spec: ArticleSpec, summary: str) -> str:
    body = _strip_frontmatter(article_text).strip()
    footer = [
        "",
        "---",
        "",
        "## Why this article is code-backed",
        "",
        summary,
        "",
        _render_code_refs(spec.code_refs),
        "",
        "## Repro Commands",
        "",
        _command_block(spec.slug),
    ]
    return body + "\n" + "\n".join(footer).rstrip() + "\n"


def _render_linkedin(title: str, summary: str, spec: ArticleSpec) -> str:
    refs = ", ".join(f"`{path}`" for path in spec.code_refs[:3])
    return (
        f"# {title}\n\n"
        f"{summary}\n\n"
        "Why this matters:\n"
        "- SCBE is moving from planning docs to executable operator surfaces.\n"
        "- The work is tied to real commands, guides, and tests already in the repo.\n"
        "- The point is governed execution, not vague agent theater.\n\n"
        f"Code refs: {refs}\n\n"
        "If you are building bounded multi-agent systems, this is the shape I think is actually shippable.\n"
    )


def _render_reddit(title: str, summary: str, spec: ArticleSpec) -> str:
    refs = "\n".join(f"- `{path}`" for path in spec.code_refs[:4])
    return (
        f"# {title}\n\n"
        f"{summary}\n\n"
        "I am building this in public in one repo, and the claim I care about is simple: the code should exist before the article exists.\n\n"
        "Repo-backed references:\n"
        f"{refs}\n\n"
        "If you were evaluating this as a workflow/runtime instead of a paper idea, what would you test first?\n"
    )


def _render_short_thread(title: str, summary: str, spec: ArticleSpec, *, site: str) -> str:
    lines = [
        f"# {title} ({site})",
        "",
        "## 1/4",
        summary,
        "",
        "## 2/4",
        "This is grounded in repo paths and live operator commands, not only architecture prose.",
        "",
        "## 3/4",
        "Key files:",
    ]
    for relative_path in spec.code_refs[:3]:
        lines.append(f"- `{relative_path}`")
    lines.extend(
        [
            "",
            "## 4/4",
            "The real test is whether the workflow can be replayed, audited, and promoted into training data.",
            "",
        ]
    )
    return "\n".join(lines)


def _site_targets(title: str, spec: ArticleSpec) -> list[dict[str, Any]]:
    return [
        {
            "platform": "github",
            "site": "github",
            "target": {"owner": "issdandavis", "repo": "SCBE-AETHERMOORE", "category": "General"},
        },
        {
            "platform": "huggingface",
            "site": "huggingface_model",
            "target": {"repo_id": "issdandavis/phdm-21d-embedding", "repo_type": "model"},
        },
        {
            "platform": "huggingface",
            "site": "huggingface_dataset",
            "target": {"repo_id": "issdandavis/scbe-aethermoore-knowledge-base", "repo_type": "dataset"},
        },
        {"platform": "devto", "site": "devto", "target": {"tags": list(spec.tags), "series": spec.series}},
        {"platform": "linkedin", "site": "linkedin", "target": {}},
        {"platform": "medium", "site": "medium", "target": {}},
        {"platform": "substack", "site": "substack", "target": {}},
        {"platform": "reddit", "site": "reddit_machinelearning", "target": {"subreddit": "MachineLearning"}},
        {"platform": "bluesky", "site": "bluesky", "target": {}},
        {"platform": "mastodon", "site": "mastodon", "target": {}},
    ]


def _render_for_site(site: str, article_text: str, title: str, summary: str, spec: ArticleSpec) -> str:
    if site in {"github", "huggingface_model", "huggingface_dataset", "devto", "medium", "substack"}:
        return _render_longform(article_text, spec, summary)
    if site == "linkedin":
        return _render_linkedin(title, summary, spec)
    if site == "reddit_machinelearning":
        return _render_reddit(title, summary, spec)
    if site in {"bluesky", "mastodon"}:
        return _render_short_thread(title, summary, spec, site=site)
    return _render_longform(article_text, spec, summary)


def _validate_claim(source_root: Path, claim: ClaimSpec) -> dict[str, Any]:
    source_path = (source_root / claim.source).resolve()
    if not source_path.exists():
        return {
            "text": claim.text,
            "source": claim.source,
            "anchor": claim.anchor,
            "pass": False,
            "reasons": [f"source_not_found:{claim.source}"],
        }
    text = _read_text(source_path)
    passed = claim.anchor.lower() in text.lower()
    reasons: list[str] = [] if passed else [f"anchor_not_found:{claim.anchor}"]
    return {
        "text": claim.text,
        "source": claim.source,
        "anchor": claim.anchor,
        "pass": passed,
        "reasons": reasons,
    }


def build_claim_report(posts: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    failed = 0
    checked = 0
    for post in posts:
        for claim in post["claims"]:
            checked += 1
            row = _validate_claim(REPO_ROOT, ClaimSpec(**claim))
            row["post_id"] = post["id"]
            rows.append(row)
            if not row["pass"]:
                failed += 1
    return {
        "summary": {
            "posts": len(posts),
            "claims_checked": checked,
            "claims_failed": failed,
            "pass": failed == 0,
        },
        "rows": rows,
    }


def build_dispatch_plan(campaign_id: str, posts: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    channel_offsets: dict[str, int] = defaultdict(int)
    events: list[dict[str, Any]] = []
    for post in posts:
        platform = post["platform"]
        offset = channel_offsets[platform]
        publish_at = now + timedelta(minutes=offset + 5)
        cadence = PLATFORM_CADENCE_MINUTES.get(platform, 180)
        channel_offsets[platform] += cadence
        events.append(
            {
                "ts": publish_at.isoformat().replace("+00:00", "Z"),
                "type": "publish",
                "campaign_id": campaign_id,
                "channel": platform,
                "post_id": post["id"],
                "payload": {
                    "title": post["title"],
                    "site": post["site"],
                    "content_file": post["content_file"],
                },
            }
        )
        events.append(
            {
                "ts": (publish_at + timedelta(minutes=20)).isoformat().replace("+00:00", "Z"),
                "type": "metric_check",
                "campaign_id": campaign_id,
                "channel": platform,
                "post_id": post["id"],
                "payload": {"window_minutes": 20},
            }
        )
    return {
        "campaign_id": campaign_id,
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "events": events,
        "summary": {
            "event_count": len(events),
            "publish_count": len([event for event in events if event["type"] == "publish"]),
            "platform_count": len({post["platform"] for post in posts}),
        },
    }


def build_note(
    campaign_id: str, posts: list[dict[str, Any]], claim_report: dict[str, Any], dispatch_plan: dict[str, Any]
) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for post in posts:
        grouped[post["article_slug"]].append(post)

    lines = [
        "# Research Publishing Campaign - March 21, 2026",
        "",
        f"Campaign id: `{campaign_id}`",
        "",
        "## What shipped",
        f"- Articles: {len(grouped)}",
        f"- Post packages: {len(posts)}",
        f"- Platforms covered: {len({post['platform'] for post in posts})}",
        f"- Claim gate pass: {claim_report['summary']['pass']}",
        f"- Claims checked: {claim_report['summary']['claims_checked']}",
        f"- Dispatch publish events: {dispatch_plan['summary']['publish_count']}",
        "",
        "## Articles",
    ]
    for article_slug, article_posts in sorted(grouped.items()):
        first = article_posts[0]
        lines.append(f"- `{article_slug}` :: {first['title']}")
        lines.append(f"  Source: `{first['source_article']}`")
        lines.append("  Sites: " + ", ".join(sorted(post["site"] for post in article_posts)))
    lines.extend(
        [
            "",
            "## Commands",
            "```bash",
            "python scripts/publish/build_research_campaign.py",
            "python scripts/publish/post_all.py --campaign-posts artifacts/publish_campaigns/latest/campaign_posts.json --dry-run",
            "```",
            "",
            "## Why this matters",
            "- The article lane is now tied to real repo sources and explicit anchors.",
            "- Every generated post package can be claim-checked before distribution.",
            "- The dispatch plan is structured enough to feed the publishing autopilot later.",
            "",
        ]
    )
    return "\n".join(lines)


def build_campaign(
    *,
    campaign_id: str,
    article_specs: tuple[ArticleSpec, ...] = DEFAULT_ARTICLES,
    artifact_root: Path = ARTIFACT_ROOT,
    platform_root: Path = ARTICLE_PLATFORM_ROOT,
    note_path: Path = DEFAULT_NOTE_PATH,
) -> dict[str, Any]:
    artifact_dir = artifact_root / campaign_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    platform_dir = platform_root / campaign_id
    platform_dir.mkdir(parents=True, exist_ok=True)

    latest_dir = artifact_root / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)

    posts: list[dict[str, Any]] = []
    article_rows: list[dict[str, Any]] = []

    for spec in article_specs:
        article_path = REPO_ROOT / spec.path
        article_text = _read_text(article_path)
        title = _extract_title(article_text)
        summary = _extract_abstract(article_text)
        article_rows.append(
            {
                "slug": spec.slug,
                "title": title,
                "path": spec.path,
                "summary": summary,
                "tags": list(spec.tags),
                "code_refs": list(spec.code_refs),
            }
        )

        for target in _site_targets(title, spec):
            site = target["site"]
            platform = target["platform"]
            content = _render_for_site(site, article_text, title, summary, spec)
            extension = "txt" if site in {"bluesky", "mastodon"} else "md"
            output_dir = platform_dir / site
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{spec.slug}.{extension}"
            output_path.write_text(content, encoding="utf-8")

            posts.append(
                {
                    "id": f"{spec.slug}-{site}",
                    "article_slug": spec.slug,
                    "title": title,
                    "summary": summary,
                    "platform": platform,
                    "site": site,
                    "source_article": spec.path,
                    "content_file": _relative_string(output_path),
                    "claims": [
                        {"text": claim.text, "source": claim.source, "anchor": claim.anchor} for claim in spec.claims
                    ],
                    "code_refs": list(spec.code_refs),
                    "tags": list(spec.tags),
                    "series": spec.series,
                    "target": target["target"],
                    "cta": "Read the repo-backed article and inspect the code paths directly.",
                    "offer_path": spec.path,
                }
            )

    claim_report = build_claim_report(posts)
    dispatch_plan = build_dispatch_plan(campaign_id, posts)
    note_text = build_note(campaign_id, posts, claim_report, dispatch_plan)

    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(note_text, encoding="utf-8")

    campaign_manifest = {
        "campaign_id": campaign_id,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "article_count": len(article_rows),
        "post_count": len(posts),
        "platforms": sorted({post["platform"] for post in posts}),
        "sites": sorted({post["site"] for post in posts}),
        "articles": article_rows,
        "note_path": _relative_string(note_path),
        "platform_root": _relative_string(platform_dir),
    }
    campaign_payload = {
        "campaign_id": campaign_id,
        "run_hours": 12,
        "heartbeat_minutes": 15,
        "channels": [
            {"name": platform, "cadence_minutes": PLATFORM_CADENCE_MINUTES.get(platform, 180), "enabled": True}
            for platform in sorted({post["platform"] for post in posts})
        ],
        "posts": posts,
    }
    posts_payload = {"campaign_id": campaign_id, "posts": posts}

    outputs = {
        "campaign_manifest.json": campaign_manifest,
        "campaign.json": campaign_payload,
        "campaign_posts.json": posts_payload,
        "claim_gate_report.json": claim_report,
        "dispatch_plan.json": dispatch_plan,
        "repo_obsidian_note.json": {"note_path": _relative_string(note_path)},
    }
    for name, payload in outputs.items():
        (artifact_dir / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        (latest_dir / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    (artifact_dir / "repo_obsidian_note.md").write_text(note_text, encoding="utf-8")
    (latest_dir / "repo_obsidian_note.md").write_text(note_text, encoding="utf-8")

    return {
        "campaign_id": campaign_id,
        "artifact_dir": _relative_string(artifact_dir),
        "platform_dir": _relative_string(platform_dir),
        "note_path": _relative_string(note_path),
        "article_count": len(article_rows),
        "post_count": len(posts),
        "platform_count": len(campaign_manifest["platforms"]),
        "claim_gate_pass": claim_report["summary"]["pass"],
    }


def main() -> int:
    args = parse_args()
    campaign_id = args.campaign_id.strip() or datetime.now(timezone.utc).strftime("research-campaign-%Y%m%dT%H%M%SZ")
    result = build_campaign(
        campaign_id=campaign_id,
        artifact_root=Path(args.artifact_root),
        platform_root=Path(args.platform_root),
        note_path=Path(args.note_path),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
