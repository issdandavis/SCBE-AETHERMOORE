"""scbe-bookforge: Markdown to KDP-ready paperback, hardcover, and Kindle EPUB.

Public API:

    from scbe_bookforge import load_profile, build_all, build_interior, build_cover

    profile = load_profile("my-book/profile.json")
    artifacts = build_all(profile)
    # -> {"interior_pdf": ..., "cover_pdf": ..., "epub": ..., "docx": ...}
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import cover as _cover
from . import ebook as _ebook
from . import interior_reportlab as _interior_rl
from . import interior_xelatex as _interior_xe
from .profile import Profile, load_profile

__all__ = [
    "Profile",
    "load_profile",
    "build_interior",
    "build_cover",
    "build_epub",
    "build_docx",
    "build_all",
    "interior_engine_for",
    "__version__",
]

__version__ = "0.1.0"


def interior_engine_for(profile: Profile) -> str:
    """Resolve which interior engine will run for this profile."""
    pref = profile.interior_engine
    if pref == "xelatex":
        return "xelatex"
    if pref == "reportlab":
        return "reportlab"
    return "xelatex" if _interior_xe.is_available() else "reportlab"


def build_interior(profile: Profile, *, out_pdf: Optional[Path] = None) -> Path:
    engine = interior_engine_for(profile)
    if engine == "xelatex":
        return _interior_xe.build(profile, out_pdf=out_pdf)
    return _interior_rl.build(profile, out_pdf=out_pdf)


def build_cover(profile: Profile, **cover_kwargs) -> Path:
    return _cover.build(profile, **cover_kwargs)


def build_epub(profile: Profile, *, out_path: Optional[Path] = None) -> Path:
    return _ebook.build_epub(profile, out_path=out_path)


def build_docx(profile: Profile, *, out_path: Optional[Path] = None) -> Path:
    return _ebook.build_docx(profile, out_path=out_path)


def build_all(
    profile: Profile,
    *,
    skip: Optional[list[str]] = None,
    cover_kwargs: Optional[dict] = None,
) -> dict[str, Path]:
    skip = set(skip or [])
    out: dict[str, Path] = {}
    if "interior" not in skip:
        out["interior_pdf"] = build_interior(profile)
    if "cover" not in skip and profile.page_count is not None:
        out["cover_pdf"] = build_cover(profile, **(cover_kwargs or {}))
    if "epub" not in skip:
        out["epub"] = build_epub(profile)
    if "docx" not in skip:
        out["docx"] = build_docx(profile)
    return out
