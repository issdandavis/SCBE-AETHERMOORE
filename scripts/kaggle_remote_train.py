"""
Kaggle Remote Training Automation

Push, trigger, poll, and download fine-tuning jobs on Kaggle's free GPUs.
Designed to be called by Claude Code for fully automated training runs.

Setup (one-time):
  1. Create Kaggle account at kaggle.com
  2. Go to kaggle.com/settings → API → Create New Token
  3. Save kaggle.json to ~/.kaggle/kaggle.json
  4. Add HF_TOKEN as a Kaggle secret:
     kaggle.com → Settings → Secrets → Add "HF_TOKEN"

Usage:
  python scripts/kaggle_remote_train.py push      # Push kernel to Kaggle
  python scripts/kaggle_remote_train.py status     # Check kernel status
  python scripts/kaggle_remote_train.py poll       # Poll until complete
  python scripts/kaggle_remote_train.py output     # Download output files
  python scripts/kaggle_remote_train.py run        # Push + poll + download (full pipeline)
  python scripts/kaggle_remote_train.py setup      # Check prerequisites
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
KERNEL_SCRIPT = REPO_ROOT / "training" / "kaggle_kernel.py"
KERNEL_DIR = REPO_ROOT / "training" / "kaggle_push"
METADATA_FILE = KERNEL_DIR / "kernel-metadata.json"
OUTPUT_DIR = REPO_ROOT / "artifacts" / "kaggle_runs"

# Kaggle kernel identifier
KAGGLE_USERNAME = os.environ.get("KAGGLE_USERNAME", "issdandavis")
KERNEL_SLUG = "scbe-aethermoore-qlora-sft"
KERNEL_ID = f"{KAGGLE_USERNAME}/{KERNEL_SLUG}"


def check_kaggle_cli():
    """Verify kaggle CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["kaggle", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"Kaggle CLI: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass

    print("ERROR: Kaggle CLI not found.")
    print("Install with: pip install kaggle")
    return False


def check_credentials():
    """Check for ~/.kaggle/kaggle.json credentials."""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if kaggle_json.exists():
        creds = json.loads(kaggle_json.read_text())
        username = creds.get("username", "unknown")
        print(f"Kaggle credentials: {username}")
        return True

    # Also check env vars
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        print(f"Kaggle credentials: {os.environ['KAGGLE_USERNAME']} (from env)")
        return True

    print("ERROR: No Kaggle credentials found.")
    print("Steps:")
    print("  1. Go to kaggle.com/settings > API > Create New Token")
    print("  2. Save the downloaded kaggle.json to ~/.kaggle/kaggle.json")
    print("  Or set KAGGLE_USERNAME and KAGGLE_KEY environment variables.")
    return False


def cmd_setup():
    """Check all prerequisites for remote training."""
    print("=" * 60)
    print("KAGGLE REMOTE TRAINING — SETUP CHECK")
    print("=" * 60)

    checks = []

    # 1. Kaggle CLI
    checks.append(("Kaggle CLI", check_kaggle_cli()))

    # 2. Credentials
    checks.append(("Credentials", check_credentials()))

    # 3. Kernel script
    exists = KERNEL_SCRIPT.exists()
    print(f"Kernel script: {'OK' if exists else 'MISSING'} ({KERNEL_SCRIPT})")
    checks.append(("Kernel script", exists))

    # 4. HF token (for pushing trained model)
    hf_token = bool(os.environ.get("HF_TOKEN"))
    print(f"HF_TOKEN env: {'Set' if hf_token else 'Not set (add as Kaggle secret instead)'}")
    checks.append(("HF_TOKEN", True))  # Not blocking — can use Kaggle secrets

    print()
    all_ok = all(ok for _, ok in checks)
    if all_ok:
        print("All checks passed. Ready to push kernels.")
    else:
        failed = [name for name, ok in checks if not ok]
        print(f"FAILED: {', '.join(failed)}")
        print("Fix the above issues before running.")

    return all_ok


def cmd_push():
    """Push the kernel to Kaggle for execution."""
    if not check_kaggle_cli() or not check_credentials():
        return False

    # Create push directory
    KERNEL_DIR.mkdir(parents=True, exist_ok=True)

    # Copy kernel script
    dest_script = KERNEL_DIR / "kaggle_kernel.py"
    shutil.copy2(KERNEL_SCRIPT, dest_script)

    # Create kernel-metadata.json
    metadata = {
        "id": KERNEL_ID,
        "title": "SCBE-AETHERMOORE QLoRA SFT Training",
        "code_file": "kaggle_kernel.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
    }

    METADATA_FILE.write_text(json.dumps(metadata, indent=2))
    print(f"Metadata written: {METADATA_FILE}")

    # Push to Kaggle
    print(f"\nPushing kernel: {KERNEL_ID}")
    result = subprocess.run(
        ["kaggle", "kernels", "push", "-p", str(KERNEL_DIR)],
        capture_output=True, text=True, timeout=120
    )

    if result.returncode == 0:
        print(f"Kernel pushed successfully.")
        print(result.stdout)
        return True
    else:
        print(f"Push failed: {result.stderr}")
        return False


def cmd_status():
    """Check the status of the kernel."""
    if not check_kaggle_cli():
        return None

    result = subprocess.run(
        ["kaggle", "kernels", "status", KERNEL_ID],
        capture_output=True, text=True, timeout=30
    )

    if result.returncode == 0:
        status = result.stdout.strip()
        print(f"Kernel: {KERNEL_ID}")
        print(f"Status: {status}")
        return status
    else:
        print(f"Status check failed: {result.stderr}")
        return None


def cmd_poll(timeout_minutes=120, interval_seconds=60):
    """Poll kernel status until complete or timeout."""
    if not check_kaggle_cli():
        return False

    print(f"Polling {KERNEL_ID} (timeout: {timeout_minutes}min, interval: {interval_seconds}s)")
    start = time.time()
    deadline = start + timeout_minutes * 60

    while time.time() < deadline:
        result = subprocess.run(
            ["kaggle", "kernels", "status", KERNEL_ID],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            print(f"Status check failed: {result.stderr}")
            time.sleep(interval_seconds)
            continue

        status = result.stdout.strip().lower()
        elapsed = (time.time() - start) / 60
        print(f"[{elapsed:.1f}min] Status: {status}")

        if "complete" in status:
            print("Kernel completed successfully!")
            return True
        elif "error" in status or "cancel" in status:
            print(f"Kernel failed: {status}")
            return False

        time.sleep(interval_seconds)

    print(f"Timeout after {timeout_minutes} minutes.")
    return False


def cmd_output():
    """Download kernel output files."""
    if not check_kaggle_cli():
        return False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading output from {KERNEL_ID} to {OUTPUT_DIR}")
    result = subprocess.run(
        ["kaggle", "kernels", "output", KERNEL_ID, "-p", str(OUTPUT_DIR)],
        capture_output=True, text=True, timeout=300
    )

    if result.returncode == 0:
        print("Output downloaded.")
        print(result.stdout)

        # Check for training summary
        summary_file = OUTPUT_DIR / "training_summary.json"
        if summary_file.exists():
            summary = json.loads(summary_file.read_text())
            print("\nTraining Summary:")
            print(json.dumps(summary, indent=2))

        return True
    else:
        print(f"Download failed: {result.stderr}")
        return False


def cmd_log():
    """View kernel execution log."""
    if not check_kaggle_cli():
        return False

    # Kaggle CLI doesn't have a direct log command, but output includes it
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["kaggle", "kernels", "output", KERNEL_ID, "-p", str(OUTPUT_DIR)],
        capture_output=True, text=True, timeout=300
    )

    log_file = OUTPUT_DIR / "__results__.html"
    if log_file.exists():
        print(f"Log saved to: {log_file}")
        return True

    # Try the notebook log
    log_file2 = OUTPUT_DIR / "output.log"
    if log_file2.exists():
        print(log_file2.read_text()[-5000:])  # Last 5K chars
        return True

    print("No log file found in output.")
    return False


def cmd_run(timeout_minutes=120):
    """Full pipeline: push → poll → download."""
    print("=" * 60)
    print("KAGGLE REMOTE TRAINING — FULL RUN")
    print("=" * 60)

    # Push
    if not cmd_push():
        print("Push failed. Aborting.")
        return False

    # Wait a moment for Kaggle to register the kernel
    print("\nWaiting 30s for Kaggle to queue the kernel...")
    time.sleep(30)

    # Poll
    if not cmd_poll(timeout_minutes=timeout_minutes):
        print("Training did not complete successfully.")
        cmd_output()  # Try to get partial output anyway
        return False

    # Download
    if not cmd_output():
        print("Output download failed.")
        return False

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Output: {OUTPUT_DIR}")
    print(f"Model: https://huggingface.co/issdandavis/scbe-aethermoore-sft-v1")
    return True


def cmd_list():
    """List recent kernel runs."""
    if not check_kaggle_cli():
        return False

    result = subprocess.run(
        ["kaggle", "kernels", "list", "--mine", "--sort-by", "dateRun"],
        capture_output=True, text=True, timeout=30
    )

    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"List failed: {result.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Kaggle Remote Training Automation for SCBE-AETHERMOORE"
    )
    parser.add_argument(
        "command",
        choices=["setup", "push", "status", "poll", "output", "log", "run", "list"],
        help="Command to execute",
    )
    parser.add_argument(
        "--timeout", type=int, default=120,
        help="Poll timeout in minutes (default: 120)",
    )
    parser.add_argument(
        "--interval", type=int, default=60,
        help="Poll interval in seconds (default: 60)",
    )

    args = parser.parse_args()

    commands = {
        "setup": cmd_setup,
        "push": cmd_push,
        "status": cmd_status,
        "poll": lambda: cmd_poll(args.timeout, args.interval),
        "output": cmd_output,
        "log": cmd_log,
        "run": lambda: cmd_run(args.timeout),
        "list": cmd_list,
    }

    success = commands[args.command]()

    if success is False:
        sys.exit(1)


if __name__ == "__main__":
    main()
