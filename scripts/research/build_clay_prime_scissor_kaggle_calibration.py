"""Build the private, calibration-only Kaggle packet for prime-scissor input.

The packet contains the three immutable frozen parents, exact source/runtime
dependencies, and the sealed preregistration/preflight authorities.  It does
not contain a material-training entry point.  Building this packet never
uploads it and never starts Kaggle or a Clay horse.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping
import zipfile

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.research.build_clay_frozen_multiview_kaggle_packet import (
    LOOM_FILES,
    canonical_json,
    copy_exact,
    descriptor,
    deterministic_zip,
    load_json,
    sha256_file,
    write_json,
)

PACKET_SCHEMA = "clay.prime-scissor-input-kaggle-calibration-packet.v1"
DESCRIPTOR_SCHEMA = "clay.prime-scissor-input-kaggle-calibration-dataset.v1"
BUILD_SCHEMA = "clay.prime-scissor-input-kaggle-calibration-build.v1"
KERNEL_AUTHORITY_SCHEMA = "clay.prime-scissor-input-kaggle-calibration-kernel-authority.v1"
EXPECTED_BASELINE_SCHEMA = "clay.frozen-multiview-adapter-campaign.v1.manifest"
EXPECTED_DATASET_MANIFEST_SHA256 = "7460665cbb718097438227c452f1915e88bdc5a10ac643122b17908b505d0041"
EXPECTED_BASELINE_MANIFEST_SHA256 = "7f2516af8ae5a122f357565afad60ab412fdf54e76a3018cd8f1ddbfdb702a97"
EXPECTED_BASELINE_RESULT_SHA256 = "c5261ada862a2851db0b1dd7e53835b5ddef22299660921527a249a866361482"
EXPECTED_PARENT_SHA256 = {
    20261134: "e719ca2398f0a96e4c80d2119897ad36202fb34bd8fbe37190655d581411b910",
    20261135: "bb4d912d413dd76174986a89b24f713268e90138808b69107aac01736c218438",
    20261136: "820f0ed122b27261eb91391d4b69efe987f2e8a8e5f79b27c9e2a7f431267929",
}
EXPECTED_PARENT_RESULT_SHA256 = {
    20261134: "08fc1d8ae8ca46fa2802db66150716b49a69aa0db9d709b5b24940058c68fbf4",
    20261135: "3293b973243f43cc0bf0b100412f806ecb5b3693a1886c4739cf907036ed6ee8",
    20261136: "811eecc628af67e27ef7ca83def7dfe7096d7ee0e21a826a0c89dbd632b2f652",
}
EXPECTED_PREREGISTRATION_SHA256 = "bd277d1c3218fca6a520e393b6ea99a5efc6e2d1d7c89a45b2b12563d66555ab"
EXPECTED_PREFLIGHT_SHA256 = "7d1732045829534170d75923af14a9fde44c569be06980d54b0a5b3aecd5889a"
FROZEN_ARTIFACT_AUTHORITY = "data/clay_prime_scissor_input_20261118/prime_scissor_inputs.pack"
EXPECTED_FROZEN_ARTIFACT_SHA256 = "8cf629170554970ec6541d0a129c48d64e3e38925ae318eb0cd5e8a860492dd4"
EXPECTED_FROZEN_ARTIFACT_BYTES = 905_507
EXPECTED_MATH_COMMIT = "0a5a06bed57e922f7e9ca04229664266aa8d215c"
EXPECTED_SEEDS = (20261134, 20261135, 20261136)
FULL_SCBE_INIT_SOURCE = "python/scbe/__init__.py"
GENERATED_SCBE_INIT_TARGET = "payload/scbe_repo/python/scbe/__init__.py"
MINIMAL_SCBE_RUNTIME_INIT = '''"""Generated package marker for the sealed Clay calibration runtime.

The full application initializer is retained as source authority outside the
runtime import path.  Calibration modules import their dependencies directly.
"""

__all__ = ()
'''
ISOLATED_REPLAY_BOOTSTRAP = (
    "import runpy,sys;"
    "roots=sys.argv[1:5];"
    "forbidden=sys.argv[5].casefold();"
    "script=sys.argv[6];"
    "args=sys.argv[7:];"
    "sys.path[:0]=roots;"
    "assert all(forbidden not in str(item).casefold() for item in sys.path);"
    "sys.argv=[script,*args];"
    "runpy.run_path(script,run_name='__main__')"
)
EMBEDDED_KERNEL_AUTHORITY_SENTINEL = "EMBEDDED_KERNEL_AUTHORITY_JSON: str | None = None"
KAGGLE_CODE_FILE_ONLY_BOOTSTRAP = r"""
import importlib.util
import json
from pathlib import Path
import sys

