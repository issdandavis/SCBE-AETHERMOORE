# Task Manager intermediary -- client examples

The HTTP server in `tools/taskmgr_server.py` exposes the same data and
actions the GUI uses, so multiple AI models can hit the same endpoints
through one intermediary instead of each calling psutil directly.

## Start the server

```powershell
# Read-open, /kill enabled with token:
python -m tools.taskmgr_server --write-token MY_WRITE_SECRET

# Read-only too:
python -m tools.taskmgr_server --read-token MY_READ_SECRET --write-token MY_WRITE_SECRET

# LAN-exposed (use a write-token!):
python -m tools.taskmgr_server --host 0.0.0.0 --write-token MY_WRITE_SECRET
```

Default bind: `127.0.0.1:8765`.

## Discovery (any model)

```bash
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/tools     # OpenAI-style function descriptors
```

## Read endpoints

```bash
curl http://127.0.0.1:8765/agents | jq .
curl http://127.0.0.1:8765/system | jq .
curl 'http://127.0.0.1:8765/procs?filter=python&top=5' | jq .
curl 'http://127.0.0.1:8765/sample?seconds=2' | jq .
```

## Write endpoint (kill a process; requires --write-token)

```bash
# Dry-run first (always recommended):
curl -X POST http://127.0.0.1:8765/kill \
  -H "Authorization: Bearer MY_WRITE_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"pid": 1234, "tree": true, "dry_run": true}'

# Execute:
curl -X POST http://127.0.0.1:8765/kill \
  -H "Authorization: Bearer MY_WRITE_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"pid": 1234, "tree": true}'
```

## Python client

```python
import urllib.request, json
def call(path, body=None, token=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:8765{path}",
        method="POST" if body else "GET",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode()
    with urllib.request.urlopen(req, data=data, timeout=10) as r:
        return r.status, json.loads(r.read())

print(call("/agents"))
print(call("/sample?seconds=1"))
print(call("/kill", {"pid": 1234, "dry_run": True}, token="MY_WRITE_SECRET"))
```

## Hooking into a function-calling model

`/tools` returns descriptors shaped like OpenAI function-calling /
Claude tool-use, so most models can consume them directly. Pseudocode
for a Claude tool-use loop:

```python
import anthropic, urllib.request, json

def fetch_tools():
    with urllib.request.urlopen("http://127.0.0.1:8765/tools") as r:
        return json.loads(r.read())["tools"]

def call_tool(name, args, write_token=None):
    tool = next(t for t in fetch_tools() if t["name"] == name)
    method, path = tool["endpoint"]["method"], tool["endpoint"]["path"]
    if method == "GET":
        qs = "&".join(f"{k}={v}" for k, v in args.items())
        url = f"http://127.0.0.1:8765{path}" + (f"?{qs}" if qs else "")
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(
            f"http://127.0.0.1:8765{path}", method="POST",
            data=json.dumps(args).encode(),
            headers={"Content-Type": "application/json"},
        )
        if write_token:
            req.add_header("Authorization", f"Bearer {write_token}")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

# Send `fetch_tools()` to your model as the tool list, then route any
# tool_use blocks the model emits through `call_tool`.
```

## SCBE n8n bridge route (live)

`workflows/n8n/scbe_n8n_bridge.py` now exposes `tools.taskmgr_core` directly
under the `/v1/taskmgr/*` prefix, so every n8n workflow + every model that
already uses the bridge gets task-manager access without a second host.

```
n8n workflow -> /v1/taskmgr/{action} -> bridge -> tools.taskmgr_core
```

Auth model:
- All routes require the bridge `x-api-key` header (`SCBE_API_KEYS`).
- `/v1/taskmgr/kill` additionally requires `SCBE_TASKMGR_WRITE=1` in the
  bridge's env, so a leaked read key cannot terminate processes.

Example calls:

```bash
K="$SCBE_API_KEYS"

curl -H "x-api-key: $K" http://127.0.0.1:8001/v1/taskmgr/scbe
curl -H "x-api-key: $K" http://127.0.0.1:8001/v1/taskmgr/agents
curl -H "x-api-key: $K" "http://127.0.0.1:8001/v1/taskmgr/procs?top=5"
curl -H "x-api-key: $K" "http://127.0.0.1:8001/v1/taskmgr/sample?seconds=1"

# Kill (only with SCBE_TASKMGR_WRITE=1):
curl -X POST -H "x-api-key: $K" -H "Content-Type: application/json" \
     -d '{"pid": 1234, "dry_run": true}' \
     http://127.0.0.1:8001/v1/taskmgr/kill
```

The standalone `tools.taskmgr_server` is still useful for fleets that don't
have the bridge running — pick whichever fits the deployment.
