# Cube Hardware Bridge

Connect a physical cube to the SCBE cube controller. A twist fires an opcode; the
program is compiled, run, and spoken back.

```
 physical cube ──(twist events)──▶ transport ──(wire protocol)──▶ cube_bridge
   smart cube (BLE)                 BleSource                       │
   DIY cube (gyro/hall/buttons)     SerialSource                    ▼
   simulator                        SimSource                cube_controller.narrate
                                                              opcode → code → run → voice
```

## Wire protocol

One twist per line, ASCII, standard cube (Singmaster) notation. A microcontroller
just `println`s these over serial:

| Token | Meaning            | Opcode |
|-------|--------------------|--------|
| `R`   | right, clockwise   | add    |
| `R'`  | right, counter-cw  | sub    |
| `L` / `L'` | left            | mul / div |
| `U` / `U'` | up              | inc / dec |
| `D` / `D'` | down            | max / min |
| `F` / `F'` | front           | sqrt / pow |
| `B` / `B'` | back            | mod / neg |
| `F2`  | front twice        | sqrt sqrt |
| `GO`  | commit: run + speak the accumulated program | — |

Accepted suffixes: `'` `i` `3` = counter-clockwise; `2` = twice; none/`1` = clockwise.
The 6 faces map to the 6 Sacred Tongues (R→KO, L→AV, U→RU, D→CA, F→UM, B→DR).

**Compact 1-byte form** (`parse_wire_byte`): low 3 bits = face index into `URFDLB`,
bit 3 set = counter-clockwise. e.g. `0x02` = `F`, `0x0A` = `F'`.

## Transports

```bash
scbe bopit --sim "R U F' GO"        # no hardware — simulate the stream
scbe bopit --serial COM3            # DIY cube on a serial port (needs: pip install pyserial)
scbe bopit --serial /dev/ttyUSB0 --baud 115200
```

Python:

```python
from python.scbe.cube_bridge import bridge, SerialSource, SimSource
bridge(SerialSource("COM3", 115200), voice=True)   # a real cube, spoken aloud
bridge(SimSource("R U GO"))                          # a simulated cube
```

### Bluetooth smart cubes (GoCube / Rubik's Connected / GAN / MoYu)

`BleSource` (needs `pip install bleak`) subscribes to the cube's notify
characteristic and runs a per-brand `decoder` on each packet. `gocube_decode` is a
reference for GoCube/Rubik's-Connected-style packets (face byte + direction byte).

> Verify the decoder against your own cube — brands differ, and **GAN packets are
> AES-128 encrypted** (you must add the known key/IV derivation for your model). The
> serial path is the most portable and is fully tested; BLE is a documented adapter.

```python
from python.scbe.cube_bridge import bridge, BleSource
bridge(BleSource("GoCube", char_uuid="<notify-uuid>"))
```

## DIY cube

The reference firmware [`cube_firmware.ino`](cube_firmware.ino) (Arduino / ESP32)
reads 6 face inputs + a direction toggle, debounces, and emits the wire protocol
over USB serial — flash it, then `scbe bopit --serial <port>`. Adapt the input stage
to hall-effect sensors, rotary encoders, or an MPU-6050 as your build dictates.
