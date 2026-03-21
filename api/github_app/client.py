from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class GitHubAppConfig:
    app_id: str
    private_key_pem: str
    webhook_secret: str
    api_url: str = "https://api.github.com"
    check_name: str = "LatticeGate"
    comment_mode: str = "always"

    @classmethod
    def from_env(cls) -> "GitHubAppConfig":
        private_key_pem = os.getenv("GITHUB_APP_PRIVATE_KEY", "").strip()
        if not private_key_pem:
            private_key_path = (
                os.getenv("GITHUB_PRIVATE_KEY_PATH", "").strip()
                or os.getenv("GITHUB_APP_PRIVATE_KEY_PATH", "").strip()
            )
            if private_key_path and os.path.exists(private_key_path):
                with open(private_key_path, "r", encoding="utf-8") as handle:
                    private_key_pem = handle.read()

        if "\\n" in private_key_pem:
            private_key_pem = private_key_pem.replace("\\n", "\n")

        return cls(
            app_id=os.getenv("GITHUB_APP_ID", "").strip(),
            private_key_pem=private_key_pem.strip(),
            webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET", "").strip(),
            api_url=os.getenv("GITHUB_APP_API_URL", "https://api.github.com").strip()
            or "https://api.github.com",
            check_name=os.getenv("GITHUB_APP_CHECK_NAME", "LatticeGate").strip() or "LatticeGate",
            comment_mode=os.getenv("GITHUB_APP_COMMENT_MODE", "always").strip().lower() or "always",
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.app_id and self.private_key_pem and self.webhook_secret)


class GitHubAppApiClient:
    def __init__(
        self,
        config: GitHubAppConfig,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config
        self._transport = transport
        self._private_key = None

    def _load_private_key(self) -> Any:
        if self._private_key is None:
            self._private_key = serialization.load_pem_private_key(
                self.config.private_key_pem.encode("utf-8"),
                password=None,
            )
        return self._private_key

    def build_app_jwt(self) -> str:
        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {
            "iat": now - 60,
            "exp": now + 540,
            "iss": self.config.app_id,
        }
        signing_input = (
            f"{_b64url(json.dumps(header, separators=(',', ':')).encode('utf-8'))}."
            f"{_b64url(json.dumps(payload, separators=(',', ':')).encode('utf-8'))}"
        ).encode("ascii")
        signature = self._load_private_key().sign(
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return f"{signing_input.decode('ascii')}.{_b64url(signature)}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        bearer_token: str,
        json_body: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "SCBE-AETHERMOORE-LatticeGate/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(
            base_url=self.config.api_url,
            timeout=30.0,
            transport=self._transport,
        ) as client:
            response = await client.request(
                method,
                path,
                headers=headers,
                json=json_body,
                params=params,
            )
            response.raise_for_status()
            if not response.content:
                return None
            return response.json()

    async def create_installation_token(self, installation_id: int) -> str:
        payload = await self._request(
            "POST",
            f"/app/installations/{installation_id}/access_tokens",
            bearer_token=self.build_app_jwt(),
            json_body={},
        )
        return str(payload["token"])

    async def list_pull_request_files(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        *,
        installation_token: str,
        page_limit: int = 3,
    ) -> list[str]:
        filenames: list[str] = []
        for page in range(1, page_limit + 1):
            payload = await self._request(
                "GET",
                f"/repos/{owner}/{repo}/pulls/{pull_number}/files",
                bearer_token=installation_token,
                params={"per_page": 100, "page": page},
            )
            if not payload:
                break
            filenames.extend(str(item.get("filename", "")) for item in payload if item.get("filename"))
            if len(payload) < 100:
                break
        return filenames

    async def post_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
        *,
        installation_token: str,
    ) -> None:
        await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            bearer_token=installation_token,
            json_body={"body": body},
        )

    async def create_check_run(
        self,
        owner: str,
        repo: str,
        *,
        installation_token: str,
        name: str,
        head_sha: str,
        conclusion: str,
        title: str,
        summary: str,
        text: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> None:
        payload: dict[str, Any] = {
            "name": name,
            "head_sha": head_sha,
            "status": "completed",
            "conclusion": conclusion,
            "output": {
                "title": title,
                "summary": summary,
            },
        }
        if text:
            payload["output"]["text"] = text
        if external_id:
            payload["external_id"] = external_id
        await self._request(
            "POST",
            f"/repos/{owner}/{repo}/check-runs",
            bearer_token=installation_token,
            json_body=payload,
        )
