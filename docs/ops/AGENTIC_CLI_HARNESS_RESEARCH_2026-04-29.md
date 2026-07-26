# Agentic CLI Harness Research - 2026-04-29

## Research Takeaways

Primary-source patterns from current agentic coding tools:

- OpenAI Codex CLI exposes explicit sandbox modes (`read-only`, `workspace-write`, `danger-full-access`) and approval/sandbox separation. SCBE should model permissions as data, not prose.
- Claude Code documents MCP tool integration, hooks, and permission processing. SCBE should expose a pre-tool contract that any model can read before requesting shell, network, cloud, or write access.
- OpenHands emphasizes sandboxed environments, multi-agent coordination, and evaluation benchmarks. SCBE should keep `agentic_ladder`, `testing-cli`, and replay artifacts as promotion gates.
- Aider’s terminal workflow keeps Git central and makes model edits recoverable through normal Git operations. SCBE should keep task trajectories and patches small enough for Git review.
- The Model Context Protocol organizes agent surfaces around tools, resources, prompts, and host-controlled authorization. SCBE should export GeoSeal harness capabilities in that shape, even when not running as an MCP server.

## Implemented Direction

The new `agent-harness` manifest is the canonical model-facing packet for free or weak models:

```powershell
python -m src.geoseal_cli agent-harness --goal "fix tests" --language python --permission-mode observe --json
```

It returns:

- all mapped code-language routes: Python, TypeScript, Rust, C, Julia, Haskell, Go, Zig
- Sacred Tongue route for each language
- parent route for extended lanes (`GO -> CA`, `ZI -> RU`)
- exact CLI commands for code packets, route explanation, and testing
- permission profiles for observe, workspace-write, cloud-dispatch, and maintenance
- tool contracts for read, write, tests, network/cloud, secrets, and destructive filesystem actions
- service endpoint locations for HTTP runners

## CLI Improvement Rule

Every future agent-facing CLI feature should answer four questions in JSON:

1. What language/tongue route owns this task?
2. What tool class is being requested?
3. What permission profile allows or blocks it?
4. What command or service endpoint can replay or verify it?

That turns GeoSeal from a local operator command into a harness contract that other agents can use without needing hidden local context.

## GLM-5.2 and OpenAI-Compatible Agent Adapters

GLM-5.2 is integrated as an optional Z.ai proposal engine, not as a second harness and not as an executor. The same model-neutral GeoSeal contract can be consumed by GLM, Claude Code, Codex, OpenHands, a local Ollama model, or another controller.

The stable boundary is:

```text
model/controller -> agent-harness manifest -> SCBE permission gate
                 -> bounded tool execution -> validation -> receipt -> repair
```

Provider responsibilities:

- The model proposes plans, code, and tool calls.
- GeoSeal supplies explicit tool schemas and permission profiles.
- SCBE decides whether execution is permitted.
- Local tools perform filesystem, terminal, browser, test, and packaging work.
- Validators and receipts determine whether the task actually succeeded.
- Secret values never enter manifests, logs, or committed configuration.

Z.ai uses an OpenAI-compatible API adapter with these environment variables:

```powershell
$env:ZAI_API_KEY = "<secret>"
$env:ZAI_MODEL = "glm-5.2"
$env:ZAI_BASE_URL = "https://api.z.ai/api/paas/v4"
geoseal agent "refactor this module" --provider zai
```

The streaming SCBE controller can use the same provider:

```powershell
$env:SCBE_PROVIDER = "zai"
$env:SCBE_MODEL = "glm-5.2"
$env:ZAI_API_KEY = "<secret>"
$env:ZAI_BASE_URL = "https://api.z.ai/api/paas/v4"
scbe shell --agent-json
```

GLM remains outside automatic paid-provider routing unless `ZAI_API_KEY` is configured. `--small-first` reserves GLM and Claude for `ESCALATE` work so local, Ollama, and included-credit routes are attempted first.

This adapter pattern is the extension point for future providers: implement the transport, declare capabilities and budget, then reuse the same harness, governance, verification, and receipt layers.

## Source Links

- OpenAI Codex sandbox documentation: https://github.com/openai/codex/blob/main/docs/sandbox.md
- OpenAI Codex Rust CLI README: https://github.com/openai/codex/blob/main/codex-rs/README.md
- Claude Code MCP documentation: https://code.claude.com/docs/en/mcp
- Claude Agent SDK permissions documentation: https://docs.claude.com/en/docs/agent-sdk/permissions
- Claude Code hooks documentation: https://docs.anthropic.com/en/docs/claude-code/hooks
- OpenHands repository: https://github.com/OpenHands/OpenHands
- Aider repository: https://github.com/Aider-AI/aider
- Model Context Protocol specification: https://modelcontextprotocol.io/specification
- GLM-5.2 repository: https://github.com/zai-org/GLM-5
- Z.ai chat-completion API: https://docs.z.ai/api-reference/llm/chat-completion
