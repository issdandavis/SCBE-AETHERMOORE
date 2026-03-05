from __future__ import annotations

import functools
import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for root in (REPO_ROOT, REPO_ROOT / "src"):
    if root.exists() and str(root) not in sys.path:
        sys.path.insert(0, str(root))

MODULE_CANDIDATES = (
    "sacred_eggs",
    "sacred_egg",
    "scbe_sacred_eggs",
    "scbe_eggs",
    "src.sacred_eggs",
    "src.sacred_egg",
    "src.scbe_sacred_eggs",
    "src.scbe_14layer_reference",
    "scbe_14layer_reference",
)

FILE_CANDIDATES = (
    REPO_ROOT / "src" / "sacred_eggs.py",
    REPO_ROOT / "src" / "sacred_egg.py",
    REPO_ROOT / "src" / "scbe_sacred_eggs.py",
    REPO_ROOT / "src" / "scbe_eggs.py",
    REPO_ROOT / "src" / "scbe_14layer_reference.py",
    REPO_ROOT / "sacred_eggs.py",
    REPO_ROOT / "sacred_egg.py",
)

INVOKE_ALIASES = ("invoke_ritual", "perform_ritual", "ritual_invoke", "invoke", "ritual")
INCUBATION_ALIASES = (
    "solitary_incubation",
    "begin_solitary_incubation",
    "incubate_solitary",
    "solitaryIncubation",
    "incubate",
)
TRIADIC_ALIASES = (
    "triadic_binding",
    "perform_triadic_binding",
    "triadic_bind",
    "bind_triad",
    "triad_bind",
    "triadicBinding",
)
MANIFOLD_BIND_ALIASES = (
    "manifold_binding",
    "bind_manifold",
    "bind_to_manifold",
    "manifold_bind",
    "lock_to_manifold",
    "attach_manifold",
)
MANIFOLD_RITUAL_ALIASES = MANIFOLD_BIND_ALIASES + TRIADIC_ALIASES
VERIFY_ALIASES = (
    "verify_binding",
    "verify_manifold_binding",
    "validate_manifold_binding",
    "validate_binding",
    "verify_seal",
    "unlock",
    "open",
    "reveal",
    "verify",
)
RING_DESCENT_ALIASES = (
    "ring_descent",
    "perform_ring_descent",
    "descend_ring",
    "ringDescent",
    "descent",
)
FAIL_TO_NOISE_ALIASES = (
    "fail_to_noise",
    "noise_failover",
    "zeroize_to_noise",
    "obscure_to_noise",
    "failToNoise",
)

PAYLOAD = b"SCBE::SacredEgg::payload"
TRIAD = ("guardian-alpha", "guardian-beta", "guardian-gamma")
SIX_GUARDIANS = (
    "guardian-alpha",
    "guardian-beta",
    "guardian-gamma",
    "guardian-delta",
    "guardian-epsilon",
    "guardian-zeta",
)

# Ordered manifold axes are assumed to be [X, Y, Z, V, P, S].
# Points are assumed to live in an open Poincare ball, so ||x|| < 1.
VALID_MANIFOLD = (0.12, -0.18, 0.11, 0.09, -0.07, 0.06)
PERTURBED_MANIFOLD = (0.12, -0.18, 0.11, 0.09, -0.07, 0.065)
PERMUTED_MANIFOLD = (0.11, 0.12, -0.18, 0.09, -0.07, 0.06)
DIM_MISMATCH_MANIFOLD = (0.12, -0.18, 0.11)
BOUNDARY_MANIFOLD = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
OUTSIDE_MANIFOLD = (1.01, 0.0, 0.0, 0.0, 0.0, 0.0)
NAN_MANIFOLD = (0.12, float("nan"), 0.11, 0.09, -0.07, 0.06)
INF_MANIFOLD = (0.12, float("inf"), 0.11, 0.09, -0.07, 0.06)

