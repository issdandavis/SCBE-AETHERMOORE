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
ready_or_pass=12/14
blocked_or_failed=2/14
```

Executed and passing locally:

- SCBE Local SWE-Style Control: `1.0000`
- SCBE Real-Patch Fixtures: `1.0000`
- SCBE Pathfinding Suite: `0.8125`
- Public Harness Setup: `1.0000`
- BrowseComp-style research fixture: `1.0000`
- GAIA-style research fixture: `1.0000`
- Rubix Browser Hypercube fixture: `1.0000`

Setup-ready locally, not public scores:

- ARC-AGI-2: local dataset/check readiness passed
- MLE-bench: Kaggle CLI and local ML stack readiness passed
- WebArena / VisualWebArena: Docker/Podman and Playwright readiness passed
- OSWorld: desktop eval stack readiness passed
- Vending-Bench: Inspect/Vending environment readiness passed

Blocked locally:

- SWE-bench Verified: missing SWE-bench harness
- Terminal-Bench: missing `tb`

## Claim Boundary

Allowed:

- SCBE has an executable pretest matrix for hard agentic benchmark readiness.
- SCBE locally passes its SWE-style control lane, real-patch fixture lane, and
  pathfinding suite.
- SCBE locally passes BrowseComp-style and GAIA-style evidence fixture lanes.
- SCBE locally passes a Rubix Browser Hypercube fixture that models browser
  control as permission-defined geometric routing.
- Several public benchmarks are setup-blocked and are explicitly not claimed.

Not allowed yet:

- Public Terminal-Bench score.
- Public SWE-bench score.
- Public ARC-AGI-2 score.
- Public GAIA/BrowseComp score.
- Public WebArena, VisualWebArena, BrowserGym, or OSWorld score.
- "Best agentic OS" claim.

## Defender Framing

The useful question is not only "can the agent solve it?" It is:

> What does the task do that keeps agents from reaching 100%, and what support
> can the environment provide without leaking the hidden answer?

The pretest report records this per target as:

- why agents fail,
- how the benchmark defends itself,
- what missing-link assistance is acceptable.

The shared capability under test is context retention through deferred work:

- stateful reasoning across tool calls,
- multi-step reasoning across partial observations,
- deferred subgoals that survive after another lane runs,
- task-stack continuity when a parent goal branches into child tasks,
- tool-routing memory, including which provider/tool was used and why,
- tool looping with progress checks, so repeated calls must add evidence,
  reduce uncertainty, or trigger recovery instead of spinning,
- permission-boundary memory, including denied actions and required approvals,
- provenance continuity from prompt to action to artifact,
- recoverability after interruption or failed attempts,
- cost/latency awareness when choosing local, free-tier, or paid routes,
- receipts proving that the agent did not merely answer, but carried state into
  the next executable step.

Examples:

- Code repair tasks may reveal failing tests and allowed edit scope, but not the
  gold patch.
- Pathfinding tasks may reveal local sensors, frontier pressure, and uncertainty
  heat maps, but not the hidden global route.
- Web tasks may reveal DOM snapshots, screenshots, permission faces, and action
  receipts, but not the final click coordinates.
- Research tasks may reveal source requirements and branch ledgers, but not the
  answer string.

## Highest-Value Next Fixes

1. Install `tb` and add a Terminal-Bench adapter that exposes SCBE as the
   benchmark agent command.
2. Install the SWE-bench harness or route official SWE-bench work to a
   GitHub/Linux runner.
3. Convert the Rubix Browser Hypercube receipts into a Playwright local-page
   fixture, then a BrowserGym/WebArena adapter.
4. Run a small ARC-AGI-2 public-eval smoke from the local checkout.
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
- BrowserGym: https://github.com/ServiceNow/BrowserGym
- Vending-Bench: https://arxiv.org/abs/2502.15840
- ASI:One developer docs: https://docs.asi1.ai/docs
- ASI:One MCP CLI package: https://pypi.org/project/asi1-mcp-cli/
