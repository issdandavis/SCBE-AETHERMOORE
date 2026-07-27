"""Where a decision came from -- byte offsets in the ORIGINAL input, not just a score.

`scan()` answered "how bad" (score, d*, pd) and never "where". For a person holding a
flagged prompt that is the wrong half of the answer: `score=0.1961` is not actionable, and
`d*=2.5000` is only meaningful if you already know the pipeline. "line 1, col 1 --
`ignore all previous instructions`" is the thing you can act on.

The reason this was not already there: the intent screen never matches the input. It matches
CANONICALIZED CANDIDATES -- NFKC + homoglyph fold + zero-width strip + casefold + whitespace
collapse, and then leet, spaced-letter-join, rot13, Unicode-tag decode, and base64 decode on
top. Every one of those changes string length, so a match offset in a candidate does not
point anywhere in the text the user typed.

This module rebuilds each candidate WITH an index map back to the original:

    channel          maps back by
    ---------------  ----------------------------------------------------------
    text             per-character normalization, index recorded per emitted char
    leet             1:1 char translate over `text`, so it inherits that map
    rot13            length-preserving, inherits that map
    spaced-letters   deletion-only, aligned to `text` by two-pointer walk
    base64           no char map -- points at the ENCODED TOKEN's span instead
    unicode-tags     no char map -- points at the invisible tag-character run

The honesty rule throughout: a wrong location is worse than no location. The per-character
walk is checked against the authoritative whole-string `_normalize_for_intent`, and if they
disagree (possible for exotic combining sequences, where per-char NFKC is not whole-string
NFKC) the map is dropped and the finding reports its channel with no offsets rather than a
plausible-looking lie.

Nothing here changes a decision. `scan()` now takes its `intent_flags` from the families of
these findings, so the labels that drive d* and the locations shown to the user are the same
object rather than two implementations kept in step by hand. `_intent_screen.adversarial_intent`
stays as the reference implementation (the `scbe` CLI still calls it), and
`tests/test_locate_parity.py` asserts the two agree -- flags, order, and risk -- across the
whole attack corpus, so a divergence is a test failure and not a silent behaviour change.
"""

from __future__ import annotations

import codecs
import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ._intent_screen import (
    _HOMOGLYPH_TABLE,
    _INJECTION_FAMILIES,
    _LEET_TABLE,
    _SEM_FAMILIES,
    _ZERO_WIDTH_OR_CONTROL,
    _b64_tokens,
    _decode_tag_chars,
    _despace_runs,
    _normalize_for_intent,
)

_WS = re.compile(r"\s")

Finding = Dict[str, Any]


# ── offset-preserving normalization ───────────────────────────────────────────


def _walk_normalize(text: str) -> Tuple[List[str], List[int]]:
    """Per-character mirror of `_normalize_for_intent`, recording the source index.

    Returns (chars, src) with len(chars) == len(src); src[i] is the index in `text` of the
    character that produced chars[i]. A character can expand (NFKC 'ﬁ' -> 'fi', casefold
    'ß' -> 'ss'), in which case several output chars share one source index, or vanish
    (zero-width), in which case it contributes nothing.
    """
    chars: List[str] = []
    src: List[int] = []
    for i, ch in enumerate(text):
        piece = unicodedata.normalize("NFKC", ch).translate(_HOMOGLYPH_TABLE)
        piece = _ZERO_WIDTH_OR_CONTROL.sub("", piece).casefold()
        for c in piece:
            chars.append(c)
            src.append(i)

    # `re.sub(r"\s+", " ", s)` then `.strip()` -- collapse runs, keep the run's first index.
    out_c: List[str] = []
    out_s: List[int] = []
    prev_ws = False
    for c, i in zip(chars, src):
        if _WS.fullmatch(c):
            if not prev_ws:
                out_c.append(" ")
                out_s.append(i)
            prev_ws = True
        else:
            out_c.append(c)
            out_s.append(i)
            prev_ws = False
    start, end = 0, len(out_c)
    while start < end and out_c[start] == " ":
        start += 1
    while end > start and out_c[end - 1] == " ":
        end -= 1
    return out_c[start:end], out_s[start:end]


def _normalized_with_map(text: str) -> Tuple[str, Optional[List[int]]]:
    """The canonical base candidate, plus an index map back to `text` when it is trustworthy.

    `_normalize_for_intent` stays authoritative for the STRING -- the walk only supplies
    offsets, and only if it reproduces that string exactly.
    """
    base = _normalize_for_intent(text)
    chars, src = _walk_normalize(text)
    if "".join(chars) != base:
        return base, None
    return base, src


