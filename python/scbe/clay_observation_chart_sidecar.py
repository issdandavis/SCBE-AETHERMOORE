"""Default-off observation anchors for Clay's existing multi-view action data.

The sidecar keeps the canonical sampled state separate from every derived
feature view.  It is an audit/data-construction surface only: it does not alter
prompts, labels, model inputs, samplers, weights, or training configuration.
"""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import random
from typing import Any, Mapping, Protocol, Sequence

from torch import Tensor

from python.scbe.clay_frozen_multiview_data import feature_bytes

SCHEMA = "clay.observation-chart-sidecar.v1"
BINDING_SCHEMA = "clay.observation-chart-binding.v1"
VIEW_COUNT = 3
FEATURE_BYTES = 37 * 4
BINDING_MODES = ("authority", "rotated_control")


class ObservationSidecarError(ValueError):
    """Raised when an observation/chart sidecar violates its exact contract."""


class ObservationChartProvider(Protocol):
    """Read-only subset of the existing Clay source adapter."""

    source_hashes: Mapping[str, str]

    def training_sandboxes(self) -> tuple[Any, ...]: ...

    def sample_state(self, sandbox: Any, rng: random.Random) -> Any: ...

    def materialize(self, sandbox: Any, state: Any) -> tuple[Tensor, int, int]: ...


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_json(value: object) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_observation(state: Any) -> tuple[dict[str, Any], str]:
    recorder = getattr(state, "record", None)
    if not callable(recorder):
        raise ObservationSidecarError("sampled state has no canonical record()")
    record = recorder()
    if not isinstance(record, Mapping):
        raise ObservationSidecarError("canonical state record must be a mapping")
    # Round-trip through canonical JSON so the stored value is detached from the
    # source object and contains only the literal JSON observation.
    detached = json.loads(canonical_json(dict(record)))
    digest = sha256_json(detached)
    declared = getattr(state, "sha256", None)
    if declared is not None and str(declared).casefold() != digest:
        raise ObservationSidecarError("state.sha256 differs from state.record()")
    return detached, digest


def _sidecar_body(sidecar: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in sidecar.items() if key != "manifest_sha256"}


def verify_observation_chart_sidecar(sidecar: Mapping[str, Any]) -> bool:
    """Recompute every canonical observation and exact view payload hash."""

    try:
        if sidecar["schema"] != SCHEMA or int(sidecar["view_count"]) != VIEW_COUNT:
            return False
        if int(sidecar["feature_bytes_per_view"]) != FEATURE_BYTES:
            return False
        observations = sidecar["observations"]
        if not isinstance(observations, list) or not observations:
            return False
        if int(sidecar["observation_count"]) != len(observations):
            return False
        if not isinstance(sidecar["source_hashes"], dict):
            return False
        if sha256_json(_sidecar_body(sidecar)) != str(sidecar["manifest_sha256"]):
            return False
        for expected_index, observation in enumerate(observations):
            if int(observation["observation_index"]) != expected_index:
                return False
            record = observation["observation"]
            observation_sha256 = str(observation["observation_sha256"])
            if not isinstance(record, dict) or sha256_json(record) != observation_sha256:
                return False
            views = observation["views"]
            if not isinstance(views, list) or len(views) != VIEW_COUNT:
                return False
            if {int(view["view_id"]) for view in views} != set(range(VIEW_COUNT)):
                return False
            for view in views:
                if str(view["observation_sha256"]) != observation_sha256:
                    return False
                payload = bytes.fromhex(str(view["feature_bytes_hex"]))
                if len(payload) != FEATURE_BYTES:
                    return False
                if sha256(payload).hexdigest() != str(view["feature_sha256"]):
                    return False
                int(view["label"])
                int(view["sector"])
        return True
    except (KeyError, TypeError, ValueError):
        return False


