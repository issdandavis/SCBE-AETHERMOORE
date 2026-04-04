#!/usr/bin/env python3
"""
Post to X/Twitter via the X API v2.

Supports:
- OAuth 2.0 PKCE user-context tokens (access/refresh)
- OAuth 1.0a user-context tokens (API key/secret + access token/secret)

Usage:
    python scripts/publish/post_to_x.py --auth          # One-time: authorize and get access token
    python scripts/publish/post_to_x.py --text "Hello"   # Post a single tweet
    python scripts/publish/post_to_x.py --thread file.md  # Post a thread
    python scripts/publish/post_to_x.py --thread file.md --dry-run

Environment (from config/connector_oauth/.env.connector.oauth):
    OAuth 2.0:
      X_CLIENT_ID            - OAuth 2.0 Client ID
      X_CLIENT_SECRET        - OAuth 2.0 Client Secret
      X_ACCESS_TOKEN         - User access token (set after --auth)
      X_REFRESH_TOKEN        - Refresh token (set after --auth)

    OAuth 1.0a:
      X_API_KEY              - Consumer/API key
      X_API_SECRET           - Consumer/API secret
      X_ACCESS_TOKEN         - User access token
      X_ACCESS_TOKEN_SECRET  - User access token secret
"""
import argparse
import base64
import hashlib
import http.server
import hmac
import json
import os
import re
import secrets
import ssl
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
TOKEN_FILE = REPO_ROOT / "config" / "connector_oauth" / ".x_tokens.json"
ENV_FILE = REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth"

AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"
TWEET_URL = "https://api.x.com/2/tweets"
REDIRECT_URI = "http://127.0.0.1:8921/callback"
SCOPES = "tweet.read tweet.write users.read offline.access"


def _is_present(value: str) -> bool:
    return bool(value and value != "REPLACE_ME")


def _pct(value: str) -> str:
    return urllib.parse.quote(value, safe="~-._")


def _build_oauth1_auth_header(
    method: str, url: str, consumer_key: str, consumer_secret: str, token: str, token_secret: str
) -> str:
    parsed = urllib.parse.urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)

    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }

    sig_pairs: list[tuple[str, str]] = []
    sig_pairs.extend((k, v) for k, v in query_params)
    sig_pairs.extend((k, v) for k, v in oauth_params.items())
    sig_pairs.sort(key=lambda kv: (_pct(kv[0]), _pct(kv[1])))

    parameter_string = "&".join(f"{_pct(k)}={_pct(v)}" for k, v in sig_pairs)
    signature_base = "&".join(
        [
            method.upper(),
            _pct(base_url),
            _pct(parameter_string),
        ]
    )
    signing_key = f"{_pct(consumer_secret)}&{_pct(token_secret)}"
    oauth_signature = base64.b64encode(
        hmac.new(signing_key.encode("utf-8"), signature_base.encode("utf-8"), hashlib.sha1).digest()
    ).decode("ascii")

    oauth_params["oauth_signature"] = oauth_signature
    parts = ", ".join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth_params.items(), key=lambda kv: kv[0]))
    return f"OAuth {parts}"


def get_oauth1_credentials():
    """Return OAuth 1.0a credentials tuple if fully configured."""
    api_key = os.environ.get("X_API_KEY", "") or os.environ.get("X_CONSUMER_KEY", "")
    api_secret = os.environ.get("X_API_SECRET", "") or os.environ.get("X_CONSUMER_SECRET", "")
    access = os.environ.get("X_ACCESS_TOKEN", "")
    access_secret = os.environ.get("X_ACCESS_TOKEN_SECRET", "")

    if all(_is_present(v) for v in (api_key, api_secret, access, access_secret)):
        return api_key, api_secret, access, access_secret
    return None


def load_env():
    """Load credentials from .env files if not in environment."""
    env_files = [str(ENV_FILE), str(REPO_ROOT / ".env")]
    for f in env_files:
        if os.path.exists(f):
            with open(f, "r") as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if v != "REPLACE_ME" and k not in os.environ:
                            os.environ[k] = v


def load_tokens():
    """Load saved access/refresh tokens."""
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {}


def save_tokens(tokens):
    """Persist access/refresh tokens to disk (gitignored)."""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2), "utf-8")
    print(f"  Tokens saved to {TOKEN_FILE}")


def get_access_token():
    """Get a valid access token, refreshing if needed."""
    tokens = load_tokens()
    access = tokens.get("access_token") or os.environ.get("X_ACCESS_TOKEN", "")
    if _is_present(access):
        return access

    refresh = tokens.get("refresh_token") or os.environ.get("X_REFRESH_TOKEN", "")
    if _is_present(refresh):
        new_tokens = refresh_access_token(refresh)
        if new_tokens:
            return new_tokens.get("access_token", "")

    print("ERROR: No access token. Run: python scripts/publish/post_to_x.py --auth")
    return ""


def refresh_access_token(refresh_token):
    """Use refresh token to get a new access token."""
    client_id = os.environ.get("X_CLIENT_ID", "")
    client_secret = os.environ.get("X_CLIENT_SECRET", "")
    if not client_id:
        return None

    data = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        }
    ).encode("utf-8")

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    if client_secret:
        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")

    try:
        ctx = ssl.create_default_context()
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        tokens = json.loads(resp.read().decode())
        save_tokens(tokens)
        print("  Access token refreshed.")
        return tokens
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  Refresh failed {e.code}: {body[:300]}")
        return None


