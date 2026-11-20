"""Safely audit Clay parent vocabularies without importing Torch or unpickling.

PyTorch checkpoints are ZIP containers whose ``data.pkl`` describes tensors and
metadata. This scanner inspects pickle opcodes as inert data and accepts only
the exact list shape used for the vocabulary field. It never executes pickle
instructions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickletools
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import clay_vqcc_byte_codec as codec


AUDIT_SCHEMA = "clay.vqcc-parent-vocab-audit.v1"
MAX_DATA_PICKLE_BYTES = 1 << 20
UNICODE_OPS = frozenset(("BINUNICODE", "SHORT_BINUNICODE", "UNICODE"))
MEMO_OPS = frozenset(("BINPUT", "LONG_BINPUT", "PUT", "MEMOIZE"))


def _sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _skip_memo(ops: Sequence[tuple[Any, Any, int]], index: int) -> int:
    while index < len(ops) and ops[index][0].name in MEMO_OPS:
        index += 1
    return index


def extract_vocab(checkpoint: str | Path) -> tuple[str, ...]:
    """Extract the one explicit ``vocab`` list through an opcode shape check."""

    checkpoint = Path(checkpoint).resolve(strict=True)
    with zipfile.ZipFile(checkpoint, "r") as archive:
        candidates = [name for name in archive.namelist() if name.endswith("/data.pkl")]
        if len(candidates) != 1:
            raise ValueError(f"checkpoint must contain exactly one /data.pkl: {checkpoint}")
        info = archive.getinfo(candidates[0])
        if info.file_size > MAX_DATA_PICKLE_BYTES:
            raise ValueError(f"checkpoint data.pkl exceeds the audit cap: {info.file_size}")
        payload = archive.read(info)
    ops = list(pickletools.genops(payload))
    vocab_keys = [
        index
        for index, (opcode, argument, _position) in enumerate(ops)
        if opcode.name in UNICODE_OPS and argument == "vocab"
    ]
    if len(vocab_keys) != 1:
        raise ValueError(f"checkpoint must contain exactly one Unicode vocab key: {vocab_keys}")
    index = _skip_memo(ops, vocab_keys[0] + 1)
    if index >= len(ops) or ops[index][0].name != "EMPTY_LIST":
        raise ValueError("vocab key is not followed by an explicit empty list")
    index = _skip_memo(ops, index + 1)
    if index >= len(ops) or ops[index][0].name != "MARK":
        raise ValueError("vocab list does not begin with MARK")
    index += 1
    tokens: list[str] = []
    while index < len(ops):
        opcode, argument, _position = ops[index]
        if opcode.name == "APPENDS":
            break
        if opcode.name not in UNICODE_OPS or not isinstance(argument, str):
            raise ValueError(f"unexpected opcode inside vocab list: {opcode.name}")
        tokens.append(argument)
        index = _skip_memo(ops, index + 1)
    else:
        raise ValueError("vocab list has no APPENDS terminator")
    codec.validate_parent_vocab(tokens, expected_sha256=codec.PARENT_VOCAB_SHA256)
    return tuple(tokens)


def audit_checkpoints(
    checkpoints: Mapping[str, str | Path],
    *,
    expected_checkpoint_sha256: Mapping[str, str],
) -> dict[str, Any]:
    if not checkpoints or set(checkpoints) != set(expected_checkpoint_sha256):
        raise ValueError("checkpoint paths and expected hashes must have identical non-empty keys")
    rows = []
    common_vocab: tuple[str, ...] | None = None
    for seed in sorted(checkpoints):
        path = Path(checkpoints[seed]).resolve(strict=True)
        actual_checkpoint_sha256 = _sha256_file(path)
        if actual_checkpoint_sha256 != expected_checkpoint_sha256[seed]:
            raise ValueError(f"checkpoint hash differs for seed {seed}")
        vocab = extract_vocab(path)
        if common_vocab is None:
            common_vocab = vocab
        elif vocab != common_vocab:
            raise ValueError(f"checkpoint vocabulary differs for seed {seed}")
        rows.append(
            {
                "seed": seed,
                "checkpoint_bytes": path.stat().st_size,
                "checkpoint_sha256": actual_checkpoint_sha256,
                "vocab_sha256": codec.canonical_vocab_sha256(vocab),
                "vocab_size": len(vocab),
            }
        )
    assert common_vocab is not None
    validation = codec.validate_parent_vocab(
        common_vocab,
        expected_sha256=codec.PARENT_VOCAB_SHA256,
    )
    expected_vocab = tuple(
        [
            "\x00",
            "\x02",
            "\x1f",
            "\x03",
            " ",
            *list("0123456789"),
            ":",
            "=",
            ">",
            "C",
            "K",
            *(codec.byte_token(value) for value in range(codec.BYTE_TOKEN_COUNT)),
        ]
    )
    return {
        "schema": AUDIT_SCHEMA,
        "status": "PASS_SAFE_OPCODE_SCAN",
        "method": "zipfile-plus-pickletools-no-unpickle-v1",
        "checkpoints": rows,
        "vocab": validation,
        "exact_fixture_match": common_vocab == expected_vocab,
        "torch_imported": False,
        "pickle_executed": False,
        "model_loaded": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint",
        action="append",
        nargs=3,
        metavar=("SEED", "PATH", "SHA256"),
        required=True,
    )
    args = parser.parse_args(argv)
    checkpoints = {seed: path for seed, path, _sha256 in args.checkpoint}
    hashes = {seed: sha256 for seed, _path, sha256 in args.checkpoint}
    result = audit_checkpoints(checkpoints, expected_checkpoint_sha256=hashes)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
