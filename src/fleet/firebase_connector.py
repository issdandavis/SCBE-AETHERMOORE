"""
Firebase Connector — Persistent Backend for PollyPad + OctoArmor + AetherNet
=============================================================================

Connects SCBE to Firebase for:
- PollyPad session persistence (Firestore)
- Training data sync (Cloud Storage)
- Agent identity registry (Firestore)
- Real-time tentacle status (Firestore)
- AetherNet social platform (posts, tasks, leaderboards, training pairs)

Setup::

    # Option 1: Service account key (local dev)
    export FIREBASE_CREDENTIALS_PATH=path/to/serviceAccountKey.json
    export FIREBASE_PROJECT_ID=studio-6928670609-fdd4c

    # Option 2: Default credentials (Cloud Run, GCE, etc.)
    export FIREBASE_PROJECT_ID=studio-6928670609-fdd4c

Usage::

    from src.fleet.firebase_connector import FirebaseSync
    fb = FirebaseSync()
    fb.save_session(session_data)
    fb.push_training_batch(pairs)
    fb.save_tentacle_snapshot(status)

    # AetherNet social platform
    fb.save_post({"post_id": "p1", "content": "...", "tongue": "KO"})
    fb.get_feed(channel="general", limit=20)
    fb.save_task({"task_id": "t1", "title": "...", "status": "available"})
    fb.get_available_tasks()
    fb.update_agent_score("agent-42", {"governance_score": 0.95, "xp": 120})
    fb.get_leaderboard()
    fb.save_training_pair({"instruction": "...", "output": "..."})
    fb.get_platform_stats()

@module fleet/firebase_connector
"""

from __future__ import annotations

import json
import os
import site
import time
import uuid
import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.security import get_secret

# Load .env from repo root (two parents up from src/fleet/)
REPO_ROOT = Path(__file__).resolve().parents[2]
_env_path = REPO_ROOT / ".env"
if _env_path.exists():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                if _v and _k.strip():
                    os.environ.setdefault(_k.strip(), _v.strip())


def _ensure_google_cloud_namespace() -> None:
    """Ensure google.cloud namespace can see user-site packages on Windows.

    Some setups install google-cloud-firestore in user site-packages while a
    base google.cloud namespace exists in system site-packages. In that case,
    firestore imports can fail unless both paths are visible on google.cloud.
    """
    try:
        user_cloud = Path(site.getusersitepackages()) / "google" / "cloud"
        if not user_cloud.exists():
            return
        cloud_pkg = importlib.import_module("google.cloud")
        namespace = getattr(cloud_pkg, "__path__", None)
        if namespace is None:
            return
        user_cloud_str = str(user_cloud)
        if user_cloud_str not in namespace:
            namespace.append(user_cloud_str)
    except Exception:
        # Best-effort compatibility shim; never block normal initialization.
        return


