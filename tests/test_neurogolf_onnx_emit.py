from __future__ import annotations

from zipfile import ZipFile

import onnx

from neurogolf.ir import (
    make_copy_color_program,
    make_orientation_color_remap_program,
    make_shift_color_program,
    make_shift_color_remap_program,
)
from neurogolf.onnx_emit import export_program_onnx
from neurogolf.package import build_submission_zip


def test_export_program_onnx_for_shift_then_remap(tmp_path):
    output_path = tmp_path / "task201.onnx"
    program = make_shift_color_remap_program(shift_x=0, shift_y=1, mapping={1: 5, 2: 6})

    export_program_onnx(program, output_path)
    model = onnx.load(str(output_path), load_external_data=False)

    assert [node.op_type for node in model.graph.node] == ["Conv", "Conv"]
    assert [dim.dim_value for dim in model.graph.input[0].type.tensor_type.shape.dim] == [
        1,
        10,
        30,
        30,
    ]


def test_build_submission_zip_with_exported_program(tmp_path):
    onnx_path = tmp_path / "task001.onnx"
    zip_path = tmp_path / "submission.zip"
    program = make_shift_color_remap_program(shift_x=1, shift_y=0, mapping={1: 7})

    export_program_onnx(program, onnx_path)
    build_submission_zip({"task001": onnx_path}, zip_path)

    with ZipFile(zip_path) as zf:
        assert zf.namelist() == ["task001.onnx"]


def test_export_program_onnx_for_flip_then_remap(tmp_path):
    output_path = tmp_path / "task202.onnx"
    program = make_orientation_color_remap_program("flip_x", {1: 8, 2: 9})

    export_program_onnx(program, output_path)
    model = onnx.load(str(output_path), load_external_data=False)

    op_types = [node.op_type for node in model.graph.node]
    assert "Conv" in op_types
    assert len(op_types) >= 2


def test_export_program_onnx_for_shift_color(tmp_path):
    output_path = tmp_path / "task203.onnx"
    program = make_shift_color_program(color=3, shift_x=1, shift_y=0)

    export_program_onnx(program, output_path)
    model = onnx.load(str(output_path), load_external_data=False)

    assert [node.op_type for node in model.graph.node] == ["Conv"]


def test_export_program_onnx_for_copy_color(tmp_path):
    output_path = tmp_path / "task204.onnx"
    program = make_copy_color_program(color=3, shift_x=1, shift_y=0)

    export_program_onnx(program, output_path)
    model = onnx.load(str(output_path), load_external_data=False)

    op_types = [node.op_type for node in model.graph.node]
    assert "Conv" in op_types
    assert "Clip" in op_types
