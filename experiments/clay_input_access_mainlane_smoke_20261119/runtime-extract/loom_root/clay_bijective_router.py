"""Verified, bijective command routing for Clay's bounded tool-call grammar.

This router uses training requests as a retrieval index, then reconstructs
request-contained slots (numbers, file names, patterns, URLs) before sealing a
typed ``ToolCall``.  It never loads held-out data when serving a request.

The bijection is intentionally at the command layer: one canonical command
line maps to exactly one ``ToolCall(tool, payload)`` and formatting that call
returns exactly that canonical command line.  Validation also proves that the
named Clay handler exists before a route can be considered executable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


SCHEMA = "clay.bijective-router.v1"
HERE = Path(__file__).resolve().parent
DEFAULT_TRAIN = HERE / "clay_tool_data.jsonl"
DEFAULT_HOLDOUT = HERE / "clay_tool_holdout.jsonl"
HANDLERS = {
    "sieve": "clay_sieve.py",
    "web": "clay_web.py",
    "remember": "clay_remember.py",
    "read": "clay_read.py",
    "tools": "clay_tools.py",
    "solve": "clay_cli.py",
    "accuplacer": "clay_accuplacer.py",
    "email": "clay_email.py",
    "localapi": "clay_localapi.py",
    "ferro": "ferro_field.py",
}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
MCP_ARGUMENT_RULES: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "mcp__github__get_me": (frozenset(), frozenset()),
    "mcp__github__search_code": (
        frozenset({"query"}),
        frozenset({"query", "order", "page", "perPage", "sort"}),
    ),
    "mcp__github__get_file_contents": (
        frozenset({"owner", "repo"}),
        frozenset({"owner", "repo", "path", "ref", "sha"}),
    ),
    "mcp__openaiDeveloperDocs__search_openai_docs": (
        frozenset({"query"}),
        frozenset({"query", "cursor", "limit"}),
    ),
    "mcp__openaiDeveloperDocs__fetch_openai_doc": (
        frozenset({"url"}),
        frozenset({"url", "anchor"}),
    ),
    "mcp__cloudflare__docs": (
        frozenset({"query"}),
        frozenset({"query"}),
    ),
    "mcp__codex_apps__google_drive_search": (
        frozenset({"query"}),
        frozenset(
            {
                "query",
                "topn",
                "special_filter_query_str",
                "best_effort_fetch",
                "fetch_ttl",
                "require_viewed_by_user",
            }
        ),
    ),
    "mcp__codex_apps__hugging_face_mcp_model_search": (
        frozenset(),
        frozenset({"author", "library", "limit", "query", "sort", "task"}),
    ),
    "mcp__codex_apps__hugging_face_mcp_dataset_search": (
        frozenset(),
        frozenset({"author", "limit", "query", "sort", "tags"}),
    ),
}
MCP_TOOL_ALIASES: dict[str, tuple[str, dict[str, str]]] = {
    "@1": ("mcp__github__get_me", {}),
    "@2": (
        "mcp__github__search_code",
        {"q": "query", "n": "perPage"},
    ),
    "@3": (
        "mcp__github__get_file_contents",
        {"o": "owner", "r": "repo", "p": "path"},
    ),
    "@4": (
        "mcp__openaiDeveloperDocs__search_openai_docs",
        {"q": "query", "n": "limit"},
    ),
    "@5": (
        "mcp__openaiDeveloperDocs__fetch_openai_doc",
        {"u": "url", "d": "document_alias"},
    ),
    "@6": ("mcp__cloudflare__docs", {"q": "query"}),
    "@7": (
        "mcp__codex_apps__google_drive_search",
        {"q": "query", "n": "topn"},
    ),
    "@8": (
        "mcp__codex_apps__hugging_face_mcp_model_search",
        {"q": "query", "n": "limit", "t": "task"},
    ),
    "@9": (
        "mcp__codex_apps__hugging_face_mcp_dataset_search",
        {"q": "query", "n": "limit"},
    ),
}
OPENAI_DOCUMENT_ALIASES = {
    "tools": "https://developers.openai.com/api/docs/guides/tools",
    "function-calling": (
        "https://developers.openai.com/api/docs/guides/function-calling"
    ),
    "remote-mcp": (
        "https://developers.openai.com/api/docs/guides/tools-remote-mcp"
    ),
}
SENSITIVE_ARGUMENT_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "access_token",
    "password",
    "private_key",
    "secret",
    "token",
}
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?:bearer\s+[A-Za-z0-9._~-]+|"
    r"(?:sk|ghp|github_pat|aj_tcc_svc)_[A-Za-z0-9_-]{12,})",
    re.IGNORECASE,
)
SLASH_NAME_PATTERN = re.compile(r"[a-z][a-z0-9-]{0,31}")
RESERVED_SLASH_NAMES = {
    "agent",
    "agents",
    "auto",
    "command",
    "commands",
    "exit",
    "file",
    "help",
    "loop",
    "model",
    "new",
    "status",
    "thinking",
    "workflow",
}


@dataclass(frozen=True)
class ToolCall:
    """A command whose identity is the pair of a handler and canonical payload."""

    tool: str
    payload: str


@dataclass(frozen=True)
class RouteResult:
    line: str
    retrieval_score: float
    reconstructed: bool
    verification: dict[str, Any]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_rows(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            request = record.get("request")
            target = record.get("target")
            if not isinstance(request, str) or not isinstance(target, str):
                raise ValueError(f"invalid route record at {path}:{line_number}")
            rows.append((request, target))
    if not rows:
        raise ValueError(f"no route records: {path}")
    return rows


def parse_tool_call(line: str) -> ToolCall:
    """Parse the only command representation accepted by the router."""
    text = line.strip()
    if " ::" not in text:
        raise ValueError("tool call must contain a ' ::' separator")
    tool, payload = text.split(" ::", maxsplit=1)
    tool = tool.strip()
    payload = payload.lstrip()
    if tool not in HANDLERS:
        raise ValueError(f"unknown tool: {tool!r}")
    if not tool or any(char.isspace() for char in tool):
        raise ValueError("tool name must be a single token")
    if "\x00" in payload or "\n" in payload or "\r" in payload:
        raise ValueError("payload contains a forbidden control character")
    return ToolCall(tool=tool, payload=payload)


def format_tool_call(call: ToolCall) -> str:
    """Canonical inverse of :func:`parse_tool_call`."""
    if call.tool not in HANDLERS:
        raise ValueError(f"unknown tool: {call.tool!r}")
    payload = call.payload.strip()
    if "\x00" in payload or "\n" in payload or "\r" in payload:
        raise ValueError("payload contains a forbidden control character")
    return f"{call.tool} ::" if not payload else f"{call.tool} :: {payload}"


def is_safe_relative_name(value: str, suffixes: tuple[str, ...] | None = None) -> bool:
    if not value or value.startswith(("/", "\\")) or ".." in Path(value).parts:
        return False
    if suffixes and not value.lower().endswith(suffixes):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+", value))


def _contains_sensitive_argument(value: Any, *, key: str = "") -> bool:
    if key.lower() in SENSITIVE_ARGUMENT_KEYS:
        return True
    if isinstance(value, dict):
        return any(
            _contains_sensitive_argument(child, key=str(child_key))
            for child_key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_argument(child) for child in value)
    return isinstance(value, str) and bool(SENSITIVE_VALUE_PATTERN.search(value))


def expand_mcp_payload(payload: str) -> dict[str, Any]:
    first_token = payload.partition(" ")[0]
    compact = payload.startswith("mcp ") or first_token in MCP_TOOL_ALIASES
    body = (
        payload.removeprefix("mcp ")
        if payload.startswith("mcp ")
        else payload.removeprefix("mcp-call ")
        if payload.startswith("mcp-call ")
        else payload
    )
    tool_name, separator, arguments_text = body.partition(" ")
    if not separator:
        raise ValueError("MCP envelope needs a tool and compact JSON arguments")
    if len(arguments_text) > 768:
        raise ValueError("MCP arguments exceed the bounded envelope")
    try:
        arguments = json.loads(arguments_text)
    except json.JSONDecodeError as error:
        raise ValueError("MCP arguments must be one compact JSON object") from error
    if not isinstance(arguments, dict):
        raise ValueError("MCP arguments must be a JSON object")
    canonical = json.dumps(
        arguments,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    if arguments_text != canonical:
        raise ValueError("MCP arguments are not in canonical compact JSON form")

    if compact:
        if tool_name not in MCP_TOOL_ALIASES:
            raise ValueError("MCP opcode is not registered")
        expanded_name, key_map = MCP_TOOL_ALIASES[tool_name]
        unknown = set(arguments) - set(key_map)
        if unknown:
            raise ValueError(f"unknown compact MCP arguments: {sorted(unknown)}")
        expanded_arguments = {
            key_map[key]: value for key, value in arguments.items()
        }
        if "document_alias" in expanded_arguments:
            document = expanded_arguments.pop("document_alias")
            if document not in OPENAI_DOCUMENT_ALIASES:
                raise ValueError("unknown OpenAI document opcode")
            expanded_arguments["url"] = OPENAI_DOCUMENT_ALIASES[document]
        tool_name = expanded_name
        arguments = expanded_arguments

    if tool_name not in MCP_ARGUMENT_RULES:
        raise ValueError("MCP tool is not a registered read-only route")
    required, allowed = MCP_ARGUMENT_RULES[tool_name]
    keys = frozenset(arguments)
    if not required.issubset(keys) or not keys.issubset(allowed):
        raise ValueError("MCP arguments do not match the registered tool schema")
    if _contains_sensitive_argument(arguments):
        raise ValueError("MCP arguments contain credential-shaped data")
    return {"tool": tool_name, "arguments": arguments}


def compact_mcp_payload(payload: str) -> str:
    expanded = expand_mcp_payload(payload)
    actual_tool = expanded["tool"]
    alias = next(
        (
            name
            for name, (registered_tool, _keys) in MCP_TOOL_ALIASES.items()
            if registered_tool == actual_tool
        ),
        None,
    )
    if alias is None:
        raise ValueError(f"MCP tool has no compact opcode: {actual_tool}")
    key_map = MCP_TOOL_ALIASES[alias][1]
    reverse_keys = {full: short for short, full in key_map.items()}
    arguments = dict(expanded["arguments"])
    if alias == "@5":
        url = arguments.get("url")
        document_alias = next(
            (
                name
                for name, registered_url in OPENAI_DOCUMENT_ALIASES.items()
                if registered_url == url
            ),
            None,
        )
        if document_alias is not None:
            arguments = {"document_alias": document_alias}
    compact_arguments = {}
    for key, value in arguments.items():
        if key not in reverse_keys:
            raise ValueError(f"MCP argument has no compact opcode: {key}")
        compact_arguments[reverse_keys[key]] = value
    arguments_text = json.dumps(
        compact_arguments,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    result = f"{alias} {arguments_text}"
    if expand_mcp_payload(result) != expanded:
        raise ValueError("compact MCP opcode failed its expansion seal")
    return result


def _validate_mcp_payload(payload: str) -> tuple[bool, str]:
    try:
        expand_mcp_payload(payload)
    except ValueError as error:
        return False, str(error)
    return True, ""


def expand_slash_payload(payload: str) -> str:
    if payload in {"sc?", "@A"}:
        return "/commands"
    if payload.startswith(("sc> ", "@B ")):
        return (
            payload.removeprefix("sc> ")
            if payload.startswith("sc> ")
            else payload.removeprefix("@B ")
        )
    if payload.startswith(("sc+ ", "@C ")):
        body = (
            payload.removeprefix("sc+ ")
            if payload.startswith("sc+ ")
            else payload.removeprefix("@C ")
        )
        name, separator, template = body.partition(" :: ")
        if not separator:
            raise ValueError("sc+ needs /NAME :: TEMPLATE")
        return f"/command add {name.removeprefix('/')} {template}"
    if payload.startswith(("sc- ", "@D ")):
        name = (
            payload.removeprefix("sc- ")
            if payload.startswith("sc- ")
            else payload.removeprefix("@D ")
        ).removeprefix("/")
        return f"/command remove {name}"
    if payload == "slash-list":
        return "/commands"
    if payload.startswith("slash-run "):
        return payload.removeprefix("slash-run ")
    if payload.startswith("slash-create "):
        body = payload.removeprefix("slash-create ")
        name, separator, template = body.partition(" :: ")
        if not separator:
            raise ValueError("slash-create needs /NAME :: TEMPLATE")
        return f"/command add {name.removeprefix('/')} {template}"
    if payload.startswith("slash-remove "):
        name = payload.removeprefix("slash-remove ").removeprefix("/")
        return f"/command remove {name}"
    raise ValueError("unknown slash envelope")


def compact_slash_payload(payload: str) -> str:
    expanded = expand_slash_payload(payload)
    if expanded == "/commands":
        return "@A"
    if expanded.startswith("/command add "):
        body = expanded.removeprefix("/command add ")
        name, separator, template = body.partition(" ")
        if not separator:
            raise ValueError("expanded slash create is missing a template")
        return f"@C /{name} :: {template}"
    if expanded.startswith("/command remove "):
        name = expanded.removeprefix("/command remove ")
        return f"@D /{name}"
    return f"@B {expanded}"


def compact_tools_payload(payload: str) -> str:
    if payload.startswith(("mcp-call ", "mcp ", "@1 ", "@2 ", "@3 ", "@4 ", "@5 ", "@6 ", "@7 ", "@8 ", "@9 ")):
        return compact_mcp_payload(payload)
    if payload.startswith(("slash-", "sc", "@A", "@B ", "@C ", "@D ")):
        return compact_slash_payload(payload)
    raise ValueError("tools payload has no compact opcode")


def _validate_slash_payload(payload: str) -> tuple[bool, str]:
    if payload in {"slash-list", "sc?", "@A"}:
        return True, ""
    if payload.startswith(("slash-run ", "sc> ", "@B ")):
        command = (
            payload.removeprefix("slash-run ")
            if payload.startswith("slash-run ")
            else payload.removeprefix("sc> ")
            if payload.startswith("sc> ")
            else payload.removeprefix("@B ")
        )
        name, _, arguments = command.partition(" ")
        if not name.startswith("/") or not SLASH_NAME_PATTERN.fullmatch(name[1:]):
            return False, "slash-run requires /NAME and optional bounded arguments"
        if len(arguments) > 256 or SENSITIVE_VALUE_PATTERN.search(arguments):
            return False, "slash-run arguments are unsafe or too long"
        return True, ""
    if payload.startswith(("slash-create ", "sc+ ", "@C ")):
        body = (
            payload.removeprefix("slash-create ")
            if payload.startswith("slash-create ")
            else payload.removeprefix("sc+ ")
            if payload.startswith("sc+ ")
            else payload.removeprefix("@C ")
        )
        name, separator, template = body.partition(" :: ")
        normalized = name.removeprefix("/")
        if (
            not separator
            or not SLASH_NAME_PATTERN.fullmatch(normalized)
            or normalized in RESERVED_SLASH_NAMES
        ):
            return False, "slash-create requires a non-reserved /NAME"
        if (
            "{args}" not in template
            or not 1 <= len(template) <= 256
            or SENSITIVE_VALUE_PATTERN.search(template)
        ):
            return False, "slash-create needs a bounded {args} template"
        return True, ""
    if payload.startswith(("slash-remove ", "sc- ", "@D ")):
        name = (
            payload.removeprefix("slash-remove ")
            if payload.startswith("slash-remove ")
            else payload.removeprefix("sc- ")
            if payload.startswith("sc- ")
            else payload.removeprefix("@D ")
        ).removeprefix("/")
        return (
            bool(
                SLASH_NAME_PATTERN.fullmatch(name)
                and name not in RESERVED_SLASH_NAMES
            ),
            "slash-remove requires a non-reserved /NAME",
        )
    return False, "invalid tools payload"


def payload_is_valid(call: ToolCall) -> tuple[bool, str]:
    """Independently validate a parsed call before it can be dispatched."""
    payload = call.payload
    if call.tool == "tools":
        if payload == "":
            return True, ""
        if payload.startswith(("mcp-call ", "mcp ", "@1 ", "@2 ", "@3 ", "@4 ", "@5 ", "@6 ", "@7 ", "@8 ", "@9 ")):
            return _validate_mcp_payload(payload)
        if payload.startswith(("slash-", "sc", "@A", "@B ", "@C ", "@D ")):
            return _validate_slash_payload(payload)
        return False, "tools accepts inventory, registered MCP, or slash envelopes"
    if call.tool == "sieve":
        return (payload.isdecimal() and int(payload) >= 2, "sieve needs an integer >= 2")
    if call.tool == "web":
        if payload.startswith("fetch "):
            parsed = urlparse(payload.removeprefix("fetch "))
            return (parsed.scheme in {"http", "https"} and bool(parsed.netloc), "invalid fetch URL")
        return (bool(payload), "web search query is empty")
    if call.tool == "remember":
        return (
            payload == "resume" or bool(re.fullmatch(r"(?:note|recall) .+", payload)),
            "remember requires resume, note TEXT, or recall TEXT",
        )
    if call.tool == "read":
        match = re.fullmatch(r"(?P<file>[A-Za-z0-9_.-]+\.(?:md|py))(?: --find (?P<pattern>.+))?", payload)
        return (bool(match), "read requires a local .md/.py filename and optional --find pattern")
    if call.tool == "solve":
        return (is_safe_relative_name(payload, (".json", ".jsonl")), "solve needs a local JSON task file")
    if call.tool == "accuplacer":
        return (
            payload in {"start", "status", "plan"}
            or bool(re.fullmatch(r"question (?:reading|writing|arithmetic|qas|advanced)", payload)),
            "invalid accuplacer action",
        )
    if call.tool == "email":
        allowed = (
            r"(?:mailbox-status|training-status|style-hints)",
            r"scrub --file [A-Za-z0-9_.-]+",
            r"triage [A-Za-z0-9_.-]+",
            r"prepare [A-Za-z0-9_.-]+ --out [A-Za-z0-9_.-]+",
            r"cleanup-plan [A-Za-z0-9_.-]+ --out [A-Za-z0-9_.-]+",
        )
        return (any(re.fullmatch(pattern, payload) for pattern in allowed), "invalid email action")
    if call.tool == "localapi":
        if payload in {"list", "ollama tags", "ollama ps", "ollama version", "aetherdesk status", "aetherdesk health", "aetherdesk runs"}:
            return True, ""
        if re.fullmatch(r"ollama generate [A-Za-z0-9_.:-]+ :: .+", payload):
            return True, ""
        if payload.startswith("get "):
            parsed = urlparse(payload.removeprefix("get "))
            return (
                parsed.scheme in {"http", "https"} and parsed.hostname in LOCAL_HOSTS,
                "localapi get must target a loopback host",
            )
        return False, "invalid localapi action"
    if call.tool == "ferro":
        return (
            payload in {
                "ring",
                "circle",
                "spike",
                "spike center",
                "center",
                "two spikes",
                "twin",
                "line",
                "bar",
                "spell AI",
                "spell HK",
            },
            "invalid governed magnet-grid pattern",
        )
    return False, "unhandled tool"


def verify_tool_call(line: str) -> dict[str, Any]:
    """Seal syntax, grammar, handler presence, and parse/format bijection."""
    try:
        call = parse_tool_call(line)
        canonical = format_tool_call(call)
        recovered = parse_tool_call(canonical)
        valid_payload, reason = payload_is_valid(call)
        handler = HERE / HANDLERS[call.tool]
        result = {
            "valid": valid_payload and handler.is_file() and recovered == call,
            "call": asdict(call),
            "canonical": canonical,
            "round_trip": recovered == call,
            "payload_valid": valid_payload,
            "handler": str(handler),
            "handler_exists": handler.is_file(),
            "reason": "" if valid_payload else reason,
        }
    except ValueError as error:
        result = {
            "valid": False,
            "round_trip": False,
            "payload_valid": False,
            "handler_exists": False,
            "reason": str(error),
        }
    return result


def trim_request(text: str) -> str:
    return re.sub(r"(?:\s+please)?[?!.]*$", "", text.strip(), flags=re.IGNORECASE)


def build_unambiguous_map(values: list[str]) -> dict[str, str]:
    grouped: dict[str, set[str]] = {}
    for value in values:
        grouped.setdefault(value.lower(), set()).add(value)
    return {key: next(iter(group)) for key, group in grouped.items() if len(group) == 1}


class CandidateIndex:
    """Training-only retrieval memory plus request-slot reconstruction."""

    def __init__(self, rows: list[tuple[str, str]]) -> None:
        self.rows = rows
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), lowercase=True, sublinear_tf=True
        )
        self.matrix = self.vectorizer.fit_transform([request for request, _ in rows])
        web_values: list[str] = []
        web_fetch_values: list[str] = []
        read_patterns: list[str] = []
        for _request, target in rows:
            call = parse_tool_call(target)
            if call.tool == "web":
                if call.payload.startswith("fetch "):
                    web_fetch_values.append(call.payload.removeprefix("fetch "))
                else:
                    web_values.append(call.payload)
            if call.tool == "read" and " --find " in call.payload:
                read_patterns.append(call.payload.split(" --find ", maxsplit=1)[1])
        self.web_canonical = build_unambiguous_map(web_values)
        self.web_fetch_canonical = build_unambiguous_map(web_fetch_values)
        self.read_pattern_canonical = build_unambiguous_map(read_patterns)

    def propose(self, request: str) -> tuple[str, float]:
        query = self.vectorizer.transform([request])
        scores = linear_kernel(query, self.matrix)[0]
        index = int(scores.argmax())
        return self.rows[index][1], float(scores[index])

    def reconstruct(self, request: str, proposal: str) -> tuple[str, bool]:
        call = parse_tool_call(proposal)
        cleaned = trim_request(request)
        if call.tool == "sieve":
            numbers = re.findall(r"\b\d+\b", cleaned)
            if numbers:
                return format_tool_call(ToolCall("sieve", numbers[-1])), True
        if call.tool == "read":
            match = re.match(r"(?i)^scan\s+(?P<file>\S+)\s+for\s+(?P<pattern>.+)$", cleaned)
            if not match:
                match = re.match(r"(?i)^find\s+(?P<pattern>.+)\s+in\s+(?P<file>\S+)$", cleaned)
            if match:
                pattern = match.group("pattern").strip()
                pattern = self.read_pattern_canonical.get(pattern.lower(), pattern)
                payload = f"{match.group('file')} --find {pattern}"
                return format_tool_call(ToolCall("read", payload)), True
        if call.tool == "web":
            fetch = re.match(r"(?i)^(?:read the page|open|fetch)\s+(?P<url>https?://\S+)$", cleaned)
            if fetch:
                url = fetch.group("url")
                url = self.web_fetch_canonical.get(url.lower(), url)
                return format_tool_call(ToolCall("web", f"fetch {url}")), True
            query = re.match(
                r"(?i)^(?:who was|search for|look up|tell me about|find information on|find out about|research)\s+(?P<query>.+)$",
                cleaned,
            )
            if query:
                value = query.group("query").strip()
                value = self.web_canonical.get(value.lower(), value)
                return format_tool_call(ToolCall("web", value)), True
        if call.tool == "ferro":
            lowered = cleaned.lower()
            if re.search(r"\b(?:spell|glyphs?|render)\b", lowered):
                if re.search(r"\bai\b", lowered):
                    return format_tool_call(ToolCall("ferro", "spell AI")), True
                if re.search(r"\bhk\b", lowered):
                    return format_tool_call(ToolCall("ferro", "spell HK")), True
            if re.search(r"\b(?:two|twin)\b", lowered) and re.search(
                r"\bspikes?\b", lowered
            ):
                return format_tool_call(ToolCall("ferro", "two spikes")), True
            if re.search(r"\b(?:center|one)\b", lowered) and re.search(
                r"\b(?:spike|magnet)\b", lowered
            ):
                return format_tool_call(ToolCall("ferro", "spike center")), True
            if re.search(r"\b(?:ring|circle)\b", lowered):
                return format_tool_call(ToolCall("ferro", "ring")), True
            if re.search(r"\b(?:line|bar)\b", lowered):
                return format_tool_call(ToolCall("ferro", "line")), True
        return format_tool_call(call), False

    def route(self, request: str) -> RouteResult:
        proposal, score = self.propose(request)
        line, reconstructed = self.reconstruct(request, proposal)
        verification = verify_tool_call(line)
        if not verification["valid"]:
            raise ValueError(f"unsealed route: {verification}")
        return RouteResult(line=line, retrieval_score=score, reconstructed=reconstructed, verification=verification)


def evaluate(train_path: Path, holdout_path: Path) -> dict[str, Any]:
    """Evaluate without feeding held-out rows into the serving index."""
    train = load_rows(train_path)
    holdout = load_rows(holdout_path)
    index = CandidateIndex(train)
    exact = 0
    verified = 0
    tool_exact = 0
    for request, target in holdout:
        result = index.route(request)
        exact += result.line == format_tool_call(parse_tool_call(target))
        verified += result.verification["valid"]
        tool_exact += parse_tool_call(result.line).tool == parse_tool_call(target).tool
    return {
        "schema": SCHEMA,
        "train_records": len(train),
        "holdout_records": len(holdout),
        "tool_accuracy": tool_exact / len(holdout),
        "exact_accuracy": exact / len(holdout),
        "verified_accuracy": verified / len(holdout),
        "all_exact": exact == len(holdout),
        "all_verified": verified == len(holdout),
        "train_sha256": sha256_file(train_path),
        "holdout_sha256": sha256_file(holdout_path),
        "router_sha256": sha256_file(Path(__file__)),
    }


def write_evaluation_receipt(result: dict[str, Any], output: Path) -> None:
    receipt = {
        **result,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "claim": "bounded synthetic tool-call grammar only; not a general natural-language guarantee",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", nargs="?", help="Request to route using the training-only index.")
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--output", type=Path, help="Optional evaluation receipt path.")
    args = parser.parse_args()
    if args.evaluate:
        result = evaluate(args.train, args.holdout)
        if args.output:
            write_evaluation_receipt(result, args.output)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["all_exact"] and result["all_verified"] else 2
    if not args.request:
        parser.error("provide a request or use --evaluate")
    result = CandidateIndex(load_rows(args.train)).route(args.request)
    print(json.dumps({"line": result.line, **asdict(result)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
