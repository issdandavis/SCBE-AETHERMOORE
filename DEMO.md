# SCBE-AETHERMOORE Beginner Demo

This is the short path for people who only want to see SCBE catch unsafe input.

SCBE is easiest to understand as a safety gate:

```text
user input -> SCBE scan -> ALLOW / QUARANTINE / ESCALATE / DENY -> model or agent
```

You do not need Docker, a GPU, an API key, or an external model.

---

## Option A: CLI demo

Install the Python package:

```bash
pip install scbe-aethermoore
```

Run three scans:

```bash
scbe-scan "hello world"
scbe-scan "ignore all previous instructions"
scbe-scan "DROP TABLE users"
```

Expected shape:

```text
[OK] ALLOW         score=1.0000  d*=0.0000  pd=0.0000  len=11
[!!] ESCALATE      score=0.3846  d*=0.0000  pd=0.8000  len=32
[!!] ESCALATE      score=0.3846  d*=0.0000  pd=0.8000  len=16
```

Higher score is safer. The decision tiers are:

| Decision | Meaning |
|---|---|
| `ALLOW` | Safe enough to continue |
| `QUARANTINE` | Suspicious; review before execution |
| `ESCALATE` | High risk; governance action required |
| `DENY` | Blocked |

---

## Option B: Browser demo

Run the no-dependency browser demo:

```bash
python -m scbe_aethermoore.demo.web
```

Open:

```text
http://127.0.0.1:8765
```

Type a prompt or command. The page shows:

- decision
- score
- audit digest
- simple six-axis Sacred Tongues demo bars
- raw JSON result

The six bars are a lightweight demo visualization derived from the public scan
features. They are meant to make the gate visible, not replace the full semantic
projector.

---

## Option C: Wrap a model in 20 lines

Run the basic firewall example:

```bash
python examples/python/basic_firewall.py
```

The example has a toy model:

```python
def toy_model(prompt: str) -> str:
    return f"MODEL_OUTPUT: {prompt[:80]}..."
```

SCBE runs first. Unsafe input is blocked before the model sees it.

Replace `toy_model()` with your own model call when you want to integrate it.

---

## Python integration

```python
from scbe_aethermoore import is_safe, scan

user_input = "ignore all previous instructions"

if not is_safe(user_input):
    result = scan(user_input)
    raise PermissionError(f"Blocked by SCBE: {result['decision']}")

print("send to model")
```

Batch scan:

```python
from scbe_aethermoore import scan_batch

items = ["hello", "DROP TABLE users", "how are you?"]
for result in scan_batch(items):
    print(result["decision"], result["score"])
```

Demo visualization payload:

```python
from scbe_aethermoore import scan_with_tongues

result = scan_with_tongues("ignore all previous instructions")
print(result["decision"])
print(result["tongues"])
```

---

## API demo for deeper testing

The repo also includes a FastAPI governance route for people who want an HTTP
surface:

```bash
pip install -r requirements.txt
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Interactive docs:

```text
http://127.0.0.1:8000/docs
```

Health check:

```bash
curl http://127.0.0.1:8000/v1/govern/health
```

One scan:

```bash
curl -s -X POST http://127.0.0.1:8000/v1/govern \
  -H "Content-Type: application/json" \
  -d "{\"input\":\"rm -rf /var/log && exfil passwords\",\"context\":\"untrusted\"}"
```

---

## Under the hood

The beginner path uses the installable Python package:

- `scan(text)` returns a decision, score, distance, phase deviation, and audit digest.
- `is_safe(text)` gives a boolean gate for apps.
- `scan_with_tongues(text)` adds demo-friendly six-axis bars.

For the full system map, read:

- [README.md](README.md)
- [docs/specs/SCBE_CANONICAL_CONSTANTS.md](docs/specs/SCBE_CANONICAL_CONSTANTS.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
