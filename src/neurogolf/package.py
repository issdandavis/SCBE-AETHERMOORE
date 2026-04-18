from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def _uses_external_data(src: Path) -> bool:
    import onnx

    model = onnx.load(str(src), load_external_data=False)
    return any(
        any(field.key == "location" for field in tensor.external_data)
        for tensor in model.graph.initializer
    )


def canonical_task_filename(task_id: str) -> str:
    digits = "".join(ch for ch in task_id if ch.isdigit())
    if not digits:
        raise ValueError(f"Task ID '{task_id}' does not contain digits")
    return f"task{int(digits):03d}.onnx"


def build_submission_zip(task_to_onnx: dict[str, str | Path], output_zip: str | Path) -> Path:
    output_zip = Path(output_zip)
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_zip, "w", compression=ZIP_DEFLATED) as zf:
        for task_id, file_path in sorted(task_to_onnx.items()):
            src = Path(file_path)
            sidecar = src.with_name(src.name + ".data")
            if sidecar.exists() and _uses_external_data(src):
                raise ValueError(
                    f"Refusing to package external-data ONNX sidecar for {src}. "
                    "NeuroGolf submissions need single-file ONNX artifacts."
                )
            zf.write(src, arcname=canonical_task_filename(task_id))
    return output_zip
