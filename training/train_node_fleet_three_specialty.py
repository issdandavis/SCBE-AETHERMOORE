#!/usr/bin/env python3
"""Train 3 specialty AI heads + fleet coordinator using SCBE-style context spin scoring."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

try:
    from huggingface_hub import HfApi, get_token
except Exception:  # noqa: BLE001
    HfApi = None  # type: ignore[assignment]
    get_token = None  # type: ignore[assignment]


TOKEN_RE = re.compile(r"[A-Za-z0-9_:/.\-]+")
GIST_ID_RE = re.compile(r"([0-9a-f]{32})", re.IGNORECASE)
DEFAULT_GIST = "https://colab.research.google.com/gist/issdandavis/c38b2eface8d456b90c6bf02678871d8/copy-of-spiralverse-protocol-ai-training-data-generator.ipynb"
DEFAULT_PATTERNS = ("training/**/*.jsonl", "training-data/**/*.jsonl")


@dataclass
class Record:
    text: str
    source: str
    raw: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train SCBE node-fleet with 3 specialist heads")
    parser.add_argument("--constants", default="training/config/node_fleet_constants.json")
    parser.add_argument("--run-dir", default=None, help="Output run directory")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--embedding-dim", type=int, default=320)
    parser.add_argument("--learning-rate", type=float, default=0.16)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-samples", type=int, default=50000)
    parser.add_argument("--min-samples", type=int, default=120)
    parser.add_argument("--model-repo", default="issdandavis/spiralverse-ai-federated-v1")
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--conversation-spin-gist", default=DEFAULT_GIST)
    parser.add_argument("--local-glob", action="append", default=[])
    return parser.parse_args()


def _tok(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _extract_text(row: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key in ("event_type", "dataset", "message", "reason", "status", "product"):
        if row.get(key) is not None:
            chunks.append(str(row[key]))
    payload = row.get("event_payload")
    if isinstance(payload, dict):
        chunks.append(json.dumps(payload, sort_keys=True))
    targets = row.get("targets")
    if isinstance(targets, list):
        chunks.extend(str(t) for t in targets)
    if row.get("source_text") is not None:
        chunks.append(str(row["source_text"]))
    return " ".join(chunks).strip()


def _hash_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_jsonl_records(patterns: list[str], max_samples: int) -> list[Record]:
    out: list[Record] = []
    seen: set[str] = set()
    for pattern in patterns:
        for path in sorted(Path(".").glob(pattern)):
            if not path.is_file():
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            row = json.loads(line)
                        except Exception:  # noqa: BLE001
                            continue
                        if not isinstance(row, dict):
                            continue
                        text = _extract_text(row)
                        if not text:
                            continue
                        key = _hash_key(text)
                        if key in seen:
                            continue
                        seen.add(key)
                        out.append(Record(text=text, source=str(path), raw=row))
                        if len(out) >= max_samples:
                            return out
            except Exception:  # noqa: BLE001
                continue
    return out


def load_conversation_spin_records(gist_url: str, cap: int = 2500) -> list[Record]:
    m = GIST_ID_RE.search(gist_url)
    if not m:
        return []
    gist_id = m.group(1)
    try:
        proc = subprocess.run(
            ["gh", "api", f"/gists/{gist_id}"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        payload = json.loads(proc.stdout)
    except Exception:  # noqa: BLE001
        return []

    files = payload.get("files", {})
    if not isinstance(files, dict) or not files:
        return []

    notebook_text = None
    for v in files.values():
        if isinstance(v, dict) and isinstance(v.get("content"), str) and v.get("filename", "").endswith(".ipynb"):
            notebook_text = v["content"]
            break
    if not notebook_text:
        return []

    try:
        nb = json.loads(notebook_text)
    except Exception:  # noqa: BLE001
        return []

    out: list[Record] = []
    seen: set[str] = set()
    for cell in nb.get("cells", []):
        if not isinstance(cell, dict):
            continue
        src = cell.get("source", [])
        if isinstance(src, list):
            text = "".join(str(x) for x in src).strip()
        else:
            text = str(src).strip()
        if len(text) < 20:
            continue
        row = {"source_text": text, "event_type": "conversation_spin_cell", "dataset": "conversation_spin_notebook"}
        key = _hash_key(text)
        if key in seen:
            continue
        seen.add(key)
        out.append(Record(text=text, source=f"gist:{gist_id}", raw=row))
        if len(out) >= cap:
            break
    return out


def augment_records(records: list[Record], min_samples: int, seed: int) -> list[Record]:
    if len(records) >= min_samples:
        return records
    rng = random.Random(seed)
    out = list(records)
    for r in list(records):
        toks = _tok(r.text)
        if len(toks) < 8:
            continue
        variants = [
            " ".join(toks[: len(toks) // 2]),
            " ".join(toks[len(toks) // 2 :]),
            " ".join(toks[::2]),
            " ".join(toks[1::2]),
        ]
        for v in variants:
            if len(v) < 20:
                continue
            out.append(Record(text=v, source=f"{r.source}#aug", raw=dict(r.raw)))
            if len(out) >= min_samples:
                return out
    while len(out) < min_samples:
        out.append(rng.choice(records))
    return out


def hashed_embed(text: str, dim: int) -> np.ndarray:
    vec = np.zeros((dim,), dtype=np.float32)
    for tok in _tok(text):
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "big", signed=False) % dim
        sign = -1.0 if (h[4] & 1) else 1.0
        vec[idx] += sign
    n = float(np.linalg.norm(vec))
    if n > 0:
        vec /= n
    return vec


def vectorize(records: list[Record], dim: int) -> np.ndarray:
    x = np.zeros((len(records), dim), dtype=np.float32)
    for i, r in enumerate(records):
        x[i] = hashed_embed(r.text, dim)
    return x


def softmax(z: np.ndarray) -> np.ndarray:
    x = z - z.max(axis=1, keepdims=True)
    ex = np.exp(x)
    return ex / ex.sum(axis=1, keepdims=True)


def ce(p: np.ndarray, y: np.ndarray) -> float:
    eps = 1e-9
    rows = np.arange(y.shape[0])
    return float(-np.mean(np.log(p[rows, y] + eps)))


def acc(p: np.ndarray, y: np.ndarray) -> float:
    pred = np.argmax(p, axis=1)
    return float(np.mean((pred == y).astype(np.float32)))


def parse_ts(record: Record) -> float:
    raw = record.raw
    for key in ("created_at_utc", "timestamp", "generated_at"):
        v = raw.get(key)
        if not isinstance(v, str):
            continue
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:  # noqa: BLE001
            continue
    return 0.0


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def spin_components(
    text: str,
    raw: dict[str, Any],
    spec: dict[str, Any],
    constants: dict[str, Any],
    now_ts: float,
    ts: float,
) -> dict[str, float]:
    toks = set(_tok(text))
    ctx_terms = [str(x).lower() for x in spec.get("context_terms", [])]
    non_terms = [str(x).lower() for x in spec.get("non_interest_terms", [])]
    action_terms = [str(x).lower() for x in spec.get("action_targets", [])]

    context_hits = sum(1 for t in ctx_terms if t in toks)
    non_hits = sum(1 for t in non_terms if t in toks)
    action_hits = sum(1 for t in action_terms if t in toks)
    context_score = _safe_div(context_hits, max(1, len(ctx_terms)))
    non_interest_score = _safe_div(non_hits, max(1, len(non_terms)))
    relevance_score = min(1.0, 0.6 * _safe_div(action_hits, max(1, len(action_terms))) + 0.4 * (1.0 if context_hits > 0 else 0.0))
    interest_score = min(1.0, 0.5 * context_score + 0.5 * relevance_score)

    txt = text.lower()
    ternary_flux = 1.0 if any(k in txt for k in ("ternary", "dual_ternary", "-1", "mirror_shift")) else 0.0
    drift_raw = max(0.0, non_interest_score - context_score)
    hyperbolic_drift = math.tanh(drift_raw)
    if ts <= 0.0:
        memory_retention = 0.5
    else:
        hours = max(0.0, (now_ts - ts) / 3600.0)
        memory_retention = math.exp(-hours / 72.0)
    consensus_coherence = 1.0 if any(k in txt for k in ("consensus", "quorum", "byzantine", "coherence", "trust")) else 0.0
    harmonic_r = float(constants["math_extensions"].get("harmonic_R", 1.5))
    harmonic_wall_signal = min(1.0, (harmonic_r ** (max(0.0, context_score - non_interest_score) ** 2)) - 1.0)

    return {
        "context": float(context_score),
        "non_interest": float(non_interest_score),
        "interest": float(interest_score),
        "relevancy": float(relevance_score),
        "ternary_flux": float(ternary_flux),
        "hyperbolic_drift": float(hyperbolic_drift),
        "memory_retention": float(memory_retention),
        "consensus_coherence": float(consensus_coherence),
        "harmonic_wall_signal": float(harmonic_wall_signal),
    }


def spin_score(parts: dict[str, float], constants: dict[str, Any]) -> float:
    bw = constants["base_weights"]
    me = constants["math_extensions"]
    base = bw["context"] * (parts["context"] - parts["non_interest"]) + bw["interest"] * parts["interest"] + bw["relevancy"] * parts["relevancy"]
    extra = (
        me["k_ternary"] * parts["ternary_flux"]
        - me["k_drift"] * parts["hyperbolic_drift"]
        + me["k_memory"] * parts["memory_retention"]
        + me["k_coherence"] * parts["consensus_coherence"]
        + me["k_harmonic"] * parts["harmonic_wall_signal"]
    )
    return float(base + extra)


def train_binary_classifier(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    epochs: int,
    lr: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, float]]]:
    rng = np.random.default_rng(seed)
    n, d = x_train.shape
    w = rng.normal(0.0, 0.01, size=(2, d)).astype(np.float32)
    b = np.zeros((2,), dtype=np.float32)
    history: list[dict[str, float]] = []

    y_oh = np.zeros((n, 2), dtype=np.float32)
    y_oh[np.arange(n), y_train] = 1.0

    for e in range(1, epochs + 1):
        lrate = lr * (0.97 ** (e - 1))
        p_train = softmax(x_train @ w.T + b)
        loss_t = ce(p_train, y_train)
        acc_t = acc(p_train, y_train)

        grad = (p_train - y_oh) / float(n)
        grad_w = grad.T @ x_train
        grad_b = grad.mean(axis=0)
        w -= lrate * grad_w
        b -= lrate * grad_b

        p_val = softmax(x_val @ w.T + b)
        loss_v = ce(p_val, y_val)
        acc_v = acc(p_val, y_val)
        history.append(
            {
                "epoch": float(e),
                "learning_rate": float(lrate),
                "train_loss": float(loss_t),
                "train_accuracy": float(acc_t),
                "val_loss": float(loss_v),
                "val_accuracy": float(acc_v),
            }
        )
    return w, b, history


def train_fleet_coordinator(
    p_train: np.ndarray,
    y_train: np.ndarray,
    p_val: np.ndarray,
    y_val: np.ndarray,
    epochs: int,
    lr: float,
    seed: int,
    situational: dict[str, float],
) -> tuple[np.ndarray, float, list[dict[str, float]]]:
    rng = np.random.default_rng(seed + 99)
    w = rng.normal(0.0, 0.05, size=(p_train.shape[1],)).astype(np.float32)
    b = 0.0
    history: list[dict[str, float]] = []

    sf = float(situational.get("alpha_focus", 1.0))
    sn = float(situational.get("beta_noise", 1.0))
    sm = float(situational.get("gamma_memory", 1.0))
    se = float(situational.get("delta_execution", 1.0))
    scale = np.array([se, sf, sm], dtype=np.float32)[: p_train.shape[1]]
    scale = scale * (1.0 / max(1e-6, sn))

    xtr = p_train * scale
    xva = p_val * scale
    ytr = y_train.astype(np.float32)
    yva = y_val.astype(np.float32)

    for e in range(1, epochs + 1):
        lrate = lr * (0.95 ** (e - 1))
        z = xtr @ w + b
        yhat = 1.0 / (1.0 + np.exp(-z))
        eps = 1e-9
        loss_t = float(-np.mean(ytr * np.log(yhat + eps) + (1 - ytr) * np.log(1 - yhat + eps)))
        pred_t = (yhat >= 0.5).astype(np.int64)
        acc_t = float(np.mean((pred_t == y_train).astype(np.float32)))

        grad = yhat - ytr
        grad_w = (xtr.T @ grad) / xtr.shape[0]
        grad_b = float(np.mean(grad))
        w -= lrate * grad_w
        b -= lrate * grad_b

        zv = xva @ w + b
        yv = 1.0 / (1.0 + np.exp(-zv))
        loss_v = float(-np.mean(yva * np.log(yv + eps) + (1 - yva) * np.log(1 - yv + eps)))
        pred_v = (yv >= 0.5).astype(np.int64)
        acc_v = float(np.mean((pred_v == y_val).astype(np.float32)))
        history.append(
            {
                "epoch": float(e),
                "learning_rate": float(lrate),
                "train_loss": loss_t,
                "train_accuracy": acc_t,
                "val_loss": loss_v,
                "val_accuracy": acc_v,
            }
        )
    return w, float(b), history


def upload_artifacts(repo_id: str, run_dir: Path, run_id: str) -> dict[str, Any]:
    if HfApi is None or get_token is None:
        return {"status": "skipped", "reason": "huggingface_hub unavailable"}
    token = (get_token() or "").strip()
    if not token:
        return {"status": "skipped", "reason": "hf token unavailable"}

    api = HfApi(token=token)
    prefix = f"node_fleet_runs/{run_id}"
    try:
        api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "reason": f"create_repo: {exc}"}

    uploaded: list[str] = []
    for name in ("fleet_training_metrics.json", "fleet_model.npz", "fleet_growth_summary.md"):
        p = run_dir / name
        if not p.exists():
            continue
        api.upload_file(
            path_or_fileobj=str(p),
            path_in_repo=f"{prefix}/{name}",
            repo_id=repo_id,
            repo_type="model",
            commit_message=f"node-fleet training artifacts {run_id} - {name}",
        )
        uploaded.append(f"{prefix}/{name}")
    return {"status": "ok", "uploaded_files": uploaded}


def main() -> int:
    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)

    constants = json.loads(Path(args.constants).read_text(encoding="utf-8"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(args.run_dir) if args.run_dir else Path("training/runs/node_fleet") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    patterns = args.local_glob or list(DEFAULT_PATTERNS)
    records = load_jsonl_records(patterns, max_samples=args.max_samples)
    records.extend(load_conversation_spin_records(args.conversation_spin_gist, cap=3000))
    if len(records) < 2:
        raise RuntimeError(f"Not enough base records found ({len(records)}). Need at least 2.")
    records = augment_records(records, min_samples=max(2, args.min_samples), seed=args.seed)
    random.shuffle(records)

    x = vectorize(records, args.embedding_dim)
    split = max(1, int((1.0 - args.val_ratio) * len(records)))
    split = min(split, len(records) - 1)
    x_train, x_val = x[:split], x[split:]
    rec_train, rec_val = records[:split], records[split:]
    now_ts = datetime.now(timezone.utc).timestamp()

    spec_names = ["code_execute", "doc_plan", "memory_storage"]
    specialist_models: dict[str, dict[str, Any]] = {}
    train_probs: list[np.ndarray] = []
    val_probs: list[np.ndarray] = []
    growth_flags: list[bool] = []

    for name in spec_names:
        spec = constants["specialists"][name]
        threshold = float(spec.get("threshold", 0.15))

        ytr = []
        yva = []
        for r in rec_train:
            parts = spin_components(r.text, r.raw, spec, constants, now_ts=now_ts, ts=parse_ts(r))
            score = spin_score(parts, constants)
            ytr.append(1 if score >= threshold else 0)
        for r in rec_val:
            parts = spin_components(r.text, r.raw, spec, constants, now_ts=now_ts, ts=parse_ts(r))
            score = spin_score(parts, constants)
            yva.append(1 if score >= threshold else 0)
        ytr_a = np.array(ytr, dtype=np.int64)
        yva_a = np.array(yva, dtype=np.int64)

        # Ensure both classes exist to avoid degenerate training.
        if np.unique(ytr_a).size < 2:
            flip_idx = np.arange(0, ytr_a.shape[0], max(1, ytr_a.shape[0] // 5))
            ytr_a[flip_idx] = 1 - ytr_a[flip_idx]
        if np.unique(yva_a).size < 2:
            yva_a[: max(1, yva_a.shape[0] // 3)] = 1

        w, b, hist = train_binary_classifier(
            x_train=x_train,
            y_train=ytr_a,
            x_val=x_val,
            y_val=yva_a,
            epochs=args.epochs,
            lr=args.learning_rate,
            seed=args.seed + (len(specialist_models) * 17),
        )
        p_tr = softmax(x_train @ w.T + b)[:, 1]
        p_va = softmax(x_val @ w.T + b)[:, 1]
        train_probs.append(p_tr)
        val_probs.append(p_va)

        first = hist[0]
        last = hist[-1]
        gain = float(last["val_accuracy"] - first["val_accuracy"])
        drop = float(first["val_loss"] - last["val_loss"])
        growth_ok = bool((gain > 0.01) or (drop > 0.02))
        growth_flags.append(growth_ok)
        specialist_models[name] = {
            "weights_shape": [int(x) for x in w.shape],
            "history": hist,
            "growth": {
                "confirmed": growth_ok,
                "val_accuracy_gain": round(gain, 6),
                "val_loss_drop": round(drop, 6),
                "first_val_accuracy": round(first["val_accuracy"], 6),
                "last_val_accuracy": round(last["val_accuracy"], 6),
            },
            "class_balance": {
                "train_positive_ratio": round(float(np.mean(ytr_a)), 6),
                "val_positive_ratio": round(float(np.mean(yva_a)), 6),
            },
        }
        np.savez(run_dir / f"specialist_{name}.npz", w=w, b=b)

    p_train_mat = np.stack(train_probs, axis=1)
    p_val_mat = np.stack(val_probs, axis=1)
    y_train_fleet = ((p_train_mat.mean(axis=1) >= 0.45).astype(np.int64))
    y_val_fleet = ((p_val_mat.mean(axis=1) >= 0.45).astype(np.int64))
    if np.unique(y_train_fleet).size < 2:
        y_train_fleet[::3] = 1 - y_train_fleet[::3]
    if np.unique(y_val_fleet).size < 2:
        y_val_fleet[::3] = 1 - y_val_fleet[::3]

    fw, fb, fleet_hist = train_fleet_coordinator(
        p_train=p_train_mat,
        y_train=y_train_fleet,
        p_val=p_val_mat,
        y_val=y_val_fleet,
        epochs=max(6, args.epochs),
        lr=max(0.03, args.learning_rate * 0.4),
        seed=args.seed,
        situational=constants["situational_constants"],
    )
    f_first = fleet_hist[0]
    f_last = fleet_hist[-1]
    fleet_growth = {
        "confirmed": bool((f_last["val_accuracy"] - f_first["val_accuracy"] > 0.01) or (f_first["val_loss"] - f_last["val_loss"] > 0.02)),
        "val_accuracy_gain": round(float(f_last["val_accuracy"] - f_first["val_accuracy"]), 6),
        "val_loss_drop": round(float(f_first["val_loss"] - f_last["val_loss"]), 6),
        "first_val_accuracy": round(float(f_first["val_accuracy"]), 6),
        "last_val_accuracy": round(float(f_last["val_accuracy"]), 6),
    }

    report = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "training_goal": "3-specialty node-fleet co-training",
        "specialties": spec_names,
        "constants_file": args.constants,
        "spin_formula": constants.get("spin_formula"),
        "data": {
            "sample_count": len(records),
            "train_count": int(x_train.shape[0]),
            "val_count": int(x_val.shape[0]),
            "embedding_dim": args.embedding_dim,
            "sources_used": sorted({r.source for r in records})[:200],
            "conversation_spin_gist": args.conversation_spin_gist,
        },
        "specialist_models": specialist_models,
        "fleet_coordinator": {
            "weights": [float(x) for x in fw.tolist()],
            "bias": float(fb),
            "history": fleet_hist,
            "growth": fleet_growth,
        },
        "growth": {
            "specialists_confirmed": bool(all(growth_flags)),
            "fleet_confirmed": bool(fleet_growth["confirmed"]),
            "overall_confirmed": bool(all(growth_flags) and fleet_growth["confirmed"]),
        },
    }

    np.savez(run_dir / "fleet_model.npz", weights=fw, bias=np.array([fb], dtype=np.float32))
    (run_dir / "fleet_training_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (run_dir / "fleet_growth_summary.md").write_text(
        "\n".join(
            [
                "# Node-Fleet 3-Specialty Training Summary",
                "",
                f"- run_id: `{run_id}`",
                f"- sample_count: `{report['data']['sample_count']}`",
                f"- train/val: `{report['data']['train_count']}/{report['data']['val_count']}`",
                f"- specialties: `{', '.join(spec_names)}`",
                f"- specialists_confirmed: `{report['growth']['specialists_confirmed']}`",
                f"- fleet_confirmed: `{report['growth']['fleet_confirmed']}`",
                f"- overall_confirmed: `{report['growth']['overall_confirmed']}`",
                "",
                "## Fleet Growth",
                f"- first_val_accuracy: `{fleet_growth['first_val_accuracy']}`",
                f"- last_val_accuracy: `{fleet_growth['last_val_accuracy']}`",
                f"- val_accuracy_gain: `{fleet_growth['val_accuracy_gain']}`",
                f"- val_loss_drop: `{fleet_growth['val_loss_drop']}`",
            ]
        ),
        encoding="utf-8",
    )

    upload = {"status": "skipped", "reason": "push disabled"}
    if args.push_to_hub:
        upload = upload_artifacts(args.model_repo, run_dir, run_id)
    report["huggingface_upload"] = upload
    (run_dir / "fleet_training_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Node-fleet training completed.")
    print("Run dir:", run_dir)
    print("Specialists confirmed:", report["growth"]["specialists_confirmed"])
    print("Fleet confirmed:", report["growth"]["fleet_confirmed"])
    print("Overall growth confirmed:", report["growth"]["overall_confirmed"])
    print("HF upload:", upload.get("status"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
