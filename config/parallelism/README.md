# Parallelism Workflow Specs

This folder contains workflow specs for `scripts/system/parallelism_system.py`.

## HF Coding-Agent v8 Production Lane

Spec: `config/parallelism/hf_coding_agent_v8_production.json`

This lane runs:
- A Hugging Face / TRL / PEFT research search job.
- A bijective-coding research search job.
- A local preflight shell job that verifies key coding-agent v8 files are present.

Run with one command from repo root:

```powershell
python scripts/system/parallelism_system.py run --spec config/parallelism/hf_coding_agent_v8_production.json --workers 3
```

Artifacts are written under:

`artifacts/parallelism_system/<lane-name>-<utc-stamp>/`
