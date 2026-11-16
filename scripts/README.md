# scripts/

Automation scripts: close to a thousand tracked files, about 370 of them directly in this folder. New scripts belong in a subfolder; command logic that ships to users belongs in `packages/`.

## Subfolders

| Folder | Files | Purpose |
|--------|------:|---------|
| `system/` | 249 | Multi-agent operations: dispatch, audits, ledgers, GitHub sweeps, repo review |
| `benchmark/` | 90 | Benchmark adapters and drivers for external suites |
| `eval/` | 37 | Evaluation builders and scorers for trained adapters |
| `publish/` | 21 | Publishing: article-to-video, cross-posting, print (KDP) proof builders |
| `windows/` | 13 | Windows batch build and packaging scripts |
| `apollo/` | 12 | Email triage agent |
| `experiments/` | 12 | One-off experiments (tokenizer, braid routing) |
| `ci/` | 10 | CI failure detection, auto-fix dispatch, determinism scan |
| `research/` | 10 | Research simulators and logging |
| `security/` | 10 | Artifact triage, alert fusion, code governance gate |
| `training/`, `train/`, `training_data/` | 17 | Training-corpus builders and training launchers |
| `kaggle/`, `kaggle_auto/`, `hf_jobs/` | 18 | Kaggle and Hugging Face Jobs launchers |
| `mountain_map/` | 8 | Cross-language construct table and map |
| `wildlife/` | 7 | "Wildlife Board" work-organisation model |
| `repo_reorg/` | 6 | The phased 2026-04 repository reorganisation |
| `benchmarks/` | 6 | AST cube encoder and round-trip benchmarks |
| `sandbox/` | 5 | Throwaway Docker sandbox for the GeoSeal gate. Has a README |
| `aetherpp/`, `dsl/` | 8 | Aether++ parser and lowering; DSL holdout audits |
| `video/`, `video_lattice/`, `youtube/`, `audiobook/` | 10 | Media packaging, quality gates, upload |
| `revenue/`, `outreach/`, `mail/`, `social/` | 10 | Sales, outreach, and mailbox utilities |
| `vercel/` | 3 | Generates and verifies `api/agent/router.js` and `api/polly/router.js` |
| `hooks/`, `git-hooks/` | 3 | Git hooks; install with `npm run hooks:install` |
| `docs/` | 1 | `build_file_index.py`, which generates `docs/file-index/` |
| others | — | `agents/`, `polly/`, `powershell/`, `gitlab/`, `mcp_rooms/`, `knowledge/`, `legal/`, `kdp/`, `encoding/`, `bootstrap/`, `aetherbrowser/`, `unix/`, and single-script folders |

## Root-level scripts

Named by verb: `build_*` (36), `generate_*` (34), `run_*` (28), `train_*` (13), `scbe_*` (11), then `test_*`, `gen_*`, `forge_*`, `setup_*`, `arxiv_*`.

About one script in five has no docstring or header comment; the file index lists the functions each of those defines.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/scripts.md`](../docs/file-index/scripts.md).
