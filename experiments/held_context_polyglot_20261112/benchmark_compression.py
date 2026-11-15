"""Reproducible market-style compression report for HeldContextPacket corpora."""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import lzma
import math
from pathlib import Path
import platform
import random
import statistics
import struct
import subprocess
import sys
import time
from typing import Callable
import zlib

import brotli
import lz4.frame
import zstandard

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "python"))

from held_context import (  # noqa: E402
    EvidenceState,
    HeldContextLane,
    HeldContextPacket,
    LaneFlags,
    LaneKind,
    LaneRole,
    NO_EXPIRY,
)
from sieve_codec import structural_pack, structural_unpack  # noqa: E402


def frame_records(records: list[bytes]) -> bytes:
    output = bytearray(struct.pack("<I", len(records)))
    for record in records:
        output.extend(struct.pack("<I", len(record)))
        output.extend(record)
    return bytes(output)


def parse_records(frame: bytes) -> list[bytes]:
    if len(frame) < 4:
        raise ValueError("truncated record frame")
    count = struct.unpack_from("<I", frame)[0]
    if count > 100_000:
        raise ValueError("record count exceeds benchmark limit")
    offset = 4
    records: list[bytes] = []
    for _ in range(count):
        if len(frame) - offset < 4:
            raise ValueError("truncated record length")
        length = struct.unpack_from("<I", frame, offset)[0]
        offset += 4
        if length > len(frame) - offset:
            raise ValueError("truncated record")
        records.append(frame[offset : offset + length])
        offset += length
    if offset != len(frame):
        raise ValueError("trailing record-frame bytes")
    return records


