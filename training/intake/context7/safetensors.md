# SafeTensors
> Source: Context7 MCP | Category: science
> Fetched: 2026-04-04

### Safetensors File Format Specification

Source: https://github.com/huggingface/safetensors/blob/main/safetensors/README.md

Detailed specification of the safetensors file format, outlining the structure of the header, JSON metadata, data offsets, and general notes on tensor representation. This defines how tensors are stored safely and efficiently, ensuring zero-copy loading.

```
File Format:
- 8 bytes: N, an unsigned little-endian 64-bit integer, containing the size of the header
- N bytes: a JSON UTF-8 string representing the header.
  - The header data MUST begin with a { character (0x7B).
  - The header data MAY be trailing padded with whitespace (0x20).
  - The header is a dict like:
    {"TENSOR_NAME": {"dtype": "F16", "shape": [1, 16, 256], "data_offsets": [BEGIN, END]}, ...}
  - data_offsets point to the tensor data relative to the beginning of the byte buffer
    with BEGIN as the starting offset and END as the one-past offset
  - A special key __metadata__ is allowed to contain free form string-to-string map.
- Rest of the file: byte-buffer.

Notes:
 - Duplicate keys are disallowed.
 - Tensor values are not checked against (NaN and +/-Inf could be in the file)
 - Empty tensors (tensors with 1 dimension being 0) are allowed.
 - 0-rank Tensors (tensors with shape []) are allowed (scalars).
 - The byte buffer needs to be entirely indexed, and cannot contain holes.
 - Endianness: Little-endian.
 - Order: 'C' or row-major.
```

---

### Comparison of ML Data Formats

Source: https://github.com/huggingface/safetensors/blob/main/README.md

| Format | Safe | Zero-copy | Lazy loading | No file size limit | Layout control | Flexibility | Bfloat16/Fp8 |
|---|---|---|---|---|---|---|---|
| pickle (PyTorch) | No | No | No | Yes | No | Yes | Yes |
| H5 (Tensorflow) | Yes | No | Yes | Yes | ~ | ~ | No |
| SavedModel (Tensorflow) | Yes | No | No | Yes | Yes | No | Yes |
| MsgPack (flax) | Yes | Yes | No | Yes | No | No | Yes |
| Protobuf (ONNX) | Yes | No | No | No | No | No | Yes |
| Cap'n'Proto | Yes | Yes | ~ | Yes | Yes | ~ | No |
| Numpy (npy,npz) | Yes | ? | ? | No | Yes | No | No |
| SafeTensors | Yes | Yes | Yes | Yes | Yes | No | Yes |

---

### Save Tensors to Safetensors File

Source: https://github.com/huggingface/safetensors/blob/main/docs/source/index.mdx

Shows how to save a collection of PyTorch tensors from a Python dictionary into a .safetensors file.

```python
import torch
from safetensors.torch import save_file

tensors = {
    "embedding": torch.zeros((2, 2)),
    "attention": torch.zeros((2, 3))
}
save_file(tensors, "model.safetensors")
```

---

### Save and Load NumPy Tensors with safetensors

Source: https://github.com/huggingface/safetensors/blob/main/bindings/python/README.md

Demonstrates how to serialize NumPy arrays into a `.safetensors` file and then deserialize them back into memory.

```python
from safetensors.numpy import save_file, load_file
import numpy as np

tensors = {
   "a": np.zeros((2, 2)),
   "b": np.zeros((2, 3), dtype=np.uint8)
}

save_file(tensors, "./model.safetensors")

# Now loading
loaded = load_file("./model.safetensors")
```
