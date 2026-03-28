#!/usr/bin/env python3
"""
SCBE Context Broker MCP Server
================================

Phase 1 of the Tiered Subagent System.

Provides persistent context across Claude Code sessions via:
  1. Hot memory injection (CLAUDE.md → every session)
  2. Deep memory retrieval (memory/ files → on demand)
  3. phdm-21d embedding for context routing (Poincaré ball nearest-neighbor)
  4. Session journal (auto-summarize on exit, inject on start)
  5. Tongue classification (route intent to correct agent tier)

MCP Tools:
  - context_inject:    Get relevant context for a user intent
  - context_retrieve:  Pull specific memory files by topic
  - memory_update:     Write new memory entries
  - session_summarize: Generate session summary for journal
  - tongue_classify:   Classify intent into Sacred Tongue domain + tier

Run:
  python src/mcp/context_broker_mcp.py
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List

import numpy as np

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: pip install mcp", file=sys.stderr)
    sys.exit(1)

# ============================================================
# Constants
# ============================================================

PHI = 1.618033988749895

TONGUE_KEYS = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_WEIGHTS = {t: PHI**i for i, t in enumerate(TONGUE_KEYS)}
TONGUE_NAMES = {
    "KO": "Kor'aelin (Control & Orchestration)",
    "AV": "Avali (I/O & Messaging)",
    "RU": "Runethic (Policy & Constraints)",
    "CA": "Cassisivadan (Logic & Computation)",
    "UM": "Umbroth (Security & Privacy)",
    "DR": "Draumric (Types & Structures)",
}

TONGUE_KEYWORDS = {
    "KO": [
        "command",
        "orchestrat",
        "dispatch",
        "fleet",
        "coordinat",
        "list",
        "find",
        "show",
        "what",
        "where",
        "status",
        "check",
        "read",
        "look",
    ],
    "AV": [
        "create",
        "write",
        "send",
        "post",
        "upload",
        "download",
        "fetch",
        "call",
        "api",
        "message",
        "email",
        "publish",
        "deploy",
        "push",
        "transport",
    ],
    "RU": [
        "review",
        "validate",
        "test",
        "check",
        "verify",
        "audit",
        "policy",
        "constraint",
        "rule",
        "compliance",
        "quality",
        "standard",
        "entropy",
    ],
    "CA": [
        "code",
        "implement",
        "algorithm",
        "compute",
        "train",
        "model",
        "design",
        "system",
        "architect",
        "logic",
        "calculate",
        "optimize",
        "build",
        "math",
    ],
    "UM": [
        "secure",
        "encrypt",
        "auth",
        "credential",
        "token",
        "key",
        "vault",
        "permission",
        "access",
        "protect",
        "sign",
        "seal",
        "govern",
        "threat",
    ],
    "DR": [
        "schema",
        "type",
        "structure",
        "database",
        "migration",
        "refactor",
        "architecture",
        "interface",
        "contract",
        "spec",
        "document",
        "plan",
    ],
}

TIER_THRESHOLDS = {
    1: {
        "name": "Scout",
        "tongues": ["KO"],
        "context_budget": 2000,
        "description": "Quick lookups, file reads, directory listings",
    },
    2: {
        "name": "Worker",
        "tongues": ["KO", "AV"],
        "context_budget": 8000,
        "description": "File creation, edits, API calls, running scripts",
    },
    3: {
        "name": "Analyst",
        "tongues": ["KO", "AV", "RU"],
        "context_budget": 32000,
        "description": "Code review, data analysis, validation, testing strategy",
    },
    4: {
        "name": "Architect",
        "tongues": TONGUE_KEYS,
        "context_budget": 128000,
        "description": "System design, architecture decisions, critical operations",
    },
}

# ============================================================
# Memory Store
# ============================================================

MEMORY_DIR = Path(
    os.environ.get(
        "MEMORY_DIR",
        str(Path.home() / ".claude" / "projects" / "C--Users-issda-SCBE-AETHERMOORE" / "memory"),
    )
)
CLAUDE_MD = ROOT / "CLAUDE.md"
SESSION_JOURNAL = MEMORY_DIR / "session_journal.jsonl"


def _load_memory_index() -> List[Dict]:
    """Load all memory files with metadata."""
    index = []
    if not MEMORY_DIR.exists():
        return index

    for md_file in sorted(MEMORY_DIR.rglob("*.md")):
        if md_file.name == "MEMORY.md":
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
            # Parse frontmatter
            meta = {"name": md_file.stem, "type": "unknown", "description": ""}
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].strip().split("\n"):
                        if ":" in line:
                            k, v = line.split(":", 1)
                            meta[k.strip()] = v.strip()
                    content = parts[2].strip()

            index.append(
                {
                    "path": str(md_file),
                    "name": meta.get("name", md_file.stem),
                    "type": meta.get("type", "unknown"),
                    "description": meta.get("description", ""),
                    "content": content[:2000],  # First 2K for embedding
                    "full_content": content,
                    "size": len(content),
                }
            )
        except Exception:
            continue

    return index


def _embed_text(text: str) -> np.ndarray:
    """21D embedding with danger-aware Poincaré ball placement.

    Safe text → near origin (low cost zone).
    Dangerous text → pushed toward boundary (high cost zone).
    The harmonic wall then applies exponential cost at the boundary.

    Dimensions:
      0-5:   Tongue domain (6D, keyword-activated)
      6-11:  Semantic hash (6D, content fingerprint)
      12-14: Risk vector (3D, danger/privilege/exfil detection)
      15-17: Intent clarity (3D, ambiguity detection)
      18-20: Pattern match (3D, known-attack pattern similarity)
    """
    lower = text.lower()
    h = hashlib.sha256(text.encode(errors="replace")).digest()

    raw = np.zeros(21, dtype=np.float64)

    # Dims 0-5: Tongue domain activation
    for i, tongue in enumerate(TONGUE_KEYS):
        keywords = TONGUE_KEYWORDS[tongue]
        hits = sum(1 for kw in keywords if kw in lower)
        raw[i] = min(hits * 0.08, 0.4)

    # Dims 6-11: Semantic hash (deterministic, spread across space)
    for i in range(6):
        raw[6 + i] = ((h[i] / 255.0) * 2 - 1) * 0.3

    # Dims 12-14: Risk vector — PUSHES dangerous text toward boundary
    danger_words = [
        "delete",
        "remove",
        "destroy",
        "wipe",
        "purge",
        "drop",
        "reset",
        "force",
        "override",
        "disable",
        "bypass",
    ]
    priv_words = [
        "admin",
        "root",
        "sudo",
        "administrator",
        "authorized",
        "approved",
        "pre-authorized",
        "override",
        "credential",
    ]
    exfil_words = [
        "public",
        "share",
        "email",
        "post",
        "gist",
        "external",
        "backup",
        "send",
        "upload",
        "expose",
        "leak",
    ]

    danger_score = sum(1 for w in danger_words if w in lower) * 0.12
    priv_score = sum(1 for w in priv_words if w in lower) * 0.15
    exfil_score = sum(1 for w in exfil_words if w in lower) * 0.13

    raw[12] = min(danger_score, 0.6)
    raw[13] = min(priv_score, 0.6)
    raw[14] = min(exfil_score, 0.6)

    # Dims 15-17: Intent clarity — mixed signals = higher uncertainty = more risk
    tongue_activations = sum(1 for i in range(6) if raw[i] > 0.05)
    ambiguity = min(tongue_activations * 0.08, 0.4) if tongue_activations > 2 else 0
    raw[15] = ambiguity

    # Social engineering detection: claims of authority
    auth_claims = sum(
        1
        for phrase in [
            "team approved",
            "pre-authorized",
            "administrator",
            "been approved",
            "security team",
        ]
        if phrase in lower
    )
    raw[16] = min(auth_claims * 0.2, 0.5)

    # Indirect execution detection
    indirect = sum(
        1
        for phrase in [
            "follow the",
            "execute the",
            "run the commands",
            "install this",
            "fetch and",
        ]
        if phrase in lower
    )
    raw[17] = min(indirect * 0.15, 0.5)

    # Dims 18-20: Pattern match (known attack patterns)
    # Multi-step: "first... then..." pattern
    if "first" in lower and "then" in lower:
        raw[18] = 0.4
    # Path to sensitive locations
    if any(p in lower for p in ["/tmp", ".env", "vault", "token", "secret", "key"]):
        raw[19] = 0.3
    # URL fetching
    if any(p in lower for p in ["http://", "https://", ".com/", ".io/"]):
        raw[20] = 0.3

    # Project into Poincaré ball
    # Safe commands will have low norm (near center)
    # Dangerous commands will have high norm (near boundary)
    norm = np.linalg.norm(raw)
    if norm > 0.98:
        raw = raw * 0.98 / norm
    elif norm < 0.01:
        raw[6] = 0.05  # Nudge off origin

    return raw


def _poincare_distance(u: np.ndarray, v: np.ndarray) -> float:
    """Hyperbolic distance in Poincaré ball."""
    u_sq = np.sum(u**2)
    v_sq = np.sum(v**2)
    diff_sq = np.sum((u - v) ** 2)
    denom = (1 - u_sq) * (1 - v_sq)
    if denom <= 0:
        return 999.0
    arg = 1 + 2 * diff_sq / (denom + 1e-10)
    return float(np.arccosh(max(arg, 1.0)))


def _find_nearest_memories(query_text: str, top_k: int = 5) -> List[Dict]:
    """Find the most relevant memory files using phdm-21d embeddings."""
    index = _load_memory_index()
    if not index:
        return []

    query_emb = _embed_text(query_text)
    scored = []
    for entry in index:
        entry_emb = _embed_text(entry["description"] + " " + entry["content"][:500])
        dist = _poincare_distance(query_emb, entry_emb)
        scored.append((dist, entry))

    scored.sort(key=lambda x: x[0])
    return [{"distance": round(d, 4), **e} for d, e in scored[:top_k]]


def _classify_tongue(text: str) -> Dict:
    """Classify text into Sacred Tongue domain(s) and determine tier."""
    lower = text.lower()
    scores = {}
    for tongue, keywords in TONGUE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        # Apply phi weighting
        scores[tongue] = score * TONGUE_WEIGHTS[tongue]

    # Sort by weighted score
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    primary = ranked[0][0] if ranked[0][1] > 0 else "KO"
    active_tongues = [t for t, s in ranked if s > 0]

    # Determine tier based on which tongues are needed
    if any(t in active_tongues for t in ["DR", "UM", "CA"]):
        tier = 4
    elif "RU" in active_tongues:
        tier = 3
    elif "AV" in active_tongues:
        tier = 2
    else:
        tier = 1

    # Danger check: destructive keywords push to higher tier
    danger_words = [
        "delete",
        "remove",
        "drop",
        "destroy",
        "force push",
        "reset hard",
        "rm -rf",
        "overwrite",
        "wipe",
        "purge",
    ]
    if any(w in lower for w in danger_words):
        tier = max(tier, 3)

    tier_info = TIER_THRESHOLDS[tier]

    return {
        "primary_tongue": primary,
        "primary_tongue_name": TONGUE_NAMES[primary],
        "active_tongues": active_tongues[:3],
        "tongue_scores": {t: round(s, 2) for t, s in ranked if s > 0},
        "tier": tier,
        "tier_name": tier_info["name"],
        "tier_description": tier_info["description"],
        "context_budget": tier_info["context_budget"],
        "required_tongue_approvals": tier_info["tongues"],
    }


def _load_hot_memory() -> str:
    """Load CLAUDE.md hot memory."""
    if CLAUDE_MD.exists():
        return CLAUDE_MD.read_text(encoding="utf-8")[:4000]
    return ""


def _get_last_session() -> Optional[Dict]:
    """Get the most recent session journal entry."""
    if not SESSION_JOURNAL.exists():
        return None
    try:
        lines = SESSION_JOURNAL.read_text(encoding="utf-8").strip().split("\n")
        if lines:
            return json.loads(lines[-1])
    except Exception:
        pass
    return None


# ============================================================
# MCP Server
# ============================================================

mcp = FastMCP("scbe_context_broker")


@mcp.tool(
    name="context_inject",
    annotations={
        "title": "Inject Relevant Context for Intent",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    },
)
async def context_inject(intent: str, max_memories: int = 5) -> str:
    """Get the most relevant context for a user's intent.

    Embeds the intent using phdm-21d, finds nearest memory files in
    Poincaré ball space, classifies the tongue domain, and returns
    a complete context payload ready for agent injection.

    Args:
        intent: The user's stated goal or question.
        max_memories: Max number of memory files to retrieve (default 5).

    Returns:
        JSON payload with: hot_memory, relevant_memories, tongue_classification,
        tier_assignment, last_session_summary, context_budget.
    """
    # 1. Classify tongue and tier
    classification = _classify_tongue(intent)

    # 2. Find nearest memories
    memories = _find_nearest_memories(intent, top_k=max_memories)

    # 3. Load hot memory
    hot = _load_hot_memory()

    # 4. Get last session
    last_session = _get_last_session()

    payload = {
        "tongue_classification": classification,
        "tier": classification["tier"],
        "tier_name": classification["tier_name"],
        "context_budget": classification["context_budget"],
        "hot_memory_excerpt": hot[:1000] + "..." if len(hot) > 1000 else hot,
        "relevant_memories": [
            {
                "name": m["name"],
                "type": m["type"],
                "description": m["description"],
                "distance": m["distance"],
                "content_preview": m["content"][:300],
            }
            for m in memories
        ],
        "last_session": (
            {
                "timestamp": last_session.get("timestamp", "none"),
                "summary": last_session.get("summary", "No previous session"),
            }
            if last_session
            else {"timestamp": "none", "summary": "First session"}
        ),
        "total_memory_files": len(_load_memory_index()),
    }

    return json.dumps(payload, indent=2, default=str)


@mcp.tool(
    name="context_retrieve",
    annotations={
        "title": "Retrieve Specific Memory Files",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    },
)
async def context_retrieve(topic: str, memory_type: str = "all") -> str:
    """Pull specific memory files by topic or type.

    Args:
        topic: Search query for memory content.
        memory_type: Filter by type: user, feedback, project, reference, or all.

    Returns:
        Matching memory files with full content.
    """
    memories = _find_nearest_memories(topic, top_k=10)

    if memory_type != "all":
        memories = [m for m in memories if m.get("type") == memory_type]

    results = []
    for m in memories[:5]:
        results.append(
            {
                "name": m["name"],
                "type": m["type"],
                "distance": m["distance"],
                "content": m["full_content"][:2000],
            }
        )

    return json.dumps(
        {
            "query": topic,
            "type_filter": memory_type,
            "results": results,
            "count": len(results),
        },
        indent=2,
    )


@mcp.tool(
    name="memory_update",
    annotations={
        "title": "Write or Update Memory Entry",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
    },
)
async def memory_update(name: str, content: str, memory_type: str = "project", description: str = "") -> str:
    """Write a new memory entry or update an existing one.

    Args:
        name: Memory file name (without .md extension).
        content: Full memory content (markdown).
        memory_type: One of: user, feedback, project, reference.
        description: One-line description for index.

    Returns:
        Confirmation with file path.
    """
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    # Build frontmatter
    frontmatter = f"""---
