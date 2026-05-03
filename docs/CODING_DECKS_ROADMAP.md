# Coding Decks Roadmap

Generated: 2026-05-02

Purpose: turn the coding-tokenizer idea into a repeatable deck system. The goal is not to pretend the repo already covers every programming language. The goal is to build a grounded base deck, count it honestly, and make every new language lane additive.

## Core Rule

Use substrate cards first.

```text
operation substrate -> language view -> binary transport -> pair/witness routes
```

The operation substrate is the source of truth. Language cards are projections of the same operation, not separate meanings.

## Current Grounded Deck

Current source:

```text
src.ca_lexicon.LEXICON
python.scbe.tongue_isa_binary.STIB
src.symphonic_cipher.scbe_aethermoore.trijective.DEFAULT_WITNESSES
```

Current language lanes:

| Tongue | Language | Status |
|---|---|---|
| KO | Python | Primary |
| AV | TypeScript | Primary |
| RU | Rust | Primary |
| CA | C | Primary |
| UM | Julia | Primary |
| DR | Haskell | Primary |
| GO | Go | Extended, inherits from CA when no override exists |
| ZI | Zig | Extended, inherits from RU when no override exists |

## Deck Count

The first grounded minimum is:

```text
64 operation cards
+ 64 * 8 language-view cards
+ 256 binary byte cards
+ 13 STIB structure cards
+ 54 pairing cards
= 899 cards
```

That is the current playable/codeable base deck.

## What The Cards Mean

| Card class | Count | Meaning |
|---|---:|---|
| Operation | 64 | Canonical CA opcode substrate rows. |
| Language view | 512 | One operation projected into one language lane. |
| Binary byte | 256 | Full 8-bit byte space for binary/STIB transport. |
| STIB structure | 13 | Binary envelope fields: magic, versions, tongue id, op count, opcode bytes, hash, etc. |
| Pairing | 54 | Witness triangles, complement pairs, inheritance pairs, primary pairs, and all-lane pairs. |

## Expansion Math

Adding one new language lane currently costs:

```text
64 language-view cards
+ N pairing cards to every existing lane
```

With the current 8 lanes, that means:

```text
64 + 8 = 72 cards
```

If the new language needs special runtime constructs beyond the 64-op substrate, add those as extension cards, not by mutating the base operation cards.

## Commands

Generate the deck manifest:

```powershell
python scripts/system/build_coding_decks.py
```

Print full JSON:

```powershell
python scripts/system/build_coding_decks.py --json
```

Focused test:

```powershell
python -m pytest tests/system/test_build_coding_decks.py -q
```

## Next Expansion Targets

1. Add a compact SFT generator that turns deck cards into instruction/response rows.
2. Add per-language override coverage reports for GO and ZI.
3. Add construct decks for functions, loops, modules, types, errors, async, memory, and package IO.
4. Add a "world language inventory" file where unsupported languages can be listed without claiming coverage.
5. Wire this into the coding-Pazaak simulator so agents can play operation and language cards against a task board.

## Do Not Cargo-Cult This

Do not add a language card just because the language exists. A lane becomes grounded when it has one of:

- a direct template for each substrate operation,
- an inheritance route plus explicit overrides,
- a parser/emitter route through Code Prism,
- a binary/STIB route with round-trip tests.

