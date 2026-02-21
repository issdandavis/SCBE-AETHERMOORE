# STVM Execution Model v0

Last updated: February 19, 2026
Status: Deterministic interpreter model

## Runtime State
- Registers: `r0..r20`
- Memory: 1024 integer words
- Program counter: instruction index
- Call stack: return addresses
- Event log: deterministic side-channel for `SEND`, `RECV`, `SYSCALL`, `VERIFY`, `YIELD`
- Mailbox: channel -> last sent integer

## Determinism
- No wall-clock dependency in instruction semantics
- Fixed-width decode
- Integer arithmetic semantics
- Explicit trap states for illegal operations

## Trap Conditions
- `pc` out of program bounds
- step limit exceeded
- division/modulo by zero
- failed `DR.ASSERT`
- unknown opcode/tongue

## Instruction Semantics (Summary)
- Control flow (`KO`) mutates `pc` and call stack
- Arithmetic (`CA`) mutates registers and comparison state
- Memory (`RU`) maps addresses via modulo memory size
- IPC/syscalls (`AV`) append events and use mailbox
- Validation (`DR`) enforces predicates and logs verify events
- Security (`UM`) hashes or redacts register values

## Assembly Flow
1. Source `.sta` parsed by `stasm`.
2. Labels resolved to absolute instruction indices.
3. Bytecode emitted with `STV1` header.
4. `stvm` loads and executes.

## Phase-1 Tooling
- Assembler: `scripts/stasm.py`
- VM runner/disassembler: `scripts/stvm.py`
- Core model: `scripts/stvm_core.py`

## Example Workflow
```powershell
python scripts/stasm.py examples/stvm/hello_world.sta -o examples/stvm/hello_world.stv --listing
python scripts/stvm.py dis examples/stvm/hello_world.stv
python scripts/stvm.py run examples/stvm/hello_world.stv
```

## Next Steps for Phase-2
- Enforce trust rings (`CORE/INNER/OUTER/WALL`) in syscall gate
- Add process model and scheduler hooks
- Add Sacred Tongue IPC envelope integration
- Add PHDM-aware typed register classes

