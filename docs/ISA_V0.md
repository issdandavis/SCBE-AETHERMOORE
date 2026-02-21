# Sacred Tongue ISA v0 (stvm)

This document defines the first executable ISA slice for the Sacred Tongue VM prototype.

## Scope

- VM target: `tools/stvm`
- Assembler target: `tools/stasm`
- Supported tongues in v0:
  - **KO (Kor'aelin)**: control flow + runtime control
  - **CA (Cassisivadan)**: arithmetic / logic
- Encoding: fixed-width 4-byte instructions

## Machine Model

- Registers: `r0..r15` (8-bit unsigned values, wrapping arithmetic)
- Program counter (`pc`): instruction index (not byte index)
- Memory: not exposed in v0
- Halt state: reached by `ko:halt` or stepping beyond program

## Instruction Encoding

Every instruction is 4 bytes:

- `byte0`: opcode
- `byte1`: operand A
- `byte2`: operand B
- `byte3`: operand C

Unused operands must be set to `0`.

## Operand Conventions

- Register IDs: `r0..r15` map to values `0..15`
- Immediate values: unsigned byte `0..255`
- Jump targets: absolute instruction indices `0..255`

## Opcode Table (v0)

### KO tongue opcodes

| Opcode | Mnemonic         | Form                  | Semantics |
|--------|------------------|-----------------------|-----------|
| `0x00` | `ko:nop`         | `ko:nop`              | No-op |
| `0x01` | `ko:halt`        | `ko:halt`             | Stop execution |
| `0x02` | `ko:jmp`         | `ko:jmp <target>`     | `pc = target` |
| `0x03` | `ko:jz`          | `ko:jz <reg>, <tgt>`  | Jump if `reg == 0` |
| `0x04` | `ko:jnz`         | `ko:jnz <reg>, <tgt>` | Jump if `reg != 0` |
| `0x05` | `ko:set`         | `ko:set <reg>, <imm>` | `reg = imm` |
| `0x06` | `ko:mov`         | `ko:mov <dst>, <src>` | `dst = src` |
| `0x07` | `ko:print`       | `ko:print <reg>`      | Emit register value |

### CA tongue opcodes

| Opcode | Mnemonic         | Form                         | Semantics |
|--------|------------------|------------------------------|-----------|
| `0x10` | `ca:add`         | `ca:add <dst>, <a>, <b>`     | `dst = (a + b) mod 256` |
| `0x11` | `ca:sub`         | `ca:sub <dst>, <a>, <b>`     | `dst = (a - b) mod 256` |
| `0x12` | `ca:mul`         | `ca:mul <dst>, <a>, <b>`     | `dst = (a * b) mod 256` |
| `0x13` | `ca:div`         | `ca:div <dst>, <a>, <b>`     | `dst = floor(a / b)`, error on div-by-zero |
| `0x14` | `ca:xor`         | `ca:xor <dst>, <a>, <b>`     | bitwise XOR |
| `0x15` | `ca:and`         | `ca:and <dst>, <a>, <b>`     | bitwise AND |
| `0x16` | `ca:or`          | `ca:or <dst>, <a>, <b>`      | bitwise OR |
| `0x17` | `ca:cmp_eq`      | `ca:cmp_eq <dst>, <a>, <b>`  | `dst = 1 if a == b else 0` |

## Sacred Tongue Token Mapping

For each tongue, raw byte `b` maps to a pronounceable token:

- `token = prefix[b >> 4] + "'" + suffix[b & 0x0F]`

`tools/stasm` includes KO and CA prefix/suffix lists mirrored from `packages/kernel/src/sacredTongues.ts`, so each opcode byte has a canonical Sacred Tongue token alias.

Example aliases:

- `0x05` (KO `set`) => `ko:sil'uu`
- `0x10` (CA `add`) => `ca:bop'a`

Assembler supports both stable mnemonics (`ko:set`) and token aliases (`ko:sil'uu`).

## Minimal ABI (v0)

v0 has no syscall surface yet. The only host-visible operation is `ko:print`, used for deterministic demo output.

Future ABI surface (v1+) should include capability invocation and sealed memory operations.
