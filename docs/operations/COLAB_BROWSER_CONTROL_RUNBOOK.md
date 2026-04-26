# Colab Browser Control Runbook

**Status:** operational note  
**Scope:** free or already-paid Colab training lanes for SCBE adapters

## Rule

Colab should be operated through a browser-controlled lane when the run matters. A static notebook file is only the payload. The browser session is the control surface that lets the operator verify runtime state, inspect errors, reconnect, change runtime type, and repair cells.

## Why

- Colab failures are usually interactive: missing `HF_TOKEN` secret, disconnected runtime, no GPU, wrong GPU class, interrupted install, or a stale notebook state.
- A browser-backed lease can verify whether the notebook is open, whether auth is required, whether the runtime is connected, and whether the connect/reconnect control is visible.
- This fits the SCBE rule that training runs are not considered real until the run is verified, error states are captured, and repair is possible.

## Existing Entry Points

```powershell
python scripts\system\colab_workflow_catalog.py list
python scripts\system\colab_workflow_catalog.py show operator-specialty --json
python scripts\system\colab_workflow_catalog.py url operator-specialty
```

Browser-backed worker lease:

```powershell
python scripts\system\colab_worker_lease.py --notebook operator-specialty --no-headless --keep-open
```

Dry run without launching a browser:

```powershell
python scripts\system\colab_worker_lease.py --notebook operator-specialty --dry-run
```

Collect saved Colab receipts into reports and training data:

```powershell
python scripts\training\collect_colab_run_results.py
```

## Saved Run Evidence Already Present

This repo already contains saved Colab interaction evidence. Treat these as prior receipts, not future plans:

| Surface | Evidence path | What it proves |
|---|---|---|
| `scbe-finetune-free` browser smoke | `artifacts/colab_smoke/smoke-20260422T030950Z-scbe-finetune-free/result.json` | Colab notebook opened through the browser lane; cell inventory and runtime probe were captured. |
| `scbe-finetune-free` browser smoke | `artifacts/colab_smoke/smoke-20260422T031543Z-scbe-finetune-free/result.json` | Repeat browser smoke receipt for the same notebook, useful for before/after comparison. |
| `qlora-training` browser smoke | `artifacts/colab_smoke/smoke-20260424T134536Z-qlora-training/result.json` | QLoRA Colab notebook opened through the browser lane; 36 cells and runtime probe captured. |
| `aligned-foundations-qwen-primary` Colab handoff | `artifacts/colab_training_handoffs/aligned-foundations-qwen-primary/20260424T133512Z/colab_training_handoff.json` | Training handoff packet exists with model profile, notebook route, local preflight, and dry-run worker lease. |
| `aligned-foundations-qwen-primary` browser failure receipt | `artifacts/colab_training_handoffs/aligned-foundations-qwen-primary/20260424T133657Z/worker/colab_worker_error.json` | Browser launch failure captured as `playwright_blocked` with `[WinError 5] Access is denied`. |
| `aligned-foundations-qwen-primary` browser failure receipt | `artifacts/colab_training_handoffs/aligned-foundations-qwen-primary/20260424T133806Z/worker/colab_worker_error.json` | Browser dependency failure captured; the remedy was `playwright install`. |
| `aligned-foundations-qwen-primary` verified browser session | `artifacts/colab_training_handoffs/aligned-foundations-qwen-primary/20260424T133913Z/worker/colab-train-aligned-foundations-qwen-primary-20260424T133913Z/worker-colab-train-aligned-foundations-qwen-primary/colab_worker_session.json` | Browser opened `colab_qlora_training.ipynb`, state reached `notebook_open`, runtime probe was captured, and a screenshot path was saved. |

The pattern is already useful: failed Colab control attempts are saved as error receipts, and working attempts save notebook state, runtime probe, URL, screenshot, and relay packet IDs.

## Recovered Inventory Snapshot

The 2026-04-26 collector run recovered `40` local Colab receipts and wrote them into the existing training corpus:

| Output | Path | Use |
|---|---|---|
| JSON report | `artifacts/training_reports/colab_saved_runs_inventory_20260426.json` | Full machine-readable inventory of saved smoke tests, handoffs, worker sessions, execution receipts, run packets, and service logs. |
| Markdown report | `artifacts/training_reports/colab_saved_runs_inventory_20260426.md` | Human-readable status sheet for operator review. |
| SFT records | `training-data/sft/colab_run_evidence_v1.sft.jsonl` | 40 supervised examples teaching the operator to classify Colab receipts and choose next actions. |
| Manifest | `training-data/sft/colab_run_evidence_v1_manifest.json` | Counts and promotion-evidence summary for training inventory. |

Recovered receipt classes:

| Class | Count | Meaning |
|---|---:|---|
| `browser_verified_notebook` | 3 | Colab notebooks opened and cell/runtime probes were captured. |
| `browser_worker_verified` | 2 | Worker browser sessions reached notebook-open state with probe evidence. |
| `browser_worker_blocked` | 2 | Browser or Playwright failure was captured with repair evidence. |
| `handoff_ready` | 1 | Dry-run training handoff packet exists and was preflighted. |
| `handoff_live` | 3 | Live handoff attempts were recorded. |
| `runtime_allocation_only` | 4 | Notebook opened but the runtime stayed in allocation/no-training state. |
| `status_receipt` | 5 | Status snapshots exist for execution attempts. |
| `run_packet` | 17 | Colab run packets exist for profile/session tracking. |
| `service_error` | 2 | Service logs captured blocking errors. |
| `service_result_dump` | 1 | Service log captured a full run/result dump. |

Current hard finding: `promotion_evidence_count` is `0`. The saved Colab data proves browser control, handoff construction, runtime allocation attempts, and failure capture. It does not prove a completed adapter-training run. These records are still valuable because they teach the operator the exact distinction between "opened", "allocated", "failed", and "promotion-ready".

## Verification Receipts

The browser lane should preserve:

- resolved notebook URL with query string and fragment stripped;
- state: `auth_required`, `notebook_open`, `runtime_disconnected`, or `runtime_connected`;
- screenshot path when a real browser session is launched;
- runtime probe fields: usage visibility, machine type, connect button visibility, and sampled button labels.

## Repair Loop

1. Open the notebook through the catalog URL or browser lease.
2. Confirm the notebook belongs to the expected branch/path.
3. Confirm the `HF_TOKEN` Colab secret is available through the Colab secrets sidebar. Do not paste raw tokens into notebook cells.
4. Confirm runtime type is GPU and the notebook reports a supported GPU.
5. Run install/auth/data-load cells first.
6. If a cell fails, capture the error text and fix the cell or builder script before continuing.
7. Only treat the run as launched after the training cell starts and a visible log confirms record count, model name, and output repo.

## Promotion Rule

Colab output is not merge-eligible from notebook completion alone. It still needs the normal adapter registry entry, frozen eval, executable or lane-specific gate, and merge/routing approval.

Saved Colab receipts only become promotion evidence when a receipt contains completed trainer output plus the downstream frozen-eval gate. Browser-open and runtime-allocation receipts are control evidence, not model-quality evidence.
