#!/usr/bin/env python3
"""
Gumroad OAuth Token Generator
==============================
Handles the OAuth2 flow to get a Gumroad access token.

Usage:
    python scripts/gumroad_oauth.py          # Opens browser + catches callback
    python scripts/gumroad_oauth.py --code CODE  # Exchange an auth code directly

The token is saved to .env.gumroad (gitignored) and printed to stdout.
"""

import http.server
import json
import os
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# App credentials (from Gumroad Settings > Advanced > Applications)
CLIENT_ID = "TaGXwDdl5iFSWiZIDPXweL-cK3r_gIbcQn5jArADlAY"
CLIENT_SECRET = os.environ.get("GUMROAD_CLIENT_SECRET", "")

# After you update the redirect URI in Gumroad settings, use this:
REDIRECT_URI = "http://localhost:8001/oauth/callback"
CALLBACK_PORT = 8001

# Scopes we need
SCOPES = "edit_products view_sales mark_sales_as_shipped refund_sales"

# Where to save the token
TOKEN_FILE = ROOT / ".env.gumroad"


def build_auth_url() -> str:
    """Build the Gumroad OAuth authorization URL."""
    params = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "response_type": "code",
    })
    return f"https://gumroad.com/oauth/authorize?{params}"


def exchange_code(code: str) -> dict:
    """Exchange an authorization code for an access token."""
    secret = CLIENT_SECRET
    if not secret:
        secret = input("Enter your Gumroad Application Secret: ").strip()

    data = urllib.parse.urlencode({
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(
        "https://api.gumroad.com/oauth/token",
        data=data,
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def save_token(token: str):
    """Save token to .env.gumroad file."""
    TOKEN_FILE.write_text(f"GUMROAD_API_TOKEN={token}\n")

    # Also add to .gitignore if not already there
    gitignore = ROOT / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        if ".env.gumroad" not in content:
            with gitignore.open("a") as f:
                f.write("\n# Gumroad API token\n.env.gumroad\n")

    print(f"\n  Token saved to: {TOKEN_FILE}")
    print(f"  Load it with: source .env.gumroad")
    print(f"  Or set manually: export GUMROAD_API_TOKEN={token}")


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handles the OAuth callback from Gumroad."""

    auth_code = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            CallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
            <html><body style="font-family:monospace;text-align:center;padding:50px;background:#1a1a2e;color:#e0e0e0">
            <h1 style="color:#00ff88">Authorization Successful!</h1>
            <p>You can close this tab. The token is being generated...</p>
            <p style="color:#888">SCBE-Aethermoore Publishing Pipeline</p>
            </body></html>
            """)
        else:
            error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><h1>Error: {error}</h1></body></html>".encode())

        # Shutdown after handling
        threading.Thread(target=self.server.shutdown).start()

    def log_message(self, format, *args):
        pass  # Suppress request logs


def run_oauth_flow():
    """Run the full OAuth flow: open browser, catch callback, exchange code."""
    print(f"\n{'='*60}")
    print(f"  GUMROAD OAUTH TOKEN GENERATOR")
    print(f"{'='*60}")

    auth_url = build_auth_url()
    print(f"\n  Opening browser for authorization...")
    print(f"  URL: {auth_url}")
    print(f"\n  Waiting for callback on port {CALLBACK_PORT}...")

    # Start callback server
    server = http.server.HTTPServer(("127.0.0.1", CALLBACK_PORT), CallbackHandler)

    # Open browser
    webbrowser.open(auth_url)

    # Wait for callback (blocks until GET request received)
    server.handle_request()
    server.server_close()

    code = CallbackHandler.auth_code
    if not code:
        print("  ERROR: No authorization code received.")
        return 1

    print(f"  Authorization code received!")
    print(f"  Exchanging for access token...")

    try:
        result = exchange_code(code)
        token = result.get("access_token")
        if token:
            print(f"\n  ACCESS TOKEN: {token}")
            save_token(token)
            print(f"\n  Now run:")
            print(f"    export GUMROAD_API_TOKEN={token}")
            print(f"    python scripts/gumroad_publish.py publish")
            return 0
        else:
            print(f"  ERROR: {json.dumps(result, indent=2)}")
            return 1
    except Exception as e:
        print(f"  ERROR exchanging code: {e}")
        return 1


def exchange_code_direct(code: str):
    """Exchange a code directly (if you already have one)."""
    print(f"  Exchanging code for token...")
    try:
        result = exchange_code(code)
        token = result.get("access_token")
        if token:
            print(f"\n  ACCESS TOKEN: {token}")
            save_token(token)
            return 0
        else:
            print(f"  ERROR: {json.dumps(result, indent=2)}")
            return 1
    except Exception as e:
        print(f"  ERROR: {e}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--code":
        sys.exit(exchange_code_direct(sys.argv[2]))
    elif len(sys.argv) > 1 and sys.argv[1] == "--url":
        print(build_auth_url())
    else:
        sys.exit(run_oauth_flow())
