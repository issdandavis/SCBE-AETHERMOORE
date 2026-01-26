"""
AETHERMOORE Threat Engine
=========================
Physics-based threat detection using Lorentz dilation and hyperbolic trust.
"""

import hashlib
import os
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple
import struct

# Import AETHERMOORE math (relative imports)
from ..aethermoore_math.lorentz import lorentz_factor, dilated_path_cost, threat_velocity
from ..aethermoore_math.hyperbolic import hyperbolic_distance, trust_cost
from ..aethermoore_math.constants import COX_CONSTANT


class ThreatLevel(Enum):
    """Threat classification based on Lorentz factor."""
    SAFE = auto()        # γ < 1.2 (v < 0.3c)
    SUSPICIOUS = auto()  # γ 1.2-2.0 (v 0.3-0.6c)
    MALICIOUS = auto()   # γ 2.0-5.0 (v 0.6-0.9c)
    CRITICAL = auto()    # γ > 5.0 (v > 0.9c)


@dataclass
class ThreatSignal:
    """Individual threat signal from detection engine."""
    name: str
    score: float  # 0.0 to 1.0
    weight: float = 1.0
    details: str = ""


@dataclass
class ThreatAssessment:
    """Complete threat assessment for a target."""
    target: str
    threat_velocity: float  # 0.0 to 1.0 (fraction of c)
    lorentz_factor: float   # γ (time dilation factor)
    threat_level: ThreatLevel
    signals: List[ThreatSignal] = field(default_factory=list)
    trust_radius: float = 4.0  # Hyperbolic radius (0=core, 4=edge)
    recommendation: str = ""

    @property
    def should_quarantine(self) -> bool:
        return self.threat_level in (ThreatLevel.MALICIOUS, ThreatLevel.CRITICAL)

    @property
    def should_throttle(self) -> bool:
        return self.threat_level == ThreatLevel.SUSPICIOUS

    @property
    def execution_cost(self) -> float:
        """Dilated execution cost (higher = slower/blocked)."""
        return dilated_path_cost(1.0, self.threat_velocity)


