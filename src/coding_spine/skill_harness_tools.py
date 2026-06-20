"""Discover Codex/Claude-style ``SKILL.md`` files and expose them as harness tools.

Agents receive structured tool definitions (OpenAI function-calling shape) plus
metadata paths so runtimes can load the full skill body on demand.

Search roots (existing dirs only):

- ``<repo>/.claude/skills/*``
- ``<repo>/.agents/skills/*``
- ``<repo>/skills/*`` (optional repo-local lane)

Extra absolute paths via ``SCBE_HARNESS_SKILL_ROOTS`` (``;`` on Windows, ``;``
or ``:`` on POSIX). Example::

    SCBE_HARNESS_SKILL_ROOTS=C:\\Users\\me\\.codex\\skills

Caps: ``SCBE_HARNESS_SKILL_MAX`` (default 400), description length 2400 chars.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "scbe_harness_skill_tools_v1"

_DEFAULT_RELATIVE_ROOTS = (
    ".claude/skills",
    ".agents/skills",
    "skills",
)

_TOOL_NAME_RE = re.compile(r"[^a-z0-9_]+")

FUNCTION_AREAS: dict[str, dict[str, str]] = {
    "agent_tool": {
        "abbrev": "agt",
        "label": "Agent orchestration, coding helpers, model runners, handoffs, and swarm work.",
    },
    "cli_tool": {
        "abbrev": "cli",
        "label": "Command-line, shell, terminal, local service, and developer-machine tools.",
    },
    "recon_tool": {
        "abbrev": "rec",
        "label": "Research, browsing, source verification, email triage, opportunity discovery, "
        "and intelligence gathering.",
    },
    "training_tool": {
        "abbrev": "trn",
        "label": "Training data, model fine-tuning, evaluation, benchmark, and dataset pipelines.",
    },
    "governance_tool": {
        "abbrev": "gov",
        "label": "Policy, safety, compliance, security, authorization, and evidence gates.",
    },
    "data_tool": {
        "abbrev": "dat",
        "label": "Storage, backup, document management, RAG, notes, and structured data movement.",
    },
    "publishing_tool": {
        "abbrev": "pub",
        "label": "Writing, articles, website, art, media, story, and public-surface publishing.",
    },
    "commerce_tool": {
        "abbrev": "com",
        "label": "Checkout, revenue, Shopify, Stripe, sales, and product packaging.",
    },
    "ops_tool": {
        "abbrev": "ops",
        "label": "General operations and maintenance skills that do not fit a narrower lane.",
    },
}

_AREA_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "training_tool",
        (
            "training",
            "sft",
            "fine-tune",
            "finetune",
            "model",
            "dataset",
            "hugging face",
            "huggingface",
            "colab",
            "kaggle",
            "benchmark",
            "eval",
            "evaluation",
            "lora",
            "corpus",
        ),
    ),
    (
        "recon_tool",
        (
            "research",
            "browser",
            "browsing",
            "search",
            "source",
            "verify",
            "verification",
            "email",
            "gmail",
            "proton",
            "sam.gov",
            "contract",
            "opportunity",
            "intelligence",
            "arxiv",
            "youtube",
            "notion",
            "web",
        ),
    ),
    (
        "governance_tool",
        (
            "governance",
            "safety",
            "security",
            "compliance",
            "policy",
            "authorize",
            "authorization",
            "gate",
            "audit",
            "risk",
            "permission",
            "secret",
            "credential",
            "privacy",
        ),
    ),
    (
        "agent_tool",
        (
            "agent",
            "swarm",
            "flock",
            "orchestrator",
            "handoff",
            "crosstalk",
            "codex",
            "claude",
            "copilot",
            "worker",
            "harness",
            "multi-agent",
            "ai-to-ai",
        ),
    ),
    (
        "cli_tool",
        (
            "cli",
            "terminal",
            "shell",
            "powershell",
            "command",
            "docker",
            "postgres",
            "mcp",
            "npm",
            "github actions",
            "local service",
            "emulator",
        ),
    ),
    (
        "commerce_tool",
        (
            "stripe",
            "shopify",
            "checkout",
            "revenue",
            "sales",
            "money",
            "product",
            "buyer",
            "fulfillment",
            "monetization",
        ),
    ),
    (
        "publishing_tool",
        (
            "article",
            "publish",
            "posting",
            "website",
            "story",
            "canon",
            "art",
            "image",
            "video",
            "youtube",
            "doc maker",
            "visual",
            "media",
            "manhwa",
        ),
    ),
    (
        "data_tool",
        (
            "storage",
            "backup",
            "offload",
            "document",
            "docs",
            "rag",
            "notes",
            "obsidian",
            "database",
            "files",
            "cloud",
            "drive",
            "dropbox",
        ),
    ),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _clean_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def _parse_frontmatter_simple(raw: str) -> dict[str, str]:
    """Extract ``name`` and ``description`` from small YAML-like frontmatter."""

    text = raw.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}
    out: dict[str, str] = {}
    body = lines[1:end]
    i = 0
    while i < len(body):
        line = body[i].strip()
        i += 1
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if key in ("name", "description"):
            if val in {">", ">-", "|", "|-"}:
                folded: list[str] = []
                while i < len(body):
                    next_line = body[i]
                    if re.match(r"^[A-Za-z0-9_-]+\s*:", next_line.strip()):
                        break
                    i += 1
                    stripped = next_line.strip()
                    if stripped and not stripped.startswith("#"):
                        folded.append(stripped)
                sep = "\n" if val.startswith("|") else " "
                out[key] = _clean_yaml_scalar(sep.join(folded))
            else:
                out[key] = _clean_yaml_scalar(val)
    return out


def _classify_function_area(skill_id: str, description: str, skill_path: str = "") -> str:
    haystack = f"{skill_id} {description}".lower()
    for area, keywords in _AREA_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return area
    return "ops_tool"


def _classify_invocation_kind(function_area: str, skill_id: str, description: str) -> str:
    haystack = f"{skill_id} {description}".lower()
    if function_area in {"recon_tool", "governance_tool"}:
        return "skill_lookup"
    if function_area in {"publishing_tool", "data_tool", "commerce_tool"}:
        return "skill_write"
    if function_area in {"agent_tool", "cli_tool", "training_tool"}:
        return "tool_call"
    if any(word in haystack for word in ("build", "execute", "run", "deploy", "automate", "orchestrate", "multi-step")):
        return "tool_call"
    if any(word in haystack for word in ("write", "draft", "create", "edit", "publish", "document")):
        return "skill_write"
    return "skill_lookup"


def _route_name_for_skill(skill_id: str, invocation_kind: str, area_abbrev: str) -> str:
    s = skill_id.strip().lower().replace("-", "_")
    s = _TOOL_NAME_RE.sub("_", s).strip("_") or "unnamed_skill"
    prefix = {
        "skill_lookup": "Skill_lookup",
        "skill_write": "Skill_write",
        "tool_call": "Tool_call",
    }.get(invocation_kind, "Skill_lookup")
    name = f"{prefix}_{area_abbrev}_{s}"
    return name[:96].rstrip("_")


def _sanitize_tool_name(skill_id: str, *, area_abbrev: str | None = None) -> str:
    s = skill_id.strip().lower().replace("-", "_")
    s = _TOOL_NAME_RE.sub("_", s).strip("_")
    if not s:
        s = "unnamed_skill"
    if area_abbrev:
        area = _TOOL_NAME_RE.sub("_", area_abbrev.strip().lower()).strip("_") or "ops"
        base = f"scbe_{area}_{s}"
    else:
        base = f"scbe_skill_{s}"
    if len(base) > 64:
        base = base[:64].rstrip("_")
    return base


def _dedupe_named_field(records: list[dict[str, Any]], field: str, base_field: str) -> None:
    seen: dict[str, int] = {}
    for record in records:
        base = str(record[field])
        count = seen.get(base, 0) + 1
        seen[base] = count
        if count == 1:
            continue
        suffix = f"_{count}"
        limit = 64 if field == "tool_name" else 96
        record[field] = f"{base[: limit - len(suffix)].rstrip('_')}{suffix}"
        record[base_field] = base


def _dedupe_tool_names(records: list[dict[str, Any]]) -> None:
    _dedupe_named_field(records, "tool_name", "tool_name_base")
    _dedupe_named_field(records, "route_name", "route_name_base")


def _extra_roots_from_env() -> list[Path]:
    raw = os.environ.get("SCBE_HARNESS_SKILL_ROOTS", "").strip()
    if not raw:
        return []
    parts = re.split(r"[;]+", raw) if os.sep == "\\" else re.split(r"[;:]+", raw)
    return [Path(p.strip()).expanduser() for p in parts if p.strip()]


def _iter_skill_dirs(root: Path) -> Iterable[tuple[Path, Path]]:
    """Yield ``(skill_dir, skill_md)`` for each skill under ``root``."""

    if not root.is_dir():
        return
    direct = root / "SKILL.md"
    if direct.is_file():
        yield root, direct
        return
    try:
        children = sorted(root.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return
    for child in children:
        if not child.is_dir():
            continue
        md = child / "SKILL.md"
        if md.is_file():
            yield child, md


def discover_skills(
    *,
    repo_root: Path | None = None,
    max_skills: int | None = None,
    max_description_len: int = 2400,
) -> list[dict[str, Any]]:
    """Return one record per ``SKILL.md`` found."""

    root = repo_root or _repo_root()
    cap = max_skills
    if cap is None:
        try:
            cap = int(os.environ.get("SCBE_HARNESS_SKILL_MAX", "400"))
        except ValueError:
            cap = 400
    cap = max(1, min(cap, 2000))

    roots: list[Path] = []
    for rel in _DEFAULT_RELATIVE_ROOTS:
        roots.append((root / rel).resolve())
    roots.extend(p.resolve() for p in _extra_roots_from_env())

    seen_paths: set[Path] = set()
    records: list[dict[str, Any]] = []

    for base in roots:
        for skill_dir, skill_md in _iter_skill_dirs(base):
            try:
                key = skill_md.resolve()
            except OSError:
                continue
            if key in seen_paths:
                continue
            seen_paths.add(key)
            try:
                raw = skill_md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm = _parse_frontmatter_simple(raw)
            skill_id = (fm.get("name") or skill_dir.name).strip()
            if not skill_id:
                skill_id = skill_dir.name
            desc = (fm.get("description") or f"SCBE skill at {skill_dir.name}").strip()
            if len(desc) > max_description_len:
                desc = desc[: max_description_len - 3] + "..."

            try:
                rel_skill = str(skill_md.resolve().relative_to(root.resolve()))
            except ValueError:
                rel_skill = str(skill_md.resolve())
            function_area = _classify_function_area(skill_id, desc, rel_skill)
            function_area_abbrev = FUNCTION_AREAS[function_area]["abbrev"]
            invocation_kind = _classify_invocation_kind(function_area, skill_id, desc)

            records.append(
                {
                    "skill_id": skill_id,
                    "function_area": function_area,
                    "function_area_abbrev": function_area_abbrev,
                    "function_area_label": FUNCTION_AREAS[function_area]["label"],
                    "invocation_kind": invocation_kind,
                    "route_name": _route_name_for_skill(skill_id, invocation_kind, function_area_abbrev),
                    "tool_name": _sanitize_tool_name(skill_id, area_abbrev=function_area_abbrev),
                    "description": desc,
                    "skill_path": rel_skill,
                    "skill_dir": str(skill_dir.resolve()),
                }
            )
            if len(records) >= cap:
                return records

    records.sort(key=lambda r: (r["skill_id"].lower(), r["skill_path"].lower()))
    _dedupe_tool_names(records)
    return records


def build_openai_style_skill_tools(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """OpenAI-compatible function tool list for model harnesses."""

    tools: list[dict[str, Any]] = []
    for s in skills:
        if s.get("invocation_kind") != "tool_call":
            continue
        desc = s["description"]
        path_hint = s["skill_path"]
        area = s.get("function_area", "ops_tool")
        full_desc = f"{desc}\n\n" f"function_area={area}\n" f"skill_id={s['skill_id']}\n" f"SKILL.md path={path_hint}"
        if len(full_desc) > 2800:
            full_desc = full_desc[:2797] + "..."
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": s["tool_name"],
                    "description": full_desc,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_context": {
                                "type": "string",
                                "description": "Optional user goal; do not put secrets here.",
                            },
                        },
                        "additionalProperties": False,
                    },
                },
            }
        )
    return tools


def build_harness_skill_tools_v1(
    *,
    repo_root: Path | None = None,
    max_skills: int | None = None,
) -> dict[str, Any]:
    """Payload embedded in ``build_agent_harness_manifest_v1``."""

    root = repo_root or _repo_root()
    skills = discover_skills(repo_root=root, max_skills=max_skills)
    roots_searched: list[str] = []
    for rel in _DEFAULT_RELATIVE_ROOTS:
        p = (root / rel).resolve()
        if p.is_dir():
            roots_searched.append(str(p))
    for p in _extra_roots_from_env():
        if p.is_dir():
            roots_searched.append(str(p.resolve()))
    area_counts: dict[str, int] = {area: 0 for area in FUNCTION_AREAS}
    skills_by_area: dict[str, list[str]] = {area: [] for area in FUNCTION_AREAS}
    invocation_counts: dict[str, int] = {"skill_lookup": 0, "skill_write": 0, "tool_call": 0}
    routes_by_invocation: dict[str, list[str]] = {"skill_lookup": [], "skill_write": [], "tool_call": []}
    for skill in skills:
        area = skill.get("function_area", "ops_tool")
        area_counts[area] = area_counts.get(area, 0) + 1
        skills_by_area.setdefault(area, []).append(skill["route_name"])
        invocation = skill.get("invocation_kind", "skill_lookup")
        invocation_counts[invocation] = invocation_counts.get(invocation, 0) + 1
        routes_by_invocation.setdefault(invocation, []).append(skill["route_name"])

    return {
        "schema_version": SCHEMA_VERSION,
        "discovered_count": len(skills),
        "search_roots": roots_searched,
        "function_areas": FUNCTION_AREAS,
        "function_area_counts": {k: v for k, v in area_counts.items() if v},
        "skills_by_area": {k: v for k, v in skills_by_area.items() if v},
        "invocation_kinds": {
            "skill_lookup": "Non-executing skill route for reading guidance, references, recon, and policy context.",
            "skill_write": "Skill route for drafting, editing, packaging, or repo-local authoring under write policy.",
            "tool_call": "Executable harness tool for multi-step automation, recursive build/test loops, "
            "remote compute, or live system actions.",
        },
        "invocation_counts": {k: v for k, v in invocation_counts.items() if v},
        "routes_by_invocation": {k: v for k, v in routes_by_invocation.items() if v},
        "skills": skills,
        "openai_style_tools": build_openai_style_skill_tools(skills),
        "invoke_contract": (
            "When a model selects a skill tool, the runner MUST load ``skill_path`` from disk, "
            "follow the SKILL body + references/, and stay inside permission_mode + tool_contracts."
        ),
    }
