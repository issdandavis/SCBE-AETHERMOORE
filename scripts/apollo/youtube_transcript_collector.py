"""Apollo YouTube Transcript Collector — Free daily transcript harvesting.

Pulls transcripts from curated channels, classifies by tongue,
scrubs secrets, generates SFT training pairs.

Uses youtube-transcript-api (free, no API key needed for public videos).
Uses YouTube Data API only for video search (via MCP or direct).

Usage:
    python scripts/apollo/youtube_transcript_collector.py collect --channel "3Blue1Brown" --max 5
    python scripts/apollo/youtube_transcript_collector.py collect-all --max-per-channel 3
    python scripts/apollo/youtube_transcript_collector.py stats
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

CHANNELS_PATH = ROOT / "config" / "training" / "curated_youtube_channels.json"
OUTPUT_DIR = ROOT / "training-data" / "apollo" / "youtube_transcripts"
SFT_DIR = ROOT / "training-data" / "sft"
STATE_PATH = ROOT / "artifacts" / "apollo" / "youtube_collector_state.json"


def load_channels() -> list[dict]:
    data = json.loads(CHANNELS_PATH.read_text())
    return data.get("channels", [])


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"collected": {}, "total_transcripts": 0, "last_run": None}


def save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def search_channel_videos(channel_name: str, max_results: int = 5, handle: str | None = None) -> list[dict]:
    """Search YouTube for recent videos from a channel.

    When *handle* is provided (e.g. ``"@RobertMilesAI"``), the yt-dlp
    search query uses the handle instead of the display name.  This avoids
    ambiguous matches — for example, searching "Robert Miles" returns the
    Italian musician, not the AI-safety YouTuber.
    """
    try:
        import urllib.request
        # Prefer the handle for search queries — it is unique on YouTube
        search_term = handle if handle else channel_name
        # Fallback: use yt-dlp if available
        import subprocess
        result = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--print", "%(id)s %(title)s",
             f"ytsearch{max_results}:{search_term}", "--no-warnings"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            videos = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        videos.append({"id": parts[0], "title": parts[1]})
            return videos[:max_results]
    except FileNotFoundError:
        logger.debug("yt-dlp not found, falling back to manual list")
    except Exception:
        logger.debug("yt-dlp search failed", exc_info=True)

    # Manual fallback: use known video IDs if yt-dlp not available
    return []


_TRANSCRIPT_DELAY = 30  # seconds between requests to avoid rate limiting


def get_transcript(video_id: str, delay: bool = True) -> Optional[str]:
    """Get transcript for a video using youtube-transcript-api.

    Adds a delay between calls to avoid YouTube rate limiting (429).
    """
    import time as _time

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)
        full_text = " ".join(snippet.text for snippet in transcript)
        if delay:
            _time.sleep(_TRANSCRIPT_DELAY)
        return full_text
    except ImportError:
        print("  youtube-transcript-api not installed. Run: pip install youtube-transcript-api")
        return None
    except Exception as e:
        if "429" in str(e) or "IpBlocked" in str(type(e).__name__):
            print(f"  Rate limited for {video_id}. Waiting 60s...")
            _time.sleep(60)
            # One retry after cooldown
            try:
                api = YouTubeTranscriptApi()
                transcript = api.fetch(video_id)
                return " ".join(snippet.text for snippet in transcript)
            except Exception:
                print(f"  Still blocked. Skip and try later.")
                return None
        print(f"  Transcript unavailable for {video_id}: {e}")
        return None


def scrub_transcript(text: str) -> tuple[str, int]:
    """Light scrub — remove URLs, emails, phone numbers from transcript."""
    from scripts.apollo.apollo_core import scrub_text
    clean, items = scrub_text(text)
    # Also remove URLs
    clean = re.sub(r"https?://\S+", "[URL]", clean)
    return clean, len(items)


def generate_sft_from_transcript(channel: dict, video_title: str, transcript: str) -> list[dict]:
    """Generate SFT pairs from a transcript."""
    pairs = []
    tongue = channel.get("tongue", "AV")
    domain = channel.get("domain", "general")

    # Pair 1: Summarize
    if len(transcript) > 200:
        pairs.append({
            "instruction": f"Summarize the key ideas from this {domain} content by {channel['name']}: '{video_title}'",
            "response": f"This content from {channel['name']} covers {domain}. " + transcript[:500].strip() + "...",
            "source": f"youtube_{channel['name'].lower().replace(' ', '_')}",
            "category": f"youtube_{tongue.lower()}",
            "tongue": tongue,
        })

    # Pair 2: Extract concepts
    if len(transcript) > 500:
        # Find sentences with key terms
        sentences = [s.strip() for s in re.split(r'[.!?]', transcript) if len(s.strip()) > 30]
        if len(sentences) >= 3:
            sample = ". ".join(sentences[:3])
            pairs.append({
                "instruction": f"What concepts does {channel['name']} explain in '{video_title}'?",
                "response": f"Key concepts covered: {sample}.",
                "source": f"youtube_{channel['name'].lower().replace(' ', '_')}",
                "category": f"youtube_{tongue.lower()}",
                "tongue": tongue,
            })

    return pairs


def collect_channel(channel_name: str, max_videos: int = 5) -> dict:
    """Collect transcripts from a specific channel."""
    channels = load_channels()
    channel = next((c for c in channels if c["name"].lower() == channel_name.lower()), None)

    if not channel:
        print(f"Channel '{channel_name}' not in curated list. Available:")
        for c in channels:
            print(f"  - {c['name']} ({c['tongue']}, rating: {c['rating']})")
        return {"collected": 0}

    print(f"Collecting from {channel['name']} (tongue: {channel['tongue']}, rating: {channel['rating']})")

    state = load_state()
    videos = search_channel_videos(channel["name"], max_videos, handle=channel.get("handle"))

    if not videos:
        print(f"  No videos found via search. Skipping.")
        return {"collected": 0}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_sft = []
    collected = 0

    for video in videos:
        vid_id = video["id"]
        title = video.get("title", vid_id)

        # Skip already collected
        if vid_id in state.get("collected", {}):
            print(f"  [skip] {title[:60]} (already collected)")
            continue

        print(f"  [fetch] {title[:60]}...", end=" ")
        transcript = get_transcript(vid_id)

        if not transcript:
            print("no transcript")
            continue

        # Scrub
        clean, scrubbed_count = scrub_transcript(transcript)
        print(f"{len(clean)} chars, {scrubbed_count} scrubbed")

        # Save transcript
        out_file = OUTPUT_DIR / f"{channel['name'].lower().replace(' ', '_')}_{vid_id}.txt"
        out_file.write_text(clean[:50000])  # cap at 50KB

        # Generate SFT
        pairs = generate_sft_from_transcript(channel, title, clean)
        all_sft.extend(pairs)

        # Update state
        state.setdefault("collected", {})[vid_id] = {
            "channel": channel["name"],
            "title": title,
            "tongue": channel["tongue"],
            "chars": len(clean),
            "date": datetime.date.today().isoformat(),
        }
        collected += 1

    state["total_transcripts"] = len(state.get("collected", {}))
    state["last_run"] = datetime.datetime.now().isoformat()
    save_state(state)

    # Save SFT
    if all_sft:
        sft_path = SFT_DIR / f"youtube_transcripts_{datetime.date.today().isoformat()}.jsonl"
        with open(sft_path, "a") as f:
            for p in all_sft:
                json.dump(p, f)
                f.write("\n")
        print(f"  SFT: {len(all_sft)} pairs -> {sft_path}")

    return {"collected": collected, "sft_pairs": len(all_sft)}


def collect_all(max_per_channel: int = 3):
    """Collect from all curated channels."""
    channels = load_channels()
    # Sort by rating (highest first)
    channels.sort(key=lambda c: c.get("rating", 0), reverse=True)

    print("APOLLO YOUTUBE TRANSCRIPT COLLECTOR")
    print("=" * 60)
    print(f"  Channels: {len(channels)}")
    print(f"  Max per channel: {max_per_channel}")
    print()

    total = {"collected": 0, "sft_pairs": 0}
    for channel in channels:
        result = collect_channel(channel["name"], max_per_channel)
        total["collected"] += result.get("collected", 0)
        total["sft_pairs"] += result.get("sft_pairs", 0)
        print()

    print(f"Total: {total['collected']} transcripts, {total['sft_pairs']} SFT pairs")
    return total


def show_stats():
    """Show collection stats."""
    state = load_state()
    channels = load_channels()

    print("YOUTUBE TRANSCRIPT STATS")
    print("=" * 60)
    print(f"  Total transcripts: {state.get('total_transcripts', 0)}")
    print(f"  Last run: {state.get('last_run', 'never')}")
    print(f"  Curated channels: {len(channels)}")
    print()

    # Per-channel breakdown
    collected = state.get("collected", {})
    by_channel = {}
    for _vid_id, info in collected.items():
        ch = info.get("channel", "?")
        by_channel[ch] = by_channel.get(ch, 0) + 1

    if by_channel:
        print("  Per channel:")
        for ch, count in sorted(by_channel.items(), key=lambda x: x[1], reverse=True):
            print(f"    {ch}: {count}")

    # Per-tongue breakdown
    by_tongue = {}
    for _vid_id, info in collected.items():
        t = info.get("tongue", "?")
        by_tongue[t] = by_tongue.get(t, 0) + 1

    if by_tongue:
        print(f"\n  Per tongue:")
        for t, count in sorted(by_tongue.items()):
            print(f"    {t}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Apollo YouTube Transcript Collector")
    sub = parser.add_subparsers(dest="command")

    c = sub.add_parser("collect", help="Collect from one channel")
    c.add_argument("--channel", required=True)
    c.add_argument("--max", type=int, default=5)

    a = sub.add_parser("collect-all", help="Collect from all curated channels")
    a.add_argument("--max-per-channel", type=int, default=3)

    sub.add_parser("stats", help="Show collection stats")
    sub.add_parser("channels", help="List curated channels")

    args = parser.parse_args()

    if args.command == "collect":
        collect_channel(args.channel, args.max)
    elif args.command == "collect-all":
        collect_all(args.max_per_channel)
    elif args.command == "stats":
        show_stats()
    elif args.command == "channels":
        channels = load_channels()
        print(f"{'Name':25s} {'Tongue':6s} {'Rating':6s} Domain")
        print("-" * 70)
        for c in sorted(channels, key=lambda x: x["rating"], reverse=True):
            print(f"{c['name']:25s} {c['tongue']:6s} {'*' * c['rating']:6s} {c['domain'][:40]}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