class ThreatEngine:
    """
    Physics-based threat detection engine.

    Uses Lorentz dilation to "slow down" suspicious processes
    and hyperbolic geometry to model trust hierarchies.
    """

    # Known malicious patterns (simplified - real AV uses larger DB)
    MALICIOUS_PATTERNS = [
        # Ransomware indicators
        (r"\.encrypted$", 0.9, "Ransomware extension"),
        (r"readme.*ransom", 0.95, "Ransom note"),
        (r"your files have been encrypted", 0.95, "Ransom message"),

        # Shell/script injection
        (r"eval\s*\(", 0.6, "Eval injection risk"),
        (r"exec\s*\(", 0.5, "Exec call"),
        (r"os\.system\s*\(", 0.7, "OS command execution"),
        (r"subprocess\.(call|run|Popen)", 0.5, "Subprocess execution"),

        # Network exfiltration
        (r"socket\.connect", 0.4, "Network connection"),
        (r"requests\.(get|post)", 0.3, "HTTP request"),
        (r"urllib", 0.3, "URL access"),

        # Persistence mechanisms
        (r"HKEY_LOCAL_MACHINE", 0.6, "Registry modification"),
        (r"crontab", 0.5, "Cron persistence"),
        (r"\.bashrc|\.profile", 0.4, "Shell config modification"),

        # Crypto mining
        (r"stratum\+tcp://", 0.9, "Mining pool connection"),
        (r"xmrig|minerd|cpuminer", 0.95, "Crypto miner"),

        # Keyloggers
        (r"pynput|keyboard\.hook", 0.8, "Keyboard hook"),
        (r"GetAsyncKeyState", 0.85, "Windows keylogger API"),
    ]

    # Known safe patterns (whitelist)
    SAFE_PATTERNS = [
        (r"^/usr/bin/", 0.3, "System binary"),
        (r"^/usr/lib/", 0.3, "System library"),
        (r"\.pyc$", 0.2, "Python bytecode"),
        (r"node_modules", 0.1, "NPM package"),
    ]

    def __init__(self, trust_db: Optional["TrustDatabase"] = None):
        self.trust_db = trust_db
        self._compiled_malicious = [
            (re.compile(p, re.IGNORECASE), s, d)
            for p, s, d in self.MALICIOUS_PATTERNS
        ]
        self._compiled_safe = [
            (re.compile(p, re.IGNORECASE), s, d)
            for p, s, d in self.SAFE_PATTERNS
        ]

    def analyze_file(self, filepath: str, content: Optional[bytes] = None) -> ThreatAssessment:
        """
        Analyze a file for threats using multi-signal detection.

        Args:
            filepath: Path to file
            content: Optional file content (reads if not provided)

        Returns:
            ThreatAssessment with Lorentz-dilated threat score
        """
        signals = []

        # 1. File path analysis
        path_signals = self._analyze_path(filepath)
        signals.extend(path_signals)

        # 2. Content analysis (if available)
        if content is None and os.path.isfile(filepath):
            try:
                with open(filepath, 'rb') as f:
                    content = f.read(1024 * 1024)  # First 1MB
            except (IOError, PermissionError):
                signals.append(ThreatSignal(
                    name="read_error",
                    score=0.3,
                    details="Cannot read file (possible protection)"
                ))

        if content:
            content_signals = self._analyze_content(content)
            signals.extend(content_signals)

            # 3. Entropy analysis (packed/encrypted detection)
            entropy_signal = self._analyze_entropy(content)
            if entropy_signal:
                signals.append(entropy_signal)

        # 4. Trust database lookup
        trust_radius = 4.0  # Default: untrusted (edge)
        if self.trust_db:
            trust_radius = self.trust_db.get_trust_radius(filepath)

        # 5. Calculate composite threat velocity
        v = self._calculate_threat_velocity(signals, trust_radius)

        # 6. Apply Lorentz factor
        gamma = lorentz_factor(v)

        # 7. Classify threat level
        level = self._classify_threat(gamma)

        # 8. Generate recommendation
        recommendation = self._generate_recommendation(level, gamma, signals)

        return ThreatAssessment(
            target=filepath,
            threat_velocity=v,
            lorentz_factor=gamma,
            threat_level=level,
            signals=signals,
            trust_radius=trust_radius,
            recommendation=recommendation,
        )

    def _analyze_path(self, filepath: str) -> List[ThreatSignal]:
        """Analyze file path for threat indicators."""
        signals = []

        # Check against safe patterns (reduces threat)
        for pattern, reduction, desc in self._compiled_safe:
            if pattern.search(filepath):
                signals.append(ThreatSignal(
                    name="safe_path",
                    score=-reduction,  # Negative = reduces threat
                    details=desc
                ))

        # Check against malicious patterns
        for pattern, score, desc in self._compiled_malicious:
            if pattern.search(filepath):
                signals.append(ThreatSignal(
                    name="path_match",
                    score=score,
                    details=desc
                ))

        # Suspicious locations
        suspicious_paths = [
            ("/tmp/", 0.3, "Temp directory"),
            ("/dev/shm/", 0.5, "Shared memory (fileless malware)"),
            ("AppData/Local/Temp", 0.3, "Windows temp"),
            ("Downloads/", 0.2, "Downloads folder"),
        ]

        for path, score, desc in suspicious_paths:
            if path in filepath:
                signals.append(ThreatSignal(
                    name="suspicious_location",
                    score=score,
                    details=desc
                ))

        return signals

    def _analyze_content(self, content: bytes) -> List[ThreatSignal]:
        """Analyze file content for threat patterns."""
        signals = []

        # Try to decode as text
        try:
            text = content.decode('utf-8', errors='ignore')
        except:
            text = ""

        # Check against malicious patterns
        for pattern, score, desc in self._compiled_malicious:
            matches = pattern.findall(text)
            if matches:
                signals.append(ThreatSignal(
                    name="content_match",
                    score=min(score * len(matches), 0.99),
                    details=f"{desc} ({len(matches)} occurrences)"
                ))

        # Binary analysis
        if content[:2] == b'MZ':  # Windows PE
            signals.append(ThreatSignal(
                name="windows_executable",
                score=0.2,
                details="Windows PE executable"
            ))
        elif content[:4] == b'\x7fELF':  # Linux ELF
            signals.append(ThreatSignal(
                name="linux_executable",
                score=0.1,
                details="Linux ELF executable"
            ))
        elif content[:2] == b'#!':  # Shebang
            signals.append(ThreatSignal(
                name="script",
                score=0.1,
                details="Script with shebang"
            ))

        return signals

    def _analyze_entropy(self, content: bytes) -> Optional[ThreatSignal]:
        """
        Analyze byte entropy to detect packed/encrypted content.
        High entropy (>7.0) suggests encryption or packing.
        """
        if len(content) < 256:
            return None

        # Calculate Shannon entropy
        byte_counts = [0] * 256
        for byte in content:
            byte_counts[byte] += 1

        entropy = 0.0
        length = len(content)
        for count in byte_counts:
            if count > 0:
                p = count / length
                entropy -= p * (p and __import__('math').log2(p))

        # High entropy is suspicious
        if entropy > 7.5:
            return ThreatSignal(
                name="high_entropy",
                score=0.7,
                details=f"Entropy {entropy:.2f} (likely encrypted/packed)"
            )
        elif entropy > 7.0:
            return ThreatSignal(
                name="elevated_entropy",
                score=0.4,
                details=f"Entropy {entropy:.2f} (possibly compressed)"
            )

        return None

    def _calculate_threat_velocity(
        self,
        signals: List[ThreatSignal],
        trust_radius: float
    ) -> float:
        """
        Calculate composite threat velocity from signals.

        Uses weighted combination of signals plus hyperbolic trust penalty.
        """
        if not signals:
            # No signals = base threat from trust radius
            return min(trust_radius / 10.0, 0.3)

        # Weighted signal aggregation
        total_weight = sum(abs(s.weight) for s in signals)
        if total_weight == 0:
            return 0.0

        weighted_score = sum(s.score * s.weight for s in signals) / total_weight

        # Apply hyperbolic trust penalty
        # Agents at edge (r=4) get +0.2 threat boost
        trust_penalty = trust_radius / 20.0

        # Combine and clamp
        v = weighted_score + trust_penalty
        return max(0.0, min(0.9999, v))

    def _classify_threat(self, gamma: float) -> ThreatLevel:
        """Classify threat level based on Lorentz factor."""
        if gamma < 1.2:
            return ThreatLevel.SAFE
        elif gamma < 2.0:
            return ThreatLevel.SUSPICIOUS
        elif gamma < 5.0:
            return ThreatLevel.MALICIOUS
        else:
            return ThreatLevel.CRITICAL

    def _generate_recommendation(
        self,
        level: ThreatLevel,
        gamma: float,
        signals: List[ThreatSignal]
    ) -> str:
        """Generate human-readable recommendation."""
        if level == ThreatLevel.SAFE:
            return "ALLOW: No significant threats detected"
        elif level == ThreatLevel.SUSPICIOUS:
            top_signals = sorted(signals, key=lambda s: s.score, reverse=True)[:3]
            reasons = ", ".join(s.details for s in top_signals if s.score > 0)
            return f"THROTTLE (γ={gamma:.1f}x): {reasons}"
        elif level == ThreatLevel.MALICIOUS:
            top_signals = sorted(signals, key=lambda s: s.score, reverse=True)[:3]
            reasons = ", ".join(s.details for s in top_signals if s.score > 0)
            return f"QUARANTINE (γ={gamma:.1f}x): {reasons}"
        else:
            return f"BLOCK (γ={gamma:.1f}x): Critical threat - immediate quarantine"


def calculate_file_hash(filepath: str, algorithm: str = 'sha256') -> str:
    """Calculate cryptographic hash of file."""
    h = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()
