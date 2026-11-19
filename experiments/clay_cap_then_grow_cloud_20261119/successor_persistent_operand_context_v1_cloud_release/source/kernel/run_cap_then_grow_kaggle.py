"""Run the sealed Clay arithmetic code-out campaign on Kaggle CPU storage."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import random
import shutil
import statistics
import subprocess
import sys
from typing import Any, Iterable, Mapping, Sequence
import zipfile

import torch
import torch.nn.functional as F


SCHEMA = "clay.cap-then-grow-arithmetic-codeout.v1"
PREREGISTRATION_COMMIT = "a546670c70d2c4750ff30b3efec374874c1ec1d1"
PREREGISTRATION_SHA256 = "4669cc76d0428915dbbc806817a2ba532bf036cf74beb81786f52a1f4348def6"
DATASET_ID = "issacizrealdavis/clay-input-access-efficacy-input-20261119"
DESCRIPTOR_SCHEMA = "clay.input-access-kaggle-dataset.v1"
PACKET_SCHEMA = "clay.input-access-kaggle-packet.v1"
DESCRIPTOR_SHA256 = "e52f6b4811520d350e5fd1bc1c29b20f672bb9b04aacada2915cc4efdc1a9613"
ARCHIVE_SHA256 = "21ee43590a07a8016757b23d7a9423ec7877146cdaf22b0808ed5de3ca660ef7"
PACKET_MANIFEST_SHA256 = "f4ba71ee68dfea85a56d8665d844d9315c4eec7e0d44629a3cbcb66d3397622b"
BASELINE_MANIFEST_SHA256 = "7f2516af8ae5a122f357565afad60ab412fdf54e76a3018cd8f1ddbfdb702a97"
BASELINE_RESULT_SHA256 = "c5261ada862a2851db0b1dd7e53835b5ddef22299660921527a249a866361482"
CORE_SOURCE_SHA256 = "2cb6b396b4e5bec4427dfb033ba0dbc0bcd4d4aec06e2f5bb5864483dcf22eb8"
PARENT_HASHES = {
    20261134: "e719ca2398f0a96e4c80d2119897ad36202fb34bd8fbe37190655d581411b910",
    20261135: "bb4d912d413dd76174986a89b24f713268e90138808b69107aac01736c218438",
    20261136: "820f0ed122b27261eb91391d4b69efe987f2e8a8e5f79b27c9e2a7f431267929",
}
PARENT_RESULT_HASHES = {
    20261134: "08fc1d8ae8ca46fa2802db66150716b49a69aa0db9d709b5b24940058c68fbf4",
    20261135: "3293b973243f43cc0bf0b100412f806ecb5b3693a1886c4739cf907036ed6ee8",
    20261136: "811eecc628af67e27ef7ca83def7dfe7096d7ee0e21a826a0c89dbd632b2f652",
}
SEEDS = (20261134, 20261135, 20261136)
ARMS = ("candidate", "target_shuffle", "zero_update")
TRAINED_ARMS = ("candidate", "target_shuffle")
OPCODES = {"add": 0, "subtract": 1, "multiply": 2}
UPDATES = 18_000
CHECKPOINT_EVERY = 500
BATCH_SIZE = 128
LEARNING_RATE = 0.002
EXPECTED_TRAINABLE = 140_820
REQUIRED_FREE_BYTES = 25 * 1024**3
TARGET_VOLUME = Path("/tmp")
FROZEN_PREFIXES = ("e.", "g.", "count_head.")
AUTHORITY = "MEASUREMENT_ONLY_NO_PROMOTION"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def stable_hash(value: object) -> str:
    return sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_bytes(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    os.replace(pending, path)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def require_hash(path: Path, expected: str, label: str) -> None:
    observed = sha256_file(path)
    if observed != expected:
        raise RuntimeError(f"{label} hash differs: {observed}")


def require_target_capacity(target: Path) -> dict[str, Any]:
    target = target.resolve(strict=True)
    usage = shutil.disk_usage(target)
    receipt = {
        "path": str(target),
        "device_id": int(target.stat().st_dev),
        "free_bytes": int(usage.free),
        "free_gib": usage.free / 1024**3,
        "required_free_bytes": REQUIRED_FREE_BYTES,
        "required_free_gib": 25.0,
        "writable": os.access(target, os.W_OK),
        "gate_lowered": False,
    }
    receipt["passed"] = bool(receipt["writable"] and usage.free >= REQUIRED_FREE_BYTES)
    if not receipt["passed"]:
        raise RuntimeError(f"target volume failed unchanged 25 GiB gate: {receipt}")
    return receipt


def discover_packet(input_root: Path) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(input_root.rglob("PACKET_DESCRIPTOR.json")):
        value = load_json(path)
        if value.get("schema") == DESCRIPTOR_SCHEMA and value.get("dataset_id") == DATASET_ID:
            matches.append((path, value))
    if len(matches) != 1:
        raise RuntimeError(f"expected one pinned Clay packet, found {len(matches)}")
    path, value = matches[0]
    require_hash(path, DESCRIPTOR_SHA256, "dataset descriptor")
    if value.get("archive", {}).get("sha256") != ARCHIVE_SHA256:
        raise RuntimeError("archive descriptor differs")
    if value.get("packet_manifest", {}).get("sha256") != PACKET_MANIFEST_SHA256:
        raise RuntimeError("packet manifest descriptor differs")
    return path, value


def safe_members(archive: zipfile.ZipFile) -> tuple[zipfile.ZipInfo, ...]:
    members = tuple(archive.infolist())
    for member in members:
        path = PurePosixPath(member.filename)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise RuntimeError(f"unsafe archive member: {member.filename}")
    return members


def verify_runtime(runtime_root: Path, manifest: Mapping[str, Any]) -> None:
    for item in manifest["files"]:
        relative = PurePosixPath(str(item["path"]))
        path = (runtime_root / Path(*relative.parts)).resolve(strict=True)
        if not path.is_relative_to(runtime_root.resolve(strict=True)):
            raise RuntimeError(f"packet path escaped runtime: {relative}")
        if path.stat().st_size != int(item["bytes"]):
            raise RuntimeError(f"packet byte count differs: {relative}")
        require_hash(path, str(item["sha256"]), f"packet file {relative}")
    expected = {"CLAY_INPUT_ACCESS_KAGGLE_PACKET.json", *(str(row["path"]) for row in manifest["files"])}
    actual = {path.relative_to(runtime_root).as_posix() for path in runtime_root.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError("packet inventory differs")


def extract_packet(input_root: Path, runtime_root: Path) -> dict[str, Any]:
    descriptor_path, descriptor = discover_packet(input_root)
    archive_path = descriptor_path.parent / str(descriptor["archive"]["path"])
    require_hash(archive_path, ARCHIVE_SHA256, "packet archive")
    runtime_root.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive_path, "r") as archive:
        archive.extractall(runtime_root, members=safe_members(archive))
    manifest_path = runtime_root / "CLAY_INPUT_ACCESS_KAGGLE_PACKET.json"
    require_hash(manifest_path, PACKET_MANIFEST_SHA256, "packet manifest")
    manifest = load_json(manifest_path)
    if manifest.get("schema") != PACKET_SCHEMA or manifest.get("dataset_id") != DATASET_ID:
        raise RuntimeError("packet identity differs")
    verify_runtime(runtime_root, manifest)
    require_hash(runtime_root / "baseline_run/RUN_MANIFEST.json", BASELINE_MANIFEST_SHA256, "baseline manifest")
    require_hash(runtime_root / "baseline_run/RESULT.json", BASELINE_RESULT_SHA256, "baseline result")
    require_hash(runtime_root / "scbe_repo/python/scbe/clay_frozen_multiview_adapter.py", CORE_SOURCE_SHA256, "frozen core source")
    for seed, expected in PARENT_HASHES.items():
        require_hash(runtime_root / f"baseline_run/parents/seed-{seed}/PARENT.pt", expected, f"parent {seed}")
        require_hash(runtime_root / f"baseline_run/parents/seed-{seed}/RESULT.json", PARENT_RESULT_HASHES[seed], f"parent result {seed}")
    return manifest


@dataclass(frozen=True, slots=True)
class Row:
    operation: str
    opcode: int
    x: int
    y: int
    split: str
    result: int
    prompt: str
    target: str
    identity_sha256: str


def make_row(operation: str, x: int, y: int, split: str) -> Row:
    if operation == "add":
        result = x + y
    elif operation == "subtract":
        result = x - y
    elif operation == "multiply":
        result = x * y
    else:
        raise ValueError(operation)
    opcode = OPCODES[operation]
    raw = bytes((opcode, (x >> 8) & 255, x & 255, (y >> 8) & 255, y & 255))
    byte_tokens = "".join(chr(0xE100 + value) for value in raw)
    target = " " + str(result)[::-1]
    identity = {
        "opcode": opcode,
        "operation": operation,
        "x": x,
        "y": y,
        "target": target,
        "split": split,
    }
    return Row(operation, opcode, x, y, split, result, f"K :{byte_tokens} =>", target, stable_hash(identity))


def build_rows() -> tuple[list[Row], list[Row], str]:
    train: list[Row] = []
    held_out: list[Row] = []
    train.extend(make_row("add", x, y, "train") for x in range(30) for y in range(30))
    train.extend(make_row("subtract", x, y, "train") for x in range(30) for y in range(x + 1))
    train.extend(make_row("multiply", x, y, "train") for x in range(13) for y in range(13))
    held_out.extend(make_row("add", x, y, "held_out") for x in range(30, 60) for y in range(30, 60))
    held_out.extend(make_row("subtract", x, y, "held_out") for x in range(30, 60) for y in range(30, x + 1))
    held_out.extend(make_row("multiply", x, y, "held_out") for x in range(13, 25) for y in range(13, 25))
    identities = [row.identity_sha256 for row in (*train, *held_out)]
    return train, held_out, stable_hash(identities)


def shuffled_pairs(rows: Sequence[Row], seed: int) -> tuple[list[tuple[str, str]], str]:
    targets = [row.target for row in rows]
    groups: dict[tuple[str, int], list[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault((row.operation, len(str(row.result))), []).append(index)
    for group_index, key in enumerate(sorted(groups)):
        indices = groups[key]
        values = [targets[index] for index in indices]
        rng = random.Random(seed + 1_000_003 * (group_index + 1))
        rng.shuffle(values)
        original = [targets[index] for index in indices]
        if len(values) > 1 and values == original:
            values = values[1:] + values[:1]
        for index, target in zip(indices, values, strict=True):
            targets[index] = target
    assignments = [stable_hash({"prompt": row.prompt, "target": target}) for row, target in zip(rows, targets, strict=True)]
    return [(row.prompt, target) for row, target in zip(rows, targets, strict=True)], stable_hash(assignments)


def tensor_map_hash(state: Mapping[str, torch.Tensor], prefixes: Sequence[str] | None = None) -> str:
    digest = sha256()
    for name in sorted(state):
        if prefixes is not None and not name.startswith(tuple(prefixes)):
            continue
        tensor = state[name].detach().cpu().contiguous()
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(str(tensor.dtype).encode("ascii") + b"\0")
        digest.update(canonical_json(list(tensor.shape)))
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def trainable_parameters(model: torch.nn.Module) -> list[torch.nn.Parameter]:
    for parameter in model.parameters():
        parameter.requires_grad = False
    selected = [*model.adapter.parameters(), *model.adapter_head.parameters()]
    for parameter in selected:
        parameter.requires_grad = True
    count = sum(parameter.numel() for parameter in selected)
    if count != EXPECTED_TRAINABLE:
        raise RuntimeError(f"trainable parameter count differs: {count}")
    return selected


def trainable_hash(model: torch.nn.Module) -> str:
    state = {
        name: value
        for name, value in model.state_dict().items()
        if name.startswith(("adapter.", "adapter_head."))
    }
    return tensor_map_hash(state)


@torch.inference_mode()
def generate_text(core: Any, model: torch.nn.Module, prompt: str, stoi: Mapping[str, int], itos: Mapping[int, str], *, max_tokens: int = 8) -> str:
    model.eval()
    model.set_path("adapter")
    ids = [stoi[core.BOS], *(stoi[char] for char in prompt), stoi[core.SEP]]
    logits, state = model(torch.tensor([ids], dtype=torch.long), "action")
    token = int(logits[0, -1].argmax())
    output: list[str] = []
    for _ in range(max_tokens):
        if token == stoi[core.EOS]:
            break
        output.append(itos[token])
        logits, state = model(torch.tensor([[token]], dtype=torch.long), "action", state)
        token = int(logits[0, -1].argmax())
    return "".join(output)


def evaluate(core: Any, model: torch.nn.Module, rows: Sequence[Row], stoi: Mapping[str, int], itos: Mapping[int, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    predictions = []
    by_operation: dict[str, list[bool]] = {name: [] for name in OPCODES}
    for index, row in enumerate(rows):
        predicted = generate_text(core, model, row.prompt, stoi, itos)
        correct = predicted == row.target
        by_operation[row.operation].append(correct)
        predictions.append({
            "index": index,
            "operation": row.operation,
            "x": row.x,
            "y": row.y,
            "target": row.target,
            "prediction": predicted,
            "correct": correct,
            "identity_sha256": row.identity_sha256,
        })
    per_operation = {
        name: {"support": len(values), "exact_accuracy": statistics.fmean(values)}
        for name, values in by_operation.items()
    }
    metrics = {
        "exact_accuracy": statistics.fmean(bool(row["correct"]) for row in predictions),
        "macro_operation_accuracy": statistics.fmean(value["exact_accuracy"] for value in per_operation.values()),
        "per_operation": per_operation,
    }
    return predictions, metrics


def save_model(path: Path, *, model: torch.nn.Module, seed: int, arm: str, dataset_sha256: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(".pt.pending")
    torch.save({
        "schema": f"{SCHEMA}.model",
        "seed": seed,
        "arm": arm,
        "dataset_sha256": dataset_sha256,
        "model_state": model.state_dict(),
    }, pending)
    os.replace(pending, path)
    return sha256_file(path)


def train_one(core: Any, *, parent: Mapping[str, Any], rows: Sequence[tuple[str, str]], seed: int, arm: str, checkpoint_root: Path, dataset_sha256: str, status_path: Path) -> tuple[torch.nn.Module, dict[str, Any]]:
    model = core.FrozenActionModel(len(parent["vocab"]))
    model.load_state_dict(parent["model_state"])
    frozen_before = tensor_map_hash(model.state_dict(), FROZEN_PREFIXES)
    initial_trainable = trainable_hash(model)
    selected = trainable_parameters(model)
    optimizer = torch.optim.Adam(selected, lr=LEARNING_RATE)
    sampler = core.DeterministicBatchSampler(len(rows), BATCH_SIZE, seed)
    checkpoint = core.TwoSlotCheckpoint(checkpoint_root / f"seed-{seed}" / arm)
    restored = checkpoint.load()
    step = 0
    generation = 0
    final_loss = math.nan
    if restored is not None:
        payload, pointer = restored
        expected = {"schema": f"{SCHEMA}.checkpoint", "seed": seed, "arm": arm, "dataset_sha256": dataset_sha256}
        if any(payload.get(key) != value for key, value in expected.items()):
            raise RuntimeError("checkpoint identity differs")
        model.load_state_dict(payload["model_state"])
        optimizer.load_state_dict(payload["optimizer_state"])
        sampler.load_state_dict(payload["sampler_state"])
        torch.set_rng_state(payload["torch_rng_state"])
        step = int(payload["step"])
        generation = int(pointer["generation"]) + 1
        final_loss = float(payload["loss"])
    stoi = {char: index for index, char in enumerate(parent["vocab"])}
    while step < UPDATES:
        model.train()
        indices = sampler.next_indices()
        inputs, labels, masks = core.make_batch(rows, indices, stoi, "cpu")
        logits, _ = model(inputs, "action")
        token_loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), labels.reshape(-1), reduction="none").reshape(labels.shape)
        denominators = masks.sum(dim=1).clamp(min=1)
        loss = ((token_loss * masks).sum(dim=1) / denominators).mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        step += 1
        final_loss = float(loss.detach())
        if step % CHECKPOINT_EVERY == 0 or step == UPDATES:
            checkpoint.save({
                "schema": f"{SCHEMA}.checkpoint",
                "seed": seed,
                "arm": arm,
                "dataset_sha256": dataset_sha256,
                "step": step,
                "loss": final_loss,
                "model_state": model.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "sampler_state": sampler.state_dict(),
                "torch_rng_state": torch.get_rng_state(),
            }, generation)
            write_json(status_path, {
                "schema": f"{SCHEMA}.status",
                "status": "TRAINING",
                "seed": seed,
                "arm": arm,
                "step": step,
                "updates": UPDATES,
                "loss": final_loss,
                "checkpoint_generation": generation,
                "updated_at_utc": utc_now(),
            })
            print(json.dumps({"status": "TRAINING", "seed": seed, "arm": arm, "step": step, "loss": final_loss}), flush=True)
            generation += 1
    frozen_after = tensor_map_hash(model.state_dict(), FROZEN_PREFIXES)
    final_trainable = trainable_hash(model)
    if frozen_after != frozen_before:
        raise RuntimeError(f"frozen tensors changed for {seed}/{arm}")
    changed = sum(
        int(not torch.equal(parent["model_state"][name], value.detach().cpu()))
        * value.numel()
        for name, value in model.state_dict().items()
        if name.startswith(("adapter.", "adapter_head."))
    )
    return model, {
        "steps": step,
        "final_loss": final_loss,
        "trainable_parameters": sum(parameter.numel() for parameter in selected),
        "initial_trainable_sha256": initial_trainable,
        "final_trainable_sha256": final_trainable,
        "changed_tensor_scalar_upper_bound": changed,
        "frozen_before_sha256": frozen_before,
        "frozen_after_sha256": frozen_after,
        "frozen_core_bit_identical": frozen_before == frozen_after,
    }


def comparison(candidate: Sequence[Mapping[str, Any]], control: Sequence[Mapping[str, Any]], metric: str) -> dict[str, Any]:
    left = [float(row["metrics"][metric]) for row in candidate]
    right = [float(row["metrics"][metric]) for row in control]
    left_sd = statistics.stdev(left)
    right_sd = statistics.stdev(right)
    pooled = math.sqrt((left_sd * left_sd + right_sd * right_sd) / 2.0)
    delta = statistics.fmean(left) - statistics.fmean(right)
    return {
        "metric": metric,
        "candidate_mean": statistics.fmean(left),
        "control_mean": statistics.fmean(right),
        "mean_delta": delta,
        "pooled_sample_sd": pooled,
        "two_pooled_sd": 2.0 * pooled,
        "matched_seed_wins": sum(a > b for a, b in zip(left, right, strict=True)),
        "matched_seed_losses": sum(a < b for a, b in zip(left, right, strict=True)),
        "passes": delta > 2.0 * pooled and all(a > b for a, b in zip(left, right, strict=True)),
    }


REPLAY_SOURCE = r'''from __future__ import annotations
import argparse, hashlib, json, statistics, sys
from pathlib import Path
import torch

OPCODES = {"add": 0, "subtract": 1, "multiply": 2}

def stable(value):
    raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
    return hashlib.sha256(raw).hexdigest()

def make(operation,x,y,split):
    result={"add":x+y,"subtract":x-y,"multiply":x*y}[operation]
    opcode=OPCODES[operation]
    raw=bytes((opcode,(x>>8)&255,x&255,(y>>8)&255,y&255))
    prompt="K :"+"".join(chr(0xE100+v) for v in raw)+" =>"
    target=" "+str(result)[::-1]
    ident=stable({"opcode":opcode,"operation":operation,"x":x,"y":y,"target":target,"split":split})
    return {"operation":operation,"x":x,"y":y,"prompt":prompt,"target":target,"identity_sha256":ident}

def rows():
    train=[]; held=[]
    train += [make("add",x,y,"train") for x in range(30) for y in range(30)]
    train += [make("subtract",x,y,"train") for x in range(30) for y in range(x+1)]
    train += [make("multiply",x,y,"train") for x in range(13) for y in range(13)]
    held += [make("add",x,y,"held_out") for x in range(30,60) for y in range(30,60)]
    held += [make("subtract",x,y,"held_out") for x in range(30,60) for y in range(30,x+1)]
    held += [make("multiply",x,y,"held_out") for x in range(13,25) for y in range(13,25)]
    return held, stable([r["identity_sha256"] for r in train+held])

@torch.inference_mode()
def generate(core,model,prompt,stoi,itos):
    model.eval(); model.set_path("adapter")
    ids=[stoi[core.BOS],*[stoi[c] for c in prompt],stoi[core.SEP]]
    logits,state=model(torch.tensor([ids],dtype=torch.long),"action")
    token=int(logits[0,-1].argmax()); out=[]
    for _ in range(8):
        if token==stoi[core.EOS]: break
        out.append(itos[token]); logits,state=model(torch.tensor([[token]]),"action",state); token=int(logits[0,-1].argmax())
    return "".join(out)

def metrics(predictions):
    by={k:[] for k in OPCODES}
    for row in predictions: by[row["operation"]].append(bool(row["correct"]))
    per={k:{"support":len(v),"exact_accuracy":statistics.fmean(v)} for k,v in by.items()}
    return {"exact_accuracy":statistics.fmean(bool(r["correct"]) for r in predictions),"macro_operation_accuracy":statistics.fmean(v["exact_accuracy"] for v in per.values()),"per_operation":per}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--result",type=Path,required=True); p.add_argument("--runtime-root",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    result=json.loads(a.result.read_text(encoding="utf-8")); held,dataset_hash=rows()
    if dataset_hash!=result["dataset"]["identity_sha256"]: raise RuntimeError("independent dataset hash differs")
    scbe=a.runtime_root/"scbe_repo"; sys.path.insert(0,str(scbe)); from python.scbe import clay_frozen_multiview_adapter as core
    checks=[]
    for run in result["runs"]:
        seed=int(run["seed"]); arm=run["arm"]
        path=(a.result.parent/run["model_relative_path"]) if arm!="zero_update" else (a.runtime_root/f"baseline_run/parents/seed-{seed}/PARENT.pt")
        payload=torch.load(path,map_location="cpu",weights_only=False); vocab=payload["vocab"] if "vocab" in payload else result["vocab"]
        state=payload["model_state"]; model=core.FrozenActionModel(len(vocab)); model.load_state_dict(state)
        stoi={c:i for i,c in enumerate(vocab)}; itos={i:c for i,c in enumerate(vocab)}
        predictions=[]
        for index,row in enumerate(held):
            predicted=generate(core,model,row["prompt"],stoi,itos); predictions.append({"index":index,"operation":row["operation"],"x":row["x"],"y":row["y"],"target":row["target"],"prediction":predicted,"correct":predicted==row["target"],"identity_sha256":row["identity_sha256"]})
        observed=metrics(predictions)
        if predictions!=run["predictions"] or observed!=run["metrics"]: raise RuntimeError(f"independent replay differs: {seed}/{arm}")
        checks.append({"seed":seed,"arm":arm,"predictions":len(predictions),"metrics":observed})
    receipt={"schema":"clay.cap-then-grow-independent-replay.v1","status":"PASS","dataset_identity_sha256":dataset_hash,"checks":checks}
    a.output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
if __name__=="__main__": main()
'''


def run_campaign(args: argparse.Namespace) -> dict[str, Any]:
    capacity = require_target_capacity(args.target_volume)
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    status_path = output_root / "STATUS.json"
    runtime_root = args.target_volume / "clay-cap-then-grow-runtime"
    checkpoint_root = args.target_volume / "clay-cap-then-grow-checkpoints"
    if runtime_root.exists():
        raise RuntimeError("foreign or stale runtime root exists")
    packet = extract_packet(args.input_root.resolve(strict=True), runtime_root)
    scbe_root = runtime_root / "scbe_repo"
    sys.path.insert(0, str(scbe_root))
    from python.scbe import clay_frozen_multiview_adapter as core

    torch.set_num_threads(min(4, max(1, os.cpu_count() or 1)))
    torch.use_deterministic_algorithms(True)
    train_rows, held_out_rows, dataset_sha256 = build_rows()
    expected_counts = {"train": 1534, "held_out": 1509}
    if {"train": len(train_rows), "held_out": len(held_out_rows)} != expected_counts:
        raise RuntimeError("dataset row counts differ")
    runs: list[dict[str, Any]] = []
    vocab: list[str] | None = None
    initial_hashes: dict[int, dict[str, str]] = {}
    for seed in SEEDS:
        parent_path = runtime_root / f"baseline_run/parents/seed-{seed}/PARENT.pt"
        parent_result_path = runtime_root / f"baseline_run/parents/seed-{seed}/RESULT.json"
        parent = torch.load(parent_path, map_location="cpu", weights_only=False)
        parent_result = load_json(parent_result_path)
        if int(parent.get("seed", seed)) != seed:
            raise RuntimeError(f"parent seed differs: {seed}")
        if vocab is None:
            vocab = list(parent["vocab"])
        elif vocab != list(parent["vocab"]):
            raise RuntimeError("parent vocab differs by seed")
        missing = [value for value in range(256) if chr(0xE100 + value) not in vocab]
        if missing:
            raise RuntimeError(f"byte-token vocab incomplete: {missing[:8]}")
        stoi = {char: index for index, char in enumerate(vocab)}
        itos = {index: char for index, char in enumerate(vocab)}
        candidate_pairs = [(row.prompt, row.target) for row in train_rows]
        shuffled, shuffle_sha256 = shuffled_pairs(train_rows, seed)
        initial_hashes[seed] = {}
        for arm, pairs in (("candidate", candidate_pairs), ("target_shuffle", shuffled)):
            model, training = train_one(core, parent=parent, rows=pairs, seed=seed, arm=arm, checkpoint_root=checkpoint_root, dataset_sha256=dataset_sha256, status_path=status_path)
            initial_hashes[seed][arm] = training["initial_trainable_sha256"]
            predictions, metrics = evaluate(core, model, held_out_rows, stoi, itos)
            count_score = core.counting_accuracy(model=model, rows=core.counting_rows(True), stoi=stoi, itos=itos, device="cpu")
            model_path = output_root / "models" / f"seed-{seed}" / f"{arm}.pt"
            model_sha256 = save_model(model_path, model=model, seed=seed, arm=arm, dataset_sha256=dataset_sha256)
            runs.append({
                "seed": seed,
                "arm": arm,
                "steps": UPDATES,
                "training": training,
                "metrics": metrics,
                "predictions": predictions,
                "counting_accuracy": count_score,
                "parent_counting_accuracy": float(parent_result["counting_accuracy"]),
                "retention_exact": count_score == float(parent_result["counting_accuracy"]),
                "model_relative_path": model_path.relative_to(output_root).as_posix(),
                "model_sha256": model_sha256,
                "shuffle_assignment_sha256": shuffle_sha256 if arm == "target_shuffle" else None,
            })
        if initial_hashes[seed]["candidate"] != initial_hashes[seed]["target_shuffle"]:
            raise RuntimeError(f"trained arms did not start identically for seed {seed}")
        zero_model = core.FrozenActionModel(len(vocab)); zero_model.load_state_dict(parent["model_state"])
        zero_params = trainable_parameters(zero_model)
        predictions, metrics = evaluate(core, zero_model, held_out_rows, stoi, itos)
        count_score = core.counting_accuracy(model=zero_model, rows=core.counting_rows(True), stoi=stoi, itos=itos, device="cpu")
        runs.append({
            "seed": seed,
            "arm": "zero_update",
            "steps": 0,
            "training": {
                "trainable_parameters": sum(parameter.numel() for parameter in zero_params),
                "initial_trainable_sha256": trainable_hash(zero_model),
                "final_trainable_sha256": trainable_hash(zero_model),
                "frozen_core_bit_identical": True,
            },
            "metrics": metrics,
            "predictions": predictions,
            "counting_accuracy": count_score,
            "parent_counting_accuracy": float(parent_result["counting_accuracy"]),
            "retention_exact": count_score == float(parent_result["counting_accuracy"]),
            "model_relative_path": None,
            "model_sha256": PARENT_HASHES[seed],
            "shuffle_assignment_sha256": None,
        })

    by_arm = {arm: sorted((run for run in runs if run["arm"] == arm), key=lambda row: int(row["seed"])) for arm in ARMS}
    comparisons = {
        f"candidate_vs_{control}": {
            metric: comparison(by_arm["candidate"], by_arm[control], metric)
            for metric in ("exact_accuracy", "macro_operation_accuracy")
        }
        for control in ("target_shuffle", "zero_update")
    }
    zero_check = all(
        all(float(value["exact_accuracy"]) > 0.0 for value in run["metrics"]["per_operation"].values())
        for run in by_arm["candidate"]
    )
    retention = all(bool(run["retention_exact"]) and bool(run["training"]["frozen_core_bit_identical"]) for run in runs)
    effect_gate = all(metric["passes"] for control in comparisons.values() for metric in control.values())
    result = {
        "schema": SCHEMA,
        "status": "AWAITING_INDEPENDENT_REPLAY",
        "authority": AUTHORITY,
        "created_at_utc": utc_now(),
        "preregistration": {"commit": PREREGISTRATION_COMMIT, "sha256": PREREGISTRATION_SHA256},
        "packet": {
            "dataset_id": DATASET_ID,
            "descriptor_sha256": DESCRIPTOR_SHA256,
            "archive_sha256": ARCHIVE_SHA256,
            "packet_manifest_sha256": PACKET_MANIFEST_SHA256,
            "manifest_source_commit": packet["source_commit"],
            "parent_hashes": PARENT_HASHES,
        },
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "torch": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "threads": torch.get_num_threads(),
            "target_capacity": capacity,
        },
        "contract": {
            "seeds": list(SEEDS),
            "updates": UPDATES,
            "checkpoint_every": CHECKPOINT_EVERY,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "loss": "ordinary_torch_cross_entropy",
            "optimizer": "Adam",
            "trainable_parameters": EXPECTED_TRAINABLE,
            "opcode_mapping": OPCODES,
            "promotion": "NONE",
        },
        "dataset": {
            "identity_sha256": dataset_sha256,
            "train_rows": len(train_rows),
            "held_out_rows": len(held_out_rows),
            "record_layout": "opcode:u8 || x:u16be || y:u16be",
        },
        "vocab": vocab,
        "runs": runs,
        "comparisons": comparisons,
        "gates": {
            "effect_size_and_matched_seed_wins": effect_gate,
            "candidate_per_operation_nonzero": zero_check,
            "retention_and_frozen_identity": retention,
            "independent_replay": False,
            "promotion": "NONE",
        },
    }
    result_path = output_root / "RESULT.json"
    write_json(result_path, result)
    replay_path = args.target_volume / "clay_cap_then_grow_independent_replay.py"
    replay_bytes = REPLAY_SOURCE.encode("utf-8")
    replay_path.write_bytes(replay_bytes)
    replay_sha256 = sha256(replay_bytes).hexdigest()
    replay_receipt = output_root / "INDEPENDENT_REPLAY.json"
    command = [sys.executable, str(replay_path), "--result", str(result_path), "--runtime-root", str(runtime_root), "--output", str(replay_receipt)]
    completed = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"independent replay failed: {completed.stdout[-1000:]} {completed.stderr[-1000:]}")
    replay = load_json(replay_receipt)
    if replay.get("status") != "PASS":
        raise RuntimeError("independent replay did not pass")
    result["status"] = "COMPLETE_CONTROLLED_MEASUREMENT_NO_PROMOTION"
    result["independent_replay"] = {
        "program_sha256": replay_sha256,
        "receipt_sha256": sha256_file(replay_receipt),
        "checks": len(replay["checks"]),
    }
    result["gates"]["independent_replay"] = True
    result["gates"]["all_measurement_gates"] = bool(effect_gate and zero_check and retention)
    write_json(result_path, result)
    write_json(status_path, {
        "schema": f"{SCHEMA}.status",
        "status": "COMPLETE",
        "result_sha256": sha256_file(result_path),
        "promotion": "NONE",
        "completed_at_utc": utc_now(),
    })
    return result


def validate_only(runtime_root: Path) -> dict[str, Any]:
    for seed, expected in PARENT_HASHES.items():
        require_hash(runtime_root / f"baseline_run/parents/seed-{seed}/PARENT.pt", expected, f"parent {seed}")
    require_hash(runtime_root / "baseline_run/RUN_MANIFEST.json", BASELINE_MANIFEST_SHA256, "baseline manifest")
    require_hash(runtime_root / "baseline_run/RESULT.json", BASELINE_RESULT_SHA256, "baseline result")
    scbe_root = runtime_root / "scbe_repo"
    sys.path.insert(0, str(scbe_root))
    from python.scbe import clay_frozen_multiview_adapter as core
    train, held, dataset_sha256 = build_rows()
    parent = torch.load(runtime_root / f"baseline_run/parents/seed-{SEEDS[0]}/PARENT.pt", map_location="cpu", weights_only=False)
    model = core.FrozenActionModel(len(parent["vocab"])); model.load_state_dict(parent["model_state"])
    count = sum(parameter.numel() for parameter in trainable_parameters(model))
    stoi = {char: index for index, char in enumerate(parent["vocab"])}
    batch = core.make_batch([(row.prompt, row.target) for row in train], range(2), stoi, "cpu")
    logits, _ = model(batch[0], "action")
    return {
        "schema": f"{SCHEMA}.validation",
        "status": "PASS_NO_TRAINING",
        "dataset_identity_sha256": dataset_sha256,
        "train_rows": len(train),
        "held_out_rows": len(held),
        "trainable_parameters": count,
        "batch_shape": list(batch[0].shape),
        "logit_shape": list(logits.shape),
        "replay_program_sha256": sha256(REPLAY_SOURCE.encode("utf-8")).hexdigest(),
    }


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("/kaggle/input"))
    parser.add_argument("--output-root", type=Path, default=Path("/kaggle/working/clay-cap-then-grow-codeout-20261119-v1"))
    parser.add_argument("--target-volume", type=Path, default=TARGET_VOLUME)
    parser.add_argument("--validate-only", type=Path)
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    args = parse_args(arguments)
    if args.validate_only is not None:
        print(json.dumps(validate_only(args.validate_only.resolve(strict=True)), sort_keys=True))
        return 0
    result = run_campaign(args)
    print(json.dumps({"status": result["status"], "gates": result["gates"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
