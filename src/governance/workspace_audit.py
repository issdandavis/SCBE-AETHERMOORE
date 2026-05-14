"""Read-only Python reader for the SCBE workspace audit chain.

Downstream consumers (HYDRA, governance engine, scbe-flow runners) read
lineage / report receipts produced by the TypeScript CLI rather than
re-walk the receipt directory themselves. This module owns the
canonical Python shape that mirrors `aethermoor.bus.workspace_*.v1`.

Pure stdlib, no network, no writes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal, Optional, Union

LINEAGE_SCHEMA = "aethermoor.bus.workspace_lineage.v1"
REPORT_SCHEMA = "aethermoor.bus.workspace_report.v1"

LineageKind = Literal["formation", "ingest", "export", "verify", "import", "trap_dispatch", "unknown"]
AuditHealth = Literal["green", "amber", "red"]


@dataclass
class LineageEntry:
    kind: LineageKind
    receipt_path: str
    receipt_name: str
    timestamp: str
    schema_version: str
    receipt: str
    export_id: Optional[str] = None
    manifest_sha256: Optional[str] = None
    manifest_intact: Optional[bool] = None
    mismatch_count: Optional[int] = None
    # Populated only for trap_dispatch entries.
    gate_decision: Optional[str] = None
    redirect_emitted: Optional[bool] = None
    parse_error: Optional[str] = None


@dataclass
class WorkspaceLineage:
    schema_version: str
    receipt: str
    workspace_root: str
    workspace_id: str
    generated_at: str
    entries: List[LineageEntry] = field(default_factory=list)
    formation_count: int = 0
    ingest_count: int = 0
    export_count: int = 0
    verify_count: int = 0
    import_count: int = 0
    trap_dispatch_count: int = 0
    trap_redirect_count: int = 0
    unverified_exports: List[str] = field(default_factory=list)
    failed_verifies: int = 0


@dataclass
class FolderStat:
    path: str
    file_count: int
    total_bytes: int


@dataclass
class WorkspaceReport:
    schema_version: str
    receipt: str
    workspace_id: str
    workspace_root: str
    generated_at: str
    created_at: str
    folders: List[FolderStat] = field(default_factory=list)
    formation_count: int = 0
    ingest_count: int = 0
    export_count: int = 0
    verify_count: int = 0
    import_count: int = 0
    trap_dispatch_count: int = 0
    trap_redirect_count: int = 0
    failed_verifies: int = 0
    unverified_exports: List[str] = field(default_factory=list)
    last_activity: str = ""
    audit_health: AuditHealth = "green"


def _lineage_from_dict(d: dict) -> WorkspaceLineage:
    if d.get("schema_version") != LINEAGE_SCHEMA:
        raise ValueError(f"expected {LINEAGE_SCHEMA}, got {d.get('schema_version')!r}")
    entries: List[LineageEntry] = []
    for raw in d.get("entries", []):
        entries.append(
            LineageEntry(
                kind=raw.get("kind", "unknown"),
                receipt_path=raw.get("receipt_path", ""),
                receipt_name=raw.get("receipt_name", ""),
                timestamp=raw.get("timestamp", ""),
                schema_version=raw.get("schema_version", ""),
                receipt=raw.get("receipt", ""),
                export_id=raw.get("export_id"),
                manifest_sha256=raw.get("manifest_sha256"),
                manifest_intact=raw.get("manifest_intact"),
                mismatch_count=raw.get("mismatch_count"),
                gate_decision=raw.get("gate_decision"),
                redirect_emitted=raw.get("redirect_emitted"),
                parse_error=raw.get("parse_error"),
            )
        )
    return WorkspaceLineage(
        schema_version=d["schema_version"],
        receipt=d["receipt"],
        workspace_root=d["workspace_root"],
        workspace_id=d["workspace_id"],
        generated_at=d["generated_at"],
        entries=entries,
        formation_count=int(d.get("formation_count", 0)),
        ingest_count=int(d.get("ingest_count", 0)),
        export_count=int(d.get("export_count", 0)),
        verify_count=int(d.get("verify_count", 0)),
        import_count=int(d.get("import_count", 0)),
        trap_dispatch_count=int(d.get("trap_dispatch_count", 0)),
        trap_redirect_count=int(d.get("trap_redirect_count", 0)),
        unverified_exports=list(d.get("unverified_exports", [])),
        failed_verifies=int(d.get("failed_verifies", 0)),
    )


def _report_from_dict(d: dict) -> WorkspaceReport:
    if d.get("schema_version") != REPORT_SCHEMA:
        raise ValueError(f"expected {REPORT_SCHEMA}, got {d.get('schema_version')!r}")
    ls = d.get("lineage_summary", {})
    folders = [
        FolderStat(
            path=f.get("path", ""),
            file_count=int(f.get("file_count", 0)),
            total_bytes=int(f.get("total_bytes", 0)),
        )
        for f in d.get("folders", [])
    ]
    return WorkspaceReport(
        schema_version=d["schema_version"],
        receipt=d["receipt"],
        workspace_id=d["workspace_id"],
        workspace_root=d["workspace_root"],
        generated_at=d["generated_at"],
        created_at=d.get("created_at", ""),
        folders=folders,
        formation_count=int(ls.get("formation_count", 0)),
        ingest_count=int(ls.get("ingest_count", 0)),
        export_count=int(ls.get("export_count", 0)),
        verify_count=int(ls.get("verify_count", 0)),
        import_count=int(ls.get("import_count", 0)),
        trap_dispatch_count=int(ls.get("trap_dispatch_count", 0)),
        trap_redirect_count=int(ls.get("trap_redirect_count", 0)),
        failed_verifies=int(ls.get("failed_verifies", 0)),
        unverified_exports=list(ls.get("unverified_exports", [])),
        last_activity=d.get("last_activity", ""),
        audit_health=d.get("audit_health", "green"),
    )


def read_lineage(source: Union[str, Path, dict]) -> WorkspaceLineage:
    """Read a workspace lineage receipt from a file path, JSON string, or
    pre-parsed dict. Raises ValueError on schema mismatch.
    """
    if isinstance(source, dict):
        return _lineage_from_dict(source)
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).exists()):
        text = Path(source).read_text(encoding="utf-8")
    else:
        text = str(source)
    return _lineage_from_dict(json.loads(text))


def read_report(source: Union[str, Path, dict]) -> WorkspaceReport:
    """Read a workspace report receipt from a file path, JSON string, or
    pre-parsed dict. Raises ValueError on schema mismatch.
    """
    if isinstance(source, dict):
        return _report_from_dict(source)
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).exists()):
        text = Path(source).read_text(encoding="utf-8")
    else:
        text = str(source)
    return _report_from_dict(json.loads(text))


def has_unverified_exports(lineage: WorkspaceLineage) -> bool:
    return bool(lineage.unverified_exports)


def is_clean_chain(lineage: WorkspaceLineage) -> bool:
    """True iff every export has a passing verify and no verify recorded a failure."""
    return not has_unverified_exports(lineage) and lineage.failed_verifies == 0
