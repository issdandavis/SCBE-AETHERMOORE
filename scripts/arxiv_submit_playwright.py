#!/usr/bin/env python3
"""Optional browser-assisted arXiv uploader.

Defaults to dry-run for safety. Requires playwright and explicit credentials.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


LOGIN_URL = "https://arxiv.org/login"
SUBMIT_URL = "https://arxiv.org/submit"


def main() -> int:
    parser = argparse.ArgumentParser(description="Browser-assisted arXiv submission")
    parser.add_argument("--bundle", default="artifacts/arxiv/arxiv-submission.tar.gz")
    parser.add_argument("--manifest", default="artifacts/arxiv/manifest.json")
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    if args.dry_run:
        print("dry-run enabled: no browser actions performed")
        print(f"bundle={args.bundle}")
        print(f"manifest={args.manifest}")
        return 0

    user = os.getenv("ARXIV_USER", "").strip()
    password = os.getenv("ARXIV_PASS", "").strip()
    if not user or not password:
        raise RuntimeError("ARXIV_USER and ARXIV_PASS must be set")

    bundle_path = Path(args.bundle)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    from playwright.sync_api import sync_playwright  # local import by design

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(LOGIN_URL)
        page.fill('#username', user)
        page.fill('#password', password)
        page.click('button[type="submit"]')

        page.goto(SUBMIT_URL)
        page.set_input_files('input[type="file"]', str(bundle_path))

        title = manifest.get("title", "")
        if title:
            page.fill('input[name="title"]', title)
        abstract = manifest.get("abstract", "")
        if abstract:
            page.fill('textarea[name="abstract"]', abstract)

        print("Uploaded files and metadata. Review in browser before final submission.")
        input("Press Enter to close browser...")
        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
