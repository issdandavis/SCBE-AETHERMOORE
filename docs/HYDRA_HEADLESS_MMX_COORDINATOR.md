# HYDRA Headless MMX Coordinator

Status: active implementation  
Script: `scripts/hydra_headless_mmx_coordinator.py`

## What it does

This runner combines:

- HYDRA headless browser tabs (`MultiTabBrowserLimb`)
- Antivirus membrane scan (`scan_text_for_threats`)
- Multi-model modal matrix reducer (`agents/multi_model_modal_matrix.py`)

to process many URLs in parallel and emit a final decision per URL:

- `ALLOW`
- `QUARANTINE`
- `DENY`

## Run

```powershell
python scripts/hydra_headless_mmx_coordinator.py `
  --urls https://example.com https://github.com `
  --backend playwright `
  --max-tabs 6 `
  --query "scbe hydra browser automation" `
  --output-json artifacts/hydra/mmx_headless_run.json
```

Or file input:

```powershell
python scripts/hydra_headless_mmx_coordinator.py `
  --urls-file examples/urls.json `
  --backend playwright `
  --max-tabs 8
```

## Output shape

- `summary`: backend, tabs, URL count, decision counts
- `results[]` per URL:
  - navigation result/latency
  - content metadata (length/hash/preview)
  - threat scan
  - matrix cells
  - reducer signals and final decision

## Notes

- Designed for rapid parallel sweeps.
- Decision path is deterministic and auditable.
- Uses existing SCBE/HYDRA governance surfaces; does not bypass turnstile logic.

