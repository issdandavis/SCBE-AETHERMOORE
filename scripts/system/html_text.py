#!/usr/bin/env python3
"""HTML-to-text helpers for script-safe extraction."""

from __future__ import annotations

import re
from html.parser import HTMLParser


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag.lower() in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._chunks.append(data)

    def get_text(self) -> str:
        return " ".join(self._chunks)


def html_to_text(raw_html: str, *, lower: bool = False, max_chars: int | None = None) -> str:
    parser = _HTMLTextParser()
    parser.feed(raw_html or "")
    text = re.sub(r"\s+", " ", parser.get_text()).strip()
    if lower:
        text = text.lower()
    if max_chars is not None:
        return text[:max_chars]
    return text
