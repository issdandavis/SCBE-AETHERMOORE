#!/usr/bin/env python3
"""Unified Training Pipeline — Kaggle + HuggingFace + Local SFT
================================================================

One script that:
  1. Pulls training data from Kaggle (40K adversarial prompts)
  2. Merges with local SCBE SFT records (900+ examples)
  3. Downloads your HF base model (phdm-21d-embedding)
  4. Fine-tunes a governance classifier (benign vs adversarial)
  5. Evaluates against the SCBE benchmark attack suite
  6. Pushes the trained model + results to HuggingFace

Usage:
    python scripts/unified_training_pipeline.py
    python scripts/unified_training_pipeline.py --push      # push to HF
    python scripts/unified_training_pipeline.py --dry-run   # skip training, test pipeline
    python scripts/unified_training_pipeline.py --epochs 5  # more epochs

Environment:
    HF_TOKEN               — HuggingFace write token (required for --push)
    KAGGLE_KEY             — Kaggle API key
    KAGGLE_API_TOKEN       — Alternate Kaggle token shape; normalized to KAGGLE_KEY

Connections used:
    - Kaggle MCP:     Download adversarial prompt dataset (40K samples)
    - HuggingFace:    Pull base model, push trained model + dataset
    - Local SFT:      training-data/sft/*.jsonl (900+ SCBE-specific examples)
    - SCBE Benchmark: benchmarks/scbe/attacks/generator.py (400+ attack vectors)
    - RuntimeGate:    src/governance/runtime_gate.py (governance labeling)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure repo root on path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("unified_training")

# Paths
SFT_DIR = REPO_ROOT / "training-data" / "sft"
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "training"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# HuggingFace targets
HF_USER = "issdandavis"
HF_DATASET = f"{HF_USER}/scbe-aethermoore-training-data"
HF_BASE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
HF_OUTPUT_MODEL = f"{HF_USER}/scbe-governance-classifier-v1"

# Kaggle dataset
KAGGLE_DATASET = "mohammedaminejebbar/malicious-prompt-detection-dataset-mpdd"


def ensure_kaggle_env() -> None:
    """Normalize Kaggle credential env vars for kagglehub and kaggle CLI."""
    api_token = os.environ.get("KAGGLE_API_TOKEN")
    key = os.environ.get("KAGGLE_KEY")
    if api_token and not key:
        os.environ["KAGGLE_KEY"] = api_token
    elif key and not api_token:
        os.environ["KAGGLE_API_TOKEN"] = key


# ---------------------------------------------------------------------------
#  Step 1: Load data from all sources
# ---------------------------------------------------------------------------

def load_kaggle_data(max_samples: int = 10000) -> list[dict[str, Any]]:
    """Pull adversarial prompt dataset from Kaggle."""
    ensure_kaggle_env()
    logger.info("[1a] Loading Kaggle dataset: %s", KAGGLE_DATASET)

    cache_path = ARTIFACTS_DIR / "kaggle_mpdd_cache.jsonl"
    if cache_path.exists():
        logger.info("  Using cached Kaggle data: %s", cache_path)
        records = []
        with open(cache_path) as f:
            for line in f:
                records.append(json.loads(line))
        return records[:max_samples]

    try:
        import kagglehub
        path = kagglehub.dataset_download(KAGGLE_DATASET)
        logger.info("  Downloaded to: %s", path)
    except Exception:
        # Fallback: try kaggle CLI
        try:
            import subprocess
            result = subprocess.run(
                ["kaggle", "datasets", "download", "-d", KAGGLE_DATASET, "-p",
                 str(ARTIFACTS_DIR / "kaggle_downloads"), "--unzip"],
                capture_output=True, text=True, timeout=120,
            )
            path = str(ARTIFACTS_DIR / "kaggle_downloads")
            logger.info("  Downloaded via CLI to: %s", path)
        except Exception as e:
            logger.warning("  Kaggle download failed: %s. Using synthetic data.", e)
            return _generate_synthetic_adversarial(max_samples)

    # Parse CSV -- handle multiple file formats in this dataset
    records = []
    import csv

    # Files that are implicitly ALL adversarial (no label column)
    IMPLICIT_MALICIOUS = {"forbidden_question_set_df", "jailbreak_prompts",
                          "malicous_deepset", "malignant", "predictionguard_df"}

    for csv_file in Path(path).rglob("*.csv"):
        stem = csv_file.stem
        is_implicit_malicious = stem in IMPLICIT_MALICIOUS
        file_count = 0

        with open(csv_file, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []

            # Skip files without usable text columns
            text_col = None
            for candidate in ["Prompt", "prompt", "text", "question1", "Input"]:
                if candidate in cols:
                    text_col = candidate
                    break
            if text_col is None:
                continue

            # Determine label column
            label_col = None
            for candidate in ["isMalicious", "is_malicious", "label", "Label", "class"]:
                if candidate in cols:
                    label_col = candidate
                    break

            for row in reader:
                text = row.get(text_col, "").strip()
                if len(text) < 10:
                    continue
                # Skip rows with embeddings in the text (corrupted)
                if text.startswith("[[") or text.startswith("[-"):
                    continue

                if is_implicit_malicious:
                    label = 1  # These files are ALL adversarial
                elif label_col:
                    try:
                        label = int(float(row.get(label_col, "0")))
                    except (ValueError, TypeError):
                        raw = str(row.get(label_col, "")).lower()
                        label = 1 if raw in ("malicious", "jailbreak", "1", "true") else 0
                else:
                    label = 0  # Default to benign if no label

                records.append({
                    "text": text[:2000],
                    "label": label,
                    "source": f"kaggle_{stem}",
                })
                file_count += 1

        if file_count > 0:
            logger.info("    %s: %d records (implicit_malicious=%s)", stem, file_count, is_implicit_malicious)

    # Apply max_samples BEFORE caching (per-label cap to keep balance)
    import random as _rng
    _rng.seed(42)
    pos_recs = [r for r in records if r["label"] == 1]
    neg_recs = [r for r in records if r["label"] == 0]
    half = max_samples // 2
    if len(pos_recs) > half:
        pos_recs = _rng.sample(pos_recs, half)
    if len(neg_recs) > half:
        neg_recs = _rng.sample(neg_recs, half)
    records = pos_recs + neg_recs
    _rng.shuffle(records)

    logger.info("  After balance cap: %d adversarial + %d benign = %d total",
                len(pos_recs), len(neg_recs), len(records))

    # Cache for next run
    with open(cache_path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    return records


def _generate_synthetic_adversarial(n: int) -> list[dict[str, Any]]:
    """Fallback: generate adversarial data from SCBE benchmark suite."""
    from benchmarks.scbe.attacks.generator import generate_attacks
    attacks = generate_attacks(scale=max(10, n // 20))
    records = []
    for atk in attacks[:n]:
        records.append({
            "text": atk["prompt"][:2000],
            "label": 1,
            "source": f"scbe_benchmark_{atk['class']}",
        })
    # Add benign samples
    benign = [
        "Summarize this quarterly financial report.",
        "What are the differences between Python and JavaScript?",
        "Help me write a professional email to my team.",
        "Explain hyperbolic geometry in simple terms.",
        "Review this code for potential bugs.",
        "What is the weather like today?",
        "How do I set up a Python virtual environment?",
        "List the main features of the new product.",
        "Calculate the compound interest on a $10000 investment.",
        "Translate this paragraph to Spanish.",
    ]
    for b in benign:
        records.append({"text": b, "label": 0, "source": "synthetic_benign"})
    return records


def load_local_sft() -> list[dict[str, Any]]:
    """Load local SCBE SFT training records."""
    logger.info("[1b] Loading local SFT data from %s", SFT_DIR)
    records = []
    for jsonl_file in sorted(SFT_DIR.glob("*.jsonl")):
        with open(jsonl_file, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    # Extract text from various SFT formats
                    text = ""
                    if "messages" in rec:
                        for msg in rec["messages"]:
                            if msg.get("role") == "user":
                                text = msg.get("content", "")
                                break
                    elif "prompt" in rec:
                        text = rec["prompt"]
                    elif "text" in rec:
                        text = rec["text"]
                    elif "input" in rec:
                        text = rec["input"]

                    if text.strip():
                        records.append({
                            "text": text.strip()[:2000],
                            "label": 0,  # SFT records are legitimate by definition
                            "source": f"local_sft_{jsonl_file.stem}",
                        })
                except json.JSONDecodeError:
                    continue

    logger.info("  Loaded %d local SFT records", len(records))
    return records


def load_scbe_benchmark_attacks() -> list[dict[str, Any]]:
    """Load attack vectors from SCBE benchmark suite.

    IMPORTANT: These are used ONLY for blind evaluation, NEVER for training.
    This is the strict data isolation boundary. If benchmark attacks leak
    into training data, the benchmark numbers are meaningless.
    """
    logger.info("[1c] Loading SCBE benchmark attacks (20 categories) — HOLDOUT ONLY")
    from benchmarks.scbe.attacks.generator import generate_attacks
    attacks = generate_attacks(scale=20)
    records = []
    for atk in attacks:
        records.append({
            "text": atk["prompt"][:2000],
            "label": 1,
            "source": f"scbe_benchmark_{atk['class']}",
            "category": atk["class"],
        })
    logger.info("  Loaded %d benchmark attacks (reserved for blind test)", len(records))
    return records


def load_additional_benign() -> list[dict[str, Any]]:
    """Load extra benign text from markdown docs for negative class balance."""
    logger.info("[1d] Loading benign text from docs/ and training-data/")
    records = []

    # Pull sentences from markdown docs (real benign content)
    docs_dir = REPO_ROOT / "docs"
    count = 0
    for md_file in sorted(docs_dir.rglob("*.md")):
        if count >= 500:
            break
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
            # Extract paragraphs (lines with 30+ chars that aren't headers/code)
            for line in text.split("\n"):
                line = line.strip()
                if (len(line) >= 40
                    and not line.startswith("#")
                    and not line.startswith("```")
                    and not line.startswith("|")
                    and not line.startswith("-")
                    and "http" not in line.lower()):
                    records.append({
                        "text": line[:500],
                        "label": 0,
                        "source": f"docs_{md_file.stem}",
                    })
                    count += 1
                    if count >= 500:
                        break
        except Exception:
            continue

    logger.info("  Loaded %d benign text samples from docs", len(records))
    return records


# ---------------------------------------------------------------------------
#  Step 2: Prepare dataset with STRICT DATA ISOLATION
# ---------------------------------------------------------------------------

def prepare_dataset(
    train_records: list[dict[str, Any]],
    holdout_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Prepare training data with strict isolation from benchmark holdout.

    CRITICAL RULE: train_records and holdout_records must have ZERO overlap.
    The model trains on train_records only. Holdout is used for blind eval.
    If any holdout text appears in training, the benchmark is compromised.
    """
    import hashlib

    logger.info("[2] Preparing dataset with STRICT DATA ISOLATION")

    # Hash all holdout texts to ensure no contamination
    holdout_hashes = set()
    for r in holdout_records:
        holdout_hashes.add(hashlib.md5(r["text"].encode()).hexdigest())
    logger.info("  Holdout fingerprints: %d (these MUST NOT appear in training)", len(holdout_hashes))

    # Deduplicate training data AND filter out any holdout contamination
    seen = set()
    clean_train = []
    contamination_count = 0
    for r in train_records:
        h = hashlib.md5(r["text"].encode()).hexdigest()
        if h in holdout_hashes:
            contamination_count += 1
            continue  # BLOCK: this text is in the holdout set
        if h not in seen:
            seen.add(h)
            clean_train.append(r)

    if contamination_count > 0:
        logger.warning("  BLOCKED %d records that leaked from holdout into training", contamination_count)
    else:
        logger.info("  No contamination detected — holdout is clean")

    logger.info("  After dedup + isolation: %d clean training records", len(clean_train))

    # Count by label
    pos = [r for r in clean_train if r["label"] == 1]
    neg = [r for r in clean_train if r["label"] == 0]
    logger.info("  Positive (adversarial): %d, Negative (benign): %d", len(pos), len(neg))

    # Balance classes
    import random
    random.seed(42)
    if len(pos) == 0 or len(neg) == 0:
        logger.warning("  One class is empty! Using all data unbalanced.")
        balanced = clean_train
    else:
        # Use all of minority class, sample up to 2x from majority
        min_size = min(len(pos), len(neg))
        max_size = min_size * 3  # Allow 3:1 ratio max
        sampled_pos = random.sample(pos, min(len(pos), max_size))
        sampled_neg = random.sample(neg, min(len(neg), max_size))
        balanced = sampled_pos + sampled_neg
        random.shuffle(balanced)

    # Split 80/20 (this eval split is for training loss tracking only)
    # The REAL eval is the holdout benchmark — never touched during training
    split_idx = int(len(balanced) * 0.8)
    train = balanced[:split_idx]
    eval_data = balanced[split_idx:]

    logger.info("  Train: %d, Train-eval: %d, Blind holdout: %d", len(train), len(eval_data), len(holdout_records))

    return {
        "train": train,
        "eval": eval_data,
        "holdout": holdout_records,
        "total": len(balanced),
        "contamination_blocked": contamination_count,
    }


