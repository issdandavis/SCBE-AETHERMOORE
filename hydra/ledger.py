"""
HYDRA Central Ledger
====================

SQLite-based ledger for cross-session memory and action history.
Portable, works anywhere Python runs.
"""

import sqlite3
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum
import hashlib
import threading


class EntryType(str, Enum):
    """Types of ledger entries."""
    ACTION = "action"           # User-requested action
    DECISION = "decision"       # SCBE governance decision
    HEAD_CONNECT = "head_connect"    # AI head connected
    HEAD_DISCONNECT = "head_disconnect"
    LIMB_ACTIVATE = "limb_activate"  # Execution limb activated
    LIMB_DEACTIVATE = "limb_deactivate"
    CONSENSUS = "consensus"     # Roundtable vote result
    MEMORY = "memory"           # Stored fact/context
    ERROR = "error"             # Error record
    CHECKPOINT = "checkpoint"   # Session checkpoint


@dataclass
class LedgerEntry:
    """A single entry in the central ledger."""
    id: str
    entry_type: str
    timestamp: str
    head_id: Optional[str]      # Which AI head
    limb_id: Optional[str]      # Which execution limb
    action: str
    target: str
    payload: Dict[str, Any]
    decision: Optional[str] = None
    score: Optional[float] = None
    parent_id: Optional[str] = None  # For threading/grouping
    session_id: Optional[str] = None
    signature: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def sign(self, secret: str) -> None:
        """Sign entry for integrity verification."""
        content = f"{self.id}:{self.entry_type}:{self.action}:{self.target}"
        self.signature = hashlib.sha256(f"{content}:{secret}".encode()).hexdigest()[:32]

    def verify(self, secret: str) -> bool:
        """Verify entry signature."""
        content = f"{self.id}:{self.entry_type}:{self.action}:{self.target}"
        expected = hashlib.sha256(f"{content}:{secret}".encode()).hexdigest()[:32]
        return self.signature == expected


