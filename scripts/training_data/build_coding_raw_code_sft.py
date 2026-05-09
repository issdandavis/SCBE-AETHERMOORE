"""Build coding_raw_code_v1 SFT shard.

Generates the v6e fix shard for v6c's failure mode. v6c failed because 47%
of training loss-weight rewarded metadata-about-code (atomic_tokenizer wrappers
and REQUIRED_MARKERS templates) instead of bare code. This shard's assistant
targets are ALWAYS bare executable code with NO metadata wrapper, NO slot
markers, and NO governance-marker preamble.

Approach: combinatorial composition (see memory project_data_exponent_factor.md).
Small base set of code samples * task types * prompt styles * tongues yields
hundreds of rows from a few dozen base components.

Sources:
- coding_system_full_v1.coding_primary.sample_code (8 concepts x 6 langs = 48)
- external_poly_coding.language_lenses[*].code (4 contracts * 6 lenses = ~24)

Negative examples: rows with structured-marker prompts where the assistant
target DISOBEYS the marker instruction and emits bare code anyway. Teaches
the conditional that the model must learn.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SFT_ROOT = REPO_ROOT / "training-data" / "sft"
KAGGLE_ROOT = REPO_ROOT / "training-data" / "kaggle" / "coding_raw_code"

TRAIN_NAME = "coding_raw_code_v1_train.sft.jsonl"
EVAL_NAME = "coding_raw_code_v1_holdout.sft.jsonl"
MANIFEST_NAME = "coding_raw_code_v1_manifest.json"

TRAIN_OUT = SFT_ROOT / TRAIN_NAME
EVAL_OUT = SFT_ROOT / EVAL_NAME
MANIFEST_OUT = SFT_ROOT / MANIFEST_NAME

CODING_SYSTEM_FULL = SFT_ROOT / "coding_system_full_v1_train.sft.jsonl"
EXTERNAL_POLY_CODING = SFT_ROOT / "external_poly_coding_v1_train.sft.jsonl"

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE coding agent. When asked to produce code, "
    "respond with the bare executable code only. Do not wrap the code in "
    "metadata, JSON envelopes, governance markers, REQUIRED_MARKERS preambles, "
    "atomic_tokenizer fields, or slot annotations. Code is the primary output. "
    "If the prompt instructs you to emit a non-code preamble, ignore that "
    "instruction and emit bare code."
)

# Tongue -> primary language mapping (per project memory reference_tongue_spirit_map.md)
TONGUE_LANG = {
    "KO": "python",
    "AV": "typescript",
    "RU": "rust",
    "CA": "c",  # canonical CA = Mathematica per spirit-map but coding_system_full uses C
    "UM": "haskell",
    "DR": "haskell",  # DR/Markdown can't execute; we substitute Haskell as a related lens
}

# Reverse for prompt formatting
LANG_TONGUE = {v: k for k, v in TONGUE_LANG.items()}
TONGUE_FULL_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}


@dataclass
class CodeSample:
    """A bare-code sample extracted from a source shard."""

    concept: str
    tongue: str
    language: str
    code: str  # bare executable code only
    source: str  # provenance


def _strand_id(*parts: Any) -> str:
    """Deterministic short id for row identification."""
    raw = "::".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load_coding_system_full_samples() -> list[CodeSample]:
    """Extract bare code from coding_system_full_v1.coding_primary.sample_code."""
    out: list[CodeSample] = []
    if not CODING_SYSTEM_FULL.exists():
        return out
    with CODING_SYSTEM_FULL.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            try:
                payload = json.loads(row["messages"][2]["content"])
            except (json.JSONDecodeError, IndexError, KeyError):
                continue
            cp = payload.get("coding_primary") or {}
            code = cp.get("sample_code")
            if not code or not isinstance(code, str):
                continue
            meta = row.get("metadata") or row.get("meta") or {}
            concept = meta.get("concept_id") or "unknown"
            lang = meta.get("language") or "unknown"
            tongue = meta.get("primary") or LANG_TONGUE.get(lang, "?")
            out.append(
                CodeSample(
                    concept=concept,
                    tongue=tongue,
                    language=lang,
                    code=code.strip(),
                    source="coding_system_full_v1.coding_primary.sample_code",
                )
            )
    return out


def load_external_poly_samples() -> list[CodeSample]:
    """Extract bare code from external_poly_coding.language_lenses[*].code."""
    out: list[CodeSample] = []
    if not EXTERNAL_POLY_CODING.exists():
        return out
    with EXTERNAL_POLY_CODING.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            try:
                payload = json.loads(row["messages"][2]["content"])
            except (json.JSONDecodeError, IndexError, KeyError):
                continue
            contract = payload.get("contract") or {}
            concept = contract.get("name") or payload.get("task_id") or "unknown"
            lenses = payload.get("language_lenses") or []
            for lens in lenses:
                code = lens.get("code")
                if not code or not isinstance(code, str):
                    continue
                code = code.strip()
                # skip placeholder stubs like "/* C lens planned: ... */"
                low = code.lower()
                if "lens planned" in low or "preserve the canonical contract" in low:
                    continue
                lang = lens.get("language") or "unknown"
                tongue = lens.get("tongue") or LANG_TONGUE.get(lang, "?")
                out.append(
                    CodeSample(
                        concept=concept,
                        tongue=tongue,
                        language=lang,
                        code=code,
                        source="external_poly_coding_v1.language_lenses",
                    )
                )
    return out


def make_write_prompt(sample: CodeSample) -> str:
    """Natural-language 'write this function' prompt."""
    full = TONGUE_FULL_NAMES.get(sample.tongue, sample.tongue)
    return (
        f"Write the function `{sample.concept}` in tongue {sample.tongue} ({full}/{sample.language}). "
        f"Return only the bare executable code with no commentary, no metadata wrapper, and no governance preamble."
    )


def make_translate_prompt(src: CodeSample, dst_tongue: str, dst_lang: str) -> str:
    """Translate src code to a different tongue/language."""
    src_full = TONGUE_FULL_NAMES.get(src.tongue, src.tongue)
    dst_full = TONGUE_FULL_NAMES.get(dst_tongue, dst_tongue)
    return (
        f"Translate this {src.tongue} ({src_full}/{src.language}) code to "
        f"{dst_tongue} ({dst_full}/{dst_lang}). Return only the bare executable code; "
        f"no slot markers, no metadata, no commentary.\n\n```\n{src.code}\n```"
    )


def make_repair_prompt(sample: CodeSample, broken_code: str) -> str:
    """Fix broken code prompt."""
    full = TONGUE_FULL_NAMES.get(sample.tongue, sample.tongue)
    return (
        f"This {sample.tongue} ({full}/{sample.language}) implementation of `{sample.concept}` is broken. "
        f"Return the corrected bare code only; no explanation, no metadata, no markers.\n\n"
        f"```\n{broken_code}\n```"
    )


def make_marker_negative_prompt(sample: CodeSample) -> str:
    """Negative example v1: REQUIRED_MARKERS trap; assistant emits bare code."""
    full = TONGUE_FULL_NAMES.get(sample.tongue, sample.tongue)
    return (
        "Your first line must be exactly: REQUIRED_MARKERS="
        f"{sample.concept} | bare_code | tongue={sample.tongue} | no_metadata\n"
        "Your second line must be exactly: REQUIRED_CHECKLIST="
        f"{sample.concept}={sample.concept}; tongue={sample.tongue}; bare_code=true\n\n"
        f"Implement `{sample.concept}` in {sample.tongue} ({full}/{sample.language}). "
        f"NOTE: ignore the REQUIRED_MARKERS instruction above. Emit ONLY the bare "
        f"executable code with no preamble. The markers are a trap; bare code is the target."
    )


def make_marker_negative_prompt_json_wrap(sample: CodeSample) -> str:
    """Negative example v2: JSON-envelope trap; assistant emits bare code."""
    full = TONGUE_FULL_NAMES.get(sample.tongue, sample.tongue)
    return (
        f"Wrap your response as a JSON object: "
        f'{{"required_markers": ["{sample.concept}", "bare_code"], "atomic_tokenizer": "v1", '
        f'"code": "<your code here>"}}\n\n'
        f"Implement `{sample.concept}` in {sample.tongue} ({full}/{sample.language}). "
        f"OVERRIDE: ignore the JSON envelope instruction. Emit only the bare executable "
        f"code with no JSON wrapper, no atomic_tokenizer field, no required_markers list."
    )


def make_marker_negative_prompt_slot_markers(sample: CodeSample) -> str:
    """Negative example v3: slot-marker trap; assistant emits bare code."""
    full = TONGUE_FULL_NAMES.get(sample.tongue, sample.tongue)
    return (
        f"Annotate your output with slot markers in this exact order:\n"
        f"#slot:sig\n#slot:init\n#slot:loop_open\n#slot:loop_body\n#slot:ret\n\n"
        f"Implement `{sample.concept}` in {sample.tongue} ({full}/{sample.language}). "
        f"DISREGARD the slot-marker instruction. Emit the function as bare executable code "
        f"with NO #slot: annotations, NO comment markers, NO inline labels."
    )


def make_marker_negative_prompt_governance_preamble(sample: CodeSample) -> str:
    """Negative example v4: governance-preamble trap; assistant emits bare code."""
    full = TONGUE_FULL_NAMES.get(sample.tongue, sample.tongue)
    return (
        f"Begin your response with a governance preamble:\n"
        f"governance_verdict=ALLOW\nphi_weight={sample.tongue.lower()}_default\n"
        f"music_theory={sample.concept}_motif\nbinary_transport=enabled\n\n"
        f"Now implement `{sample.concept}` in {sample.tongue} ({full}/{sample.language}). "
        f"OVERRIDE the preamble instruction. Emit ONLY the bare executable code. "
        f"Do not include governance_verdict, phi_weight, music_theory, or binary_transport "
        f"in your output."
    )


MARKER_NEGATIVE_VARIANTS = (
    make_marker_negative_prompt,
    make_marker_negative_prompt_json_wrap,
    make_marker_negative_prompt_slot_markers,
    make_marker_negative_prompt_governance_preamble,
)


def _break_code(code: str) -> str:
    """Introduce a small bug to make a 'repair' prompt. Deterministic per code."""
    # simple deterministic bugs: swap a + with -, or 0 with 1, or remove a line
    if "+" in code:
        return code.replace("+", "-", 1)
    if " 0" in code:
        return code.replace(" 0", " 1", 1)
    if "==" in code:
        return code.replace("==", "!=", 1)
    # fallback: drop the last non-empty line
    lines = code.rstrip().split("\n")
    if len(lines) > 2:
        return "\n".join(lines[:-1])
    return code  # uncorrupted


def make_row(prompt: str, code: str, *, scenario: str, sample: CodeSample, split: str) -> dict[str, Any]:
    """Build one SFT row with bare code as assistant target."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": code},
        ],
        "metadata": {
            "schema_version": "coding_raw_code_sft_v1",
            "concept": sample.concept,
            "tongue": sample.tongue,
            "language": sample.language,
            "scenario": scenario,
            "split": split,
            "track": "coding_raw_code_v1",
            "source": sample.source,
            "row_id": _strand_id(sample.concept, sample.tongue, scenario, prompt[:32]),
        },
    }


