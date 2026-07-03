# SCBE Conlang, Tokenizer, Compiler, and Music-Mapping Notes

Date: 2026-06-27
Status: living research note

## Core idea

SCBE already has "six in a way": six tongues / lanes / semantic profiles that can be treated like constructed programming languages. The useful research direction is not just making a weird syntax. It is making a safe layered system:

```text
human-facing language
  -> tokenizer
  -> parser
  -> typed intermediate representation
  -> verifier
  -> compiler/interpreter
  -> binary/hex/music/tool output
```

The important rule is to keep each lane distinct while allowing deterministic mappings between them.

## Six-lane research frame

| Lane | Research question | Product value |
|---|---|---|
| Conlang syntax | How do humans write intent in each tongue? | Makes SCBE readable and teachable. |
| Tokenizer | How does text become stable tokens/features? | Enables training, eval, and deterministic round trips. |
| Compiler/interpreter | How do tokens become executable behavior? | Turns SCBE from lore into tools. |
| Binary/hex transport | How do symbols map to bytes and recover exactly? | Gives receipts, hashes, and reversible evidence. |
| Musical/piano mapping | How do bytes/tokens map to pitch, interval, rhythm, or chord? | Makes structure audible and teachable. |
| Tool/browser actions | How does language safely call real tools? | Makes AetherDesk useful without unsafe free-form shell. |

## Code conlang lesson

Esolangs show that strange human syntax can still be formally executable if it has:

- a small instruction set
- a precise VM or interpreter
- deterministic parsing
- explicit I/O
- receipts or examples

SCBE should use that lesson without inheriting the gimmick. The model should learn:

```text
odd language in
  -> exact structured packet out
  -> verifier checks packet
  -> only then tools run
```

## Tokenizer research notes

Good tokenizer targets:

- source-stable: same input gives same tokens
- reversible where possible
- keeps semantic tokens separate from transport bytes
- supports per-tongue profiles
- stores metadata for language, lane, source hash, token hash, and version

Questions to investigate:

- Should each tongue have its own tokenizer vocabulary?
- Should binary/hex be a transport layer only, or also a trainable token stream?
- Which parts should be BPE-like versus grammar/token-table based?
- Can piano/music tokens become a parallel annotation instead of replacing text?

## Compiler/interpreter research notes

Best first target:

```text
SCBE browser-action conlang
  -> JSON action packet
  -> schema validation
  -> AetherDesk route call
```

Example:

```text
BROWSE source "https://example.com"
AUDIT source
VERIFY claim
REPORT receipt
```

Compiles to:

```json
{
  "route": "browser_use",
  "steps": [
    {"tool": "POST /api/playwright/view", "body": {"url": "https://example.com"}},
    {"tool": "POST /api/web/audit", "body": {"url": "https://example.com"}},
    {"tool": "POST /api/verified/ask", "body": {"question": "Is the claim supported?"}}
  ],
  "background_polling": false,
  "token_boundary": "server_only"
}
```

This is safer than compiling directly to shell or browser automation.

## Binary and piano mapping

Treat binary/hex and music as two views of the same underlying structure:

```text
byte stream
  -> hex
  -> bit groups
  -> pitch classes / intervals / rhythm
  -> piano roll / audible checksum
```

Possible mappings:

- 4-bit nibble -> 16 pitch-class/register choices
- byte -> pitch + duration
- token class -> instrument/voice
- tongue/lane -> musical mode
- hash prefix -> motif
- control-flow branch -> chord transition
- verification failure -> dissonance marker

Important boundary:

Music is an annotation/inspection layer unless a runtime explicitly consumes it. Do not claim the music itself "executes" unless there is a defined interpreter.

## Training implication

This is good model-training material if split into clean datasets:

1. Human-authored open-source language/compiler/tokenizer guides after license review.
2. SCBE synthetic route examples with exact local APIs.
3. Holdout tasks that require JSON action packets.
4. Round-trip tests: text -> token -> binary -> music annotation -> original meaning.

The target behavior is not "make prettier prose." It is:

```text
structured intent
  -> correct packet
  -> no token leakage
  -> no background polling
  -> no unverified claims
  -> executable only after validation
```

## Research artifacts already started

- `docs/research/CODE_CONLANGS_RESEARCH_2026-06-27.md`
- `docs/research/CODE_CONLANGS_EVIDENCE_2026-06-27.csv`
- `docs/research/CODE_CONLANGS_OPEN_QUESTIONS_2026-06-27.md`
- `docs/research/ISSAC_SYSTEMS_INSPIRATION_INDEX_2026-06-27.md`
- `training-data/sft/aetherdesk_browser_use_v1.sft.jsonl`
- `training-data/sft/aetherdesk_browser_use_v1_holdout.sft.jsonl`
- `docs/training/AETHERDESK_BROWSER_USE_TRAINING_2026-06-27.md`

## Inspiration pass from local systems and Issac notes

Key design patterns to preserve:

- A URL is a graph node with six tongue-weighted readings, not just a string.
- Browser distance is agent-dependent; the same route has different cost for KO/RU/CA/UM/DR-heavy agents.
- A click is a haptic route through 2D sweep, 3D press, 4D membrane breach, and 2.5D event transit.
- Semantic atoms are meaning objects with valence, orbitals, bonds, and receipts.
- SS1/binary/hex are transport evidence, not semantic meaning.
- Training maturity should follow realification phases: imprint, shadow, overlap, resonance, autonomy.

This turns the next build into a concrete compiler problem:

```text
browser-action conlang
  -> six-tongue semantic atoms
  -> haptic/web-route IR
  -> verified JSON packet
  -> AetherDesk browser/tool action
```

## Working hypothesis

SCBE's strongest path is a small, verifiable language stack:

```text
six tongues
  -> deterministic tokenizer
  -> compact IR
  -> browser/tool/compiler targets
  -> musical/binary receipt views
  -> model trained to emit validated packets
```

That can become both a research artifact and a product feature inside AetherDesk.
