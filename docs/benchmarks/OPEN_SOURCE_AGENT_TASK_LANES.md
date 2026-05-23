# Open-Source Agent Task Lanes

Status: external task map for Aether Programmer Index.
Last researched: 2026-05-23.

This file lists open-source task pools we can run against so SCBE is not limited by the current state of this repo. The source of truth is `config/eval/aether_external_task_lanes.v1.json`.

## What Makes A Strong Coding Assistant

The base model matters, but it is not the whole product. Strong coding assistants are usually strong because the model is wrapped in a better system:

| Layer | What it does | What paid products win on |
| --- | --- | --- |
| Base model | Generates code and reasons through patches. | Access to frontier models and large context. |
| Context system | Finds the right files, symbols, docs, issues, and past failures. | Cursor/Sourcegraph-style codebase retrieval. |
| Task harness | Defines "done" for each task. | Issue-to-PR flow, hidden tests, shell execution. |
| Tool runtime | Runs git, shell, browser, package managers, GitHub, deploy checks. | Cloud workspaces and IDE integration. |
| Verification loop | Runs build, lint, format, test, deploy smoke, and reruns. | Managed automation and polished UX. |
| Governance layer | Keeps tool use scoped and auditable. | This is where SCBE can compete now. |

So the strategy is not "make a better base model." It is: use available models, then make the harness, context, completion rules, and recovery loop better than the default agent workflow.

## Model Orchestration

Do not spend the largest model on every task. With many agents in flight, the highest-context model should be the leader/judge/router:

| Role | Model tier | Job |
| --- | --- | --- |
| Leader | strongest available model | Interpret root intent, select lane, assign workers, resolve disagreement, approve plan. |
| Specialist | medium model or tool-specific agent | Handle code search, docs lookup, benchmark interpretation, security review. |
| Worker | cheap/free/local model | Inspect files, generate candidate fixes, run commands, summarize evidence. |
| External tool | Copilot, Cody/Sourcegraph, other agent | Propose or retrieve; never decide completion alone. |
| Harness | deterministic scripts/tests/policy | Decide pass/fail, evidence quality, and whether rerun is required. |

This is how SCBE can improve beyond base-model limits. If Opus-class reasoning is too expensive for 1000 agents, use it at the trunk and branch points. Let smaller agents do leaf work, then force every leaf through the same completion rules.

## Lanes To Run

| Lane | Task pool | First SCBE run |
| --- | --- | --- |
| Real repo repair | SWE-bench | 1-3 Lite/Verified tasks with patch, tests, logs, cost, and failure mode. |
| Harness reference | SWE-agent / SWE-ReX | Reuse compatible sandbox and trajectory ideas where practical. |
| Terminal execution | Terminal-Bench | Small Docker-backed subset through SCBE CLI/agent-bus. |
| Multi-language editing | Aider Polyglot | Re-run the known Rust failure, then one Python and one JS task. |
| Cheap language drills | Exercism direct | SCBE-owned mini subset for weak/free models before full Polyglot. |
| Function correctness | EvalPlus | Cheap local correctness lane for HumanEval+/MBPP+. |
| Java repair | Defects4J | One small Java bug-fix task after Maven/Gradle harness support exists. |
| Practical generation | BigCodeBench | Tiny instruct split sample for library/function-call tasks. |
| Fresh coding | LiveCodeBench | Custom-output JSON evaluation for a small release slice. |
| Security/governance | AgentDojo | One prompt-injection/tool-use subset through SCBE gate. |
| Browser/desktop | WebArena / OSWorld | Later lane after the browser/desktop operator is stable. |
| Live issues | GitHub good first issues | Convert maintainer-labeled public issues into task packets and PRs. |

## GitHub Issue And PR Harness

SCBE should support this issue-to-PR loop:

1. Import GitHub issue or external benchmark task.
2. Build a task packet with repo URL, base commit, instructions, allowed tools, completion tests, and policy limits.
3. Let an agent propose changes on a vine branch.
4. Run pre-lint, format, typecheck, unit tests, and target benchmark tests.
5. Optionally call GitHub Copilot coding agent as a tool, not as the judge.
6. Score the result with Aether Programmer Index.
7. If failed, generate procedural solution triage and rerun.
8. If passed, raise pass quality: usability, minimality, verification, governance, cost/time.
9. Open or update PR only with evidence attached.

The key distinction: external tools can propose. SCBE decides completion.

## Sourcegraph-Style Context

We should either use open-source code search/context tools or build the minimum local version:

| Tool | Use |
| --- | --- |
| `ripgrep` | Fast text search for issue terms, stack traces, imports, and error strings. |
| `universal-ctags` | Quick symbol index for MVP retrieval. |
| `tree-sitter` | Parse source into syntax trees; extract functions, classes, imports, and call sites. |
| `SCIP` | Sourcegraph-style language-agnostic code intelligence and cross-reference graph. |
| `Semgrep` | Pattern search for similar bugs, policy violations, and security-sensitive paths. |
| `LSP` | Go-to-definition and find-references through existing language servers. |

Minimum local version:

1. `ripgrep` issue terms.
2. `ctags` symbol map.
3. file shortlist.
4. test ownership guess.
5. prior failure memory.
6. API/doc lookup when the issue depends on current external behavior.

This is probably one of the biggest deltas between weak agents and strong agents. The model often fails because it is looking at the wrong slice of the codebase, not because it cannot write code.

## Near-Term Order

1. **Exercism direct mini subset**: cheapest cross-language usability lane.
2. **EvalPlus**: cheap function correctness lane.
3. **Terminal-Bench tiny subset**: proves the terminal operator.
4. **Aider Polyglot re-run**: directly attacks the known Rust failure.
5. **Retrieval MVP**: `ripgrep` + `ctags` issue-to-file shortlist.
6. **AgentDojo tiny subset**: proves governed tool use.
7. **SWE-bench Lite/Verified 1-task run**: public repo repair evidence.
8. **GitHub good-first-issue packet**: live issue-to-branch-to-PR workflow.
9. **Defects4J one-bug run**: Java repair evidence.
10. **LiveCodeBench/BigCodeBench**: fresh and practical code generation.
11. **SCIP/tree-sitter graph**: Sourcegraph-style context upgrade.
12. **WebArena/OSWorld**: only after browser/desktop harness is stable.

## Claim Guardrails

Allowed:

- "SCBE has mapped open-source external task lanes for Aether Programmer Index."
- "SCBE can evaluate against public task pools outside its own repo once adapters exist."
- "SCBE treats Copilot/other agents as tools whose outputs must still pass SCBE verification."

Not allowed yet:

- "SCBE beats Cursor/Devin/Copilot" without external task scores.
- "SCBE passes SWE-bench/Terminal-Bench/Aider" before run packets exist.
- "SCBE has Sourcegraph-level code intelligence" before a real index/search layer exists.
