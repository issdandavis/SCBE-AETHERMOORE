#!/usr/bin/env python3
"""Automated Gumroad zip upload runner.

This script uses Playwright to automate authenticated Gumroad product uploads from a local
folder containing your package ZIP files.

Typical workflow:
  python scripts/gumroad_auto_upload.py --zip-dir "C:\\Users\\issda\\SCBE-AETHERMOORE\\GumRoad" \
    --manifest GumRoad/gumroad_publish_manifest.json --headful --wait-for-login 900 --headless
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GUMROAD_DIR = ROOT / "GumRoad"
DEFAULT_MANIFESTS = [
    DEFAULT_GUMROAD_DIR / "gumroad_publish_manifest.json",
    ROOT / "artifacts" / "products" / "product_manifest.json",
    ROOT / "GumRoad" / "upload_results.json",
]
GUMROAD_PRODUCTS_URL = "https://app.gumroad.com/products"


@dataclass
class UploadTarget:
    name: str
    zip_path: Path
    product_url: str | None = None
    gumroad_id: str | None = None
    gumroad_lookup_key: str | None = None


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _tokens(text: str) -> set[str]:
    return {t for t in _norm(text).split() if t}


def _score_match(target: str, candidate: str) -> float:
    if not target or not candidate:
        return 0.0
    t = _norm(target)
    c = _norm(candidate)
    token_a = _tokens(target)
    token_b = _tokens(candidate)
    ratio = 0.0
    if token_a and token_b:
        overlap = len(token_a & token_b) / max(len(token_a), 1)
        ratio = max(ratio, overlap)
    ratio = max(ratio, __import__("difflib").SequenceMatcher(None, t, c).ratio())
    return ratio


def _candidate_zip_path(zip_dir: Path, zip_name: str) -> Path:
    name = Path(zip_name)
    if name.exists():
        return name
    if name.is_absolute():
        return name
    for root in [zip_dir, ROOT / "artifacts" / "products"]:
        p = root / name.name
        if p.exists():
            return p
    return zip_dir / name.name


def _infer_zip_path_from_name(zip_dir: Path, item: dict[str, Any]) -> Path | None:
    """Infer a zip file path from manifest metadata or nearest filename match."""

    explicit_zip = str(item.get("zip_file") or "").strip()
    if explicit_zip:
        candidate = _candidate_zip_path(zip_dir, explicit_zip)
        if candidate.exists():
            return candidate

    # Gather likely identity tokens.
    raw_candidates = [
        str(item.get("name") or ""),
        str(item.get("_name") or ""),
        str(item.get("product_name") or ""),
        str(item.get("slug") or ""),
        str(item.get("title") or ""),
    ]
    normalized_tokens: list[str] = []
    for raw in raw_candidates:
        token = _norm(raw)
        if token:
            normalized_tokens.append(token)
            normalized_tokens.append(token.replace(" ", "-"))
            normalized_tokens.append(token.replace(" ", "_"))

    # Fallback short aliases from common keys.
    short_alias = str(item.get("_name") or "").strip().lower()
    if short_alias:
        normalized_tokens.append(short_alias)
        normalized_tokens.append(short_alias.replace("-", " "))

    if not normalized_tokens:
        return None

    zip_files = [p for p in sorted(zip_dir.glob("*.zip")) if p.is_file()]
    best_path: Path | None = None
    best_score = 0.0
    for zip_path in zip_files:
        stem = zip_path.stem.lower().replace("-", " ").replace("_", " ")
        score = 0.0
        for token in normalized_tokens:
            if not token:
                continue
            # Direct containment is strong for exact short keys like n8n.
            if token and token in stem:
                score = max(score, 0.95)
            else:
                score = max(score, _score_match(token, stem))
        if score > best_score:
            best_score = score
            best_path = zip_path

    # Require a minimal confidence threshold to avoid wrong attachment.
    if best_score >= 0.35:
        return best_path
    return None


def _load_manifest_targets(path: Path, zip_dir: Path) -> list[UploadTarget]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items: Iterable[dict[str, Any]]

    raw_products: Any = data.get("products")
    if isinstance(raw_products, dict):
        items = [dict(v, **{"_name": k}) for k, v in raw_products.items() if isinstance(v, dict)]
    elif isinstance(raw_products, list):
        items = raw_products
    else:
        return []

    targets: list[UploadTarget] = []
    for item in items:
        name = str(item.get("name") or item.get("_name") or "").strip()
        if not name:
            continue

        zip_path = _infer_zip_path_from_name(zip_dir=zip_dir, item=item)
        if zip_path is None:
            continue
        targets.append(
            UploadTarget(
                name=name,
                zip_path=zip_path,
                product_url=str(item.get("gumroad_url") or item.get("product_url") or ""),
                gumroad_id=str(item.get("gumroad_id") or item.get("id") or "") or None,
                gumroad_lookup_key=str(item.get("gumroad_lookup_key") or "") or None,
            )
        )
    return targets


def _load_zip_targets(zip_dir: Path) -> list[UploadTarget]:
    targets: list[UploadTarget] = []
    for p in sorted(zip_dir.glob("*.zip")):
        if not p.is_file():
            continue
        name = p.stem.replace("-", " ").replace("_", " ").replace("v1.0.0", "").strip()
        if not name:
            continue
        targets.append(UploadTarget(name=name, zip_path=p))
    return targets


def _resolve_targets(zip_dir: Path, manifest: str | None, explicit_targets: list[str] | None) -> list[UploadTarget]:
    candidates: list[UploadTarget] = []
    if manifest:
        mpath = Path(manifest).expanduser().resolve()
        if mpath.exists():
            candidates = _load_manifest_targets(mpath, zip_dir)

    if not candidates:
        candidates = _load_zip_targets(zip_dir)

    if not explicit_targets:
        return candidates

    wanted = {_norm(t): t for t in explicit_targets}
    matched: list[UploadTarget] = []
    for raw_target in explicit_targets:
        target_text = raw_target.strip()
        if not target_text:
            continue
        best = None
        best_score = 0.0
        for candidate in candidates:
            score = _score_match(target_text, candidate.name)
            if score > best_score:
                best = candidate
                best_score = score
        if best is not None and best_score >= 0.35:
            matched.append(best)
    return matched


def _find_products(page: Any) -> dict[str, str]:
    page.goto(GUMROAD_PRODUCTS_URL, wait_until="domcontentloaded")

    products: dict[str, str] = {}
    page.wait_for_selector("a[href*='/products/']", timeout=30_000)
    anchors = page.locator("a[href*='/products/']")

    for i in range(anchors.count()):
        a = anchors.nth(i)
        href = (a.get_attribute("href") or "").strip()
        if not href or "/products/" not in href:
            continue
        if href.endswith("/edit"):
            href = href[:-5]
        if href.endswith("/"):
            href = href[:-1]
        if "/products/new" in href:
            continue

        raw_text = (a.inner_text() or "").strip()
        text = re.sub(r"\s+", " ", raw_text)
        if not text:
            text = href.rstrip("/").split("/")[-1]

        if text in products:
            continue
        products[text] = href
    return products


def _find_best_product_match(target_name: str, product_map: dict[str, str]) -> tuple[str | None, float]:
    best_name = None
    best_score = 0.0
    for name in product_map:
        score = _score_match(target_name, name)
        if score > best_score:
            best_name = name
            best_score = score
    return best_name, best_score


def _pick_file_input(page: Any) -> Any | None:
    all_inputs = page.locator("input[type='file']").all()
    for input_el in all_inputs:
        accept = (input_el.get_attribute("accept") or "").lower()
        if "zip" in accept or "*/*" in accept:
            try:
                input_el.set_input_files([], timeout=1_000)
            except Exception:
                pass
            return input_el

    for input_el in all_inputs:
        try:
            if input_el.is_visible():
                return input_el
        except Exception:
            continue

    if all_inputs:
        return all_inputs[0]
    return None


def _find_save_button(page: Any) -> Any | None:
    candidates = [
        "button:has-text('Save changes')",
        "button:has-text('Save & Close')",
        "button:has-text('Update')",
        "button:has-text('Save')",
        "button:has-text('Publish')",
    ]
    for selector in candidates:
        button = page.locator(selector)
        if button.count() > 0:
            btn = button.first
            try:
                if btn.is_visible() and btn.is_enabled():
                    return btn
            except Exception:
                continue

    # Last-ditch fallback: JS click first matching button with text in page
    button = page.evaluate(
        """
        () => {
            const labels = ['Save changes', 'Update', 'Save', 'Publish'];
            const candidates = [...document.querySelectorAll('button')];
            for (const button of candidates) {
                const text = (button.innerText || '').toLowerCase();
                if (!text.trim()) continue;
                if (labels.some((l) => text.includes(l.toLowerCase()))) {
                    if (!button.disabled) {
                        button.click();
                        return true;
                    }
                }
            }
            return false;
        }
        """
    )
    if button:
        return "clicked"
    return None


def _upload_one(page: Any, target: UploadTarget, timeout: float, screenshot_dir: Path | None, logger, index: int) -> tuple[bool, str]:
    if not target.zip_path.exists():
        return False, f"Zip not found: {target.zip_path}"

    logger(
        {
            "event": "target_start",
            "target": target.name,
            "zip_path": str(target.zip_path),
            "index": index,
        }
    )

    product_map = _find_products(page)
    if not product_map:
        return False, "No products found on products page. Ensure you are logged in."

    matched_name, score = _find_best_product_match(target.name, product_map)
    if not matched_name or score < 0.20:
        return False, f"No matching product found for target={target.name!r} score={score:.2f}"

    edit_url = product_map[matched_name].rstrip("/") + "/edit"
    page.goto(edit_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    file_input = _pick_file_input(page)
    if file_input is None:
        return False, f"No file input found on edit page for {matched_name}"

    file_input.set_input_files(str(target.zip_path), timeout=int(timeout * 1000))

    # Give Gumroad UI a chance to accept the file and update previews.
    page.wait_for_timeout(2_000)

    save_btn = _find_save_button(page)
    if save_btn is None:
        return False, f"File attached but save button not found for {matched_name}."

    if save_btn != "clicked":
        save_btn.click()
    page.wait_for_timeout(1_500)

    if screenshot_dir is not None:
        shot_path = screenshot_dir / f"{_norm(target.name).replace(' ', '_')}-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(shot_path), full_page=True)

    return True, f"Uploaded {target.zip_path.name} to '{matched_name}'"


def _append_jsonl(log_path: Path, payload: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def run_upload(args: argparse.Namespace) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print("Playwright not installed.")
        print("Fix: python -m pip install playwright && python -m playwright install chromium")
        return 2

    zip_dir = Path(args.zip_dir).expanduser().resolve()
    if not zip_dir.exists():
        raise FileNotFoundError(f"zip-dir not found: {zip_dir}")

    targets = _resolve_targets(zip_dir=zip_dir, manifest=args.manifest if args.manifest != "" else None, explicit_targets=args.targets)
    if not targets:
        print("No upload targets found.")
        return 3

    log_path = Path(args.log).expanduser().resolve()
    screenshot_dir = Path(args.screenshot_dir).expanduser().resolve() if args.screenshot_dir else None

    print(f"Found {len(targets)} target(s).")
    for t in targets:
        print(f"  - {t.name} => {t.zip_path}")

    if args.dry_run:
        for i, t in enumerate(targets, 1):
            _append_jsonl(log_path, {"event": "dry_run", "index": i, "target": t.name, "zip": str(t.zip_path), "status": "would_upload"})
        print(f"Dry-run complete. Log: {log_path}")
        return 0

    start_ts = datetime.now(timezone.utc).isoformat()
    failures = 0

    with sync_playwright() as p:
        use_persistent = bool(args.user_data_dir)
        if use_persistent:
            user_data_dir = str(Path(args.user_data_dir).expanduser().resolve())
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=args.headless,
                viewport={"width": 1440, "height": 1200},
            )
            page = context.pages[0] if context.pages else context.new_page()
        else:
            browser = p.chromium.launch(headless=args.headless)
            context = browser.new_context(viewport={"width": 1440, "height": 1200})
            page = context.new_page()

        try:
            page.set_default_timeout(int(args.timeout * 1000))
            page.set_default_navigation_timeout(int(args.timeout * 1000))

            print(f"Opening {GUMROAD_PRODUCTS_URL}")
            page.goto(GUMROAD_PRODUCTS_URL, wait_until="domcontentloaded")

            if "signin" in page.url.lower() or "login" in page.url.lower() or "accounts" in page.url.lower():
                if args.wait_for_login:
                    print("Session not authenticated. Waiting for manual login (this window stays open).")
                    login_deadline = time.time() + args.login_wait
                    while time.time() < login_deadline:
                        page.goto(GUMROAD_PRODUCTS_URL, wait_until="domcontentloaded")
                        if "signin" not in page.url.lower() and "login" not in page.url.lower():
                            break
                        time.sleep(2)
                    else:
                        print("Login timeout waiting for authentication.")
                        return 4
                else:
                    print("Login required. Re-run with --wait-for-login if not signed in yet.")
                    return 4

            for pass_index in range(args.passes):
                run_events: list[dict[str, Any]] = []
                for idx, target in enumerate(targets, 1):
                    ok, message = _upload_one(
                        page=page,
                        target=target,
                        timeout=args.timeout,
                        screenshot_dir=screenshot_dir,
                        logger=lambda payload: run_events.append(payload),
                        index=idx,
                    )
                    record = {
                        "event": "upload",
                        "run": pass_index + 1,
                        "index": idx,
                        "target": target.name,
                        "zip": str(target.zip_path),
                        "ok": ok,
                        "message": message,
                    }
                    _append_jsonl(log_path, record)
                    run_events.append(record)
                    if not ok:
                        failures += 1
                        print(f"[FAIL] {message}")
                        if args.stop_on_error:
                            break
                    else:
                        print(f"[OK] {message}")

                if pass_index + 1 < args.passes:
                    print(f"Pass {pass_index + 1} done. Pausing {args.pause_between_passes}s")
                    time.sleep(args.pause_between_passes)

                if args.stop_on_error and failures:
                    break

            _append_jsonl(
                log_path,
                {
                    "event": "summary",
                    "start_time_utc": start_ts,
                    "targets": len(targets),
                    "passes": args.passes,
                    "failures": failures,
                    "log": str(log_path),
                },
            )
            print(f"Done. Log: {log_path}")
        finally:
            context.close()

    return 0 if failures == 0 else 1


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Upload Gumroad zip files via Playwright")
    p.add_argument("--zip-dir", default=str(DEFAULT_GUMROAD_DIR), help="Folder containing zip files")
    p.add_argument("--manifest", default="", help="Optional manifest JSON file (upload_results.json, gumroad_publish_manifest.json, product_manifest.json)")
    p.add_argument("--targets", nargs="+", default=None, help="Explicit product targets by product name")
    p.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    p.add_argument("--user-data-dir", default=str(Path.home() / ".scbe-gumroad-profile"), help="Reuse Chrome profile between runs")
    p.add_argument("--wait-for-login", action="store_true", help="Pause and allow manual login if not already authenticated")
    p.add_argument("--login-wait", type=int, default=900, help="Seconds to wait for manual login when --wait-for-login is set")
    p.add_argument("--timeout", type=float, default=20.0, help="Action timeout in seconds")
    p.add_argument("--passes", type=int, default=1, help="Number of upload passes")
    p.add_argument("--pause-between-passes", type=float, default=3.0, help="Pause in seconds between passes")
    p.add_argument("--stop-on-error", action="store_true", help="Abort when a target fails")
    p.add_argument("--dry-run", action="store_true", help="Show targets and write plan without uploading")
    p.add_argument("--screenshot-dir", default="", help="Optional screenshot directory for upload attempts")
    p.add_argument("--log", default=str(Path("training") / "runs" / "gumroad_auto_upload.jsonl"), help="JSONL log path")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.passes <= 0:
        raise ValueError("--passes must be >= 1")

    manifest_path = args.manifest.strip()
    if manifest_path:
        if not Path(manifest_path).expanduser().exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    for candidate in DEFAULT_MANIFESTS:
        if args.manifest:
            break
        if candidate.exists():
            args.manifest = str(candidate)
            break

    return run_upload(args)


if __name__ == "__main__":
    raise SystemExit(main())
