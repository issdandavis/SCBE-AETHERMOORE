"""Minimal NeuroGolf submission scaffold."""

from .arc_io import ARCExample, ARCTask, grid_to_one_hot, load_arc_task, pad_grid
from .components import ConnectedComponent, component_mask, connected_components, extract_component
from .cost import score_from_total_cost
from .ir import StraightLineProgram
from .onnx_emit import export_program_onnx
from .solver import SynthesizedSolution, execute_program, synthesize_program
from .structural_encode import StructuralEncoding, encode_grid_structurally

__all__ = [
    "ARCExample",
    "ARCTask",
    "ConnectedComponent",
    "StraightLineProgram",
    "component_mask",
    "connected_components",
    "StructuralEncoding",
    "encode_grid_structurally",
    "execute_program",
    "extract_component",
    "export_program_onnx",
    "grid_to_one_hot",
    "load_arc_task",
    "pad_grid",
    "score_from_total_cost",
    "synthesize_program",
    "SynthesizedSolution",
]

try:
    from .validate import ValidationReport, validate_submission_model
except ImportError:  # Optional ONNX dependency for validation-only workflows.
    ValidationReport = None  # type: ignore[assignment]
    validate_submission_model = None  # type: ignore[assignment]
else:
    __all__.extend([
        "ValidationReport",
        "validate_submission_model",
    ])
