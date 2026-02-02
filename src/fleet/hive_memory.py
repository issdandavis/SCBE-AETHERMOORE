"""
Hive Memory Management System for HYDRA Swarm Coordination

Integrates with HYDRA Librarian for:
- Auto-save of agent state to persistent storage
- LRU eviction with tongue-weighted importance
- Cross-session memory sharing between swarm members
- Hierarchical memory tiers (Hot/Warm/Cold)

@module fleet/hive_memory
@layer Layer 13 (Risk Decision)
@version 1.0.0
@since 2026-02-02
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from collections import OrderedDict
import time
import hashlib
import json
import math
import threading

# ============================================================================
# Constants
# ============================================================================

PHI = 1.618033988749895  # Golden ratio


class SacredTongueHive(Enum):
    """Sacred Tongues for memory importance weighting."""
    KO = "ko"  # Light - High visibility, UI state
    AV = "av"  # Water - Flow state, pipeline cache
    RU = "ru"  # Wood - Growth/learning, model weights
    CA = "ca"  # Fire - Transform, computation cache
    UM = "um"  # Earth - Foundation, persistent config
    DR = "dr"  # Metal - Structure, audit logs


# Tongue importance weights for eviction (higher = more important)
TONGUE_IMPORTANCE: Dict[SacredTongueHive, float] = {
    SacredTongueHive.KO: PHI ** 0,  # 1.000 - Ephemeral UI
    SacredTongueHive.AV: PHI ** 1,  # 1.618 - Flow state
    SacredTongueHive.RU: PHI ** 2,  # 2.618 - Learning
    SacredTongueHive.CA: PHI ** 3,  # 4.236 - Computation
    SacredTongueHive.UM: PHI ** 4,  # 6.854 - Config
    SacredTongueHive.DR: PHI ** 5,  # 11.09 - Audit (never evict)
}


class MemoryTier(Enum):
    """Hierarchical memory tiers."""
    HOT = "hot"      # In-memory, instant access
    WARM = "warm"    # Local disk, fast access
    COLD = "cold"    # Remote storage, slow access
    FROZEN = "frozen"  # Archive, manual retrieval


# Tier access latency (simulated)
TIER_LATENCY_MS: Dict[MemoryTier, int] = {
    MemoryTier.HOT: 0,
    MemoryTier.WARM: 10,
    MemoryTier.COLD: 100,
    MemoryTier.FROZEN: 1000,
}


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class MemoryEntry:
    """Single entry in Hive Memory."""
    key: str
    value: Any
    tongue: SacredTongueHive
    tier: MemoryTier = MemoryTier.HOT
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0
    owner_agent: Optional[str] = None
    shared_with: Set[str] = field(default_factory=set)
    ttl_seconds: Optional[float] = None  # None = no expiry
    checksum: str = ""

    def __post_init__(self):
        """Compute size and checksum."""
        serialized = json.dumps(self.value, default=str)
        self.size_bytes = len(serialized.encode('utf-8'))
        self.checksum = hashlib.sha256(serialized.encode()).hexdigest()[:16]

    @property
    def importance_score(self) -> float:
        """Calculate importance score for eviction priority."""
        base_importance = TONGUE_IMPORTANCE[self.tongue]
        recency_factor = 1.0 / (1.0 + time.time() - self.accessed_at)
        frequency_factor = math.log(1 + self.access_count)
        return base_importance * recency_factor * frequency_factor

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl_seconds is None:
            return False
        return time.time() > self.created_at + self.ttl_seconds

    def touch(self) -> None:
        """Update access metadata."""
        self.accessed_at = time.time()
        self.access_count += 1


@dataclass
class HiveStats:
    """Statistics for Hive Memory."""
    total_entries: int = 0
    total_size_bytes: int = 0
    hot_entries: int = 0
    warm_entries: int = 0
    cold_entries: int = 0
    frozen_entries: int = 0
    evictions: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    shared_entries: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


@dataclass
class EvictionEvent:
    """Record of an eviction event."""
    key: str
    tongue: SacredTongueHive
    previous_tier: MemoryTier
    new_tier: Optional[MemoryTier]  # None = fully evicted
    reason: str
    timestamp: float = field(default_factory=time.time)
    importance_score: float = 0.0


# ============================================================================
# Hive Memory Manager
# ============================================================================

class HiveMemory:
    """
    Hive Memory Manager for HYDRA swarm coordination.

    Provides:
    - LRU eviction with tongue-weighted importance
    - Hierarchical storage tiers (Hot/Warm/Cold/Frozen)
    - Auto-save to persistent storage
    - Cross-agent memory sharing
    """

    def __init__(
        self,
        max_hot_entries: int = 1000,
        max_hot_bytes: int = 100 * 1024 * 1024,  # 100 MB
        auto_demote: bool = True,
        eviction_callback: Optional[Callable[[EvictionEvent], None]] = None,
    ):
        """
        Initialize Hive Memory.

        Args:
            max_hot_entries: Maximum entries in hot tier
            max_hot_bytes: Maximum bytes in hot tier
            auto_demote: Auto-demote to lower tiers instead of evicting
            eviction_callback: Callback for eviction events
        """
        self._lock = threading.RLock()

        # Storage by tier (OrderedDict for LRU ordering)
        self._hot: OrderedDict[str, MemoryEntry] = OrderedDict()
        self._warm: Dict[str, MemoryEntry] = {}
        self._cold: Dict[str, MemoryEntry] = {}
        self._frozen: Dict[str, MemoryEntry] = {}

        # Configuration
        self.max_hot_entries = max_hot_entries
        self.max_hot_bytes = max_hot_bytes
        self.auto_demote = auto_demote
        self._eviction_callback = eviction_callback

        # Statistics
        self.stats = HiveStats()

        # Agent sharing index
        self._agent_keys: Dict[str, Set[str]] = {}  # agent_id -> set of keys

    def save(
        self,
        key: str,
        value: Any,
        tongue: SacredTongueHive,
        owner_agent: Optional[str] = None,
        ttl_seconds: Optional[float] = None,
    ) -> MemoryEntry:
        """
        Save a value to Hive Memory.

        Args:
            key: Unique identifier
            value: Data to store (must be JSON-serializable)
            tongue: Sacred Tongue domain for importance weighting
            owner_agent: Agent that owns this entry
            ttl_seconds: Time-to-live (None = no expiry)

        Returns:
            Created MemoryEntry
        """
        with self._lock:
            entry = MemoryEntry(
                key=key,
                value=value,
                tongue=tongue,
                tier=MemoryTier.HOT,
                owner_agent=owner_agent,
                ttl_seconds=ttl_seconds,
            )

            # Remove from any existing tier
            self._remove_from_all_tiers(key)

            # Ensure capacity
            self._ensure_capacity(entry.size_bytes)

            # Add to hot tier
            self._hot[key] = entry
            self._hot.move_to_end(key)  # Most recently used

            # Update agent index
            if owner_agent:
                if owner_agent not in self._agent_keys:
                    self._agent_keys[owner_agent] = set()
                self._agent_keys[owner_agent].add(key)

            # Update stats
            self.stats.total_entries += 1
            self.stats.total_size_bytes += entry.size_bytes
            self.stats.hot_entries += 1

            return entry

    def load(self, key: str, requesting_agent: Optional[str] = None) -> Optional[Any]:
        """
        Load a value from Hive Memory.

        Args:
            key: Key to retrieve
            requesting_agent: Agent requesting the data (for access control)

        Returns:
            Stored value or None if not found/unauthorized
        """
        with self._lock:
            entry = self._find_entry(key)

            if entry is None:
                self.stats.cache_misses += 1
                return None

            # Check expiry
            if entry.is_expired:
                self._evict_entry(key, "expired")
                self.stats.cache_misses += 1
                return None

            # Check access permissions
            if not self._can_access(entry, requesting_agent):
                self.stats.cache_misses += 1
                return None

            # Update access metadata
            entry.touch()

            # Promote to hot if in lower tier
            if entry.tier != MemoryTier.HOT:
                self._promote_to_hot(key, entry)

            self.stats.cache_hits += 1
            return entry.value

    def delete(self, key: str) -> bool:
        """Delete an entry from all tiers."""
        with self._lock:
            entry = self._find_entry(key)
            if entry is None:
                return False

            self._remove_from_all_tiers(key)

            # Update agent index
            if entry.owner_agent and entry.owner_agent in self._agent_keys:
                self._agent_keys[entry.owner_agent].discard(key)

            # Update stats
            self.stats.total_entries -= 1
            self.stats.total_size_bytes -= entry.size_bytes

            return True

    def share_with_swarm(
        self,
        keys: List[str],
        target_agents: Optional[List[str]] = None,
    ) -> int:
        """
        Share entries with other swarm members.

        Args:
            keys: Keys to share
            target_agents: Specific agents (None = all)

        Returns:
            Number of entries shared
        """
        with self._lock:
            shared_count = 0

            for key in keys:
                entry = self._find_entry(key)
                if entry is None:
                    continue

                if target_agents:
                    entry.shared_with.update(target_agents)
                else:
                    entry.shared_with.add("*")  # Wildcard = all agents

                shared_count += 1
                self.stats.shared_entries += 1

            return shared_count

    def get_agent_keys(self, agent_id: str) -> List[str]:
        """Get all keys owned by an agent."""
        with self._lock:
            return list(self._agent_keys.get(agent_id, set()))

    def evict_lru(self, count: int = 1) -> List[str]:
        """
        Evict least recently used entries from hot tier.

        Args:
            count: Number of entries to evict

        Returns:
            List of evicted keys
        """
        with self._lock:
            evicted = []

            # Sort by importance score (ascending = lowest importance first)
            sorted_entries = sorted(
                self._hot.items(),
                key=lambda x: x[1].importance_score,
            )

            for key, entry in sorted_entries[:count]:
                # Never evict DR (audit) tongue
                if entry.tongue == SacredTongueHive.DR:
                    continue

                if self.auto_demote:
                    self._demote_entry(key, entry)
                else:
                    self._evict_entry(key, "lru")

                evicted.append(key)

            return evicted

    def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        with self._lock:
            expired_keys = []

            for tier_dict in [self._hot, self._warm, self._cold]:
                for key, entry in list(tier_dict.items()):
                    if entry.is_expired:
                        expired_keys.append(key)

            for key in expired_keys:
                self._evict_entry(key, "expired")

            return len(expired_keys)

    def get_stats(self) -> HiveStats:
        """Get current statistics."""
        with self._lock:
            self.stats.hot_entries = len(self._hot)
            self.stats.warm_entries = len(self._warm)
            self.stats.cold_entries = len(self._cold)
            self.stats.frozen_entries = len(self._frozen)
            return self.stats

    def get_tier_summary(self) -> Dict[str, Any]:
        """Get summary of entries by tier and tongue."""
        with self._lock:
            summary = {
                "tiers": {
                    MemoryTier.HOT.value: {"count": len(self._hot), "keys": list(self._hot.keys())[:10]},
                    MemoryTier.WARM.value: {"count": len(self._warm), "keys": list(self._warm.keys())[:10]},
                    MemoryTier.COLD.value: {"count": len(self._cold), "keys": list(self._cold.keys())[:10]},
                    MemoryTier.FROZEN.value: {"count": len(self._frozen), "keys": list(self._frozen.keys())[:10]},
                },
                "tongues": {},
                "total_bytes": self.stats.total_size_bytes,
            }

            # Count by tongue
            for tongue in SacredTongueHive:
                count = sum(
                    1 for entry in self._all_entries() if entry.tongue == tongue
                )
                summary["tongues"][tongue.value] = count

            return summary

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _all_entries(self) -> List[MemoryEntry]:
        """Get all entries across all tiers."""
        return (
            list(self._hot.values()) +
            list(self._warm.values()) +
            list(self._cold.values()) +
            list(self._frozen.values())
        )

    def _find_entry(self, key: str) -> Optional[MemoryEntry]:
        """Find entry in any tier."""
        if key in self._hot:
            return self._hot[key]
        if key in self._warm:
            return self._warm[key]
        if key in self._cold:
            return self._cold[key]
        if key in self._frozen:
            return self._frozen[key]
        return None

    def _remove_from_all_tiers(self, key: str) -> Optional[MemoryEntry]:
        """Remove entry from all tiers."""
        for tier_dict in [self._hot, self._warm, self._cold, self._frozen]:
            if key in tier_dict:
                entry = tier_dict.pop(key)
                return entry
        return None

    def _ensure_capacity(self, needed_bytes: int) -> None:
        """Ensure hot tier has capacity."""
        # Check entry count
        while len(self._hot) >= self.max_hot_entries:
            self.evict_lru(1)

        # Check byte count
        current_bytes = sum(e.size_bytes for e in self._hot.values())
        while current_bytes + needed_bytes > self.max_hot_bytes and len(self._hot) > 0:
            self.evict_lru(1)
            current_bytes = sum(e.size_bytes for e in self._hot.values())

    def _can_access(self, entry: MemoryEntry, requesting_agent: Optional[str]) -> bool:
        """Check if agent can access entry."""
        if requesting_agent is None:
            return True
        if entry.owner_agent == requesting_agent:
            return True
        if "*" in entry.shared_with:
            return True
        if requesting_agent in entry.shared_with:
            return True
        return False

    def _promote_to_hot(self, key: str, entry: MemoryEntry) -> None:
        """Promote entry to hot tier."""
        self._remove_from_all_tiers(key)
        self._ensure_capacity(entry.size_bytes)

        entry.tier = MemoryTier.HOT
        self._hot[key] = entry
        self._hot.move_to_end(key)

    def _demote_entry(self, key: str, entry: MemoryEntry) -> None:
        """Demote entry to next lower tier."""
        previous_tier = entry.tier

        # Determine new tier
        if entry.tier == MemoryTier.HOT:
            entry.tier = MemoryTier.WARM
            self._hot.pop(key, None)
            self._warm[key] = entry
            self.stats.hot_entries -= 1
            self.stats.warm_entries += 1
        elif entry.tier == MemoryTier.WARM:
            entry.tier = MemoryTier.COLD
            self._warm.pop(key, None)
            self._cold[key] = entry
            self.stats.warm_entries -= 1
            self.stats.cold_entries += 1
        elif entry.tier == MemoryTier.COLD:
            entry.tier = MemoryTier.FROZEN
            self._cold.pop(key, None)
            self._frozen[key] = entry
            self.stats.cold_entries -= 1
            self.stats.frozen_entries += 1
        else:
            # Already frozen, evict
            self._evict_entry(key, "tier_overflow")
            return

        # Record event
        event = EvictionEvent(
            key=key,
            tongue=entry.tongue,
            previous_tier=previous_tier,
            new_tier=entry.tier,
            reason="demotion",
            importance_score=entry.importance_score,
        )

        if self._eviction_callback:
            self._eviction_callback(event)

    def _evict_entry(self, key: str, reason: str) -> None:
        """Fully evict entry from all tiers."""
        entry = self._find_entry(key)
        if entry is None:
            return

        previous_tier = entry.tier
        self._remove_from_all_tiers(key)

        # Update stats
        self.stats.total_entries -= 1
        self.stats.total_size_bytes -= entry.size_bytes
        self.stats.evictions += 1

        # Decrement tier count
        if previous_tier == MemoryTier.HOT:
            self.stats.hot_entries -= 1
        elif previous_tier == MemoryTier.WARM:
            self.stats.warm_entries -= 1
        elif previous_tier == MemoryTier.COLD:
            self.stats.cold_entries -= 1
        elif previous_tier == MemoryTier.FROZEN:
            self.stats.frozen_entries -= 1

        # Update agent index
        if entry.owner_agent and entry.owner_agent in self._agent_keys:
            self._agent_keys[entry.owner_agent].discard(key)

        # Record event
        event = EvictionEvent(
            key=key,
            tongue=entry.tongue,
            previous_tier=previous_tier,
            new_tier=None,
            reason=reason,
            importance_score=entry.importance_score,
        )

        if self._eviction_callback:
            self._eviction_callback(event)


# ============================================================================
# HYDRA Librarian Integration
# ============================================================================

class HYDRALibrarian:
    """
    HYDRA Librarian - Orchestrates Hive Memory across swarm.

    Responsibilities:
    - Coordinate memory sharing between agents
    - Enforce tongue-based access policies
    - Trigger auto-save to persistent storage
    - Handle cross-session state restoration
    """

    def __init__(
        self,
        hive: HiveMemory,
        auto_save_interval: float = 60.0,  # seconds
        persistence_path: Optional[str] = None,
    ):
        """
        Initialize HYDRA Librarian.

        Args:
            hive: Underlying HiveMemory instance
            auto_save_interval: Auto-save interval in seconds
            persistence_path: Path for persistent storage (None = no persistence)
        """
        self._hive = hive
        self._auto_save_interval = auto_save_interval
        self._persistence_path = persistence_path
        self._running = False
        self._save_thread: Optional[threading.Thread] = None

        # Access policy by tongue (which tongues can access which)
        self._tongue_access_policy: Dict[SacredTongueHive, Set[SacredTongueHive]] = {
            SacredTongueHive.KO: {SacredTongueHive.KO, SacredTongueHive.AV},
            SacredTongueHive.AV: {SacredTongueHive.AV, SacredTongueHive.RU},
            SacredTongueHive.RU: {SacredTongueHive.RU, SacredTongueHive.CA},
            SacredTongueHive.CA: {SacredTongueHive.CA, SacredTongueHive.UM},
            SacredTongueHive.UM: {SacredTongueHive.UM, SacredTongueHive.DR},
            SacredTongueHive.DR: set(SacredTongueHive),  # DR can access all
        }

    def start(self) -> None:
        """Start auto-save background thread."""
        if self._running:
            return

        self._running = True
        self._save_thread = threading.Thread(target=self._auto_save_loop, daemon=True)
        self._save_thread.start()

    def stop(self) -> None:
        """Stop auto-save thread."""
        self._running = False
        if self._save_thread:
            self._save_thread.join(timeout=5.0)

    def save_checkpoint(self) -> str:
        """
        Save current hive state to checkpoint.

        Returns:
            Checkpoint identifier
        """
        if not self._persistence_path:
            raise RuntimeError("No persistence path configured")

        checkpoint_id = f"checkpoint_{int(time.time())}"
        checkpoint_data = {
            "id": checkpoint_id,
            "timestamp": time.time(),
            "stats": {
                "total_entries": self._hive.stats.total_entries,
                "total_bytes": self._hive.stats.total_size_bytes,
            },
            "entries": [],
        }

        # Serialize all entries
        for entry in self._hive._all_entries():
            checkpoint_data["entries"].append({
                "key": entry.key,
                "value": entry.value,
                "tongue": entry.tongue.value,
                "tier": entry.tier.value,
                "created_at": entry.created_at,
                "access_count": entry.access_count,
                "owner_agent": entry.owner_agent,
                "shared_with": list(entry.shared_with),
                "ttl_seconds": entry.ttl_seconds,
            })

        # Write to file (simplified - real implementation would use proper storage)
        # In production, this would use SQLite, Redis, or cloud storage
        return checkpoint_id

    def restore_checkpoint(self, checkpoint_id: str) -> int:
        """
        Restore hive state from checkpoint.

        Returns:
            Number of entries restored
        """
        # Placeholder - real implementation would read from persistence
        # and call self._hive.save() for each entry
        return 0

    def get_for_agent(
        self,
        agent_id: str,
        agent_tongue: SacredTongueHive,
    ) -> List[Tuple[str, Any]]:
        """
        Get all entries accessible to an agent.

        Args:
            agent_id: Agent identifier
            agent_tongue: Agent's dominant tongue

        Returns:
            List of (key, value) tuples
        """
        accessible = []
        allowed_tongues = self._tongue_access_policy.get(agent_tongue, {agent_tongue})

        for entry in self._hive._all_entries():
            if entry.tongue in allowed_tongues:
                if self._hive._can_access(entry, agent_id):
                    accessible.append((entry.key, entry.value))

        return accessible

    def _auto_save_loop(self) -> None:
        """Background thread for auto-saving."""
        while self._running:
            time.sleep(self._auto_save_interval)

            if not self._running:
                break

            try:
                # Cleanup expired entries
                self._hive.cleanup_expired()

                # Save checkpoint if persistence configured
                if self._persistence_path:
                    self.save_checkpoint()

            except Exception:
                pass  # Log error in production


# ============================================================================
# Convenience Functions
# ============================================================================

# Global default hive instance
_default_hive: Optional[HiveMemory] = None
_default_librarian: Optional[HYDRALibrarian] = None


def get_default_hive() -> HiveMemory:
    """Get or create default HiveMemory instance."""
    global _default_hive
    if _default_hive is None:
        _default_hive = HiveMemory()
    return _default_hive


def get_default_librarian() -> HYDRALibrarian:
    """Get or create default HYDRALibrarian instance."""
    global _default_hive, _default_librarian
    if _default_librarian is None:
        _default_librarian = HYDRALibrarian(get_default_hive())
    return _default_librarian


def hive_save(
    key: str,
    value: Any,
    tongue: SacredTongueHive = SacredTongueHive.CA,
    **kwargs,
) -> MemoryEntry:
    """Convenience function to save to default hive."""
    return get_default_hive().save(key, value, tongue, **kwargs)


def hive_load(key: str, **kwargs) -> Optional[Any]:
    """Convenience function to load from default hive."""
    return get_default_hive().load(key, **kwargs)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "SacredTongueHive",
    "MemoryTier",
    # Dataclasses
    "MemoryEntry",
    "HiveStats",
    "EvictionEvent",
    # Classes
    "HiveMemory",
    "HYDRALibrarian",
    # Constants
    "TONGUE_IMPORTANCE",
    "TIER_LATENCY_MS",
    "PHI",
    # Functions
    "get_default_hive",
    "get_default_librarian",
    "hive_save",
    "hive_load",
]
