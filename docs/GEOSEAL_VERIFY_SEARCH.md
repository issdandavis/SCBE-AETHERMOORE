# GeoSeal Verify Search

GeoSeal verify search separates candidate generation from candidate
verification. The useful pattern is:

1. Generate or run a candidate with local scripts.
2. Verify the candidate with deterministic checks.
3. Write a receipt.
4. Optionally ask local Ollama models for the next candidate/check ideas.

This keeps paid model usage focused on strategy and lets local tooling do the
looping.

## Built-in preset

```powershell
node bin/geoseal.cjs verify-search --preset arc-rubix --json
```

With local Ollama critics:

```powershell
node bin/geoseal.cjs verify-search --preset arc-rubix --ollama-models openclaw:latest,qwen2.5-coder:1.5b --json
```

## Custom manifest shape

```json
{
  "name": "my-search",
  "budget": {
    "max_rounds": 1
  },
  "stop_on_pass": true,
  "candidates": [
    {
      "id": "candidate_1",
      "command": ["python", "scripts/system/some_local_loop.py", "--json"],
      "timeout_seconds": 3600,
      "verify": {
        "returncode": 0,
        "json_fields": [
          {
            "path": "$.ok",
            "equals": true
          }
        ]
      }
    }
  ]
}
```

Run it:

```powershell
node bin/geoseal.cjs verify-search --manifest reports/my_search_manifest.json --json
```

## Output

Default receipt:

```text
reports/geoseal_verify_search_receipt.json
```

The receipt records commands, return codes, check results, stdout/stderr tails,
winning candidate, and optional local Ollama notes.
