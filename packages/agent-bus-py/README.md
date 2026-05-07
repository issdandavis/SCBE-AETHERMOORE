# scbe-agent-bus (Python)

Python surface over the SCBE governed event runner. Routes AI/human/AI events
through the harmonic-wall pipeline and returns a typed envelope matching the
`scbe-agentbus-pipe-result-v1` schema used by the Node sibling on npm.

## Install

```bash
pip install scbe-agent-bus
```

## Use as a library

```python
from scbe_agent_bus import run_event, run_batch

result = run_event(
    {"task": "summarize repo state", "task_type": "research"},
    repo_root="/path/to/SCBE-AETHERMOORE",
)
print(result["ok"], result["result"])
```

`repo_root` must point at a checkout of `issdandavis/SCBE-AETHERMOORE` that
contains `scripts/scbe-system-cli.py`. If omitted, defaults to `os.getcwd()`.

## Use as a CLI

```bash
echo '{"task": "summarize repo state"}' | scbe-agent-bus --repo-root .
```

Emits one JSON object per event (JSONL) on stdout, or to `--output PATH`.

## Schema

Every result is a dict matching `scbe-agentbus-pipe-result-v1`:

```python
{
    "schema_version": "scbe-agentbus-pipe-result-v1",
    "event_index": 1,
    "started_at": "2026-05-07T...Z",
    "finished_at": "2026-05-07T...Z",
    "ok": True,
    "exit_code": 0,
    "stderr_tail": "",
    "event": {
        "task_sha256": "...",
        "task_chars": 22,
        "series_id": "pipe-event-1",
        "operation_command_chars": 0,
    },
    "result": { ... },  # underlying scbe-system-cli payload
}
```

## Relationship to the Node package

This package is the Python sibling of [`scbe-agent-bus`](https://www.npmjs.com/package/scbe-agent-bus)
on npm. Both wrap the same underlying Python runner (`scripts/scbe-system-cli.py
agentbus run`) and produce identical envelope shapes. Pick whichever fits your
host environment.

## License

MIT — see `LICENSE`.
