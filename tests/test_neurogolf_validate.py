from __future__ import annotations

import onnx
from onnx import TensorProto, helper

from neurogolf.ir import make_multi_shift_color_program
from neurogolf.onnx_emit import export_program_onnx
from neurogolf.validate import validate_submission_model


def test_validate_submission_model_reports_costs(tmp_path):
    output_path = tmp_path / "task301.onnx"
    program = make_multi_shift_color_program([(1, 1, 0), (2, -1, 0)])

    export_program_onnx(program, output_path)
    report = validate_submission_model(output_path)

    assert report.file_size_bytes > 0
    assert "Conv" in report.op_types
    assert report.cost.parameters > 0
    assert report.cost.memory_bytes > 0
    assert report.cost.macs > 0
    assert report.score >= 1.0


def test_validate_submission_model_rejects_banned_ops(tmp_path):
    model_path = tmp_path / "bad.onnx"
    input_info = helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 1])
    output_info = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 1])
    graph = helper.make_graph(
        nodes=[helper.make_node("Loop", inputs=["x"], outputs=["y"])],
        name="bad_graph",
        inputs=[input_info],
        outputs=[output_info],
    )
    model = helper.make_model(graph)
    onnx.save(model, model_path)

    try:
        validate_submission_model(model_path)
    except ValueError as exc:
        assert "Banned ONNX operators" in str(exc)
    else:
        raise AssertionError("Expected banned-op validation failure")