class Ledger:
    """
    Central ledger for the HYDRA system.

    Features:
    - SQLite for portability (works on any machine)
    - Thread-safe operations
    - Full action history with decisions
    - Cross-session memory
    - Sync-ready for AI Workflow Architect
    """

    def __init__(
        self,
        db_path: str = None,
        session_id: str = None
    ):
        # Default to user's home directory
        if db_path is None:
            hydra_dir = os.path.join(os.path.expanduser("~"), ".hydra")
            os.makedirs(hydra_dir, exist_ok=True)
            db_path = os.path.join(hydra_dir, "ledger.db")

        self.db_path = db_path
        self.session_id = session_id or self._generate_session_id()
        self._lock = threading.Lock()
        self._secret = hashlib.sha256(f"hydra:{self.session_id}".encode()).hexdigest()

        self._init_db()

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        rand = hashlib.sha256(str(id(self)).encode()).hexdigest()[:8]
        return f"session-{ts}-{rand}"

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Main ledger table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ledger (
                    id TEXT PRIMARY KEY,
                    entry_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    head_id TEXT,
                    limb_id TEXT,
                    action TEXT NOT NULL,
                    target TEXT,
                    payload TEXT,
                    decision TEXT,
                    score REAL,
                    parent_id TEXT,
                    session_id TEXT,
                    signature TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes for fast queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON ledger(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON ledger(entry_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_head ON ledger(head_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_decision ON ledger(decision)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON ledger(timestamp)")

            # Memory table for cross-session facts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    category TEXT,
                    importance REAL DEFAULT 0.5,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0
                )
            """)

            # Active heads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_heads (
                    head_id TEXT PRIMARY KEY,
                    ai_type TEXT,
                    model TEXT,
                    connected_at DATETIME,
                    last_action DATETIME,
                    status TEXT DEFAULT 'active'
                )
            """)

            # Active limbs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_limbs (
                    limb_id TEXT PRIMARY KEY,
                    limb_type TEXT,
                    tab_id TEXT,
                    activated_at DATETIME,
                    last_action DATETIME,
                    status TEXT DEFAULT 'active'
                )
            """)

            conn.commit()
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def write(self, entry: LedgerEntry) -> str:
        """Write entry to ledger."""
        entry.session_id = self.session_id
        entry.sign(self._secret)

        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO ledger (
                    id, entry_type, timestamp, head_id, limb_id,
                    action, target, payload, decision, score,
                    parent_id, session_id, signature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.entry_type,
                entry.timestamp,
                entry.head_id,
                entry.limb_id,
                entry.action,
                entry.target,
                json.dumps(entry.payload),
                entry.decision,
                entry.score,
                entry.parent_id,
                entry.session_id,
                entry.signature
            ))

            conn.commit()
            conn.close()

        return entry.id

    def read(self, entry_id: str) -> Optional[LedgerEntry]:
        """Read single entry by ID."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM ledger WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                return self._row_to_entry(row)
            return None

    def query(
        self,
        entry_type: str = None,
        head_id: str = None,
        limb_id: str = None,
        decision: str = None,
        session_id: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[LedgerEntry]:
        """Query ledger entries."""
        conditions = []
        params = []

        if entry_type:
            conditions.append("entry_type = ?")
            params.append(entry_type)
        if head_id:
            conditions.append("head_id = ?")
            params.append(head_id)
        if limb_id:
            conditions.append("limb_id = ?")
            params.append(limb_id)
        if decision:
            conditions.append("decision = ?")
            params.append(decision)
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        where = " AND ".join(conditions) if conditions else "1=1"

        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute(f"""
                SELECT * FROM ledger
                WHERE {where}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (*params, limit, offset))

            rows = cursor.fetchall()
            conn.close()

            return [self._row_to_entry(row) for row in rows]

    def _row_to_entry(self, row: sqlite3.Row) -> LedgerEntry:
        """Convert database row to LedgerEntry."""
        return LedgerEntry(
            id=row["id"],
            entry_type=row["entry_type"],
            timestamp=row["timestamp"],
            head_id=row["head_id"],
            limb_id=row["limb_id"],
            action=row["action"],
            target=row["target"],
            payload=json.loads(row["payload"]) if row["payload"] else {},
            decision=row["decision"],
            score=row["score"],
            parent_id=row["parent_id"],
            session_id=row["session_id"],
            signature=row["signature"]
        )

    # =========================================================================
    # Memory Operations (Cross-session facts)
    # =========================================================================

    def remember(self, key: str, value: Any, category: str = "general", importance: float = 0.5) -> None:
        """Store a fact in cross-session memory."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO memory (key, value, category, importance, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (key, json.dumps(value), category, importance))

            conn.commit()
            conn.close()

    def recall(self, key: str) -> Optional[Any]:
        """Recall a fact from memory."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE memory SET access_count = access_count + 1 WHERE key = ?
            """, (key,))

            cursor.execute("SELECT value FROM memory WHERE key = ?", (key,))
            row = cursor.fetchone()

            conn.commit()
            conn.close()

            if row:
                return json.loads(row["value"])
            return None

    def search_memory(self, pattern: str = None, category: str = None, limit: int = 20) -> List[Dict]:
        """Search memory by pattern or category."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            if pattern and category:
                cursor.execute("""
                    SELECT * FROM memory
                    WHERE key LIKE ? AND category = ?
                    ORDER BY importance DESC, access_count DESC
                    LIMIT ?
                """, (f"%{pattern}%", category, limit))
            elif pattern:
                cursor.execute("""
                    SELECT * FROM memory
                    WHERE key LIKE ? OR value LIKE ?
                    ORDER BY importance DESC, access_count DESC
                    LIMIT ?
                """, (f"%{pattern}%", f"%{pattern}%", limit))
            elif category:
                cursor.execute("""
                    SELECT * FROM memory WHERE category = ?
                    ORDER BY importance DESC, access_count DESC
                    LIMIT ?
                """, (category, limit))
            else:
                cursor.execute("""
                    SELECT * FROM memory
                    ORDER BY importance DESC, access_count DESC
                    LIMIT ?
                """, (limit,))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

    # =========================================================================
    # Head/Limb Registry
    # =========================================================================

    def register_head(self, head_id: str, ai_type: str, model: str) -> None:
        """Register an active AI head."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO active_heads (head_id, ai_type, model, connected_at, status)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'active')
            """, (head_id, ai_type, model))

            conn.commit()
            conn.close()

    def unregister_head(self, head_id: str) -> None:
        """Unregister an AI head."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE active_heads SET status = 'disconnected' WHERE head_id = ?
            """, (head_id,))

            conn.commit()
            conn.close()

    def get_active_heads(self) -> List[Dict]:
        """Get all active heads."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM active_heads WHERE status = 'active'
            """)

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

    def register_limb(self, limb_id: str, limb_type: str, tab_id: str = None) -> None:
        """Register an active execution limb."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO active_limbs (limb_id, limb_type, tab_id, activated_at, status)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'active')
            """, (limb_id, limb_type, tab_id))

            conn.commit()
            conn.close()

    def get_active_limbs(self) -> List[Dict]:
        """Get all active limbs."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM active_limbs WHERE status = 'active'
            """)

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get ledger statistics."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            # Total entries
            cursor.execute("SELECT COUNT(*) as count FROM ledger")
            total = cursor.fetchone()["count"]

            # By type
            cursor.execute("""
                SELECT entry_type, COUNT(*) as count
                FROM ledger GROUP BY entry_type
            """)
            by_type = {row["entry_type"]: row["count"] for row in cursor.fetchall()}

            # By decision
            cursor.execute("""
                SELECT decision, COUNT(*) as count
                FROM ledger WHERE decision IS NOT NULL
                GROUP BY decision
            """)
            by_decision = {row["decision"]: row["count"] for row in cursor.fetchall()}

            # Active components
            cursor.execute("SELECT COUNT(*) as count FROM active_heads WHERE status = 'active'")
            active_heads = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM active_limbs WHERE status = 'active'")
            active_limbs = cursor.fetchone()["count"]

            # Memory stats
            cursor.execute("SELECT COUNT(*) as count FROM memory")
            memory_count = cursor.fetchone()["count"]

            conn.close()

            return {
                "total_entries": total,
                "by_type": by_type,
                "by_decision": by_decision,
                "active_heads": active_heads,
                "active_limbs": active_limbs,
                "memory_facts": memory_count,
                "session_id": self.session_id,
                "db_path": self.db_path
            }

    def export_session(self, session_id: str = None) -> List[Dict]:
        """Export all entries for a session."""
        sid = session_id or self.session_id
        entries = self.query(session_id=sid, limit=10000)
        return [e.to_dict() for e in entries]
