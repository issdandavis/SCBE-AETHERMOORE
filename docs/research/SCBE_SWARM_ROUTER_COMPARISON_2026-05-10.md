# SCBE Swarm Router Comparison — 2026-05-10

Question: after wiring local and Ollama Cloud model lanes, what are we still
missing compared with nearby coding-agent systems?

## Current Finding

The SCBE swarm router now resolves local, Ollama Launch, and Ollama Cloud lanes
under one artifact contract. The important result from the latest cloud
benchmark is not that the cloud lanes passed; they did not. The useful result is
that the router rejected confident but non-applicable cloud proposals that
invented files or wrapper symbols.

That is the right failure mode. A multi-agent coding system should block a bad
proposal cheaply before it reaches `safe_apply`, even when the text sounds
credible.

## System Comparison

| System class | Strong at | Weak at | SCBE router role |
|---|---|---|---|
| Ollama Launch tools | Fast access to many terminal agents through one local command surface | Launch wrapper does not guarantee repo-grounded patches | Treat as dispatch surfaces, not truth sources |
| OpenClaw | Local bootstrap/router behavior and simple terminal operation | Can be weak when the underlying local model is small | Use as local coordinator and cheap first-pass proposer |
| OpenCode / Codex / Droid style agents | Patch proposal and repo navigation when model and tool loop are strong | Can hallucinate symbols or assume a different repo shape | Route as geometry roles, then validate against actual files |
| Hermes-style agents | Memory, skill learning, and self-improvement ideas | Windows path is less proven; skill drift can hurt | Use as critic/memory lane until locally verified |
| Aider / Goose / OpenHands / Cline / Continue class tools | Mature edit loops, IDE context, or autonomous coding environments | Each has its own assumptions and state model | Add as optional external surfaces behind the same packet contract |
| Raw HF / Ollama / paid model calls | Model breadth and cheap escalation options | No native repo safety or conflict handling | Use as planner/critic/finalizer only through SCBE packets |

## Missing Pieces To Add Next

1. Applicability scorer.
   The router needs a second pass that opens the proposed target files and
   checks that referenced classes, functions, imports, test files, and CLI flags
   actually exist before a lane can become promotable.

2. Safe-apply benchmark tier.
   The current benchmark scores the orchestration contract. The next tier should
   extract one promotable diff, run `scripts/agents/safe_apply.py`, and record
   whether the patch applies and passes a smoke command.

3. Cross-lane agreement.
   Multiple agents proposing the same target file or same defect should raise
   confidence. Multiple agents inventing different files should lower
   confidence even if each response is well-structured.

4. Cost-aware escalation.
   Local and free lanes should generate breadth. Ollama Cloud or paid lanes
   should run only when local lanes have no promotable patch, or as a final
   critic over a concrete local proposal.

5. Skill selection by task geometry.
   External benchmark research shows skills can hurt when mismatched. SCBE
   should attach a skill only when the task, files, and lane role match.

## Headless And Cloud Runtime Notes

- Ollama Cloud is the lightest cloud lane because it preserves the Ollama API
  shape. The router can run locally against `127.0.0.1:11434` after signin or
  against Ollama's hosted API when an `OLLAMA_API_KEY` path is added later.
- Goose has a documented headless mode for automation and CI-style operation.
  That makes it a good future `guard` or `helper` surface, but it should still
  emit SCBE packets instead of mutating the repo directly.
- OpenHands exposes headless CLI and remote-workspace patterns. That is a good
  fit for heavier sandboxed lanes, especially when the local machine should stay
  light.
- The practical architecture is tiered:
  local helper lanes collect file evidence; builder lanes propose code; guard
  lanes reject fake/non-applicable patches; cloud lanes run only when local
  breadth is exhausted or when they are given helper-provided evidence.

## Benchmark Evidence

Latest cloud comparison:

- command: `python scripts/benchmark/openclaw_swarm_benchmark.py --mode ollama-cloud`
- result artifact: `artifacts/benchmarks/scbe_swarm_router/20260510T210308Z/report.md`
- cases: `2`
- failed command runs: `0`
- promotable lanes: `0`
- blocked lanes: `4`

Interpretation: cloud access is wired, but generated patch quality is not yet
good enough for autonomous application. The next engineering move is not more
models; it is the applicability scorer and safe-apply benchmark tier.

## Runtime Sources

- Ollama API docs: https://docs.ollama.com/api
- Ollama Cloud docs: https://docs.ollama.com/cloud
- Goose headless mode: https://goose-docs.ai/docs/tutorials/headless-goose/
- Goose CLI commands / ACP mode: https://goose-docs.ai/docs/guides/goose-cli-commands/
- OpenHands CLI page: https://openhands.dev/product/cli
- OpenHands headless docs: https://allhandsai.mintlify.app/openhands/usage/cli/headless
