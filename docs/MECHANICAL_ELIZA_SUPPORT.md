# Mechanical ELIZA Support Switchboard

Mechanical ELIZA is a secondary support system for chatbots and command agents.
It does not try to be smarter than the caller. It gives the caller a small,
deterministic support layer that classifies a request, chooses a switch, and
returns a machine-readable receipt.

The purpose is to keep an AI from improvising when it should route.

## Model

The engine uses layered rules:

| Layer | Job |
| --- | --- |
| intake | normalize the request and create a stable request id |
| intent | classify command, debug, sales, research, design, or loop distress |
| risk | detect destructive commands, secrets, money movement, and publishing |
| context | detect human caller, AI caller, or explicit support need |
| support_mode | choose mechanical-only, agent-to-agent, or human-visible support |
| history | detect single-turn, multi-turn, possible loop, or repeated loop |

The output is a `scbe.mechanical_eliza.v1` JSON packet with:

- a route;
- an enabled command switch;
- one ELIZA-style support response;
- next questions;
- command hints;
- a support contract;
- the full switchboard state.
- an optional Free LLM bridge request.
- an optional semantic navigation array.
- an optional ChoiceScript-style scene.

## Switches

| Switch | Use |
| --- | --- |
| `ask` | missing context; ask one clarifying question |
| `route` | safe command/workflow lane; emit governed command hints |
| `diagnose` | failure or traceback; request smallest reproducible receipt |
| `offer` | pricing, checkout, or customer route |
| `probe` | secrets, money, account state, or external publish risk |
| `deny` | destructive command shape; stop and human-review |
| `loop_break` | agent is confused, looping, or carrying conflicting goals |
| `memory` | context, state, recap, or checkpoint repair |
| `model` | select the lowest sufficient model/lane |
| `handoff` | package work for another agent or squad |

## CLI

```powershell
python scripts/system/mechanical_eliza_support.py --pretty "chatbot needs support: run pytest from the terminal"
```

Response-only mode:

```powershell
python scripts/system/mechanical_eliza_support.py --response-only "the assistant is confused and looping"
```

Free LLM routing request without calling a model:

```powershell
python scripts/system/mechanical_eliza_support.py --pretty --free-llm-request "true eliza should use the free llm route"
```

Call the repo's Free LLM dispatcher through ELIZA. This defaults to dry-run unless
`--live-model` is set:

```powershell
python scripts/system/mechanical_eliza_support.py --pretty --dispatch-free-llm --provider offline "true eliza should call the free llm route"
```

ChoiceScript-style navigation:

```powershell
python scripts/system/mechanical_eliza_support.py --choicescript "customer asks what to buy"
```

Semantic navigation array:

```powershell
python scripts/system/mechanical_eliza_support.py --semantic-map --pretty "chatbot is looping and confused"
```

Multi-turn loop detection:

```powershell
@"
what next
what next
"@ | Set-Content -Encoding utf8 .\history.txt

python scripts/system/mechanical_eliza_support.py --history-file .\history.txt --pretty "what next"
```

## Product Boundary

This is a deterministic support switchboard. It does not execute commands, call
Stripe, read secrets, or browse the web. When `--dispatch-free-llm` is used, it
calls the existing free/open LLM router only after the mechanical route is
chosen. Without `--live-model`, that dispatch is a dry-run route receipt.

That makes it suitable for the $1 self-serve Workcell CLI path: buyers can use
it as a simple mechanical support layer for their own chatbots before they need
custom implementation.
