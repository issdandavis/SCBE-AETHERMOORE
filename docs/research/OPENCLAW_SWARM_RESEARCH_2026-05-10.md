# SCBE Multi-Swarm Router Research Brief — 2026-05-10

Question: what external evidence should shape the SCBE multi-swarm router?

Correction: OpenClaw is one router/bootstrap option, not the whole system. The
target architecture is a shared SCBE routing layer that can dispatch many
independent swarms through different means: Ollama Launch tools, raw Ollama
models, external free/open coding agents, Hugging Face endpoints, and paid
models only when the free lanes stop producing useful gains.

## Key Findings

1. Ollama Launch is a real integration surface, not just model naming.
   Ollama describes `ollama launch` as a command that sets up coding tools such
   as Claude Code, OpenCode, Codex, and Droid with local or cloud models. This
   supports our current design: keep agent aliases and launch commands separate
   from the underlying local model that happens to be available.

2. Ollama Cloud belongs in the same provider family as local Ollama.
   Ollama Cloud uses the same local API shape for cloud-tagged models after
   `ollama signin`, and also supports direct `https://ollama.com/api` access
   with `OLLAMA_API_KEY`. The router should model this as
   `execution_surface=ollama_local|ollama_cloud`, not as a totally separate
   provider.

3. Agent wrapper design matters, sometimes as much as model choice.
   SWE-Bench Mobile reports that the same model can vary by up to 6x across
   different agents, and the best configurations still achieved only 12% task
   success on their mobile benchmark. This argues for benchmarking the harness,
   routing, prompts, and execution loop directly instead of assuming a better
   model alone fixes the system.

4. Skills are not automatically valuable.
   SWE-Skills-Bench found that most tested skills produced no pass-rate
   improvement, with average gain only +1.2%, while some version-mismatched
   skills degraded performance. For SCBE, skills should be selected by task
   geometry and repo context, not injected wholesale.

5. Realistic coding-agent evaluation needs execution-aware tool surfaces.
   IDE-Bench emphasizes structured file editing, codebase search, and full-stack
   tests rather than raw terminal-only prompting. OmniCode similarly broadens
   evaluation beyond bug fixing into test generation, code review fixing, and
   style fixing. This supports a benchmark ladder: harness contract first,
   safe-apply patch correctness second, then broader task categories.

6. Hermes is useful as a memory/skill-learning reference, but its own Windows
   support is marked early beta.
   Hermes advertises persistent memory, skills, MCP, tools, and migration from
   OpenClaw, but notes native Windows support is early beta and WSL2 remains the
   more road-tested path. For this Windows repo, Hermes should remain a profile
   or critic lane until locally verified.

## Design Implications For SCBE

- Keep the free-first router. Run local/free lanes for breadth and only escalate
  to paid models when no lane is promotable or when the task demands final
  integration.
- Add Ollama Cloud as an opt-in middle tier before external providers. The
  current implementation uses `--allow-ollama-cloud` and
  `--prefer-ollama-cloud` so no cloud lane runs accidentally.
- Treat OpenClaw as a bootstrap/router surface, not as the product boundary.
  The product is the SCBE orchestral router coordinating many swarms into one
  project ledger.
- Add a critic/final-integrator pass next. A lane passing lexical quality gates
  is not enough; the next pass should inspect the proposed diff against actual
  files and reject fake imports, invented flags, and non-applicable patches.
- Add an applicability scorer before `safe_apply`. The latest Ollama Cloud
  benchmark proved cloud models can produce confident but fake wrapper-symbol
  patches; the router should keep blocking those before any patch application.
- Track per-agent role and model separately. `opencode` as a role may be backed
  by `qwen2.5-coder:1.5b` today and a real `opencode:latest` tomorrow.
- Treat skills as narrow routed assets. Select a skill only when its domain
  matches the lane and repo state; record whether it improved promotion rate or
  just increased tokens.
- Expand benchmarks in layers:
  - Level 0: harness contract and routing artifacts.
  - Level 1: safe-apply compatibility of generated diffs.
  - Level 2: repo-local task success using existing tests.
  - Level 3: external coding-agent benchmarks such as SWE-style or IDE-style
    tasks only after the local loop is stable.

## Sources

- Ollama Launch blog, 2026-01-23:
  https://ollama.com/blog/launch
- Ollama Cloud docs:
  https://docs.ollama.com/cloud
- Ollama API docs:
  https://docs.ollama.com/api
- NousResearch Hermes Agent GitHub README:
  https://github.com/NousResearch/hermes-agent
- OpenCode overview:
  https://env.dev/ai/opencode
- SWE-Bench Mobile, arXiv:2602.09540:
  https://arxiv.org/abs/2602.09540
- SWE-Skills-Bench, arXiv:2603.15401:
  https://arxiv.org/abs/2603.15401
- IDE-Bench, arXiv:2601.20886:
  https://arxiv.org/abs/2601.20886
- OmniCode, arXiv:2602.02262:
  https://arxiv.org/abs/2602.02262
