"""Training extension CLI surface for scbe-system-cli.

Subcommands:
- status     : unified read of local runs + recent verdicts + heartbeat (no network)
- runs       : list local training runs under training/runs/
- verdicts   : list recent run verdicts with pass/fail and scaffold flag
- heartbeat  : show the night-training-watch rolling heartbeat line
- guide      : built-in guides (sft, dpo, lora, merge, datasets, hf-jobs, kaggle, scbe-stack)
- quickstart : print the dispatch command for a new HF Job (does not execute)

Usage from the unified CLI:
    python scripts/scbe-system-cli.py training status

Usage standalone:
    python -m src.training_cli status
"""

from __future__ import annotations

from src.training_cli.cli import build_parser, main

__all__ = ["build_parser", "main"]