ALIASES = {
    "egg": {"egg", "sacred_egg", "container", "state", "instance", "obj"},
    "egg_id": {"egg_id", "id", "name", "label", "container_id"},
    "payload": {
        "payload",
        "secret",
        "data",
        "seed",
        "material",
        "blob",
        "plaintext",
        "message",
        "secret_payload",
    },
    "actor": {"actor", "invoker", "caller", "agent", "guardian", "binder", "participant"},
    "participants": {
        "participants",
        "binders",
        "agents",
        "guardians",
        "triad",
        "members",
        "signers",
        "attestors",
        "binder_ids",
        "guardian_ids",
    },
    "threshold": {"threshold", "quorum", "min_signers", "required_signers", "k"},
    "manifold": {
        "manifold",
        "coords",
        "coordinates",
        "point",
        "vector",
        "embedding",
        "location",
        "manifold_point",
        "bind_point",
    },
    "binding": {"binding", "token", "seal", "proof", "attestation", "digest", "handle", "lock"},
    "ritual": {"ritual", "ritual_name", "invocation", "action", "op", "mode", "name"},
    "ring": {"ring", "ring_level", "depth", "level", "ring_index", "realm"},
    "source_ring": {"source_ring", "from_ring", "current_ring", "src_ring", "ring_from"},
    "target_ring": {"target_ring", "to_ring", "next_ring", "dst_ring", "ring_to"},
}

GOOD_STATUS = {
    "ok",
    "success",
    "allowed",
    "allow",
    "accepted",
    "bound",
    "sealed",
    "verified",
    "complete",
    "completed",
    "pass",
    "passed",
    "true",
}
BAD_STATUS = {
    "error",
    "errors",
    "fail",
    "failed",
    "deny",
    "denied",
    "reject",
    "rejected",
    "quarantine",
    "invalid",
    "unauthorized",
    "unknown",
    "false",
}

MISSING = object()


def _norm_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


GOOD_STATUS_N = {_norm_name(x) for x in GOOD_STATUS}
BAD_STATUS_N = {_norm_name(x) for x in BAD_STATUS}


def _import_file(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(f"_pytest_autoload_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to build import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.lru_cache(maxsize=1)
def _load_sacred_eggs_module() -> Any:
    errors: list[str] = []

    for name in MODULE_CANDIDATES:
        try:
            return importlib.import_module(name)
        except Exception as exc:  # pragma: no cover
            errors.append(f"{name}: {exc.__class__.__name__}")

    for path in FILE_CANDIDATES:
        if not path.exists():
            continue
        try:
            return _import_file(path)
        except Exception as exc:  # pragma: no cover
            errors.append(f"{path}: {exc.__class__.__name__}")

    tried = ", ".join(MODULE_CANDIDATES)
    details = "; ".join(errors[:8])
    raise LookupError(
        "Could not locate a Sacred Eggs implementation module. "
        f"Tried imports [{tried}] and common file locations. "
        f"First failures: {details}"
    )


def _status_to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        norm = _norm_name(value)
        if norm in GOOD_STATUS_N:
            return True
        if norm in BAD_STATUS_N:
            return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    return None


def _resolve_param_value(param_name: str, context: dict[str, Any]) -> Any:
    lname = param_name.lower()

    if lname in context:
        return context[lname]

    for canonical, aliases in ALIASES.items():
        if lname == canonical or lname in aliases:
            if canonical in context:
                return context[canonical]

    for canonical, aliases in ALIASES.items():
        if canonical not in context:
            continue
        for alias in aliases:
            if lname.startswith(f"{alias}_") or lname.endswith(f"_{alias}"):
                return context[canonical]

    return MISSING


def _call_with_context(fn: Any, **context: Any) -> Any:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):  # pragma: no cover
        return fn()

    kwargs: dict[str, Any] = {}
    accepts_kwargs = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )

    for param in sig.parameters.values():
        if param.name in {"self", "cls"}:
            continue
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            continue

        value = _resolve_param_value(param.name, context)
        if value is not MISSING:
            kwargs[param.name] = value
            continue

        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue

        if param.default is inspect._empty:
            raise LookupError(f"Cannot satisfy required parameter '{param.name}' for {fn!r}")

    if accepts_kwargs:
        for canonical, value in context.items():
            if value is not None:
                kwargs.setdefault(canonical, value)

    return fn(**kwargs)