script = Path(sys.argv[1]).resolve(strict=True)
input_root = Path(sys.argv[2]).resolve(strict=True)
runtime_root = Path(sys.argv[3])
spec = importlib.util.spec_from_file_location("kaggle_code_file_only", script)
if spec is None or spec.loader is None:
    raise RuntimeError("could not import generated Kaggle code_file")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
authority_path = script.with_name("KERNEL_PACKET_AUTHORITY.json")
if authority_path.exists():
    raise RuntimeError("code-file-only preflight unexpectedly has a sibling authority")
dataset_id, authority = module.resolve_dataset_authority(authority_path, None)
descriptor_path, descriptor = module.discover_packet(input_root, dataset_id)
module.verify_kernel_authority(
    authority_path,
    descriptor_path,
    descriptor,
    authority=authority,
)
_, manifest = module.extract_and_verify_packet(
    descriptor_path,
    descriptor,
    runtime_root,
)
print(
    json.dumps(
        {
            "status": "PASS_CODE_FILE_ONLY_AUTHORITY_AND_DATASET_DISCOVERY",
            "dataset_id": dataset_id,
            "packet_id": manifest["packet_id"],
            "authority_source": "EMBEDDED_CANONICAL_JSON",
            "sibling_authority_present": False,
            "material_training": "NONE",
        },
        sort_keys=True,
    )
)
"""


def kernel_title_for_id(kernel_id: str) -> str:
    """Return a title whose provider-cleaned slug is exactly the pinned kernel slug."""

    owner, separator, slug = kernel_id.partition("/")
    if not separator or not owner or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError(f"kernel id must contain a clean lowercase provider slug: {kernel_id}")
    return slug


def kaggle_kernel_metadata(
    *,
    kernel_id: str,
    kernel_entry_name: str,
    dataset_id: str,
) -> dict[str, object]:
    return {
        "id": kernel_id,
        "title": kernel_title_for_id(kernel_id),
        "code_file": kernel_entry_name,
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": False,
        "dataset_sources": [dataset_id],
        "competition_sources": [],
        "kernel_sources": [],
    }


def render_kaggle_kernel_entry(
    source: Path,
    target: Path,
    authority: Mapping[str, Any],
) -> None:
    """Render one Kaggle-uploadable code file with an exact embedded authority."""

    text = source.resolve(strict=True).read_text(encoding="utf-8")
    if text.count(EMBEDDED_KERNEL_AUTHORITY_SENTINEL) != 1:
        raise RuntimeError("kernel entry has no unique embedded-authority sentinel")
    canonical_authority = canonical_json(authority)
    rendered = text.replace(
        EMBEDDED_KERNEL_AUTHORITY_SENTINEL,
        f"EMBEDDED_KERNEL_AUTHORITY_JSON: str | None = {canonical_authority!r}",
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8", newline="\n")
    if EMBEDDED_KERNEL_AUTHORITY_SENTINEL in target.read_text(encoding="utf-8"):
        raise RuntimeError("generated Kaggle entry retained the null authority sentinel")


RUNTIME_MODULES = (
    "python/__init__.py",
    "python/scbe/clay_prime_scissor_input.py",
    "python/scbe/clay_prime_scissor_input_campaign.py",
    "python/scbe/clay_frozen_multiview_adapter.py",
    "python/scbe/clay_frozen_multiview_data.py",
    "python/scbe/clay_paired_orbit_training.py",
    "python/scbe/concept_exposure_ledger.py",
    "python/scbe/atomic_tokenization.py",
    "python/scbe/bit_spine.py",
    "python/scbe/ca_opcode_table.py",
    "python/scbe/ca_semantics.py",
    "python/scbe/chemical_fusion.py",
    "python/scbe/chemistry_dimensions.py",
    "python/scbe/instrument.py",
    "python/scbe/reaction_balance.py",
    "python/scbe/reaction_state.py",
    "python/scbe/tongue_isa.py",
    "python/scbe/turing_rubix.py",
)
MATH_MODULES = (
    "__init__.py",
    "prime_lane_scissors.py",
    "universal_cycle_curriculum.py",
    "universal_prime_scissors.py",
)
AUTHORITY_DOCS = (
    "docs/research/CLAY_PRIME_SCISSOR_INPUT_PREREGISTRATION_20261118.md",
    "docs/research/CLAY_PRIME_SCISSOR_INPUT_PREFLIGHT_20261118.json",
    "docs/research/CLAY_PRIME_SCISSOR_INPUT_SYSTEM_MAP_20261118.md",
    "docs/research/CLAY_PRIME_SCISSOR_FROZEN_AUTHORITY_20261118.json",
    "docs/research/evidence/clay_prime_scissor_authority_20261118/failed_threads2_export.transcript.txt",
    "docs/research/evidence/clay_prime_scissor_authority_20261118/successful_threads6_export.transcript.txt",
)


@dataclass(frozen=True, slots=True)
class FileSpec:
    source: Path
    target: str
    role: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def git_value(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def require_clean_commit(root: Path) -> str:
    if git_value(root, "status", "--porcelain"):
        raise RuntimeError(f"packet source worktree is not clean: {root}")
    commit = git_value(root, "rev-parse", "HEAD")
    if len(commit) != 40:
        raise RuntimeError(f"invalid source commit: {commit}")
    return commit


def _add(specs: list[FileSpec], source: Path, target: str, role: str) -> None:
    source = source.resolve(strict=True)
    if not source.is_file():
        raise FileNotFoundError(source)
    if target.startswith("/") or ".." in Path(target).parts or "\\" in target:
        raise ValueError(f"unsafe packet target: {target}")
    specs.append(FileSpec(source, target, role))


def _require_hash(path: Path, expected: str, *, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected.casefold():
        raise RuntimeError(f"{label} hash differs: expected {expected}, got {actual}: {path}")


def _parent_rows(result: Mapping[str, Any]) -> dict[int, Mapping[str, Any]]:
    rows = result.get("parents")
    if not isinstance(rows, list):
        raise TypeError("baseline result has no parent rows")
    by_seed = {int(row["seed"]): row for row in rows if isinstance(row, Mapping)}
    if tuple(sorted(by_seed)) != EXPECTED_SEEDS:
        raise RuntimeError(f"baseline parent seeds differ: {sorted(by_seed)}")
    return by_seed


def collect_specs(
    *,
    worktree: Path,
    baseline_run: Path,
    source_root: Path,
    math_root: Path,
    kernel_entry: Path,
) -> tuple[list[FileSpec], dict[str, Any]]:
    """Collect and validate the deliberately compact calibration authority."""

    worktree = worktree.resolve(strict=True)
    baseline_run = baseline_run.resolve(strict=True)
    source_root = source_root.resolve(strict=True)
    math_root = math_root.resolve(strict=True)
    kernel_entry = kernel_entry.resolve(strict=True)
    implementation_commit = require_clean_commit(worktree)
    math_commit = require_clean_commit(math_root)
    if math_commit != EXPECTED_MATH_COMMIT:
        raise RuntimeError(f"clay-math commit differs: expected {EXPECTED_MATH_COMMIT}, got {math_commit}")

    baseline_manifest_path = baseline_run / "RUN_MANIFEST.json"
    baseline_result_path = baseline_run / "RESULT.json"
    _require_hash(
        baseline_manifest_path,
        EXPECTED_BASELINE_MANIFEST_SHA256,
        label="baseline run manifest",
    )
    _require_hash(
        baseline_result_path,
        EXPECTED_BASELINE_RESULT_SHA256,
        label="baseline aggregate result",
    )
    baseline_manifest = load_json(baseline_manifest_path)
    baseline_result = load_json(baseline_result_path)
    _require_hash(
        worktree / "docs" / "research" / "CLAY_PRIME_SCISSOR_INPUT_PREREGISTRATION_20261118.md",
        EXPECTED_PREREGISTRATION_SHA256,
        label="sealed preregistration",
    )
    _require_hash(
        worktree / "docs" / "research" / "CLAY_PRIME_SCISSOR_INPUT_PREFLIGHT_20261118.json",
        EXPECTED_PREFLIGHT_SHA256,
        label="sealed preflight",
    )
    frozen_authority = worktree / FROZEN_ARTIFACT_AUTHORITY
    _require_hash(
        frozen_authority,
        EXPECTED_FROZEN_ARTIFACT_SHA256,
        label="frozen feature/binding authority",
    )
    if frozen_authority.stat().st_size != EXPECTED_FROZEN_ARTIFACT_BYTES:
        raise RuntimeError(
            "frozen feature/binding authority size differs: "
            f"expected {EXPECTED_FROZEN_ARTIFACT_BYTES}, "
            f"got {frozen_authority.stat().st_size}"
        )
    if baseline_manifest.get("schema") != EXPECTED_BASELINE_SCHEMA:
        raise RuntimeError("baseline manifest schema differs")
    config = baseline_manifest.get("config")
    if not isinstance(config, Mapping):
        raise TypeError("baseline config is not an object")
    if tuple(int(seed) for seed in config.get("seeds", ())) != EXPECTED_SEEDS:
        raise RuntimeError("baseline seed set differs")
    if int(config.get("grow_steps", -1)) != 18_000:
        raise RuntimeError("baseline growth budget differs")
    if int(config.get("batch_size", -1)) != 128:
        raise RuntimeError("baseline batch size differs")
    if config.get("dataset_manifest_sha256") != EXPECTED_DATASET_MANIFEST_SHA256:
        raise RuntimeError("baseline dataset identity differs")

    source_dir = source_root / "experiments" / "clay_action_compiler_20261109"
    expected_source_hashes = config.get("source_hashes")
    if not isinstance(expected_source_hashes, Mapping):
        raise TypeError("baseline source hashes are missing")
    source_hash_files = {
        "policy": "trit_compiled_action_policy.py",
        "topology": "topology_sector_action_ab.py",
        "sandbox": "developmental_game_sandbox.py",
        "regional": "regional_breathing_field.py",
    }
    for key, filename in source_hash_files.items():
        _require_hash(
            source_dir / filename,
            str(expected_source_hashes[key]),
            label=f"baseline source {key}",
        )

    parent_rows = _parent_rows(baseline_result)
    specs: list[FileSpec] = []
    _add(
        specs,
        baseline_manifest_path,
        "payload/baseline/RUN_MANIFEST.json",
        "baseline_manifest",
    )
    _add(
        specs,
        baseline_result_path,
        "payload/baseline/RESULT.json",
        "baseline_result",
    )
    for seed in EXPECTED_SEEDS:
        parent = baseline_run / "parents" / f"seed-{seed}"
        parent_result = load_json(parent / "RESULT.json")
        recorded_hash = str(parent_rows[seed]["parent_sha256"])
        if recorded_hash != EXPECTED_PARENT_SHA256[seed]:
            raise RuntimeError(f"pinned parent hash differs for seed {seed}")
        _require_hash(
            parent / "RESULT.json",
            EXPECTED_PARENT_RESULT_SHA256[seed],
            label=f"parent result {seed}",
        )
        if str(parent_result.get("parent_sha256")) != recorded_hash:
            raise RuntimeError(f"parent result authority differs for seed {seed}")
        _require_hash(parent / "PARENT.pt", recorded_hash, label=f"parent {seed}")
        _add(
            specs,
            parent / "PARENT.pt",
            f"payload/baseline/parents/seed-{seed}/PARENT.pt",
            "frozen_parent",
        )
        _add(
            specs,
            parent / "RESULT.json",
            f"payload/baseline/parents/seed-{seed}/RESULT.json",
            "parent_result",
        )

    for relative in RUNTIME_MODULES:
        _add(
            specs,
            worktree / relative,
            f"payload/scbe_repo/{relative}",
            "experiment_runtime",
        )
    _add(
        specs,
        worktree / FULL_SCBE_INIT_SOURCE,
        f"authorities/full_source/{FULL_SCBE_INIT_SOURCE}",
        "full_source_package_authority_not_runtime",
    )
    for relative in AUTHORITY_DOCS:
        _add(
            specs,
            worktree / relative,
            f"payload/scbe_repo/{relative}",
            "sealed_authority",
        )
    _add(
        specs,
        frozen_authority,
        "payload/frozen_artifacts/prime_scissor_inputs.pack",
        "exact_frozen_feature_and_binding_artifacts",
    )
    for relative in LOOM_FILES:
        _add(
            specs,
            source_root / relative,
            f"payload/loom_root/{relative}",
            "source_dependency",
        )
    package_root = math_root / "clay-math" / "clay_math"
    for filename in MATH_MODULES:
        _add(
            specs,
            package_root / filename,
            f"payload/clay_math_root/clay_math/{filename}",
            "clay_math_0a5a06b",
        )
    _add(
        specs,
        kernel_entry,
        f"authorities/{kernel_entry.name}",
        "calibration_only_entrypoint",
    )
    targets = [spec.target for spec in specs]
    if len(targets) != len(set(targets)):
        raise RuntimeError("packet target paths are not unique")
    runtime_source_authority_sha256 = {
        relative: sha256_file(worktree / relative) for relative in sorted((FULL_SCBE_INIT_SOURCE, *RUNTIME_MODULES))
    }
    minimal_runtime_stub = MINIMAL_SCBE_RUNTIME_INIT.encode("utf-8")
    facts = {
        "implementation_commit": implementation_commit,
        "clay_math_commit": math_commit,
        "baseline_manifest_sha256": sha256_file(baseline_manifest_path),
        "baseline_result_sha256": sha256_file(baseline_result_path),
        "dataset_manifest_sha256": EXPECTED_DATASET_MANIFEST_SHA256,
        "seeds": list(EXPECTED_SEEDS),
        "source_hashes": dict(sorted(expected_source_hashes.items())),
        "runtime_source_authority_sha256": runtime_source_authority_sha256,
        "generated_runtime_stub": {
            "path": GENERATED_SCBE_INIT_TARGET,
            "bytes": len(minimal_runtime_stub),
            "sha256": sha256(minimal_runtime_stub).hexdigest(),
            "replaces_source_sha256": runtime_source_authority_sha256[FULL_SCBE_INIT_SOURCE],
            "imports": [],
        },
        "frozen_artifact_pack_sha256": EXPECTED_FROZEN_ARTIFACT_SHA256,
        "frozen_artifact_pack_bytes": EXPECTED_FROZEN_ARTIFACT_BYTES,
        "frozen_artifact_authority_mode": ("COMMITTED_RELEASE_COPY_AND_VERIFY_NO_REGENERATION"),
    }
    return specs, facts


def _packet_files(packet_root: Path, roles: Mapping[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(item for item in packet_root.rglob("*") if item.is_file()):
        relative = path.relative_to(packet_root).as_posix()
        if relative == "PACKET_MANIFEST.json":
            continue
        row = descriptor(path, relative_to=packet_root)
        row["role"] = roles[relative]
        rows.append(row)
    return rows


def _verify_frozen_artifacts(
    *,
    worktree: Path,
    baseline_run: Path,
    source_root: Path,
    math_root: Path,
    artifact: Path,
) -> Path:
    artifact = artifact.resolve(strict=True)
    _require_hash(
        artifact,
        EXPECTED_FROZEN_ARTIFACT_SHA256,
        label="packet frozen feature/binding authority",
    )
    verification_output = artifact.parent / "verification-output-must-stay-absent"
    command = [
        sys.executable,
        "-X",
        "utf8",
        str(worktree / "python" / "scbe" / "clay_prime_scissor_input_campaign.py"),
        "--baseline-run",
        str(baseline_run),
        "--output-dir",
        str(verification_output),
        "--preregistration",
        str(worktree / "docs" / "research" / "CLAY_PRIME_SCISSOR_INPUT_PREREGISTRATION_20261118.md"),
        "--preflight-receipt",
        str(worktree / "docs" / "research" / "CLAY_PRIME_SCISSOR_INPUT_PREFLIGHT_20261118.json"),
        "--clay-math-root",
        str(math_root),
        "--source-dir",
        str(source_root / "experiments" / "clay_action_compiler_20261109"),
        "--device",
        "cpu",
        "--threads",
        "2",
        "--frozen-artifact-pack",
        str(artifact),
        "--verify-frozen-artifact-pack-only",
    ]
    environment = os.environ.copy()
    python_paths = [
        worktree,
        worktree / "python",
        math_root / "clay-math",
        source_root,
    ]
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(path) for path in python_paths] + ([environment["PYTHONPATH"]] if environment.get("PYTHONPATH") else [])
    )
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "committed frozen artifact verification failed without starting calibration: "
            f"returncode={result.returncode}, stderr={result.stderr[-4000:]}"
        )
    status = json.loads(result.stdout)
    if status.get("status") != "FROZEN_ARTIFACT_VERIFIED_NO_CALIBRATION_NO_HORSES":
        raise RuntimeError(f"unexpected frozen artifact verification status: {status}")
    if verification_output.exists():
        raise RuntimeError("frozen artifact verification unexpectedly wrote run artifacts")
    return artifact


def _extract_archive_for_isolated_replay(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive.resolve(strict=True)) as bundle:
        members = tuple(bundle.infolist())
        seen: set[str] = set()
        for member in members:
            name = member.filename
            relative = PurePosixPath(name)
            mode = (member.external_attr >> 16) & 0xFFFF
            if (
                not name
                or "\\" in name
                or "\x00" in name
                or relative.is_absolute()
                or ".." in relative.parts
                or not relative.parts
            ):
                raise ValueError(f"unsafe isolated-replay archive member: {name}")
            if name in seen:
                raise RuntimeError(f"duplicate isolated-replay archive member: {name}")
            seen.add(name)
            if stat.S_ISLNK(mode):
                raise ValueError(f"isolated-replay archive symlink is forbidden: {name}")
            if member.flag_bits & 0x1:
                raise ValueError(f"isolated-replay encrypted archive member is forbidden: {name}")
        bundle.extractall(destination, members)


def verify_extracted_archive_isolated(
    archive: Path,
    *,
    worktree: Path,
    isolation_parent: Path | None = None,
) -> dict[str, Any]:
    """Run the no-training frozen-pack verifier from only the extracted archive."""

    archive = archive.resolve(strict=True)
    worktree = worktree.resolve(strict=True)
    temporary_parent = None if isolation_parent is None else str(isolation_parent.resolve(strict=True))
    with tempfile.TemporaryDirectory(
        prefix="clay-prime-scissor-isolated-replay-",
        dir=temporary_parent,
    ) as temporary:
        extracted = Path(temporary).resolve()
        _extract_archive_for_isolated_replay(archive, extracted)
        repo = extracted / "payload" / "scbe_repo"
        roots = (
            repo,
            repo / "python",
            extracted / "payload" / "clay_math_root",
            extracted / "payload" / "loom_root",
        )
        script = repo / "python" / "scbe" / "clay_prime_scissor_input_campaign.py"
        verification_output = extracted / "verification-output-must-stay-absent"
        command = [
            sys.executable,
            "-I",
            "-X",
            "utf8",
            "-c",
            ISOLATED_REPLAY_BOOTSTRAP,
            *(str(root) for root in roots),
            str(worktree),
            str(script),
            "--baseline-run",
            str(extracted / "payload" / "baseline"),
            "--output-dir",
            str(verification_output),
            "--preregistration",
            str(repo / "docs" / "research" / "CLAY_PRIME_SCISSOR_INPUT_PREREGISTRATION_20261118.md"),
            "--preflight-receipt",
            str(repo / "docs" / "research" / "CLAY_PRIME_SCISSOR_INPUT_PREFLIGHT_20261118.json"),
            "--clay-math-root",
            str(extracted / "payload" / "clay_math_root"),
            "--source-dir",
            str(extracted / "payload" / "loom_root" / "experiments" / "clay_action_compiler_20261109"),
            "--device",
            "cpu",
            "--threads",
            "2",
            "--frozen-artifact-pack",
            str(extracted / "payload" / "frozen_artifacts" / "prime_scissor_inputs.pack"),
            "--verify-frozen-artifact-pack-only",
        ]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(str(root) for root in roots)
        environment["PYTHONNOUSERSITE"] = "1"
        environment["CLAY_FORBIDDEN_WORKTREE"] = str(worktree)
        environment["GIT_CEILING_DIRECTORIES"] = str(extracted.parent)
        git_parent_probe = subprocess.run(
            ["git", "-C", str(extracted), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
            cwd=extracted,
            env=environment,
        )
        if git_parent_probe.returncode == 0:
            raise RuntimeError(
                "isolated extracted archive discovered a host Git worktree: " f"{git_parent_probe.stdout.strip()}"
            )
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=extracted,
            env=environment,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "isolated extracted-archive verification failed before calibration: "
                f"returncode={result.returncode}, stdout={result.stdout[-2000:]}, "
                f"stderr={result.stderr[-4000:]}"
            )
        status = json.loads(result.stdout)
        if status.get("status") != "FROZEN_ARTIFACT_VERIFIED_NO_CALIBRATION_NO_HORSES":
            raise RuntimeError(f"unexpected isolated archive status: {status}")
        if verification_output.exists():
            raise RuntimeError("isolated archive verification wrote run artifacts")
    return {
        "schema": f"{BUILD_SCHEMA}.isolated-archive-replay.v1",
        "status": "PASS_FROZEN_ARTIFACT_VERIFIED_NO_CALIBRATION_NO_HORSES",
        "archive_sha256": sha256_file(archive),
        "returncode": 0,
        "python_isolated_mode": True,
        "cwd_from_extracted_archive": True,
        "pythonpath_from_extracted_archive_only": True,
        "worktree_absent_from_subprocess_sys_path": True,
        "git_parent_discovery_blocked": True,
        "git_parent_probe_returncode": int(git_parent_probe.returncode),
        "verification_output_created": False,
        "material_training": "NONE",
    }


def verify_kaggle_code_file_only(
    kernel_entry: Path,
    dataset_dir: Path,
    *,
    expected_dataset_id: str,
    expected_packet_id: str,
) -> dict[str, Any]:
    """Replay Kaggle's script upload shape: one code file plus an input mount."""

    kernel_entry = kernel_entry.resolve(strict=True)
    dataset_dir = dataset_dir.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="clay-prime-scissor-kaggle-code-only-") as temporary:
        root = Path(temporary).resolve()
        src = root / "src"
        input_mount = root / "input" / "clay-prime-scissor-calibration"
        runtime = root / "runtime"
        script = src / "script.py"
        copy_exact(kernel_entry, script)
        for source in sorted(path for path in dataset_dir.iterdir() if path.is_file()):
            copy_exact(source, input_mount / source.name)
        sibling_authority = src / "KERNEL_PACKET_AUTHORITY.json"
        if sibling_authority.exists():
            raise RuntimeError("Kaggle code-file-only preflight copied a sibling authority")
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-X",
                "utf8",
                "-c",
                KAGGLE_CODE_FILE_ONLY_BOOTSTRAP,
                str(script),
                str(root / "input"),
                str(runtime),
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=src,
            env={**os.environ, "PYTHONNOUSERSITE": "1"},
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Kaggle code-file-only authority/discovery preflight failed: "
                f"returncode={result.returncode}, stdout={result.stdout[-2000:]}, "
                f"stderr={result.stderr[-4000:]}"
            )
        status = json.loads(result.stdout)
        if status.get("status") != "PASS_CODE_FILE_ONLY_AUTHORITY_AND_DATASET_DISCOVERY":
            raise RuntimeError(f"unexpected Kaggle code-file-only status: {status}")
        if status.get("dataset_id") != expected_dataset_id:
            raise RuntimeError("Kaggle code-file-only dataset identity differs")
        if status.get("packet_id") != expected_packet_id:
            raise RuntimeError("Kaggle code-file-only packet identity differs")
    return {
        "schema": f"{BUILD_SCHEMA}.kaggle-code-file-only-preflight.v1",
        **status,
        "returncode": 0,
        "python_isolated_mode": True,
        "code_file_count": 1,
        "dataset_source_attached": True,
        "packet_archive_verified": True,
        "calibration_started": False,
        "quota_spent": False,
    }


