#!/usr/bin/env python3
"""SCBE Money Operations Launcher.

Runs the full no-drag monetization pipeline:
1. Create or refresh Gumroad product records via API.
2. Upload all local ZIP files from the GumRoad folder to matching product pages
   using Playwright (headless/headful).

Usage:
  python scripts/gumroad_money_automation.py
  python scripts/gumroad_money_automation.py --manifest GumRoad/upload_results.json --no-create
  python scripts/gumroad_money_automation.py --wait-for-login --headful
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import re

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
GUMROAD_DIR = ROOT / "GumRoad"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _run_command(cmd: list[str], *, extra_env: Optional[dict[str, str]] = None) -> int:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    print("$ " + " ".join(f'\"{c}\"' if " " in c else c for c in cmd))
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env=env,
    )
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


def _ensure_token(token_env: str) -> str:
    token = os.environ.get(token_env, "").strip()
    if not token and token_env == "GUMROAD_ACCESS_TOKEN":
        token = os.environ.get("GUMROAD_API_TOKEN", "").strip()
    if not token:
        print(f"Missing token in env var: {token_env}")
        print("Set one of:")
        print("  $env:GUMROAD_ACCESS_TOKEN='...'   # preferred")
        print("  $env:GUMROAD_API_TOKEN='...'      # fallback alias")
        raise SystemExit(2)
    return token


def _iter_products(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    products = payload.get("products", [])
    if isinstance(products, dict):
        return products.values()
    if isinstance(products, list):
        return products
    return []


def _infer_zip_path(zip_dir: Path, product: dict[str, Any]) -> Optional[Path]:
    zip_file = str(product.get("zip_file") or "").strip()
    if zip_file:
        p = zip_dir / zip_file if not Path(zip_file).is_absolute() else Path(zip_file)
        if p.exists():
            return p

    candidates = [str(product.get(k) or "") for k in ("name", "product_name", "title", "_name", "slug")]
    candidates += [str(product.get("_name") or "").strip(), str(product.get("name") or "").strip().replace("-", "")]
    normalized = []
    for c in candidates:
        c = str(c).strip().lower()
        if not c:
            continue
        normalized.append(c)
        normalized.append(c.replace(" ", ""))
        normalized.append(c.replace(" ", "-"))
        normalized.append(c.replace(" ", "_"))

    zip_files = [p for p in sorted(zip_dir.glob("*.zip")) if p.is_file()]
    if not zip_files:
        return None

    best_path: Optional[Path] = None
    best_score = 0.0
    for zip_path in zip_files:
        stem = zip_path.stem.lower()
        score = 0.0
        for token in normalized:
            token = re.sub(r"[^a-z0-9]+", "", token)
            stem_clean = re.sub(r"[^a-z0-9]+", "", stem)
            if not token:
                continue
            if token in stem_clean:
                score = max(score, 0.95)
            else:
                # crude overlap fallback
                overlap = len(set(token) & set(stem_clean)) / max(len(set(token)), 1)
                score = max(score, overlap)
        if score > best_score:
            best_score = score
            best_path = zip_path

    if best_score >= 0.35:
        return best_path
    return None


def _count_ready_targets(manifest_path: Path) -> int:
    data = _read_json(manifest_path)
    count = 0
    for product in _iter_products(data):
        name = (product.get("name") or "").strip()
        if not name:
            continue
        if not _infer_zip_path(GUMROAD_DIR, product):
            continue
        count += 1
    return count


def _resolve_manifest(args: argparse.Namespace) -> Path:
    if args.manifest:
        return Path(args.manifest).expanduser().resolve()

    candidates = [
        GUMROAD_DIR / "upload_results.json",
        GUMROAD_DIR / "gumroad_publish_manifest.json",
        ROOT / "artifacts" / "products" / "gumroad_publish_manifest.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    # fallback default if none exist
    return GUMROAD_DIR / "upload_results.json"


def run_create_products(token_env: str) -> None:
    print("[1/2] Ensuring Gumroad products exist via API...")
    token = _ensure_token(token_env)
    rc = _run_command(
        [sys.executable, str(SCRIPTS_DIR / "gumroad_upload.py"), "create"],
        extra_env={token_env: token},
    )
    if rc != 0:
        raise SystemExit(rc)
    print("[1/2] Product creation step completed.")


def run_auto_upload(manifest_path: Path, args: argparse.Namespace) -> int:
    print("[2/2] Uploading local zip files to Gumroad product pages via Playwright...")
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        return 1

    ready = _count_ready_targets(manifest_path)
    print(f"Found {ready} matching zip target(s) in manifest + GumRoad folder.")
    if ready == 0:
        print("No local zip targets found. Make sure GumRoad/*.zip files exist.")
        return 2

    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "gumroad_auto_upload.py"),
        "--zip-dir",
        str(GUMROAD_DIR),
        "--manifest",
        str(manifest_path),
        "--log",
        str((ROOT / "training" / "runs" / "gumroad_money_automation.jsonl").resolve()),
        "--timeout",
        str(args.timeout),
        "--passes",
        str(args.passes),
        "--pause-between-passes",
        str(args.pause_between_passes),
        "--user-data-dir",
        str(Path(args.user_data_dir).expanduser()),
    ]

    if not args.headful:
        cmd.append("--headless")

    if args.wait_for_login:
        cmd.append("--wait-for-login")
        cmd.extend(["--login-wait", str(args.login_wait)])

    if args.screenshot_dir:
        cmd.extend(["--screenshot-dir", str(Path(args.screenshot_dir).expanduser())])

    if args.stop_on_error:
        cmd.append("--stop-on-error")

    if args.targets:
        cmd.extend(["--targets"] + args.targets)

    return _run_command(cmd)


def _write_summary(manifest_path: Path, results: int, args: argparse.Namespace) -> None:
    payload = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path),
        "headful": bool(args.headful),
        "wait_for_login": bool(args.wait_for_login),
        "passes": args.passes,
        "upload_rc": results,
        "timeout": args.timeout,
    }
    out = ROOT / "artifacts" / "runs" / "gumroad_money_automation_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Run summary: {out}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Full no-touch Gumroad monetization pipeline")
    parser.add_argument("--manifest", default="", help="Optional path to product manifest/upload_results JSON")
    parser.add_argument("--token-env", default="GUMROAD_ACCESS_TOKEN", help="Env var name for Gumroad token")
    parser.add_argument("--create", dest="do_create", action="store_true", default=True, help="Create products first (default)")
    parser.add_argument("--no-create", dest="do_create", action="store_false", help="Skip product create step")
    parser.add_argument("--headful", action="store_true", help="Run Playwright in headful mode")
    parser.add_argument("--wait-for-login", action="store_true", help="Pause up to --login-wait for manual login if needed")
    parser.add_argument("--login-wait", type=int, default=600, help="Seconds to wait for login")
    parser.add_argument("--timeout", type=float, default=30.0, help="Upload action timeout in seconds")
    parser.add_argument("--passes", type=int, default=1, help="Upload passes")
    parser.add_argument("--pause-between-passes", type=float, default=3.0, help="Pause between passes")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop when first upload fails")
    parser.add_argument("--targets", nargs="+", default=None, help="Optional explicit product names")
    parser.add_argument("--user-data-dir", default=str(ROOT / ".scbe-gumroad-profile"), help="Persistent browser profile")
    parser.add_argument("--screenshot-dir", default="", help="Optional screenshot directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.do_create:
        run_create_products(token_env=args.token_env)

    manifest_path = _resolve_manifest(args)

    upload_rc = run_auto_upload(manifest_path, args)
    _write_summary(manifest_path, upload_rc, args)

    if upload_rc != 0:
        print("Upload pipeline finished with errors.")
        return upload_rc

    print("Monetization pipeline done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