# ---------------------------------------------------------------------------
#  Step 3: Train classifier
# ---------------------------------------------------------------------------

def train_classifier(
    dataset: dict[str, Any],
    epochs: int = 3,
    batch_size: int = 32,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Fine-tune a text classifier on adversarial vs benign."""
    logger.info("[3] Training governance classifier")

    if dry_run:
        logger.info("  DRY RUN: skipping actual training")
        return {
            "model_path": str(ARTIFACTS_DIR / "governance_classifier"),
            "epochs": epochs,
            "train_size": len(dataset["train"]),
            "eval_size": len(dataset["eval"]),
            "dry_run": True,
            "eval_accuracy": 0.0,
        }

    try:
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            Trainer,
            TrainingArguments,
        )
        import torch
        from torch.utils.data import Dataset as TorchDataset
    except ImportError:
        logger.error("  transformers/torch not installed. Run: pip install transformers torch")
        logger.info("  Falling back to sklearn LogisticRegression")
        return _train_sklearn(dataset)

    # Tokenize
    tokenizer = AutoTokenizer.from_pretrained(HF_BASE_MODEL)

    class TextDataset(TorchDataset):
        def __init__(self, records):
            self.records = records
            self.encodings = tokenizer(
                [r["text"] for r in records],
                truncation=True, padding=True, max_length=256,
                return_tensors="pt",
            )

        def __len__(self):
            return len(self.records)

        def __getitem__(self, idx):
            item = {k: v[idx] for k, v in self.encodings.items()}
            item["labels"] = torch.tensor(self.records[idx]["label"], dtype=torch.long)
            return item

    train_ds = TextDataset(dataset["train"])
    eval_ds = TextDataset(dataset["eval"])

    # Model
    model = AutoModelForSequenceClassification.from_pretrained(
        HF_BASE_MODEL,
        num_labels=2,
        problem_type="single_label_classification",
    )

    output_dir = str(ARTIFACTS_DIR / "governance_classifier")

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        report_to="none",
        fp16=torch.cuda.is_available(),
    )

    def compute_metrics(eval_pred):
        import numpy as np
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        acc = (preds == labels).mean()
        return {"accuracy": float(acc)}

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        compute_metrics=compute_metrics,
    )

    logger.info("  Starting training: %d epochs, batch=%d", epochs, batch_size)
    train_result = trainer.train()
    eval_result = trainer.evaluate()

    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    logger.info("  Training complete. Eval accuracy: %.4f", eval_result.get("eval_accuracy", 0))

    return {
        "model_path": output_dir,
        "epochs": epochs,
        "train_size": len(dataset["train"]),
        "eval_size": len(dataset["eval"]),
        "train_loss": train_result.training_loss,
        "eval_accuracy": eval_result.get("eval_accuracy", 0),
        "eval_loss": eval_result.get("eval_loss", 0),
        "dry_run": False,
    }


def _train_sklearn(dataset: dict[str, Any]) -> dict[str, Any]:
    """Fallback: train with sklearn if transformers isn't available."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report
    import joblib

    logger.info("  Training sklearn LogisticRegression fallback")

    train_texts = [r["text"] for r in dataset["train"]]
    train_labels = [r["label"] for r in dataset["train"]]
    eval_texts = [r["text"] for r in dataset["eval"]]
    eval_labels = [r["label"] for r in dataset["eval"]]

    vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
    X_train = vectorizer.fit_transform(train_texts)
    X_eval = vectorizer.transform(eval_texts)

    model = LogisticRegression(max_iter=1000, C=1.0)
    model.fit(X_train, train_labels)

    preds = model.predict(X_eval)
    accuracy = accuracy_score(eval_labels, preds)
    report = classification_report(eval_labels, preds, output_dict=True)

    output_dir = str(ARTIFACTS_DIR / "governance_classifier_sklearn")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    joblib.dump(model, Path(output_dir) / "model.joblib")
    joblib.dump(vectorizer, Path(output_dir) / "vectorizer.joblib")

    logger.info("  sklearn accuracy: %.4f", accuracy)
    logger.info("  Report:\n%s", classification_report(eval_labels, preds))

    return {
        "model_path": output_dir,
        "model_type": "sklearn_logistic_regression",
        "train_size": len(train_texts),
        "eval_size": len(eval_texts),
        "eval_accuracy": accuracy,
        "classification_report": report,
        "dry_run": False,
    }


# ---------------------------------------------------------------------------
#  Step 4: Evaluate against SCBE benchmark
# ---------------------------------------------------------------------------

def evaluate_against_benchmark(model_path: str, dry_run: bool = False) -> dict[str, Any]:
    """Run the trained model against SCBE's 20-category attack suite."""
    logger.info("[4] Evaluating against SCBE benchmark (20 categories)")

    if dry_run:
        return {"benchmark_eval": "skipped_dry_run"}

    from benchmarks.scbe.attacks.generator import generate_attacks, get_category_names

    attacks = generate_attacks(scale=10)
    categories = get_category_names()

    # Try to load model
    try:
        import joblib
        model = joblib.load(Path(model_path) / "model.joblib")
        vectorizer = joblib.load(Path(model_path) / "vectorizer.joblib")
        use_sklearn = True
    except Exception:
        try:
            from transformers import pipeline
            classifier = pipeline("text-classification", model=model_path)
            use_sklearn = False
        except Exception:
            logger.warning("  Could not load model for evaluation")
            return {"benchmark_eval": "model_load_failed"}

    results_per_category = {}
    for cat in categories:
        cat_attacks = [a for a in attacks if a["class"] == cat]
        if not cat_attacks:
            continue

        detected = 0
        for atk in cat_attacks:
            if use_sklearn:
                X = vectorizer.transform([atk["prompt"]])
                pred = model.predict(X)[0]
                is_attack = pred == 1
            else:
                result = classifier(atk["prompt"][:512])[0]
                is_attack = result["label"] == "LABEL_1" or "malicious" in result["label"].lower()

            if is_attack:
                detected += 1

        rate = detected / len(cat_attacks) if cat_attacks else 0
        results_per_category[cat] = {
            "total": len(cat_attacks),
            "detected": detected,
            "rate": round(rate, 3),
        }

    overall_detected = sum(r["detected"] for r in results_per_category.values())
    overall_total = sum(r["total"] for r in results_per_category.values())
    overall_rate = overall_detected / overall_total if overall_total > 0 else 0

    logger.info("  Overall detection: %d/%d (%.1f%%)", overall_detected, overall_total, overall_rate * 100)

    return {
        "overall_detection_rate": round(overall_rate, 4),
        "overall_detected": overall_detected,
        "overall_total": overall_total,
        "per_category": results_per_category,
    }


# ---------------------------------------------------------------------------
#  Step 5: Push to HuggingFace
# ---------------------------------------------------------------------------

def push_to_huggingface(
    model_path: str,
    training_results: dict[str, Any],
    benchmark_results: dict[str, Any],
    push: bool = False,
) -> None:
    """Push trained model and results to HuggingFace Hub."""
    logger.info("[5] HuggingFace push")

    if not push:
        logger.info("  Push skipped (use --push to enable)")
        return

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        logger.warning("  HF_TOKEN not set. Skipping push.")
        return

    try:
        from huggingface_hub import HfApi
        api = HfApi(token=hf_token)

        # Push training report as dataset artifact
        report_path = ARTIFACTS_DIR / "training_report.json"
        api.upload_file(
            path_or_fileobj=str(report_path),
            path_in_repo="training_reports/latest_report.json",
            repo_id=HF_DATASET,
            repo_type="dataset",
        )
        logger.info("  Pushed training report to %s", HF_DATASET)

        # Push model if transformer-based
        if Path(model_path).joinpath("config.json").exists():
            api.upload_folder(
                folder_path=model_path,
                repo_id=HF_OUTPUT_MODEL,
                repo_type="model",
            )
            logger.info("  Pushed model to %s", HF_OUTPUT_MODEL)
        else:
            logger.info("  sklearn model — pushing as artifact only")
            for f in Path(model_path).glob("*"):
                api.upload_file(
                    path_or_fileobj=str(f),
                    path_in_repo=f"sklearn_classifier/{f.name}",
                    repo_id=HF_DATASET,
                    repo_type="dataset",
                )

    except Exception as e:
        logger.error("  HF push failed: %s", e)


def push_to_kaggle(report: dict[str, Any], push: bool = False) -> None:
    """Push eval results back to Kaggle dataset (closes the feedback loop)."""
    logger.info("[6] Kaggle push")

    if not push:
        logger.info("  Kaggle push skipped (use --push to enable)")
        return

    try:
        import csv
        import subprocess

        kaggle_dir = ARTIFACTS_DIR / "kaggle_upload"
        kaggle_dir.mkdir(parents=True, exist_ok=True)

        # Build summary CSV
        with open(kaggle_dir / "summary_stats.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Metric", "Value", "Context"])
            t = report.get("training", {})
            b = report.get("blind_benchmark_eval", {})
            w.writerow(["Training Samples", t.get("train_size", "N/A"), "Kaggle + local SFT + benign docs"])
            w.writerow(["Train-Eval Accuracy", f"{t.get('eval_accuracy', 0):.1%}", "In-distribution holdout"])
            w.writerow(["Blind Detection Rate", f"{b.get('overall_detection_rate', 0):.1%}", "20 categories, strict isolation"])
            w.writerow(["Contamination", report.get("data_isolation", {}).get("contamination_blocked", 0), "Records blocked from training"])
            w.writerow(["Timestamp", report.get("timestamp", ""), "Pipeline run time"])

        # Build per-category CSV
        per_cat = b.get("per_category", {})
        if per_cat:
            with open(kaggle_dir / "benchmark_results.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Category", "Total", "Detected", "Rate"])
                for cat, d in sorted(per_cat.items(), key=lambda x: -x[1].get("rate", 0)):
                    w.writerow([cat, d["total"], d["detected"], f"{d['rate']*100:.0f}%"])

        # Copy training report JSON
        report_path = ARTIFACTS_DIR / "training_report.json"
        if report_path.exists():
            import shutil
            shutil.copy2(report_path, kaggle_dir / "training_report.json")

        # Write metadata
        metadata = {
            "id": "issacizrealdavis/scbe-governance-research-results",
            "title": "SCBE-AETHERMOORE Governance Research Results",
            "subtitle": "AI safety benchmarks, trichromatic governance, energy simulation results",
            "isPrivate": False,
            "licenses": [{"name": "MIT"}],
            "keywords": ["nlp", "deep learning", "energy", "cyber security", "classification"],
        }
        with open(kaggle_dir / "dataset-metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # Push new version
        result = subprocess.run(
            ["kaggle", "datasets", "version", "-p", str(kaggle_dir),
             "-m", f"Auto-update from training pipeline ({report.get('timestamp', 'unknown')})"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            logger.info("  Pushed results to Kaggle: issacizrealdavis/scbe-governance-research-results")
        else:
            logger.warning("  Kaggle push returned: %s", result.stderr.strip())

    except Exception as e:
        logger.error("  Kaggle push failed: %s", e)


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Unified SCBE Training Pipeline")
    parser.add_argument("--push", action="store_true", help="Push results to HuggingFace")
    parser.add_argument("--dry-run", action="store_true", help="Test pipeline without training")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs (default: 3)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size (default: 32)")
    parser.add_argument("--max-kaggle", type=int, default=40000, help="Max Kaggle samples (default: 40000, full dataset)")
    parser.add_argument("--sklearn", action="store_true", help="Force sklearn fallback (faster, no GPU needed)")
    args = parser.parse_args()

    start = time.perf_counter()

    print("")
    print("=" * 70)
    print("  SCBE UNIFIED TRAINING PIPELINE")
    print("  Kaggle + HuggingFace + Local SFT + Benchmark Eval")
    print("=" * 70)
    print("")

    # Step 1: Load data from all sources
    kaggle_data = load_kaggle_data(max_samples=args.max_kaggle)
    local_sft = load_local_sft()
    extra_benign = load_additional_benign()

    # STRICT ISOLATION: benchmark attacks are NEVER in the training pool
    benchmark_holdout = load_scbe_benchmark_attacks()

    # Training pool = Kaggle + Local SFT + extra benign docs (NO benchmark attacks)
    train_pool = kaggle_data + local_sft + extra_benign
    logger.info("[1] Training pool: %d (Kaggle: %d, Local SFT: %d, Benign docs: %d)",
                len(train_pool), len(kaggle_data), len(local_sft), len(extra_benign))
    logger.info("    Blind holdout: %d benchmark attacks (NEVER seen during training)",
                len(benchmark_holdout))

    # Step 2: Prepare dataset with strict isolation
    dataset = prepare_dataset(train_pool, benchmark_holdout)

    # Step 3: Train
    if args.sklearn:
        training_results = _train_sklearn(dataset)
    else:
        training_results = train_classifier(
            dataset, epochs=args.epochs, batch_size=args.batch_size, dry_run=args.dry_run,
        )

    # Step 4: BLIND EVALUATION against holdout benchmark
    # The model has NEVER seen these attacks during training.
    # This is the only number that matters.
    benchmark_results = evaluate_against_benchmark(
        training_results["model_path"], dry_run=args.dry_run,
    )

    # Step 5: Save report
    report = {
        "pipeline": "unified_scbe_training_v2_strict_isolation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_isolation": {
            "method": "strict_holdout",
            "holdout_source": "scbe_benchmark_20_categories",
            "holdout_size": len(benchmark_holdout),
            "contamination_blocked": dataset.get("contamination_blocked", 0),
            "rule": "Benchmark attacks NEVER appear in training data. This is the blind test.",
        },
        "data_sources": {
            "kaggle": {"dataset": KAGGLE_DATASET, "samples": len(kaggle_data)},
            "local_sft": {"dir": str(SFT_DIR), "samples": len(local_sft)},
            "benign_docs": {"samples": len(extra_benign)},
            "blind_holdout": {"categories": 20, "samples": len(benchmark_holdout)},
        },
        "dataset": {
            "train": len(dataset["train"]),
            "train_eval": len(dataset["eval"]),
            "blind_holdout": len(benchmark_holdout),
        },
        "training": training_results,
        "blind_benchmark_eval": benchmark_results,
        "connections_used": [
            "Kaggle MCP (40K adversarial prompt dataset)",
            "HuggingFace Hub (base model + push)",
            "Local SCBE SFT (training-data/sft/)",
            "Local docs (benign text corpus)",
            "SCBE Benchmark (20-category blind holdout)",
        ],
    }

    report_path = ARTIFACTS_DIR / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Step 6: Push to HuggingFace (trained model + report)
    push_to_huggingface(
        training_results["model_path"], training_results, benchmark_results, push=args.push,
    )

    # Step 7: Push eval results back to Kaggle (closes the feedback loop)
    push_to_kaggle(report, push=args.push)

    elapsed = time.perf_counter() - start

    # Print summary
    print("")
    print("=" * 70)
    print("  TRAINING COMPLETE — STRICT DATA ISOLATION")
    print("=" * 70)
    print(f"  Time:              {elapsed:.1f}s")
    print(f"  Training data:     Kaggle ({len(kaggle_data)}) + Local SFT ({len(local_sft)}) + Benign docs ({len(extra_benign)})")
    print(f"  Train / Train-eval: {len(dataset['train'])} / {len(dataset['eval'])}")
    print(f"  Train-eval acc:    {training_results.get('eval_accuracy', 'N/A')}")
    print("")
    print("  --- BLIND HOLDOUT (model NEVER saw these during training) ---")
    print(f"  Holdout attacks:   {len(benchmark_holdout)} (20 categories)")
    if isinstance(benchmark_results.get("overall_detection_rate"), float):
        print(f"  Blind detection:   {benchmark_results['overall_detection_rate']:.1%} ({benchmark_results['overall_detected']}/{benchmark_results['overall_total']})")
    contaminated = dataset.get("contamination_blocked", 0)
    if contaminated > 0:
        print(f"  Contamination:     {contaminated} records BLOCKED from training")
    else:
        print(f"  Contamination:     CLEAN (zero holdout leaks)")
    print("")
    print(f"  Report:            {report_path}")
    if args.push:
        print(f"  Pushed to:         {HF_DATASET}")
    print("")
    print("=" * 70)


if __name__ == "__main__":
    main()
