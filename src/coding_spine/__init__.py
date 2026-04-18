"""
SCBE Coding Spine
=================
Atomic-tokenizer-driven coding agent for SCBE-AETHERMOORE.

Entry point: `python -m src.geoseal_cli agent "<task>"`

Architecture:
    router.py       — AtomicTokenState trit aggregation → dominant tongue
    polly_client.py — Polly (local vLLM) or Claude API fallback
    shared_ir.py    — minimal canonical semantic IR for dual-strand agreement
    geoseal_cli.py  — `agent` subcommand wires everything together
"""
