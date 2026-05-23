# Aether Coding Score / 100

Status: scoring design, not a leaderboard claim.
Last researched: 2026-05-23.

This is the coding-agent scorecard for SCBE/AetherMoore systems. It is meant to work like a food safety grade or Michelin-style rating, but for coding agents: one public number, with the raw evidence still attached.

The rule is simple: no benchmark evidence, no points. A smoke test proves plumbing, not capability.

## Score Formula

```
Aether Coding Score =
  sum(track_weight * normalized_benchmark_score * evidence_multiplier)
```

Evidence multipliers:

| Evidence level | Multiplier | Meaning |
| --- | ---: | --- |
| Official full run | 1.00 | Run through the official harness or accepted leaderboard protocol. |
| Reproducible full local run | 0.85 | Full task set, exact commit, artifacts, logs, cost, and command line. |
| Reproducible subset run | 0.60 | Small but real subset with task IDs and pass/fail artifacts. |
| Smoke/plumbing run | 0.25 | Harness starts and emits artifacts, but capability is not measured. |
| Unrun/planned | 0.00 | Mentioned only as roadmap. |

If a benchmark uses pass rate, use pass rate as the normalized score. If it uses a different metric, normalize to 0-1 and document the conversion in the evidence packet.

## Weighted Tracks

| Track | Weight | Why it matters |
| --- | ---: | --- |
| Real repository repair | 20 | Can the system fix real issues in real codebases? |
| Terminal execution | 15 | Can it operate a shell, inspect state, recover from failures, and verify work? |
| Multi-language editing | 12 | Can it work outside Python and TypeScript? |
| Fresh algorithmic coding | 8 | Can it solve unseen code problems without repo context? |
| Function-level correctness | 5 | Can it write small correct functions with hidden edge cases? |
| Large-context code reasoning | 5 | Can it reason over larger, more complex code tasks? |
| Tool/policy agent behavior | 10 | Can it call tools while obeying business rules and state constraints? |
| Browser/desktop operation | 8 | Can it complete UI workflows across web and desktop surfaces? |
| Security/governance resistance | 12 | Can it resist prompt injection, tool misuse, exfiltration, and policy bypass? |
| Cost/reproducibility evidence | 5 | Can another operator reproduce the score with cost, logs, and artifacts? |
| **Total** | **100** |  |

## Benchmark Map

| Lane | Primary benchmark | Current repo status | First useful SCBE action |
| --- | --- | --- | --- |
| Real repository repair | SWE-bench Verified / SWE-bench Pro | Adapter planned in `docs/benchmarks/PUBLIC_AGENTIC_CLI_BENCHMARK_PLAN.md` | Run a 1-5 task subset with exact patches, tests, cost, and failure cases. |
| Terminal execution | Terminal-Bench 2.0 | Adapter planned | Wrap GeoSeal/agent-bus as the terminal agent and run a small Docker-backed subset remotely. |
| Multi-language editing | Aider Polyglot | One remote scored smoke exists; score was 0 on 1 sampled Rust task | Re-run 1 case with diagnostics, then 3 cases only after edits actually land. |
| Fresh algorithmic coding | LiveCodeBench | Not wired | Add a harness that records problem IDs, generated code, tests, and pass/fail. |
| Function-level correctness | EvalPlus HumanEval+ / MBPP+ | Not wired | Add as a cheap local correctness lane before expensive agent runs. |
| Large-context code reasoning | BigCodeBench / ProjectEval / ProjDevBench | Not wired | Use after the small lanes show signal; expensive and less useful as a first gate. |
| Tool/policy agent behavior | tau-bench / tau2-bench | Not wired | Map SCBE receipts to policy-compliance failures and API action logs. |
| Browser/desktop operation | WebArena / OSWorld | Not wired | Use only after the browser operator is stable; UI benchmarks are brittle and setup-heavy. |
| Security/governance resistance | AgentDojo, CyberSecEval, HarmBench, garak, promptfoo | Partially wired via local SCBE red-team and promptfoo/garak scripts | Keep local SCBE red-team as internal gate, then add one public prompt-injection suite for external comparability. |
| Cost/reproducibility | Internal evidence packet | Partially wired | Every run must emit JSON, Markdown, patches, command line, model/provider, token/cost, and git SHA. |

## Grade Bands

| Score | Grade | Meaning |
| ---: | --- | --- |
| 95-100 | A+ / Grandmaster | Strong public evidence across repo repair, terminal work, multilingual editing, tool policy, and security. Rare. |
| 85-94 | A / Production contender | Good enough to compare against paid coding agents with evidence, not just demos. |
| 75-84 | B / Pilot-ready | Useful for controlled pilots; failures are known and bounded. |
| 60-74 | C / Builder-grade | Works on selected lanes; not ready for broad customer promises. |
| 40-59 | D / Scaffold | Plumbing exists, capability not proven. |
| 0-39 | F / Demo only | Mostly claims, smokes, or isolated local tests. |

## Source Notes

The benchmark choices are based on current public benchmark practice as of 2026-05-23:

- SWE-bench: real GitHub issue repair and the main public software-engineering agent benchmark.
- Terminal-Bench: hard command-line tasks in realistic terminal environments.
- Aider Polyglot: 225 challenging Exercism-based editing tasks across C++, Go, Java, JavaScript, Python, and Rust.
- LiveCodeBench: contamination-aware code generation, repair, execution, and test-output prediction.
- EvalPlus: stronger HumanEval/MBPP hidden-test style function correctness.
- GAIA: general assistant tasks requiring reasoning, retrieval, multimodal inputs, and tool use.
- tau-bench / tau2-bench: multi-turn tool-agent-user interaction with domain policy constraints.
- OSWorld and WebArena: real computer/browser-use benchmarks.
- AgentDojo, CyberSecEval, HarmBench, garak, and promptfoo: security and prompt-injection lanes.

## Claim Guardrails

Do not claim:

- "best coding agent" until the score is backed by official or reproducible full-run evidence across the weighted tracks.
- SWE-bench, Terminal-Bench, Aider Polyglot, LiveCodeBench, or OSWorld parity from a local smoke.
- public leaderboard parity from simulated competitor lanes.
- a single model score as a system score unless the agent harness, tool access, context budget, retry policy, and cost are also recorded.

Allowed claims today:

- "SCBE has a public benchmark plan and local governance/security harnesses."
- "SCBE can produce benchmark evidence packets."
- "The Aether Coding Score defines how we will grade coding-agent capability out of 100."