def _align_deletion(source: str, result: str) -> Optional[List[int]]:
    """Index map for a transformation that only DELETES characters (order preserved).

    Greedy leftmost is exact here: `result` is a subsequence of `source`, so walking both
    forward assigns every result char the earliest source char it can have come from.
    Returns None if `result` is not actually a subsequence.
    """
    out: List[int] = []
    j = 0
    for c in result:
        while j < len(source) and source[j] != c:
            j += 1
        if j >= len(source):
            return None
        out.append(j)
        j += 1
    return out


def _compose(outer: Optional[Sequence[int]], inner: Optional[Sequence[int]]) -> Optional[List[int]]:
    """inner maps candidate -> base; outer maps base -> original."""
    if outer is None or inner is None:
        return None
    if any(i >= len(outer) for i in inner):
        return None
    return [outer[i] for i in inner]


def _tag_span(text: str) -> Optional[Tuple[int, int]]:
    idx = [i for i, ch in enumerate(text) if 0xE0000 <= ord(ch) <= 0xE007F]
    return (idx[0], idx[-1] + 1) if idx else None


# ── channels ──────────────────────────────────────────────────────────────────


class _Channel:
    """One candidate string plus the best available route back to the original text."""

    __slots__ = ("name", "text", "cmap", "span")

    def __init__(
        self,
        name: str,
        text: str,
        cmap: Optional[Sequence[int]] = None,
        span: Optional[Tuple[int, int]] = None,
    ) -> None:
        self.name = name
        self.text = text
        # a map is only usable if it covers the candidate exactly
        self.cmap = list(cmap) if cmap is not None and len(cmap) == len(text) else None
        self.span = span

    def locate(self, match_span: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        i, j = match_span
        if self.cmap is not None and 0 <= i < len(self.cmap) and j > i:
            return self.cmap[i], self.cmap[min(j, len(self.cmap)) - 1] + 1
        # decoded channels cannot map character-for-character; the carrier's own span is
        # still a true location -- "inside this base64 token" is where the payload is.
        return self.span


def _channels(text: str) -> List[_Channel]:
    """Mirror of `_intent_scan_candidates`, carrying offsets.

    The order, the dedup-by-string, and the 20-candidate cap must match that function
    exactly: family labels are appended in first-hit order, so a reordering here would
    silently reorder `intent_flags`.
    """
    base, base_map = _normalized_with_map(text)
    out: List[_Channel] = [_Channel("text", base, base_map)]

    leet = base.translate(_LEET_TABLE)
    out.append(_Channel("leet", leet, base_map if len(leet) == len(base) else None))

    despaced = _despace_runs(base)
    if despaced != base:
        out.append(_Channel("spaced-letters", despaced, _compose(base_map, _align_deletion(base, despaced))))

    tag_payload = _decode_tag_chars(text)
    if tag_payload.strip():
        out.append(_Channel("unicode-tags", _normalize_for_intent(tag_payload), None, _tag_span(text)))

    try:
        out.append(_Channel("rot13", codecs.decode(base, "rot_13"), base_map))
    except Exception:
        pass

    for decoded, start, end in _b64_tokens(text):
        norm = _normalize_for_intent(decoded)
        out.append(_Channel("base64", norm, None, (start, end)))
        out.append(_Channel("base64", norm.translate(_LEET_TABLE), None, (start, end)))

    seen = set()
    unique: List[_Channel] = []
    for chan in out:
        if chan.text and chan.text not in seen:
            unique.append(chan)
            seen.add(chan.text)
    return unique[:20]


def candidate_strings(text: str) -> List[str]:
    """The candidate list, derived from the channels so the two cannot diverge."""
    return [c.text for c in _channels(text)]


# ── findings ──────────────────────────────────────────────────────────────────


def _line_col(text: str, offset: int) -> Tuple[int, int]:
    head = text[:offset]
    line = head.count("\n") + 1
    col = offset - (head.rfind("\n") + 1) + 1
    return line, col


def _excerpt(text: str, start: int, end: int, limit: int = 60) -> str:
    raw = text[start:end]
    if len(raw) > limit:
        raw = raw[: limit - 3] + "..."  # ASCII: excerpts are printed on cp1252 consoles
    return "".join(ch if ch.isprintable() or ch == " " else f"\\x{ord(ch):02x}" for ch in raw)


def _finding(
    text: str,
    family: str,
    channel: str,
    trigger: str,
    span: Optional[Tuple[int, int]],
    also: Optional[str] = None,
) -> Finding:
    f: Finding = {
        "family": family,
        "channel": channel,
        "trigger": trigger,
        "with": also,
        "start": None,
        "end": None,
        "line": None,
        "column": None,
        "excerpt": None,
    }
    if span is not None:
        start, end = span
        start = max(0, min(start, len(text)))
        end = max(start, min(end, len(text)))
        line, col = _line_col(text, start)
        f.update(start=start, end=end, line=line, column=col, excerpt=_excerpt(text, start, end))
    return f


def _semantic_hits(candidate: str) -> List[Tuple[str, str, Optional[str]]]:
    """`_semantic_intent` with the matched terms kept: (family, trigger, co-occurring term)."""
    hits: List[Tuple[str, str, Optional[str]]] = []
    for name, fam in _SEM_FAMILIES.items():
        standalone = next((s for s in fam["standalone"] if s in candidate), None)
        if standalone is not None:
            hits.append((name, standalone, None))
            continue
        actions, objects = fam["actions"], fam["objects"]
        if not actions or not objects:
            continue
        action = next((a for a in actions if a in candidate), None)
        obj = next((o for o in objects if o in candidate), None)
        if action is not None and obj is not None:
            hits.append((name, action, obj))
    return hits


def locate_intent(text: str) -> List[Finding]:
    """One finding per adversarial family, in the same first-hit order as `intent_flags`."""
    findings: List[Finding] = []
    seen: set = set()
    for chan in _channels(text):
        for name, rx in _INJECTION_FAMILIES.items():
            if name in seen:
                continue
            m = rx.search(chan.text)
            if m:
                findings.append(_finding(text, name, chan.name, m.group(0), chan.locate(m.span())))
                seen.add(name)
        for name, trigger, obj in _semantic_hits(chan.text):
            if name in seen:
                continue
            i = chan.text.find(trigger)
            span = chan.locate((i, i + len(trigger))) if i >= 0 else chan.span
            findings.append(_finding(text, name, chan.name, trigger, span, also=obj))
            seen.add(name)
    return findings


def locate_known_strings(text: str, patterns: Sequence[Tuple[float, str]], skip: Sequence[Finding]) -> List[Finding]:
    """Literal attack strings that drove phase deviation, minus anything a family already named.

    `.lower()` is length-preserving for all but a handful of codepoints ('İ' -> 'i̇'); when it
    is not, the offsets are dropped rather than reported off-by-n.
    """
    lowered = text.lower()
    mappable = len(lowered) == len(text)
    covered = [(f["start"], f["end"]) for f in skip if f["start"] is not None]
    out: List[Finding] = []
    for _penalty, pattern in patterns:
        i = lowered.find(pattern)
        if i < 0:
            continue
        span = (i, i + len(pattern)) if mappable else None
        if span and any(span[0] < ce and cs < span[1] for cs, ce in covered):
            continue  # a family finding already points here
        out.append(_finding(text, "known-attack-string", "text", pattern, span))
        if span:
            covered.append(span)
    return out


def locate_characters(text: str) -> List[Finding]:
    """Structural signals that DO have a position: control bytes and high-byte runs.

    Digit density and Shannon entropy also move d*, but they are properties of the whole
    input -- there is no honest single offset for them, so they are deliberately absent
    here rather than pinned to an arbitrary character.
    """
    raw = text.encode("utf-8")
    if not raw:
        return []
    out: List[Finding] = []
    ctrl = next((i for i, ch in enumerate(text) if ord(ch) < 32 and ch not in "\t\n\r"), None)
    if ctrl is not None:
        out.append(
            _finding(text, "control-character", "text", f"U+{ord(text[ctrl]):04X}", (ctrl, ctrl + 1)),
        )
    highbyte = sum(1 for b in raw if b > 127)
    if highbyte / len(raw) > 0.05:
        i = next((i for i, ch in enumerate(text) if ord(ch) > 127), None)
        if i is not None:
            out.append(_finding(text, "high-byte-run", "text", f"U+{ord(text[i]):04X}", (i, i + 1)))
    return out
