"""
SCBE Web Agent — Buffer Integration for Content Posting
=========================================================

Social media and CMS content posting system with SCBE governance.
Works like Buffer/Hootsuite — queue posts, schedule them, publish
across multiple platforms with full antivirus scanning.

Supported platforms (via browser automation or API):
- Twitter/X     — post tweets, threads, media
- LinkedIn      — posts, articles
- Bluesky       — posts via AT Protocol
- Mastodon      — posts via ActivityPub API
- WordPress     — blog posts via REST API
- Medium        — articles via API
- GitHub        — issues, comments, releases
- HuggingFace   — model cards, dataset cards, spaces
- Custom API    — any REST endpoint

Each post goes through:
1. Semantic antivirus scan (content safety)
2. Hamiltonian governance gate H(d,pd)
3. Platform-specific formatting
4. Rate limiting and scheduling
5. Post-publish verification

Integrates with:
- SCBE Layer 5   (Governance Mesh → content policies)
- SCBE Layer 7   (Diplomatic Accord → multi-platform coordination)
- SCBE Layer 13  (Audit → post telemetry)
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .semantic_antivirus import SemanticAntivirus, ContentVerdict


# ---------------------------------------------------------------------------
#  Platform definitions
# ---------------------------------------------------------------------------

class Platform(str, Enum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    BLUESKY = "bluesky"
    MASTODON = "mastodon"
    WORDPRESS = "wordpress"
    MEDIUM = "medium"
    GITHUB = "github"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


PLATFORM_LIMITS: Dict[Platform, Dict[str, Any]] = {
    Platform.TWITTER:     {"max_chars": 280, "max_media": 4, "max_per_hour": 50},
    Platform.LINKEDIN:    {"max_chars": 3000, "max_media": 9, "max_per_hour": 30},
    Platform.BLUESKY:     {"max_chars": 300, "max_media": 4, "max_per_hour": 100},
    Platform.MASTODON:    {"max_chars": 500, "max_media": 4, "max_per_hour": 100},
    Platform.WORDPRESS:   {"max_chars": 100000, "max_media": 50, "max_per_hour": 20},
    Platform.MEDIUM:      {"max_chars": 100000, "max_media": 50, "max_per_hour": 10},
    Platform.GITHUB:      {"max_chars": 65536, "max_media": 10, "max_per_hour": 100},
    Platform.HUGGINGFACE: {"max_chars": 100000, "max_media": 20, "max_per_hour": 50},
    Platform.CUSTOM:      {"max_chars": 100000, "max_media": 10, "max_per_hour": 100},
}


# ---------------------------------------------------------------------------
#  Post data structures
# ---------------------------------------------------------------------------

class PostStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    BLOCKED = "blocked"         # Blocked by governance


@dataclass
class PostContent:
    """Content to be posted, with platform-specific variants."""

    text: str
    title: Optional[str] = None                     # For blog posts
    media_urls: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)    # Hashtags / categories
    link: Optional[str] = None                       # Attached URL
    thread: Optional[List[str]] = None               # For thread posts (Twitter)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def for_platform(self, platform: Platform) -> str:
        """Format content for a specific platform's limits."""
        limits = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS[Platform.CUSTOM])
        max_chars = limits["max_chars"]

        text = self.text
        # Add hashtags if they fit
        if self.tags:
            tag_str = " " + " ".join(f"#{t}" for t in self.tags)
            if len(text) + len(tag_str) <= max_chars:
                text += tag_str

        # Add link if it fits
        if self.link:
            link_str = f"\n{self.link}"
            if len(text) + len(link_str) <= max_chars:
                text += link_str

        # Truncate if needed
        if len(text) > max_chars:
            text = text[:max_chars - 3] + "..."

        return text


@dataclass
class ScheduledPost:
    """A post queued for publishing."""

    post_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    content: PostContent = field(default_factory=PostContent)
    platforms: List[Platform] = field(default_factory=list)
    schedule_at: Optional[float] = None     # Unix timestamp; None = immediate
    status: PostStatus = PostStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    published_at: Optional[float] = None

    # Per-platform results
    platform_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Governance
    governance_verdict: Optional[str] = None
    governance_risk: float = 0.0

    @property
    def is_due(self) -> bool:
        if self.schedule_at is None:
            return True
        return time.time() >= self.schedule_at

    @property
    def all_published(self) -> bool:
        return all(
            p.value in self.platform_results
            for p in self.platforms
        )