def make_packet(index: int, *, random_payload: bool) -> bytes:
    rng = random.Random(0xC1A0_0000 + index)
    source_hash = hashlib.sha256(f"source-family:{index // 32}".encode()).digest()
    canonical = hashlib.sha256(f"action-family:{index % 12}".encode()).digest()
    if random_payload:
        text_payload = rng.randbytes(512)
        token_ids = tuple(int.from_bytes(text_payload[pos : pos + 2], "little") for pos in range(0, 512, 2))
    else:
        speech = (
            f"speech-block sector={index % 24} action=route opcode={index % 12} "
            f"subject=agent verb=compile object=tool generation={index // 24}"
        )
        text_payload = speech.encode("utf-8")
        token_ids = tuple(text_payload)
    angle = 2.0 * math.pi * (index % 360) / 360.0
    radius = 150_000 + (index % 7) * 50_000
    route = (
        int(round(radius * math.cos(angle))),
        int(round(radius * math.sin(angle))),
        (index % 3 - 1) * 125_000,
        index % 46 * 10_000,
        -(index % 46) * 10_000,
        (index % 5 - 2) * 75_000,
    )
    evidence = tuple(EvidenceState)[index % len(EvidenceState)]
    lanes = (
        HeldContextLane(
            lane_id=10,
            kind=LaneKind.SPEECH,
            evidence=EvidenceState.PRESENT,
            role=LaneRole.OBSERVED,
            flags=LaneFlags.PINNED | LaneFlags.EXACT_BYTES,
            payload=text_payload,
            canonical_value_id=canonical,
            source_hash=source_hash,
        ),
        HeldContextLane(
            lane_id=11,
            kind=LaneKind.LINGUISTIC,
            evidence=EvidenceState.PRESENT,
            role=LaneRole.DERIVED,
            flags=LaneFlags.COMPRESSIBLE,
            token_ids=token_ids,
            canonical_value_id=canonical,
            source_hash=source_hash,
        ),
        HeldContextLane(
            lane_id=20,
            kind=LaneKind.GEOMETRY,
            evidence=EvidenceState.NEUTRAL,
            role=LaneRole.COMPUTED,
            flags=LaneFlags.COMPRESSIBLE,
            route_q1e6=route,
            payload=struct.pack("<ii", index % 46, index // 46),
            canonical_value_id=canonical,
            source_hash=source_hash,
        ),
        HeldContextLane(
            lane_id=30,
            kind=LaneKind.TOOL,
            evidence=evidence,
            role=LaneRole.CONTROL,
            flags=LaneFlags.NONE,
            expiry_sequence=NO_EXPIRY,
            canonical_value_id=hashlib.sha256(f"control:{evidence.name}".encode()).digest(),
            source_hash=source_hash,
        ),
    )
    packet = HeldContextPacket(
        packet_id=hashlib.sha256(f"packet:{random_payload}:{index}".encode()).digest()[:16],
        generation=index,
        sequence_cutoff=index * 10,
        token_budget=1024,
        breath_q1e6=900_000 + (index % 9) * 25_000,
        radius_q1e6=min(950_000, radius),
        lanes=lanes,
    )
    return packet.encode()


def make_tracked_file_packet(index: int, *, source_name: str, payload: bytes) -> bytes:
    source_hash = hashlib.sha256(("tracked-file:" + source_name).encode()).digest()
    canonical = hashlib.sha256(("tracked-payload:" + source_name).encode()).digest()
    route = (index * 10_000, -(index % 46) * 10_000, (index % 6 - 3) * 100_000)
    lanes = (
        HeldContextLane(
            lane_id=2,
            kind=LaneKind.ROOT,
            evidence=EvidenceState.PRESENT,
            role=LaneRole.OBSERVED,
            flags=LaneFlags.PINNED | LaneFlags.EXACT_BYTES,
            payload=payload,
            canonical_value_id=canonical,
            source_hash=source_hash,
        ),
        HeldContextLane(
            lane_id=8,
            kind=LaneKind.LINGUISTIC,
            evidence=EvidenceState.PRESENT,
            role=LaneRole.DERIVED,
            flags=LaneFlags.COMPRESSIBLE,
            token_ids=tuple(payload),
            canonical_value_id=canonical,
            source_hash=source_hash,
        ),
        HeldContextLane(
            lane_id=21,
            kind=LaneKind.GEOMETRY,
            evidence=EvidenceState.NEUTRAL,
            role=LaneRole.COMPUTED,
            flags=LaneFlags.COMPRESSIBLE,
            route_q1e6=route,
            canonical_value_id=canonical,
            source_hash=source_hash,
        ),
        HeldContextLane(
            lane_id=34,
            kind=LaneKind.RECEIPT,
            evidence=EvidenceState.PRESENT,
            role=LaneRole.PROVENANCE,
            flags=LaneFlags.EXACT_BYTES,
            payload=source_name.encode("utf-8"),
            canonical_value_id=canonical,
            source_hash=source_hash,
        ),
    )
    return HeldContextPacket(
        packet_id=hashlib.sha256(f"tracked-packet:{source_name}:{index}".encode()).digest()[:16],
        generation=index,
        sequence_cutoff=index,
        token_budget=max(1, len(payload)),
        breath_q1e6=1_000_000,
        radius_q1e6=min(900_000, 50_000 + index * 1_000),
        lanes=lanes,
    ).encode()


def tracked_repository_packets() -> list[bytes]:
    relative_paths = (
        "src/storage/uncertainty_context_packet.py",
        "docs/CANONICAL_SYSTEM_STATE.md",
        "docs/specs/CANONICAL_FORMULA_REGISTRY.md",
        "docs/specs/LAYER_INDEX.md",
        "src/scbe_14layer_reference.py",
        "packages/kernel/src/pipeline14.ts",
        "rust/scbe_core/src/lib.rs",
    )
    packets: list[bytes] = []
    index = 0
    for relative_path in relative_paths:
        raw = (REPO_ROOT / relative_path).read_bytes()
        for chunk_index in range(0, len(raw), 4096):
            label = f"{relative_path}#{chunk_index // 4096}"
            packets.append(
                make_tracked_file_packet(index, source_name=label, payload=raw[chunk_index : chunk_index + 4096])
            )
            index += 1
    return packets


def git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


class Codec:
    def __init__(
        self,
        name: str,
        encode: Callable[[bytes], bytes],
        decode: Callable[[bytes], bytes],
        *,
        custom: bool = False,
    ) -> None:
        self.name = name
        self.encode = encode
        self.decode = decode
        self.custom = custom


def sieve_codec(name: str, compressor: Callable[[bytes], bytes], decompressor: Callable[[bytes], bytes]) -> Codec:
    def encode(raw_frame: bytes) -> bytes:
        transformed = frame_records([structural_pack(record) for record in parse_records(raw_frame)])
        return compressor(transformed)

    def decode(encoded: bytes) -> bytes:
        transformed = decompressor(encoded)
        return frame_records([structural_unpack(record) for record in parse_records(transformed)])

    return Codec(name, encode, decode, custom=True)


def codecs() -> list[Codec]:
    zstd22_c = zstandard.ZstdCompressor(level=22)
    zstd_d = zstandard.ZstdDecompressor()
    return [
        Codec("zlib-9", lambda data: zlib.compress(data, 9), zlib.decompress),
        Codec("bzip2-9", lambda data: bz2.compress(data, 9), bz2.decompress),
        Codec("lzma-9", lambda data: lzma.compress(data, preset=9), lzma.decompress),
        Codec("zstd-22", zstd22_c.compress, zstd_d.decompress),
        Codec("brotli-11", lambda data: brotli.compress(data, quality=11), brotli.decompress),
        Codec(
            "lz4-hc-16",
            lambda data: lz4.frame.compress(
                data,
                compression_level=16,
                block_linked=True,
                content_checksum=True,
                store_size=True,
            ),
            lz4.frame.decompress,
        ),
        sieve_codec("hctx-sieve+zlib-9", lambda data: zlib.compress(data, 9), zlib.decompress),
        sieve_codec("hctx-sieve+zstd-22", zstd22_c.compress, zstd_d.decompress),
        sieve_codec("hctx-sieve+brotli-11", lambda data: brotli.compress(data, quality=11), brotli.decompress),
    ]


def measure(codec: Codec, raw: bytes, repeats: int) -> dict[str, object]:
    encode_times: list[float] = []
    decode_times: list[float] = []
    encoded = b""
    for _ in range(repeats):
        start = time.perf_counter_ns()
        candidate = codec.encode(raw)
        encode_times.append((time.perf_counter_ns() - start) / 1_000_000)
        start = time.perf_counter_ns()
        decoded = codec.decode(candidate)
        decode_times.append((time.perf_counter_ns() - start) / 1_000_000)
        if decoded != raw:
            raise RuntimeError(f"{codec.name} failed byte-exact verification")
        if encoded and candidate != encoded:
            raise RuntimeError(f"{codec.name} was nondeterministic across repeats")
        encoded = candidate
    return {
        "method": codec.name,
        "custom": codec.custom,
        "bytes": len(encoded),
        "ratio": len(raw) / len(encoded),
        "savings_percent": 100.0 * (1.0 - len(encoded) / len(raw)),
        "encode_ms_median": statistics.median(encode_times),
        "decode_ms_median": statistics.median(decode_times),
        "verified": True,
    }


def print_table(name: str, raw_bytes: int, rows: list[dict[str, object]]) -> None:
    standard_sizes = [int(row["bytes"]) for row in rows if not row["custom"]]
    best_standard = min(standard_sizes)
    print(f"\n## {name} ({raw_bytes:,} bytes uncompressed)\n")
    print("| Rank | Method | Bytes | Ratio | Saved | Encode ms | Decode ms | Market result |")
    print("|---:|---|---:|---:|---:|---:|---:|---|")
    for rank, row in enumerate(sorted(rows, key=lambda item: (int(item["bytes"]), str(item["method"]))), start=1):
        size = int(row["bytes"])
        if bool(row["custom"]):
            if size < best_standard:
                status = f"BEATS BEST STANDARD by {best_standard - size:,} B"
            elif size == best_standard:
                status = "TIES BEST STANDARD"
            else:
                status = f"TRAILS BEST STANDARD by {size - best_standard:,} B"
        else:
            status = "BEST STANDARD" if size == best_standard else "STANDARD"
        print(
            f"| {rank} | {row['method']} | {size:,} | {float(row['ratio']):.3f}x | "
            f"{float(row['savings_percent']):.2f}% | {float(row['encode_ms_median']):.3f} | "
            f"{float(row['decode_ms_median']):.3f} | {status} |"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structured", type=int, default=256)
    parser.add_argument("--random-control", type=int, default=64)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    if args.structured < 1 or args.random_control < 1 or not 1 <= args.repeats <= 20:
        parser.error("record counts must be positive and repeats must be in [1, 20]")

    structured = [make_packet(index, random_payload=False) for index in range(args.structured)]
    random_control = [make_packet(index, random_payload=True) for index in range(args.random_control)]
    workloads = {
        "structured-sector-packets": structured,
        "random-payload-control": random_control,
        "mixed-packets": structured + random_control,
        "tracked-repository-packets": tracked_repository_packets(),
    }
    report: dict[str, object] = {
        "schema": "hctx-compression-market-v1",
        "repeats": args.repeats,
        "revision": git_revision(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "library_versions": {
            "brotli": getattr(brotli, "__version__", "unknown"),
            "lz4": getattr(lz4.frame, "__version__", "unknown"),
            "zstandard": getattr(zstandard, "__version__", "unknown"),
        },
        "workloads": {},
        "boundary": (
            "Synthetic HeldContextPacket-family benchmark. It establishes lossless size/speed on these corpora, "
            "not general-purpose or state-of-the-art supremacy."
        ),
    }
    for workload_name, records in workloads.items():
        raw = frame_records(records)
        rows = [measure(codec, raw, args.repeats) for codec in codecs()]
        report["workloads"][workload_name] = {
            "records": len(records),
            "raw_bytes": len(raw),
            "results": rows,
        }
        print_table(workload_name, len(raw), rows)
    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("\nAll decoder outputs matched the original framed bytes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
