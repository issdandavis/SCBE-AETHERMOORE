"""
SCBE Web Agent — Platform Publishers
======================================

Real platform publisher implementations for the ContentBuffer.
Each publisher handles authentication, formatting, and API calls
for a specific platform. All publishers run content through the
governance pipeline before posting.

Supported:
- Twitter/X       (OAuth 2.0 Bearer → v2 API)
- LinkedIn        (OAuth 2.0 → UGC Posts API)
- Bluesky         (AT Protocol → createRecord)
- Mastodon        (Bearer token → /api/v1/statuses)
- WordPress       (Application Password → /wp-json/wp/v2/posts)
- Medium          (Integration token → /v1/users/me/posts)
- GitHub          (Personal Access Token → repos/issues/releases)
- HuggingFace    (HF Token → /api/repos/create, model cards)
- Custom REST     (Configurable endpoint + headers)

All publishers extend `PlatformPublisher` from buffer_integration.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

from .buffer_integration import (
    Platform,
    PlatformPublisher,
    PostContent,
    PublishResult,
)


# ---------------------------------------------------------------------------
#  Shared HTTP client factory
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT = 30.0
_USER_AGENT = "SCBE-WebAgent/1.0 (Autonomous; +https://github.com/issdandavis/SCBE-AETHERMOORE)"


def _client(headers: Optional[Dict[str, str]] = None, timeout: float = _DEFAULT_TIMEOUT) -> httpx.Client:
    """Build a pre-configured httpx client."""
    base = {
        "User-Agent": _USER_AGENT,
        "Accept": "application/json",
    }
    if headers:
        base.update(headers)
    return httpx.Client(headers=base, timeout=timeout, follow_redirects=True)


# ---------------------------------------------------------------------------
#  Twitter / X  (v2 API)
# ---------------------------------------------------------------------------

class TwitterPublisher(PlatformPublisher):
    """
    Post tweets via Twitter API v2.

    Required credentials:
        bearer_token  — OAuth 2.0 Bearer Token (App or User)
    """

    API_BASE = "https://api.twitter.com/2"

    def __init__(self, credentials: Dict[str, str]) -> None:
        super().__init__(Platform.TWITTER, credentials)
        self._bearer = credentials["bearer_token"]

    def publish(self, content: PostContent) -> PublishResult:
        text = content.for_platform(self.platform)

        # Handle threads
        if content.thread:
            return self._post_thread(content.thread, text)

        return self._post_single(text)

    def _post_single(self, text: str) -> PublishResult:
        with _client({"Authorization": f"Bearer {self._bearer}"}) as client:
            try:
                resp = client.post(
                    f"{self.API_BASE}/tweets",
                    json={"text": text},
                )
                data = resp.json()
                if resp.status_code in (200, 201):
                    tweet_id = data.get("data", {}).get("id", "")
                    return PublishResult(
                        platform=self.platform,
                        success=True,
                        post_url=f"https://x.com/i/status/{tweet_id}",
                        response_data=data,
                    )
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=data.get("detail", str(data)),
                    response_data=data,
                )
            except httpx.HTTPError as e:
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=str(e),
                )

    def _post_thread(self, parts: List[str], first_text: str) -> PublishResult:
        """Post a thread by chaining reply_to_tweet_id."""
        texts = [first_text] + parts
        tweet_ids: List[str] = []

        with _client({"Authorization": f"Bearer {self._bearer}"}) as client:
            reply_to: Optional[str] = None
            for part in texts:
                body: Dict[str, Any] = {"text": part[:280]}
                if reply_to:
                    body["reply"] = {"in_reply_to_tweet_id": reply_to}

                try:
                    resp = client.post(f"{self.API_BASE}/tweets", json=body)
                    data = resp.json()
                    if resp.status_code in (200, 201):
                        tid = data.get("data", {}).get("id", "")
                        tweet_ids.append(tid)
                        reply_to = tid
                    else:
                        return PublishResult(
                            platform=self.platform,
                            success=False,
                            error=f"Thread failed at part {len(tweet_ids)+1}: {data}",
                            response_data={"tweet_ids": tweet_ids},
                        )
                except httpx.HTTPError as e:
                    return PublishResult(
                        platform=self.platform,
                        success=False,
                        error=str(e),
                        response_data={"tweet_ids": tweet_ids},
                    )

        return PublishResult(
            platform=self.platform,
            success=True,
            post_url=f"https://x.com/i/status/{tweet_ids[0]}" if tweet_ids else None,
            response_data={"tweet_ids": tweet_ids, "thread_length": len(tweet_ids)},
        )


# ---------------------------------------------------------------------------
#  LinkedIn  (UGC Posts API v2)
# ---------------------------------------------------------------------------

class LinkedInPublisher(PlatformPublisher):
    """
    Post to LinkedIn via UGC Posts API.

    Required credentials:
        access_token  — OAuth 2.0 access token
        person_urn    — urn:li:person:XXXXXX  (or urn:li:organization:XXXX)
    """

    API_BASE = "https://api.linkedin.com/v2"

    def __init__(self, credentials: Dict[str, str]) -> None:
        super().__init__(Platform.LINKEDIN, credentials)
        self._token = credentials["access_token"]
        self._author = credentials["person_urn"]

    def publish(self, content: PostContent) -> PublishResult:
        text = content.for_platform(self.platform)
        body = {
            "author": self._author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        # Attach article link if present
        if content.link:
            share = body["specificContent"]["com.linkedin.ugc.ShareContent"]
            share["shareMediaCategory"] = "ARTICLE"
            share["media"] = [{
                "status": "READY",
                "originalUrl": content.link,
                "title": {"text": content.title or content.link},
            }]

        with _client({"Authorization": f"Bearer {self._token}"}) as client:
            try:
                resp = client.post(f"{self.API_BASE}/ugcPosts", json=body)
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if resp.status_code in (200, 201):
                    post_urn = resp.headers.get("X-RestLi-Id", data.get("id", ""))
                    return PublishResult(
                        platform=self.platform,
                        success=True,
                        post_url=f"https://www.linkedin.com/feed/update/{post_urn}",
                        response_data=data,
                    )
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=str(data),
                    response_data=data,
                )
            except httpx.HTTPError as e:
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=str(e),
                )


# ---------------------------------------------------------------------------
#  Bluesky  (AT Protocol)
# ---------------------------------------------------------------------------

class BlueskyPublisher(PlatformPublisher):
    """
    Post to Bluesky via AT Protocol.

    Required credentials:
        handle    — e.g. user.bsky.social
        password  — app password
    Optional:
        pds_url   — PDS base URL (default: https://bsky.social)
    """

    def __init__(self, credentials: Dict[str, str]) -> None:
        super().__init__(Platform.BLUESKY, credentials)
        self._handle = credentials["handle"]
        self._password = credentials["password"]
        self._pds = credentials.get("pds_url", "https://bsky.social")
        self._session: Optional[Dict[str, Any]] = None

    def _login(self, client: httpx.Client) -> bool:
        resp = client.post(
            f"{self._pds}/xrpc/com.atproto.server.createSession",
            json={"identifier": self._handle, "password": self._password},
        )
        if resp.status_code == 200:
            self._session = resp.json()
            return True
        return False

    def publish(self, content: PostContent) -> PublishResult:
        text = content.for_platform(self.platform)

        with _client() as client:
            if not self._session:
                if not self._login(client):
                    return PublishResult(
                        platform=self.platform,
                        success=False,
                        error="Bluesky login failed",
                    )

            now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            record: Dict[str, Any] = {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": now,
            }

            # Add link facet if present
            if content.link:
                byte_start = text.find(content.link)
                if byte_start >= 0:
                    record["facets"] = [{
                        "index": {
                            "byteStart": byte_start,
                            "byteEnd": byte_start + len(content.link),
                        },
                        "features": [{
                            "$type": "app.bsky.richtext.facet#link",
                            "uri": content.link,
                        }],
                    }]

            body = {
                "repo": self._session["did"],
                "collection": "app.bsky.feed.post",
                "record": record,
            }

            try:
                resp = client.post(
                    f"{self._pds}/xrpc/com.atproto.repo.createRecord",
                    json=body,
                    headers={"Authorization": f"Bearer {self._session['accessJwt']}"},
                )
                data = resp.json()
                if resp.status_code == 200:
                    uri = data.get("uri", "")
                    # Convert AT URI to web URL
                    parts = uri.replace("at://", "").split("/")
                    web_url = f"https://bsky.app/profile/{parts[0]}/post/{parts[-1]}" if len(parts) >= 3 else uri
                    return PublishResult(
                        platform=self.platform,
                        success=True,
                        post_url=web_url,
                        response_data=data,
                    )
                # Session expired — retry once
                if resp.status_code == 401:
                    self._session = None
                    if self._login(client):
                        return self.publish(content)
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=str(data),
                    response_data=data,
                )
            except httpx.HTTPError as e:
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=str(e),
                )


# ---------------------------------------------------------------------------
#  Mastodon  (ActivityPub REST API)
# ---------------------------------------------------------------------------

class MastodonPublisher(PlatformPublisher):
    """
    Post to Mastodon via REST API.

    Required credentials:
        access_token   — Bearer token
        instance_url   — e.g. https://mastodon.social
    """

    def __init__(self, credentials: Dict[str, str]) -> None:
        super().__init__(Platform.MASTODON, credentials)
        self._token = credentials["access_token"]
        self._instance = credentials["instance_url"].rstrip("/")

    def publish(self, content: PostContent) -> PublishResult:
        text = content.for_platform(self.platform)
        body: Dict[str, Any] = {"status": text}

        if content.metadata.get("visibility"):
            body["visibility"] = content.metadata["visibility"]
        if content.metadata.get("spoiler_text"):
            body["spoiler_text"] = content.metadata["spoiler_text"]

        with _client({"Authorization": f"Bearer {self._token}"}) as client:
            try:
                # Upload media first if present
                media_ids = []
                for url in content.media_urls[:4]:
                    mid = self._upload_media(client, url)
                    if mid:
                        media_ids.append(mid)
                if media_ids:
                    body["media_ids"] = media_ids

                resp = client.post(f"{self._instance}/api/v1/statuses", json=body)
                data = resp.json()
                if resp.status_code in (200, 201):
                    return PublishResult(
                        platform=self.platform,
                        success=True,
                        post_url=data.get("url", data.get("uri", "")),
                        response_data=data,
                    )
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=data.get("error", str(data)),
                    response_data=data,
                )
            except httpx.HTTPError as e:
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=str(e),
                )

    def _upload_media(self, client: httpx.Client, media_url: str) -> Optional[str]:
        """Upload media from URL to Mastodon. Returns media_id or None."""
        try:
            dl = client.get(media_url)
            if dl.status_code != 200:
                return None
            content_type = dl.headers.get("content-type", "application/octet-stream")
            ext = content_type.split("/")[-1].split(";")[0]
            resp = client.post(
                f"{self._instance}/api/v2/media",
                files={"file": (f"upload.{ext}", dl.content, content_type)},
            )
            if resp.status_code in (200, 202):
                return resp.json().get("id")
        except httpx.HTTPError:
            pass
        return None


# ---------------------------------------------------------------------------
#  WordPress  (REST API with Application Password)
# ---------------------------------------------------------------------------

class WordPressPublisher(PlatformPublisher):
    """
    Post to WordPress via REST API.

    Required credentials:
        site_url    — e.g. https://myblog.com
        username    — WP username
        app_password — Application Password (not regular password)
    """

    def __init__(self, credentials: Dict[str, str]) -> None:
        super().__init__(Platform.WORDPRESS, credentials)
        self._site = credentials["site_url"].rstrip("/")
        self._username = credentials["username"]
        self._app_pw = credentials["app_password"]

    def publish(self, content: PostContent) -> PublishResult:
        body: Dict[str, Any] = {
            "title": content.title or content.text[:80],
            "content": content.text,
            "status": "publish",
        }

        if content.tags:
            body["tags"] = content.tags
        if content.metadata.get("categories"):
            body["categories"] = content.metadata["categories"]
        if content.metadata.get("slug"):
            body["slug"] = content.metadata["slug"]

        with _client() as client:
            try:
                resp = client.post(
                    f"{self._site}/wp-json/wp/v2/posts",
                    json=body,
                    auth=(self._username, self._app_pw),
                )
                data = resp.json()
                if resp.status_code in (200, 201):
                    return PublishResult(
                        platform=self.platform,
                        success=True,
                        post_url=data.get("link", data.get("guid", {}).get("rendered", "")),
                        response_data={"id": data.get("id"), "link": data.get("link")},
                    )
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=data.get("message", str(data)),
                    response_data=data,
                )
            except httpx.HTTPError as e:
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=str(e),
                )


# ---------------------------------------------------------------------------
#  Medium  (Integration Token API)
# ---------------------------------------------------------------------------

class MediumPublisher(PlatformPublisher):
    """
    Post articles to Medium.

    Required credentials:
        integration_token — Medium integration token
    """

    API_BASE = "https://api.medium.com/v1"

    def __init__(self, credentials: Dict[str, str]) -> None:
        super().__init__(Platform.MEDIUM, credentials)
        self._token = credentials["integration_token"]
        self._user_id: Optional[str] = None

    def _get_user_id(self, client: httpx.Client) -> Optional[str]:
        if self._user_id:
            return self._user_id
        resp = client.get(
            f"{self.API_BASE}/me",
            headers={"Authorization": f"Bearer {self._token}"},
        )
        if resp.status_code == 200:
            self._user_id = resp.json().get("data", {}).get("id")
        return self._user_id

    def publish(self, content: PostContent) -> PublishResult:
        with _client({"Authorization": f"Bearer {self._token}"}) as client:
            user_id = self._get_user_id(client)
            if not user_id:
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error="Failed to get Medium user ID",
                )

            body: Dict[str, Any] = {
                "title": content.title or content.text[:100],
                "contentFormat": "markdown",
                "content": content.text,
                "publishStatus": "draft",  # Safe default — user promotes to public
            }

            if content.tags:
                body["tags"] = content.tags[:5]  # Medium max 5 tags
            if content.link:
                body["canonicalUrl"] = content.link

            try:
                resp = client.post(
                    f"{self.API_BASE}/users/{user_id}/posts",
                    json=body,
                )
                data = resp.json()
                if resp.status_code in (200, 201):
                    post_data = data.get("data", {})
                    return PublishResult(
                        platform=self.platform,
                        success=True,
                        post_url=post_data.get("url", ""),
                        response_data=post_data,
                    )
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=str(data),
                    response_data=data,
                )
            except httpx.HTTPError as e:
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=str(e),
                )


# ---------------------------------------------------------------------------
#  GitHub  (Issues, Comments, Releases)
# ---------------------------------------------------------------------------

class GitHubPublisher(PlatformPublisher):
    """
    Post to GitHub (issues, comments, releases, discussions).

    Required credentials:
        token     — Personal Access Token (classic or fine-grained)
        repo      — owner/repo format
    Optional:
        post_type — "issue" (default), "comment", "release", "discussion"
        issue_number — for comments on existing issues
    """

    API_BASE = "https://api.github.com"

    def __init__(self, credentials: Dict[str, str]) -> None:
        super().__init__(Platform.GITHUB, credentials)
        self._token = credentials["token"]
        self._repo = credentials["repo"]
        self._post_type = credentials.get("post_type", "issue")

    def publish(self, content: PostContent) -> PublishResult:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        with _client(headers) as client:
            if self._post_type == "issue":
                return self._create_issue(client, content)
            elif self._post_type == "comment":
                return self._create_comment(client, content)
            elif self._post_type == "release":
                return self._create_release(client, content)
            else:
                return self._create_issue(client, content)

    def _create_issue(self, client: httpx.Client, content: PostContent) -> PublishResult:
        body = {
            "title": content.title or content.text[:80],
            "body": content.text,
        }
        if content.tags:
            body["labels"] = content.tags

        try:
            resp = client.post(f"{self.API_BASE}/repos/{self._repo}/issues", json=body)
            data = resp.json()
            if resp.status_code in (200, 201):
                return PublishResult(
                    platform=self.platform,
                    success=True,
                    post_url=data.get("html_url", ""),
                    response_data={"number": data.get("number"), "id": data.get("id")},
                )
            return PublishResult(
                platform=self.platform,
                success=False,
                error=data.get("message", str(data)),
                response_data=data,
            )
        except httpx.HTTPError as e:
            return PublishResult(platform=self.platform, success=False, error=str(e))

    def _create_comment(self, client: httpx.Client, content: PostContent) -> PublishResult:
        issue_num = content.metadata.get("issue_number") or self._credentials.get("issue_number")
        if not issue_num:
            return PublishResult(
                platform=self.platform,
                success=False,
                error="issue_number required for comment post_type",
            )

        try:
            resp = client.post(
                f"{self.API_BASE}/repos/{self._repo}/issues/{issue_num}/comments",
                json={"body": content.text},
            )
            data = resp.json()
            if resp.status_code in (200, 201):
                return PublishResult(
                    platform=self.platform,
                    success=True,
                    post_url=data.get("html_url", ""),
                    response_data=data,
                )
            return PublishResult(
                platform=self.platform,
                success=False,
                error=data.get("message", str(data)),
                response_data=data,
            )
        except httpx.HTTPError as e:
            return PublishResult(platform=self.platform, success=False, error=str(e))

    def _create_release(self, client: httpx.Client, content: PostContent) -> PublishResult:
        tag = content.metadata.get("tag_name", f"v{time.strftime('%Y%m%d%H%M%S')}")
        body = {
            "tag_name": tag,
            "name": content.title or tag,
            "body": content.text,
            "draft": content.metadata.get("draft", False),
            "prerelease": content.metadata.get("prerelease", False),
        }

        try:
            resp = client.post(f"{self.API_BASE}/repos/{self._repo}/releases", json=body)
            data = resp.json()
            if resp.status_code in (200, 201):
                return PublishResult(
                    platform=self.platform,
                    success=True,
                    post_url=data.get("html_url", ""),
                    response_data={"id": data.get("id"), "tag_name": tag},
                )
            return PublishResult(
                platform=self.platform,
                success=False,
                error=data.get("message", str(data)),
                response_data=data,
            )
        except httpx.HTTPError as e:
            return PublishResult(platform=self.platform, success=False, error=str(e))


# ---------------------------------------------------------------------------
#  HuggingFace  (Hub API)
# ---------------------------------------------------------------------------

class HuggingFacePublisher(PlatformPublisher):
    """
    Post to HuggingFace Hub (model cards, dataset cards, Space READMEs).

    Required credentials:
        hf_token    — HuggingFace API token
        repo_id     — namespace/repo-name
    Optional:
        repo_type   — "model" (default), "dataset", "space"
    """

    API_BASE = "https://huggingface.co/api"

    def __init__(self, credentials: Dict[str, str]) -> None:
        super().__init__(Platform.HUGGINGFACE, credentials)
        self._token = credentials["hf_token"]
        self._repo_id = credentials["repo_id"]
        self._repo_type = credentials.get("repo_type", "model")

    def publish(self, content: PostContent) -> PublishResult:
        headers = {"Authorization": f"Bearer {self._token}"}

        # HF Hub uses file upload to update README.md (the card)
        commit_message = content.title or "Update card via SCBE Web Agent"
        readme_content = content.text

        # Use the Hub API to create a commit
        url = f"{self.API_BASE}/repos/{self._repo_id}/commit/main"
        if self._repo_type != "model":
            url = f"{self.API_BASE}/repos/{self._repo_type}s/{self._repo_id}/commit/main"

        payload = {
            "summary": commit_message,
            "files": [{
                "path": "README.md",
                "content": readme_content,
            }],
        }

        with _client(headers) as client:
            try:
                # Use the simpler /api/{repo_type}s/{repo_id} endpoint
                # to update the model card metadata
                card_url = f"{self.API_BASE}/{self._repo_type}s/{self._repo_id}"
                resp = client.get(card_url)

                if resp.status_code == 404:
                    return PublishResult(
                        platform=self.platform,
                        success=False,
                        error=f"Repo {self._repo_id} not found",
                    )

                # Upload README via the git-based API
                upload_url = (
                    f"https://huggingface.co/api/{self._repo_type}s/{self._repo_id}"
                    f"/upload/main/README.md"
                )
                resp = client.put(
                    upload_url,
                    content=readme_content.encode("utf-8"),
                    headers={
                        **headers,
                        "Content-Type": "application/octet-stream",
                        "x-commit-message": commit_message,
                    },
                )

                if resp.status_code in (200, 201):
                    web_url = f"https://huggingface.co/{self._repo_id}"
                    if self._repo_type == "dataset":
                        web_url = f"https://huggingface.co/datasets/{self._repo_id}"
                    elif self._repo_type == "space":
                        web_url = f"https://huggingface.co/spaces/{self._repo_id}"
                    return PublishResult(
                        platform=self.platform,
                        success=True,
                        post_url=web_url,
                        response_data={"commit_message": commit_message},
                    )

                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=f"HF upload failed: {resp.status_code} {resp.text[:200]}",
                )
            except httpx.HTTPError as e:
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=str(e),
                )


# ---------------------------------------------------------------------------
#  Custom REST API
# ---------------------------------------------------------------------------

class CustomAPIPublisher(PlatformPublisher):
    """
    Post to any REST endpoint.

    Required credentials:
        endpoint    — Full URL to POST to
    Optional:
        headers     — JSON string of extra headers
        auth_header — Value for Authorization header
        method      — HTTP method (default: POST)
        body_template — JSON template with {text}, {title}, {tags} placeholders
    """

    def __init__(self, credentials: Dict[str, str]) -> None:
        super().__init__(Platform.CUSTOM, credentials)
        self._endpoint = credentials["endpoint"]
        self._extra_headers = json.loads(credentials.get("headers", "{}"))
        self._auth = credentials.get("auth_header")
        self._method = credentials.get("method", "POST").upper()
        self._template = credentials.get("body_template")

    def publish(self, content: PostContent) -> PublishResult:
        text = content.for_platform(self.platform)

        if self._template:
            body_str = self._template.replace("{text}", text)
            body_str = body_str.replace("{title}", content.title or "")
            body_str = body_str.replace("{tags}", ",".join(content.tags))
            body = json.loads(body_str)
        else:
            body = {
                "text": text,
                "title": content.title,
                "tags": content.tags,
                "link": content.link,
                "media": content.media_urls,
            }

        headers = dict(self._extra_headers)
        if self._auth:
            headers["Authorization"] = self._auth

        with _client(headers) as client:
            try:
                resp = client.request(self._method, self._endpoint, json=body)
                data = {}
                try:
                    data = resp.json()
                except Exception:
                    data = {"raw": resp.text[:500]}

                if resp.status_code < 400:
                    return PublishResult(
                        platform=self.platform,
                        success=True,
                        post_url=data.get("url", data.get("link", self._endpoint)),
                        response_data=data,
                    )
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=f"HTTP {resp.status_code}: {str(data)[:200]}",
                    response_data=data,
                )
            except httpx.HTTPError as e:
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=str(e),
                )


# ---------------------------------------------------------------------------
#  Publisher registry — factory function
# ---------------------------------------------------------------------------

PUBLISHER_CLASSES: Dict[Platform, type] = {
    Platform.TWITTER: TwitterPublisher,
    Platform.LINKEDIN: LinkedInPublisher,
    Platform.BLUESKY: BlueskyPublisher,
    Platform.MASTODON: MastodonPublisher,
    Platform.WORDPRESS: WordPressPublisher,
    Platform.MEDIUM: MediumPublisher,
    Platform.GITHUB: GitHubPublisher,
    Platform.HUGGINGFACE: HuggingFacePublisher,
    Platform.CUSTOM: CustomAPIPublisher,
}


def create_publisher(platform: str, credentials: Dict[str, str]) -> PlatformPublisher:
    """
    Factory: create a publisher for the given platform.

    Args:
        platform: Platform name string (e.g. "twitter", "bluesky")
        credentials: Platform-specific credential dict

    Returns:
        Configured PlatformPublisher subclass instance.
        Falls back to dry-run base class if platform unknown.
    """
    plat = Platform(platform)
    cls = PUBLISHER_CLASSES.get(plat)
    if cls:
        return cls(credentials)
    return PlatformPublisher(plat, credentials)
