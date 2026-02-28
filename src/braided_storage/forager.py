"""
BraidedVoxelStore — Forager
===========================

Bee/ant-style agent that scouts, fetches, scans, and deposits data
into the braided storage pipeline.

@layer Layer 13 (risk scan), Layer 12 (turnstile action)
@component BraidedStorage.Forager
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import time
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError

from agents.antivirus_membrane import scan_text_for_threats, turnstile_action, ThreatScan
from src.braided_storage.types import (
    ForagerPayload,
    ScanResult,
    StoredRecord,
    Verdict,
)

if TYPE_CHECKING:
    from src.braided_storage.pipeline import BraidedVoxelStore


def _is_local_path(url_or_path: str) -> bool:
    """Detect local filesystem paths (including Windows drive letters).

    urlparse treats 'C:\\foo' as scheme='c', so we detect Windows
    absolute paths and Unix absolute paths before parsing.
    """
    # Windows: C:\... or C:/...
    if len(url_or_path) >= 2 and url_or_path[1] == ":" and url_or_path[0].isalpha():
        return True
    # Unix absolute path
    if url_or_path.startswith("/"):
        return True
    # Relative path (no scheme)
    parsed = urlparse(url_or_path)
    return parsed.scheme in ("", "file")


# Map antivirus membrane verdicts to our Verdict enum
_VERDICT_MAP = {
    "CLEAN": Verdict.CLEAN,
    "CAUTION": Verdict.CAUTION,
    "SUSPICIOUS": Verdict.SUSPICIOUS,
    "MALICIOUS": Verdict.MALICIOUS,
}


class Forager:
    """Bee/ant forager agent — scouts, fetches, scans, carries, deposits.

    Lifecycle::

        scout(loc) -> (exists, mime_type, size)
        fetch(loc) -> raw bytes + metadata
        scan(payload) -> ScanResult (antivirus membrane)
        carry(payload, scan) -> ForagerPayload with provenance
        deposit(payload, store) -> StoredRecord
        forage(loc, store) -> full pipeline
    """

    def __init__(self, *, agent_id: str = "forager-0", domain: str = "browser"):
        self.agent_id = agent_id
        self.domain = domain
        self._forage_count = 0

    # ------------------------------------------------------------------
    #  scout: discover what's at a location
    # ------------------------------------------------------------------

    def scout(self, url_or_path: str) -> dict:
        """Probe a location and return metadata without downloading.

        Returns:
            dict with keys: exists, mime_type, size, scheme
        """
        if _is_local_path(url_or_path):
            path = url_or_path
            parsed = urlparse(url_or_path)
            if parsed.scheme == "file":
                path = parsed.path
                # On Windows, strip leading / from /C:/... paths
                if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
                    path = path[1:]
            p = Path(path)
            if p.exists():
                mime, _ = mimetypes.guess_type(str(p))
                return {
                    "exists": True,
                    "mime_type": mime or "application/octet-stream",
                    "size": p.stat().st_size,
                    "scheme": "file",
                }
            return {"exists": False, "mime_type": None, "size": 0, "scheme": "file"}

        parsed = urlparse(url_or_path)
        if parsed.scheme in ("http", "https"):
            try:
                req = Request(url_or_path, method="HEAD")
                req.add_header("User-Agent", "SCBE-Forager/1.0")
                with urlopen(req, timeout=10) as resp:
                    ct = resp.headers.get("Content-Type", "application/octet-stream")
                    cl = int(resp.headers.get("Content-Length", 0))
                    return {
                        "exists": True,
                        "mime_type": ct.split(";")[0].strip(),
                        "size": cl,
                        "scheme": parsed.scheme,
                    }
            except (URLError, OSError, ValueError):
                return {"exists": False, "mime_type": None, "size": 0, "scheme": parsed.scheme}

        return {"exists": False, "mime_type": None, "size": 0, "scheme": parsed.scheme}

    # ------------------------------------------------------------------
    #  fetch: download raw bytes
    # ------------------------------------------------------------------

    def fetch(self, url_or_path: str) -> ForagerPayload:
        """Download content from a URL or read from local path.

        Returns:
            ForagerPayload with raw bytes and metadata.
        """
        if _is_local_path(url_or_path):
            path = url_or_path
            parsed = urlparse(url_or_path)
            if parsed.scheme == "file":
                path = parsed.path
                if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
                    path = path[1:]
            p = Path(path)
            raw = p.read_bytes()
            mime, _ = mimetypes.guess_type(str(p))
            return ForagerPayload(
                raw_bytes=raw,
                source=url_or_path,
                mime_type=mime or "application/octet-stream",
            )

        parsed = urlparse(url_or_path)
        if parsed.scheme in ("http", "https"):
            req = Request(url_or_path)
            req.add_header("User-Agent", "SCBE-Forager/1.0")
            with urlopen(req, timeout=30) as resp:
                raw = resp.read()
                ct = resp.headers.get("Content-Type", "application/octet-stream")
                return ForagerPayload(
                    raw_bytes=raw,
                    source=url_or_path,
                    mime_type=ct.split(";")[0].strip(),
                )

        raise ValueError(f"Unsupported scheme: {parsed.scheme}")

    # ------------------------------------------------------------------
    #  scan: run antivirus membrane
    # ------------------------------------------------------------------

    def scan(self, payload: ForagerPayload) -> ScanResult:
        """Run antivirus membrane on payload content.

        Text content is scanned for prompt injection and malware patterns.
        Binary content gets a minimal scan on decoded-attempt.
        """
        try:
            text = payload.raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            text = ""

        threat: ThreatScan = scan_text_for_threats(text)
        action = turnstile_action(self.domain, threat)
        verdict = _VERDICT_MAP.get(threat.verdict, Verdict.CAUTION)

        return ScanResult(
            verdict=verdict,
            risk_score=threat.risk_score,
            action=action,
            reasons=threat.reasons,
        )

    # ------------------------------------------------------------------
    #  carry: wrap with provenance
    # ------------------------------------------------------------------

    def carry(self, payload: ForagerPayload, scan: ScanResult) -> ForagerPayload:
        """Stamp provenance chain onto payload."""
        content_hash = hashlib.sha256(payload.raw_bytes).hexdigest()[:16]
        payload.provenance.append(
            f"{self.agent_id}:scan={scan.verdict.value}:"
            f"risk={scan.risk_score:.4f}:hash={content_hash}:"
            f"t={time.time():.0f}"
        )
        return payload

    # ------------------------------------------------------------------
    #  deposit: push into storage pipeline
    # ------------------------------------------------------------------

    def deposit(
        self,
        payload: ForagerPayload,
        scan: ScanResult,
        store: BraidedVoxelStore,
    ) -> StoredRecord:
        """Deposit a scanned payload into the braided storage pipeline."""
        return store.ingest(
            raw_bytes=payload.raw_bytes,
            source=payload.source,
            mime_type=payload.mime_type,
            scan_override=scan,
        )

    # ------------------------------------------------------------------
    #  forage: full pipeline
    # ------------------------------------------------------------------

    def forage(
        self,
        url_or_path: str,
        store: BraidedVoxelStore,
    ) -> Optional[StoredRecord]:
        """Full forager pipeline: scout -> fetch -> scan -> carry -> deposit.

        Returns None if the location doesn't exist.
        """
        self._forage_count += 1

        info = self.scout(url_or_path)
        if not info["exists"]:
            return None

        payload = self.fetch(url_or_path)
        scan = self.scan(payload)
        payload = self.carry(payload, scan)
        return self.deposit(payload, scan, store)

    @property
    def forage_count(self) -> int:
        return self._forage_count