def build_observation_chart_sidecar(
    provider: ObservationChartProvider,
    *,
    observation_count: int,
    seed: int,
) -> dict[str, Any]:
    """Capture literal states and all three derived charts without training."""

    if observation_count < 1:
        raise ObservationSidecarError("observation_count must be positive")
    sandboxes = provider.training_sandboxes()
    if len(sandboxes) != VIEW_COUNT:
        raise ObservationSidecarError("sidecar requires exactly three legal views")
    rng = random.Random(seed)
    observations: list[dict[str, Any]] = []
    for observation_index in range(observation_count):
        state = provider.sample_state(sandboxes[0], rng)
        record, observation_sha256 = _canonical_observation(state)
        views = []
        for view_id, sandbox in enumerate(sandboxes):
            feature, label, sector = provider.materialize(sandbox, state)
            payload = feature_bytes(feature)
            views.append(
                {
                    "view_id": view_id,
                    "observation_sha256": observation_sha256,
                    "feature_bytes_hex": payload.hex(),
                    "feature_sha256": sha256(payload).hexdigest(),
                    "label": int(label),
                    "sector": int(sector),
                }
            )
        observations.append(
            {
                "observation_index": observation_index,
                "observation": record,
                "observation_sha256": observation_sha256,
                "views": views,
            }
        )
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "seed": int(seed),
        "observation_count": len(observations),
        "view_count": VIEW_COUNT,
        "feature_bytes_per_view": FEATURE_BYTES,
        "source_hashes": dict(sorted(provider.source_hashes.items())),
        "observations": observations,
        "authority": "AUDIT_ONLY_NO_MODEL_INPUT_NO_TRAINING_NO_PROMOTION",
    }
    sidecar = {**body, "manifest_sha256": sha256_json(body)}
    if not verify_observation_chart_sidecar(sidecar):
        raise ObservationSidecarError("generated sidecar failed exact verification")
    return sidecar


def _binding_rows(sidecar: Mapping[str, Any], mode: str) -> list[dict[str, Any]]:
    observations = sidecar["observations"]
    if mode == "rotated_control" and len(observations) < 2:
        raise ObservationSidecarError("rotated control needs at least two observations")
    digests = [str(row["observation_sha256"]) for row in observations]
    if mode == "rotated_control" and len(digests) != len(set(digests)):
        raise ObservationSidecarError("rotated control requires distinct observations")
    rows = []
    for anchor_index, anchor in enumerate(observations):
        origin_index = anchor_index if mode == "authority" else (anchor_index + 1) % len(observations)
        origin = observations[origin_index]
        for view in origin["views"]:
            rows.append(
                {
                    "anchor_index": anchor_index,
                    "anchor_observation_sha256": anchor["observation_sha256"],
                    "view_origin_index": origin_index,
                    "view_observation_sha256": view["observation_sha256"],
                    "view_id": view["view_id"],
                    "feature_sha256": view["feature_sha256"],
                }
            )
    return rows


def build_binding_ledger(sidecar: Mapping[str, Any], *, mode: str) -> dict[str, Any]:
    """Bind exact views correctly or through a one-to-one rotated control."""

    if mode not in BINDING_MODES:
        raise ObservationSidecarError(f"unknown binding mode: {mode}")
    if not verify_observation_chart_sidecar(sidecar):
        raise ObservationSidecarError("cannot bind an invalid sidecar")
    body: dict[str, Any] = {
        "schema": BINDING_SCHEMA,
        "sidecar_manifest_sha256": sidecar["manifest_sha256"],
        "mode": mode,
        "rows": _binding_rows(sidecar, mode),
    }
    ledger = {**body, "ledger_sha256": sha256_json(body)}
    if not verify_binding_ledger(sidecar, ledger):
        raise ObservationSidecarError("generated binding ledger failed verification")
    return ledger


def verify_binding_ledger(sidecar: Mapping[str, Any], ledger: Mapping[str, Any]) -> bool:
    try:
        if not verify_observation_chart_sidecar(sidecar):
            return False
        if ledger["schema"] != BINDING_SCHEMA or ledger["mode"] not in BINDING_MODES:
            return False
        if ledger["sidecar_manifest_sha256"] != sidecar["manifest_sha256"]:
            return False
        body = {key: value for key, value in ledger.items() if key != "ledger_sha256"}
        if sha256_json(body) != ledger["ledger_sha256"]:
            return False
        return ledger["rows"] == _binding_rows(sidecar, str(ledger["mode"]))
    except (KeyError, TypeError, ValueError, ObservationSidecarError):
        return False


def write_sidecar_create_once(path: str | Path, sidecar: Mapping[str, Any]) -> Path:
    """Write an explicitly requested sidecar without overwriting prior evidence."""

    if not verify_observation_chart_sidecar(sidecar):
        raise ObservationSidecarError("refusing to write an invalid sidecar")
    output = Path(path).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite sidecar: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, output)
    return output


__all__: Sequence[str] = (
    "BINDING_MODES",
    "BINDING_SCHEMA",
    "ObservationSidecarError",
    "SCHEMA",
    "build_binding_ledger",
    "build_observation_chart_sidecar",
    "verify_binding_ledger",
    "verify_observation_chart_sidecar",
    "write_sidecar_create_once",
)
