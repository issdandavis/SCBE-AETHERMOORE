from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any, Dict

from .client import GitHubAppApiClient, GitHubAppConfig
from .scoring import PullRequestIntentAssessment, assess_pull_request_intent

logger = logging.getLogger("scbe-github-app")

ACTIONABLE_PULL_REQUEST_EVENTS = {
    "opened",
    "edited",
    "ready_for_review",
    "reopened",
    "synchronize",
}


@dataclass
class GitHubAppService:
    config: GitHubAppConfig
    client: GitHubAppApiClient

    @classmethod
    def from_env(cls) -> "GitHubAppService":
        config = GitHubAppConfig.from_env()
        return cls(config=config, client=GitHubAppApiClient(config))

    @property
    def is_configured(self) -> bool:
        return self.config.is_configured

    def verify_signature(self, payload_body: bytes, signature_header: str | None) -> bool:
        if not self.config.webhook_secret or not signature_header:
            return False
        expected = hmac.new(
            self.config.webhook_secret.encode("utf-8"),
            msg=payload_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature_header)

    def health_status(self) -> dict[str, Any]:
        return {
            "configured": self.is_configured,
            "app_id_present": bool(self.config.app_id),
            "private_key_present": bool(self.config.private_key_pem),
            "webhook_secret_present": bool(self.config.webhook_secret),
            "check_name": self.config.check_name,
            "comment_mode": self.config.comment_mode,
            "api_url": self.config.api_url,
        }

    async def handle_event(
        self,
        *,
        event: str,
        payload: Dict[str, Any],
        delivery_id: str | None = None,
    ) -> dict[str, Any]:
        if event == "ping":
            return {
                "status": "ok",
                "event": "ping",
                "zen": payload.get("zen"),
            }

        if event != "pull_request":
            return {
                "status": "ignored",
                "event": event,
                "reason": "unsupported_event",
            }

        action = str(payload.get("action") or "")
        if action not in ACTIONABLE_PULL_REQUEST_EVENTS:
            return {
                "status": "ignored",
                "event": event,
                "action": action,
                "reason": "unsupported_action",
            }

        installation_id = payload.get("installation", {}).get("id")
        if not installation_id:
            return {
                "status": "ignored",
                "event": event,
                "action": action,
                "reason": "missing_installation",
            }

        repository = payload.get("repository") or {}
        pull_request = payload.get("pull_request") or {}
        repo_name = str(repository.get("name") or "")
        owner_name = str((repository.get("owner") or {}).get("login") or "")
        full_name = str(repository.get("full_name") or f"{owner_name}/{repo_name}")
        pull_number = int(payload.get("number") or pull_request.get("number") or 0)
        head_sha = str(((pull_request.get("head") or {}).get("sha")) or "")
        actor = str(((pull_request.get("user") or {}).get("login")) or "unknown-actor")

        installation_token = await self.client.create_installation_token(int(installation_id))

        filenames: list[str] = []
        if owner_name and repo_name and pull_number:
            try:
                filenames = await self.client.list_pull_request_files(
                    owner_name,
                    repo_name,
                    pull_number,
                    installation_token=installation_token,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("pull_request_file_listing_failed: %s", exc)

        assessment = assess_pull_request_intent(
            action=action,
            actor=actor,
            repository=full_name,
            title=str(pull_request.get("title") or ""),
            body=str(pull_request.get("body") or ""),
            additions=int(pull_request.get("additions") or 0),
            deletions=int(pull_request.get("deletions") or 0),
            changed_files_count=int(pull_request.get("changed_files") or len(filenames)),
            filenames=filenames,
            head_sha=head_sha,
        )

        if owner_name and repo_name and head_sha:
            await self.client.create_check_run(
                owner_name,
                repo_name,
                installation_token=installation_token,
                name=self.config.check_name,
                head_sha=head_sha,
                conclusion=self._decision_to_conclusion(assessment.decision),
                title=f"{self.config.check_name}: {assessment.decision}",
                summary=self._build_check_summary(assessment),
                text=self._build_check_text(assessment),
                external_id=delivery_id,
            )

        if owner_name and repo_name and pull_number and self._should_comment(assessment.decision):
            try:
                await self.client.post_issue_comment(
                    owner_name,
                    repo_name,
                    pull_number,
                    self._build_issue_comment(assessment),
                    installation_token=installation_token,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("pull_request_comment_failed: %s", exc)

        return {
            "status": "processed",
            "event": event,
            "action": action,
            "repository": full_name,
            "pull_request": pull_number,
            "decision": assessment.decision,
            "safety_score": assessment.safety_score,
            "trust_ring": assessment.trust_ring,
        }

    def _should_comment(self, decision: str) -> bool:
        mode = self.config.comment_mode
        if mode == "off":
            return False
        if mode in {"deny-only", "deny"}:
            return decision == "DENY"
        if mode in {"review-only", "quarantine+deny"}:
            return decision != "ALLOW"
        return True

    @staticmethod
    def _decision_to_conclusion(decision: str) -> str:
        if decision == "ALLOW":
            return "success"
        if decision == "DENY":
            return "failure"
        return "action_required"

    def _build_check_summary(self, assessment: PullRequestIntentAssessment) -> str:
        reason = assessment.reasons[0] if assessment.reasons else "no additional detail"
        return (
            f"Decision: **{assessment.decision}**\n\n"
            f"- Safety score: `{assessment.safety_score}`\n"
            f"- Trust ring: `{assessment.trust_ring}`\n"
            f"- Davis score: `{assessment.davis_score}`\n"
            f"- Primary reason: {reason}"
        )

    def _build_check_text(self, assessment: PullRequestIntentAssessment) -> str:
        lines = [
            f"Base score: {assessment.base_score}",
            f"Trust score: {assessment.trust_score}",
            f"Sensitivity: {assessment.sensitivity}",
            f"Drift: {assessment.drift}",
            f"Energy cost: {assessment.energy_cost}",
        ]
        if assessment.risk_hits:
            lines.append(f"Risk hits: {', '.join(assessment.risk_hits)}")
        if assessment.privileged_files:
            lines.append(f"Privileged files: {', '.join(assessment.privileged_files[:10])}")
        return "\n".join(lines)

    def _build_issue_comment(self, assessment: PullRequestIntentAssessment) -> str:
        bullets = "\n".join(f"- {reason}" for reason in assessment.reasons)
        return (
            f"**{self.config.check_name} {assessment.decision}**\n\n"
            f"Safety score: `{assessment.safety_score}`\n"
            f"Trust ring: `{assessment.trust_ring}`\n"
            f"Davis score: `{assessment.davis_score}`\n\n"
            f"{bullets}"
        )
