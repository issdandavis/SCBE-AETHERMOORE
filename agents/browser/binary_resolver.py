"""Browser binary resolution via ordered face sequence.

Resolution walks a priority-ordered list of "faces" and stops at the first
hit, exactly like a Rubix permission-hypercube path. The result is a shell-safe
command tuple (not a string) plus an auditable receipt.

Face priority order:
    env_override      SCBE_CHROME_PATH env var — operator-trusted override
    playwright_bundle Playwright's pinned Chromium — best for headless
    system_stable     google-chrome-stable (shutil.which)
    system_chromium   chromium / chromium-browser (shutil.which)
    platform_default  hardcoded OS path — last resort, may not exist
"""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BinaryResolutionReceipt:
    selected_path: str
    face_hit: str
    faces_tried: tuple[str, ...]
    platform: str
    path_hash: str  # sha256 of selected_path bytes


# ---------------------------------------------------------------------------
# Face probes
# ---------------------------------------------------------------------------

def _probe_env_override() -> Optional[str]:
    v = os.environ.get("SCBE_CHROME_PATH", "").strip()
    return v if v else None


def _probe_playwright_bundle() -> Optional[str]:
    """Return Playwright's bundled Chromium path if installed and present."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        import playwright._impl._driver as _drv

        # Playwright stores browser executables under a versioned directory.
        # The driver knows the exact path via get_driver_env().
        env = _drv.get_driver_env()
        browsers_root = Path(env.get("PLAYWRIGHT_BROWSERS_PATH", "")).expanduser()
        if not browsers_root.is_dir():
            # Fallback: ~/.cache/ms-playwright (Linux/Mac) or %LOCALAPPDATA%\ms-playwright
            if platform.system() == "Windows":
                browsers_root = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
            else:
                browsers_root = Path.home() / ".cache" / "ms-playwright"

        if browsers_root.is_dir():
            # Walk for chromium executable; stop at first match.
            for candidate in browsers_root.rglob("chrome" if platform.system() == "Windows" else "chrome"):
                if candidate.is_file() and os.access(str(candidate), os.X_OK):
                    return str(candidate)
            # Windows uses chrome.exe
            for candidate in browsers_root.rglob("chrome.exe"):
                if candidate.is_file():
                    return str(candidate)
    except Exception:
        pass
    return None


def _probe_system_stable() -> Optional[str]:
    for name in ("google-chrome-stable", "google-chrome", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _probe_system_chromium() -> Optional[str]:
    for name in ("chromium-browser", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _probe_platform_default() -> Optional[str]:
    system = platform.system()
    if system == "Windows":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        for p in candidates:
            if Path(p).exists():
                return p
        return candidates[0]  # best guess even if absent
    if system == "Darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    # Linux fallback
    return "google-chrome"


# ---------------------------------------------------------------------------
# Ordered face sequence
# ---------------------------------------------------------------------------

_FACES: tuple[tuple[str, object], ...] = (
    ("env_override",      _probe_env_override),
    ("playwright_bundle", _probe_playwright_bundle),
    ("system_stable",     _probe_system_stable),
    ("system_chromium",   _probe_system_chromium),
    ("platform_default",  _probe_platform_default),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_browser_binary() -> tuple[str, BinaryResolutionReceipt]:
    """Walk faces in priority order; return (path, receipt) at first hit.

    The returned path is always a string. The receipt records which face
    resolved it and what was tried before.
    """
    tried: list[str] = []
    for face_name, probe in _FACES:
        result = probe()
        tried.append(face_name)
        if result:
            receipt = BinaryResolutionReceipt(
                selected_path=result,
                face_hit=face_name,
                faces_tried=tuple(tried),
                platform=platform.system(),
                path_hash=hashlib.sha256(result.encode()).hexdigest()[:16],
            )
            return result, receipt

    # Should never reach here — platform_default always returns something.
    fallback = "google-chrome"
    receipt = BinaryResolutionReceipt(
        selected_path=fallback,
        face_hit="fallback",
        faces_tried=tuple(f for f, _ in _FACES),
        platform=platform.system(),
        path_hash=hashlib.sha256(fallback.encode()).hexdigest()[:16],
    )
    return fallback, receipt


def build_launch_command(
    port: int = 9222,
    user_data_dir: Optional[str] = None,
    extra_flags: tuple[str, ...] = (),
) -> tuple[tuple[str, ...], BinaryResolutionReceipt]:
    """Return a shell-safe command tuple and a resolution receipt.

    The tuple is directly passable to subprocess.run() without shell=True.
    No manual quote escaping needed.
    """
    binary, receipt = resolve_browser_binary()
    user_dir = user_data_dir or str(Path.home() / ".scbe-chrome-profile")
    cmd: tuple[str, ...] = (
        binary,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_dir}",
        "--headless=new",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        *extra_flags,
    )
    return cmd, receipt
