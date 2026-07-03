# UTF -> Python Transference Gate - 2026-06-27

Purpose: route Windows/UTF/BOM text through SCBE's Rosetta-style transfer lane before Python tools consume it.

## Why this exists

The validation-gate JSON failure exposed a real class of bug: PowerShell can write UTF-8 with BOM or other Windows encodings, while Python tools often read with strict `encoding="utf-8"` and reject the BOM.

Do not patch every consumer one by one. Use the transference gate.

## Existing systems this connects

- `python/scbe/tongue_isa_binary.py`: STIB, the executable opcode/program binary lane.
- `agents/agent_bus.py`: `tongue_to_binary()` and `binary_to_source()` for CA opcode programs.
- `src/code_prism/emitter.py`: emits code faces from shared IR.
- `python/scbe/rosetta.py`: verified Rosetta song -> many language faces.
- `src/symphonic_cipher/scbe_aethermoore/rosetta/seed_data.py`: concept Rosetta stone; now includes `UTF_TRANSFER`.
- `python/scbe/transference_gate.py`: raw UTF bytes -> Python-safe UTF-8/no-BOM text/source.

## Important boundary

STIB is for executable opcode programs. Arbitrary JSON/text is not STIB.

For text files, use `transference_gate.py`:

```powershell
python -m python.scbe.transference_gate packet path.json
python -m python.scbe.transference_gate normalize path.json --out path.pyutf8.json --receipt path.receipt.json
python -m python.scbe.transference_gate emit-python path.txt --out payload_text.py
```

## Output contract

The gate emits or writes:

- detected encoding
- BOM type
- raw SHA-256
- canonical UTF-8 SHA-256
- byte count
- character count
- Python read encoding: `utf-8`
- notes, such as inferred UTF-16 or removed BOM

## Rule

When a Python tool fails because of UTF/BOM/Windows encoding, do not manually rewrite the file first. Route it through the transference gate, keep the receipt, then feed the normalized file to the Python tool.