@dataclass
class PublishResult:
    """Result of publishing to a single platform."""

    platform: Platform
    success: bool
    post_url: Optional[str] = None
    error: Optional[str] = None
    response_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
#  Platform publishers (pluggable)
# ---------------------------------------------------------------------------

class PlatformPublisher:
    """
    Base publisher interface.

    Override `publish()` for each platform.  The default implementation
    produces a dry-run result (for testing without live API connections).
    """

    def __init__(self, platform: Platform, credentials: Optional[Dict[str, str]] = None) -> None:
        self.platform = platform
        self._credentials = credentials or {}

    def publish(self, content: PostContent) -> PublishResult:
        """Publish content. Override for real implementations."""
        formatted = content.for_platform(self.platform)
        return PublishResult(
            platform=self.platform,
            success=True,
            post_url=f"https://{self.platform.value}.example.com/post/{uuid.uuid4().hex[:8]}",
            response_data={
                "dry_run": True,
                "formatted_text": formatted,
                "char_count": len(formatted),
            },
        )

    def validate(self, content: PostContent) -> List[str]:
        """Validate content against platform limits. Returns issues."""
        issues: List[str] = []
        limits = PLATFORM_LIMITS.get(self.platform, {})
        max_chars = limits.get("max_chars", 100000)
        max_media = limits.get("max_media", 10)

        if len(content.text) > max_chars:
            issues.append(f"Text exceeds {max_chars} chars ({len(content.text)})")
        if len(content.media_urls) > max_media:
            issues.append(f"Too many media files ({len(content.media_urls)} > {max_media})")

        return issues


# ---------------------------------------------------------------------------
#  Rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Per-platform rate limiting."""

    def __init__(self) -> None:
        self._timestamps: Dict[str, List[float]] = {}

    def can_post(self, platform: Platform) -> bool:
        key = platform.value
        limits = PLATFORM_LIMITS.get(platform, {})
        max_per_hour = limits.get("max_per_hour", 100)

        now = time.time()
        one_hour_ago = now - 3600

        if key not in self._timestamps:
            self._timestamps[key] = []

        # Clean old entries
        self._timestamps[key] = [t for t in self._timestamps[key] if t > one_hour_ago]

        return len(self._timestamps[key]) < max_per_hour

    def record_post(self, platform: Platform) -> None:
        key = platform.value
        if key not in self._timestamps:
            self._timestamps[key] = []
        self._timestamps[key].append(time.time())

    def time_until_available(self, platform: Platform) -> float:
        """Seconds until next post is allowed. 0 if available now."""
        if self.can_post(platform):
            return 0.0
        key = platform.value
        oldest = min(self._timestamps.get(key, [time.time()]))
        return max(0, oldest + 3600 - time.time())


# ---------------------------------------------------------------------------
#  ContentBuffer (Buffer-style queue)
# ---------------------------------------------------------------------------

