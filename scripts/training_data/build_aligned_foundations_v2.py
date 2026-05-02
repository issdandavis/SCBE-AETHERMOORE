"""Build v2 aligned-foundations packet with coding face + concept_id threading.

v2 improvements over v1 (`scripts/build_aligned_foundations_sft.py`):
- adds the coding face (KO=Python, AV=TypeScript, RU=Rust, CA=C, UM=Julia, DR=Haskell)
  for tongue and coding-primitive concepts
- threads `concept_id` through every row's meta so cross-face alignment can be
  audited per-concept (one concept_id, one canonical fact set)
- expands categories: 5 quantum axioms, 12 coding primitives, denser chemistry
- keeps the v1 per-row pattern (one row teaches one concept across all
  applicable faces in a single assistant response) so routing models can still
  learn whole-packet emission

Outputs (under `training-data/sft/`):
- aligned_foundations_v2_train.sft.jsonl
- aligned_foundations_v2_holdout.sft.jsonl
- aligned_foundations_v2_manifest.json (counts + category breakdown + concept_id list)
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SFT_ROOT = REPO_ROOT / "training-data" / "sft"

TRAIN_OUT = SFT_ROOT / "aligned_foundations_v2_train.sft.jsonl"
EVAL_OUT = SFT_ROOT / "aligned_foundations_v2_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "aligned_foundations_v2_manifest.json"

SYSTEM = (
    "You are an SCBE aligned-foundations tutor. Teach the same concept in "
    "synchronized forms: mathematics, plain English, Sacred Tongues lane "
    "naming, binary or packet framing, and coding face when applicable. Keep "
    "answers structured, concise, and invariant-preserving across all faces."
)

TONGUES = [
    ("KO", "Kor'aelin", "intent", "Python"),
    ("AV", "Avali", "context", "TypeScript"),
    ("RU", "Runethic", "relation", "Rust"),
    ("CA", "Cassisivadan", "implementation", "C"),
    ("UM", "Umbroth", "veil", "Julia"),
    ("DR", "Draumric", "structure", "Haskell"),
]

LAYERS = [
    ("L01", "complex context ingestion", "raw input lifted into complex vectors"),
    ("L02", "realification", "complex to real with norm preserved"),
    ("L03", "weighted transform", "phi-scaled tongue weights applied"),
    ("L04", "poincare embedding", "weighted vectors enter the hyperbolic ball"),
    ("L05", "hyperbolic distance", "arcosh metric in the Poincare ball"),
    ("L06", "breathing transform", "oscillatory temporal modulation"),
    ("L07", "mobius phase", "isometric phase rotation in hyperbolic space"),
    ("L08", "hamiltonian CFI", "multi-well realm dynamics"),
    ("L09", "spectral coherence", "FFT-based frequency analysis"),
    ("L10", "spin coherence", "quantum-spin alignment of the signal"),
    ("L11", "triadic temporal", "three-scale temporal intent accumulation"),
    ("L12", "harmonic wall", "1/(1+phi*d_H+2*pd) safety score"),
    ("L13", "risk decision", "ALLOW QUARANTINE ESCALATE DENY governance"),
    ("L14", "audio axis", "phase-modulated telemetry waveform"),
]

RISK_TIERS = [
    ("ALLOW", "safe to proceed inside bounds", "00"),
    ("QUARANTINE", "hold and isolate for closer inspection", "01"),
    ("ESCALATE", "send upward for higher-authority review", "10"),
    ("DENY", "block because the action violates bounds", "11"),
]

AXIOMS = [
    ("A1", "unitarity", "norm preservation across the transform", "L02 L04 L07"),
    ("A2", "locality", "spatial bounds keep operators local", "L03 L08"),
    ("A3", "causality", "time-ordering of events is respected", "L06 L11 L13"),
    ("A4", "symmetry", "gauge invariance under valid transforms", "L05 L09 L10 L12"),
    ("A5", "composition", "pipeline integrity under sequential application", "L01 L14"),
]

CHEMISTRY_CASES = [
    ("2H2 + O2 -> 2H2O", "stable", "synthesis", "atoms conserved and products well-formed", "UM"),
    ("HCl + NaOH -> NaCl + H2O", "stable", "neutralization", "acid-base balance closes cleanly", "AV"),
    ("2Na + 2H2O -> 2NaOH + H2", "unstable", "displacement", "reactivity is high and release is vigorous", "RU"),
    ("2Al + Fe2O3 -> Al2O3 + 2Fe", "unstable", "redox", "thermite-style energy release", "RU"),
    ("CH4 + 2O2 -> CO2 + 2H2O", "stable", "combustion", "complete oxidation balances cleanly", "CA"),
    ("N2 + 3H2 -> 2NH3", "stable", "synthesis", "Haber process closes nitrogen and hydrogen lanes", "UM"),
    ("CaCO3 -> CaO + CO2", "stable", "decomposition", "thermal split releases the CO2 lane", "DR"),
    ("Fe + S -> FeS", "stable", "synthesis", "direct combination forms iron sulfide", "CA"),
    ("Zn + 2HCl -> ZnCl2 + H2", "stable", "displacement", "zinc displaces hydrogen from acid", "AV"),
    ("2KClO3 -> 2KCl + 3O2", "unstable", "decomposition", "thermal release of oxygen is energetic", "RU"),
    ("AgNO3 + NaCl -> AgCl + NaNO3", "stable", "double-displacement", "silver chloride precipitates cleanly", "KO"),
    ("CO2 + H2O -> H2CO3", "stable", "synthesis", "carbonic acid formation under aqueous lane", "UM"),
]

CODING_PRIMITIVES = [
    ("ring_buffer", "RU", "Rust", "fn push(&mut self, x: T) { self.buf[self.head] = x; self.head = (self.head + 1) % self.cap; }",
     "fixed-capacity wraparound buffer with O(1) push"),
    ("list_comprehension", "KO", "Python", "squares = [x*x for x in range(10)]",
     "concise mapping over an iterable"),
    ("react_state_hook", "AV", "TypeScript", "const [count, setCount] = useState<number>(0);",
     "browser-side reactive state primitive"),
    ("malloc_free_pair", "CA", "C", "char* buf = malloc(n); /* use */ free(buf);",
     "manual heap allocation with explicit release"),
    ("matrix_mul", "UM", "Julia", "C = A * B",
     "scientific dense matrix multiplication"),
    ("monadic_bind", "DR", "Haskell", "x >>= \\v -> return (v + 1)",
     "pure functional sequencing through a monad"),
    ("dict_comprehension", "KO", "Python", "by_id = {u.id: u for u in users}",
     "concise mapping into a dictionary"),
    ("async_await_fetch", "AV", "TypeScript", "const r = await fetch(url); const j = await r.json();",
     "non-blocking IO sequencing in the browser"),
    ("borrow_checker_slice", "RU", "Rust", "fn first<'a>(xs: &'a [T]) -> &'a T { &xs[0] }",
     "lifetime-checked borrow of a slice"),
    ("pointer_struct", "CA", "C", "struct Node { int v; struct Node* next; };",
     "low-level linked-list node by pointer"),
    ("broadcast_op", "UM", "Julia", "y = sin.(x)",
     "elementwise broadcast over an array"),
    ("type_class_eq", "DR", "Haskell", "instance Eq Color where Red == Red = True; _ == _ = False",
     "type-class instance for structural equality"),
]


def make_record(user: str, assistant: str, *, category: str, concept_id: str, faces: list[str], holdout: bool) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {
            "program": "aligned_foundations_v2",
            "category": category,
            "concept_id": concept_id,
            "faces": faces,
            "split": "holdout" if holdout else "train",
        },
    }


def letter_records() -> list[dict]:
    rows: list[dict] = []
    for idx, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=1):
        binary = format(idx, "05b")
        cid = f"alphabet:{letter}"
        user = f"Align the primitive symbol {letter} across math, English, and binary."
        assistant = (
            f"math: symbol_index({letter}) = {idx}\n"
            f"english: the letter {letter} is primitive symbol {idx}\n"
            f"binary: {idx} -> {binary}\n"
            f"invariant: one symbol, one index, one binary encoding"
        )
        rows.append(make_record(user, assistant,
                                category="alphabet", concept_id=cid,
                                faces=["math", "english", "binary"],
                                holdout=idx % 5 == 0))
    return rows


def number_records() -> list[dict]:
    rows: list[dict] = []
    for value in range(16):
        binary = format(value, "04b")
        parity = "even" if value % 2 == 0 else "odd"
        cid = f"digit:{value:02d}"
        user = f"Teach the number {value} in aligned foundations form."
        assistant = (
            f"math: {value}\n"
            f"english: the quantity is {value} and its parity is {parity}\n"
            f"binary: {binary}\n"
            f"invariant: decimal {value} maps exactly to binary {binary}"
        )
        rows.append(make_record(user, assistant,
                                category="numbers", concept_id=cid,
                                faces=["math", "english", "binary"],
                                holdout=value % 4 == 3))
    return rows


def tongue_records() -> list[dict]:
    rows: list[dict] = []
    for idx, (abbr, full_name, duty, language) in enumerate(TONGUES):
        cid = f"tongue:{abbr}"
        user = f"State the Sacred Tongue mapping for {abbr} including coding face."
        assistant = (
            f"abbr: {abbr}\n"
            f"full_name: {full_name}\n"
            f"duty: {duty}\n"
            f"coding_face: {abbr} -> {language}\n"
            f"invariant: {abbr} and {full_name} refer to one lane; coding face is {language}"
        )
        rows.append(make_record(user, assistant,
                                category="tongues", concept_id=cid,
                                faces=["english", "sacred_tongues", "coding"],
                                holdout=idx % 3 == 2))
    return rows


def layer_records() -> list[dict]:
    rows: list[dict] = []
    for idx, (code, name, role) in enumerate(LAYERS):
        cid = f"layer:{code}"
        user = f"Teach {code} in aligned foundations form."
        assistant = (
            f"layer: {code}\n"
            f"name: {name}\n"
            f"role: {role}\n"
            f"invariant: {code} and {name} identify the same layer function"
        )
        # holdout last 3 layers: L12, L13, L14
        rows.append(make_record(user, assistant,
                                category="layers", concept_id=cid,
                                faces=["math", "english"],
                                holdout=idx >= len(LAYERS) - 3))
    return rows


def tier_records() -> list[dict]:
    rows: list[dict] = []
    all_names = ", ".join(name for name, _, _ in RISK_TIERS)
    for idx, (name, meaning, code2) in enumerate(RISK_TIERS):
        cid = f"risk:{name}"
        user = f"Explain the risk tier set and define {name}."
        assistant = (
            f"set: {all_names}\n"
            f"focus: {name}\n"
            f"definition: {meaning}\n"
            f"binary: {name} -> {code2}\n"
            f"invariant: all four tiers are part of one governance decision box"
        )
        rows.append(make_record(user, assistant,
                                category="risk_tiers", concept_id=cid,
                                faces=["english", "binary"],
                                holdout=idx == 2))
    return rows


def axiom_records() -> list[dict]:
    rows: list[dict] = []
    for idx, (code, name, role, layers) in enumerate(AXIOMS):
        cid = f"axiom:{code}"
        user = f"Teach quantum axiom {code} ({name}) and which layers it governs."
        assistant = (
            f"axiom: {code}\n"
            f"name: {name}\n"
            f"role: {role}\n"
            f"layers: {layers}\n"
            f"invariant: {code} is enforced wherever {name} must hold"
        )
        # holdout the last axiom (A5 composition)
        rows.append(make_record(user, assistant,
                                category="axioms", concept_id=cid,
                                faces=["math", "english"],
                                holdout=idx == len(AXIOMS) - 1))
    return rows


def chemistry_records() -> list[dict]:
    rows: list[dict] = []
    for idx, (equation, stability, reaction_class, why, tongue) in enumerate(CHEMISTRY_CASES):
        cid = f"chem:{equation.replace(' ', '').replace('->', '_to_')}"
        user = f"Teach the chemistry packet for {equation}."
        assistant = (
            f"equation: {equation}\n"
            f"class: {reaction_class}\n"
            f"stability: {stability}\n"
            f"reason: {why}\n"
            f"tongue_face: {tongue}\n"
            f"invariant: equation atoms balance and lane is {tongue}"
        )
        rows.append(make_record(user, assistant,
                                category="chemistry", concept_id=cid,
                                faces=["math", "english", "chemistry", "sacred_tongues"],
                                holdout=idx % 3 == 2))
    return rows


def coding_records() -> list[dict]:
    rows: list[dict] = []
    for idx, (name, tongue, language, snippet, gloss) in enumerate(CODING_PRIMITIVES):
        cid = f"code:{name}"
        user = f"Teach the coding primitive {name} in its canonical Sacred Tongue lane."
        assistant = (
            f"primitive: {name}\n"
            f"tongue: {tongue}\n"
            f"language: {language}\n"
            f"snippet: {snippet}\n"
            f"english: {gloss}\n"
            f"invariant: tongue {tongue} routes {name} to {language}"
        )
        rows.append(make_record(user, assistant,
                                category="coding", concept_id=cid,
                                faces=["english", "sacred_tongues", "coding"],
                                holdout=idx % 4 == 3))
    return rows


def main() -> int:
    builders = {
        "alphabet": letter_records,
        "numbers": number_records,
        "tongues": tongue_records,
        "layers": layer_records,
        "risk_tiers": tier_records,
        "axioms": axiom_records,
        "chemistry": chemistry_records,
        "coding": coding_records,
    }

    all_rows: list[dict] = []
    category_counts: dict[str, int] = {}
    for cat, fn in builders.items():
        rows = fn()
        category_counts[cat] = len(rows)
        all_rows.extend(rows)

    train_rows = [row for row in all_rows if row["meta"]["split"] == "train"]
    holdout_rows = [row for row in all_rows if row["meta"]["split"] == "holdout"]

    SFT_ROOT.mkdir(parents=True, exist_ok=True)
    with TRAIN_OUT.open("w", encoding="utf-8") as handle:
        for row in train_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with EVAL_OUT.open("w", encoding="utf-8") as handle:
        for row in holdout_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    concept_ids = sorted({row["meta"]["concept_id"] for row in all_rows})
    face_index: dict[str, list[str]] = {}
    for row in all_rows:
        for face in row["meta"]["faces"]:
            face_index.setdefault(face, []).append(row["meta"]["concept_id"])

    manifest = {
        "schema_version": "aligned_foundations_manifest_v2",
        "train_file": str(TRAIN_OUT.relative_to(REPO_ROOT)).replace("\\", "/"),
        "eval_file": str(EVAL_OUT.relative_to(REPO_ROOT)).replace("\\", "/"),
        "counts": {
            "train": len(train_rows),
            "holdout": len(holdout_rows),
            "total": len(all_rows),
        },
        "categories": category_counts,
        "concept_id_count": len(concept_ids),
        "concept_ids": concept_ids,
        "face_index_counts": {face: len(ids) for face, ids in face_index.items()},
        "faces": sorted(face_index.keys()),
        "tongue_canonical_lang": {abbr: lang for abbr, _, _, lang in TONGUES},
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[aligned_foundations_v2] wrote {len(train_rows)} train -> {TRAIN_OUT}")
    print(f"[aligned_foundations_v2] wrote {len(holdout_rows)} holdout -> {EVAL_OUT}")
    print(f"[aligned_foundations_v2] manifest -> {MANIFEST_OUT}")
    print(f"[aligned_foundations_v2] {len(concept_ids)} concept_ids across {len(face_index)} faces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
