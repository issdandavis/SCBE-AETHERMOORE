# SCBE Forge Visual TTS Trainer

Date: 2026-06-27
Status: v0 product spec

## Product boundary

SCBE Forge should feel familiar to people who have used modern gamified coding-practice platforms: persistent path rail, hands-on exercise, code editor, tests, progress, XP/streak, and mentor panel.

It must not copy Boot.dev branding, names, characters, exact content, assets, or trade dress. The product identity is AetherDesk/SCBE: forge, opcode, receipts, six language faces, conlang-first lessons, and verified local execution.

## Core lesson model

The primary teaching language is our own code language.

```text
SCBE/conlang source
  -> tokenizer receipt
  -> opcode binding
  -> typed IR
  -> host-language emission
  -> test execution
  -> provenance/training receipt
```

Host code is a face, not the root curriculum. A Python/Rust/JS example is shown only after the SCBE source has a token/opcode receipt.

## First lesson

```text
bip'a 3 4
```

Expected receipt:

```json
{
  "surface": "bip'a 3 4",
  "binds_to": ["CA:0x00:add"],
  "emits_to": ["python"],
  "executed_on": ["browser-sim"],
  "result": 7
}
```

Honesty firewall:

- `binds_to` is provenance.
- `emits_to` is compiler target capability.
- `executed_on` is the runtime actually exercised in this lesson.
- Do not collapse these into "runs everywhere."

## Visual requirements

- Dark coding-workspace shell.
- Left curriculum path rail.
- Center lesson + SCBE code editor.
- Right AI/TTS guide.
- Bottom test output + provenance receipt.
- Top progress row with XP, streak, path, and run status.
- Rectangular panels with small radius.
- AetherDesk/SCBE colors: charcoal, teal, copper, verified green.
- No Boot.dev logo, mascot, exact copy, course names, or assets.

## TTS guide requirements

The guide is not a decoration. It is a tutor mode:

- Speak the current hint.
- Pause/resume/cancel speech.
- Maintain a visible voice mode and pace.
- Later route to `python/scbe/tts_backend.py` or `python/scbe/expressive_tts.py` for local WAV receipts.
- Keep spoken text derived from lesson state, not arbitrary background chatter.

## Training capture policy

A lesson attempt can become training data only when:

- source text is preserved
- tokenizer receipt exists
- tests pass
- mentor help level is recorded
- output claim separates binds/emits/executes

Rejected attempts can still become repair examples, but not clean solved examples.

