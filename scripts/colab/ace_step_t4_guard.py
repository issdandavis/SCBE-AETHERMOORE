"""ACEStep T4 memory guard for Colab.

Paste or run this before loading ACEStep on a Colab T4. It does not load the
model by itself; it sets the allocator and clears stale CUDA cache, then exposes
safe defaults for constructing the pipeline.
"""

from __future__ import annotations

import gc
import os


def apply_t4_guard() -> dict[str, object]:
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    info: dict[str, object] = {
        "allocator": os.environ.get("PYTORCH_CUDA_ALLOC_CONF"),
        "cuda": False,
        "device": None,
        "free_gb": None,
        "total_gb": None,
    }

    gc.collect()

    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            free, total = torch.cuda.mem_get_info()
            info.update(
                {
                    "cuda": True,
                    "device": torch.cuda.get_device_name(0),
                    "free_gb": round(free / 1024**3, 2),
                    "total_gb": round(total / 1024**3, 2),
                }
            )
    except Exception as exc:  # keep notebook preflight diagnostic, do not hide it
        info["torch_error"] = f"{type(exc).__name__}: {exc}"

    print("SCBE_ACE_T4_GUARD", info)
    return info


def ace_step_t4_kwargs(**overrides: object) -> dict[str, object]:
    """Return stable defaults for ACEStepPipeline on Colab T4."""
    kwargs: dict[str, object] = {
        "dtype": "bfloat16",
        "torch_compile": False,
        "cpu_offload": True,
        "overlapped_decode": False,
    }
    kwargs.update(overrides)
    return kwargs


if __name__ == "__main__":
    apply_t4_guard()
    print("SCBE_ACE_T4_KWARGS", ace_step_t4_kwargs())
