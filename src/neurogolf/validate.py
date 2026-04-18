from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import onnx
from onnx import TensorProto

from .cost import NetworkCost, conv2d_macs, score_from_total_cost, tensor_nbytes


BANNED_OPS = frozenset({"Loop", "Scan", "NonZero", "Unique", "Script", "Function"})
MAX_ONNX_BYTES = 1_440_000


@dataclass(frozen=True)
class ValidationReport:
    path: Path
    file_size_bytes: int
    op_types: tuple[str, ...]
    cost: NetworkCost
    score: float


def _tensor_shape(value_info) -> tuple[int, ...]:
    dims = []
    tensor_type = value_info.type.tensor_type
    for dim in tensor_type.shape.dim:
        if not dim.HasField("dim_value"):
            raise ValueError(f"Dynamic or unknown dimension found in {value_info.name}")
        dims.append(dim.dim_value)
    return tuple(int(dim) for dim in dims)


def _dtype_bytes(data_type: int) -> int:
    mapping = {
        TensorProto.FLOAT: 4,
        TensorProto.FLOAT16: 2,
        TensorProto.DOUBLE: 8,
        TensorProto.INT64: 8,
        TensorProto.INT32: 4,
        TensorProto.INT16: 2,
        TensorProto.INT8: 1,
        TensorProto.UINT8: 1,
        TensorProto.BOOL: 1,
    }
    return mapping.get(data_type, 4)


def _initializer_nbytes(tensor: onnx.TensorProto) -> int:
    shape = tuple(int(dim) for dim in tensor.dims)
    return tensor_nbytes(shape, dtype_bytes=_dtype_bytes(tensor.data_type))


def validate_submission_model(path: str | Path) -> ValidationReport:
    model_path = Path(path)
    file_size = model_path.stat().st_size
    if file_size > MAX_ONNX_BYTES:
        raise ValueError(
            f"ONNX file {model_path} exceeds NeuroGolf size cap: {file_size} > {MAX_ONNX_BYTES}"
        )

    model = onnx.load(str(model_path), load_external_data=False)
    op_types = tuple(node.op_type for node in model.graph.node)
    banned = [op for op in op_types if op in BANNED_OPS]
    if banned:
        raise ValueError(f"Banned ONNX operators present: {sorted(set(banned))}")

    for value in list(model.graph.input) + list(model.graph.output) + list(model.graph.value_info):
        if value.type.HasField("tensor_type"):
            _tensor_shape(value)

    parameters = 0
    memory_bytes = 0
    macs = 0

    init_map = {tensor.name: tensor for tensor in model.graph.initializer}
    value_shapes: dict[str, tuple[int, ...]] = {}
    for value in list(model.graph.input) + list(model.graph.output) + list(model.graph.value_info):
        if value.type.HasField("tensor_type"):
            value_shapes[value.name] = _tensor_shape(value)

    for tensor in model.graph.initializer:
        parameters += int(len(onnx.numpy_helper.to_array(tensor).reshape(-1)))
        memory_bytes += _initializer_nbytes(tensor)

    for node in model.graph.node:
        if node.op_type != "Conv":
            continue
        if len(node.input) < 2 or len(node.output) != 1:
            continue
        input_shape = value_shapes.get(node.input[0])
        output_shape = value_shapes.get(node.output[0])
        weight = init_map.get(node.input[1])
        if input_shape is None or output_shape is None or weight is None:
            continue
        weight_shape = tuple(int(dim) for dim in weight.dims)
        if len(weight_shape) != 4 or len(output_shape) != 4:
            continue
        out_channels, in_per_group, kernel_h, kernel_w = weight_shape
        out_h, out_w = output_shape[2], output_shape[3]
        groups = 1
        for attr in node.attribute:
            if attr.name == "group":
                groups = int(attr.i)
                break
        in_channels = in_per_group * groups
        macs += conv2d_macs(out_h, out_w, out_channels, in_channels, kernel_h, kernel_w)

    cost = NetworkCost(parameters=parameters, memory_bytes=memory_bytes, macs=macs)
    return ValidationReport(
        path=model_path,
        file_size_bytes=file_size,
        op_types=op_types,
        cost=cost,
        score=score_from_total_cost(cost.total),
    )
