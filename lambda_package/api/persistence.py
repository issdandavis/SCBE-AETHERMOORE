"""
SCBE Firebase Persistence Layer

Provides database persistence for:
- Audit logs (immutable decision records)
- Trust scores (agent trust history)
- Agent registry (registered AI agents)
- Alerts (for Zapier/webhook integration)

Setup:
1. Create Firebase project at https://console.firebase.google.com
2. Download service account key JSON
3. Set environment variable: GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
   OR set FIREBASE_CONFIG with the JSON content directly
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Literal
from dataclasses import dataclass, asdict
import hashlib

logger = logging.getLogger(__name__)

# Lazy initialization - only import Firebase when needed
_db = None
_initialized = False


def _get_db():
    """Lazy initialization of Firebase."""
    global _db, _initialized

    if _initialized:
        return _db

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        # Check for credentials
        cred = None

        # Option 1: GOOGLE_APPLICATION_CREDENTIALS environment variable (file path)
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            cred = credentials.ApplicationDefault()

        # Option 2: FIREBASE_CONFIG with JSON content
        elif os.getenv("FIREBASE_CONFIG"):
            config = json.loads(os.getenv("FIREBASE_CONFIG"))
            cred = credentials.Certificate(config)

        # Option 3: FIREBASE_SERVICE_ACCOUNT_KEY with JSON content
        elif os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"):
            config = json.loads(os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"))
            cred = credentials.Certificate(config)

        else:
            logger.warning(
                "Firebase credentials not configured. "
                "Set GOOGLE_APPLICATION_CREDENTIALS or FIREBASE_CONFIG. "
                "Persistence will be disabled."
            )
            _initialized = True
            return None

        # Initialize Firebase app
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)

        _db = firestore.client()
        _initialized = True
        logger.info("Firebase Firestore initialized successfully")
        return _db

    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        _initialized = True
        return None


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class AuditLog:
    """Immutable audit log entry for compliance."""
    audit_id: str
    timestamp: str
    agent_id: str
    action: str
    decision: Literal["ALLOW", "QUARANTINE", "DENY"]
    trust_score: float
    risk_level: str
    context: dict
    consensus_result: dict
    request_hash: str  # SHA-256 of request for integrity

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrustRecord:
    """Trust score record for an agent."""
    agent_id: str
    timestamp: str
    trust_score: float
    factors: dict
    decision: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AgentRecord:
    """Registered AI agent."""
    agent_id: str
    name: str
    description: str
    registered_at: str
    status: Literal["active", "suspended", "revoked"]
    trust_baseline: float
    policy_id: str
    metadata: dict

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Alert:
    """Alert for webhook/Zapier integration."""
    alert_id: str
    timestamp: str
    severity: Literal["low", "medium", "high", "critical"]
    alert_type: str
    message: str
    agent_id: Optional[str]
    audit_id: Optional[str]
    data: dict
    sent: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# Persistence Functions
# =============================================================================

class SCBEPersistence:
    """Main persistence class for SCBE."""

    COLLECTION_AUDIT = "scbe_audit_logs"
    COLLECTION_TRUST = "scbe_trust_history"
    COLLECTION_AGENTS = "scbe_agents"
    COLLECTION_ALERTS = "scbe_alerts"

    def __init__(self):
        self.db = _get_db()
        self._local_cache = {
            "audit": [],
            "trust": [],
            "agents": {},
            "alerts": []
        }

    @property
    def is_connected(self) -> bool:
        return self.db is not None

    # -------------------------------------------------------------------------
    # Audit Logs
    # -------------------------------------------------------------------------

    def log_decision(
        self,
        agent_id: str,
        action: str,
        decision: str,
        trust_score: float,
        risk_level: str,
        context: dict,
        consensus_result: dict
    ) -> str:
        """Log a governance decision. Returns audit_id."""

        timestamp = datetime.now(timezone.utc).isoformat()

        # Generate audit ID
        audit_id = f"audit-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{hashlib.sha256(f'{agent_id}{timestamp}'.encode()).hexdigest()[:8]}"

        # Hash the request for integrity verification
        request_content = json.dumps({
            "agent_id": agent_id,
            "action": action,
            "context": context,
            "timestamp": timestamp
        }, sort_keys=True)
        request_hash = hashlib.sha256(request_content.encode()).hexdigest()

        audit_log = AuditLog(
            audit_id=audit_id,
            timestamp=timestamp,
            agent_id=agent_id,
            action=action,
            decision=decision,
            trust_score=trust_score,
            risk_level=risk_level,
            context=context,
            consensus_result=consensus_result,
            request_hash=request_hash
        )

        # Store in Firebase
        if self.db:
            try:
                self.db.collection(self.COLLECTION_AUDIT).document(audit_id).set(
                    audit_log.to_dict()
                )
                logger.info(f"Audit log stored: {audit_id}")
            except Exception as e:
                logger.error(f"Failed to store audit log: {e}")
                self._local_cache["audit"].append(audit_log.to_dict())
        else:
            self._local_cache["audit"].append(audit_log.to_dict())

        # Create alert for DENY or QUARANTINE decisions
        if decision in ["DENY", "QUARANTINE"]:
            severity = "high" if decision == "DENY" else "medium"
            self.create_alert(
                severity=severity,
                alert_type=f"decision_{decision.lower()}",
                message=f"Agent {agent_id} request was {decision}: {action}",
                agent_id=agent_id,
                audit_id=audit_id,
                data={"trust_score": trust_score, "risk_level": risk_level}
            )

        return audit_id

    def get_audit_log(self, audit_id: str) -> Optional[dict]:
        """Retrieve an audit log by ID."""
        if self.db:
            try:
                doc = self.db.collection(self.COLLECTION_AUDIT).document(audit_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.error(f"Failed to get audit log: {e}")

        # Check local cache
        for log in self._local_cache["audit"]:
            if log["audit_id"] == audit_id:
                return log
        return None

    def get_audit_logs(
        self,
        agent_id: Optional[str] = None,
        decision: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """Query audit logs with optional filters."""
        if self.db:
            try:
                query = self.db.collection(self.COLLECTION_AUDIT)

                if agent_id:
                    query = query.where("agent_id", "==", agent_id)
                if decision:
                    query = query.where("decision", "==", decision)

                query = query.order_by("timestamp", direction="DESCENDING").limit(limit)

                return [doc.to_dict() for doc in query.stream()]
            except Exception as e:
                logger.error(f"Failed to query audit logs: {e}")

        # Return from local cache
        logs = self._local_cache["audit"]
        if agent_id:
            logs = [l for l in logs if l["agent_id"] == agent_id]
        if decision:
            logs = [l for l in logs if l["decision"] == decision]
        return logs[:limit]

    # -------------------------------------------------------------------------
    # Trust History
    # -------------------------------------------------------------------------

    def record_trust(
        self,
        agent_id: str,
        trust_score: float,
        factors: dict,
        decision: str
    ) -> None:
        """Record trust score for historical analysis."""

        timestamp = datetime.now(timezone.utc).isoformat()

        record = TrustRecord(
            agent_id=agent_id,
            timestamp=timestamp,
            trust_score=trust_score,
            factors=factors,
            decision=decision
        )

        if self.db:
            try:
                # Use auto-generated ID
                self.db.collection(self.COLLECTION_TRUST).add(record.to_dict())
            except Exception as e:
                logger.error(f"Failed to record trust: {e}")
                self._local_cache["trust"].append(record.to_dict())
        else:
            self._local_cache["trust"].append(record.to_dict())

    def get_trust_history(self, agent_id: str, limit: int = 30) -> list:
        """Get trust score history for an agent."""
        if self.db:
            try:
                query = (
                    self.db.collection(self.COLLECTION_TRUST)
                    .where("agent_id", "==", agent_id)
                    .order_by("timestamp", direction="DESCENDING")
                    .limit(limit)
                )
                return [doc.to_dict() for doc in query.stream()]
            except Exception as e:
                logger.error(f"Failed to get trust history: {e}")

        return [r for r in self._local_cache["trust"] if r["agent_id"] == agent_id][:limit]

    def get_trust_trend(self, agent_id: str, days: int = 7) -> dict:
        """Analyze trust score trend."""
        history = self.get_trust_history(agent_id, limit=days * 24)  # Assume hourly

        if not history:
            return {"trend": "unknown", "average": 0.0, "change": 0.0}

        scores = [h["trust_score"] for h in history]
        avg = sum(scores) / len(scores)

        if len(scores) >= 2:
            recent = scores[:len(scores)//2]
            older = scores[len(scores)//2:]
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            change = recent_avg - older_avg

            if change > 0.05:
                trend = "improving"
            elif change < -0.05:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
            change = 0.0

        return {"trend": trend, "average": avg, "change": change}

    # -------------------------------------------------------------------------
    # Agent Registry
    # -------------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        policy_id: str = "default",
        trust_baseline: float = 0.5,
        metadata: dict = None
    ) -> AgentRecord:
        """Register a new AI agent."""

        record = AgentRecord(
            agent_id=agent_id,
            name=name,
            description=description,
            registered_at=datetime.now(timezone.utc).isoformat(),
            status="active",
            trust_baseline=trust_baseline,
            policy_id=policy_id,
            metadata=metadata or {}
        )

        if self.db:
            try:
                self.db.collection(self.COLLECTION_AGENTS).document(agent_id).set(
                    record.to_dict()
                )
                logger.info(f"Agent registered: {agent_id}")
            except Exception as e:
                logger.error(f"Failed to register agent: {e}")
                self._local_cache["agents"][agent_id] = record.to_dict()
        else:
            self._local_cache["agents"][agent_id] = record.to_dict()

        return record

    def get_agent(self, agent_id: str) -> Optional[dict]:
        """Get agent by ID."""
        if self.db:
            try:
                doc = self.db.collection(self.COLLECTION_AGENTS).document(agent_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.error(f"Failed to get agent: {e}")

        return self._local_cache["agents"].get(agent_id)

    def update_agent_status(
        self,
        agent_id: str,
        status: Literal["active", "suspended", "revoked"]
    ) -> bool:
        """Update agent status."""
        if self.db:
            try:
                self.db.collection(self.COLLECTION_AGENTS).document(agent_id).update({
                    "status": status
                })
                return True
            except Exception as e:
                logger.error(f"Failed to update agent status: {e}")

        if agent_id in self._local_cache["agents"]:
            self._local_cache["agents"][agent_id]["status"] = status
            return True
        return False

    def list_agents(self, status: Optional[str] = None) -> list:
        """List all agents, optionally filtered by status."""
        if self.db:
            try:
                query = self.db.collection(self.COLLECTION_AGENTS)
                if status:
                    query = query.where("status", "==", status)
                return [doc.to_dict() for doc in query.stream()]
            except Exception as e:
                logger.error(f"Failed to list agents: {e}")

        agents = list(self._local_cache["agents"].values())
        if status:
            agents = [a for a in agents if a["status"] == status]
        return agents

    # -------------------------------------------------------------------------
    # Alerts (for Zapier/Webhooks)
    # -------------------------------------------------------------------------

    def create_alert(
        self,
        severity: str,
        alert_type: str,
        message: str,
        agent_id: Optional[str] = None,
        audit_id: Optional[str] = None,
        data: dict = None
    ) -> str:
        """Create an alert for webhook delivery."""

        timestamp = datetime.now(timezone.utc).isoformat()
        alert_id = f"alert-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{hashlib.sha256(timestamp.encode()).hexdigest()[:6]}"

        alert = Alert(
            alert_id=alert_id,
            timestamp=timestamp,
            severity=severity,
            alert_type=alert_type,
            message=message,
            agent_id=agent_id,
            audit_id=audit_id,
            data=data or {},
            sent=False
        )

        if self.db:
            try:
                self.db.collection(self.COLLECTION_ALERTS).document(alert_id).set(
                    alert.to_dict()
                )
            except Exception as e:
                logger.error(f"Failed to create alert: {e}")
                self._local_cache["alerts"].append(alert.to_dict())
        else:
            self._local_cache["alerts"].append(alert.to_dict())

        logger.warning(f"ALERT [{severity.upper()}]: {message}")
        return alert_id

    def get_pending_alerts(self, limit: int = 50) -> list:
        """Get alerts that haven't been sent to webhooks yet."""
        if self.db:
            try:
                query = (
                    self.db.collection(self.COLLECTION_ALERTS)
                    .where("sent", "==", False)
                    .order_by("timestamp", direction="DESCENDING")
                    .limit(limit)
                )
                return [doc.to_dict() for doc in query.stream()]
            except Exception as e:
                logger.error(f"Failed to get pending alerts: {e}")

        return [a for a in self._local_cache["alerts"] if not a["sent"]][:limit]

    def mark_alert_sent(self, alert_id: str) -> bool:
        """Mark an alert as sent."""
        if self.db:
            try:
                self.db.collection(self.COLLECTION_ALERTS).document(alert_id).update({
                    "sent": True
                })
                return True
            except Exception as e:
                logger.error(f"Failed to mark alert sent: {e}")

        for alert in self._local_cache["alerts"]:
            if alert["alert_id"] == alert_id:
                alert["sent"] = True
                return True
        return False

    # -------------------------------------------------------------------------
    # Metrics
    # -------------------------------------------------------------------------

    def get_metrics(self, hours: int = 24) -> dict:
        """Get decision metrics for monitoring."""
        logs = self.get_audit_logs(limit=1000)

        if not logs:
            return {
                "total_decisions": 0,
                "allow_count": 0,
                "quarantine_count": 0,
                "deny_count": 0,
                "allow_rate": 0.0,
                "quarantine_rate": 0.0,
                "deny_rate": 0.0,
                "avg_trust_score": 0.0
            }

        total = len(logs)
        allow_count = sum(1 for l in logs if l["decision"] == "ALLOW")
        quarantine_count = sum(1 for l in logs if l["decision"] == "QUARANTINE")
        deny_count = sum(1 for l in logs if l["decision"] == "DENY")
        avg_trust = sum(l["trust_score"] for l in logs) / total if total > 0 else 0

        return {
            "total_decisions": total,
            "allow_count": allow_count,
            "quarantine_count": quarantine_count,
            "deny_count": deny_count,
            "allow_rate": allow_count / total if total > 0 else 0,
            "quarantine_rate": quarantine_count / total if total > 0 else 0,
            "deny_rate": deny_count / total if total > 0 else 0,
            "avg_trust_score": avg_trust
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_persistence_instance = None

def get_persistence() -> SCBEPersistence:
    """Get the singleton persistence instance."""
    global _persistence_instance
    if _persistence_instance is None:
        _persistence_instance = SCBEPersistence()
    return _persistence_instance
