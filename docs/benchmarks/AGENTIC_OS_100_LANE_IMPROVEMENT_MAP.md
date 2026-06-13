# Agentic OS 100-Lane Improvement Map

Status: research-backed planning map for SCBE CLI, agent bus, benchmark, browser,
and provenance work.

Claim boundary: this is not a public leaderboard claim. It is a refinement map
for turning local executable evidence into stronger public-facing proof.

## Research Inputs

Local evidence:

- `docs/benchmarks/HARD_AGENTIC_BENCHMARK_PRETEST.md`
- `docs/benchmarks/RUBIX_BROWSER_HYPERCUBE_BENCHMARK.md`
- `docs/benchmarks/PUBLIC_AGENTIC_CLI_BENCHMARK_PLAN.md`
- `docs/benchmarks/OPEN_SOURCE_AGENT_TASK_LANES.md`

External benchmark/product pressure points reviewed:

- Terminal-Bench and TerminalWorld: terminal task execution, filesystem state,
  long command chains, and recovery from partial failures.
- SWE-bench and SWE-style repair: issue-to-patch workflows with tests and logs.
- GAIA and BrowseComp: tool-using research tasks with source discipline and
  short-answer verification.
- WebArena, VisualWebArena, BrowserGym, OSWorld, and WindowsAgentArena:
  browser/desktop operation under UI, permission, visual, and state pressure.
- Tau-style tool-user-policy tasks: interactive tool use where the correct
  answer must respect policy, not just task completion.
- Claude Code, Codex CLI, Gemini/Antigravity-style products: long-horizon
  repo work, tool routing, context retention, background automation, and
  permissioned computer use.

## Ten Aspects To Research And Build Against

1. Terminal execution depth
   - Target: Terminal-Bench, TerminalWorld.
   - SCBE angle: command receipts, shell state memory, rollback boundaries.

2. Repo repair and patch quality
   - Target: SWE-bench, real-patch fixtures, live good-first-issue packets.
   - SCBE angle: proof chain from issue -> files -> patch -> tests -> receipt.

3. Browser and desktop control
   - Target: WebArena, BrowserGym, OSWorld, WindowsAgentArena.
   - SCBE angle: Rubix/tesseract permission faces instead of flat click maps.

4. Research with source provenance
   - Target: GAIA, BrowseComp, internal patent and market research.
   - SCBE angle: bifurcated reasoning: proof path vs answer path.

5. Tool routing and model economy
   - Target: free/local-first routing plus paid escalation only when useful.
   - SCBE angle: squad shell, route receipts, cost-aware provider selection.

6. Stateful long-horizon work
   - Target: deferred work, resumable plans, background tasks, task ledgers.
   - SCBE angle: roundabout reversibility: route closes even when state changes.

7. Security and policy fidelity
   - Target: AgentDojo, Tau-style policy tasks, prompt injection, secrets.
   - SCBE angle: L13 gate, denied faces, approvals, deterministic rule layer.

8. Cross-domain compilation
   - Target: cross-language code transforms, binary/hex interpolation, Sacred
     Tongues transport.
   - SCBE angle: bijective packets, atomic tokenizer, compile receipts.

9. Pathfinding under incomplete information
   - Target: partial-observation mazes, vector fields, ARC-like grid tasks.
   - SCBE angle: multi-lattice sensing, heat/pressure maps, no-shortest-path
     bias.

10. Product-grade CLI experience
    - Target: Claude/Codex/Gemini-style usability without copying their product.
    - SCBE angle: Hermes-style front end, agent helper, examples, role outputs,
      and task ticker.

## 100 Improvement Lanes

### A. Terminal Execution And Shell Control

1. Terminal-Bench adapter command: expose SCBE as a benchmark agent command.
2. TerminalWorld ingest lane: convert terminal recordings into SCBE task packets.
3. Shell state snapshot: record cwd, env, git branch, modified files, and last
   command outcome before every tool call.
