"""scbe-bookforge CLI.

Subcommands:
    bookforge build [profile.json]    All artifacts (interior, cover, epub, docx)
    bookforge interior [profile.json] Interior PDF only
    bookforge cover [profile.json]    Cover wrap PDF only
    bookforge epub [profile.json]     EPUB only
    bookforge docx [profile.json]     DOCX only
    bookforge info [profile.json]     Print resolved profile + spine math
    bookforge --version
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import (
    __version__,
    build_cover,
    build_docx,
    build_epub,
    build_interior,
    interior_engine_for,
    load_profile,
)


DEFAULT_PROFILE = Path("bookforge.json")


def _resolve_profile_path(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    cwd_profile = Path.cwd() / "bookforge.json"
    if cwd_profile.exists():
        return cwd_profile
    return DEFAULT_PROFILE


def _load_blurb(profile, blurb_path: Path | None) -> dict:
    if not blurb_path:
        # fall back to extra fields on the raw profile
        raw = profile.raw or {}
        return {
            "hook": raw.get("hook", ""),
            "blurb_paragraphs": raw.get("blurb_paragraphs") or [],
            "author_bio": raw.get("author_bio", ""),
            "bottom_left_caption": raw.get("bottom_left_caption", "A WORK"),
        }
    data = json.loads(Path(blurb_path).read_text(encoding="utf-8"))
    return {
        "hook": data.get("hook", ""),
        "blurb_paragraphs": data.get("blurb_paragraphs") or [],
        "author_bio": data.get("author_bio", ""),
        "bottom_left_caption": data.get("bottom_left_caption", ""),
    }


def cmd_info(args) -> int:
    profile = load_profile(_resolve_profile_path(args.profile))
    info = {
        "title": profile.title,
        "author": profile.author,
        "source": str(profile.source_md),
        "output_dir": str(profile.output_dir),
        "binding": profile.binding,
        "trim_in": profile.trim_in,
        "paper": profile.paper,
        "ink": profile.ink,
        "page_count": profile.page_count,
        "spine_in": profile.spine_width_in() if profile.page_count else None,
        "interior_engine_resolved": interior_engine_for(profile),
    }
    print(json.dumps(info, indent=2, default=str))
    return 0


def cmd_interior(args) -> int:
    profile = load_profile(_resolve_profile_path(args.profile))
    path = build_interior(profile)
    print(str(path))
    return 0


def cmd_cover(args) -> int:
    profile = load_profile(_resolve_profile_path(args.profile))
    blurb = _load_blurb(profile, Path(args.blurb) if args.blurb else None)
    path = build_cover(profile, **blurb)
    print(str(path))
    return 0


def cmd_epub(args) -> int:
    profile = load_profile(_resolve_profile_path(args.profile))
    path = build_epub(profile)
    print(str(path))
    return 0


def cmd_docx(args) -> int:
    profile = load_profile(_resolve_profile_path(args.profile))
    path = build_docx(profile)
    print(str(path))
    return 0


def cmd_build(args) -> int:
    profile = load_profile(_resolve_profile_path(args.profile))
    blurb = _load_blurb(profile, Path(args.blurb) if args.blurb else None)
    results: dict[str, str] = {}
    if not args.no_interior:
        results["interior_pdf"] = str(build_interior(profile))
    if not args.no_epub:
        results["epub"] = str(build_epub(profile))
    if not args.no_docx:
        results["docx"] = str(build_docx(profile))
    if not args.no_cover and profile.page_count is not None:
        results["cover_pdf"] = str(build_cover(profile, **blurb))
    print(json.dumps(results, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bookforge", description=__doc__)
    parser.add_argument("--version", action="version", version=f"scbe-bookforge {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Build all artifacts")
    p_build.add_argument("profile", nargs="?")
    p_build.add_argument("--blurb", help="Path to a back-cover blurb JSON")
    p_build.add_argument("--no-interior", action="store_true")
    p_build.add_argument("--no-cover", action="store_true")
    p_build.add_argument("--no-epub", action="store_true")
    p_build.add_argument("--no-docx", action="store_true")
    p_build.set_defaults(func=cmd_build)

    p_int = sub.add_parser("interior", help="Build the interior PDF only")
    p_int.add_argument("profile", nargs="?")
    p_int.set_defaults(func=cmd_interior)

    p_cov = sub.add_parser("cover", help="Build the cover wrap PDF only")
    p_cov.add_argument("profile", nargs="?")
    p_cov.add_argument("--blurb", help="Path to a back-cover blurb JSON")
    p_cov.set_defaults(func=cmd_cover)

    p_epub = sub.add_parser("epub", help="Build the EPUB only")
    p_epub.add_argument("profile", nargs="?")
    p_epub.set_defaults(func=cmd_epub)

    p_docx = sub.add_parser("docx", help="Build the DOCX only")
    p_docx.add_argument("profile", nargs="?")
    p_docx.set_defaults(func=cmd_docx)

    p_info = sub.add_parser("info", help="Show resolved profile + spine math")
    p_info.add_argument("profile", nargs="?")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"bookforge: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"bookforge: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
