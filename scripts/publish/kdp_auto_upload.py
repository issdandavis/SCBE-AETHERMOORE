"""
KDP Auto-Upload via Playwright Browser Automation.

Automates the KDP manuscript update process:
1. Navigate to KDP Bookshelf
2. Find the book
3. Click Edit content
4. Upload new manuscript EPUB
5. Wait for conversion
6. Launch previewer (optional)
7. Save and continue
8. Publish

Usage:
    python scripts/publish/kdp_auto_upload.py                  # Full guided upload
    python scripts/publish/kdp_auto_upload.py --epub PATH      # Specify EPUB path
    python scripts/publish/kdp_auto_upload.py --dry-run        # Navigate but don't click Publish
    python scripts/publish/kdp_auto_upload.py --headless        # Run without visible browser

Requirements:
    pip install playwright
    playwright install chromium

NOTE: KDP requires login. The script will pause for you to log in manually
if you're not already authenticated. Your credentials are never stored.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(r"C:\Users\issda\SCBE-AETHERMOORE")
DEFAULT_EPUB = REPO / "artifacts" / "book" / "kdp" / "the-six-tongues-protocol.epub"
KDP_BOOKSHELF = "https://kdp.amazon.com/en_US/bookshelf"
BOOK_TITLE = "The Six Tongues Protocol"
DEFAULT_ACCEPTANCE_REPORT = REPO / "artifacts" / "book" / "kdp" / "acceptance-gate.json"


def run_acceptance_gates(manuscript_path: Path) -> None:
    """Run local story, visual, and KDP acceptance gates before browser upload."""
    commands = [
        [sys.executable, "scripts/publish/kdp_story_quality_gate.py"],
        [sys.executable, "scripts/publish/kdp_visual_format_report.py"],
        [
            sys.executable,
            "scripts/publish/kdp_acceptance_gate.py",
            "--manuscript",
            str(manuscript_path),
            "--out",
            str(DEFAULT_ACCEPTANCE_REPORT),
        ],
    ]
    for cmd in commands:
        print(f"[gate] {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=REPO, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        if result.returncode != 0:
            print("\nERROR: KDP acceptance gates did not pass. Upload blocked.")
            print("Fix the gate report before trying again.")
            sys.exit(result.returncode)

    report = json.loads(DEFAULT_ACCEPTANCE_REPORT.read_text(encoding="utf-8"))
    if report.get("decision") != "PASS":
        print(f"ERROR: KDP acceptance decision is {report.get('decision')}. Upload blocked.")
        sys.exit(2)
    print(f"[gate] PASS score={report.get('score')}/{report.get('max_score')}")


def run_upload(epub_path, dry_run=False, headless=False, skip_gate=False):
    """Run the KDP upload automation."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    epub = Path(epub_path)
    if not epub.exists():
        print(f"ERROR: EPUB not found: {epub}")
        print(f"Run: python scripts/publish/rebuild_and_stage_kdp.py")
        sys.exit(1)

    if skip_gate:
        print("[gate] SKIPPED by explicit flag. Final publish still requires manual confirmation.")
    else:
        run_acceptance_gates(epub)

    print(f"[KDP Auto-Upload]")
    print(f"  EPUB: {epub}")
    print(f"  Size: {epub.stat().st_size / 1024:.0f} KB")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    with sync_playwright() as p:
        # Use persistent context so KDP login cookies persist between runs
        user_data = REPO / "artifacts" / "browser-data" / "kdp-profile"
        user_data.mkdir(parents=True, exist_ok=True)

        browser = p.chromium.launch_persistent_context(
            str(user_data),
            headless=headless,
            slow_mo=500,  # Slow enough to see what's happening
            viewport={"width": 1400, "height": 900},
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        # Step 1: Navigate to KDP Bookshelf
        print("[1/7] Navigating to KDP Bookshelf...")
        page.goto(KDP_BOOKSHELF, wait_until="networkidle")
        time.sleep(2)

        # Check if we need to log in
        if "signin" in page.url.lower() or "ap/signin" in page.url.lower():
            print("\n  ⚠️  KDP LOGIN REQUIRED")
            print("  Please log in manually in the browser window.")
            print("  The script will continue automatically after login.\n")

            # Wait for redirect back to bookshelf (up to 5 minutes)
            try:
                page.wait_for_url("**/bookshelf**", timeout=300000)
                print("  ✓ Login successful!")
            except Exception:
                print("  ERROR: Login timeout. Please try again.")
                browser.close()
                sys.exit(1)

        time.sleep(2)

        # Step 2: Find the book on the bookshelf
        print(f"[2/7] Looking for '{BOOK_TITLE}'...")

        # Look for the book's ellipsis menu button
        book_found = False
        try:
            # KDP bookshelf has action buttons per book — look for our title
            book_rows = page.locator("tr, div[class*='book'], div[class*='title']").all()
            for row in book_rows:
                text = row.text_content() or ""
                if BOOK_TITLE.lower() in text.lower():
                    print(f"  ✓ Found: {BOOK_TITLE}")
                    # Click the ellipsis/actions button for this book
                    action_btn = row.locator("button, [class*='action'], [class*='ellipsis'], [class*='menu']").first
                    if action_btn.is_visible():
                        action_btn.click()
                        time.sleep(1)
                        book_found = True
                    break
        except Exception as e:
            print(f"  Could not find book automatically: {e}")

        if not book_found:
            print(f"\n  ⚠️  Could not automatically find '{BOOK_TITLE}' on the bookshelf.")
            print("  Please manually click the '...' button next to your book.")
            input("  Press Enter when you've opened the action menu...")

        # Step 3: Click "Edit eBook Content" or similar
        print("[3/7] Opening content editor...")
        try:
            # Look for "Edit eBook Content" or "Edit content" link
            edit_link = page.locator("text=/edit.*content/i").first
            edit_link.click()
            page.wait_for_load_state("networkidle")
            time.sleep(3)
        except Exception:
            print("  ⚠️  Could not find 'Edit content' link automatically.")
            print("  Please click 'Edit eBook Content' manually.")
            input("  Press Enter when the content page is loaded...")

        # Step 4: Upload manuscript
        print("[4/7] Uploading manuscript...")
        try:
            # Look for the upload button/input
            upload_btn = page.locator("text=/upload.*manuscript/i, button:has-text('Upload'), input[type='file']")

            # If there's a file input, use it directly
            file_input = page.locator("input[type='file']").first
            if file_input.count() > 0:
                file_input.set_input_files(str(epub))
                print(f"  ✓ Manuscript uploaded: {epub.name}")
            else:
                # Click the upload button first, then handle file dialog
                upload_btn.first.click()
                time.sleep(1)
                file_input = page.locator("input[type='file']").first
                file_input.set_input_files(str(epub))
                print(f"  ✓ Manuscript uploaded: {epub.name}")

            # Wait for conversion (KDP processes the file)
            print("  Waiting for conversion (this may take a few minutes)...")
            try:
                page.wait_for_selector(
                    "text=/uploaded successfully/i, text=/conversion complete/i, text=/manuscript.*processed/i",
                    timeout=180000,
                )
                print("  ✓ Conversion complete!")
            except Exception:
                print("  ⚠️  Could not detect conversion completion automatically.")
                print("  Check the browser to see if the upload succeeded.")
                input("  Press Enter when the manuscript is processed...")

        except Exception as e:
            print(f"  ⚠️  Upload automation failed: {e}")
            print(f"  Please manually upload: {epub}")
            input("  Press Enter when the manuscript is uploaded and processed...")

        # Step 5: Launch Previewer (optional)
        print("[5/7] Previewer available...")
        try:
            preview_btn = page.locator("text=/launch.*preview/i, text=/preview/i").first
            if preview_btn.is_visible():
                print("  Previewer button found. Skipping auto-launch (you can check manually).")
        except Exception:
            pass

        # Step 6: Save and Continue
        print("[6/7] Saving content...")
        if not dry_run:
            try:
                save_btn = page.locator("text=/save.*continue/i, input[value*='Save'], button:has-text('Save')").first
                save_btn.click()
                page.wait_for_load_state("networkidle")
                time.sleep(3)
                print("  ✓ Content saved!")
            except Exception:
                print("  ⚠️  Could not find Save button automatically.")
                input("  Please click 'Save and Continue' manually, then press Enter...")
        else:
            print("  [DRY RUN] Skipping save.")

        # Step 7: Publish
        print("[7/7] Publishing...")
        if not dry_run:
            try:
                # Navigate to pricing page if needed, then click Publish
                publish_btn = page.locator("text=/publish/i, input[value*='Publish'], button:has-text('Publish')").last
                if publish_btn.is_visible():
                    print("\n  ⚠️  Ready to publish. This will make the update LIVE on Amazon.")
                    confirm = input("  Type 'publish' to confirm: ")
                    if confirm.strip().lower() == "publish":
                        publish_btn.click()
                        time.sleep(5)
                        print("  ✓ Published! Amazon will review the update.")
                        print("  Updates typically go live within 24-72 hours.")
                    else:
                        print("  Publication cancelled.")
                else:
                    print("  ⚠️  Could not find Publish button.")
                    print("  Please click 'Publish' manually on the KDP page.")
            except Exception as e:
                print(f"  ⚠️  Publish automation failed: {e}")
                print("  Please publish manually through the KDP interface.")
        else:
            print("  [DRY RUN] Skipping publish.")

        print("\n[Done]")
        if not dry_run:
            print("  Your updated manuscript has been submitted to KDP.")
            print("  Amazon will review and publish within 24-72 hours.")
        else:
            print("  Dry run complete. No changes were made to KDP.")

        # Keep browser open so user can verify
        print("\n  Browser will stay open for verification.")
        print("  Close the browser window when done, or press Ctrl+C.")

        try:
            page.wait_for_event("close", timeout=3600000)  # Wait up to 1 hour
        except KeyboardInterrupt:
            pass
        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser(description="KDP Auto-Upload")
    parser.add_argument("--epub", default=str(DEFAULT_EPUB), help="Path to EPUB file to upload")
    parser.add_argument("--dry-run", action="store_true", help="Navigate without publishing")
    parser.add_argument("--headless", action="store_true", help="Run without visible browser")
    parser.add_argument("--skip-gate", action="store_true", help="Skip local acceptance gates before upload")

    args = parser.parse_args()
    run_upload(args.epub, args.dry_run, args.headless, args.skip_gate)


if __name__ == "__main__":
    main()