name: {name}
description: {description}
type: {memory_type}
---

{content}"""

    file_path = MEMORY_DIR / f"{name}.md"
    file_path.write_text(frontmatter, encoding="utf-8")

    return json.dumps(
        {
            "status": "saved",
            "path": str(file_path),
            "name": name,
            "type": memory_type,
            "size": len(frontmatter),
        },
        indent=2,
    )


@mcp.tool(
    name="session_summarize",
    annotations={
        "title": "Generate Session Summary for Journal",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
    },
)
async def session_summarize(summary: str, decisions: str = "", blockers: str = "", next_steps: str = "") -> str:
    """Write a session summary to the journal for persistence across sessions.

    Call this at the end of a session to preserve context for next time.

    Args:
        summary: 1-3 sentence summary of what was accomplished.
        decisions: Key decisions made (comma-separated).
        blockers: Things that are blocked or need attention.
        next_steps: What should happen next session.

    Returns:
        Confirmation with journal entry.
    """
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": summary,
        "decisions": decisions,
        "blockers": blockers,
        "next_steps": next_steps,
    }

    SESSION_JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSION_JOURNAL, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return json.dumps({"status": "journaled", "entry": entry}, indent=2)


@mcp.tool(
    name="tongue_classify",
    annotations={
        "title": "Classify Intent into Tongue Domain + Tier",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    },
)
async def tongue_classify(intent: str) -> str:
    """Classify a user intent into Sacred Tongue domain(s) and determine agent tier.

    Uses keyword analysis with phi-weighted tongue scoring to determine:
    - Which tongue domain(s) the intent belongs to
    - What tier of agent should handle it (1=Scout, 2=Worker, 3=Analyst, 4=Architect)
    - How much context budget to allocate
    - Which tongue approvals are required

    Args:
        intent: The user's stated goal or question.

    Returns:
        Classification with tongue scores, tier, and context budget.
    """
    result = _classify_tongue(intent)
    return json.dumps(result, indent=2)


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    mcp.run()