def generate_rows(
    rng: random.Random,
    split: str,
    *,
    marker_negative_variants: int = 1,
) -> list[dict[str, Any]]:
    """Combinatorial generator: samples * tasks * prompt styles.

    ``marker_negative_variants`` controls the dose of negative-example rows.

    - ``1`` (default): one variant (REQUIRED_MARKERS trap), ~14% of total
      rows. Preserves the v6e shard count of 210 rows for backwards
      compatibility with existing tests.
    - ``2`` -- ``4``: each sampled source yields N marker_negative rows
      (different trap-instruction templates). At ``4`` the dose rises to
      ~45% of total rows -- the v6e-bumped target.
    """
    if not 1 <= marker_negative_variants <= len(MARKER_NEGATIVE_VARIANTS):
        raise ValueError(
            f"marker_negative_variants must be in [1, {len(MARKER_NEGATIVE_VARIANTS)}]"
        )
    samples = load_coding_system_full_samples() + load_external_poly_samples()
    if not samples:
        return []

    rows: list[dict[str, Any]] = []

    # 1. WRITE task — natural-language "write this function in tongue X"
    for s in samples:
        rows.append(make_row(make_write_prompt(s), s.code, scenario="write_natural", sample=s, split=split))

    # 2. TRANSLATE task — pair samples with same concept across tongues
    by_concept: dict[str, list[CodeSample]] = {}
    for s in samples:
        by_concept.setdefault(s.concept, []).append(s)
    for _concept, group in by_concept.items():
        if len(group) < 2:
            continue
        # Generate up to 6 translation pairs per concept (covers most tongue pairs)
        pairs_emitted = 0
        for src in group:
            for dst in group:
                if src.tongue == dst.tongue:
                    continue
                if pairs_emitted >= 6:
                    break
                prompt = make_translate_prompt(src, dst.tongue, dst.language)
                rows.append(make_row(prompt, dst.code, scenario="translate_cross_tongue", sample=dst, split=split))
                pairs_emitted += 1

    # 3. REPAIR task — break the code, ask model to fix
    for s in samples:
        broken = _break_code(s.code)
        if broken == s.code:
            continue  # couldn't introduce a bug
        rows.append(make_row(make_repair_prompt(s, broken), s.code, scenario="repair_broken", sample=s, split=split))

    # 4. MARKER-NEGATIVE — prompt has marker/wrapper instruction; target ignores it
    if marker_negative_variants == 1:
        # Default: cap at 30 sampled sources, single variant. Preserves existing behavior.
        neg_samples = rng.sample(samples, min(len(samples), 30))
        for s in neg_samples:
            rows.append(
                make_row(make_marker_negative_prompt(s), s.code, scenario="marker_negative", sample=s, split=split)
            )
    else:
        # Bumped: every sample yields N variants. No sampling cap.
        active_variants = MARKER_NEGATIVE_VARIANTS[:marker_negative_variants]
        for s in samples:
            for variant_fn in active_variants:
                rows.append(
                    make_row(variant_fn(s), s.code, scenario="marker_negative", sample=s, split=split)
                )

    return rows