class FirebaseSync:
    """Firebase Firestore + Storage sync for SCBE services."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
    ):
        self.project_id = (
            project_id
            or os.environ.get("FIREBASE_PROJECT_ID")
            or get_secret("FIREBASE_PROJECT_ID")
            or "studio-6928670609-fdd4c"
        )
        self.credentials_path = credentials_path or os.environ.get(
            "FIREBASE_CREDENTIALS_PATH", ""
        )
        self.inline_credentials_json = (
            os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY", "")
            or os.environ.get("FIREBASE_CREDENTIALS_JSON", "")
            or get_secret("FIREBASE_SERVICE_ACCOUNT_KEY")
            or get_secret("FIREBASE_CREDENTIALS_JSON")
            or ""
        )
        self._service_account_dict: Optional[Dict[str, Any]] = None
        self._db = None
        self._storage = None
        self._initialized = False

    def _service_account_from_secret(self) -> Optional[Dict[str, Any]]:
        """Load service account JSON from env/secret-store when provided."""
        if self._service_account_dict is not None:
            return self._service_account_dict
        raw = (self.inline_credentials_json or "").strip()
        if not raw:
            self._service_account_dict = None
            return None
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            self._service_account_dict = None
            return None
        if isinstance(loaded, dict):
            self._service_account_dict = loaded
            return loaded
        self._service_account_dict = None
        return None

    @property
    def has_inline_service_account(self) -> bool:
        return self._service_account_from_secret() is not None

    def initialize(self) -> bool:
        """Initialize Firebase Admin SDK. Returns True on success."""
        if self._initialized:
            return True
        try:
            _ensure_google_cloud_namespace()
            import firebase_admin
            from firebase_admin import credentials as fb_creds, firestore

            if not firebase_admin._apps:
                if self.credentials_path and Path(self.credentials_path).exists():
                    cred = fb_creds.Certificate(self.credentials_path)
                    firebase_admin.initialize_app(
                        cred, {"projectId": self.project_id}
                    )
                elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                    google_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"].strip()
                    if google_path and Path(google_path).exists():
                        cred = fb_creds.Certificate(google_path)
                        firebase_admin.initialize_app(
                            cred, {"projectId": self.project_id}
                        )
                    else:
                        # Continue to inline secret or ADC fallback.
                        service_account = self._service_account_from_secret()
                        if service_account is None:
                            firebase_admin.initialize_app(
                                options={"projectId": self.project_id}
                            )
                        else:
                            firebase_admin.initialize_app(
                                fb_creds.Certificate(service_account),
                                {"projectId": self.project_id},
                            )
                else:
                    service_account = self._service_account_from_secret()
                    if service_account is None:
                        # Application Default Credentials (ADC) or emulator
                        firebase_admin.initialize_app(
                            options={"projectId": self.project_id}
                        )
                    else:
                        firebase_admin.initialize_app(
                            fb_creds.Certificate(service_account),
                            {"projectId": self.project_id},
                        )

            self._db = firestore.client()
            self._initialized = True
            return True
        except Exception as exc:
            print(f"[Firebase] Init failed: {exc}")
            return False

    @property
    def connected(self) -> bool:
        return self._initialized and self._db is not None

    def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """Verify Firebase Auth ID token and return decoded claims."""
        if not self.connected or not id_token:
            return {}
        try:
            from firebase_admin import auth as fb_auth
            decoded = fb_auth.verify_id_token(id_token)
            return decoded if isinstance(decoded, dict) else {}
        except Exception:
            return {}

    # ─── PollyPad Sessions ───────────────────────────────

    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """Save or update a PollyPad IDE session."""
        if not self.connected:
            return False
        try:
            session_id = session_data.get("session_id", "unknown")
            doc_ref = self._db.collection("pollypad_sessions").document(session_id)
            session_data["updated_at"] = time.time()
            doc_ref.set(session_data, merge=True)
            return True
        except Exception as exc:
            print(f"[Firebase] save_session error: {exc}")
            return False

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a session from Firestore."""
        if not self.connected:
            return None
        try:
            doc = self._db.collection("pollypad_sessions").document(session_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception:
            return None

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent sessions."""
        if not self.connected:
            return []
        try:
            docs = (
                self._db.collection("pollypad_sessions")
                .order_by("updated_at", direction="DESCENDING")
                .limit(limit)
                .stream()
            )
            return [doc.to_dict() for doc in docs]
        except Exception:
            return []

    # ─── Training Data ───────────────────────────────────

    def push_training_batch(self, pairs: List[Dict[str, str]]) -> bool:
        """Push training pairs to Firestore (for later HF sync)."""
        if not self.connected or not pairs:
            return False
        try:
            batch = self._db.batch()
            collection = self._db.collection("training_pairs")
            for pair in pairs[:500]:  # Max 500 per batch write
                doc_ref = collection.document()
                pair["pushed_at"] = time.time()
                batch.set(doc_ref, pair)
            batch.commit()
            return True
        except Exception as exc:
            print(f"[Firebase] push_training error: {exc}")
            return False

    def get_training_stats(self) -> Dict[str, Any]:
        """Get training data stats from Firestore."""
        if not self.connected:
            return {"connected": False}
        try:
            # Count documents (approximation via aggregation)
            collection = self._db.collection("training_pairs")
            # Simple count via streaming first 1000
            count = 0
            for _ in collection.limit(1000).stream():
                count += 1
            return {
                "connected": True,
                "approximate_pairs": count,
                "capped_at": 1000 if count >= 1000 else None,
            }
        except Exception:
            return {"connected": True, "approximate_pairs": 0}

    # ─── Tentacle Snapshots ──────────────────────────────

    def save_tentacle_snapshot(self, status: List[Dict[str, Any]]) -> bool:
        """Save current tentacle status to Firestore for monitoring."""
        if not self.connected:
            return False
        try:
            doc_ref = self._db.collection("tentacle_snapshots").document("latest")
            doc_ref.set({
                "tentacles": status,
                "snapshot_at": time.time(),
                "available": sum(1 for t in status if t.get("available")),
                "total": len(status),
            })
            return True
        except Exception:
            return False

    # ─── Agent Registry ──────────────────────────────────

    def register_agent(self, agent_id: str, metadata: Dict[str, Any]) -> bool:
        """Register an AI agent in the Firebase agent registry."""
        if not self.connected:
            return False
        try:
            doc_ref = self._db.collection("agent_registry").document(agent_id)
            metadata["registered_at"] = time.time()
            metadata["agent_id"] = agent_id
            doc_ref.set(metadata, merge=True)
            return True
        except Exception:
            return False

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent data from registry."""
        if not self.connected:
            return None
        try:
            doc = self._db.collection("agent_registry").document(agent_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception:
            return None

    # ─── AetherNet Social ─────────────────────────────────

    def save_post(self, post_data: Dict[str, Any]) -> bool:
        """Save a social feed post to the aethernet_posts collection.

        Expected fields in post_data:
            post_id (str): Unique post identifier (auto-generated if absent).
            content (str): Post body text.
            author_id (str): Agent or user who authored the post.
            channel (str): Feed channel (e.g. "general", "research", "lore").
            tongue (str): Sacred Tongue tag (KO/AV/RU/CA/UM/DR).
            governance_decision (str): ALLOW / QUARANTINE / ESCALATE / DENY.
        """
        if not self.connected:
            return False
        try:
            post_id = post_data.get("post_id") or str(uuid.uuid4())
            post_data["post_id"] = post_id
            post_data.setdefault("created_at", time.time())
            post_data["updated_at"] = time.time()
            doc_ref = self._db.collection("aethernet_posts").document(post_id)
            doc_ref.set(post_data, merge=True)
            return True
        except Exception as exc:
            print(f"[Firebase] save_post error: {exc}")
            return False

    def create_platform_dispatch_rows(self, post_id: str, platforms: List[str], status: str = "queued") -> bool:
        """Create a dispatch row for each platform for the given post."""
        if not self.connected:
            return False
        try:
            if not post_id:
                return False
            now = time.time()
            batch = self._db.batch()
            unique = sorted(set(p.lower().strip() for p in platforms if str(p).strip()))
            for platform in unique:
                doc_ref = self._db.collection("aethernet_platform_dispatch").document()
                batch.set(
                    doc_ref,
                    {
                        "post_id": post_id,
                        "platform": platform,
                        "status": status,
                        "attempts": 0,
                        "last_attempt_at": None,
                        "result": {},
                        "updated_at": now,
                        "created_at": now,
                    },
                )
            batch.commit()
            return True
        except Exception as exc:
            print(f"[Firebase] create_platform_dispatch_rows error: {exc}")
            return False

    def update_platform_dispatch(
        self,
        post_id: str,
        platform: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        attempts: Optional[int] = None,
    ) -> bool:
        """Update the newest dispatch row for platform + post."""
        if not self.connected or not post_id or not platform:
            return False
        normalized = platform.lower().strip()
        now = time.time()
        try:
            q = (
                self._db.collection("aethernet_platform_dispatch")
                .where("post_id", "==", post_id)
                .where("platform", "==", normalized)
                .order_by("updated_at", direction="DESCENDING")
                .limit(1)
            )
            docs = list(q.stream())
            if docs:
                row = docs[0]
                payload = {
                    "status": status,
                    "last_attempt_at": now,
                    "updated_at": now,
                }
                if attempts is not None:
                    payload["attempts"] = attempts
                if result is not None:
                    payload["result"] = result
                row.reference.set(payload, merge=True)
                return True

            # If no existing row exists, create a single row
            doc_ref = self._db.collection("aethernet_platform_dispatch").document()
            doc_ref.set(
                {
                    "post_id": post_id,
                    "platform": normalized,
                    "status": status,
                    "attempts": attempts or 0,
                    "last_attempt_at": now,
                    "result": result or {},
                    "updated_at": now,
                    "created_at": now,
                }
            )
            return True
        except Exception as exc:
            print(f"[Firebase] update_platform_dispatch error: {exc}")
            return False

    def save_reply(self, reply_data: Dict[str, Any]) -> bool:
        """Persist a reply in aethernet_replies."""
        if not self.connected:
            return False
        try:
            reply_id = reply_data.get("reply_id") or str(uuid.uuid4())
            reply_data["reply_id"] = reply_id
            reply_data.setdefault("created_at", time.time())
            doc_ref = self._db.collection("aethernet_replies").document(reply_id)
            doc_ref.set(reply_data)
            return True
        except Exception as exc:
            print(f"[Firebase] save_reply error: {exc}")
            return False

    def save_reaction(self, reaction_data: Dict[str, Any]) -> bool:
        """Persist a reaction in aethernet_reactions."""
        if not self.connected:
            return False
        try:
            reaction_id = reaction_data.get("reaction_id") or str(uuid.uuid4())
            reaction_data["reaction_id"] = reaction_id
            reaction_data.setdefault("created_at", time.time())
            doc_ref = self._db.collection("aethernet_reactions").document(reaction_id)
            doc_ref.set(reaction_data)
            return True
        except Exception as exc:
            print(f"[Firebase] save_reaction error: {exc}")
            return False

    def record_governance_event(self, event_data: Dict[str, Any]) -> bool:
        """Persist governance decision for audit trail."""
        if not self.connected:
            return False
        try:
            event_id = event_data.get("event_id") or str(uuid.uuid4())
            event_data["event_id"] = event_id
            event_data.setdefault("timestamp", time.time())
            doc_ref = self._db.collection("governance_events").document(event_id)
            doc_ref.set(event_data)
            return True
        except Exception as exc:
            print(f"[Firebase] record_governance_event error: {exc}")
            return False

    def get_feed_since(self, since: float, limit: int = 50) -> List[Dict[str, Any]]:
        """Get feed posts created after a timestamp from Firestore."""
        if not self.connected:
            return []
        try:
            docs = (
                self._db.collection("aethernet_posts")
                .where("created_at", ">", since)
                .order_by("created_at", direction="ASCENDING")
                .limit(limit)
                .stream()
            )
            return [doc.to_dict() for doc in docs]
        except Exception as exc:
            print(f"[Firebase] get_feed_since error: {exc}")
            return []

    def get_feed(self, channel: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get recent posts, optionally filtered by channel.

        Args:
            channel: If provided, only return posts from this channel.
            limit: Maximum number of posts to return (default 50).

        Returns:
            List of post dicts ordered by created_at descending.
        """
        if not self.connected:
            return []
        try:
            query = self._db.collection("aethernet_posts")
            if channel:
                query = query.where("channel", "==", channel)
            docs = (
                query
                .order_by("created_at", direction="DESCENDING")
                .limit(limit)
                .stream()
            )
            return [doc.to_dict() for doc in docs]
        except Exception as exc:
            print(f"[Firebase] get_feed error: {exc}")
            return []

    def save_task(self, task_data: Dict[str, Any]) -> bool:
        """Save a task that agents can claim and complete.

        Expected fields in task_data:
            task_id (str): Unique task identifier (auto-generated if absent).
            title (str): Short task description.
            description (str): Full task details.
            status (str): "available" | "claimed" | "completed" | "expired".
            reward_xp (int): XP awarded on completion.
            tongue (str): Sacred Tongue affinity.
            claimed_by (str|None): Agent ID that claimed the task.
        """
        if not self.connected:
            return False
        try:
            task_id = task_data.get("task_id") or str(uuid.uuid4())
            task_data["task_id"] = task_id
            task_data.setdefault("status", "available")
            task_data.setdefault("created_at", time.time())
            task_data["updated_at"] = time.time()
            doc_ref = self._db.collection("aethernet_tasks").document(task_id)
            doc_ref.set(task_data, merge=True)
            return True
        except Exception as exc:
            print(f"[Firebase] save_task error: {exc}")
            return False

    def save_task_claim(
        self,
        task_id: str,
        agent_id: str,
        action: str,
        status: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record one task claim/submission audit event."""
        if not self.connected:
            return False
        try:
            doc_ref = self._db.collection("aethernet_task_claims").document()
            doc_ref.set({
                "task_id": task_id,
                "agent_id": agent_id,
                "action": action,
                "status": status,
                "timestamp": time.time(),
                "payload": payload or {},
            })
            return True
        except Exception as exc:
            print(f"[Firebase] save_task_claim error: {exc}")
            return False

    def get_task_claims(
        self,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch recent task claim events."""
        if not self.connected:
            return []
        try:
            query = self._db.collection("aethernet_task_claims")
            if task_id:
                query = query.where("task_id", "==", task_id)
            if agent_id:
                query = query.where("agent_id", "==", agent_id)
            docs = (
                query.order_by("timestamp", direction="DESCENDING")
                .limit(limit)
                .stream()
            )
            return [doc.to_dict() for doc in docs]
        except Exception as exc:
            print(f"[Firebase] get_task_claims error: {exc}")
            return []

    def get_available_tasks(self, limit: int = 20) -> List[Dict]:
        """Get unclaimed tasks (status == 'available').

        Args:
            limit: Maximum number of tasks to return (default 20).

        Returns:
            List of task dicts with status 'available'.
        """
        if not self.connected:
            return []
        try:
            docs = (
                self._db.collection("aethernet_tasks")
                .where("status", "==", "available")
                .order_by("created_at", direction="DESCENDING")
                .limit(limit)
                .stream()
            )
            return [doc.to_dict() for doc in docs]
        except Exception as exc:
            print(f"[Firebase] get_available_tasks error: {exc}")
            return []

    def update_agent_score(self, agent_id: str, score_data: Dict[str, Any]) -> bool:
        """Update an agent's governance score and XP in the agent_registry.

        Args:
            agent_id: The agent's unique identifier.
            score_data: Dict with fields like governance_score, xp, level,
                        tasks_completed, posts_count, etc.

        Returns:
            True on success.
        """
        if not self.connected:
            return False
        try:
            doc_ref = self._db.collection("agent_registry").document(agent_id)
            score_data["agent_id"] = agent_id
            score_data["score_updated_at"] = time.time()
            doc_ref.set(score_data, merge=True)
            return True
        except Exception as exc:
            print(f"[Firebase] update_agent_score error: {exc}")
            return False

    def get_leaderboard(self, limit: int = 20) -> List[Dict]:
        """Get top agents by governance score.

        Args:
            limit: Number of top agents to return (default 20).

        Returns:
            List of agent dicts ordered by governance_score descending.
        """
        if not self.connected:
            return []
        try:
            docs = (
                self._db.collection("agent_registry")
                .order_by("governance_score", direction="DESCENDING")
                .limit(limit)
                .stream()
            )
            return [doc.to_dict() for doc in docs]
        except Exception as exc:
            print(f"[Firebase] get_leaderboard error: {exc}")
            return []

    def save_training_pair(self, pair: Dict[str, str]) -> bool:
        """Save a single training pair from an AetherNet interaction.

        Args:
            pair: Dict with at minimum 'instruction' and 'output' fields.
                  May also include 'tongue', 'source', 'governance_decision'.

        Returns:
            True on success.
        """
        if not self.connected:
            return False
        try:
            pair["pushed_at"] = time.time()
            pair.setdefault("source", "aethernet")
            doc_ref = self._db.collection("training_pairs").document()
            doc_ref.set(pair)
            return True
        except Exception as exc:
            print(f"[Firebase] save_training_pair error: {exc}")
            return False

    def get_platform_stats(self) -> Dict[str, Any]:
        """Get aggregate AetherNet platform statistics.

        Counts documents across key collections: agent_registry,
        aethernet_posts, aethernet_tasks, training_pairs.

        Returns:
            Dict with counts per collection and overall status.
        """
        if not self.connected:
            return {"connected": False}
        try:
            counts = {}
            for coll_name in [
                "agent_registry",
                "aethernet_posts",
                "aethernet_tasks",
                "training_pairs",
                "aethernet_replies",
                "aethernet_reactions",
                "aethernet_platform_dispatch",
                "governance_events",
            ]:
                count = 0
                for _ in self._db.collection(coll_name).limit(10000).stream():
                    count += 1
                counts[coll_name] = count
            return {
                "connected": True,
                "agents": counts.get("agent_registry", 0),
                "posts": counts.get("aethernet_posts", 0),
                "tasks": counts.get("aethernet_tasks", 0),
                "training_pairs": counts.get("training_pairs", 0),
                "replies": counts.get("aethernet_replies", 0),
                "reactions": counts.get("aethernet_reactions", 0),
                "dispatch_rows": counts.get("aethernet_platform_dispatch", 0),
                "governance_events": counts.get("governance_events", 0),
                "counted_at": time.time(),
            }
        except Exception as exc:
            print(f"[Firebase] get_platform_stats error: {exc}")
            return {"connected": True, "error": str(exc)}

    # ─── Diagnostics ─────────────────────────────────────

    def diagnostics(self) -> Dict[str, Any]:
        """Firebase connection diagnostics."""
        return {
            "initialized": self._initialized,
            "connected": self.connected,
            "project_id": self.project_id,
            "credentials_path": self.credentials_path or "(default/ADC)",
            "inline_service_account": bool(self.inline_credentials_json),
            "service_account_from_secret": self.has_inline_service_account,
            "collections": [
                "pollypad_sessions",
                "training_pairs",
                "tentacle_snapshots",
                "agent_registry",
                "aethernet_posts",
                "aethernet_tasks",
                "aethernet_replies",
                "aethernet_reactions",
                "aethernet_platform_dispatch",
                "governance_events",
            ],
        }
