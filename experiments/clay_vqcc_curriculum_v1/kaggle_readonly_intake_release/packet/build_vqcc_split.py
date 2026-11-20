"""Build a deterministic, source-family-disjoint VQCC train/holdout split.

The published corpus intentionally keeps all public VQCC material in its train
split.  This tool derives a *campaign-local* evaluation split without changing
the corpus.  It reconstructs fine-grained provenance from the corpus catalog
and refuses rows whose family cannot be established from stable fields.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping


SCHEMA = "clay.vqcc-source-family-split.v1"
VQCC_OWNED_LANES = {
    "owned.experimental_method",
    "owned.public_notebook_observation",
}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pair_record_id(source: str, lane: str, ordinal: Any) -> str:
    """Reproduce ``Records.pair`` identity from the v2 corpus builder."""

    return sha256_bytes(canonical_bytes([source, lane, ordinal]))


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"Expected object in {path.name}:{number}")
            yield value


def iter_train_rows(paths: Iterable[Path]) -> Iterator[dict[str, Any]]:
    for path in paths:
        for row in iter_jsonl(path):
            if row.get("split") != "train":
                raise ValueError(f"Non-train row in {path.name}: {row.get('record_id')}")
            yield row


def is_vqcc_row(row: Mapping[str, Any]) -> bool:
    lane = str(row.get("lane", ""))
    return lane.startswith("public.") or lane in VQCC_OWNED_LANES


def source_ref(manifest: Mapping[str, Any], key: str) -> str:
    value = manifest.get("public_sources", {}).get(key)
    if not isinstance(value, list) or not value or not isinstance(value[0], str):
        raise ValueError(f"Corpus manifest lacks public source pin {key!r}")
    return value[0]


@dataclass(frozen=True)
class CorpusLayout:
    train_paths: tuple[Path, ...]
    source_catalog: Path
    block_index: Path
    circuit_sequences: Path
    verified_files: Mapping[str, str]


def validate_corpus_files(root: Path, manifest: Mapping[str, Any]) -> CorpusLayout:
    if manifest.get("schema") != "clay.vqcc-research-corpus.v1":
        raise ValueError(f"Unexpected corpus manifest schema: {manifest.get('schema')!r}")
    counts = manifest.get("counts")
    if not isinstance(counts, dict) or not isinstance(counts.get("train"), int) or counts["train"] <= 0:
        raise ValueError("Corpus manifest has invalid train count")
    for name in ("holdout", "ordinary", "retention"):
        if not isinstance(counts.get(name), int) or counts[name] < 0:
            raise ValueError(f"Corpus manifest has invalid {name} count")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("Corpus manifest files table is missing")
    declared_train = sorted(
        name
        for name in files
        if isinstance(name, str) and name.startswith("train-") and name.endswith(".jsonl")
    )
    if not declared_train:
        raise ValueError("Corpus manifest declares no train shards")
    actual_train = sorted(path.name for path in root.glob("train-*.jsonl"))
    unlisted = sorted(set(actual_train) - set(declared_train))
    if unlisted:
        raise ValueError(f"Unlisted train shards present: {unlisted}")
    required = ["source-catalog.jsonl", "block-index.jsonl", "circuit-sequences.jsonl", *declared_train]
    verified: dict[str, str] = {}
    for name in required:
        if Path(name).name != name:
            raise ValueError(f"Unsafe corpus filename: {name!r}")
        spec = files.get(name)
        if not isinstance(spec, dict):
            raise ValueError(f"Corpus manifest does not declare required file {name}")
        size, expected_sha = spec.get("bytes"), spec.get("sha256")
        if not isinstance(size, int) or size < 0 or not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise ValueError(f"Invalid file receipt for {name}")
        path = root / name
        if not path.is_file() or path.stat().st_size != size:
            raise ValueError(f"Corpus file size differs for {name}")
        actual_sha = sha256_file(path)
        if actual_sha != expected_sha:
            raise ValueError(f"Corpus file hash differs for {name}")
        verified[name] = actual_sha
    return CorpusLayout(
        train_paths=tuple(root / name for name in declared_train),
        source_catalog=root / "source-catalog.jsonl",
        block_index=root / "block-index.jsonl",
        circuit_sequences=root / "circuit-sequences.jsonl",
        verified_files=verified,
    )


def reverify_consumed_files(layout: CorpusLayout) -> None:
    root = layout.source_catalog.parent
    for name, expected_sha in layout.verified_files.items():
        if sha256_file(root / name) != expected_sha:
            raise ValueError(f"Consumed corpus file changed during split build: {name}")


@dataclass(frozen=True)
class FamilyInfo:
    family: str
    tasks: tuple[str, ...] = ()


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        parent = self.parent.setdefault(item, item)
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            low, high = sorted((a, b))
            self.parent[high] = low


class FamilyResolver:
    """Resolve row IDs to the finest family supported by corpus provenance."""

    def __init__(self, root: Path, manifest: Mapping[str, Any], layout: CorpusLayout) -> None:
        self.root = root
        self.manifest = manifest
        self.layout = layout
        self.by_record_id: dict[str, FamilyInfo] = {}
        self._circuit_tasks: dict[str, str] = {}
        self._block_info: dict[str, FamilyInfo] = {}
        self._negative_info: dict[str, FamilyInfo] = {}
        self._load_circuit_tasks()
        self._load_block_components()
        self._load_negative_components()
        self._load_catalog_mappings()
        self._load_block_mappings()

    def _add(self, record_id: str, family: str, tasks: Iterable[str] = ()) -> None:
        clean_tasks = tuple(sorted({str(task) for task in tasks if str(task)}))
        value = FamilyInfo(family=family, tasks=clean_tasks)
        previous = self.by_record_id.setdefault(record_id, value)
        if previous != value:
            raise ValueError(f"Conflicting family mapping for {record_id}")

    def _load_circuit_tasks(self) -> None:
        for item in iter_jsonl(self.layout.source_catalog):
            if item.get("type") != "public_circuit":
                continue
            row = item.get("record", {})
            sha = str(row.get("sha256") or row.get("sha") or row.get("sha12") or "")
            task = str(row.get("task") or "")
            if sha and task:
                self._circuit_tasks[sha[:12]] = task

    def _load_block_components(self) -> None:
        block_sha: dict[int, str] = {}
        for row in iter_jsonl(self.layout.block_index):
            block_sha[int(row["block_id"])] = str(row["sha256"])
        union = _UnionFind()
        task_by_node: dict[str, set[str]] = collections.defaultdict(set)
        for sequence in iter_jsonl(self.layout.circuit_sequences):
            task = str(sequence.get("task") or "unknown")
            published_entry = str(sequence.get("published_entry") or "")
            if not published_entry:
                raise ValueError("Circuit sequence lacks published_entry")
            entry_node = f"entry:{published_entry}"
            union.find(entry_node)
            task_by_node[entry_node].add(task)
            for block_id in sequence.get("blocks", []):
                sha = block_sha.get(int(block_id))
                if sha is None:
                    raise ValueError(f"Circuit references unknown block {block_id}")
                block_node = f"block:{sha}"
                union.union(entry_node, block_node)
                task_by_node[block_node].add(task)
        components: dict[str, dict[str, set[str]]] = collections.defaultdict(
            lambda: {"entries": set(), "blocks": set(), "tasks": set()}
        )
        for node in union.parent:
            root = union.find(node)
            if node.startswith("entry:"):
                components[root]["entries"].add(node.removeprefix("entry:"))
            else:
                components[root]["blocks"].add(node.removeprefix("block:"))
            components[root]["tasks"].update(task_by_node[node])
        for component in components.values():
            descriptor = {
                "entries": sorted(component["entries"]),
                "blocks": sorted(component["blocks"]),
            }
            identity = sha256_bytes(canonical_bytes(descriptor))
            info = FamilyInfo(
                family=f"opcode-component:sha256:{identity}",
                tasks=tuple(sorted(component["tasks"])),
            )
            for sha in component["blocks"]:
                self._block_info[sha] = info
        missing = sorted(set(block_sha.values()) - set(self._block_info))
        if missing:
            raise ValueError(f"Opcode blocks are not referenced by published entries: {missing[:3]}")

    def _load_negative_components(self) -> None:
        """Connect findings through exact source, target, or supersession identity."""

        union = _UnionFind()
        tasks_by_item: dict[str, str] = {}
        item_ids: set[str] = set()
        for item in iter_jsonl(self.layout.source_catalog):
            if item.get("type") != "negative":
                continue
            row = item.get("record", {})
            item_id = str(row.get("id") or "").strip()
            if not item_id:
                continue
            if item_id in item_ids:
                raise ValueError(f"Repeated negative-result ID: {item_id}")
            item_ids.add(item_id)
            item_node = f"item:{item_id}"
            union.find(item_node)
            tasks_by_item[item_id] = str(row.get("task") or "unknown")
            for field, prefix in (
                ("link", "link"),
                ("family_target", "family_target"),
            ):
                value = str(row.get(field) or "").strip()
                if value:
                    union.union(item_node, f"{prefix}:{value}")
            supersedes = str(row.get("supersedes") or "")
            for other_id in supersedes.replace(",", ";").split(";"):
                other_id = other_id.strip()
                if other_id:
                    union.union(item_node, f"item:{other_id}")

        components: dict[str, dict[str, set[str]]] = collections.defaultdict(
            lambda: {"items": set(), "nodes": set(), "tasks": set()}
        )
        for node in union.parent:
            root = union.find(node)
            components[root]["nodes"].add(node)
            if node.startswith("item:"):
                item_id = node.removeprefix("item:")
                if item_id in item_ids:
                    components[root]["items"].add(item_id)
                    components[root]["tasks"].add(tasks_by_item[item_id])
        for component in components.values():
            if not component["items"]:
                continue
            identity = sha256_bytes(canonical_bytes(sorted(component["nodes"])))
            info = FamilyInfo(
                family=f"experiment-component:sha256:{identity}",
                tasks=tuple(sorted(component["tasks"])),
            )
            for item_id in component["items"]:
                self._negative_info[item_id] = info
        missing = sorted(item_ids - set(self._negative_info))
        if missing:
            raise ValueError(f"Negative-result families were not resolved: {missing[:3]}")

    @staticmethod
    def _best_catalog_family(prefix: str, row: Mapping[str, Any], fallback: str) -> str:
        for key in (
            "circuit_sha256",
            "submission_sha256",
            "source_sha256",
            "circuit_id",
            "portfolio",
            "family",
        ):
            value = row.get(key)
            if value not in (None, ""):
                return f"{prefix}:{key}:{value}"
        return f"{prefix}:{fallback}"

    def _load_catalog_mappings(self) -> None:
        library = source_ref(self.manifest, "library")
        parts = source_ref(self.manifest, "parts")
        negative = source_ref(self.manifest, "negative")
        region_ordinals: collections.Counter[str] = collections.Counter()
        for item in iter_jsonl(self.layout.source_catalog):
            kind = item.get("type")
            if kind == "public_region":
                circuit = str(item["circuit_sha256"])
                ordinal = region_ordinals[circuit]
                region_ordinals[circuit] += 1
                task = self._circuit_tasks.get(circuit[:12], "unknown")
                family = f"circuit:sha256:{circuit}"
                extent = pair_record_id(library, "public.region_extent", [circuit, ordinal])
                self._add(extent, family, (task,))
                metrics = item.get("metrics", {})
                toffoli = metrics.get("toffoli") if isinstance(metrics, dict) else None
                conditional = metrics.get("conditional_toffoli") if isinstance(metrics, dict) else None
                if isinstance(toffoli, int) and isinstance(conditional, int) and 0 <= conditional <= toffoli:
                    cost = pair_record_id(library, "public.region_cost", [circuit, ordinal])
                    self._add(cost, family, (task,))
            elif kind == "parts":
                row = item.get("record", {})
                start, end = str(row.get("op_start", "")), str(row.get("op_end", ""))
                module_id = str(row.get("module_id") or "")
                if module_id and start.isdecimal() and end.isdecimal():
                    record_id = pair_record_id(parts, "public.module_span", module_id)
                    family = self._best_catalog_family("module", row, module_id)
                    self._add(record_id, family, (str(row.get("task") or "unknown"),))
            elif kind == "negative":
                row = item.get("record", {})
                item_id = str(row.get("id") or "")
                if item_id and row.get("mechanism") and row.get("why_it_failed"):
                    record_id = pair_record_id(negative, "public.experimental_findings", item_id)
                    info = self._negative_info.get(item_id)
                    if info is None:
                        raise ValueError(f"Negative-result family is missing for {item_id}")
                    self._add(record_id, info.family, info.tasks)
            elif kind == "public_factorization_array":
                source = str(item.get("source") or "")
                array = str(item.get("array") or "")
                shape = item.get("shape")
                if source and array and isinstance(shape, list) and len(shape) > 1:
                    record_id = pair_record_id(library, "public.array_shape", [source, array])
                    self._add(record_id, f"factorization:{source}", ("chemistry",))

    def _load_block_mappings(self) -> None:
        for block_sha, info in self._block_info.items():
            record_id = pair_record_id(
                "public-vqcc-opcode-windows", "public.gate_count", block_sha
            )
            self._add(record_id, info.family, info.tasks)

    def resolve(self, row: Mapping[str, Any]) -> FamilyInfo:
        record_id = str(row.get("record_id") or "")
        mapped = self.by_record_id.get(record_id)
        if mapped is not None:
            return mapped

        lane = str(row.get("lane") or "")
        source = str(row.get("source") or "")
        source_sha = str(row.get("source_sha256") or "")
        if lane.startswith("public.notebook_"):
            if source:
                return FamilyInfo(f"notebook:{source}", self._row_tasks(row))
        if source_sha:
            family = f"source-file:{source}:{source_sha}"
            return FamilyInfo(family, self._row_tasks(row))
        path = str(row.get("path") or "")
        if source and path:
            return FamilyInfo(f"source-path:{source}:{path}", self._row_tasks(row))
        group = str(row.get("split_group") or "")
        if group.startswith("owned-method-"):
            return FamilyInfo(f"owned-method:{group}", self._row_tasks(row))
        raise ValueError(
            f"Cannot establish fine source family for {record_id} lane={lane!r} group={group!r}"
        )

    @staticmethod
    def _row_tasks(row: Mapping[str, Any]) -> tuple[str, ...]:
        direct = str(row.get("task") or "")
        if direct in {"invsqrt", "dqi", "chemistry"}:
            return (direct,)
        path = str(row.get("path") or "")
        first = path.replace("\\", "/").split("/", 1)[0]
        return (first,) if first in {"invsqrt", "dqi", "chemistry"} else ()


@dataclass
class FamilyStats:
    rows: int = 0
    lanes: collections.Counter[str] = field(default_factory=collections.Counter)
    tasks: collections.Counter[str] = field(default_factory=collections.Counter)

    @property
    def dominant_lane(self) -> str:
        return self._dominant(self.lanes)

    @property
    def dominant_task(self) -> str:
        return self._dominant(self.tasks)

    @staticmethod
    def _dominant(counter: collections.Counter[str]) -> str:
        if not counter:
            return "unknown"
        return min(counter, key=lambda key: (-counter[key], key))


def deterministic_order(seed: str, family: str) -> str:
    return sha256_bytes(f"{seed}\0{family}".encode("utf-8"))


def assign_families(
    families: Mapping[str, FamilyStats], *, seed: str, holdout_fraction: float
) -> dict[str, str]:
    if not 0 < holdout_fraction < 1:
        raise ValueError("holdout_fraction must be strictly between zero and one")
    strata: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for family, stats in families.items():
        strata[(stats.dominant_lane, stats.dominant_task)].append(family)
    assignment = {family: "train" for family in families}
    for names in strata.values():
        if len(names) < 2:
            continue
        ordered = sorted(names, key=lambda name: (deterministic_order(seed, name), name))
        total = sum(families[name].rows for name in ordered)
        target = total * holdout_fraction
        cumulative = 0
        choices: list[tuple[float, int]] = []
        for index, name in enumerate(ordered[:-1], 1):
            cumulative += families[name].rows
            choices.append((abs(cumulative - target), index))
        _, count = min(choices)
        for name in ordered[:count]:
            assignment[name] = "holdout"
    return assignment


def _counter_tree() -> dict[str, collections.Counter[str]]:
    return {
        "lane": collections.Counter(),
        "task": collections.Counter(),
        "lane_task": collections.Counter(),
    }


def build_split(
    corpus_root: Path,
    output_dir: Path,
    *,
    expected_manifest_sha256: str,
    seed: str,
    holdout_fraction: float,
) -> dict[str, Any]:
    corpus_root = corpus_root.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(output_dir)
    manifest_path = corpus_root / "CORPUS_MANIFEST.json"
    actual_manifest_sha = sha256_file(manifest_path)
    if actual_manifest_sha != expected_manifest_sha256:
        raise ValueError(
            f"Corpus manifest hash differs: expected {expected_manifest_sha256}, got {actual_manifest_sha}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    layout = validate_corpus_files(corpus_root, manifest)
    resolver = FamilyResolver(corpus_root, manifest, layout)

    families: dict[str, FamilyStats] = {}
    seen_ids: set[str] = set()
    eligible_rows = 0
    corpus_train_rows = 0
    for row in iter_train_rows(layout.train_paths):
        corpus_train_rows += 1
        if not is_vqcc_row(row):
            continue
        record_id = str(row.get("record_id") or "")
        if not record_id or record_id in seen_ids:
            raise ValueError(f"Missing or repeated VQCC record ID: {record_id!r}")
        seen_ids.add(record_id)
        info = resolver.resolve(row)
        stats = families.setdefault(info.family, FamilyStats())
        stats.rows += 1
        lane = str(row["lane"])
        stats.lanes[lane] += 1
        tasks = info.tasks or ("unknown",)
        for task in tasks:
            stats.tasks[task] += 1
        eligible_rows += 1
    if corpus_train_rows != manifest["counts"]["train"]:
        raise ValueError(
            f"Corpus train count differs: manifest={manifest['counts']['train']} read={corpus_train_rows}"
        )
    if eligible_rows == 0 or len(families) < 2:
        raise ValueError("Need at least two resolved VQCC source families")

    family_split = assign_families(families, seed=seed, holdout_fraction=holdout_fraction)
    splits = set(family_split.values())
    if splits != {"train", "holdout"}:
        raise ValueError(f"Both split roles are required, got {sorted(splits)}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    prefix = f".{output_dir.name}.tmp-"
    staging = Path(tempfile.mkdtemp(prefix=prefix, dir=output_dir.parent)).resolve()
    try:
        family_path = staging / "family-assignments.jsonl"
        row_path = staging / "row-assignments.jsonl"
        balance = {"train": _counter_tree(), "holdout": _counter_tree()}
        with family_path.open("x", encoding="utf-8", newline="\n") as stream:
            for family in sorted(families):
                stats = families[family]
                stream.write(
                    canonical_bytes(
                        {
                            "family": family,
                            "split": family_split[family],
                            "rows": stats.rows,
                            "dominant_lane": stats.dominant_lane,
                            "dominant_task": stats.dominant_task,
                            "lanes": dict(sorted(stats.lanes.items())),
                            "tasks": dict(sorted(stats.tasks.items())),
                        }
                    ).decode("utf-8")
                )

        assigned_ids: set[str] = set()
        with row_path.open("x", encoding="utf-8", newline="\n") as stream:
            for row in iter_train_rows(layout.train_paths):
                if not is_vqcc_row(row):
                    continue
                info = resolver.resolve(row)
                role = family_split[info.family]
                record_id = str(row["record_id"])
                if record_id in assigned_ids:
                    raise ValueError(f"Repeated assignment: {record_id}")
                assigned_ids.add(record_id)
                tasks = info.tasks or ("unknown",)
                task_label = "+".join(tasks)
                lane = str(row["lane"])
                balance[role]["lane"][lane] += 1
                balance[role]["task"][task_label] += 1
                balance[role]["lane_task"][f"{lane}|{task_label}"] += 1
                stream.write(
                    canonical_bytes(
                        {
                            "record_id": record_id,
                            "split": role,
                            "family": info.family,
                            "lane": lane,
                            "task": task_label,
                        }
                    ).decode("utf-8")
                )
        if assigned_ids != seen_ids:
            raise RuntimeError("Second pass assignment differs from first pass")
        reverify_consumed_files(layout)

        serial_balance = {
            role: {name: dict(sorted(counter.items())) for name, counter in groups.items()}
            for role, groups in balance.items()
        }
        result: dict[str, Any] = {
            "schema": SCHEMA,
            "corpus": {
                "manifest_sha256": actual_manifest_sha,
                "manifest_schema": manifest.get("schema"),
                "declared_train_rows": manifest["counts"]["train"],
                "read_train_rows": corpus_train_rows,
                "verified_consumed_files": dict(sorted(layout.verified_files.items())),
                "unlisted_train_files": [],
            },
            "policy": {
                "seed": seed,
                "holdout_fraction": holdout_fraction,
                "unit": "source_family",
                "unresolved_rows": 0,
            },
            "counts": {
                "eligible_rows": eligible_rows,
                "families": len(families),
                "train_families": sum(value == "train" for value in family_split.values()),
                "holdout_families": sum(value == "holdout" for value in family_split.values()),
                "train_rows": sum(
                    stats.rows for family, stats in families.items() if family_split[family] == "train"
                ),
                "holdout_rows": sum(
                    stats.rows for family, stats in families.items() if family_split[family] == "holdout"
                ),
            },
            "balance": serial_balance,
            "artifacts": {
                family_path.name: sha256_file(family_path),
                row_path.name: sha256_file(row_path),
            },
            "invariants": {
                "record_ids_unique": len(assigned_ids) == eligible_rows,
                "families_cross_splits": 0,
                "consumed_files_manifest_verified": True,
                "corpus_unchanged": True,
            },
        }
        manifest_out = staging / "SPLIT_MANIFEST.json"
        with manifest_out.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
        staging.rename(output_dir)
        return result
    except BaseException:
        if staging.exists() and staging.parent == output_dir.parent and staging.name.startswith(prefix):
            shutil.rmtree(staging)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--seed", default="clay-vqcc-curriculum-v1")
    parser.add_argument("--holdout-fraction", type=float, default=0.2)
    args = parser.parse_args()
    result = build_split(
        args.corpus_root,
        args.output_dir,
        expected_manifest_sha256=args.expected_manifest_sha256,
        seed=args.seed,
        holdout_fraction=args.holdout_fraction,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