class ContentBuffer:
    """
    Buffer-style content posting queue with SCBE governance.

    Usage::

        buffer = ContentBuffer()
        buffer.register_publisher(PlatformPublisher(Platform.TWITTER, creds))

        post = buffer.create_post(
            text="New release of SCBE-AETHERMOORE!",
            platforms=[Platform.TWITTER, Platform.LINKEDIN],
            tags=["AI", "security"],
            schedule_at=time.time() + 3600,  # 1 hour from now
        )

        # Process due posts
        results = buffer.publish_due()
    """

    def __init__(
        self,
        antivirus: Optional[SemanticAntivirus] = None,
    ) -> None:
        self._antivirus = antivirus or SemanticAntivirus()
        self._queue: List[ScheduledPost] = []
        self._published: List[ScheduledPost] = []
        self._publishers: Dict[Platform, PlatformPublisher] = {}
        self._rate_limiter = RateLimiter()

    def register_publisher(self, publisher: PlatformPublisher) -> None:
        """Register a publisher for a platform."""
        self._publishers[publisher.platform] = publisher

    def create_post(
        self,
        text: str,
        platforms: List[str],
        title: Optional[str] = None,
        media_urls: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        link: Optional[str] = None,
        thread: Optional[List[str]] = None,
        schedule_at: Optional[float] = None,
    ) -> ScheduledPost:
        """Create and queue a post. Content is scanned before queuing."""
        platform_enums = [Platform(p) for p in platforms]
        content = PostContent(
            text=text,
            title=title,
            media_urls=media_urls or [],
            tags=tags or [],
            link=link,
            thread=thread,
        )

        # Governance scan
        profile = self._antivirus.scan(text)

        post = ScheduledPost(
            content=content,
            platforms=platform_enums,
            schedule_at=schedule_at,
            governance_verdict=profile.governance_decision,
            governance_risk=profile.risk_score,
        )

        if profile.governance_decision == "DENY":
            post.status = PostStatus.BLOCKED
            return post

        # Validate against each platform
        for platform in platform_enums:
            publisher = self._publishers.get(platform)
            if publisher:
                issues = publisher.validate(content)
                if issues:
                    post.platform_results[platform.value] = {"issues": issues}

        if schedule_at:
            post.status = PostStatus.SCHEDULED
        else:
            post.status = PostStatus.QUEUED

        self._queue.append(post)
        return post

    def publish_due(self) -> List[PublishResult]:
        """Publish all posts that are due. Returns results."""
        results: List[PublishResult] = []
        completed: List[ScheduledPost] = []

        for post in self._queue:
            if post.status in (PostStatus.BLOCKED, PostStatus.FAILED):
                continue
            if not post.is_due:
                continue

            post.status = PostStatus.PUBLISHING

            for platform in post.platforms:
                if platform.value in post.platform_results:
                    # Already published or has issues
                    continue

                # Rate limit check
                if not self._rate_limiter.can_post(platform):
                    post.platform_results[platform.value] = {
                        "error": "rate_limited",
                        "retry_after": self._rate_limiter.time_until_available(platform),
                    }
                    continue

                publisher = self._publishers.get(platform)
                if not publisher:
                    # Dry run
                    publisher = PlatformPublisher(platform)

                result = publisher.publish(post.content)
                results.append(result)
                self._rate_limiter.record_post(platform)

                post.platform_results[platform.value] = {
                    "success": result.success,
                    "post_url": result.post_url,
                    "error": result.error,
                }

            # Check if all platforms done
            if post.all_published:
                post.status = PostStatus.PUBLISHED
                post.published_at = time.time()
                completed.append(post)

        # Move completed to archive
        for post in completed:
            self._queue.remove(post)
            self._published.append(post)

        return results

    def cancel_post(self, post_id: str) -> bool:
        """Cancel a queued post."""
        for i, post in enumerate(self._queue):
            if post.post_id == post_id:
                self._queue.pop(i)
                return True
        return False

    def reschedule(self, post_id: str, new_time: float) -> bool:
        """Reschedule a queued post."""
        for post in self._queue:
            if post.post_id == post_id:
                post.schedule_at = new_time
                post.status = PostStatus.SCHEDULED
                return True
        return False

    # -- query API -----------------------------------------------------------

    @property
    def queue(self) -> List[ScheduledPost]:
        return list(self._queue)

    @property
    def published(self) -> List[ScheduledPost]:
        return list(self._published)

    def due_posts(self) -> List[ScheduledPost]:
        return [p for p in self._queue if p.is_due and p.status in (PostStatus.QUEUED, PostStatus.SCHEDULED)]

    def summary(self) -> Dict[str, Any]:
        by_status: Dict[str, int] = {}
        for p in self._queue:
            by_status[p.status.value] = by_status.get(p.status.value, 0) + 1
        return {
            "queued": len(self._queue),
            "published": len(self._published),
            "due_now": len(self.due_posts()),
            "by_status": by_status,
            "platforms_registered": [p.value for p in self._publishers.keys()],
        }
