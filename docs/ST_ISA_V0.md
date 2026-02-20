# Sacred Tongue ISA v0

Last updated: February 19, 2026
Status: Prototype ISA for STVM Phase-1

## Scope
This is the bootstrap ISA for Sacred Tongue VM.
It does not claim full 1,536 semantic ops yet.
It defines a deterministic executable subset.

## Opcode Space
- Tongues: 6 (`KO`, `CA`, `RU`, `AV`, `DR`, `UM`)
- Per-tongue opcode byte: `0..255`
- Total addressable instruction heads: `6 * 256 = 1536`
- Implemented in v0: 29 instructions

## Instruction Encoding
Fixed-width 8-byte instruction:

```
byte 0: tongue_id   (KO=0, CA=1, RU=2, AV=3, DR=4, UM=5)
byte 1: opcode      (0..255)
byte 2: a           (u8)
byte 3: b           (u8)
byte 4..7: imm      (i32 little-endian)
```

Container format (`STV1`):

```
offset 0..3:  magic = "STV1"
offset 4..7:  instruction_count (u32 LE)
offset 8.. :  instruction stream (count * 8 bytes)
```

## Register File
- `r0..r20` (21 registers, integer semantics in v0)

## Tongue Families (v0)

### KO Control Flow
- `KO.NOP` `0x00`
- `KO.HALT` `0x01`
- `KO.JMP target` `0x02`
- `KO.JZ reg target` `0x03`
- `KO.JNZ reg target` `0x04`
- `KO.CALL target` `0x05`
- `KO.RET` `0x06`
- `KO.YIELD` `0x07`

### CA Arithmetic and Logic
- `CA.MOVI reg imm` `0x10`
- `CA.MOV dst src` `0x11`
- `CA.ADD dst src` `0x12`
- `CA.SUB dst src` `0x13`
- `CA.MUL dst src` `0x14`
- `CA.DIV dst src` `0x15`
- `CA.MOD dst src` `0x16`
- `CA.CMP lhs rhs` `0x17`
- `CA.AND dst src` `0x18`
- `CA.OR dst src` `0x19`
- `CA.XOR dst src` `0x1A`

### RU Memory
- `RU.LOAD reg addr` `0x20`
- `RU.STORE reg addr` `0x21`

### AV IPC and Syscalls
- `AV.SEND reg channel` `0x30`
- `AV.RECV reg channel` `0x31`
- `AV.SYSCALL id` `0x32`

### DR Validation
- `DR.ASSERT reg` `0x40`
- `DR.VERIFY reg` `0x41`

### UM Security Ops
- `UM.HASH reg` `0x50`
- `UM.REDACT reg` `0x51`

## Sacred Token Heads
Instruction heads can be authored as:
- mnemonic: `KO.JMP`
- sacred token form: `ko:<prefix>'<suffix>`

`stasm` decodes sacred token heads using `packages/sixtongues/sixtongues.py`.

## Example
Assembly:

```asm
start:
  CA.MOVI r0 2
  CA.MOVI r1 3
  CA.ADD r0 r1
  AV.SEND r0 1
  KO.HALT
```

Build and run:

```powershell
python scripts/stasm.py examples/stvm/hello_world.sta -o examples/stvm/hello_world.stv --listing
python scripts/stvm.py run examples/stvm/hello_world.stv
```

## Out of Scope in v0
- Floating-point ops
- Vectorized PHDM register ops
- Privilege ring enforcement in interpreter core
- Syscall ABI and host HAL
- JIT/AOT backends

