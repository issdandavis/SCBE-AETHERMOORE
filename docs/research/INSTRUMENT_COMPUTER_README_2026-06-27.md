# SCBE Instrument Computer

The Instrument Computer consolidates the music/code experiments into one local-first package:

```text
instrument input
-> notes / scale degrees / finite alphabet
-> governed compiler surface
-> verified SCBE runtime
-> code faces, result receipts, color, optional voice, persistent RAM
```

## What It Is

- `python/scbe/instrument_computer.py` is the reusable package.
- `scripts/audio/instrument_computer.py` is the CLI/demo entry point.
- `tests/audio/test_instrument_computer_package.py` proves the package behavior.

The package unifies:

- Holophonor: one note phrase emits language faces, executes the Python face, returns color/wavelength metadata, and can optionally write a spoken WAV.
- STISTA/atomic-token lane: played op tokens are mapped into existing `AtomicTokenState` rows for governance/semantic atoms.
- Full coding systems: receipts expose 8 primary `tongue_isa` faces plus the broader `instrument.emit_all` face set.
- Haskell primary face: Haskell is kept as a primary target and called out in receipts because pure stack transforms fit the CA model cleanly.
- Key governance: a note is legal or illegal relative to a key/mode dialect.
- Music theory: the same pitch has different scale-degree meaning in different keys.
- Bijection layer: degree programs render into different keys and decode back losslessly.
- Any-instrument layer: any instrument with at least two distinguishable symbols can encode the same program; smaller alphabets use longer note sequences.
- Shell-in-the-hole: played phrases compile to tape ops and mutate persistent RAM.
- Reel tape: the shell/runtime can model tape as old movie-player reels with automatic reel changes when the pointer crosses reel boundaries.
- DAW/ruling map: tracks, loops, fan-out, quotient/transversal, and homomorphism are named as separate routing rules.

## Commands

Run the full receipt:

```powershell
python scripts\audio\instrument_computer.py demo
```

Run the Holophonor receipt:

```powershell
python scripts\audio\instrument_computer.py holophonor --song "C E" --args 2,3,4
```

Write a spoken WAV with Windows SAPI:

```powershell
python scripts\audio\instrument_computer.py holophonor --song "C E" --args 2,3,4 --speak
```

Check note role:

```powershell
python scripts\audio\instrument_computer.py role E C major
python scripts\audio\instrument_computer.py role E E minor
```

Prove the key bijection:

```powershell
python scripts\audio\instrument_computer.py bijection
```

Prove instrument alphabet independence:

```powershell
python scripts\audio\instrument_computer.py any-instrument
```

Run the persistent shell demo:

```powershell
python scripts\audio\instrument_computer.py shell
```

Run the old movie-reel tape demo:

```powershell
python scripts\audio\instrument_computer.py reel
```

## Verified Claims

- `C E` in coding mode maps to CA ops `add, mul`.
- With args `2,3,4`, Python execution returns `14`.
- The Holophonor emits 8 primary `tongue_isa` faces and 18 broad `instrument.emit_all` faces.
- Haskell is present as a primary face and keeps opcode trace comments such as `-- add (0x00)`.
- STISTA atoms are present for played ops, including op id and CA word provenance.
- E is degree 3 in C major and degree 1 in E minor.
- The same degree program renders into E minor, C major, and G major, then decodes back and computes `5`.
- Piano, bagpipe, harp, guzheng, and a two-tone whistle all encode/decode the same loop program and compute `5`.
- The persistent shell loads `5`, doubles it to `10`, then emits byte `0x0a`.
- The reel-tape demo auto-changes reels and emits byte `0x05`.

## Honest Boundary

This does not make the physical instrument itself magical or independently Turing-complete. The instrument is an input alphabet and rendering surface. Computational power comes from the interpreter with memory and control flow: SCBE CA stack code and the Machine Crystal tape runtime. Finite local runs are bounded by local memory and step limits.

Haskell is primary here because the CA stack program is a sequence of pure transformations. It is less common in mainstream product work mostly because its ecosystem and hiring pool are smaller, lazy evaluation and typeclass-heavy APIs are harder for many teams, and deployment/interop habits are less universal than Python, JavaScript, Go, or Rust.

## Validation

```powershell
python scripts\audio\instrument_computer.py demo
python -m pytest tests\audio\test_instrument_computer_package.py -q
```
