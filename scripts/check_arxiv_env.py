"""check_arxiv_env.py -- confirm the arXiv key loaded, WITHOUT printing it.

A secret you have to echo to verify is a secret you have leaked into scrollback,
shell history, and any log that captured the run. This reports presence, length,
and a short salted fingerprint instead -- enough to tell "loaded" from "not
loaded", and enough to tell two different keys apart, without revealing either.

    python scripts/check_arxiv_env.py
"""

from __future__ import annotations

import hashlib
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# Load .env.local / .env if python-dotenv is available; otherwise rely on the
# environment already being populated.
def _load() -> str:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return "python-dotenv not installed -- reading the live environment only"
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    loaded = []
    for name in (".env.local", ".env"):
        p = os.path.join(here, name)
        if os.path.isfile(p):
            load_dotenv(p, override=False)
            loaded.append(name)
    return "loaded: " + (", ".join(loaded) if loaded else "no .env file found")


def fingerprint(value: str) -> str:
    """Short digest so two keys can be told apart without either being shown."""
    return hashlib.sha256(("arxiv-env-check:" + value).encode()).hexdigest()[:12]


def main() -> int:
    print("  " + _load())
    key = os.environ.get("ARXIV_API_KEY", "")
    provider = os.environ.get("ARXIV_API_PROVIDER", "")
    base = os.environ.get("ARXIV_API_BASE", "")

    print()
    if not key:
        print("  ARXIV_API_KEY      NOT SET")
        print()
        print("  If you only need arXiv's own public API this is fine -- it takes")
        print("  no key. Set the key only for the service that actually issued it.")
    else:
        print("  ARXIV_API_KEY      set   len=%d   fingerprint=%s" % (len(key), fingerprint(key)))
        if key.strip() != key:
            print("      WARNING: leading/trailing whitespace -- a very common cause of 401s")
        if key.startswith("<") or "your-key" in key.lower() or "paste" in key.lower():
            print("      WARNING: this still looks like the placeholder, not a real key")
    print("  ARXIV_API_PROVIDER %s" % (provider or "NOT SET  (name the issuing service)"))
    print("  ARXIV_API_BASE     %s" % (base or "NOT SET"))

    print()
    # A key in a file that git can see is the failure mode worth catching early.
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    import subprocess

    for name in (".env.local", ".env"):
        p = os.path.join(here, name)
        if not os.path.isfile(p):
            continue
        r = subprocess.run(["git", "check-ignore", "-q", name], cwd=here, capture_output=True)
        state = "IGNORED by git (safe)" if r.returncode == 0 else "*** TRACKED BY GIT -- FIX THIS ***"
        print("  %-12s %s" % (name, state))
    return 0 if key else 1


if __name__ == "__main__":
    raise SystemExit(main())
