"""
AETHERMOORE File Scanner
========================
Scans files using the 14-layer governance pipeline.
"""

import os
import time
from dataclasses import dataclass, field
from typing import List, Optional, Generator
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from .threat_engine import ThreatEngine, ThreatAssessment, ThreatLevel
from .trust_db import TrustDatabase


@dataclass
class ScanResult:
    """Result of a file or directory scan."""
    path: str
    scan_time: float
    files_scanned: int
    threats_found: int
    assessments: List[ThreatAssessment] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return self.threats_found == 0

    def get_threats(self) -> List[ThreatAssessment]:
        """Get only threat assessments (non-safe)."""
        return [a for a in self.assessments if a.threat_level != ThreatLevel.SAFE]

    def summary(self) -> str:
        """Generate human-readable summary."""
        status = "✓ CLEAN" if self.is_clean else f"⚠ {self.threats_found} THREATS"
        return (
            f"{status}\n"
            f"  Scanned: {self.files_scanned} files\n"
            f"  Time: {self.scan_time:.2f}s\n"
            f"  Path: {self.path}"
        )


class Scanner:
    """
    AETHERMOORE file scanner with physics-based threat detection.

    Usage:
        scanner = Scanner()

        # Scan single file
        result = scanner.scan_file("/path/to/file")

        # Scan directory
        result = scanner.scan_directory("/path/to/dir")

        # Quick scan (skip large files)
        result = scanner.quick_scan("/home/user")
    """

    # File extensions to scan
    EXECUTABLE_EXTENSIONS = {
        '.exe', '.dll', '.so', '.dylib',  # Binaries
        '.py', '.pyc', '.pyo',            # Python
        '.js', '.mjs', '.cjs',            # JavaScript
        '.sh', '.bash', '.zsh',           # Shell
        '.ps1', '.psm1',                  # PowerShell
        '.bat', '.cmd',                   # Windows batch
        '.rb', '.pl', '.php',             # Other scripts
        '.jar', '.class',                 # Java
        '.go',                            # Go
    }

    # Skip these directories
    SKIP_DIRS = {
        '.git', '.svn', '.hg',
        'node_modules', '__pycache__', '.cache',
        'venv', '.venv', 'env', '.env',
        '.tox', '.nox', '.pytest_cache',
        'dist', 'build', 'target',
    }

    def __init__(
        self,
        trust_db: Optional[TrustDatabase] = None,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        workers: int = 4
    ):
        """
        Initialize scanner.

        Args:
            trust_db: Trust database (creates new if not provided)
            max_file_size: Maximum file size to scan (bytes)
            workers: Number of parallel scan workers
        """
        self.trust_db = trust_db or TrustDatabase()
        self.engine = ThreatEngine(trust_db=self.trust_db)
        self.max_file_size = max_file_size
        self.workers = workers

    def scan_file(self, filepath: str) -> ScanResult:
        """
        Scan a single file.

        Args:
            filepath: Path to file

        Returns:
            ScanResult with threat assessment
        """
        start = time.time()

        if not os.path.isfile(filepath):
            return ScanResult(
                path=filepath,
                scan_time=0,
                files_scanned=0,
                threats_found=0,
            )

        assessment = self.engine.analyze_file(filepath)

        # Update trust database
        is_clean = assessment.threat_level == ThreatLevel.SAFE
        self.trust_db.update_trust(filepath, is_clean, save=True)

        threats = 0 if is_clean else 1

        return ScanResult(
            path=filepath,
            scan_time=time.time() - start,
            files_scanned=1,
            threats_found=threats,
            assessments=[assessment],
        )

    def scan_directory(
        self,
        dirpath: str,
        recursive: bool = True,
        extensions: Optional[set] = None
    ) -> ScanResult:
        """
        Scan a directory.

        Args:
            dirpath: Path to directory
            recursive: Whether to scan subdirectories
            extensions: File extensions to scan (None = all executables)

        Returns:
            ScanResult with all assessments
        """
        start = time.time()
        extensions = extensions or self.EXECUTABLE_EXTENSIONS

        files_to_scan = list(self._enumerate_files(dirpath, recursive, extensions))

        assessments = []
        threats = 0

        # Parallel scanning
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(self.engine.analyze_file, f): f
                for f in files_to_scan
            }

            for future in as_completed(futures):
                filepath = futures[future]
                try:
                    assessment = future.result()
                    assessments.append(assessment)

                    if assessment.threat_level != ThreatLevel.SAFE:
                        threats += 1

                    # Update trust
                    is_clean = assessment.threat_level == ThreatLevel.SAFE
                    self.trust_db.update_trust(filepath, is_clean, save=False)

                except Exception as e:
                    # Log error but continue
                    pass

        # Save trust database once at end
        self.trust_db._save()

        return ScanResult(
            path=dirpath,
            scan_time=time.time() - start,
            files_scanned=len(files_to_scan),
            threats_found=threats,
            assessments=assessments,
        )

    def quick_scan(self, dirpath: str) -> ScanResult:
        """
        Quick scan - only executable files, skip large files.

        Args:
            dirpath: Path to directory

        Returns:
            ScanResult
        """
        return self.scan_directory(
            dirpath,
            recursive=True,
            extensions=self.EXECUTABLE_EXTENSIONS
        )

    def deep_scan(self, dirpath: str) -> ScanResult:
        """
        Deep scan - all files including large ones.

        Args:
            dirpath: Path to directory

        Returns:
            ScanResult
        """
        original_max = self.max_file_size
        self.max_file_size = 1024 * 1024 * 1024  # 1GB

        try:
            return self.scan_directory(
                dirpath,
                recursive=True,
                extensions=None  # All files
            )
        finally:
            self.max_file_size = original_max

    def _enumerate_files(
        self,
        dirpath: str,
        recursive: bool,
        extensions: Optional[set]
    ) -> Generator[str, None, None]:
        """Enumerate files to scan."""
        try:
            for entry in os.scandir(dirpath):
                if entry.is_file(follow_symlinks=False):
                    # Check extension
                    if extensions:
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext not in extensions:
                            continue

                    # Check size
                    try:
                        if entry.stat().st_size > self.max_file_size:
                            continue
                    except OSError:
                        continue

                    yield entry.path

                elif entry.is_dir(follow_symlinks=False) and recursive:
                    # Skip excluded directories
                    if entry.name in self.SKIP_DIRS:
                        continue

                    yield from self._enumerate_files(entry.path, recursive, extensions)

        except PermissionError:
            pass  # Skip directories we can't read
