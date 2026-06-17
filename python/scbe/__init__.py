"""SCBE Python package.

The CLI imports lightweight submodules such as ``python.scbe.bit_spine``.
Keep this package root lazy so installing the base wheel does not import
optional science, network, or governance dependencies before a command asks
for them.
"""

from importlib import import_module

__version__ = "3.0.0"
__author__ = "Issac Davis"

_LAZY_EXPORTS = {
    "AetherBrain": ("python.scbe.brain", "AetherBrain"),
    "PoincareBall": ("python.scbe.brain", "PoincareBall"),
    "PHDMLattice": ("python.scbe.brain", "PHDMLattice"),
    "FluxState": ("python.scbe.brain", "FluxState"),
    "TrustRing": ("python.scbe.brain", "TrustRing"),
    "ThoughtStatus": ("python.scbe.brain", "ThoughtStatus"),
    "ThoughtResult": ("python.scbe.brain", "ThoughtResult"),
    "create_brain": ("python.scbe.brain", "create_brain"),
    "embed_text": ("python.scbe.brain", "embed_text"),
    "embed_to_21d": ("python.scbe.brain", "embed_to_21d"),
    "embed_vector_to_21d": ("python.scbe.brain", "embed_vector_to_21d"),
    "TONGUES": ("python.scbe.brain", "TONGUES"),
    "GOLDEN_RATIO": ("python.scbe.brain", "GOLDEN_RATIO"),
    "GOLDEN_RATIO_INV": ("python.scbe.brain", "GOLDEN_RATIO_INV"),
    "PYTHAGOREAN_COMMA": ("python.scbe.brain", "PYTHAGOREAN_COMMA"),
    "R_FIFTH": ("python.scbe.brain", "R_FIFTH"),
    "DIMENSIONS_21D": ("python.scbe.brain", "DIMENSIONS_21D"),
    "DIMENSIONS_6D": ("python.scbe.brain", "DIMENSIONS_6D"),
    "TUBE_RADIUS": ("python.scbe.brain", "TUBE_RADIUS"),
    "DefensiveMeshKernel": ("python.scbe.defensive_mesh", "DefensiveMeshKernel"),
    "GovernedJob": ("python.scbe.defensive_mesh", "GovernedJob"),
    "GovernedTask": ("python.scbe.defensive_mesh", "GovernedTask"),
    "TaskGateResult": ("python.scbe.defensive_mesh", "TaskGateResult"),
    "AtomicElement": ("python.scbe.atomic_tokenization", "Element"),
    "AtomicTokenState": ("python.scbe.atomic_tokenization", "AtomicTokenState"),
    "TritVector": ("python.scbe.atomic_tokenization", "TritVector"),
    "atomic_drift_scale": ("python.scbe.atomic_tokenization", "atomic_drift_scale"),
    "element_to_tau": ("python.scbe.atomic_tokenization", "element_to_tau"),
    "element_to_trit_vector": ("python.scbe.atomic_tokenization", "element_to_trit_vector"),
    "map_token_to_element": ("python.scbe.atomic_tokenization", "map_token_to_element"),
    "map_token_to_atomic_state": ("python.scbe.atomic_tokenization", "map_token_to_atomic_state"),
    "FusionParams": ("python.scbe.chemical_fusion", "FusionParams"),
    "FusionResult": ("python.scbe.chemical_fusion", "FusionResult"),
    "fuse_atomic_states": ("python.scbe.chemical_fusion", "fuse_atomic_states"),
    "fuse_tokens": ("python.scbe.chemical_fusion", "fuse_tokens"),
    "CAOpcodeEntry": ("python.scbe.ca_opcode_table", "CAOpcodeEntry"),
    "CA_OP_TABLE": ("python.scbe.ca_opcode_table", "OP_TABLE"),
    "validate_ca_table": ("python.scbe.ca_opcode_table", "validate_ca_table"),
    "get_ca_opcode": ("python.scbe.ca_opcode_table", "get_ca_opcode"),
    "ca_opcode_to_atomic_state": ("python.scbe.ca_opcode_table", "ca_opcode_to_atomic_state"),
    "ca_opcodes_to_atomic_states": ("python.scbe.ca_opcode_table", "ca_opcodes_to_atomic_states"),
    "fuse_ca_opcodes": ("python.scbe.ca_opcode_table", "fuse_ca_opcodes"),
    "FibonacciTrustLadder": ("python.scbe.history_reducer", "FibonacciTrustLadder"),
    "HistoryReducerState": ("python.scbe.history_reducer", "HistoryReducerState"),
    "HistoryStepResult": ("python.scbe.history_reducer", "HistoryStepResult"),
    "reduce_atomic_history": ("python.scbe.history_reducer", "reduce_atomic_history"),
    "reduce_years": ("python.scbe.history_reducer", "reduce_years"),
    "CODE_LANE_REGISTRY": ("python.scbe.tongue_code_lanes", "CODE_LANE_REGISTRY"),
    "default_code_lane_profile": ("python.scbe.tongue_code_lanes", "default_code_lane_profile"),
    "expected_code_lanes": ("python.scbe.tongue_code_lanes", "expected_code_lanes"),
    "classify_code_lane_alignment": ("python.scbe.tongue_code_lanes", "classify_code_lane_alignment"),
    "load_source_registry": ("python.scbe.ingestion_rights", "load_source_registry"),
    "get_source_record": ("python.scbe.ingestion_rights", "get_source_record"),
    "classify_ingestion_rights_record": (
        "python.scbe.ingestion_rights",
        "classify_ingestion_rights_record",
    ),
    "rhombic_fusion": ("python.scbe.rhombic_bridge", "rhombic_fusion"),
    "rhombic_score": ("python.scbe.rhombic_bridge", "rhombic_score"),
    "SemanticSignal": ("python.scbe.semantic_gate", "SemanticSignal"),
    "SemanticBlendPolicy": ("python.scbe.semantic_gate", "SemanticBlendPolicy"),
    "SemanticGateRecord": ("python.scbe.semantic_gate", "SemanticGateRecord"),
    "evaluate_semantic_gate": ("python.scbe.semantic_gate", "evaluate_semantic_gate"),
    "ReactionEndpoint": ("python.scbe.reaction_state", "ReactionEndpoint"),
    "ReactionRecalculation": ("python.scbe.reaction_state", "ReactionRecalculation"),
    "ReactionStatePacket": ("python.scbe.reaction_state", "ReactionStatePacket"),
    "build_reaction_state_packet": ("python.scbe.reaction_state", "build_reaction_state_packet"),
    "classify_reaction": ("python.scbe.reaction_state", "classify_reaction"),
    "packet_from_dict": ("python.scbe.reaction_state", "packet_from_dict"),
    "ReactionFieldCheck": ("python.scbe.reaction_harness", "ReactionFieldCheck"),
    "BijectiveReactionResult": ("python.scbe.reaction_harness", "BijectiveReactionResult"),
    "evaluate_bijective_reaction": ("python.scbe.reaction_harness", "evaluate_bijective_reaction"),
    "RecouplingState": ("python.scbe.quasi_integer_recoupling", "RecouplingState"),
    "QuasiIntegerRecoupling": ("python.scbe.quasi_integer_recoupling", "QuasiIntegerRecoupling"),
    "CHEMICAL_BOND_ORDER_STATES": (
        "python.scbe.quasi_integer_recoupling",
        "CHEMICAL_BOND_ORDER_STATES",
    ),
    "FORMAL_CHARGE_STATES": ("python.scbe.quasi_integer_recoupling", "FORMAL_CHARGE_STATES"),
    "integer_states": ("python.scbe.quasi_integer_recoupling", "integer_states"),
    "half_integer_states": ("python.scbe.quasi_integer_recoupling", "half_integer_states"),
    "recouple_to_states": ("python.scbe.quasi_integer_recoupling", "recouple_to_states"),
    "recouple_to_integer": ("python.scbe.quasi_integer_recoupling", "recouple_to_integer"),
    "recouple_bond_order": ("python.scbe.quasi_integer_recoupling", "recouple_bond_order"),
    "recouple_formal_charge": ("python.scbe.quasi_integer_recoupling", "recouple_formal_charge"),
    "AudioFieldModel": ("python.scbe.audio_field_observables", "AudioFieldModel"),
    "AudioFieldObservables": ("python.scbe.audio_field_observables", "AudioFieldObservables"),
    "analyze_audio_field": ("python.scbe.audio_field_observables", "analyze_audio_field"),
    "generate_sine": ("python.scbe.audio_field_observables", "generate_sine"),
    "generate_decaying_sine": ("python.scbe.audio_field_observables", "generate_decaying_sine"),
}

__all__ = sorted(_LAZY_EXPORTS)


def __getattr__(name):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, export_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), export_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted({*globals(), *_LAZY_EXPORTS})
