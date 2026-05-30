# Hard Agentic Benchmark Pretest

Status: executable pretest matrix, not a public leaderboard claim.

This lane asks a practical question before full public benchmark runs:

> Which hard agentic benchmarks can SCBE execute or prepare for locally, what
> blocks the rest, and what non-leaky assistance would help an agent solve the
> task without handing it the answer?

## Command

```bash
python scripts/benchmark/hard_agentic_benchmark_pretest.py --timeout 180
```

Artifacts:

- `artifacts/benchmarks/hard_agentic_pretest/latest_report.json`
- `artifacts/benchmarks/hard_agentic_pretest/LATEST.md`

## Latest Local Pretest

```text
ready_or_pass=6/13
blocked_or_failed=7/13
```

Passing or ready locally:

- SCBE Local SWE-Style Control: `1.0000`
- SCBE Real-Patch Fixtures: `1.0000`
- SCBE Pathfinding Suite: `0.8125`
- Public Harness Setup: `1.0000`
- BrowseComp setup pretest: ready
- GAIA setup pretest: ready

Blocked locally:

- SWE-bench Verified: missing Docker and SWE-bench harness
- Terminal-Bench: missing Docker and `tb`
- ARC-AGI-2: missing ARC-AGI-2 dataset or checkout
- MLE-bench: missing Kaggle CLI or credentials
- WebArena / VisualWebArena: missing Docker
- OSWorld: missing desktop eval stack
- Vending-Bench: missing Inspect/Vending environment

## Claim Boundary

Allowed:

- SCBE has an executable pretest matrix for hard agentic benchmark readiness.
- SCBE locally passes its SWE-style control lane, real-patch fixture lane, and
  pathfinding suite.
- Several public benchmarks are setup-blocked and are explicitly not claimed.

Not allowed yet:

- Public Terminal-Bench score.
- Public SWE-bench score.
- Public ARC-AGI-2 score.
- Public GAIA/BrowseComp score.
- "Best agentic OS" claim.

## Defender Framing

The useful question is not only "can the agent solve it?" It is:

> What does the task do that keeps agents from reaching 100%, and what support
> can the environment provide without leaking the hidden answer?

The pretest report records this per target as:

- why agents fail,
- how the benchmark defends itself,
- what missing-link assistance is acceptable.

Examples:

- Code repair tasks may reveal failing tests and allowed edit scope, but not the
  gold patch.
- Pathfinding tasks may reveal local sensors, frontier pressure, and uncertainty
  heat maps, but not the hidden global route.
- Web tasks may reveal DOM snapshots, screenshots, and action receipts, but not
  the final click coordinates.
- Research tasks may reveal source requirements and branch ledgers, but not the
  answer string.

## Highest-Value Next Fixes

1. Install or route Docker-backed public harnesses to a GitHub/Linux runner.
2. Add a Terminal-Bench adapter that exposes SCBE as the benchmark agent command.
3. Add ARC-AGI-2 checkout/readiness and run a small public-eval smoke.
4. Add BrowseComp/GAIA mini-subsets using the research bus and evidence ledger.
5. Add a non-leaky hint/assistance schema shared across all benchmark lanes.

## Public Context Sources

- Terminal-Bench: https://terminalbench.lol/
- SWE-bench caution: https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- ARC-AGI-2: https://arcprize.org/arc-agi/2
- MLE-bench: https://openai.com/index/mle-bench/
- BrowseComp: https://openai.com/index/browsecomp/
- GAIA: https://huggingface.co/learn/agents-course/unit4/what-is-gaia
- WebArena: https://arxiv.org/abs/2307.13854
- VisualWebArena: https://arxiv.org/abs/2401.13649
- Vending-Bench: https://arxiv.org/abs/2502.15840