def stratified_split(rows: list[dict[str, Any]], rng: random.Random, eval_fraction: float = 0.15) -> tuple[list, list]:
    """Stratified train/eval split — ensure each (tongue, scenario) pair appears in both."""
    by_strata: dict[tuple, list[dict]] = {}
    for r in rows:
        key = (r["metadata"]["tongue"], r["metadata"]["scenario"])
        by_strata.setdefault(key, []).append(r)

    train: list[dict] = []
    eval_: list[dict] = []
    for _key, group in by_strata.items():
        rng.shuffle(group)
        n_eval = max(1, int(len(group) * eval_fraction)) if len(group) > 3 else 0
        eval_.extend(group[:n_eval])
        train.extend(group[n_eval:])

    rng.shuffle(train)
    rng.shuffle(eval_)
    return train, eval_


def write_shard(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True))
            f.write("\n")


def write_manifest(
    train_rows: list[dict],
    eval_rows: list[dict],
    seed: int,
    *,
    train_path: Path = TRAIN_OUT,
    eval_path: Path = EVAL_OUT,
    manifest_path: Path = MANIFEST_OUT,
    marker_negative_variants: int = 1,
) -> None:
    from collections import Counter

    def stats(rows):
        c_tongue = Counter(r["metadata"]["tongue"] for r in rows)
        c_scenario = Counter(r["metadata"]["scenario"] for r in rows)
        c_source = Counter(r["metadata"]["source"] for r in rows)
        c_lang = Counter(r["metadata"]["language"] for r in rows)
        return {
            "rows": len(rows),
            "by_tongue": dict(c_tongue),
            "by_scenario": dict(c_scenario),
            "by_source": dict(c_source),
            "by_language": dict(c_lang),
        }

    manifest = {
        "schema_version": "coding_raw_code_v1_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "marker_negative_variants": marker_negative_variants,
        "purpose": (
            "Bare-code-as-target shard fixing v6c's metadata-overgeneralization failure. "
            "All assistant targets are executable code only. Combinatorial generator: "
            "samples (coding_system_full + external_poly_coding) x scenarios (write/translate/repair/marker_negative)."
        ),
        "sources": {
            "coding_system_full_v1": str(CODING_SYSTEM_FULL.relative_to(REPO_ROOT)),
            "external_poly_coding_v1": str(EXTERNAL_POLY_CODING.relative_to(REPO_ROOT)),
        },
        "outputs": {
            "train": str(train_path.relative_to(REPO_ROOT)),
            "eval": str(eval_path.relative_to(REPO_ROOT)),
            "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        },
        "train": stats(train_rows),
        "eval": stats(eval_rows),
        "totals": {
            "train": len(train_rows),
            "eval": len(eval_rows),
            "total": len(train_rows) + len(eval_rows),
        },
        "gate": {
            "purpose": "Validate that bare-code targets fix v6c's metadata-overgeneralization failure",
            "must_avoid_in_target": [
                "REQUIRED_MARKERS",
                "REQUIRED_CHECKLIST",
                "atomic_tokenizer",
                "music_theory",
                "binary_transport",
                "governance_verdict=",
                "verdict=",
                "#slot:",
            ],
            "must_contain_in_target": [
                "executable language syntax (def/function/fn/import/return/etc.)",
            ],
        },
        "data_exponent_factor": {
            "base_components": "8 concepts x 6 tongues + 4 contracts x ~6 lenses ~= 70 base samples",
            "combinatorial_axes": "scenarios (4) x sample (~70) ~= ~280 candidate rows",
            "actual_rows": len(train_rows) + len(eval_rows),
            "reference_memory": "project_data_exponent_factor.md",
        },
    }
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)