4. Command retry policy: retry only when new evidence is added or a repair plan
   changes.
5. Command safety tiers: classify read-only, reversible, destructive, network,
   and secret-touching shell commands.
6. Windows/Linux command dualizer: emit equivalent PowerShell and POSIX commands
   when possible.
7. Long command chain receipts: hash each command, output preview, exit code,
   and downstream decision.
8. Terminal task ticker: show active task, elapsed time, current command, and
   next verification without visual clutter.
9. Failure replay packet: preserve failing command, logs, and minimal rerun
   instructions.
10. Terminal benchmark scorer shim: normalize pass/fail, latency, cost, and
    artifact paths across internal and external terminal lanes.

### B. Repo Repair, Context, And Patch Quality

11. Issue-to-file shortlist using `rg` plus file ownership heuristics.
12. Symbol index MVP using ctags or tree-sitter, with fallback to `rg`.
13. Test ownership predictor: map changed files to likely tests.
14. Patch minimality score: penalize unrelated churn and generated artifacts.
15. Diff risk classifier: mark auth, crypto, policy, filesystem, and network
    edits for stricter gates.
16. Real-patch expansion: add 20 more local repair fixtures with hidden-style
    tests.
17. SWE-bench remote runner packet: push Docker-heavy runs to Linux CI.
18. Patch provenance card: issue, files read, commands run, tests passed,
    rollback note.
19. Multi-model patch bakeoff: cheap model proposes, strong model reviews,
    deterministic harness decides.
20. PR description generator: include purpose, changed paths, test evidence, and
    rollback notes from receipts.

### C. Browser, Desktop, And Rubix/Tesseract Control

21. Playwright local Rubix fixture: turn face routes into real page actions.
22. Browser permission face schema: READ, NAV, FORM, AUTH, FILE, PREVIEW,
    SANITIZE, SUBMIT, DENY.
23. DOM-to-face mapper: classify elements into permission faces before click
    planning.
24. Screenshot-to-face mapper: include visual affordances for VisualWebArena-like
    tasks.
25. BrowserGym adapter: wrap Rubix receipts in a BrowserGym-compatible agent.
26. WebArena setup smoke: run one local self-hosted task through the adapter.
27. OSWorld readiness lane: distinguish desktop control from browser control.
28. Secret-field guard: route password, token, cookie, and payment zones to
    denied or approval faces.
29. Reversible-first browser policy: prefer preview/save-draft over destructive
    submit/delete paths.
30. Tesseract minimap: project high-dimensional permission state into a compact
    operator view.

### D. Research, Source Provenance, And Writing Pipeline

31. Research task packet: question, source policy, answer type, disallowed
    sources, citation bar.
32. BrowseComp-style local expansion: add 25 short-answer research fixtures.
33. GAIA-style local expansion: add multi-tool tasks with files, web, math, and
    code.
34. Source conflict ledger: preserve contradictory sources instead of flattening
    them.
35. Evidence vs execution split: require both "what was found" and "what action
    was taken."
36. Patent tie-back scanner: map benchmark artifacts to patent doc sections and
    claim families.
37. YouTube upload research lane: title, description, transcript, tags, upload
    checklist, and proof artifacts.
38. Writing pipeline role cards: editor, fact-checker, title optimizer, uploader,
    and compliance reviewer.
39. Auto-abridgement lane: compress long notes into short scripts while keeping
    source pointers.
40. Public claim generator: convert evidence packets into website-safe claims
    with forbidden-claim warnings.

### E. Tool Routing, Model Economy, And Free-First Operation

41. Provider health matrix: check Ollama, Cerebras, Groq, Hugging Face, OpenAI,
    Anthropic, and XAI.
42. Free-first router policy: local/free tiers first; paid routes require a
    reason receipt.
43. Cost envelope per task: expected tokens, API cost, retry budget, and timeout.
44. Weak-model instruction scaffolds: next steps, examples, expected output, and
    validation rules for low-capability models.
