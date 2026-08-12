from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def _uses_external_data(src: Path) -> bool:
    import onnx

    model = onnx.load(str(src), load_external_data=False)
    return any(any(field.key == "location" for field in tensor.external_data) for tensor in model.graph.initializer)


#: A canonical competition key is a task number, optionally prefixed with "task".
#: Anything else -- notably an ARC task HASH like "136b0064" -- is not addressable here.
_CANONICAL_KEY = re.compile(r"^(?:task[_-]?)?(\d{1,4})$", re.IGNORECASE)


def canonical_task_filename(task_id: str) -> str:
    """Map a competition key to its submission filename, rejecting anything that is not one.

    The previous implementation stripped every non-digit and packed whatever was left:
    ``"136b0064"`` -- an ARC task hash -- lost its ``b`` and became ``task1360064.onnx``. That
    is not an error the submission process can survive, because the file is written under a
    task number that does not exist and the whole zip is silently wrong. It only looked safe
    because the guard checked "are there any digits at all", which a hash always satisfies.

    Args:
        task_id: A canonical key, e.g. ``"task001"``, ``"task_12"`` or ``"7"``.

    Returns:
        The ``taskNNN.onnx`` filename.

    Raises:
        ValueError: If ``task_id`` is not a canonical competition key.
    """
    match = _CANONICAL_KEY.match(str(task_id).strip())
    if not match:
        raise ValueError(
            f"Task ID {task_id!r} is not a canonical competition key. Expected a task number "
            "(e.g. 'task001', 'task_12', '7'); an ARC task hash cannot be mapped to a "
            "submission filename."
        )
    return f"task{int(match.group(1)):03d}.onnx"


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