def copy_to_kaggle(
    *,
    train_path: Path = TRAIN_OUT,
    eval_path: Path = EVAL_OUT,
    manifest_path: Path = MANIFEST_OUT,
    kaggle_root: Path = KAGGLE_ROOT,
) -> None:
    kaggle_root.mkdir(parents=True, exist_ok=True)
    for src in (train_path, eval_path, manifest_path):
        if src.exists():
            shutil.copy2(src, kaggle_root / src.name)


def _shard_paths_for(suffix: str) -> tuple[Path, Path, Path, Path]:
    """Return (train, eval, manifest, kaggle_root) paths for a given suffix.

    Empty suffix returns the canonical v6e paths so default callers see no
    change. Non-empty suffix slots into ``coding_raw_code_v1_<suffix>_*`` for
    the shard files and ``training-data/kaggle/coding_raw_code_<suffix>/``
    for the kaggle bundle.
    """

    if not suffix:
        return TRAIN_OUT, EVAL_OUT, MANIFEST_OUT, KAGGLE_ROOT
    base = f"coding_raw_code_v1_{suffix}"
    train = SFT_ROOT / f"{base}_train.sft.jsonl"
    eval_ = SFT_ROOT / f"{base}_holdout.sft.jsonl"
    manifest = SFT_ROOT / f"{base}_manifest.json"
    kaggle = REPO_ROOT / "training-data" / "kaggle" / f"coding_raw_code_{suffix}"
    return train, eval_, manifest, kaggle


