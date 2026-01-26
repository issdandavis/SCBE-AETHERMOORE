"""
AETHERMOORE Real-Time Monitor
=============================
Watches file system for changes and scans new/modified files.
"""

import os
import time
import threading
import queue
from dataclasses import dataclass
from typing import Callable, Optional, Set
from pathlib import Path

from .scanner import Scanner
from .threat_engine import ThreatLevel, ThreatAssessment


@dataclass
class FileEvent:
    """File system event."""
    path: str
    event_type: str  # "created", "modified", "deleted"
    timestamp: float


class Monitor:
    """
    Real-time file system monitor with threat scanning.

    Uses polling-based approach for cross-platform compatibility.
    For production, consider using watchdog library.

    Usage:
        monitor = Monitor("/home/user")

        # Set callback for threats
        monitor.on_threat = lambda a: print(f"THREAT: {a.target}")

        # Start monitoring
        monitor.start()

        # Stop monitoring
        monitor.stop()
    """

    def __init__(
        self,
        watch_path: str,
        scanner: Optional[Scanner] = None,
        poll_interval: float = 1.0,
        recursive: bool = True
    ):
        """
        Initialize monitor.

        Args:
            watch_path: Directory to monitor
            scanner: Scanner instance (creates new if not provided)
            poll_interval: Seconds between file system checks
            recursive: Whether to monitor subdirectories
        """
        self.watch_path = os.path.abspath(watch_path)
        self.scanner = scanner or Scanner()
        self.poll_interval = poll_interval
        self.recursive = recursive

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._event_queue: queue.Queue = queue.Queue()
        self._file_states: dict = {}  # path -> (mtime, size)

        # Callbacks
        self.on_threat: Optional[Callable[[ThreatAssessment], None]] = None
        self.on_clean: Optional[Callable[[ThreatAssessment], None]] = None
        self.on_event: Optional[Callable[[FileEvent], None]] = None

    def start(self):
        """Start monitoring in background thread."""
        if self._running:
            return

        self._running = True

        # Initial scan to build file state
        self._build_initial_state()

        # Start monitor thread
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

        # Start event processor
        self._processor = threading.Thread(target=self._process_events, daemon=True)
        self._processor.start()

        print(f"[AETHERMOORE] Monitoring: {self.watch_path}")

    def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("[AETHERMOORE] Monitor stopped")

    def _build_initial_state(self):
        """Build initial file state dictionary."""
        for filepath in self._enumerate_files():
            try:
                stat = os.stat(filepath)
                self._file_states[filepath] = (stat.st_mtime, stat.st_size)
            except OSError:
                pass

    def _enumerate_files(self) -> Set[str]:
        """Enumerate all files in watch path."""
        files = set()

        for root, dirs, filenames in os.walk(self.watch_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in Scanner.SKIP_DIRS]

            if not self.recursive:
                dirs.clear()

            for filename in filenames:
                filepath = os.path.join(root, filename)
                files.add(filepath)

        return files

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                self._check_changes()
            except Exception as e:
                print(f"[AETHERMOORE] Monitor error: {e}")

            time.sleep(self.poll_interval)

    def _check_changes(self):
        """Check for file system changes."""
        current_files = self._enumerate_files()
        previous_files = set(self._file_states.keys())

        # New files
        new_files = current_files - previous_files
        for filepath in new_files:
            try:
                stat = os.stat(filepath)
                self._file_states[filepath] = (stat.st_mtime, stat.st_size)
                self._event_queue.put(FileEvent(
                    path=filepath,
                    event_type="created",
                    timestamp=time.time()
                ))
            except OSError:
                pass

        # Deleted files
        deleted_files = previous_files - current_files
        for filepath in deleted_files:
            del self._file_states[filepath]
            self._event_queue.put(FileEvent(
                path=filepath,
                event_type="deleted",
                timestamp=time.time()
            ))

        # Modified files
        for filepath in current_files & previous_files:
            try:
                stat = os.stat(filepath)
                old_mtime, old_size = self._file_states.get(filepath, (0, 0))

                if stat.st_mtime != old_mtime or stat.st_size != old_size:
                    self._file_states[filepath] = (stat.st_mtime, stat.st_size)
                    self._event_queue.put(FileEvent(
                        path=filepath,
                        event_type="modified",
                        timestamp=time.time()
                    ))
            except OSError:
                pass

    def _process_events(self):
        """Process file events and run scans."""
        while self._running:
            try:
                event = self._event_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # Call event callback
            if self.on_event:
                try:
                    self.on_event(event)
                except Exception:
                    pass

            # Skip deleted files
            if event.event_type == "deleted":
                continue

            # Scan the file
            try:
                result = self.scanner.scan_file(event.path)

                if result.assessments:
                    assessment = result.assessments[0]

                    if assessment.threat_level != ThreatLevel.SAFE:
                        print(f"[THREAT] {assessment.threat_level.name}: {event.path}")
                        print(f"         γ={assessment.lorentz_factor:.2f}, {assessment.recommendation}")

                        if self.on_threat:
                            self.on_threat(assessment)
                    else:
                        if self.on_clean:
                            self.on_clean(assessment)

            except Exception as e:
                print(f"[AETHERMOORE] Scan error for {event.path}: {e}")


def watch(path: str, callback: Optional[Callable] = None) -> Monitor:
    """
    Convenience function to start monitoring.

    Args:
        path: Directory to monitor
        callback: Optional callback for threats

    Returns:
        Monitor instance (already started)

    Usage:
        monitor = watch("/home/user", callback=lambda a: print(a))
        # ... later ...
        monitor.stop()
    """
    monitor = Monitor(path)
    if callback:
        monitor.on_threat = callback
    monitor.start()
    return monitor
