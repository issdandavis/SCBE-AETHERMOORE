"""Exact EOT token lattices and bounded composite token-path races.

The immutable root alphabet is the 256 bytes. ``EOT_SYMBOL`` is a boundary
operator outside that alphabet. Multiple token tables share trie nodes while
retaining independent probability measures. An edge is both an auditable
topology function and a table-specific conditional probability.

Composing conditional functions along ``token_bytes + EOT`` reconstructs the
normalized aggregate teacher mass of that byte path. A race can begin at any
live trie node, but it covers one next-token distribution only. After EOT, a
caller must evaluate a new distribution for autoregressive continuation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence

EOT_LATTICE_SCHEMA = "scbe.interwoven-eot-token-lattice.v1"
EOT_RACE_SCHEMA = "scbe.composite-token-path-race.v1"
EOT_SYMBOL = 256
BYTE_ALPHABET_SIZE = 256
PROBABILITY_TOLERANCE = 1e-9
RECONSTRUCTION_TOLERANCE = 1e-12
FOLD_RELATIVE_TOLERANCE = 1e-12

MAX_TABLES = 64
MAX_TOKENS_PER_TABLE = 1_000_000
MAX_TOTAL_TOKENS = 2_000_000
MAX_TOKEN_BYTES = 4096
MAX_TOTAL_TOKEN_BYTES = 64_000_000
MAX_PREFIX_NODES = 4_000_000
MAX_RACE_WORK = 1_000_000
MAX_TOKEN_ID_CHARS = 1024
MAX_METADATA_CHARS = 4096


class EOTLatticeError(ValueError):
    """An EOT table, probability measure, receipt, or path is invalid."""


class _StableSum:
    """Neumaier accumulator for sparse probability edges."""

    __slots__ = ("_correction", "_total")

    def __init__(self) -> None:
        self._total = 0.0
        self._correction = 0.0

    def add(self, value: float) -> None:
        candidate = self._total + value
        if abs(self._total) >= abs(value):
            self._correction += (self._total - candidate) + value
        else:
            self._correction += (value - candidate) + self._total
        self._total = candidate

    def value(self) -> float:
        return self._total + self._correction


@dataclass(frozen=True, slots=True)
class TokenProbability:
    """One teacher token and its exact decoded-byte path."""

    token_id: int | str
    byte_hex: str
    probability: float
    label: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.token_id, bool) or not isinstance(self.token_id, (int, str)):
            raise ValueError("token_id must be an integer or string")
        if isinstance(self.token_id, str):
            if not self.token_id:
                raise ValueError("string token_id cannot be empty")
            if len(self.token_id) > MAX_TOKEN_ID_CHARS:
                raise ValueError(f"string token_id cannot exceed {MAX_TOKEN_ID_CHARS}")
        if not isinstance(self.label, str) or len(self.label) > MAX_METADATA_CHARS:
            raise ValueError(f"label must be a string of at most {MAX_METADATA_CHARS}")
        try:
            raw = bytes.fromhex(self.byte_hex)
        except (TypeError, ValueError) as exc:
            raise ValueError("byte_hex must be hexadecimal") from exc
        if raw.hex() != self.byte_hex:
            raise ValueError("byte_hex must be canonical lowercase hexadecimal")
        if len(raw) > MAX_TOKEN_BYTES:
            raise ValueError(f"token byte length cannot exceed {MAX_TOKEN_BYTES}")
        if isinstance(self.probability, bool) or not isinstance(
            self.probability, (int, float)
        ):
            raise ValueError("probability must be a real number, not bool")
        probability = float(self.probability)
        if not math.isfinite(probability) or probability < 0.0:
            raise ValueError("probability must be finite and non-negative")
        object.__setattr__(
            self, "probability", 0.0 if probability == 0.0 else probability
        )


@dataclass(frozen=True, slots=True)
class TokenTableDistribution:
    """One independently normalized token table/teacher distribution."""

    table_id: str
    tokens: tuple[TokenProbability, ...]
    tokenizer_fingerprint: str = ""

    def __post_init__(self) -> None:
        if (
            not isinstance(self.table_id, str)
            or not self.table_id.strip()
            or len(self.table_id) > MAX_METADATA_CHARS
        ):
            raise ValueError(
                f"table_id must be a non-empty string of at most {MAX_METADATA_CHARS}"
            )
        if (
            not isinstance(self.tokenizer_fingerprint, str)
            or len(self.tokenizer_fingerprint) > MAX_METADATA_CHARS
        ):
            raise ValueError("tokenizer_fingerprint is invalid")
        if not isinstance(self.tokens, tuple) or not self.tokens:
            raise ValueError("a token table needs a non-empty token tuple")
        if len(self.tokens) > MAX_TOKENS_PER_TABLE:
            raise ValueError(
                f"a token table cannot exceed {MAX_TOKENS_PER_TABLE} tokens"
            )
        if not all(isinstance(row, TokenProbability) for row in self.tokens):
            raise ValueError("every token row must be TokenProbability")
        identities = [
            (type(row.token_id).__name__, row.token_id) for row in self.tokens
        ]
        if len(set(identities)) != len(identities):
            raise ValueError("token IDs must be unique within a table")
        total = math.fsum(row.probability for row in self.tokens)
        if not math.isclose(
            total,
            1.0,
            rel_tol=PROBABILITY_TOLERANCE,
            abs_tol=PROBABILITY_TOLERANCE,
        ):
            raise ValueError(f"table probabilities must sum to one, got {total!r}")


@dataclass(frozen=True, slots=True)
class CompositeRaceSpec:
    """Hard bounds and scoring choices for one-distribution path search."""

    beam_width: int = 32
    max_steps: int = 64
    edge_probability_floor: float = 0.0
    path_probability_floor: float = 0.0
    probability_power: float = 1.0
    score_basis: str = "conditional"
    max_completed_paths: int = 4096
    max_expansions: int = 100_000

    def __post_init__(self) -> None:
        for name, value in (
            ("beam_width", self.beam_width),
            ("max_steps", self.max_steps),
            ("max_completed_paths", self.max_completed_paths),
            ("max_expansions", self.max_expansions),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.beam_width > 4096 or self.max_steps > 4096:
            raise ValueError("beam_width and max_steps cannot exceed 4096")
        if self.max_completed_paths > MAX_RACE_WORK:
            raise ValueError(f"max_completed_paths cannot exceed {MAX_RACE_WORK}")
        if self.max_expansions > MAX_RACE_WORK:
            raise ValueError(f"max_expansions cannot exceed {MAX_RACE_WORK}")
        if self.beam_width * self.max_steps > MAX_RACE_WORK:
            raise ValueError(f"beam_width * max_steps cannot exceed {MAX_RACE_WORK}")
        for name, value in (
            ("edge_probability_floor", self.edge_probability_floor),
            ("path_probability_floor", self.path_probability_floor),
        ):
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if not math.isfinite(self.probability_power) or self.probability_power <= 0.0:
            raise ValueError("probability_power must be finite and positive")
        if self.score_basis not in {"conditional", "absolute"}:
            raise ValueError("score_basis must be 'conditional' or 'absolute'")


@dataclass(slots=True)
class _TrieNode:
    parent_node_id: int | None
    incoming_byte: int | None
    depth: int
    children: dict[int, int] = field(default_factory=dict)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return sha256(_canonical_json(value)).hexdigest()


def _typed_token_id(token_id: int | str) -> str:
    kind = "int" if isinstance(token_id, int) else "str"
    return f"{kind}:{token_id}"


def _token_sort_key(row: TokenProbability) -> tuple[str, int, int | str]:
    if isinstance(row.token_id, int):
        return (row.byte_hex, 0, row.token_id)
    return (row.byte_hex, 1, row.token_id)


def _symbol_label(symbol: int) -> str:
    return "<eot>" if symbol == EOT_SYMBOL else f"byte:{symbol:02x}"


def _fold_trit(wall_mass: float, continuation_mass: float) -> int:
    difference = wall_mass - continuation_mass
    if math.isclose(
        wall_mass,
        continuation_mass,
        rel_tol=FOLD_RELATIVE_TOLERANCE,
        abs_tol=0.0,
    ):
        return 0
    return 1 if difference > 0.0 else -1


def _transition_function(
    *, node_id: int, symbol: int, child_node_id: int | None
) -> dict[str, Any]:
    identity = {
        "operation": "close_token" if symbol == EOT_SYMBOL else "append_byte",
        "domain_node_id": node_id,
        "symbol": symbol,
        "codomain_node_id": child_node_id,
    }
    return {**identity, "function_sha256": _digest(identity)}


def build_interwoven_eot_lattice(
    tables: Sequence[TokenTableDistribution],
) -> dict[str, Any]:
    """Build a shared byte trie with independent per-table probability fields."""

    if not tables:
        raise EOTLatticeError("at least one token table is required")
    if len(tables) > MAX_TABLES:
        raise EOTLatticeError(f"table count cannot exceed {MAX_TABLES}")
    if not all(isinstance(table, TokenTableDistribution) for table in tables):
        raise EOTLatticeError("every table must be TokenTableDistribution")
    if len({table.table_id for table in tables}) != len(tables):
        raise EOTLatticeError("table IDs must be unique")
    total_tokens = sum(len(table.tokens) for table in tables)
    if total_tokens > MAX_TOTAL_TOKENS:
        raise EOTLatticeError(f"total token count cannot exceed {MAX_TOTAL_TOKENS}")

    ordered_tables = sorted(tables, key=lambda table: table.table_id)
    trie = [_TrieNode(parent_node_id=None, incoming_byte=None, depth=0)]
    entries_by_table: dict[
        str, list[tuple[TokenProbability, bytes, tuple[int, ...]]]
    ] = {}
    edges_by_table: dict[str, dict[int, dict[int, _StableSum]]] = {}
    aliases_by_table: dict[str, dict[str, tuple[_StableSum, int]]] = {}
    normalizers: dict[str, float] = {}
    total_token_bytes = 0

    for table in ordered_tables:
        edge_accumulators: dict[int, dict[int, _StableSum]] = {}
        alias_accumulators: dict[str, tuple[_StableSum, int]] = {}
        entries: list[tuple[TokenProbability, bytes, tuple[int, ...]]] = []
        ordered_rows = sorted(table.tokens, key=_token_sort_key)
        normalizers[table.table_id] = math.fsum(row.probability for row in ordered_rows)

        for row in ordered_rows:
            raw = bytes.fromhex(row.byte_hex)
            total_token_bytes += len(raw)
            if total_token_bytes > MAX_TOTAL_TOKEN_BYTES:
                raise EOTLatticeError(
                    "total decoded token bytes cannot exceed "
                    f"{MAX_TOTAL_TOKEN_BYTES}"
                )
            alias_sum, alias_count = alias_accumulators.setdefault(
                row.byte_hex, (_StableSum(), 0)
            )
            alias_sum.add(row.probability)
            alias_accumulators[row.byte_hex] = (alias_sum, alias_count + 1)

            node_id = 0
            node_route = [0]
            for byte_value in raw:
                child_id = trie[node_id].children.get(byte_value)
                if child_id is None:
                    if len(trie) >= MAX_PREFIX_NODES:
                        raise EOTLatticeError(
                            f"prefix node count cannot exceed {MAX_PREFIX_NODES}"
                        )
                    child_id = len(trie)
                    trie[node_id].children[byte_value] = child_id
                    trie.append(
                        _TrieNode(
                            parent_node_id=node_id,
                            incoming_byte=byte_value,
                            depth=trie[node_id].depth + 1,
                        )
                    )
                if row.probability > 0.0:
                    symbol_masses = edge_accumulators.setdefault(node_id, {})
                    symbol_masses.setdefault(byte_value, _StableSum()).add(
                        row.probability
                    )
                node_id = child_id
                node_route.append(node_id)

            if row.probability > 0.0:
                symbol_masses = edge_accumulators.setdefault(node_id, {})
                symbol_masses.setdefault(EOT_SYMBOL, _StableSum()).add(row.probability)
            entries.append((row, raw, tuple(node_route)))

        entries_by_table[table.table_id] = entries
        edges_by_table[table.table_id] = edge_accumulators
        aliases_by_table[table.table_id] = alias_accumulators

    nodes: list[dict[str, Any]] = []
    edge_lookup: dict[tuple[int, str, int], dict[str, Any]] = {}
    intersection_order_histogram: dict[str, int] = {}

    for node_id, trie_node in enumerate(trie):
        table_views: list[dict[str, Any]] = []
        for table in ordered_tables:
            accumulators = edges_by_table[table.table_id].get(node_id)
            if not accumulators:
                continue
            next_masses = {
                symbol: accumulator.value()
                for symbol, accumulator in accumulators.items()
                if accumulator.value() > 0.0
            }
            interior_mass = math.fsum(next_masses.values())
            if interior_mass <= 0.0:
                continue
            wall_mass = next_masses.get(EOT_SYMBOL, 0.0)
            continuation_mass = math.fsum(
                mass for symbol, mass in next_masses.items() if symbol != EOT_SYMBOL
            )
            edges: list[dict[str, Any]] = []
            for symbol, mass in sorted(next_masses.items()):
                child_node_id = (
                    None if symbol == EOT_SYMBOL else trie_node.children.get(symbol)
                )
                if symbol != EOT_SYMBOL and child_node_id is None:
                    raise AssertionError("positive byte edge has no trie child")
                edge = {
                    "symbol": symbol,
                    "symbol_label": _symbol_label(symbol),
                    "root_address": (
                        None
                        if symbol == EOT_SYMBOL
                        else {
                            "byte_cell": symbol,
                            "opcode_cell": symbol & 63,
                            "orientation": symbol >> 6,
                        }
                    ),
                    "mass": mass,
                    "conditional_probability": mass / interior_mass,
                    "child_node_id": child_node_id,
                    "transition_function": _transition_function(
                        node_id=node_id,
                        symbol=symbol,
                        child_node_id=child_node_id,
                    ),
                }
                edges.append(edge)
                edge_lookup[(node_id, table.table_id, symbol)] = edge
            table_views.append(
                {
                    "table_id": table.table_id,
                    "interior_mass": interior_mass,
                    "wall_mass": wall_mass,
                    "continuation_mass": continuation_mass,
                    "wall_ratio": wall_mass / interior_mass,
                    "fold_trit": _fold_trit(wall_mass, continuation_mass),
                    "edges": edges,
                }
            )

        participating = [view["table_id"] for view in table_views]
        order = len(participating)
        intersection_order_histogram[str(order)] = (
            intersection_order_histogram.get(str(order), 0) + 1
        )
        nodes.append(
            {
                "node_id": node_id,
                "parent_node_id": trie_node.parent_node_id,
                "incoming_byte": trie_node.incoming_byte,
                "depth": trie_node.depth,
                "participating_table_ids": participating,
                "participating_table_count": order,
                "table_pair_relationship_count": order * (order - 1) // 2,
                "is_cross_table_intersection": order > 1,
                "table_views": table_views,
            }
        )

    token_paths: list[dict[str, Any]] = []
    maximum_error = 0.0
    for table in ordered_tables:
        normalizer = normalizers[table.table_id]
        for row, raw, node_route in entries_by_table[table.table_id]:
            product = 1.0
            symbols = (*raw, EOT_SYMBOL)
            steps: list[dict[str, Any]] = []
            for depth, symbol in enumerate(symbols):
                node_id = node_route[depth]
                edge = edge_lookup.get((node_id, table.table_id, symbol))
                probability = (
                    float(edge["conditional_probability"]) if edge is not None else 0.0
                )
                product = product * probability if edge is not None else 0.0
                steps.append(
                    {
                        "node_id": node_id,
                        "symbol": symbol,
                        "conditional_probability": probability,
                        "positive_mass_edge_present": edge is not None,
                        "transition_function_sha256": (
                            None
                            if edge is None
                            else edge["transition_function"]["function_sha256"]
                        ),
                    }
                )
            alias_sum, alias_count = aliases_by_table[table.table_id][row.byte_hex]
            raw_alias_mass = alias_sum.value()
            expected = raw_alias_mass / normalizer
            error = abs(product - expected)
            maximum_error = max(maximum_error, error)
            token_paths.append(
                {
                    "table_id": table.table_id,
                    "token_id": row.token_id,
                    "typed_token_id": _typed_token_id(row.token_id),
                    "label": row.label,
                    "byte_hex": row.byte_hex,
                    "symbols_with_eot": list(symbols),
                    "node_route": list(node_route),
                    "teacher_token_probability_raw": row.probability,
                    "teacher_distribution_normalizer": normalizer,
                    "normalized_teacher_token_probability": row.probability
                    / normalizer,
                    "raw_aggregate_byte_path_mass": raw_alias_mass,
                    "exact_byte_path_mass": expected,
                    "reconstructed_path_mass": product,
                    "reconstruction_abs_error": error,
                    "active_probability_path": expected > 0.0,
                    "byte_path_alias_count": alias_count,
                    "steps": steps,
                }
            )

    body = {
        "schema": EOT_LATTICE_SCHEMA,
        "alphabet": {
            "byte_range": [0, BYTE_ALPHABET_SIZE - 1],
            "eot_symbol": EOT_SYMBOL,
            "eot_is_not_a_byte": True,
        },
        "tables": [
            {
                "table_id": table.table_id,
                "tokenizer_fingerprint": table.tokenizer_fingerprint,
                "token_count": len(table.tokens),
                "input_probability_sum": normalizers[table.table_id],
                "probabilities_normalized_for_lattice": True,
            }
            for table in ordered_tables
        ],
        "nodes": nodes,
        "token_paths": token_paths,
        "metrics": {
            "table_count": len(ordered_tables),
            "token_count": len(token_paths),
            "total_decoded_token_bytes": total_token_bytes,
            "prefix_node_count": len(nodes),
            "cross_table_intersection_count": sum(
                bool(node["is_cross_table_intersection"]) for node in nodes
            ),
            "intersection_order_histogram": intersection_order_histogram,
            "positive_probability_path_count": sum(
                bool(row["active_probability_path"]) for row in token_paths
            ),
            "zero_probability_path_count": sum(
                not row["active_probability_path"] for row in token_paths
            ),
            "maximum_path_reconstruction_abs_error": maximum_error,
            "all_path_masses_exact_within_1e_12": maximum_error
            <= RECONSTRUCTION_TOLERANCE,
        },
        "topology_contract": {
            "root_byte_cells_are_immutable_0_to_255": True,
            "root_bytes_factor_as_four_orientations_of_64_opcode_cells": True,
            "eot_is_an_explicit_boundary_wall": True,
            "prefix_nodes_are_interiors": True,
            "outgoing_byte_edges_are_exterior_folds": True,
            "table_measures_remain_independent_at_shared_nodes": True,
            "geometry_never_replaces_exact_byte_identity": True,
            "nodes_store_parent_links_not_copied_full_prefixes": True,
        },
        "composition_contract": {
            "edge_functions_are_append_byte_or_close_token": True,
            "path_composition_is_ordered_function_composition": True,
            "decoded_byte_aliases_share_pushforward_path_mass": True,
            "individual_alias_token_probability_retained_separately": True,
            "external_quine_adapter_invoked": False,
            "external_covering_sieve_invoked": False,
        },
        "receipt_security": "unkeyed-corruption-detection-only",
    }
    if maximum_error > RECONSTRUCTION_TOLERANCE:
        raise AssertionError("EOT lattice failed exact path-mass reconstruction")
    return {**body, "receipt_sha256": _digest(body)}


def _validate_lattice(
    lattice: Mapping[str, Any],
) -> tuple[
    dict[int, Mapping[str, Any]],
    dict[tuple[int, int], int],
    dict[tuple[int, str], Mapping[str, Any]],
]:
    """Verify receipt plus semantic invariants consumed by the race."""

    if lattice.get("schema") != EOT_LATTICE_SCHEMA:
        raise EOTLatticeError("invalid EOT lattice schema")
    claimed = lattice.get("receipt_sha256")
    body = dict(lattice)
    body.pop("receipt_sha256", None)
    if claimed != _digest(body):
        raise EOTLatticeError("EOT lattice receipt hash mismatch")
    if lattice.get("receipt_security") != "unkeyed-corruption-detection-only":
        raise EOTLatticeError("receipt security label is invalid")
    alphabet = lattice.get("alphabet")
    if not isinstance(alphabet, Mapping) or (
        alphabet.get("byte_range") != [0, 255]
        or alphabet.get("eot_symbol") != EOT_SYMBOL
        or alphabet.get("eot_is_not_a_byte") is not True
    ):
        raise EOTLatticeError("invalid byte/EOT alphabet contract")
    table_rows = lattice.get("tables")
    if not isinstance(table_rows, list) or not 1 <= len(table_rows) <= MAX_TABLES:
        raise EOTLatticeError("invalid lattice table catalog")
    known_tables = {
        row.get("table_id") for row in table_rows if isinstance(row, Mapping)
    }
    if len(known_tables) != len(table_rows) or not all(
        isinstance(table_id, str) for table_id in known_tables
    ):
        raise EOTLatticeError("invalid or duplicate lattice table IDs")

    node_rows = lattice.get("nodes")
    if not isinstance(node_rows, list) or not 1 <= len(node_rows) <= MAX_PREFIX_NODES:
        raise EOTLatticeError("invalid lattice node catalog")
    nodes: dict[int, Mapping[str, Any]] = {}
    children: dict[tuple[int, int], int] = {}
    views: dict[tuple[int, str], Mapping[str, Any]] = {}

    for expected_id, node in enumerate(node_rows):
        if not isinstance(node, Mapping) or node.get("node_id") != expected_id:
            raise EOTLatticeError("node IDs must be contiguous and ordered")
        parent = node.get("parent_node_id")
        incoming = node.get("incoming_byte")
        depth = node.get("depth")
        if expected_id == 0:
            if parent is not None or incoming is not None or depth != 0:
                raise EOTLatticeError("invalid root trie node")
        else:
            valid_relation = (
                not isinstance(parent, bool)
                and isinstance(parent, int)
                and 0 <= parent < expected_id
                and not isinstance(incoming, bool)
                and isinstance(incoming, int)
                and 0 <= incoming < BYTE_ALPHABET_SIZE
                and isinstance(depth, int)
                and depth == nodes[parent]["depth"] + 1
            )
            if not valid_relation:
                raise EOTLatticeError("invalid trie parent/incoming/depth relation")
            child_key = (parent, incoming)
            if child_key in children:
                raise EOTLatticeError("duplicate byte child under one trie node")
            children[child_key] = expected_id
        nodes[expected_id] = node

        table_views = node.get("table_views")
        if not isinstance(table_views, list):
            raise EOTLatticeError("node table_views must be a list")
        participating = node.get("participating_table_ids")
        actual_tables: list[str] = []
        for view in table_views:
            if not isinstance(view, Mapping):
                raise EOTLatticeError("table view must be an object")
            table_id = view.get("table_id")
            if table_id not in known_tables or table_id in actual_tables:
                raise EOTLatticeError("invalid or duplicate table view")
            actual_tables.append(table_id)
            interior = view.get("interior_mass")
            wall = view.get("wall_mass")
            continuation = view.get("continuation_mass")
            masses = (interior, wall, continuation)
            if (
                not all(
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and value >= 0.0
                    for value in masses
                )
                or interior <= 0.0
            ):
                raise EOTLatticeError("invalid table-view masses")
            if not math.isclose(
                wall + continuation,
                interior,
                rel_tol=PROBABILITY_TOLERANCE,
                abs_tol=PROBABILITY_TOLERANCE,
            ):
                raise EOTLatticeError("wall and continuation masses do not partition")
            if not math.isclose(
                view.get("wall_ratio"),
                wall / interior,
                rel_tol=PROBABILITY_TOLERANCE,
                abs_tol=PROBABILITY_TOLERANCE,
            ) or view.get("fold_trit") != _fold_trit(wall, continuation):
                raise EOTLatticeError("invalid wall ratio or fold trit")
            edge_rows = view.get("edges")
            if not isinstance(edge_rows, list) or not edge_rows:
                raise EOTLatticeError("live table view requires edges")
            symbols: set[int] = set()
            conditional_sum = 0.0
            mass_sum = 0.0
            for edge in edge_rows:
                if not isinstance(edge, Mapping):
                    raise EOTLatticeError("edge must be an object")
                symbol = edge.get("symbol")
                if (
                    isinstance(symbol, bool)
                    or not isinstance(symbol, int)
                    or not 0 <= symbol <= EOT_SYMBOL
                    or symbol in symbols
                ):
                    raise EOTLatticeError("invalid or duplicate edge symbol")
                symbols.add(symbol)
                mass = edge.get("mass")
                conditional = edge.get("conditional_probability")
                if not all(
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and value > 0.0
                    for value in (mass, conditional)
                ):
                    raise EOTLatticeError("edge mass/probability must be positive")
                mass_sum += float(mass)
                conditional_sum += float(conditional)
                child = edge.get("child_node_id")
                root_address = edge.get("root_address")
                if symbol == EOT_SYMBOL:
                    if child is not None or root_address is not None:
                        raise EOTLatticeError("EOT edge cannot have byte address/child")
                else:
                    child_matches = (
                        isinstance(child, int)
                        and not isinstance(child, bool)
                        and expected_id < child < len(node_rows)
                        and node_rows[child].get("parent_node_id") == expected_id
                        and node_rows[child].get("incoming_byte") == symbol
                    )
                    if not child_matches:
                        raise EOTLatticeError("byte edge does not match trie child")
                    expected_address = {
                        "byte_cell": symbol,
                        "opcode_cell": symbol & 63,
                        "orientation": symbol >> 6,
                    }
                    if root_address != expected_address:
                        raise EOTLatticeError("byte edge has invalid root address")
                expected_function = _transition_function(
                    node_id=expected_id,
                    symbol=symbol,
                    child_node_id=child,
                )
                if edge.get("transition_function") != expected_function:
                    raise EOTLatticeError("edge transition function is invalid")
            if not math.isclose(
                mass_sum,
                interior,
                rel_tol=PROBABILITY_TOLERANCE,
                abs_tol=PROBABILITY_TOLERANCE,
            ) or not math.isclose(
                conditional_sum,
                1.0,
                rel_tol=PROBABILITY_TOLERANCE,
                abs_tol=PROBABILITY_TOLERANCE,
            ):
                raise EOTLatticeError("edge masses/probabilities do not normalize")
            views[(expected_id, table_id)] = view

        if participating != actual_tables:
            raise EOTLatticeError("participating table IDs do not match views")
        count = len(actual_tables)
        if (
            node.get("participating_table_count") != count
            or node.get("table_pair_relationship_count") != count * (count - 1) // 2
            or node.get("is_cross_table_intersection") is not (count > 1)
        ):
            raise EOTLatticeError("node intersection metadata is invalid")

    return nodes, children, views


def race_interwoven_token_paths(
    lattice: Mapping[str, Any],
    *,
    start_prefix: bytes = b"",
    spec: CompositeRaceSpec = CompositeRaceSpec(),
) -> dict[str, Any]:
    """Race bounded composed paths and report exact-byte convergence groups."""

    if not isinstance(start_prefix, bytes):
        raise EOTLatticeError("start_prefix must be bytes")
    nodes, children, views = _validate_lattice(lattice)
    start_node_id = 0
    start_node_route = [0]
    for byte_value in start_prefix:
        child_id = children.get((start_node_id, byte_value))
        if child_id is None:
            raise EOTLatticeError("start_prefix is not a lattice cell")
        start_node_id = child_id
        start_node_route.append(child_id)

    start_node = nodes[start_node_id]
    table_ids = list(start_node["participating_table_ids"])
    if not table_ids:
        raise EOTLatticeError("start_prefix has no positive probability mass")
    start_masses: dict[str, dict[str, float]] = {}
    for table_id in table_ids:
        root_view = views[(0, table_id)]
        start_view = views[(start_node_id, table_id)]
        start_masses[table_id] = {
            "raw_start_prefix_mass": float(start_view["interior_mass"]),
            "normalized_start_prefix_mass": float(start_view["interior_mass"])
            / float(root_view["interior_mass"]),
        }

    completed: list[dict[str, Any]] = []
    pruned = 0
    expansion_count = 0
    expansion_budget_exhausted = False
    max_step_limit_reached = False
    unfinished_frontier_count = 0
    processed_table_count = 0

    for table_id in table_ids:
        processed_table_count += 1
        start_absolute_mass = start_masses[table_id]["normalized_start_prefix_mass"]
        frontier: list[dict[str, Any]] = [
            {
                "node_id": start_node_id,
                "symbols": (),
                "node_route": (start_node_id,),
                "function_route": (),
                "conditional_probability": 1.0,
                "conditional_log_probability": 0.0,
            }
        ]
        for _ in range(spec.max_steps):
            expanded: list[dict[str, Any]] = []
            for candidate in frontier:
                view = views[(candidate["node_id"], table_id)]
                ordered_edges = sorted(
                    view["edges"],
                    key=lambda edge: (-edge["conditional_probability"], edge["symbol"]),
                )
                for edge in ordered_edges:
                    if expansion_count >= spec.max_expansions:
                        expansion_budget_exhausted = True
                        break
                    expansion_count += 1
                    edge_probability = float(edge["conditional_probability"])
                    conditional = (
                        candidate["conditional_probability"] * edge_probability
                    )
                    if (
                        edge_probability < spec.edge_probability_floor
                        or conditional < spec.path_probability_floor
                    ):
                        pruned += 1
                        continue
                    symbols = (*candidate["symbols"], int(edge["symbol"]))
                    conditional_log = candidate[
                        "conditional_log_probability"
                    ] + math.log(edge_probability)
                    absolute_mass = start_absolute_mass * conditional
                    score_log = (
                        conditional_log
                        if spec.score_basis == "conditional"
                        else math.log(start_absolute_mass) + conditional_log
                    )
                    function_route = (
                        *candidate["function_route"],
                        edge["transition_function"]["function_sha256"],
                    )
                    if edge["symbol"] == EOT_SYMBOL:
                        completed.append(
                            {
                                "table_id": table_id,
                                "start_prefix_hex": start_prefix.hex(),
                                "continuation_byte_hex": bytes(symbols[:-1]).hex(),
                                "symbols_with_eot": list(symbols),
                                "node_route": list(candidate["node_route"]),
                                "function_route": list(function_route),
                                "conditional_probability_from_start": conditional,
                                "absolute_teacher_path_mass": absolute_mass,
                                "conditional_log_probability": conditional_log,
                                "score_basis": spec.score_basis,
                                "power_log_score": spec.probability_power * score_log,
                                "power_score": math.exp(
                                    spec.probability_power * score_log
                                ),
                                "step_count": len(symbols),
                            }
                        )
                    else:
                        child_node_id = int(edge["child_node_id"])
                        expanded.append(
                            {
                                "node_id": child_node_id,
                                "symbols": symbols,
                                "node_route": (
                                    *candidate["node_route"],
                                    child_node_id,
                                ),
                                "function_route": function_route,
                                "conditional_probability": conditional,
                                "conditional_log_probability": conditional_log,
                            }
                        )
                if expansion_budget_exhausted:
                    break
            expanded.sort(
                key=lambda row: (
                    -row["conditional_log_probability"],
                    row["symbols"],
                )
            )
            if len(expanded) > spec.beam_width:
                pruned += len(expanded) - spec.beam_width
            frontier = expanded[: spec.beam_width]
            if len(completed) > spec.max_completed_paths:
                completed.sort(
                    key=lambda row: (
                        -row["power_log_score"],
                        row["table_id"],
                        row["symbols_with_eot"],
                    )
                )
                overflow = len(completed) - spec.max_completed_paths
                del completed[spec.max_completed_paths :]
                pruned += overflow
            if not frontier or expansion_budget_exhausted:
                break
        if frontier:
            unfinished_frontier_count += len(frontier)
            if not expansion_budget_exhausted:
                max_step_limit_reached = True
        if expansion_budget_exhausted:
            break

    completed.sort(
        key=lambda row: (
            -row["power_log_score"],
            row["table_id"],
            row["symbols_with_eot"],
        )
    )
    convergence: dict[str, list[dict[str, Any]]] = {}
    for row in completed:
        convergence.setdefault(row["continuation_byte_hex"], []).append(row)
    convergence_rows = []
    for byte_hex, rows in sorted(convergence.items()):
        row_tables = sorted({row["table_id"] for row in rows})
        convergence_rows.append(
            {
                "continuation_byte_hex": byte_hex,
                "table_count": len(row_tables),
                "tables": row_tables,
                "table_pair_relationship_count": len(row_tables)
                * (len(row_tables) - 1)
                // 2,
                "routes": rows,
            }
        )

    body = {
        "schema": EOT_RACE_SCHEMA,
        "source_lattice_sha256": lattice["receipt_sha256"],
        "spec": asdict(spec),
        "start_prefix_hex": start_prefix.hex(),
        "start_node_id": start_node_id,
        "start_node_route": start_node_route,
        "start_prefix_table_masses": start_masses,
        "completed_paths": completed,
        "convergence": convergence_rows,
        "metrics": {
            "participating_table_count": len(table_ids),
            "completed_path_count": len(completed),
            "multi_table_convergence_count": sum(
                row["table_count"] > 1 for row in convergence_rows
            ),
            "pruned_candidate_count": pruned,
            "expansion_count": expansion_count,
            "expansion_budget_exhausted": expansion_budget_exhausted,
            "max_step_limit_reached": max_step_limit_reached,
            "unfinished_frontier_count": unfinished_frontier_count,
            "processed_table_count": processed_table_count,
            "unprocessed_table_count": len(table_ids) - processed_table_count,
            "search_exhaustive_within_lattice": (
                not expansion_budget_exhausted
                and not max_step_limit_reached
                and pruned == 0
            ),
        },
        "claim_boundary": {
            "one_next_token_distribution_only": True,
            "new_distribution_required_after_eot": True,
            "conditional_and_absolute_mass_are_separate": True,
            "power_score_is_selection_telemetry_not_probability": True,
            "positive_power_preserves_probability_order_in_log_domain": True,
            "external_quine_adapter_invoked": False,
            "learned_gain_proven": False,
            "bounded_search_may_be_non_exhaustive": True,
        },
        "receipt_security": "unkeyed-corruption-detection-only",
    }
    return {**body, "receipt_sha256": _digest(body)}


def validate_eot_lattice(lattice: Mapping[str, Any]) -> None:
    """Fail closed unless a lattice receipt and its consumed topology are valid."""

    _validate_lattice(lattice)


def verify_eot_lattice_receipt(lattice: Mapping[str, Any]) -> bool:
    """Boolean convenience wrapper over :func:`validate_eot_lattice`."""

    try:
        validate_eot_lattice(lattice)
    except (EOTLatticeError, KeyError, TypeError, ValueError):
        return False
    return True


def verify_eot_race_receipt(
    race: Mapping[str, Any], lattice: Mapping[str, Any]
) -> bool:
    """Verify race integrity and its binding to a semantically valid lattice."""

    _validate_lattice(lattice)
    if race.get("schema") != EOT_RACE_SCHEMA:
        raise EOTLatticeError("invalid EOT race schema")
    claimed = race.get("receipt_sha256")
    body = dict(race)
    body.pop("receipt_sha256", None)
    if claimed != _digest(body):
        raise EOTLatticeError("EOT race receipt hash mismatch")
    if race.get("source_lattice_sha256") != lattice.get("receipt_sha256"):
        raise EOTLatticeError("race is not bound to this lattice")
    if race.get("receipt_security") != "unkeyed-corruption-detection-only":
        raise EOTLatticeError("race receipt security label is invalid")
    metrics = race.get("metrics")
    completed = race.get("completed_paths")
    if (
        not isinstance(metrics, Mapping)
        or not isinstance(completed, list)
        or metrics.get("completed_path_count") != len(completed)
    ):
        raise EOTLatticeError("race metrics do not match completed paths")
    return True


__all__ = [
    "BYTE_ALPHABET_SIZE",
    "EOT_LATTICE_SCHEMA",
    "EOT_RACE_SCHEMA",
    "EOT_SYMBOL",
    "CompositeRaceSpec",
    "EOTLatticeError",
    "TokenProbability",
    "TokenTableDistribution",
    "build_interwoven_eot_lattice",
    "race_interwoven_token_paths",
    "validate_eot_lattice",
    "verify_eot_lattice_receipt",
    "verify_eot_race_receipt",
]
