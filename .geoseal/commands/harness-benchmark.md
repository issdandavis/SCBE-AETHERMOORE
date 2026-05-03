---
name: harness-benchmark
description: Run the local GeoSeal harness benchmark and release-readiness checks.
---

Run the evidence-backed GeoSeal harness checks from the repository root:

```powershell
python scripts/benchmark/cli_competitive_benchmark.py --json
python scripts/ci/harness_release_readiness.py --json
```

Use this command template when a coding agent needs a small, repeatable proof
packet for the GeoSeal command-line interface harness.
