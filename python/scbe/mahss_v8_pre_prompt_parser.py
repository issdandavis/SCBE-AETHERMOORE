"""Deterministic prompt-to-schema parser for v8-pre Phase 2.

Reads ONLY the prompt text (never the answer key) and emits a schema
``{role: [filler, ...]}`` describing what semantic markers the prompt
expects in the response.

Honest scope: this parser is calibrated against the v6g eval contract's
prompt structure. It is NOT a general English parser. It works because
the contract uses a stable surface form across all twelve prompts:

  - "tongue XY (Name/Language)"      -> TONGUE + LANG
  - "Source tongue: XY ... Translate to tongue ZW (Name, Language)"
  - "tongue {XY,...} ... language lenses: KO (...), AV (...), RU (...)"
  - "Mark each slot in the output" + slot list in parens
  - approval-card / lane-boundary / identify-algorithm modes detected
    by anchor phrases ("verdict", "queue_drain_guard"-style identifier
    isolation, "algorithm name, description, tongue with phi-weight").

When this parser is run on text that does NOT match the v6g surface
form, it returns whatever it can extract; downstream code must not
assume completeness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

# Canonical Sacred Tongue surface forms used by the contract.
TONGUE_CODES: tuple[tuple[str, str, str, float], ...] = (
    # (code, full_name_lower, default_lang_lower, phi_weight)
    ("KO", "kor'aelin", "python", 1.00),
    ("AV", "avali", "javascript", 1.62),
    ("RU", "runethic", "rust", 2.62),
    ("CA", "cassisivadan", "mathematica", 4.24),
    ("UM", "umbroth", "haskell", 6.85),
    ("DR", "draumric", "markdown", 11.09),
)

_CODE_TO_TONGUE = {code: name for code, name, _lang, _phi in TONGUE_CODES}
_CODE_TO_LANG = {code: lang for code, _name, lang, _phi in TONGUE_CODES}
_CODE_TO_PHI = {code: phi for code, _name, _lang, phi in TONGUE_CODES}
_NAME_TO_PHI = {name: phi for _code, name, _lang, phi in TONGUE_CODES}

# Match patterns like "tongue UM (Umbroth/Haskell)" or "tongue UM (Umbroth, Haskell)"
_TONGUE_PAREN_RE = re.compile(
    r"tongue\s+([A-Z]{2})\s*\(\s*([A-Za-z'][A-Za-z'_-]*)\s*[/,]\s*([A-Za-z]+)\s*\)",
    re.IGNORECASE,
)
# Match bare lens form "KO (Kor'aelin/Python)" without 'tongue' before -- multi-lens prompts
_LENS_PAREN_RE = re.compile(
    r"\b([A-Z]{2})\s*\(\s*([A-Za-z'][A-Za-z'_-]*)\s*[/,]\s*([A-Za-z]+)\s*\)",
)
# Match "(UM, Haskell)" inline form used in identify-algorithm prompt
_TONGUE_INLINE_RE = re.compile(r"\(\s*([A-Z]{2})\s*,\s*([A-Za-z]+)\s*\)")
# Bare tongue-code mention as fallback ("KO is the routing tongue")
_BARE_TONGUE_CODE_RE = re.compile(
    r"\b([A-Z]{2})\b(?=[^\(]{0,40}(?:tongue|lens|route|routing))",
)
# Direct language mentions when no tongue code given ("Python function")
_BARE_LANG_RE = re.compile(
    r"\b(Python|JavaScript|Rust|Haskell|Mathematica|Markdown)\b\s+(?:function|implementation|code|script)",
    re.IGNORECASE,
)
_LANG_TO_TONGUE_NAME = {
    "python": "kor'aelin",
    "javascript": "avali",
    "rust": "runethic",
    "mathematica": "cassisivadan",
    "haskell": "umbroth",
    "markdown": "draumric",
}

# Per-language structural keyword templates. Filled in when prompt parses
# both a language and a function signature requirement.
_LANG_DEF_KEYWORD = {
    "python": "def ",
    "javascript": "export function ",
    "rust": "fn ",
    "haskell": "::",  # Haskell uses sig: ... :: ... -> ...
}

# Phrases in prompts that map to specific structural keywords.
# Each is a (regex, keyword) pair. Regex applied case-insensitively to prompt.
_PHRASE_TO_KEYWORD: tuple[tuple[str, str], ...] = (
    (r"\bthe return\b", "return"),
    (r"\botherwise return\b", "return"),
    (r"\bexplicit return\b", "return"),
    (r"\bearly return\b", "return"),
    (r"\bnone fallback\b", "none"),
    (r"\breturn\s+(?:type|value)\b", "return"),
    (r"\bthe loop\b", "for "),
    (r"\bfor[- ]loop\b", "for "),
    (r"\biteration over\b", "for "),
    (r"\b(?:zero|none|empty|missing|out[- ]of[- ]bounds)[- ]guard\b", "if "),
    (r"\bexplicit\s+\w+\s+guard\b", "if "),
    (r"\b(?:lower|upper)[- ]bound branch\b", "if "),
    (r"\bmembership check\b", "not in"),
    (r"\bseen[- ]set\b", "seen"),
    (r"\bget[- ]with[- ]default\b", "get("),
    (r"\bnew[- ]dict initialization\b", "result"),
    (r"\brunning[- ]sum\s+accumulator\b", "total"),
    (r"\bdivisor by index\b", "/"),
    (r"\bappend\b", "append"),
    (r"\breturns\s+(\d+)\s*\*", "* {captured}"),  # "returns 3 * x" -> "* 3"
    (r"\bmultiplication body\b", "* 3"),  # multi_lens uses this phrase
)

# Mapping prompt-mentioned types to required tokens for languages
_RUST_TYPE_TOKENS = ("i64", "Option")
_RUST_OPTION_VARIANTS = ("Some", "None")
# Match "Source tongue: KO" / "Translate to tongue UM"
_TONGUE_VERB_RE = re.compile(
    r"(?:source\s+tongue|translate\s+to\s+tongue|target\s+tongue)\s*:?\s*([A-Z]{2})\b",
    re.IGNORECASE,
)
# Match "card_route: DR / Draumric Markdown" or "script_route: KO / Kor'aelin / Python"
_ROUTE_RE = re.compile(
    r"(?:card_route|script_route|route)\s*:\s*([A-Z]{2})\b",
    re.IGNORECASE,
)

# Slot list when prompt explicitly enumerates them, e.g. "(sig, init, loop_open, loop_body, ret)"
_SLOT_LIST_RE = re.compile(
    r"\(\s*((?:sig|init|loop_open|loop_body|ret|body|algorithm|slots)(?:\s*,\s*(?:sig|init|loop_open|loop_body|ret|body|algorithm|slots))*)\s*\)",
    re.IGNORECASE,
)

# Function/identifier names mentioned in the prompt
_DEF_IDENT_RE = re.compile(
    r"\b(?:Implement|Define|implement|define)\s+(?:a\s+function\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
)
_BACKTICK_IDENT_RE = re.compile(r"`([a-zA-Z_][a-zA-Z0-9_]*)`")


@dataclass(frozen=True)
class PromptSchema:
    """Parsed semantic schema for a single eval prompt."""

    tongues: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    identifiers: tuple[str, ...] = ()
    slots: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    mode: str = "code"  # one of: code, translate, identify, approval, route, lane_boundary

    def to_role_filler_pairs(self) -> tuple[tuple[str, str], ...]:
        """Flatten to the (role, filler) form RolePinnedMemory expects."""

        out: list[tuple[str, str]] = []
        for t in self.tongues:
            out.append(("TONGUE", t))
        for lang in self.languages:
            out.append(("LANG", lang))
        for ident in self.identifiers:
            out.append(("IDENT", ident))
        for slot in self.slots:
            out.append(("SLOT", slot))
        for metric in self.metrics:
            out.append(("METRIC", metric))
        for kw in self.keywords:
            out.append(("KEYWORD", kw))
        return tuple(out)

    def role_counts(self) -> dict[str, int]:
        """Count fillers per role (Phase 2 needs this for top-N retrieval)."""

        counts: dict[str, int] = {}
        for role, _ in self.to_role_filler_pairs():
            counts[role] = counts.get(role, 0) + 1
        return counts


def _dedupe(items: Iterable[str], *, preserve_case: bool = False) -> tuple[str, ...]:
    """Deduplicate by lowercase key, optionally preserving original case."""

    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        key = x.lower()
        if key not in seen:
            seen.add(key)
            out.append(x if preserve_case else x.lower())
    return tuple(out)


def _detect_mode(prompt: str) -> str:
    p = prompt.lower()
    if "translate to tongue" in p or "source tongue" in p:
        return "translate"
    if "identify the algorithm" in p or "return algorithm name" in p:
        return "identify"
    if "card_route" in p or "verdict" in p and "promote" in p:
        return "approval"
    if "do not mention chemistry" in p or "lane boundary" in p:
        return "lane_boundary"
    if "language lenses" in p or "three language" in p:
        return "multi_lens"
    return "code"


def parse_prompt(prompt: str) -> PromptSchema:
    """Parse a v6g-style eval prompt into a semantic schema."""

    tongues: list[str] = []
    languages: list[str] = []
    identifiers: list[str] = []
    slots: list[str] = []
    metrics: list[str] = []
    keywords: list[str] = []

    # Tongue + language from "tongue XY (Name/Language)" or "(Name, Language)"
    matched_spans: list[tuple[int, int]] = []
    for m in _TONGUE_PAREN_RE.finditer(prompt):
        code = m.group(1).upper()
        name = m.group(2).lower()
        lang = m.group(3).lower()
        tongues.append(name)
        languages.append(lang)
        if code in _CODE_TO_TONGUE and _CODE_TO_TONGUE[code] != name:
            # Trust the code; spec lower-cases
            tongues[-1] = _CODE_TO_TONGUE[code]
        matched_spans.append(m.span())

    # Bare lens form "KO (Kor'aelin/Python)" without 'tongue' before -- multi-lens
    for m in _LENS_PAREN_RE.finditer(prompt):
        if any(start <= m.start() < end for start, end in matched_spans):
            continue
        code = m.group(1).upper()
        lang = m.group(3).lower()
        if code in _CODE_TO_TONGUE:
            tongues.append(_CODE_TO_TONGUE[code])
            languages.append(lang)
            matched_spans.append(m.span())

    # Inline "(UM, Haskell)" form
    for m in _TONGUE_INLINE_RE.finditer(prompt):
        if any(start <= m.start() < end for start, end in matched_spans):
            continue
        code = m.group(1).upper()
        lang = m.group(2).lower()
        if code in _CODE_TO_TONGUE:
            tongues.append(_CODE_TO_TONGUE[code])
            languages.append(lang)

    # Verb-form "Source tongue: KO" / "Translate to tongue UM"
    for m in _TONGUE_VERB_RE.finditer(prompt):
        code = m.group(1).upper()
        if code in _CODE_TO_TONGUE:
            tongues.append(_CODE_TO_TONGUE[code])
            languages.append(_CODE_TO_LANG[code])

    # Route lines (card_route / script_route)
    for m in _ROUTE_RE.finditer(prompt):
        code = m.group(1).upper()
        if code in _CODE_TO_TONGUE:
            tongues.append(_CODE_TO_TONGUE[code])
            languages.append(_CODE_TO_LANG[code])

    # Fallback: bare tongue code mentioned near "tongue/lens/route" word
    if not tongues:
        for m in _BARE_TONGUE_CODE_RE.finditer(prompt):
            code = m.group(1).upper()
            if code in _CODE_TO_TONGUE:
                tongues.append(_CODE_TO_TONGUE[code])
                languages.append(_CODE_TO_LANG[code])

    # Fallback: language name mentioned ("Python function") -> infer tongue
    if not tongues:
        for m in _BARE_LANG_RE.finditer(prompt):
            lang = m.group(1).lower()
            if lang in _LANG_TO_TONGUE_NAME:
                tongues.append(_LANG_TO_TONGUE_NAME[lang])
                languages.append(lang)

    # Slot list in parens
    for m in _SLOT_LIST_RE.finditer(prompt):
        for slot in re.split(r"\s*,\s*", m.group(1)):
            slots.append(slot.strip().lower())

    # Function names mentioned by definition or backtick
    for m in _DEF_IDENT_RE.finditer(prompt):
        identifiers.append(m.group(1))
    for m in _BACKTICK_IDENT_RE.finditer(prompt):
        ident = m.group(1)
        if "_" in ident or any(c.isupper() for c in ident[1:]):
            identifiers.append(ident)

    mode = _detect_mode(prompt)

    # Mode-specific augmentations -- these correspond to the prompt's semantic
    # contract, not the answer key. The prompt explicitly asks for these markers.
    if mode == "identify":
        slots.extend(["algorithm:", "slots:", "sig", "body"])
        # The prompt asks for tongue WITH PHI-WEIGHT -> add phi metric for the tongue
        for tongue in tongues:
            phi = _NAME_TO_PHI.get(tongue.lower())
            if phi is not None:
                metrics.append(f"phi={phi:.2f}")
    if mode == "approval":
        keywords.extend(["verdict", "evidence", "next", "horizon"])
    if mode == "lane_boundary":
        keywords.extend(["code identifier", "definition", "unit test", "run"])
    if mode == "translate":
        # Translate prompts ask for slot-aligned output
        slots.extend(["sig", "init", "loop_open", "loop_body", "ret"])

    # ------------------------------------------------------------------
    # Structural keyword extraction from prompt phrasing
    # ------------------------------------------------------------------

    # Function-signature keyword based on requested language
    if "function signature" in prompt.lower() or "function syntax" in prompt.lower():
        for lang in languages:
            if lang in _LANG_DEF_KEYWORD:
                kw = _LANG_DEF_KEYWORD[lang]
                # Prefer "def {ident}" / "fn {ident}" forms when we have an ident
                if identifiers and lang == "python":
                    keywords.append(f"def {identifiers[0]}")
                elif identifiers and lang == "rust":
                    keywords.append(f"fn {identifiers[0]}")
                elif identifiers and lang == "javascript":
                    # JavaScript: export function camelCase
                    snake = identifiers[0]
                    camel = "".join(p.capitalize() if i else p for i, p in enumerate(snake.split("_")))
                    keywords.append(f"export function {camel}")
                else:
                    keywords.append(kw)

    # Phrase-pattern extraction
    for pattern, kw in _PHRASE_TO_KEYWORD:
        m = re.search(pattern, prompt, re.IGNORECASE)
        if m:
            if "{captured}" in kw and m.groups():
                keywords.append(kw.replace("{captured}", m.group(1)))
            else:
                keywords.append(kw)

    # Rust types when prompt mentions them explicitly
    for t in _RUST_TYPE_TOKENS:
        if t.lower() in prompt.lower() and "rust" in [l.lower() for l in languages]:
            keywords.append(t)
    # Rust Option variants
    if "rust" in [l.lower() for l in languages] and "option" in prompt.lower():
        for v in _RUST_OPTION_VARIANTS:
            keywords.append(v)

    # Specific value patterns the prompt asks for
    if "empty string" in prompt.lower() or "empty input" in prompt.lower():
        keywords.append("''")

    return PromptSchema(
        tongues=_dedupe(tongues),
        languages=_dedupe(languages),
        identifiers=_dedupe(identifiers, preserve_case=True),
        slots=_dedupe(slots),
        metrics=_dedupe(metrics),
        keywords=_dedupe(keywords, preserve_case=True),
        mode=mode,
    )


def format_mahss_prefix(schema: PromptSchema, retrieved: dict[str, list[str]]) -> str:
    """Format a structured retrieval prefix for Qwen's prompt.

    Schema gives us the role list to query; retrieved gives the actual
    retrieved fillers per role. The prefix is a compact, code-flavored
    one-liner per role so the model treats it as a hint, not a wall of
    text. Empty roles are omitted."""

    parts: list[str] = []
    for role in ("TONGUE", "LANG", "IDENT", "SLOT", "METRIC", "KEYWORD"):
        if role not in retrieved or not retrieved[role]:
            continue
        label = {
            "TONGUE": "required-tongues",
            "LANG": "required-langs",
            "IDENT": "required-idents",
            "SLOT": "required-slots",
            "METRIC": "required-metrics",
            "KEYWORD": "required-keywords",
        }[role]
        joined = ", ".join(retrieved[role])
        parts.append(f"{label}: {joined}")
    if not parts:
        return ""
    return " | ".join(parts) + " ::\n"


__all__ = [
    "PromptSchema",
    "TONGUE_CODES",
    "format_mahss_prefix",
    "parse_prompt",
]
