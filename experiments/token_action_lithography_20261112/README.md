# Token action lithography fixture

This fixture proves a narrow deterministic path:

1. five declared token identities are built into an exact EOT lattice;
2. each identity is explicitly bound to an existing semantic VM contract;
3. the mask assembles to bytes and disassembles to the same instructions;
4. the bounded toy VM executes `LOAD`, `COMPARE`, `VERIFY`, and `HALT`.

The wafer-growth receipt is attached as provenance only. It grants no compiler
or execution authority. The fixture does not train weights, infer a binding,
invoke the physical virtual-lithography simulator, or authorize an OS/shell.

Rebuild from the repository root:

```powershell
python scripts/tokenizer/build_eot_token_lattice.py experiments/token_action_lithography_20261112/teacher.json experiments/token_action_lithography_20261112/lattice.json --force
python scripts/tokenizer/build_token_action_lithography.py experiments/token_action_lithography_20261112/lattice.json experiments/token_action_lithography_20261112/bindings.json experiments/token_action_lithography_20261112/result.json --execute --force
```