def do_auth():
    """Run the full OAuth 2.0 PKCE authorization flow."""
    client_id = os.environ.get("X_CLIENT_ID", "")
    client_secret = os.environ.get("X_CLIENT_SECRET", "")
    if not client_id:
        print("ERROR: X_CLIENT_ID not set in env or .env.connector.oauth")
        return

    # Generate PKCE verifier + challenge
    code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    state = secrets.token_urlsafe(32)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    print("Opening browser for X authorization...")
    print(f"URL: {auth_url}\n")
    webbrowser.open(auth_url)

    # Start local server to catch callback
    auth_code = [None]

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            if qs.get("state", [None])[0] != state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"State mismatch")
                return
            auth_code[0] = qs.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization successful!</h1><p>You can close this tab.</p>")

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 8921), CallbackHandler)
    print("Waiting for callback on http://127.0.0.1:8921/callback ...")
    server.handle_request()
    server.server_close()

    if not auth_code[0]:
        print("ERROR: No authorization code received.")
        return

    print(f"  Got authorization code: {auth_code[0][:10]}...")

    # Exchange code for tokens
    data = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": auth_code[0],
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "code_verifier": code_verifier,
        }
    ).encode("utf-8")

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    if client_secret:
        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")

    try:
        ctx = ssl.create_default_context()
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        tokens = json.loads(resp.read().decode())
        save_tokens(tokens)
        print(f"\n  Access token obtained!")
        print(f"  Scopes: {tokens.get('scope', 'unknown')}")
        print(f"  Expires in: {tokens.get('expires_in', '?')}s")
        if tokens.get("refresh_token"):
            print("  Refresh token saved for auto-renewal.")
        print("\nYou can now post tweets with: --text or --thread")
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  Token exchange failed {e.code}: {body[:300]}")


def post_tweet(text, reply_to=None):
    """Post a single tweet via X API v2 with user context."""
    oauth1 = get_oauth1_credentials()
    if oauth1:
        return post_tweet_oauth1(text, reply_to=reply_to, creds=oauth1)

    # Fallback to OAuth 2.0 PKCE user-context bearer token.
    token = get_access_token()
    if not token:
        return None

    payload = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}

    data = json.dumps(payload).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(TWEET_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")

    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        result = json.loads(resp.read().decode())
        tweet_id = result.get("data", {}).get("id")
        print(f"  Posted tweet {tweet_id}")
        return tweet_id
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  ERROR {e.code}: {body[:300]}")
        if e.code == 401:
            print("  Token may be expired. Try: --auth to re-authorize")
        return None


def post_tweet_oauth1(text, reply_to=None, creds=None):
    """Post a single tweet via OAuth 1.0a user context."""
    if creds is None:
        creds = get_oauth1_credentials()
    if not creds:
        return None

    api_key, api_secret, access, access_secret = creds
    payload = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}

    data = json.dumps(payload).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(TWEET_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header(
        "Authorization",
        _build_oauth1_auth_header("POST", TWEET_URL, api_key, api_secret, access, access_secret),
    )

    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        result = json.loads(resp.read().decode())
        tweet_id = result.get("data", {}).get("id")
        print(f"  Posted tweet {tweet_id}")
        return tweet_id
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  ERROR {e.code}: {body[:300]}")
        return None


def parse_thread_file(filepath):
    """Parse a thread markdown file into individual tweets."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    tweets = []
    parts = re.split(r"^## \d+/\d+\s*\n", content, flags=re.MULTILINE)

    for part in parts:
        part = part.strip()
        if not part or part.startswith("---") or part.startswith("#"):
            continue
        text = part.strip()
        if len(text) > 280:
            text = text[:277] + "..."
        if text:
            tweets.append(text)

    return tweets


def post_thread(filepath, dry_run=False):
    """Post a thread from a markdown file."""
    tweets = parse_thread_file(filepath)
    if not tweets:
        print("No tweets found in file")
        return False

    print(f"Thread: {len(tweets)} tweets")
    print("=" * 60)

    reply_to = None
    success = True
    for i, tweet in enumerate(tweets):
        print(f"\n--- Tweet {i+1}/{len(tweets)} ({len(tweet)} chars) ---")
        print(tweet)

        if dry_run:
            print("  [DRY RUN - not posted]")
            continue

        tweet_id = post_tweet(tweet, reply_to=reply_to)
        if tweet_id:
            reply_to = tweet_id
            if i < len(tweets) - 1:
                time.sleep(2)
        else:
            print("  FAILED - stopping thread")
            success = False
            break

    print("\n" + "=" * 60)
    if dry_run:
        print(f"DRY RUN complete. {len(tweets)} tweets ready.")
        return True
    if success:
        print(f"Thread posted. {len(tweets)} tweets.")
    else:
        print(f"Thread failed. Posted fewer than {len(tweets)} tweets.")
    return success


def main():
    parser = argparse.ArgumentParser(description="Post to X/Twitter via OAuth 2.0 PKCE")
    parser.add_argument("--auth", action="store_true", help="Run OAuth 2.0 authorization flow")
    parser.add_argument("--text", help="Single tweet text")
    parser.add_argument("--thread", help="Thread markdown file")
    parser.add_argument("--dry-run", action="store_true", help="Show tweets without posting")
    args = parser.parse_args()

    load_env()

    if args.auth:
        do_auth()
        return 0
    if args.thread:
        ok = post_thread(args.thread, dry_run=args.dry_run)
        return 0 if ok else 1
    if args.text:
        if args.dry_run:
            print(f"[DRY RUN] Would post: {args.text}")
            return 0
        return 0 if post_tweet(args.text) else 1
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
