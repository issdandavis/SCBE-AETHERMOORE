# A 14-layer governance gate you can test in your browser (and why it matters)

Prompt injection is not “one bug.” It’s an exploit class: you can’t fix it with a single regex, a single blacklist, or a single model fine-tune.

So I built a public, interactive demo that shows the *shape* of a governance pipeline: 14 sequential checks (layers), 6 named semantic dimensions (“tongues”), and a final decision gate that is allowed to say **ALLOW**, **QUARANTINE**, or **DENY**.

## Try it

- Live demo: https://aethermoorgames.com/demos/governance-gate.html  
- Red-team proof surface: https://aethermoorgames.com/redteam.html

The demo lets you type any prompt and watch each layer run in sequence. It’s designed to be understandable by a human in one sitting, and inspectable enough to be useful to engineers.

## What the “14 layers” are (in plain terms)

Think of it like a safety pipeline that turns free-form text into a controlled action:

- early layers: interpret intent and context
- middle layers: measure drift / distance / coherence
- late layers: apply a cost curve (“harmonic wall”) and produce a risk decision

Most security writeups skip this and jump directly to “we blocked the jailbreak.” I’m trying to make the architecture legible so the *evaluation* can be legible.

## What’s real vs what’s a demo

The website demo is a simulation of the decision logic, not a claim that every internal math module is running client-side in your browser.

The point of the demo is:

- show the *pipeline* structure
- make the decision boundary explicit
- let people test inputs and see why they were routed to ALLOW / QUARANTINE / DENY

If you want the full implementation truth, the repo is public:

- GitHub: https://github.com/issdandavis/SCBE-AETHERMOORE

## If you want a shortcut: the $29 toolkit

If you don’t want to dig through a full repo and stitch your own starter lane, I also ship a small paid entry point:

- Toolkit offer: https://aethermoorgames.com/
- Manuals + delivery path: https://aethermoorgames.com/product-manual/index.html

One payment. One manual. One recovery/support route if anything breaks.

## Why I think this matters

We need AI security that is:

- inspectable enough to audit
- boring enough to operate
- explicit enough to benchmark against control groups

If you’re building anything agentic (tools, browsing, workflows), the “governance gate” isn’t optional. It’s the system.

If you read this and want to collaborate, the best entry is the demo + the red-team surface.

