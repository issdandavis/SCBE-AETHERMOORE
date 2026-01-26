"""
AETHERMOORE Antivirus Engine
============================
Behavioral antivirus using physics-based threat detection.

Core Principles:
1. Lorentz Dilation - Suspicious processes get time-dilated (throttled)
2. Hyperbolic Trust - New executables start untrusted, earn trust over time
3. Byzantine Consensus - Multiple detection engines vote on threats
4. Soliton Integrity - Self-verifying file hashes detect tampering
5. 14-Layer Governance - Full security pipeline before execution

Usage:
    from aethermoore_av import Scanner, Monitor

    # Scan a file
    scanner = Scanner()
    result = scanner.scan_file("/path/to/file.exe")

    # Real-time monitoring
    monitor = Monitor("/home/user")
    monitor.start()
"""

from .scanner import Scanner, ScanResult
from .monitor import Monitor
from .trust_db import TrustDatabase
from .threat_engine import ThreatEngine, ThreatLevel

__version__ = "1.0.0"
__all__ = [
    "Scanner",
    "ScanResult",
    "Monitor",
    "TrustDatabase",
    "ThreatEngine",
    "ThreatLevel",
]
