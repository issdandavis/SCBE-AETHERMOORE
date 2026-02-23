"""
HYDRA Librarian - Cross-Session Memory Manager
================================================

The Librarian manages the central ledger and provides:
- Semantic memory search
- Action history analysis
- Cross-session context
- AI-to-AI knowledge sharing
- Workflow templates

"The Librarian remembers everything, forgets nothing,
 and knows exactly when to share what with whom."
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import hashlib
import re

from .ledger import Ledger, LedgerEntry, EntryType


@dataclass
class MemoryQuery:
    """A query for searching memory."""
    keywords: List[str] = field(default_factory=list)
    category: Optional[str] = None
    min_importance: float = 0.0
    max_age_hours: Optional[int] = None
    head_id: Optional[str] = None
    limit: int = 20


@dataclass
class MemoryResult:
    """A result from memory search."""
    key: str
    value: Any
    category: str
    importance: float
    relevance_score: float
    access_count: int
    created_at: str


class Librarian:
    """
    Cross-session memory manager for the HYDRA system.

    The Librarian provides:
    1. Semantic search across all stored memories
    2. Action history analysis and patterns
    3. Workflow template management
    4. AI-to-AI knowledge sharing with governance
    5. Context summarization for new sessions
    """

    def __init__(self, ledger: Ledger):
        self.ledger = ledger

        # Cache for frequently accessed memories
        self._cache: Dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0

        # Keyword index for fast search — load persisted data
        self._keyword_index: Dict[str, List[str]] = self.ledger.load_keywords()

    # =========================================================================
    # Memory Operations
    # =========================================================================

    def remember(
        self,
        key: str,
        value: Any,
        category: str = "general",
        importance: float = 0.5,
        keywords: List[str] = None
    ) -> None:
        """
        Store a fact in memory.

        Args:
            key: Unique identifier for the memory
            value: The data to store (any JSON-serializable value)
            category: Category for organization
            importance: 0.0-1.0 importance score
            keywords: Additional keywords for search
        """
        # Store in ledger
        self.ledger.remember(key, value, category, importance)

        # Update keyword index
        all_keywords = keywords or []

        # Extract keywords from key and value
        all_keywords.extend(self._extract_keywords(key))
        if isinstance(value, str):
            all_keywords.extend(self._extract_keywords(value))
        elif isinstance(value, dict):
            all_keywords.extend(self._extract_keywords(json.dumps(value)))

        for kw in set(all_keywords):
            if kw not in self._keyword_index:
                self._keyword_index[kw] = []
            if key not in self._keyword_index[kw]:
                self._keyword_index[kw].append(key)
                self.ledger.save_keyword(kw, key)

        # Invalidate cache
        if key in self._cache:
            del self._cache[key]

    def recall(self, key: str) -> Optional[Any]:
        """
        Recall a specific memory by key.

        Returns None if not found.
        """
        # Check cache first
        if key in self._cache:
            self._cache_hits += 1
            return self._cache[key]

        self._cache_misses += 1

        # Query ledger
        value = self.ledger.recall(key)

        # Update cache
        if value is not None:
            self._cache[key] = value

        return value

    def search(self, query: MemoryQuery) -> List[MemoryResult]:
        """
        Search memory using semantic matching.

        Returns results sorted by relevance.
        """
        results = []

        # Get all memories matching criteria
        memories = self.ledger.search_memory(
            pattern=query.keywords[0] if query.keywords else None,
            category=query.category,
            limit=query.limit * 2  # Get extra for filtering
        )

        for mem in memories:
            # Check importance
            if mem.get("importance", 0) < query.min_importance:
                continue

            # Check age
            if query.max_age_hours:
                created = datetime.fromisoformat(mem.get("created_at", ""))
                age = datetime.now(timezone.utc) - created.replace(tzinfo=timezone.utc)
                if age > timedelta(hours=query.max_age_hours):
                    continue

            # Calculate relevance score
            relevance = self._calculate_relevance(
                mem.get("key", ""),
                mem.get("value", ""),
                query.keywords
            )

            # Boost by importance and access count
            relevance *= (1 + mem.get("importance", 0))
            relevance *= (1 + min(0.5, mem.get("access_count", 0) * 0.05))

            results.append(MemoryResult(
                key=mem.get("key", ""),
                value=json.loads(mem.get("value", "null")) if mem.get("value") else None,
                category=mem.get("category", "general"),
                importance=mem.get("importance", 0),
                relevance_score=relevance,
                access_count=mem.get("access_count", 0),
                created_at=mem.get("created_at", "")
            ))

        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results[:query.limit]

    def forget(self, key: str) -> bool:
        """
        Remove a memory (mark as forgotten, not deleted).

        For audit purposes, memories are marked rather than deleted.
        """
        # Move to forgotten category with low importance
        value = self.recall(key)
        if value is not None:
            self.ledger.remember(key, value, category="forgotten", importance=0.0)

            # Remove from cache
            if key in self._cache:
                del self._cache[key]

            return True
        return False

    # =========================================================================
    # Action History Analysis
    # =========================================================================

    def get_recent_actions(
        self,
        head_id: str = None,
        limit: int = 50,
        decision_filter: str = None
    ) -> List[Dict[str, Any]]:
        """Get recent actions from the ledger."""
        entries = self.ledger.query(
            entry_type=EntryType.ACTION.value,
            head_id=head_id,
            decision=decision_filter,
            limit=limit
        )

        return [e.to_dict() for e in entries]

    def get_action_patterns(self, head_id: str = None) -> Dict[str, Any]:
        """
        Analyze action patterns for a head or all heads.

        Returns common action sequences, success rates, etc.
        """
        actions = self.get_recent_actions(head_id=head_id, limit=500)

        patterns = {
            "total_actions": len(actions),
            "by_action": {},
            "by_decision": {},
            "success_rate": 0.0,
            "common_targets": {},
            "peak_hours": {}
        }

        if not actions:
            return patterns

        successes = 0
        for a in actions:
            action = a.get("action", "unknown")
            decision = a.get("decision", "UNKNOWN")
            target = a.get("target", "")

            # Count by action
            patterns["by_action"][action] = patterns["by_action"].get(action, 0) + 1

            # Count by decision
            patterns["by_decision"][decision] = patterns["by_decision"].get(decision, 0) + 1

            # Count successes
            if decision == "ALLOW":
                successes += 1

            # Track common targets (domains)
            if "://" in target:
                domain = target.split("://")[1].split("/")[0]
                patterns["common_targets"][domain] = patterns["common_targets"].get(domain, 0) + 1

            # Track peak hours
            try:
                ts = datetime.fromisoformat(a.get("timestamp", ""))
                hour = ts.hour
                patterns["peak_hours"][hour] = patterns["peak_hours"].get(hour, 0) + 1
            except Exception:
                pass

        patterns["success_rate"] = successes / len(actions) if actions else 0

        return patterns

    def get_denied_actions(self, head_id: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get actions that were denied by SCBE."""
        return self.get_recent_actions(
            head_id=head_id,
            decision_filter="DENY",
            limit=limit
        )

    # =========================================================================
    # Workflow Templates
    # =========================================================================

    def save_workflow_template(
        self,
        name: str,
        phases: List[Dict[str, Any]],
        description: str = "",
        tags: List[str] = None
    ) -> str:
        """
        Save a workflow as a reusable template.

        Templates can be loaded and executed later.
        """
        template = {
            "name": name,
            "description": description,
            "phases": phases,
            "tags": tags or [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        key = f"workflow:{name}"
        self.remember(key, template, category="workflow", importance=0.8)

        return key

    def get_workflow_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a workflow template by name."""
        return self.recall(f"workflow:{name}")

    def list_workflow_templates(self) -> List[str]:
        """List all saved workflow templates."""
        results = self.ledger.search_memory(pattern="workflow:", category="workflow")
        return [r.get("key", "").replace("workflow:", "") for r in results]

    # =========================================================================
    # Session Context
    # =========================================================================

    def get_session_summary(self, session_id: str = None) -> Dict[str, Any]:
        """
        Get a summary of a session for handoff to new AI.

        This is crucial for multi-AI workflows where context
        needs to be passed between different AI heads.
        """
        sid = session_id or self.ledger.session_id

        # Get all actions for this session
        entries = self.ledger.query(session_id=sid, limit=1000)

        if not entries:
            return {"session_id": sid, "actions": 0, "summary": "No actions recorded"}

        # Build summary
        actions = []
        decisions = {"ALLOW": 0, "QUARANTINE": 0, "ESCALATE": 0, "DENY": 0}
        heads_involved = set()
        limbs_used = set()

        for e in entries:
            if e.entry_type == EntryType.ACTION.value:
                actions.append({
                    "action": e.action,
                    "target": e.target[:50] if e.target else "",
                    "decision": e.decision,
                    "timestamp": e.timestamp
                })

            if e.decision:
                decisions[e.decision] = decisions.get(e.decision, 0) + 1

            if e.head_id:
                heads_involved.add(e.head_id)
            if e.limb_id:
                limbs_used.add(e.limb_id)

        return {
            "session_id": sid,
            "total_actions": len(actions),
            "decisions": decisions,
            "heads_involved": list(heads_involved),
            "limbs_used": list(limbs_used),
            "actions": actions[:20],  # Last 20 actions
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    def create_handoff_context(self, for_head: str, max_items: int = 10) -> str:
        """
        Create a text summary for handing off to another AI.

        This is what you'd paste into a new Claude/GPT session
        to give it context about what's been happening.
        """
        summary = self.get_session_summary()

        context = f"""
=== HYDRA SESSION CONTEXT ===
Session: {summary['session_id']}
Total Actions: {summary['total_actions']}
Decisions: {json.dumps(summary['decisions'])}
Heads: {', '.join(summary['heads_involved'])}

Recent Actions:
"""
        for a in summary['actions'][:max_items]:
            context += f"  - {a['action']}: {a['target']} ({a['decision']})\n"

        context += f"\n=== END CONTEXT ===\n"

        return context

    # =========================================================================
    # AI-to-AI Knowledge Sharing
    # =========================================================================

    def share_knowledge(
        self,
        from_head: str,
        to_head: str,
        knowledge: Dict[str, Any],
        category: str = "shared"
    ) -> bool:
        """
        Share knowledge between AI heads with governance.

        Knowledge is stored in the ledger with attribution.
        """
        key = f"shared:{from_head}:{to_head}:{datetime.now().timestamp()}"

        self.remember(
            key,
            {
                "from": from_head,
                "to": to_head,
                "knowledge": knowledge,
                "shared_at": datetime.now(timezone.utc).isoformat()
            },
            category=category,
            importance=0.7
        )

        return True

    def get_shared_knowledge(self, head_id: str, limit: int = 20) -> List[Dict]:
        """Get knowledge shared with a specific head."""
        results = self.ledger.search_memory(
            pattern=f":{head_id}:",
            category="shared",
            limit=limit
        )

        return [
            json.loads(r.get("value", "{}"))
            for r in results
        ]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Remove special characters, split on whitespace
        words = re.findall(r'\b\w+\b', text.lower())

        # Filter short words and common stop words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "can", "this",
            "that", "it", "to", "of", "in", "for", "on", "with", "at",
            "by", "from", "as", "or", "and", "but", "not", "so", "if"
        }

        return [w for w in words if len(w) > 2 and w not in stop_words]

    def _calculate_relevance(
        self,
        key: str,
        value: str,
        keywords: List[str]
    ) -> float:
        """Calculate relevance score for a memory."""
        if not keywords:
            return 0.5

        text = f"{key} {value}".lower()
        matches = sum(1 for kw in keywords if kw.lower() in text)

        # Calculate base relevance
        relevance = matches / len(keywords) if keywords else 0

        # Bonus for exact key match
        if any(kw.lower() == key.lower() for kw in keywords):
            relevance += 0.3

        return min(1.0, relevance)

    def get_stats(self) -> Dict[str, Any]:
        """Get Librarian statistics."""
        ledger_stats = self.ledger.get_stats()

        return {
            **ledger_stats,
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": self._cache_hits / max(1, self._cache_hits + self._cache_misses),
            "keyword_index_size": len(self._keyword_index)
        }