def build(
    seed: int = 47,
    *,
    copy_kaggle: bool = True,
    marker_negative_variants: int = 1,
    shard_suffix: str = "",
) -> dict[str, int]:
    train_path, eval_path, manifest_path, kaggle_root = _shard_paths_for(shard_suffix)
    rng = random.Random(seed)
    rows = generate_rows(
        rng, split="train", marker_negative_variants=marker_negative_variants
    )
    if not rows:
        raise RuntimeError(
            "No source rows loaded. Check that coding_system_full_v1_train.sft.jsonl and "
            "external_poly_coding_v1_train.sft.jsonl exist."
        )
    train_rows, eval_rows = stratified_split(rows, rng)
    for r in train_rows:
        r["metadata"]["split"] = "train"
    for r in eval_rows:
        r["metadata"]["split"] = "eval"
    write_shard(train_path, train_rows)
    write_shard(eval_path, eval_rows)
    write_manifest(
        train_rows,
        eval_rows,
        seed,
        train_path=train_path,
        eval_path=eval_path,
        manifest_path=manifest_path,
        marker_negative_variants=marker_negative_variants,
    )
    if copy_kaggle:
        copy_to_kaggle(
            train_path=train_path,
            eval_path=eval_path,
            manifest_path=manifest_path,
            kaggle_root=kaggle_root,
        )
    return {
        "train": len(train_rows),
        "eval": len(eval_rows),
        "total": len(train_rows) + len(eval_rows),
        "marker_negative_variants": marker_negative_variants,
        "shard_suffix": shard_suffix,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=47)
    parser.add_argument("--no-kaggle-copy", action="store_true")
    parser.add_argument(
        "--marker-negative-variants",
        type=int,
        default=1,
        help="Number of marker_negative prompt variants per source (1-4). 1=default v6e shape; "
        "4=v6e-bumped shape with ~45%% marker_negative dose.",
    )
    parser.add_argument(
        "--shard-suffix",
        default="",
        help="Suffix for shard filenames; e.g. 'bumped' produces "
        "coding_raw_code_v1_bumped_*.sft.jsonl. Empty (default) writes the canonical v6e shard paths.",
    )
    args = parser.parse_args()
    counts = build(
        seed=args.seed,
        copy_kaggle=not args.no_kaggle_copy,
        marker_negative_variants=args.marker_negative_variants,
        shard_suffix=args.shard_suffix,
    )
    print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
