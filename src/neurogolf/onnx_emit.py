from __future__ import annotations

from pathlib import Path
import sys

from .ir import StraightLineProgram, make_color_remap_program


def _cleanup_sidecar(output_path: Path) -> None:
    sidecar_path = output_path.with_name(output_path.name + ".data")
    if sidecar_path.exists():
        sidecar_path.unlink()


def export_program_onnx(
    program: StraightLineProgram,
    output_path: str | Path,
    *,
    grid_size: int = 30,
    num_colors: int = 10,
    opset_version: int = 18,
) -> Path:
    """Export a restricted straight-line NeuroGolf program as a static ONNX graph."""

    try:
        import onnx
        import torch
        import torch.nn as nn
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("PyTorch and ONNX are required for NeuroGolf export") from exc

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _cleanup_sidecar(output_path)

    class ColorRemapLayer(nn.Module):
        def __init__(self, mapping_dict: dict[int, int]) -> None:
            super().__init__()
            weight = torch.zeros((num_colors, num_colors, 1, 1), dtype=torch.float32)
            for src in range(num_colors):
                dst = int(mapping_dict.get(src, src))
                weight[dst, src, 0, 0] = 1.0
            self.register_buffer("weight", weight)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return torch.nn.functional.conv2d(x, self.weight)

    class ShiftLayer(nn.Module):
        def __init__(self, shift_x: int, shift_y: int) -> None:
            super().__init__()
            radius = max(abs(shift_x), abs(shift_y))
            kernel_size = 2 * radius + 1
            center = radius
            weight = torch.zeros((num_colors, 1, kernel_size, kernel_size), dtype=torch.float32)
            weight[:, 0, center + shift_y, center + shift_x] = 1.0
            self.register_buffer("weight", weight)
            self.padding = radius

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return torch.nn.functional.conv2d(
                x,
                self.weight,
                padding=self.padding,
                groups=num_colors,
            )

    class ShiftColorLayer(nn.Module):
        def __init__(self, color: int, shift_x: int, shift_y: int) -> None:
            super().__init__()
            radius = max(abs(shift_x), abs(shift_y))
            kernel_size = 2 * radius + 1
            center = radius
            weight = torch.zeros((num_colors, 1, kernel_size, kernel_size), dtype=torch.float32)
            weight[:, 0, center, center] = 1.0
            weight[color, 0, :, :] = 0.0
            weight[color, 0, center + shift_y, center + shift_x] = 1.0
            self.register_buffer("weight", weight)
            self.padding = radius

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return torch.nn.functional.conv2d(
                x,
                self.weight,
                padding=self.padding,
                groups=num_colors,
            )

    class CopyColorLayer(nn.Module):
        def __init__(self, color: int, shift_x: int, shift_y: int) -> None:
            super().__init__()
            radius = max(abs(shift_x), abs(shift_y))
            kernel_size = 2 * radius + 1
            center = radius
            weight = torch.zeros((num_colors, 1, kernel_size, kernel_size), dtype=torch.float32)
            weight[:, 0, center, center] = 1.0
            weight[color, 0, center + shift_y, center + shift_x] += 1.0
            self.register_buffer("weight", weight)
            self.padding = radius

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            out = torch.nn.functional.conv2d(
                x,
                self.weight,
                padding=self.padding,
                groups=num_colors,
            )
            return torch.clamp(out, 0.0, 1.0)

    class FlipXLayer(nn.Module):
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return torch.flip(x, dims=(3,))

    class FlipYLayer(nn.Module):
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return torch.flip(x, dims=(2,))

    class TransposeLayer(nn.Module):
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return torch.transpose(x, 2, 3)

    modules: list[nn.Module] = []
    for step in program.steps:
        if step.op == "identity":
            modules.append(ColorRemapLayer({color: color for color in range(num_colors)}))
            continue
        if step.op == "color_remap":
            modules.append(ColorRemapLayer(dict(step.args["mapping"])))
            continue
        if step.op == "shift":
            modules.append(
                ShiftLayer(
                    int(step.args["shift_x"]),
                    int(step.args["shift_y"]),
                )
            )
            continue
        if step.op == "shift_color":
            modules.append(
                ShiftColorLayer(
                    int(step.args["color"]),
                    int(step.args["shift_x"]),
                    int(step.args["shift_y"]),
                )
            )
            continue
        if step.op == "copy_color":
            modules.append(
                CopyColorLayer(
                    int(step.args["color"]),
                    int(step.args["shift_x"]),
                    int(step.args["shift_y"]),
                )
            )
            continue
        if step.op == "flip_x":
            modules.append(FlipXLayer())
            continue
        if step.op == "flip_y":
            modules.append(FlipYLayer())
            continue
        if step.op == "transpose":
            modules.append(TransposeLayer())
            continue
        raise ValueError(f"Unsupported ONNX lowering for primitive '{step.op}'")

    model = nn.Sequential(*modules)
    model.eval()
    dummy = torch.zeros((1, num_colors, grid_size, grid_size), dtype=torch.float32)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        torch.onnx.export(
            model,
            dummy,
            str(output_path),
            input_names=["grid"],
            output_names=["grid_out"],
            opset_version=opset_version,
            do_constant_folding=True,
            dynamic_axes=None,
            external_data=False,
        )
    except ModuleNotFoundError as exc:  # pragma: no cover - environment-specific
        if exc.name == "onnxscript":
            raise RuntimeError(
                "ONNX export requires the 'onnxscript' package in this environment"
            ) from exc
        raise

    sidecar_path = output_path.with_name(output_path.name + ".data")
    if sidecar_path.exists():
        try:
            model_proto = onnx.load(str(output_path), load_external_data=False)
            uses_external_data = any(
                any(field.key == "location" for field in tensor.external_data)
                for tensor in model_proto.graph.initializer
            )
            if not uses_external_data:
                sidecar_path.unlink()
        except Exception:
            pass
    return output_path


def export_color_remap_onnx(
    mapping: dict[int, int],
    output_path: str | Path,
    *,
    grid_size: int = 30,
    num_colors: int = 10,
    opset_version: int = 18,
) -> Path:
    return export_program_onnx(
        make_color_remap_program(mapping),
        output_path,
        grid_size=grid_size,
        num_colors=num_colors,
        opset_version=opset_version,
    )
