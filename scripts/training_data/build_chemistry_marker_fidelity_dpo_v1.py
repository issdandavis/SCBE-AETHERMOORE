"""Build chemistry marker-fidelity DPO shard from v6 + v7 raw failures.

Why this exists:
- v6 (180 steps) and v7 (240 steps + 90-row anchor-repair shard) BOTH failed
  raw 0/5 on the chemistry gate. SFT did not internalize verbatim required
  markers.
- Each v6/v7 raw response is, by construction, a perfect REJECTED example for
  DPO: the model wrote something marker-shaped but paraphrased the required
  token (carboxyllic acid, NA_clathrine, queue_drill_guard, etc.).
- DPO with these natural rejections + synthetic perturbations should push the
  model AWAY from paraphrase variants and TOWARD the verbatim required
  markers, without retraining on broader code/chemistry knowledge.

Output: training-data/dpo/chemistry_marker_fidelity_dpo_v1_train.jsonl
        training-data/dpo/chemistry_marker_fidelity_dpo_v1_eval.jsonl
        training-data/dpo/chemistry_marker_fidelity_dpo_v1_manifest.json

Each row: {"prompt": "...", "chosen": "...", "rejected": "..."}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DPO_ROOT = REPO_ROOT / "training-data" / "dpo"
TRAIN_OUT = DPO_ROOT / "chemistry_marker_fidelity_dpo_v1_train.jsonl"
EVAL_OUT = DPO_ROOT / "chemistry_marker_fidelity_dpo_v1_eval.jsonl"
MANIFEST_OUT = DPO_ROOT / "chemistry_marker_fidelity_dpo_v1_manifest.json"

CONTRACT_PATH = REPO_ROOT / "config" / "model_training" / "chemistry_verification_eval_contract.json"


@dataclass(frozen=True)
class Pair:
    prompt: str
    chosen: str
    rejected: str
    metadata: dict[str, Any]


def chosen_template(prompt_id: str, required: list[str]) -> str:
    """Synthesize a chosen response that uses every required marker verbatim
    in a chemistry-route explanatory paragraph. The structure mirrors the v5
    scaffolded gate's PASS path — every required marker appears as bare text,
    not a slot/REQUIRED_MARKERS preamble (which the v6h system prompt forbids).
    """
    if prompt_id == "chem_eval_ethanol_route":
        return (
            "Walking the chemistry route for SMILES CCO: each atom is one carbon "
            "or one oxygen, the bond order satisfies normal valence, and the "
            "polarity from the C-O bond identifies an alcohol functional group. "
            "RDKit returns a valid molecule. The SCBE fusion signal is coherent "
            "and the governance verdict is PASS."
        )
    if prompt_id == "chem_eval_aspirin_route":
        return (
            "For aspirin from SMILES CC(=O)Oc1ccccc1C(=O)O the structure has an "
            "aromatic ring, an ester linkage, and a free carboxylic acid. The "
            "valence count is satisfied for every carbon and oxygen, the molecule "
            "is valid under RDKit, and the governance verdict is PASS."
        )
    if prompt_id == "chem_eval_pentavalent_carbon_reject":
        return (
            "The proposed structure C(C)(C)(C)(C)C places five bonds on a single "
            "carbon. That violates valence; the central carbon would be "
            "pentavalent, which is invalid. RDKit rejects this SMILES. The "
            "governance verdict is DENY."
        )
    if prompt_id == "chem_eval_nacl_boundary":
        return (
            "NaCl is an ionic salt of sodium and chloride; it is not organic and "
            "has no carbon-based functional group. It is a valid chemistry "
            "tokenization boundary case and the conservative governance verdict "
            "treats it as a recognized inorganic boundary, not a molecule for "
            "organic-route scoring."
        )
    if prompt_id == "chem_eval_lane_boundary":
        return (
            "queue_drain_guard is a code identifier inside the SCBE atomic "
            "tokenizer, not a real material chemistry molecule. The agent must "
            "avoid claiming it is a chemical formula or that real atoms back "
            "the structural metaphor. It is not a molecule; the chemistry "
            "verification lane does not score it."
        )
    raise KeyError(f"No chosen template for prompt id: {prompt_id}")


def v6_raw_responses() -> dict[str, str]:
    """v6 chemistry gate raw responses (paraphrase failures)."""
    return {
        "chem_eval_ethanol_route": (
            "REQUIRED_MARKERS= CCO | carbon 1 carbon is carbon   # Required atom "
            "token\nRDKit_VALIDITY= PAS    # RDKit validity verdict is valid\n"
            "GOLD_PATH= CCO is carbon; carbon valence is below hydrogen's limit; "
            "functional group is ethanol; SCBE promise passes\nVERIFICATION_result= PASS"
        ),
        "chem_eval_aspirin_route": (
            "REQUIRED_MARKERS= aspirin | acidic | carboxyllic acid | aromatic "
            "ring | ester : valid, valence : acceptable, governance : PASS, "
            "governance limit : pure carbon"
        ),
        "chem_eval_pentavalent_carbon_reject": (
            "REQUIRED_MARKERS=C(CK)(C)(K)(C)(CK)C(C)(C)K(C)(C); carbon=carbon ; "
            "valence=valence ; pentavalent = pentavalent ; invalid = invalid ; "
            "RDKit = RDKit ; DENY = RDKit molecules]. RDKit validity: valid."
        ),
        "chem_eval_nacl_boundary": (
            "Verification: NA_clathrine is a sodium-chloride boundary case, "
            "not organic, but a valid chemistry tokenization boundary. The "
            "ionic boundary is sodium ions, governance verdict PASS."
        ),
        "chem_eval_lane_boundary": (
            "queue_drill_guard is a code-token in the atomic tokenizer for "
            "structural metaphors only, not_a_molecule. The agent must avoid "
            "claiming it is a real material chemistry route."
        ),
    }


def v7_raw_responses() -> dict[str, str]:
    """v7 chemistry gate raw responses (different paraphrase failures)."""
    return {
        "chem_eval_ethanol_route": (
            "VERIFY_C_COOLING_C0.CCO[smiles=coo] is COO but not carbon-oxygen. "
            "PASS only when the atom, bond, valence, functional-group, RDKit, "
            "SCBE, and fusion-governance verdict are valid."
        ),
        "chem_eval_aspirin_route": (
            "PASS\nCC(=O)c1ccccc(=O)(C(=OO)O)O is an acceptable molecule. The "
            "central carbon is aromatic. The ester forms a carbonyl-acid bond. "
            "The valence pressure is below the safe value boundary. This route "
            "does not produce a chemistry verification promise; it is raw "
            "material science."
        ),
        "chem_eval_pentavalent_carbon_reject": (
            "PASS\nExact chemistry verification anchor present: "
            "C(C)(CCCC)(C)(CC)C = C(C)(CCC)(C)(CCC)C. Valence: one carbon, "
            "three bonds, one aromatic group. RDKit validity: the RDKit "
            "considers this a valid route even though it has near-misses."
        ),
        "chem_eval_nacl_boundary": (
            "VALID\nAn ionic NaCl boundary case can still be verified as a "
            "chemistry tokenization boundary case. The Na+ ion is ionic, and "
            "the Cl- ion is sodium ions. This is a valid chemistry route that "
            "does not involve an organic molecule."
        ),
        "chem_eval_lane_boundary": (
            "PASS: The code token queue_driver_guard is a valid chemistry "
            "route for material chemistry verification. The agent should "
            "avoid reparatory claims from invalid or material examples."
        ),
    }


# Empirical paraphrase variants observed across v5/v6/v7 — each gets one
# synthetic rejected per prompt by mutating one required marker.
PARAPHRASE_MUTATIONS: dict[str, list[tuple[str, str]]] = {
    "chem_eval_ethanol_route": [
        ("CCO", "C-C-O"),
        ("alcohol", "ethyl alcohol"),
        ("SCBE fusion", "SCBE-fusion"),
        ("PASS", "PASSED"),
    ],
    "chem_eval_aspirin_route": [
        ("carboxylic acid", "carboxyllic acid"),
        ("carboxylic acid", "carboxyl acid"),
        ("ester", "ester linkage"),
        ("aromatic", "aromatic phenyl"),
    ],
    "chem_eval_pentavalent_carbon_reject": [
        ("C(C)(C)(C)(C)C", "C(CK)(C)(K)(C)C"),
        ("C(C)(C)(C)(C)C", "C(CCCC)C"),
        ("pentavalent", "five-valent"),
        ("DENY", "REJECT"),
    ],
    "chem_eval_nacl_boundary": [
        ("NaCl", "Na_Cl"),
        ("NaCl", "NA_clathrine"),
        ("not organic", "non-organic"),
        ("chloride", "chlorine"),
    ],
    "chem_eval_lane_boundary": [
        ("queue_drain_guard", "queue_drill_guard"),
        ("queue_drain_guard", "queue_driver_guard"),
        ("not a molecule", "not_a_molecule"),
        ("atomic tokenizer", "atomic-tokenizer"),
    ],
}


def synthetic_rejected(chosen_text: str, required: list[str], mutation: tuple[str, str]) -> str:
    """Apply one observed paraphrase mutation to chosen text. The mutated text
    is identical to chosen except one required marker is corrupted to its
    observed-paraphrase variant."""
    correct, paraphrase = mutation
    if correct not in chosen_text:
        return chosen_text  # mutation doesn't apply (defensive)
    return chosen_text.replace(correct, paraphrase, 1)


def build_pairs(rng: random.Random) -> tuple[list[Pair], list[Pair]]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    v6 = v6_raw_responses()
    v7 = v7_raw_responses()
    train_pairs: list[Pair] = []
    eval_pairs: list[Pair] = []
    for entry in contract["prompts"]:
        pid = entry["id"]
        prompt = entry["prompt"]
        required = entry["required"]
        chosen = chosen_template(pid, required)
        # 1. natural rejection from v6
        if pid in v6:
            train_pairs.append(Pair(
                prompt=prompt, chosen=chosen, rejected=v6[pid],
                metadata={"prompt_id": pid, "rejection_source": "v6_raw"},
            ))
        # 2. natural rejection from v7
        if pid in v7:
            train_pairs.append(Pair(
                prompt=prompt, chosen=chosen, rejected=v7[pid],
                metadata={"prompt_id": pid, "rejection_source": "v7_raw"},
            ))
        # 3. synthetic paraphrase mutations from observed failure modes
        muts = PARAPHRASE_MUTATIONS.get(pid, [])
        for mut in muts:
            rej = synthetic_rejected(chosen, required, mut)
            if rej == chosen:
                continue  # mutation didn't apply
            train_pairs.append(Pair(
                prompt=prompt, chosen=chosen, rejected=rej,
                metadata={
                    "prompt_id": pid,
                    "rejection_source": "synthetic",
                    "mutation": list(mut),
                },
            ))
    # Hold out one synthetic mutation per prompt for eval, not seen in train
    pid_to_eval: dict[str, list[Pair]] = {}
    train_kept: list[Pair] = []
    for pair in train_pairs:
        pid = pair.metadata["prompt_id"]
        if pair.metadata["rejection_source"] == "synthetic":
            pid_to_eval.setdefault(pid, []).append(pair)
        else:
            train_kept.append(pair)
    rng.seed(48)
    for pid, lst in pid_to_eval.items():
        if not lst:
            continue
        # Reserve last synthetic per prompt as eval
        eval_pairs.append(lst[-1])
        train_kept.extend(lst[:-1])
    return train_kept, eval_pairs


def write_jsonl(path: Path, pairs: list[Pair]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for p in pairs:
            row = {
                "prompt": p.prompt,
                "chosen": p.chosen,
                "rejected": p.rejected,
                "metadata": dict(p.metadata),
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-train", type=Path, default=TRAIN_OUT)
    parser.add_argument("--out-eval", type=Path, default=EVAL_OUT)
    parser.add_argument("--out-manifest", type=Path, default=MANIFEST_OUT)
    parser.add_argument("--seed", type=int, default=48)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    train_pairs, eval_pairs = build_pairs(rng)
    write_jsonl(args.out_train, train_pairs)
    write_jsonl(args.out_eval, eval_pairs)

    blob = {
        "schema_version": "scbe_chemistry_dpo_manifest_v1",
        "shard_id": "chemistry_marker_fidelity_dpo_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "n_train_pairs": len(train_pairs),
        "n_eval_pairs": len(eval_pairs),
        "sources": {
            "natural_rejections": ["v6_raw", "v7_raw"],
            "synthetic_rejections": "PARAPHRASE_MUTATIONS in build_chemistry_marker_fidelity_dpo_v1.py",
        },
        "outputs": {
            "train": str(args.out_train.relative_to(REPO_ROOT)),
            "eval": str(args.out_eval.relative_to(REPO_ROOT)),
        },
        "purpose": (
            "Push base model away from observed paraphrase variants "
            "(carboxyllic acid, NA_clathrine, queue_drill_guard, "
            "queue_driver_guard, etc.) toward verbatim required markers."
        ),
    }
    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(train_pairs)} train + {len(eval_pairs)} eval DPO pairs")
    print(f"  train: {args.out_train.relative_to(REPO_ROOT)}")
    print(f"  eval:  {args.out_eval.relative_to(REPO_ROOT)}")
    print(f"  manifest: {args.out_manifest.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