def _find_callable(targets: tuple[Any, ...], aliases: tuple[str, ...]) -> Any | None:
    wanted = [_norm_name(alias) for alias in aliases]

    for target in targets:
        callables: dict[str, Any] = {}
        for name in dir(target):
            if name.startswith("_"):
                continue
            try:
                attr = getattr(target, name)
            except Exception:  # pragma: no cover
                continue
            if callable(attr):
                callables[name] = attr

        for want in wanted:
            for name, attr in callables.items():
                if _norm_name(name) == want:
                    return attr

        for want in wanted:
            for name, attr in callables.items():
                normalized = _norm_name(name)
                if want in normalized or normalized in want:
                    return attr

    return None


def _is_success(result: Any) -> bool:
    status = _status_to_bool(result)
    if status is not None:
        return status

    if result is None:
        return True

    if isinstance(result, dict):
        for key in ("ok", "success", "allowed", "bound", "sealed", "verified", "accepted"):
            if key in result:
                status = _status_to_bool(result[key])
                return bool(result[key]) if status is None else status
        if "status" in result:
            status = _status_to_bool(result["status"])
            if status is not None:
                return status
        return True

    for attr in ("ok", "success", "allowed", "bound", "sealed", "verified", "accepted"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            status = _status_to_bool(value)
            return bool(value) if status is None else status

    if hasattr(result, "status"):
        status = _status_to_bool(getattr(result, "status"))
        if status is not None:
            return status

    return True


def _has_explicit_status(result: Any) -> bool:
    if isinstance(result, dict):
        return any(
            key in result
            for key in ("ok", "success", "allowed", "bound", "sealed", "verified", "accepted", "status")
        )
    return any(
        hasattr(result, attr)
        for attr in ("ok", "success", "allowed", "bound", "sealed", "verified", "accepted", "status")
    )


def _binding_fingerprint(result: Any) -> Any:
    if isinstance(result, (str, bytes, bytearray, memoryview, int, float, bool)) or result is None:
        return result

    if isinstance(result, dict):
        for key in ("binding", "digest", "seal", "token", "proof", "fingerprint", "id", "handle", "lock"):
            if key in result:
                return result[key]
        return repr(sorted(result.items()))

    for attr in ("binding", "digest", "seal", "token", "proof", "fingerprint", "id", "handle", "lock"):
        if hasattr(result, attr):
            return getattr(result, attr)

    return repr(result)


def assert_rejected(invocation) -> None:
    try:
        result = invocation()
    except Exception:
        return
    assert not _is_success(result), f"Expected rejection, got success-like result: {result!r}"


def assert_no_payload_leak(value: Any, payload: bytes = PAYLOAD) -> None:
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        assert raw != payload, "raw payload leaked directly"
        assert payload not in raw, "payload bytes leaked inside noise output"

    if isinstance(value, dict):
        for inner in value.values():
            assert_no_payload_leak(inner, payload)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for inner in value:
            assert_no_payload_leak(inner, payload)

    text = repr(value)
    decoded = payload.decode("utf-8", errors="ignore")
    assert payload.hex() not in text, "payload hex leaked through repr/exception text"
    if decoded:
        assert decoded not in text, "payload text leaked through repr/exception text"


class SacredEggAPI:
    FACTORY_NAMES = (
        "SacredEgg",
        "SacredEggContainer",
        "SacredEggs",
        "EggContainer",
        "Egg",
        "create_sacred_egg",
        "new_sacred_egg",
        "make_sacred_egg",
        "build_sacred_egg",
    )

    def __init__(self, module: Any) -> None:
        self.module = module
        self.instance = self._make_instance()

    @property
    def targets(self) -> tuple[Any, ...]:
        return tuple(target for target in (self.instance, self.module) if target is not None)

    def available(self) -> list[str]:
        names: set[str] = set()
        for target in self.targets:
            for name in dir(target):
                if name.startswith("_"):
                    continue
                try:
                    attr = getattr(target, name)
                except Exception:
                    continue
                if callable(attr):
                    names.add(name)
        return sorted(names)

    def _make_instance(self) -> Any | None:
        for name in self.FACTORY_NAMES:
            candidate = getattr(self.module, name, None)
            if not callable(candidate):
                continue
            try:
                return _call_with_context(
                    candidate,
                    payload=PAYLOAD,
                    egg_id="pytest-sacred-egg",
                    manifold=VALID_MANIFOLD,
                    participants=TRIAD,
                    threshold=3,
                )
            except Exception:
                continue
        return None

    def find(self, aliases: tuple[str, ...]) -> Any | None:
        return _find_callable(self.targets, aliases)

    def call(self, fn: Any, **context: Any) -> Any:
        context.setdefault("egg", self.instance)
        return _call_with_context(fn, **context)

    def ritual(self, ritual_name: str, aliases: tuple[str, ...], **context: Any) -> Any:
        fn = self.find(aliases)
        if fn is not None:
            try:
                return self.call(fn, ritual=ritual_name, **context)
            except LookupError:
                pass

        invoker = self.find(INVOKE_ALIASES)
        if invoker is None:
            pytest.skip(
                f"No callable found for ritual '{ritual_name}'. "
                f"Discovered callables: {', '.join(self.available()) or '<none>'}"
            )
        return self.call(invoker, ritual=ritual_name, **context)

    def verify(self, binding: Any, **context: Any) -> Any | None:
        verifier = self.find(VERIFY_ALIASES)
        if verifier is None:
            return None
        return self.call(verifier, binding=binding, **context)


@pytest.fixture()
def egg_api() -> SacredEggAPI:
    try:
        module = _load_sacred_eggs_module()
    except LookupError as exc:
        pytest.skip(str(exc))

    api = SacredEggAPI(module)
    if not any(
        api.find(group) is not None
        for group in (
            INVOKE_ALIASES,
            INCUBATION_ALIASES,
            TRIADIC_ALIASES,
            MANIFOLD_RITUAL_ALIASES,
            RING_DESCENT_ALIASES,
            FAIL_TO_NOISE_ALIASES,
        )
    ):
        pytest.skip(
            "Loaded a module but did not discover Sacred Eggs entry points. "
            f"Callables found: {', '.join(api.available()) or '<none>'}"
        )
    return api


def test_unknown_ritual_name_is_rejected(egg_api: SacredEggAPI) -> None:
    invoker = egg_api.find(INVOKE_ALIASES)
    if invoker is None:
        pytest.skip("Generic ritual invoker is not exposed by this implementation")

    assert_rejected(
        lambda: egg_api.call(
            invoker,
            ritual="__not_a_real_sacred_ritual__",
            actor=TRIAD[0],
            participants=(TRIAD[0],),
            payload=PAYLOAD,
            manifold=VALID_MANIFOLD,
        )
    )


def test_solitary_incubation_accepts_one_invoker(egg_api: SacredEggAPI) -> None:
    result = egg_api.ritual(
        "solitary_incubation",
        INCUBATION_ALIASES,
        actor=TRIAD[0],
        participants=(TRIAD[0],),
        payload=PAYLOAD,
    )
    assert _is_success(result), f"solitary incubation unexpectedly failed: {result!r}"


@pytest.mark.parametrize(
    "participants",
    [
        ("guardian-alpha", "guardian-beta"),
        ("guardian-alpha", "guardian-alpha", "guardian-beta"),
    ],
)
def test_triadic_binding_rejects_insufficient_or_non_distinct_binders(
    egg_api: SacredEggAPI, participants: tuple[str, ...]
) -> None:
    assert_rejected(
        lambda: egg_api.ritual(
            "triadic_binding",
            TRIADIC_ALIASES,
            participants=participants,
            threshold=3,
            payload=PAYLOAD,
            manifold=VALID_MANIFOLD,
        )
    )


def test_triadic_binding_accepts_three_of_six_distinct_guardians(egg_api: SacredEggAPI) -> None:
    result = egg_api.ritual(
        "triadic_binding",
        TRIADIC_ALIASES,
        participants=SIX_GUARDIANS[:3],
        threshold=3,
        payload=PAYLOAD,
        manifold=VALID_MANIFOLD,
    )
    assert _is_success(result), f"3-of-6 triadic binding should succeed, got {result!r}"


def test_ring_descent_rejects_negative_target_ring(egg_api: SacredEggAPI) -> None:
    assert_rejected(
        lambda: egg_api.ritual(
            "ring_descent",
            RING_DESCENT_ALIASES,
            actor=TRIAD[0],
            payload=PAYLOAD,
            ring=-1,
            source_ring=0,
            target_ring=-1,
        )
    )


@pytest.mark.parametrize(
    "manifold",
    [
        DIM_MISMATCH_MANIFOLD,
        BOUNDARY_MANIFOLD,
        OUTSIDE_MANIFOLD,
        NAN_MANIFOLD,
        INF_MANIFOLD,
    ],
)
def test_manifold_binding_rejects_invalid_points(
    egg_api: SacredEggAPI, manifold: tuple[float, ...]
) -> None:
    assert_rejected(
        lambda: egg_api.ritual(
            "manifold_binding",
            MANIFOLD_RITUAL_ALIASES,
            participants=TRIAD,
            threshold=3,
            payload=PAYLOAD,
            manifold=manifold,
        )
    )


@pytest.mark.parametrize("wrong_manifold", [PERTURBED_MANIFOLD, PERMUTED_MANIFOLD])
def test_manifold_binding_breaks_on_coordinate_change(
    egg_api: SacredEggAPI, wrong_manifold: tuple[float, ...]
) -> None:
    binding = egg_api.ritual(
        "manifold_binding",
        MANIFOLD_RITUAL_ALIASES,
        participants=TRIAD,
        threshold=3,
        payload=PAYLOAD,
        manifold=VALID_MANIFOLD,
    )
    assert _is_success(binding), f"valid manifold binding failed: {binding!r}"

    verified = egg_api.verify(
        binding,
        participants=TRIAD,
        threshold=3,
        payload=PAYLOAD,
        manifold=VALID_MANIFOLD,
    )
    if verified is not None:
        assert _is_success(verified), f"binding did not verify at original manifold: {verified!r}"
        assert_rejected(
            lambda: egg_api.verify(
                binding,
                participants=TRIAD,
                threshold=3,
                payload=PAYLOAD,
                manifold=wrong_manifold,
            )
        )
        return

    rebound = egg_api.ritual(
        "manifold_binding",
        MANIFOLD_RITUAL_ALIASES,
        participants=TRIAD,
        threshold=3,
        payload=PAYLOAD,
        manifold=wrong_manifold,
    )
    assert _is_success(rebound), f"rebind on changed manifold unexpectedly failed: {rebound!r}"

    fp_a = _binding_fingerprint(binding)
    fp_b = _binding_fingerprint(rebound)
    if fp_a in (True, False, None) or fp_b in (True, False, None):
        pytest.skip(
            "Need either a verify/open API or a structured binding token "
            "to prove coordinate sensitivity for this implementation"
        )
    assert fp_a != fp_b, "changing manifold coordinates should change the binding token/fingerprint"


def test_fail_to_noise_never_leaks_raw_payload(egg_api: SacredEggAPI) -> None:
    fail_fn = egg_api.find(FAIL_TO_NOISE_ALIASES)

    if fail_fn is not None:
        result = egg_api.call(
            fail_fn,
            actor=TRIAD[0],
            participants=("guardian-alpha", "guardian-alpha", "guardian-beta"),
            payload=PAYLOAD,
            manifold=OUTSIDE_MANIFOLD,
        )
        assert_no_payload_leak(result, PAYLOAD)
        return

    # Fallback: force a known-invalid binding path and ensure the surfaced error/result
    # still does not contain the underlying secret material.
    try:
        result = egg_api.ritual(
            "manifold_binding",
            MANIFOLD_RITUAL_ALIASES,
            participants=("guardian-alpha", "guardian-alpha", "guardian-beta"),
            threshold=3,
            payload=PAYLOAD,
            manifold=OUTSIDE_MANIFOLD,
        )
    except Exception as exc:
        assert_no_payload_leak(exc, PAYLOAD)
        return

    assert_no_payload_leak(result, PAYLOAD)
    if _has_explicit_status(result):
        assert not _is_success(result), (
            "Invalid manifold + duplicate binders should not surface a success status; "
            f"got {result!r}"
        )
