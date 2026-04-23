# Constrained Traces Make Better Datasets

**By Issac Davis** | March 17, 2026

---

If you want better agent datasets, stop chasing giant free-form autonomy logs.

The higher-signal data usually comes from constrained loops:

- one task
- one allowed tool surface
- explicit checkpoints
- clear success or failure
- replayable context

That is the same pattern the official browser-agent and game-AI docs keep reinforcing.

Anthropic recommends isolated computer-use environments and warns about prompt injection. OpenAI's Operator uses takeover and confirmation points. Ubisoft's Ghostwriter keeps AI inside first-draft bark generation. Rainbow Six Siege combined traditional AI and ML instead of pretending one lane should do everything. EA SEED uses learned agents for specific testing problems.

Why this matters for datasets:

- narrow traces are easier to label
- negative examples are cleaner
- policy violations are easier to spot
- evaluation becomes less ambiguous

And the blocked traces matter too.

Denied, quarantined, or redirected actions are not useless exhaust. They are the highest-signal examples of where intent was heading before it was allowed to bloom into execution. They are unbloomed buds: evidence of what the system wanted to do, what policy caught, and what the next training pass should understand better.

The glamorous story is autonomous agents.

The useful data story is governed loops.

That is the direction I want for SCBE training sets: browser traces, relay packets, approvals, denials, and recoveries that are structured enough to train on later.

Useful references:

- Anthropic computer use: https://docs.anthropic.com/en/docs/build-with-claude/computer-use
- OpenAI Operator: https://help.openai.com/en/articles/10421097-operator
- Ubisoft Ghostwriter: https://news.ubisoft.com/en-gb/article/7Cm07zbBGy4Xml6WgYi25d/the-convergence-of-ai-and-creativity-introducing-ghostwriter
- EA SEED game testing: https://www.ea.com/seed/news/seed-ml-research-aaa-game-testing

Repo: https://github.com/issdandavis/SCBE-AETHERMOORE
