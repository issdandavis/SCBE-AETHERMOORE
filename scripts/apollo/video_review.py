"""Apollo Video Review — Score your own uploaded videos.

Pulls video metadata + transcript, scores quality across dimensions,
flags issues, suggests improvements.

Usage:
    python scripts/apollo/video_review.py review --video-id PTT5R9TEhds
    python scripts/apollo/video_review.py review-all
    python scripts/apollo/video_review.py report
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse as _urlparse

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

REPORT_DIR = ROOT / "artifacts" / "apollo" / "video_reviews"
PLAN_FILES = [
    REPORT_DIR / "youtube_description_updates_2026-03-26.json",
    REPORT_DIR / "youtube_title_tag_updates_2026-03-26.json",
]


@dataclass
class VideoScore:
    video_id: str
    title: str
    duration_seconds: int
    transcript_length: int
    scores: dict  # dimension -> 0-10
    issues: List[str]
    suggestions: List[str]
    overall: float
    reviewed_at: str = ""

    def __post_init__(self):
        if not self.reviewed_at:
            self.reviewed_at = datetime.datetime.now().isoformat()


def parse_duration(iso_duration: str) -> int:
    """Parse ISO 8601 duration or 'Xm Ys' to seconds."""
    m = re.match(r"(\d+)m\s*(\d+)s", iso_duration)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if m:
        h = int(m.group(1) or 0)
        mins = int(m.group(2) or 0)
        s = int(m.group(3) or 0)
        return h * 3600 + mins * 60 + s
    return 0


def score_title(title: str) -> tuple[int, list, list]:
    """Score video title quality (0-10).

    Rewards:
      - Structured separators (pipe, dash, colon)
      - Series format (Ch., Part, Ep.)
      - Searchable/curiosity words (how, why, what, secret, hidden, ...)
      - Hook-first: title opens with a question or dramatic statement
      - Pipe separator format ("Hook | Series Ch.X")
      - Mobile-friendly length (under 55 chars)
    """
    issues, suggestions = [], []
    score = 4  # baseline

    # --- Length checks ---
    if len(title) < 15:
        issues.append("Title too short")
        score -= 2
    elif len(title) > 80:
        issues.append("Title may be too long for mobile display")
        score -= 1
    elif len(title) <= 55:
        score += 1  # mobile-friendly length

    # --- Structural separators ---
    if "|" in title:
        score += 1  # pipe separator (preferred hook|series format)
    if "--" in title or ":" in title:
        score += 1  # structured title with dash or colon

    # --- Series format ---
    if any(w in title.lower() for w in ["chapter", "ch.", "ep.", "part"]):
        score += 1  # series format

    # --- Searchable / curiosity / emotional words ---
    curiosity_words = [
        "how", "why", "what", "secret", "hidden", "every", "never",
        "broke", "hacked", "tutorial", "guide", "explained",
    ]
    matched_curiosity = [w for w in curiosity_words if w in title.lower()]
    if matched_curiosity:
        score += 1  # at least one curiosity/emotional word

    # --- Hook-first: title starts with a question or dramatic statement ---
    title_stripped = title.strip()
    first_segment = title_stripped.split("|")[0].strip() if "|" in title_stripped else title_stripped
    hook_first = False
    # Question hook: opens with interrogative or ends segment with '?'
    if first_segment.endswith("?") or re.match(r"(?i)^(how|why|what|who|when|where|can|is|are|do|does|will|did)\b", first_segment):
        hook_first = True
    # Dramatic statement hook: starts with a strong verb phrase or personal pronoun
    if re.match(r"(?i)^(he |she |they |i |we |it |the |this |every |no one |never |stop |watch |meet |inside )", first_segment):
        hook_first = True
    if hook_first:
        score += 1  # hook-first title

    # --- ALL CAPS penalty ---
    if title == title.upper() and len(title) > 5:
        issues.append("ALL CAPS title")
        score -= 2

    # --- Suggestions for low-scoring titles ---
    if not hook_first:
        suggestions.append("Start with a question or dramatic hook for higher CTR")
    if "|" not in title:
        suggestions.append("Consider pipe format: 'Hook | Series Ch.X'")

    return min(10, max(0, score)), issues, suggestions


def score_description(description: str) -> tuple[int, list, list]:
    """Score video description quality (0-10)."""
    issues, suggestions = [], []
    score = 5

    if len(description) < 50:
        issues.append("Description too short")
        suggestions.append("Add 2-3 sentences explaining what the video covers")
        score -= 3
    elif len(description) > 200:
        score += 2  # substantial description

    # Use urlparse for proper URL detection instead of substring matching
    url_candidates = re.findall(r'https?://[^\s\'"<>]+', description)
    if any(_urlparse(u).netloc for u in url_candidates):
        score += 1  # has valid links

    if "#" in description:
        score += 1  # has hashtags

    if "patent" in description.lower() or "USPTO" in description:
        score += 1  # references IP

    if "Maps to:" in description:
        score += 1  # maps to code (unique to SCBE)

    return min(10, max(0, score)), issues, suggestions


def score_transcript(transcript: str, duration_s: int) -> tuple[int, list, list]:
    """Score transcript quality (0-10)."""
    issues, suggestions = [], []
    score = 5

    if not transcript:
        return 0, ["No transcript available"], ["Add captions/subtitles"]

    words = transcript.split()
    wpm = len(words) / max(duration_s / 60, 0.5)

    if wpm < 80:
        issues.append(f"Speaking rate low ({wpm:.0f} WPM)")
        suggestions.append("Consider tighter editing or faster narration")
        score -= 1
    elif wpm > 180:
        issues.append(f"Speaking rate very fast ({wpm:.0f} WPM)")
        suggestions.append("Slow down for comprehension")
        score -= 1
    else:
        score += 1  # good pace

    # Vocabulary richness
    unique_words = len(set(w.lower() for w in words))
    richness = unique_words / max(len(words), 1)
    if richness > 0.4:
        score += 1  # diverse vocabulary
    elif richness < 0.2:
        issues.append("Low vocabulary diversity — may be repetitive")

    # Technical depth
    tech_terms = sum(1 for w in words if w.lower() in {
        "algorithm", "protocol", "encryption", "authentication", "governance",
        "topology", "manifold", "hyperbolic", "byzantine", "consensus",
        "phi", "fibonacci", "ternary", "entropy", "harmonic",
        "poincare", "tensor", "eigenvalue", "gradient", "vector",
    })
    if tech_terms > 5:
        score += 2  # technically dense

    # Length appropriateness
    if len(transcript) > 3000:
        score += 1  # substantial content

    return min(10, max(0, score)), issues, suggestions


def score_tags(tags: list) -> tuple[int, list, list]:
    """Score tag quality (0-10)."""
    issues, suggestions = [], []
    score = 5

    if not tags:
        return 2, ["No tags"], ["Add 5-10 relevant tags"]

    if len(tags) < 3:
        issues.append("Too few tags")
        suggestions.append("Add more tags for discoverability")
        score -= 2
    elif len(tags) >= 8:
        score += 2

    core_tags = {"ai safety", "scbe", "aethermoore", "issac daniel davis"}
    has_brand = any(t.lower() in core_tags for t in tags)
    if has_brand:
        score += 1
    else:
        suggestions.append("Add brand tags: SCBE, Aethermoore, AI Safety")

    return min(10, max(0, score)), issues, suggestions


def review_video(video_data: dict, transcript: Optional[str] = None) -> VideoScore:
    """Full review of a video."""
    vid_id = video_data.get("id", "?")
    title = video_data.get("title", "")
    desc = video_data.get("description", "")
    tags = video_data.get("tags", [])
    duration = parse_duration(video_data.get("duration", "0m 0s"))

    all_issues, all_suggestions = [], []

    title_score, ti, ts = score_title(title)
    all_issues.extend(ti); all_suggestions.extend(ts)

    desc_score, di, ds = score_description(desc)
    all_issues.extend(di); all_suggestions.extend(ds)

    trans_score, tri, trs = score_transcript(transcript or "", duration)
    all_issues.extend(tri); all_suggestions.extend(trs)

    tag_score, tai, tas = score_tags(tags)
    all_issues.extend(tai); all_suggestions.extend(tas)

    scores = {
        "title": title_score,
        "description": desc_score,
        "transcript": trans_score,
        "tags": tag_score,
    }
    overall = sum(scores.values()) / len(scores)

    return VideoScore(
        video_id=vid_id,
        title=title,
        duration_seconds=duration,
        transcript_length=len(transcript or ""),
        scores=scores,
        issues=all_issues,
        suggestions=all_suggestions,
        overall=round(overall, 1),
    )


def print_review(vs: VideoScore):
    """Print a video review."""
    grade = "A" if vs.overall >= 8 else "B" if vs.overall >= 6 else "C" if vs.overall >= 4 else "D"
    print(f"\n  {vs.title} ({vs.video_id})")
    print(f"  Grade: {grade} ({vs.overall}/10)")
    print(f"  Duration: {vs.duration_seconds // 60}m {vs.duration_seconds % 60}s | Transcript: {vs.transcript_length} chars")
    for dim, score in vs.scores.items():
        bar = "#" * score + "." * (10 - score)
        print(f"    {dim:12s} [{bar}] {score}/10")
    if vs.issues:
        print(f"  Issues:")
        for i in vs.issues:
            print(f"    ! {i}")
    if vs.suggestions:
        print(f"  Suggestions:")
        for s in vs.suggestions:
            print(f"    > {s}")


def main():
    parser = argparse.ArgumentParser(description="Apollo Video Review")
    sub = parser.add_subparsers(dest="command")

    r = sub.add_parser("review", help="Review a single video")
    r.add_argument("--video-id", required=True)

    sub.add_parser("review-all", help="Review all own channel videos")
    sub.add_parser("report", help="Show saved review reports")

    args = parser.parse_args()

    if args.command == "review-all":
        # Use YouTube MCP data if available, otherwise hardcoded
        videos = [
            {"id": "PTT5R9TEhds", "title": "The Six Tongues Protocol -- Ch.1: Protocol Handshake", "duration": "3m 46s", "tags": ["AI Safety", "SCBE", "Isekai", "Issac Daniel Davis"], "description": "Marcus Chen, a systems engineer, falls through reality into Aethermoor..."},
            {"id": "JMDyvza6c4w", "title": "The Six Tongues Protocol -- Ch.2: The Language Barrier", "duration": "6m 5s", "tags": ["AI Safety", "SCBE", "Isekai", "Cryptography"], "description": "Marcus discovers the Six Sacred Tongues..."},
            {"id": "M3-lY7-RdrI", "title": "The Six Tongues Protocol -- Ch.3: Hyperbolic Consequences", "duration": "7m 37s", "tags": ["AI Safety", "SCBE", "Isekai", "Hyperbolic Geometry"], "description": "Marcus learns that trust in Aethermoor isn't binary..."},
            {"id": "Ry5yDARTUYc", "title": "The Six Tongues Protocol -- Ch.4: The Swarm Beneath", "duration": "8m 53s", "tags": ["AI Safety", "SCBE", "Isekai", "Distributed Systems"], "description": "Marcus discovers the Echoes..."},
            {"id": "4SE-YZItxO8", "title": "The Six Tongues Protocol -- Ch.5: Intent and Integrity", "duration": "5m 36s", "tags": ["AI Safety", "SCBE", "Isekai", "Security Engineering"], "description": "Marcus has his breakthrough..."},
            {"id": "tkUmJsk0fKM", "title": "The Six Tongues Protocol -- Ch.6: The Harmonic Wall", "duration": "8m 1s", "tags": ["AI Safety", "SCBE", "Isekai"], "description": "Marcus's training escalates into real protocol work..."},
            {"id": "ROYbRIY90Pc", "title": "The Six Tongues Protocol -- Ch.7: Fleet Dynamics", "duration": "7m 10s", "tags": ["AI Safety", "SCBE", "Isekai", "Swarm Intelligence"], "description": "Marcus pilots his first drone swarm..."},
            {"id": "Oo7sT_dJ7eQ", "title": "The Six Tongues Protocol -- Ch.8: Rogue Signatures", "duration": "7m 38s", "tags": ["AI Safety", "SCBE", "Isekai", "Security"], "description": "Polly introduces Marcus to rogue agents..."},
            {"id": "HhGA0aXpTAg", "title": "The Everweave Protocol: How a DnD Campaign Became an AI Safety Framework", "duration": "4m 45s", "tags": ["AI Safety", "Aethermoore", "DnD", "Everweave"], "description": "X Thread: The Everweave Protocol..."},
        ]

        for plan_path in PLAN_FILES:
            if not plan_path.exists():
                continue
            planned = {
                item["video_id"]: item
                for item in json.loads(plan_path.read_text(encoding="utf-8"))
            }
            for video in videos:
                override = planned.get(video["id"])
                if override:
                    if override.get("description"):
                        video["description"] = override["description"]
                    if override.get("title"):
                        video["title"] = override["title"]
                    if override.get("tags"):
                        video["tags"] = override["tags"]

        from scripts.apollo.youtube_transcript_collector import get_transcript

        print("APOLLO VIDEO REVIEW -- Own Channel")
        print("=" * 60)

        all_reviews = []
        for v in videos:
            # Try to load cached transcript
            cached = ROOT / "training-data" / "apollo" / "youtube_transcripts" / f"own_channel_{v['id']}.txt"
            if cached.exists():
                transcript = cached.read_text(encoding="utf-8")
            else:
                transcript = get_transcript(v["id"])

            review = review_video(v, transcript)
            all_reviews.append(review)
            print_review(review)

        avg = sum(r.overall for r in all_reviews) / len(all_reviews)
        print(f"\n{'=' * 60}")
        print(f"  Channel Average: {avg:.1f}/10")

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / f"review_{datetime.date.today().isoformat()}.json"
        with open(report_path, "w") as f:
            json.dump([asdict(r) for r in all_reviews], f, indent=2)
        print(f"  Report: {report_path}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