45. Model role contracts: router, worker, verifier, summarizer, security judge.
46. Provider fallback receipts: record why the route moved from one provider to
    another.
47. Offline degraded mode: produce commands and checklists even when no API is
    reachable.
48. Local model task bank: identify tasks that Ollama can handle acceptably.
49. Paid escalation guard: require failed local/free attempt or high-risk
    classification.
50. Router benchmark: compare provider choice accuracy against fixed task labels.

### F. Stateful Reasoning And Deferred Work

51. Deferred work ledger: every "later" item gets owner, reason, artifact, and
    next trigger.
52. Resume packet: current goal, open files, last passing tests, blockers, next
    command.
53. Task stack tree: parent goal, child tasks, dependencies, and proof status.
54. Roundabout route audit: input -> action -> environment change -> response
    -> next input.
55. Tool-loop detector: stop loops where repeated tool calls add no evidence.
56. Interruption recovery test: kill and resume a benchmark run without losing
    state.
57. Background task clock: local time, system time, optional ISS/UTC marker, and
    task ticker.
58. Human input checkpoint schema: ask only when the missing fact cannot be
    discovered or safely assumed.
59. Multi-session memory boundary: separate persistent project memory from
    ephemeral run state.
60. Long-horizon benchmark: 50-step internal task with deferred branches and
    recovery checks.

### G. Security, Policy, And Governance

61. Deterministic deny layer: reduce false-allow risk before model reasoning.
62. Permission abridgement compiler: translate broad intents into least-privilege
    tool scopes.
63. Secret exfiltration fixtures: test prompt injection and accidental file
    leakage.
64. Approval face receipts: record human approvals with exact scope and duration.
65. Policy conflict resolver: when user intent conflicts with tool policy, emit a
    safe alternate route.
66. AgentDojo-style lane: local prompt-injection/tool-use mini benchmark.
67. Tau-style interactive policy lane: user asks for help, environment has rules,
    agent must comply.
68. Governance drift report: compare model-proposed action to deterministic rule
    result.
69. Destructive command sandbox: require dry-run, path check, and rollback plan.
70. Public safety artifact: publish redacted receipts, not secrets or full local
    state.

### H. Cross-Domain Compiler, Tokenizer, And Binary/Hex Work

71. Atomic tokenizer spec draft: minimal reversible token units and claim
    boundary.
72. Binary/hex compiler lane: convert bytes -> semantic packets -> target
    language representation.
73. Cross-language compile benchmark: KO/RU/CA/UM/DR broadcast with expected
    semantic equivalence.
74. Loss declaration field: every transform states exact known loss or
    non-reversibility.
75. Bijective packet validator: encode/decode round-trip tests for code and
    metadata.
76. Hex board visualizer: map bytes/opcodes to go-board or lattice positions.
77. Permission-aware compiler: generated code carries allowed operations and
    denied side effects.
78. Language bridge corpus: small verified examples across Python, TS, Rust, Go,
    and shell.
79. Patent-safe tokenizer notes: separate implementation evidence from legal
    conclusions.
80. Cross-domain compile scorer: correctness, reversibility, safety, and
    readability.

### I. Pathfinding, Lattice Sensors, And Non-Standard Mazes

81. Pathfinding suite expansion: 20 more partial-observation mazes.
82. Random-solve baseline bank: preserve floor scores across seeds.
83. Fluidic heat map: mark explored, frontier, risk, pressure, and stale zones.
84. Pressure-sense sensor: increase exploration weight where local uncertainty
    traps the agent.
85. Vector-field planner ensemble: run A*, frontier, wall-follow, heat, and
    lattice pressure together.
86. Best-strength path selector: pick path by evidence-weighted composite score,
    not shortest length.
