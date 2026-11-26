"""
Cube hardware bridge — connect a physical cube to the controller.
=================================================================

A real cube (a smart cube over Bluetooth, or a DIY cube with a gyro / hall sensors
on a microcontroller) emits TWIST EVENTS. This bridge ingests them from any
transport and feeds them into cube_controller.narrate, so a physical turn fires an
opcode, builds a program, runs it, and speaks the command.

Transports (a MoveSource yields move tokens):
  SimSource     synthetic twists — tests / demo, no hardware needed
  SerialSource  USB / UART line protocol (Arduino / ESP32 + MPU-6050 or hall sensors)
  BleSource     Bluetooth smart cube (GoCube / Rubik's Connected / GAN ...) via bleak

The WIRE PROTOCOL any microcontroller can speak — one twist per line, ASCII, standard
cube notation:  R  U'  F2  L  ...  and the literal token  GO  to commit+run+speak the
accumulated program. A compact 1-byte form is also decoded: low 3 bits = face index
into URFDLB, bit 3 = counter-clockwise. See docs/hardware/CUBE_BRIDGE.md + the
reference firmware docs/hardware/cube_firmware.ino.
"""

from __future__ import annotations

from typing import Callable, Iterable, Iterator, List, Optional

from . import cube_controller as C

WIRE_FACES = "URFDLB"  # canonical face order; index 0..5
COMMIT = "GO"  # the wire token that runs the accumulated program


def parse_wire(line: str) -> List[str]:
    """One wire line -> move tokens. 'R'->[R], "U'"/Ui/U3->[U'], 'F2'->[F,F], 'GO'->[GO]."""
    out: List[str] = []
    for tok in line.strip().upper().replace("’", "'").split():
        if tok == COMMIT:
            out.append(COMMIT)
            continue
        face = tok[0]
        if face not in WIRE_FACES:
            raise ValueError("bad wire token %r (faces are %s)" % (tok, WIRE_FACES))
        rest = tok[1:]
        if rest in ("", "1"):
            out.append(face)
        elif rest in ("'", "I", "3"):
            out.append(face + "'")
        elif rest == "2":
            out += [face, face]
        else:
            raise ValueError("bad wire suffix %r" % tok)
    return out


def parse_wire_byte(b: int) -> str:
    """Compact form: low 3 bits = face index into URFDLB, bit 3 = counter-clockwise."""
    fi = b & 0x07
    if fi >= len(WIRE_FACES):
        raise ValueError("face index %d out of range" % fi)
    return WIRE_FACES[fi] + ("'" if (b >> 3) & 1 else "")


# --- transports -----------------------------------------------------------------
class MoveSource:
    """A stream of move tokens. Subclasses implement moves()."""

    def moves(self) -> Iterator[str]:
        raise NotImplementedError

    def close(self) -> None:
        pass


class SimSource(MoveSource):
    """Synthetic twists from a list or a wire string — no hardware."""

    def __init__(self, seq: Iterable[str] | str):
        if isinstance(seq, str):
            seq = parse_wire(seq)
        self.seq = list(seq)

    def moves(self) -> Iterator[str]:
        yield from self.seq


class SerialSource(MoveSource):
    """A cube on a serial/USB port (Arduino/ESP32 printing wire lines). Needs pyserial."""

    def __init__(self, port: str, baud: int = 115200, timeout: float = 1.0):
        try:
            import serial  # pyserial
        except Exception as e:  # pragma: no cover - optional dep
            raise RuntimeError("SerialSource needs pyserial: pip install pyserial") from e
        self._ser = serial.Serial(port, baud, timeout=timeout)

    def moves(self) -> Iterator[str]:
        while True:
            raw = self._ser.readline()
            if not raw:
                continue
            line = raw.decode("ascii", "ignore").strip()
            if line:
                yield from parse_wire(line)

    def close(self) -> None:
        try:
            self._ser.close()
        except Exception:  # pragma: no cover
            pass


def gocube_decode(data: bytes) -> List[str]:
    """Reference decoder for GoCube / Rubik's Connected style notifications: turn
    packets carry a face byte (0..5) + a direction byte. Best-effort — VERIFY against
    your own cube's stream; brands differ (GAN packets are AES-128 encrypted)."""
    out: List[str] = []
    for i in range(0, len(data) - 1, 2):
        face, direction = data[i] & 0x07, data[i + 1]
        if face < len(WIRE_FACES):
            out.append(WIRE_FACES[face] + ("'" if direction else ""))
    return out


class BleSource(MoveSource):
    """A Bluetooth smart cube. Subscribes to a notify characteristic and runs `decoder`
    on each packet. Needs bleak. decoder defaults to gocube_decode (verify per brand)."""

    def __init__(self, address_or_name: str, char_uuid: str, decoder: Callable[[bytes], List[str]] = gocube_decode):
        try:
            import bleak  # noqa: F401  (cross-platform BLE)
        except Exception as e:  # pragma: no cover - optional dep
            raise RuntimeError("BleSource needs bleak: pip install bleak") from e
        self.target, self.char_uuid, self.decoder = address_or_name, char_uuid, decoder

    def moves(self) -> Iterator[str]:  # pragma: no cover - needs a device
        import asyncio
        import queue
        from bleak import BleakClient, BleakScanner

        q: "queue.Queue[str]" = queue.Queue()

        async def run():
            dev = self.target
            if not all(c in "0123456789ABCDEFabcdef:" for c in self.target):
                found = await BleakScanner.find_device_by_name(self.target)
                dev = found.address if found else self.target
            async with BleakClient(dev) as client:

                def cb(_h, data):
                    for mv in self.decoder(bytes(data)):
                        q.put(mv)

                await client.start_notify(self.char_uuid, cb)
                while True:
                    await asyncio.sleep(3600)

        import threading

        threading.Thread(target=lambda: asyncio.run(run()), daemon=True).start()
        while True:
            yield q.get()


# --- the bridge loop ------------------------------------------------------------
def bridge(source: MoveSource, voice: bool = False, on_command: Optional[Callable[[List[int]], None]] = None) -> int:
    """Read twists from `source`, announce each live, and on a GO token (or end of
    stream) run+speak the accumulated program. A physical turn -> a spoken command."""
    pending: List[str] = []

    def commit():
        if pending:
            prog, _lines = C.narrate(list(pending), voice)
            if on_command:
                on_command(prog)
            pending.clear()

    try:
        for m in source.moves():
            if m == COMMIT:
                commit()
            elif m in C.MOVE_OP:
                print("  twist: " + C.say_move(m))
                C.speak(C.say_move(m), voice) if voice else None
                pending.append(m)
    except (KeyboardInterrupt, StopIteration):
        pass
    finally:
        commit()
        source.close()
    return 0


def _demo() -> None:
    print("Cube hardware bridge — simulated cube (no hardware):\n")
    bridge(SimSource("R U F' GO  L L GO"))


if __name__ == "__main__":
    _demo()