def build_packet(
    *,
    worktree: Path,
    baseline_run: Path,
    source_root: Path,
    math_root: Path,
    output_parent: Path,
    dataset_id: str,
    kernel_id: str,
    kernel_entry: Path,
) -> dict[str, Any]:
    output_parent = output_parent.resolve()
    specs, facts = collect_specs(
        worktree=worktree,
        baseline_run=baseline_run,
        source_root=source_root,
        math_root=math_root,
        kernel_entry=kernel_entry,
    )
    with tempfile.TemporaryDirectory(prefix="clay-prime-scissor-calibration-") as temporary:
        packet_root = Path(temporary) / "packet"
        packet_root.mkdir()
        roles: dict[str, str] = {}
        for spec in specs:
            target = packet_root / Path(*spec.target.split("/"))
            copy_exact(spec.source, target)
            roles[spec.target] = spec.role
        runtime_stub = packet_root / Path(*GENERATED_SCBE_INIT_TARGET.split("/"))
        if runtime_stub.exists():
            raise RuntimeError("generated runtime package stub target is already occupied")
        runtime_stub.parent.mkdir(parents=True, exist_ok=True)
        runtime_stub.write_text(
            MINIMAL_SCBE_RUNTIME_INIT,
            encoding="utf-8",
            newline="\n",
        )
        roles[GENERATED_SCBE_INIT_TARGET] = "generated_minimal_runtime_package_stub"
        stub_fact = facts["generated_runtime_stub"]
        if runtime_stub.stat().st_size != int(stub_fact["bytes"]) or sha256_file(runtime_stub) != stub_fact["sha256"]:
            raise RuntimeError("generated runtime package stub differs from sealed facts")
        artifact = _verify_frozen_artifacts(
            worktree=worktree.resolve(strict=True),
            baseline_run=baseline_run.resolve(strict=True),
            source_root=source_root.resolve(strict=True),
            math_root=math_root.resolve(strict=True),
            artifact=(packet_root / "payload" / "frozen_artifacts" / "prime_scissor_inputs.pack"),
        )
        files = _packet_files(packet_root, roles)
        body: dict[str, Any] = {
            "schema": PACKET_SCHEMA,
            "authority": {
                "calibration": "TIMING_ONLY",
                "material_training": "NONE",
                "horse_creation": "NONE",
                "upload": "NONE",
                "promotion": "NONE",
            },
            "claim_boundary": (
                "Exact-device timing calibration only. No horse, checkpoint, "
                "model, material-training, upload, or promotion authority."
            ),
            "dataset_id": dataset_id,
            "kernel_id": kernel_id,
            "facts": facts,
            "fixed_run_contract": {
                "calibration_only": True,
                "device": "cuda",
                "batch_size": 128,
                "grow_steps_per_horse": 18_000,
                "checkpoint_every": 500,
                "learning_rate": 0.002,
                "threads": 2,
                "minimum_free_gib": 25.0,
                "internet": False,
                "gpu": True,
                "frozen_artifact_pack_sha256": sha256_file(artifact),
            },
            "files": files,
            "file_count": len(files),
            "payload_bytes": sum(int(row["bytes"]) for row in files),
        }
        packet_id = stable_hash(body)
        manifest = {
            **body,
            "packet_id": packet_id,
            "manifest_body_sha256": packet_id,
            "self_hash_rule": (
                "SHA256(canonical JSON after removing packet_id, " "manifest_body_sha256, and self_hash_rule)"
            ),
        }
        write_json(packet_root / "PACKET_MANIFEST.json", manifest)

        output_root = output_parent / f"clay-prime-scissor-calibration-{packet_id[:16]}"
        if output_root.exists():
            raise FileExistsError(f"content-addressed output already exists: {output_root}")
        dataset_dir = output_root / "dataset"
        kernel_dir = output_root / "kernel"
        dataset_dir.mkdir(parents=True)
        kernel_dir.mkdir()
        archive = dataset_dir / f"clay-prime-scissor-calibration-{packet_id[:16]}.packet"
        deterministic_zip(packet_root, archive)
        isolated_archive_replay = verify_extracted_archive_isolated(
            archive,
            worktree=worktree,
        )
        packet_descriptor = {
            "schema": DESCRIPTOR_SCHEMA,
            "dataset_id": dataset_id,
            "packet_id": packet_id,
            "archive": descriptor(archive),
            "packet_manifest": descriptor(packet_root / "PACKET_MANIFEST.json"),
            "authority": manifest["authority"],
        }
        write_json(dataset_dir / "PACKET_DESCRIPTOR.json", packet_descriptor)
        write_json(
            dataset_dir / "dataset-metadata.json",
            {
                "title": kernel_title_for_id(dataset_id),
                "id": dataset_id,
                "licenses": [{"name": "other"}],
            },
        )
        kernel_authority = {
            "schema": KERNEL_AUTHORITY_SCHEMA,
            "dataset_id": dataset_id,
            "packet_id": packet_id,
            "packet_descriptor": descriptor(dataset_dir / "PACKET_DESCRIPTOR.json"),
            "archive": packet_descriptor["archive"],
            "packet_manifest": packet_descriptor["packet_manifest"],
        }
        write_json(
            kernel_dir / "KERNEL_PACKET_AUTHORITY.json",
            kernel_authority,
        )
        render_kaggle_kernel_entry(
            kernel_entry.resolve(strict=True),
            kernel_dir / kernel_entry.name,
            kernel_authority,
        )
        write_json(
            kernel_dir / "kernel-metadata.json",
            kaggle_kernel_metadata(
                kernel_id=kernel_id,
                kernel_entry_name=kernel_entry.name,
                dataset_id=dataset_id,
            ),
        )
        kaggle_code_file_only_preflight = verify_kaggle_code_file_only(
            kernel_dir / kernel_entry.name,
            dataset_dir,
            expected_dataset_id=dataset_id,
            expected_packet_id=packet_id,
        )
        launch_plan = {
            "schema": f"{BUILD_SCHEMA}.launch-plan",
            "status": "READY_NOT_UPLOADED_NOT_RUN",
            "dataset_id": dataset_id,
            "kernel_id": kernel_id,
            "internet": False,
            "gpu": True,
            "entry_mode": "CALIBRATION_ONLY",
            "kernel_authority_mode": "EMBEDDED_CANONICAL_JSON_WITH_LOCAL_AUDIT_COPY",
            "fixed_budget": {
                "batch_size": 128,
                "grow_steps_per_horse": 18_000,
                "minimum_free_gib": 25.0,
                "projected_campaign_gate_hours_with_margin": 24.0,
            },
            "commands": {
                "version_private_dataset": (
                    f'kaggle datasets version -p "{dataset_dir}" ' f'-m "Calibration packet {packet_id}" --dir-mode zip'
                ),
                "push_private_gpu_kernel": f'kaggle kernels push -p "{kernel_dir}"',
            },
            "expected_outputs": [
                "/kaggle/working/clay-prime-scissor-calibration/ENVIRONMENT_RECEIPT.json",
                "/kaggle/working/clay-prime-scissor-calibration/LAUNCH_RECEIPT.json",
                "/kaggle/working/clay-prime-scissor-calibration/TIMING_CALIBRATION.json",
                "/kaggle/working/clay-prime-scissor-calibration/RECOVERY_RECEIPT.json",
            ],
            "forbidden_outputs": ["horses/", "checkpoints/", "*.pt", "*.pth"],
            "authority": {
                "upload": "REQUIRES_SEPARATE_USER_ACTION",
                "run": "REQUIRES_SEPARATE_USER_ACTION",
                "material_training": "NONE",
            },
        }
        write_json(output_root / "PRIVATE_KAGGLE_LAUNCH_PLAN.json", launch_plan)

    receipt = {
        "schema": BUILD_SCHEMA,
        "status": "BUILT_PRIVATE_OFFLINE_NOT_UPLOADED_NOT_RUN",
        "created_at_utc": utc_now(),
        "packet_id": packet_id,
        "output_root": str(output_root),
        "implementation_commit": facts["implementation_commit"],
        "clay_math_commit": facts["clay_math_commit"],
        "packet_payload_bytes": int(manifest["payload_bytes"]),
        "packet_file_count": int(manifest["file_count"]),
        "archive": descriptor(archive, relative_to=output_root),
        "dataset_descriptor": descriptor(dataset_dir / "PACKET_DESCRIPTOR.json", relative_to=output_root),
        "kernel_entry": descriptor(kernel_dir / kernel_entry.name, relative_to=output_root),
        "kernel_packet_authority": descriptor(kernel_dir / "KERNEL_PACKET_AUTHORITY.json", relative_to=output_root),
        "launch_plan": descriptor(output_root / "PRIVATE_KAGGLE_LAUNCH_PLAN.json", relative_to=output_root),
        "isolated_archive_replay": isolated_archive_replay,
        "kaggle_code_file_only_preflight": kaggle_code_file_only_preflight,
        "authority": {
            "calibration": "TIMING_ONLY",
            "material_training": "NONE",
            "upload": "NONE",
            "run": "NONE",
        },
    }
    write_json(output_root / "BUILD_RECEIPT.json", receipt)
    return receipt


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--baseline-run", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--math-root", type=Path, required=True)
    parser.add_argument("--output-parent", type=Path, required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--kernel-id", required=True)
    parser.add_argument(
        "--kernel-entry",
        type=Path,
        default=Path(__file__).with_name("run_clay_prime_scissor_kaggle_calibration.py"),
    )
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    args = parse_args(arguments)
    receipt = build_packet(**vars(args))
    print(canonical_json(receipt), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
