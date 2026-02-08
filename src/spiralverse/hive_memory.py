"""
Hive Memory Management - Auto-Save & Distributed Backup
========================================================

AET (Aetheric) Protocol for temporal state management.

Features:
- Auto-save every 30-60 seconds (mission-distance adaptive)
- Priority-based memory eviction using CHARM dimension
- Zero data loss (everything backed up before deletion)
- Graceful degradation for offline operations
- Three-tier memory hierarchy (Hot/Warm/Cold)

"Memory is not lost, only transformed across the hive."
"""

import asyncio
import hashlib
import struct
import gzip
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pathlib import Path
import numpy as np


# =============================================================================
# Constants
# =============================================================================

DEFAULT_AUTO_SAVE_INTERVAL = 30  # seconds
DEFAULT_SYNC_INTERVAL = 120  # seconds
MAX_OFFLINE_HOURS = 48
MEMORY_PRESSURE_THRESHOLD = 0.8  # 80% triggers eviction


class MemoryTier(Enum):
    """Three-tier memory hierarchy."""
    HOT = "hot"      # RAM - instant access, limited capacity
    WARM = "warm"    # SSD - fast access, larger capacity
    COLD = "cold"    # Hive - network access, unlimited capacity


class EvictionPriority(Enum):
    """Priority levels for memory eviction."""
    CRITICAL = 1.0   # Never evict (emergency data)
    HIGH = 0.8       # Evict last
    MEDIUM = 0.5     # Normal eviction candidate
    LOW = 0.2        # Evict first
    EXPIRED = 0.0    # Immediate eviction


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class MemoryBlock:
    """
    Single unit of agent memory with metadata.

    Uses CHARM dimension for priority scoring.
    """
    block_id: str
    data: bytes
    timestamp: datetime
    tongue: str = "AET"  # Aetheric by default (temporal)
    charm: float = 0.5   # Priority/harmony coefficient [-1, 1]
    critical_event: bool = False
    reference_count: int = 0
    compressed: bool = False
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            self.checksum = hashlib.sha256(self.data).hexdigest()[:16]

    @property
    def size_bytes(self) -> int:
        return len(self.data)

    @property
    def age_hours(self) -> float:
        delta = datetime.utcnow() - self.timestamp
        return delta.total_seconds() / 3600

    def compress(self) -> 'MemoryBlock':
        """Compress data using gzip."""
        if self.compressed:
            return self
        compressed_data = gzip.compress(self.data)
        return MemoryBlock(
            block_id=self.block_id,
            data=compressed_data,
            timestamp=self.timestamp,
            tongue=self.tongue,
            charm=self.charm,
            critical_event=self.critical_event,
            reference_count=self.reference_count,
            compressed=True,
            checksum=self.checksum
        )

    def decompress(self) -> 'MemoryBlock':
        """Decompress data."""
        if not self.compressed:
            return self
        decompressed_data = gzip.decompress(self.data)
        return MemoryBlock(
            block_id=self.block_id,
            data=decompressed_data,
            timestamp=self.timestamp,
            tongue=self.tongue,
            charm=self.charm,
            critical_event=self.critical_event,
            reference_count=self.reference_count,
            compressed=False,
            checksum=self.checksum
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "block_id": self.block_id,
            "data": self.data.hex(),
            "timestamp": self.timestamp.isoformat(),
            "tongue": self.tongue,
            "charm": self.charm,
            "critical_event": self.critical_event,
            "reference_count": self.reference_count,
            "compressed": self.compressed,
            "checksum": self.checksum
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'MemoryBlock':
        """Deserialize from dictionary."""
        return cls(
            block_id=d["block_id"],
            data=bytes.fromhex(d["data"]),
            timestamp=datetime.fromisoformat(d["timestamp"]),
            tongue=d.get("tongue", "AET"),
            charm=d.get("charm", 0.5),
            critical_event=d.get("critical_event", False),
            reference_count=d.get("reference_count", 0),
            compressed=d.get("compressed", False),
            checksum=d.get("checksum", "")
        )


@dataclass
class AgentSnapshot:
    """
    Complete state snapshot of an agent at a point in time.
    """
    agent_id: str
    timestamp: datetime
    position_6d: np.ndarray  # [AXIOM, FLOW, GLYPH, ORACLE, CHARM, LEDGER]
    memory_blocks: List[MemoryBlock] = field(default_factory=list)
    mission_context: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_size_bytes(self) -> int:
        return sum(b.size_bytes for b in self.memory_blocks)

    def to_bytes(self) -> bytes:
        """Serialize snapshot to bytes for transmission."""
        data = {
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "position_6d": self.position_6d.tolist(),
            "memory_blocks": [b.to_dict() for b in self.memory_blocks],
            "mission_context": self.mission_context
        }
        json_str = json.dumps(data)
        return gzip.compress(json_str.encode('utf-8'))

    @classmethod
    def from_bytes(cls, data: bytes) -> 'AgentSnapshot':
        """Deserialize snapshot from bytes."""
        json_str = gzip.decompress(data).decode('utf-8')
        d = json.loads(json_str)
        return cls(
            agent_id=d["agent_id"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            position_6d=np.array(d["position_6d"]),
            memory_blocks=[MemoryBlock.from_dict(b) for b in d["memory_blocks"]],
            mission_context=d.get("mission_context", {})
        )


# =============================================================================
# Memory Eviction Engine
# =============================================================================

class MemoryEvictionEngine:
    """
    Priority-based memory eviction using CHARM dimension.

    Eviction priority formula:
        priority = base + critical_bonus + age_factor + charm_factor + reference_bonus

    Higher priority = keep longer, lower = evict first.
    """

    def __init__(self, charm_threshold: float = 0.5):
        self.charm_threshold = charm_threshold

    def calculate_retention_priority(self, block: MemoryBlock) -> float:
        """
        Returns priority score (0-1) for keeping this data.
        Higher = more important, keep longer.
        """
        priority = 0.5  # Base priority

        # 1. Critical events (emergency, collision warnings)
        if block.critical_event:
            priority += 0.4

        # 2. Age factor (recent = more valuable)
        age = block.age_hours
        if age < 1:
            priority += 0.2
        elif age < 6:
            priority += 0.1
        elif age > 24:
            priority -= 0.3
        elif age > 48:
            priority -= 0.4

        # 3. CHARM coefficient (harmony/importance)
        priority += block.charm * 0.3

        # 4. Reference count (collaborative data)
        if block.reference_count > 0:
            priority += min(0.2, block.reference_count * 0.05)

        # 5. Tongue-specific bonuses
        tongue_bonuses = {
            "KO": 0.1,   # Control flow - important
            "UM": 0.15,  # Security - very important
            "DR": 0.05,  # Types - moderate
            "AET": 0.0,  # Default temporal
            "CA": 0.0,   # Computation
            "AV": -0.05  # I/O - can be regenerated
        }
        priority += tongue_bonuses.get(block.tongue, 0.0)

        return max(0.0, min(1.0, priority))

    def rank_for_eviction(self, blocks: List[MemoryBlock]) -> List[Tuple[MemoryBlock, float]]:
        """
        Rank blocks by eviction priority (lowest first = evict first).
        """
        ranked = [(b, self.calculate_retention_priority(b)) for b in blocks]
        ranked.sort(key=lambda x: x[1])  # Ascending (lowest priority first)
        return ranked

    def select_eviction_candidates(
        self,
        blocks: List[MemoryBlock],
        target_free_bytes: int
    ) -> List[MemoryBlock]:
        """
        Select blocks to evict to free target_free_bytes.
        """
        ranked = self.rank_for_eviction(blocks)
        candidates = []
        freed = 0

        for block, priority in ranked:
            if priority >= 0.9:  # Never evict critical
                continue
            candidates.append(block)
            freed += block.size_bytes
            if freed >= target_free_bytes:
                break

        return candidates


# =============================================================================
# Adaptive Sync Scheduler
# =============================================================================

class AdaptiveSyncScheduler:
    """
    Adjusts sync frequency based on distance from hive.

    Closer to hive = more frequent backups.
    Further from hive = conserve bandwidth.
    """

    # Distance thresholds (in km) and corresponding intervals (in seconds)
    DISTANCE_INTERVALS = [
        (10, 15),       # 0-10 km: every 15 seconds
        (100, 60),      # 10-100 km: every 1 minute
        (500, 300),     # 100-500 km: every 5 minutes
        (2000, 900),    # 500-2000 km: every 15 minutes
        (float('inf'), 3600)  # 2000+ km: every 1 hour
    ]

    def calculate_sync_interval(self, distance_from_hive_km: float) -> int:
        """Returns sync interval in seconds based on distance."""
        for threshold, interval in self.DISTANCE_INTERVALS:
            if distance_from_hive_km < threshold:
                return interval
        return 3600  # Default: 1 hour

    def calculate_save_interval(self, distance_from_hive_km: float) -> int:
        """Returns local save interval (always faster than sync)."""
        sync_interval = self.calculate_sync_interval(distance_from_hive_km)
        return max(15, sync_interval // 4)  # Save 4x more often than sync


# =============================================================================
# Hive Client (Network Interface)
# =============================================================================

class HiveClient:
    """
    Interface to the central Hive Data Center.

    Handles:
    - Snapshot uploads
    - Data retrieval
    - Connection management
    - Offline buffering
    """

    def __init__(self, hive_url: str = "hive://localhost:8080"):
        self.hive_url = hive_url
        self.connected = False
        self.offline_buffer: List[AgentSnapshot] = []
        self.last_sync = datetime.utcnow()
        self.upload_count = 0
        self.download_count = 0

    async def connect(self) -> bool:
        """Establish connection to hive."""
        # Simulated connection - in production, use actual network
        await asyncio.sleep(0.1)  # Simulate network latency
        self.connected = True
        print(f"[HIVE] Connected to {self.hive_url}")
        return True

    async def disconnect(self):
        """Disconnect from hive."""
        self.connected = False
        print("[HIVE] Disconnected")

    async def upload_snapshot(self, snapshot: AgentSnapshot) -> bool:
        """Upload snapshot to hive."""
        if not self.connected:
            self.offline_buffer.append(snapshot)
            print(f"[HIVE] Offline - buffered snapshot for {snapshot.agent_id}")
            return False

        # Simulate upload
        data = snapshot.to_bytes()
        await asyncio.sleep(len(data) / 1_000_000)  # ~1MB/s simulated

        self.upload_count += 1
        self.last_sync = datetime.utcnow()
        print(f"[HIVE] Uploaded snapshot: {snapshot.agent_id} ({len(data)} bytes)")
        return True

    async def bulk_upload(
        self,
        snapshots: List[AgentSnapshot],
        priority: str = "medium",
        compression: str = "gzip"
    ) -> bool:
        """Bulk upload multiple snapshots."""
        if not self.connected:
            self.offline_buffer.extend(snapshots)
            return False

        for snapshot in snapshots:
            await self.upload_snapshot(snapshot)

        return True

    async def query(
        self,
        agent_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[AgentSnapshot]:
        """Query historical snapshots from hive."""
        if not self.connected:
            return []

        # Simulated query - in production, actual database query
        await asyncio.sleep(0.2)
        self.download_count += 1

        # Return empty for simulation
        return []

    async def sync_offline_buffer(self) -> int:
        """Upload all buffered data when connection restored."""
        if not self.connected or not self.offline_buffer:
            return 0

        count = len(self.offline_buffer)
        print(f"[HIVE] Syncing {count} buffered snapshots...")

        await self.bulk_upload(self.offline_buffer)
        self.offline_buffer.clear()

        print(f"[HIVE] Offline sync complete ({count} snapshots)")
        return count


# =============================================================================
# Agent Memory System
# =============================================================================

class AgentMemorySystem:
    """
    Three-tier memory hierarchy for a single agent.

    Tier 1 (Hot): RAM - instant access, limited capacity
    Tier 2 (Warm): SSD - fast access, larger capacity
    Tier 3 (Cold): Hive - network access, unlimited capacity
    """

    def __init__(
        self,
        agent_id: str,
        hot_capacity_mb: int = 64,
        warm_capacity_mb: int = 512,
        warm_path: Optional[Path] = None
    ):
        self.agent_id = agent_id
        self.hot_capacity = hot_capacity_mb * 1024 * 1024
        self.warm_capacity = warm_capacity_mb * 1024 * 1024

        # Hot memory (in-process)
        self.hot_memory: Dict[str, MemoryBlock] = {}

        # Warm memory path (local SSD)
        self.warm_path = warm_path or Path(f"./hive_warm/{agent_id}")
        self.warm_path.mkdir(parents=True, exist_ok=True)

        # Position tracking (6D)
        self.position_6d = np.zeros(6)

        # Mission context
        self.mission_context: Dict[str, Any] = {}

        # Eviction engine
        self.eviction_engine = MemoryEvictionEngine()

    @property
    def hot_usage(self) -> int:
        """Current hot memory usage in bytes."""
        return sum(b.size_bytes for b in self.hot_memory.values())

    @property
    def hot_usage_ratio(self) -> float:
        """Hot memory usage as fraction of capacity."""
        return self.hot_usage / self.hot_capacity

    def store(
        self,
        block_id: str,
        data: bytes,
        tongue: str = "AET",
        charm: float = 0.5,
        critical: bool = False
    ) -> bool:
        """
        Store data in hot memory.

        Triggers eviction if memory pressure exceeds threshold.
        """
        block = MemoryBlock(
            block_id=block_id,
            data=data,
            timestamp=datetime.utcnow(),
            tongue=tongue,
            charm=charm,
            critical_event=critical
        )

        # Check if eviction needed
        if self.hot_usage_ratio >= MEMORY_PRESSURE_THRESHOLD:
            self._evict_to_warm(target_free_bytes=block.size_bytes * 2)

        self.hot_memory[block_id] = block
        return True

    def retrieve(self, block_id: str) -> Optional[bytes]:
        """Retrieve data from hot memory."""
        block = self.hot_memory.get(block_id)
        if block:
            block.reference_count += 1
            return block.data
        return None

    def _evict_to_warm(self, target_free_bytes: int):
        """Evict low-priority blocks from hot to warm storage."""
        candidates = self.eviction_engine.select_eviction_candidates(
            list(self.hot_memory.values()),
            target_free_bytes
        )

        for block in candidates:
            # Compress and write to warm storage
            compressed = block.compress()
            warm_file = self.warm_path / f"{block.block_id}.bin"
            warm_file.write_bytes(compressed.data)

            # Remove from hot
            del self.hot_memory[block.block_id]

        if candidates:
            print(f"[MEMORY] Evicted {len(candidates)} blocks to warm storage")

    def create_snapshot(self) -> AgentSnapshot:
        """Create full state snapshot."""
        return AgentSnapshot(
            agent_id=self.agent_id,
            timestamp=datetime.utcnow(),
            position_6d=self.position_6d.copy(),
            memory_blocks=list(self.hot_memory.values()),
            mission_context=self.mission_context.copy()
        )

    def restore_snapshot(self, snapshot: AgentSnapshot):
        """Restore state from snapshot."""
        self.position_6d = snapshot.position_6d.copy()
        self.mission_context = snapshot.mission_context.copy()
        self.hot_memory = {b.block_id: b for b in snapshot.memory_blocks}


# =============================================================================
# Auto-Save Worker
# =============================================================================

class AutoSaveWorker:
    """
    Background worker for automatic state persistence.

    Runs continuously, saving snapshots at adaptive intervals.
    """

    def __init__(
        self,
        agent_id: str,
        memory_system: AgentMemorySystem,
        hive_client: HiveClient,
        sync_scheduler: AdaptiveSyncScheduler
    ):
        self.agent_id = agent_id
        self.memory = memory_system
        self.hive = hive_client
        self.scheduler = sync_scheduler

        self.running = False
        self.last_save = datetime.utcnow()
        self.last_sync = datetime.utcnow()
        self.save_count = 0
        self.sync_count = 0

        # Distance from hive (updated externally)
        self.distance_from_hive_km = 100.0

    async def start(self):
        """Start the auto-save worker."""
        self.running = True
        print(f"[AUTO-SAVE] Started for agent {self.agent_id}")

        while self.running:
            await self._tick()
            await asyncio.sleep(1)  # Check every second

    async def stop(self):
        """Stop the auto-save worker."""
        self.running = False
        print(f"[AUTO-SAVE] Stopped for agent {self.agent_id}")

    async def _tick(self):
        """Single tick of the auto-save loop."""
        now = datetime.utcnow()

        # Check if local save needed
        save_interval = self.scheduler.calculate_save_interval(self.distance_from_hive_km)
        if (now - self.last_save).total_seconds() >= save_interval:
            await self._local_save()

        # Check if hive sync needed
        sync_interval = self.scheduler.calculate_sync_interval(self.distance_from_hive_km)
        if (now - self.last_sync).total_seconds() >= sync_interval:
            await self._hive_sync()

    async def _local_save(self):
        """Save snapshot to warm storage."""
        snapshot = self.memory.create_snapshot()
        data = snapshot.to_bytes()

        # Write to warm storage
        save_file = self.memory.warm_path / f"snapshot_{self.save_count:06d}.bin"
        save_file.write_bytes(data)

        self.last_save = datetime.utcnow()
        self.save_count += 1

    async def _hive_sync(self):
        """Sync to hive data center."""
        snapshot = self.memory.create_snapshot()
        success = await self.hive.upload_snapshot(snapshot)

        if success:
            self.last_sync = datetime.utcnow()
            self.sync_count += 1


# =============================================================================
# Offline Resilience
# =============================================================================

class OfflineResilience:
    """
    Handles offline operation and reconnection.
    """

    def __init__(self, max_offline_hours: int = MAX_OFFLINE_HOURS):
        self.max_offline_hours = max_offline_hours
        self.offline_since: Optional[datetime] = None
        self.offline_buffer: List[AgentSnapshot] = []

    def go_offline(self):
        """Mark system as offline."""
        self.offline_since = datetime.utcnow()
        print(f"[OFFLINE] System offline at {self.offline_since}")

    def queue_snapshot(self, snapshot: AgentSnapshot):
        """Queue snapshot while offline."""
        self.offline_buffer.append(snapshot)

        # Compress old snapshots to save space
        if len(self.offline_buffer) > 100:
            self._compress_buffer()

        # Check offline duration
        if self.offline_since:
            age_hours = (datetime.utcnow() - self.offline_since).total_seconds() / 3600
            if age_hours > self.max_offline_hours:
                print(f"[WARNING] Offline for {age_hours:.1f} hours - risk of data loss")

    def _compress_buffer(self):
        """Compress old snapshots in buffer."""
        # Keep last 50 uncompressed, compress rest
        for i, snapshot in enumerate(self.offline_buffer[:-50]):
            for block in snapshot.memory_blocks:
                if not block.compressed:
                    compressed = block.compress()
                    snapshot.memory_blocks[i] = compressed

    async def reconnect(self, hive_client: HiveClient) -> int:
        """Sync all buffered data on reconnection."""
        if not self.offline_buffer:
            return 0

        count = len(self.offline_buffer)
        print(f"[OFFLINE] Reconnecting - syncing {count} buffered snapshots")

        # Batch upload
        batch_size = 50
        for i in range(0, count, batch_size):
            batch = self.offline_buffer[i:i+batch_size]
            await hive_client.bulk_upload(batch)
            print(f"  Uploaded batch {i//batch_size + 1}/{(count + batch_size - 1)//batch_size}")

        self.offline_buffer.clear()
        self.offline_since = None

        print(f"[OFFLINE] Sync complete ({count} snapshots)")
        return count


# =============================================================================
# Demo
# =============================================================================

async def demo():
    """Demonstrate hive memory management."""
    print("=" * 70)
    print("  HIVE MEMORY MANAGEMENT - AET Protocol Demo")
    print("=" * 70)
    print()

    # Create components
    agent_id = "AGENT-001"
    memory = AgentMemorySystem(agent_id, hot_capacity_mb=64)
    hive = HiveClient("hive://localhost:8080")
    scheduler = AdaptiveSyncScheduler()

    # Connect to hive
    await hive.connect()

    # Store some data
    print("[DEMO] Storing memory blocks...")
    for i in range(10):
        data = f"Memory block {i}: {np.random.randn(100).tobytes().hex()[:100]}".encode()
        memory.store(
            block_id=f"block_{i:03d}",
            data=data,
            tongue=["KO", "AV", "RU", "CA", "UM", "DR"][i % 6],
            charm=np.random.uniform(-0.5, 1.0),
            critical=(i == 0)  # First block is critical
        )

    print(f"  Hot memory usage: {memory.hot_usage / 1024:.1f} KB ({memory.hot_usage_ratio:.1%})")
    print()

    # Update position
    memory.position_6d = np.array([10.5, 20.3, 15.0, 5.0, 0.7, 200.0])
    print(f"[DEMO] Position 6D: {memory.position_6d}")
    print()

    # Create and upload snapshot
    print("[DEMO] Creating snapshot...")
    snapshot = memory.create_snapshot()
    print(f"  Snapshot size: {snapshot.total_size_bytes} bytes")
    print(f"  Memory blocks: {len(snapshot.memory_blocks)}")

    await hive.upload_snapshot(snapshot)
    print()

    # Test eviction
    print("[DEMO] Testing eviction engine...")
    eviction = MemoryEvictionEngine()
    ranked = eviction.rank_for_eviction(list(memory.hot_memory.values()))
    print("  Eviction priority ranking:")
    for block, priority in ranked[:5]:
        print(f"    {block.block_id}: priority={priority:.3f}, charm={block.charm:.2f}, age={block.age_hours:.2f}h")
    print()

    # Test adaptive sync
    print("[DEMO] Testing adaptive sync scheduler...")
    for distance in [5, 50, 200, 1000, 5000]:
        sync_int = scheduler.calculate_sync_interval(distance)
        save_int = scheduler.calculate_save_interval(distance)
        print(f"  Distance {distance:5d} km: sync every {sync_int:4d}s, save every {save_int:3d}s")
    print()

    # Disconnect
    await hive.disconnect()

    print("=" * 70)
    print("  Hive Memory Demo Complete")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