87. No-goal ablation tracker: detect when goal vector creates local minima.
88. Worm logic adapter: local gradient sensing, turn bias, obstacle memory, and
    exploratory persistence.
89. Octree/octicube minimap: compress high-dimensional awareness into an
    operator-visible board.
90. ARC grid bridge: convert pathfinding sensors into ARC-style grid transforms
    for testable abstraction.

### J. Product Surface, Docs, And Market Proof

91. `scbe bench` command family: keep adding local evidence lanes behind one
    stable CLI surface.
92. Hermes-style CLI front end: task menu, helper, examples, and active proof
    status.
93. Website evidence cells: publish only reproducible local commands and public
    benchmark boundaries.
94. Competitor feature matrix: Claude/Codex/Gemini/ASI-style features vs SCBE
    receipts and gaps.
95. "Use it today" cookbook: website, YouTube upload, repo repair, research
    packet, benchmark run.
96. Install doctor: verify keys, free models, local models, Python packages, and
    Docker readiness.
97. Demo script: 5-minute terminal path from install -> task -> proof report.
98. Public artifact index: latest JSON/Markdown reports with commit hashes.
99. Five-branch roadmap page: show what is shipping now vs later.
100. Claim hardening checklist: every website claim must link to command,
     artifact, commit, and boundary.

## Refinement Into Five Branch Families

These are the first five branches to cut from the 100 lanes.

1. `feat/bench-evidence-hub`
   - Lanes: 1, 10, 31, 32, 33, 40, 91, 98, 100.
   - Goal: one command and one artifact index for all local and public evidence.
   - First pass: extend `scbe bench` with `list`, `latest`, and `prove`.

2. `feat/rubix-browser-adapter`
   - Lanes: 21, 22, 23, 24, 25, 28, 29, 30.
   - Goal: move from fixture proof to Playwright-backed browser execution.
   - First pass: local page fixture with permission faces and receipts.

3. `feat/stateful-task-ledger`
   - Lanes: 51, 52, 53, 54, 55, 56, 57, 58.
   - Goal: make deferred work, context retention, and tool loops measurable.
   - First pass: resume packet plus tool-loop detector.

4. `feat/free-first-router-hardening`
   - Lanes: 41, 42, 43, 44, 45, 46, 47, 48, 49, 50.
   - Goal: make weak/free models useful through scaffolds and verification.
   - First pass: provider health matrix plus route receipts.

5. `feat/lattice-pathfinding-kernel`
   - Lanes: 81, 82, 83, 84, 85, 86, 87, 88, 89, 90.
   - Goal: improve partial-observation navigation without overfitting.
   - First pass: ensemble path selector plus fluidic heat/pressure maps.

## Scoring Rule For Picking The First Branch

Score each branch 1-5 on:

- Evidence lift: produces a command/artifact we can show.
- Product lift: makes the CLI more useful immediately.
- Patent provenance: ties cleanly to filed/pending docs without overclaiming.
- Benchmark lift: improves a measurable lane.
- Risk: lower score means less risk; invert when ranking.

Recommended first branch: `feat/bench-evidence-hub`.

Reason: it makes every later improvement easier to prove. It also prevents the
website from drifting into claims that are not tied to commands, artifacts,
commits, and explicit boundaries.

## Source Links

- Terminal-Bench: https://www.tbench.ai/
- TerminalWorld paper: https://arxiv.org/abs/2605.22535
- Terminal-Agent benchmark task guidelines: https://arxiv.org/abs/2604.28093
- WebArena: https://webarena.dev/
- BrowserGym: https://github.com/ServiceNow/BrowserGym
- VisualWebArena: https://arxiv.org/abs/2401.13649
- OSWorld: https://os-world.github.io/
- WindowsAgentArena: https://videowebarena.github.io/static/files/windows_agent_arena.pdf
- BrowseComp: https://openai.com/index/browsecomp/
- GAIA overview: https://huggingface.co/learn/agents-course/unit4/what-is-gaia
