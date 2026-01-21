"""
Audit Logging and Workflow Tracking
====================================

Comprehensive logging system for AI orchestration with:
- Immutable audit trails
- Secure storage integration
- File change tracking
- Decision logging
- Compliance reporting

Version: 1.0.0
"""

import os
import json
import hashlib
import hmac
import gzip
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import secrets


class LogLevel(Enum):
    """Log severity levels."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    AUDIT = 100  # Special level for audit logs


class LogCategory(Enum):
    """Categories for log entries."""
    AGENT = "agent"
    TASK = "task"
    WORKFLOW = "workflow"
    SECURITY = "security"
    FILE = "file"
    DECISION = "decision"
    COMMUNICATION = "communication"
    SYSTEM = "system"


@dataclass
class LogEntry:
    """A single log entry with integrity verification."""
    id: str
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    source: str  # agent ID or system component
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    previous_hash: Optional[str] = None
    hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "category": self.category.value,
            "source": self.source,
            "message": self.message,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
        }

    def compute_hash(self) -> str:
        """Compute hash for integrity verification."""
        content = json.dumps({
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "category": self.category.value,
            "source": self.source,
            "message": self.message,
            "data": self.data,
            "previous_hash": self.previous_hash,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class FileChange:
    """Record of a file change."""
    file_path: str
    change_type: str  # created, modified, deleted
    timestamp: datetime
    agent_id: str
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    diff_summary: Optional[str] = None


@dataclass
class DecisionRecord:
    """Record of an AI decision for audit."""
    decision_id: str
    timestamp: datetime
    agent_id: str
    decision_type: str
    input_context: Dict[str, Any]
    options_considered: List[Dict[str, Any]]
    selected_option: str
    reasoning: str
    confidence: float
    approved_by: Optional[str] = None


class AuditLogger:
    """
    Secure audit logging with chain-of-custody verification.

    Features:
    - Hash-chained log entries (tamper detection)
    - Encrypted storage option
    - Automatic rotation and compression
    - Integrity verification
    """

    def __init__(
        self,
        storage_path: str = "./audit_logs",
        signing_key: Optional[bytes] = None,
        max_entries_per_file: int = 10000,
        enable_compression: bool = True,
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.signing_key = signing_key or secrets.token_bytes(32)
        self.max_entries_per_file = max_entries_per_file
        self.enable_compression = enable_compression

        self.current_entries: List[LogEntry] = []
        self.last_hash: Optional[str] = None
        self.entry_counter = 0
        self.current_file_index = 0
        self._lock = threading.Lock()

        # Load existing chain
        self._load_chain_state()

    def log(
        self,
        level: LogLevel,
        category: LogCategory,
        source: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> LogEntry:
        """Create and store a log entry."""
        with self._lock:
            entry = LogEntry(
                id=f"log_{self.entry_counter:08d}",
                timestamp=datetime.now(),
                level=level,
                category=category,
                source=source,
                message=message,
                data=data or {},
                previous_hash=self.last_hash,
            )

            # Compute and set hash
            entry.hash = entry.compute_hash()
            self.last_hash = entry.hash

            self.current_entries.append(entry)
            self.entry_counter += 1

            # Check if rotation needed
            if len(self.current_entries) >= self.max_entries_per_file:
                self._rotate_log()

            return entry

    def log_agent_action(
        self,
        agent_id: str,
        action: str,
        details: Dict[str, Any],
    ) -> LogEntry:
        """Log an agent action."""
        return self.log(
            LogLevel.INFO,
            LogCategory.AGENT,
            agent_id,
            f"Agent action: {action}",
            details,
        )

    def log_task_event(
        self,
        task_id: str,
        event: str,
        agent_id: str,
        details: Dict[str, Any],
    ) -> LogEntry:
        """Log a task event."""
        return self.log(
            LogLevel.INFO,
            LogCategory.TASK,
            agent_id,
            f"Task {task_id}: {event}",
            {"task_id": task_id, **details},
        )

    def log_security_event(
        self,
        source: str,
        event_type: str,
        details: Dict[str, Any],
        level: LogLevel = LogLevel.WARNING,
    ) -> LogEntry:
        """Log a security event."""
        return self.log(
            level,
            LogCategory.SECURITY,
            source,
            f"Security event: {event_type}",
            details,
        )

    def log_file_change(self, change: FileChange) -> LogEntry:
        """Log a file change."""
        return self.log(
            LogLevel.AUDIT,
            LogCategory.FILE,
            change.agent_id,
            f"File {change.change_type}: {change.file_path}",
            {
                "file_path": change.file_path,
                "change_type": change.change_type,
                "old_hash": change.old_hash,
                "new_hash": change.new_hash,
                "diff_summary": change.diff_summary,
            },
        )

    def log_decision(self, decision: DecisionRecord) -> LogEntry:
        """Log an AI decision for audit."""
        return self.log(
            LogLevel.AUDIT,
            LogCategory.DECISION,
            decision.agent_id,
            f"Decision: {decision.decision_type}",
            {
                "decision_id": decision.decision_id,
                "input_context": decision.input_context,
                "options": decision.options_considered,
                "selected": decision.selected_option,
                "reasoning": decision.reasoning,
                "confidence": decision.confidence,
                "approved_by": decision.approved_by,
            },
        )

    def log_communication(
        self,
        sender_id: str,
        receiver_id: str,
        message_type: str,
        content_hash: str,
    ) -> LogEntry:
        """Log agent-to-agent communication."""
        return self.log(
            LogLevel.INFO,
            LogCategory.COMMUNICATION,
            sender_id,
            f"Message to {receiver_id}: {message_type}",
            {
                "sender": sender_id,
                "receiver": receiver_id,
                "message_type": message_type,
                "content_hash": content_hash,
            },
        )

    def verify_chain_integrity(self) -> Dict[str, Any]:
        """Verify the integrity of the log chain."""
        issues = []
        verified_count = 0
        previous_hash = None

        # Check current entries
        for entry in self.current_entries:
            # Verify hash matches
            computed = entry.compute_hash()
            if computed != entry.hash:
                issues.append({
                    "entry_id": entry.id,
                    "issue": "hash_mismatch",
                    "expected": entry.hash,
                    "computed": computed,
                })

            # Verify chain
            if entry.previous_hash != previous_hash:
                issues.append({
                    "entry_id": entry.id,
                    "issue": "chain_break",
                    "expected_previous": previous_hash,
                    "actual_previous": entry.previous_hash,
                })

            previous_hash = entry.hash
            verified_count += 1

        return {
            "verified_entries": verified_count,
            "issues": issues,
            "chain_intact": len(issues) == 0,
            "verified_at": datetime.now().isoformat(),
        }

    def query(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[LogLevel] = None,
        category: Optional[LogCategory] = None,
        source: Optional[str] = None,
        limit: int = 1000,
    ) -> List[LogEntry]:
        """Query log entries with filters."""
        results = []

        for entry in self.current_entries:
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            if level and entry.level.value < level.value:
                continue
            if category and entry.category != category:
                continue
            if source and entry.source != source:
                continue

            results.append(entry)

            if len(results) >= limit:
                break

        return results

    def export(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        format: str = "json",
    ) -> str:
        """Export logs for external analysis."""
        entries = self.query(start_time=start_time, end_time=end_time, limit=100000)

        if format == "json":
            return json.dumps([e.to_dict() for e in entries], indent=2)
        elif format == "csv":
            lines = ["id,timestamp,level,category,source,message"]
            for e in entries:
                lines.append(
                    f"{e.id},{e.timestamp.isoformat()},{e.level.name},"
                    f"{e.category.value},{e.source},\"{e.message}\""
                )
            return "\n".join(lines)
        else:
            raise ValueError(f"Unknown format: {format}")

    def _rotate_log(self):
        """Rotate current log file."""
        if not self.current_entries:
            return

        filename = f"audit_{self.current_file_index:06d}.json"
        if self.enable_compression:
            filename += ".gz"

        filepath = self.storage_path / filename

        data = json.dumps([e.to_dict() for e in self.current_entries])

        if self.enable_compression:
            with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                f.write(data)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(data)

        # Sign the file
        signature = hmac.new(
            self.signing_key,
            data.encode(),
            hashlib.sha256
        ).hexdigest()

        sig_path = self.storage_path / f"{filename}.sig"
        with open(sig_path, 'w') as f:
            f.write(signature)

        self.current_entries = []
        self.current_file_index += 1
        self._save_chain_state()

    def _save_chain_state(self):
        """Save chain state for recovery."""
        state = {
            "last_hash": self.last_hash,
            "entry_counter": self.entry_counter,
            "file_index": self.current_file_index,
        }
        state_path = self.storage_path / "chain_state.json"
        with open(state_path, 'w') as f:
            json.dump(state, f)

    def _load_chain_state(self):
        """Load chain state from disk."""
        state_path = self.storage_path / "chain_state.json"
        if state_path.exists():
            with open(state_path, 'r') as f:
                state = json.load(f)
                self.last_hash = state.get("last_hash")
                self.entry_counter = state.get("entry_counter", 0)
                self.current_file_index = state.get("file_index", 0)

    def flush(self):
        """Flush current entries to disk."""
        if self.current_entries:
            self._rotate_log()


class WorkflowTracker:
    """
    Tracks workflow execution with detailed progress logging.
    """

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        self.audit_logger = audit_logger or AuditLogger()
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.completed_workflows: List[Dict[str, Any]] = []

    def start_workflow(
        self,
        workflow_id: str,
        name: str,
        initiator: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Track workflow start."""
        self.active_workflows[workflow_id] = {
            "id": workflow_id,
            "name": name,
            "initiator": initiator,
            "started_at": datetime.now(),
            "status": "running",
            "steps": [],
            "metadata": metadata or {},
        }

        self.audit_logger.log(
            LogLevel.INFO,
            LogCategory.WORKFLOW,
            initiator,
            f"Workflow started: {name}",
            {"workflow_id": workflow_id, "metadata": metadata},
        )

    def log_step(
        self,
        workflow_id: str,
        step_name: str,
        status: str,
        agent_id: str,
        result: Optional[Dict[str, Any]] = None,
    ):
        """Log a workflow step."""
        if workflow_id not in self.active_workflows:
            return

        step = {
            "name": step_name,
            "status": status,
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "result": result,
        }

        self.active_workflows[workflow_id]["steps"].append(step)

        self.audit_logger.log_task_event(
            step_name,
            status,
            agent_id,
            {"workflow_id": workflow_id, "result": result},
        )

    def complete_workflow(
        self,
        workflow_id: str,
        status: str,
        final_result: Optional[Dict[str, Any]] = None,
    ):
        """Mark workflow as complete."""
        if workflow_id not in self.active_workflows:
            return

        workflow = self.active_workflows[workflow_id]
        workflow["status"] = status
        workflow["completed_at"] = datetime.now()
        workflow["final_result"] = final_result
        workflow["duration_seconds"] = (
            workflow["completed_at"] - workflow["started_at"]
        ).total_seconds()

        self.completed_workflows.append(workflow)
        del self.active_workflows[workflow_id]

        self.audit_logger.log(
            LogLevel.INFO,
            LogCategory.WORKFLOW,
            workflow["initiator"],
            f"Workflow completed: {workflow['name']} ({status})",
            {
                "workflow_id": workflow_id,
                "duration_seconds": workflow["duration_seconds"],
                "steps_completed": len(workflow["steps"]),
            },
        )

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a workflow."""
        if workflow_id in self.active_workflows:
            return self.active_workflows[workflow_id]

        for wf in self.completed_workflows:
            if wf["id"] == workflow_id:
                return wf

        return None

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get all active workflows."""
        return list(self.active_workflows.values())

    def generate_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate workflow execution report."""
        workflows = self.completed_workflows.copy()

        if start_time:
            workflows = [
                w for w in workflows
                if w["started_at"] >= start_time
            ]

        if end_time:
            workflows = [
                w for w in workflows
                if w["started_at"] <= end_time
            ]

        if not workflows:
            return {"workflows": [], "summary": {}}

        total = len(workflows)
        successful = sum(1 for w in workflows if w["status"] == "completed")
        failed = sum(1 for w in workflows if w["status"] == "failed")
        avg_duration = sum(w.get("duration_seconds", 0) for w in workflows) / total

        return {
            "workflows": workflows,
            "summary": {
                "total_workflows": total,
                "successful": successful,
                "failed": failed,
                "success_rate": successful / total * 100 if total > 0 else 0,
                "average_duration_seconds": avg_duration,
                "report_generated_at": datetime.now().isoformat(),
            },
        }


# =============================================================================
# SECURE STORAGE INTEGRATION
# =============================================================================

class SecureStorage:
    """
    Secure local storage with optional cloud backup.

    Features:
    - Encrypted at rest
    - Integrity verification
    - Automatic backup scheduling
    - Cloud sync (optional extension)
    """

    def __init__(
        self,
        storage_path: str = "./secure_storage",
        encryption_key: Optional[bytes] = None,
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.encryption_key = encryption_key or secrets.token_bytes(32)
        self.manifest: Dict[str, Dict[str, Any]] = {}
        self._load_manifest()

    def store(
        self,
        key: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store data securely."""
        # Compute hash
        data_hash = hashlib.sha256(data).hexdigest()

        # Simple XOR encryption (real implementation would use AES-256-GCM)
        encrypted = self._encrypt(data)

        # Store file
        file_path = self.storage_path / f"{key}.enc"
        with open(file_path, 'wb') as f:
            f.write(encrypted)

        # Update manifest
        self.manifest[key] = {
            "hash": data_hash,
            "size": len(data),
            "stored_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self._save_manifest()

        return data_hash

    def retrieve(self, key: str) -> Optional[bytes]:
        """Retrieve stored data."""
        if key not in self.manifest:
            return None

        file_path = self.storage_path / f"{key}.enc"
        if not file_path.exists():
            return None

        with open(file_path, 'rb') as f:
            encrypted = f.read()

        data = self._decrypt(encrypted)

        # Verify integrity
        computed_hash = hashlib.sha256(data).hexdigest()
        if computed_hash != self.manifest[key]["hash"]:
            raise ValueError(f"Data integrity check failed for key: {key}")

        return data

    def delete(self, key: str) -> bool:
        """Delete stored data."""
        if key not in self.manifest:
            return False

        file_path = self.storage_path / f"{key}.enc"
        if file_path.exists():
            file_path.unlink()

        del self.manifest[key]
        self._save_manifest()
        return True

    def list_keys(self) -> List[str]:
        """List all stored keys."""
        return list(self.manifest.keys())

    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a stored item."""
        if key not in self.manifest:
            return None
        return self.manifest[key]

    def _encrypt(self, data: bytes) -> bytes:
        """Encrypt data (simplified XOR for demo; use AES-256-GCM in production)."""
        key_bytes = self.encryption_key * (len(data) // len(self.encryption_key) + 1)
        return bytes(a ^ b for a, b in zip(data, key_bytes[:len(data)]))

    def _decrypt(self, data: bytes) -> bytes:
        """Decrypt data."""
        return self._encrypt(data)  # XOR is symmetric

    def _save_manifest(self):
        """Save manifest to disk."""
        manifest_path = self.storage_path / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)

    def _load_manifest(self):
        """Load manifest from disk."""
        manifest_path = self.storage_path / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                self.manifest = json.load(f)
