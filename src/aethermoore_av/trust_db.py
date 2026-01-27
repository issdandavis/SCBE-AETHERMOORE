"""
AETHERMOORE Hyperbolic Trust Database
=====================================
Trust scores stored in hyperbolic space.
- Center (r=0): Maximum trust (system binaries)
- Edge (r=4): Minimum trust (unknown files)

Trust is earned over time through clean behavior.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List
from pathlib import Path

# Import AETHERMOORE math (relative imports)
from ..aethermoore_math.hyperbolic import hyperbolic_distance


@dataclass
class TrustEntry:
    """Trust entry for a file or executable."""
    file_hash: str
    filepath: str
    trust_radius: float  # 0 = core (trusted), 4 = edge (untrusted)
    trust_angle: float   # Angular position (for clustering)
    first_seen: float    # Unix timestamp
    last_seen: float
    scan_count: int
    clean_count: int     # Times scanned as clean
    threat_count: int    # Times flagged as threat
    is_system: bool = False
    signature: Optional[str] = None  # Code signing signature if available

    @property
    def trust_score(self) -> float:
        """Calculate trust score (0=untrusted, 1=fully trusted)."""
        # Inverse of radius, normalized
        return max(0.0, 1.0 - (self.trust_radius / 4.0))

    @property
    def reputation(self) -> float:
        """Calculate reputation from scan history."""
        if self.scan_count == 0:
            return 0.5  # Unknown
        return self.clean_count / self.scan_count

    def earn_trust(self, amount: float = 0.1):
        """Move toward center (earn trust) after clean scan."""
        self.trust_radius = max(0.0, self.trust_radius - amount)
        self.clean_count += 1
        self.scan_count += 1
        self.last_seen = time.time()

    def lose_trust(self, amount: float = 0.5):
        """Move toward edge (lose trust) after threat detection."""
        self.trust_radius = min(4.0, self.trust_radius + amount)
        self.threat_count += 1
        self.scan_count += 1
        self.last_seen = time.time()


class TrustDatabase:
    """
    Hyperbolic trust database for files and executables.

    Files start at the edge (untrusted) and move toward center
    as they demonstrate clean behavior over time.
    """

    # Default trust radii for known categories
    TRUST_LEVELS = {
        "system_core": 0.0,      # Kernel, init
        "system_binary": 0.5,    # /usr/bin/*
        "system_lib": 0.5,       # /usr/lib/*
        "signed_app": 1.0,       # Code-signed applications
        "package_managed": 1.5,  # apt/npm/pip installed
        "user_app": 2.5,         # User-installed apps
        "downloaded": 3.5,       # Downloaded files
        "unknown": 4.0,          # Unknown/new files
    }

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize trust database.

        Args:
            db_path: Path to persistent storage (JSON file)
        """
        self.db_path = db_path or os.path.expanduser("~/.aethermoore_av/trust.json")
        self.entries: Dict[str, TrustEntry] = {}
        self._load()

    def _load(self):
        """Load database from disk."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    for hash_val, entry_data in data.items():
                        self.entries[hash_val] = TrustEntry(**entry_data)
            except (json.JSONDecodeError, IOError):
                pass  # Start fresh on error

    def _save(self):
        """Persist database to disk."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, 'w') as f:
            data = {h: asdict(e) for h, e in self.entries.items()}
            json.dump(data, f, indent=2)

    def get_trust_radius(self, filepath: str) -> float:
        """
        Get trust radius for a file.

        Args:
            filepath: Path to file

        Returns:
            Trust radius (0=trusted, 4=untrusted)
        """
        # Calculate hash
        try:
            file_hash = self._hash_file(filepath)
        except (IOError, PermissionError):
            return 4.0  # Cannot read = untrusted

        # Check database
        if file_hash in self.entries:
            entry = self.entries[file_hash]
            entry.last_seen = time.time()
            return entry.trust_radius

        # New file - determine initial trust from path
        initial_radius = self._classify_path(filepath)

        # Create entry
        now = time.time()
        entry = TrustEntry(
            file_hash=file_hash,
            filepath=filepath,
            trust_radius=initial_radius,
            trust_angle=self._path_to_angle(filepath),
            first_seen=now,
            last_seen=now,
            scan_count=0,
            clean_count=0,
            threat_count=0,
            is_system=initial_radius < 1.0,
        )
        self.entries[file_hash] = entry

        return initial_radius

    def update_trust(self, filepath: str, is_clean: bool, save: bool = True):
        """
        Update trust based on scan result.

        Args:
            filepath: Path to file
            is_clean: True if scan was clean, False if threat detected
            save: Whether to persist to disk
        """
        file_hash = self._hash_file(filepath)

        if file_hash not in self.entries:
            self.get_trust_radius(filepath)  # Create entry

        entry = self.entries[file_hash]

        if is_clean:
            entry.earn_trust(0.1)  # Small trust gain per clean scan
        else:
            entry.lose_trust(0.5)  # Larger trust loss for threats

        if save:
            self._save()

    def get_entry(self, filepath: str) -> Optional[TrustEntry]:
        """Get full trust entry for a file."""
        try:
            file_hash = self._hash_file(filepath)
            return self.entries.get(file_hash)
        except:
            return None

    def add_trusted(
        self,
        filepath: str,
        trust_level: str = "signed_app",
        signature: Optional[str] = None
    ):
        """
        Manually add a trusted file.

        Args:
            filepath: Path to file
            trust_level: One of TRUST_LEVELS keys
            signature: Optional code signing signature
        """
        file_hash = self._hash_file(filepath)
        radius = self.TRUST_LEVELS.get(trust_level, 2.5)

        now = time.time()
        entry = TrustEntry(
            file_hash=file_hash,
            filepath=filepath,
            trust_radius=radius,
            trust_angle=self._path_to_angle(filepath),
            first_seen=now,
            last_seen=now,
            scan_count=1,
            clean_count=1,
            threat_count=0,
            is_system=(radius < 1.0),
            signature=signature,
        )
        self.entries[file_hash] = entry
        self._save()

    def add_blocked(self, filepath: str, reason: str = ""):
        """Add a file to the blocked list (maximum distrust)."""
        file_hash = self._hash_file(filepath)

        now = time.time()
        entry = TrustEntry(
            file_hash=file_hash,
            filepath=filepath,
            trust_radius=4.0,
            trust_angle=self._path_to_angle(filepath),
            first_seen=now,
            last_seen=now,
            scan_count=1,
            clean_count=0,
            threat_count=1,
            is_system=False,
        )
        self.entries[file_hash] = entry
        self._save()

    def get_statistics(self) -> Dict:
        """Get database statistics."""
        total = len(self.entries)
        if total == 0:
            return {"total": 0}

        trusted = sum(1 for e in self.entries.values() if e.trust_radius < 1.0)
        suspicious = sum(1 for e in self.entries.values() if 1.0 <= e.trust_radius < 3.0)
        untrusted = sum(1 for e in self.entries.values() if e.trust_radius >= 3.0)

        return {
            "total": total,
            "trusted": trusted,
            "suspicious": suspicious,
            "untrusted": untrusted,
            "system_files": sum(1 for e in self.entries.values() if e.is_system),
            "avg_trust_radius": sum(e.trust_radius for e in self.entries.values()) / total,
        }

    def _hash_file(self, filepath: str) -> str:
        """Calculate SHA-256 hash of file."""
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def _classify_path(self, filepath: str) -> float:
        """Determine initial trust radius from file path."""
        path = filepath.lower()

        # System paths (most trusted)
        if any(p in path for p in ['/usr/bin/', '/bin/', '/sbin/', '/usr/sbin/']):
            return self.TRUST_LEVELS["system_binary"]
        if any(p in path for p in ['/usr/lib/', '/lib/', '/lib64/']):
            return self.TRUST_LEVELS["system_lib"]

        # Package-managed
        if any(p in path for p in ['site-packages', 'node_modules', '/usr/share/']):
            return self.TRUST_LEVELS["package_managed"]

        # User directories
        if '/home/' in path or 'Users/' in path:
            if 'downloads' in path.lower():
                return self.TRUST_LEVELS["downloaded"]
            return self.TRUST_LEVELS["user_app"]

        # Temp directories (least trusted)
        if any(p in path for p in ['/tmp/', '/dev/shm/', 'temp', 'cache']):
            return self.TRUST_LEVELS["unknown"]

        return self.TRUST_LEVELS["unknown"]

    def _path_to_angle(self, filepath: str) -> float:
        """
        Convert file path to angular position in hyperbolic space.
        Used for clustering similar files.
        """
        # Hash the directory to get consistent angle
        directory = os.path.dirname(filepath)
        hash_val = int(hashlib.md5(directory.encode()).hexdigest()[:8], 16)
        return (hash_val % 360) * (3.14159 / 180)  # Convert to radians
