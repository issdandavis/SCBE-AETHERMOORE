"""Built-in training guides.

Topics ship as markdown files under guides/data/. The loader reads them at call time.
"""

from __future__ import annotations

from pathlib import Path

_GUIDE_DIR = Path(__file__).parent / "data"


def list_topics() -> list[str]:
    if not _GUIDE_DIR.exists():
        return []
    return sorted(p.stem for p in _GUIDE_DIR.glob("*.md"))


def read_guide(topic: str) -> str | None:
    path = _GUIDE_DIR / f"{topic}.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")
