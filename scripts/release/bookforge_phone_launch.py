from __future__ import annotations

import argparse
import http.server
import socket
import socketserver
import sys
import webbrowser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
APP_PAGE = "bookforge-writing-studio.html"


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())
    finally:
        sock.close()


def write_phone_card(url: str, port: int) -> Path:
    out = REPO_ROOT / "artifacts" / "release" / "bookforge-phone-launch.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Bookforge Phone Launch</title>
    <style>
      body {{ margin: 0; font: 18px/1.5 system-ui, sans-serif; background: #f7f1e6; color: #18211f; }}
      main {{ width: min(760px, calc(100% - 32px)); margin: 0 auto; padding: 48px 0; }}
      a {{ color: #8b3b41; font-weight: 800; }}
      .card {{ border: 1px solid rgba(24, 33, 31, .18); border-radius: 12px; background: #fffdf8; padding: 22px; }}
      code {{ display: block; overflow-wrap: anywhere; margin-top: 12px; padding: 12px; background: #f0d9b5; border-radius: 8px; }}
    </style>
  </head>
  <body>
    <main>
      <h1>Bookforge is running</h1>
      <div class="card">
        <p>Open this URL on your phone while it is on the same Wi-Fi network:</p>
        <p><a href="{url}">{url}</a></p>
        <code>{url}</code>
        <p>Then use your browser menu: <strong>Add to Home Screen</strong> / <strong>Install app</strong>.</p>
        <p>If your phone cannot reach it, confirm both devices are on the same Wi-Fi and Windows Firewall allows Python on port {port}.</p>
      </div>
    </main>
  </body>
</html>
""",
        encoding="utf-8",
    )
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve Bookforge Studio on the LAN for phone testing.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--open-card", action="store_true", help="Open the local launch card in the desktop browser.")
    parser.add_argument("--card-only", action="store_true", help="Write the launch card and print URLs without starting a server.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    page = DOCS_DIR / APP_PAGE
    if not page.exists():
        print(f"missing {page}", file=sys.stderr)
        return 2

    ip = lan_ip()
    url = f"http://{ip}:{args.port}/{APP_PAGE}"
    local_url = f"http://127.0.0.1:{args.port}/{APP_PAGE}"
    card = write_phone_card(url, args.port)
    if args.open_card:
        webbrowser.open(card.resolve().as_uri())

    print("Bookforge Studio phone launch", flush=True)
    print("==============================", flush=True)
    print(f"Phone URL : {url}", flush=True)
    print(f"Local URL : {local_url}", flush=True)
    print(f"Launch card: {card}", flush=True)
    print("", flush=True)
    print("On phone: open the Phone URL on the same Wi-Fi, then Add to Home Screen / Install app.", flush=True)
    print("Note: full PWA service-worker install needs HTTPS after deployment; local LAN is for immediate phone testing.", flush=True)
    if args.card_only:
        return 0

    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(DOCS_DIR), **kw)
    try:
        server = ReusableTCPServer((args.host, args.port), handler)
    except OSError as exc:
        print(f"Could not bind {args.host}:{args.port}: {exc}", file=sys.stderr, flush=True)
        print("Try another port, for example: python scripts/release/bookforge_phone_launch.py --port 8766", file=sys.stderr, flush=True)
        return 3

    with server:
        print("Press Ctrl+C here to stop the server.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
