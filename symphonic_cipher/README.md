# symphonic_cipher/

The **root** `symphonic_cipher` Python package.

There are two packages with this name and they compute different things:

| Location | Formula | Meaning |
|----------|---------|---------|
| `symphonic_cipher/` (this folder) | `H(d, R) = R^(d²)` | Unbounded cost multiplier |
| `src/symphonic_cipher/` | `H(d, pd) = 1 / (1 + d + 2·pd)` | Bounded safety score in (0, 1] |

Many tests insert `src/` at the front of `sys.path`, which makes `import symphonic_cipher` resolve to the other one. Check at runtime:

```python
import symphonic_cipher
symphonic_cipher._VARIANT          # "root" here, "src" for the other
symphonic_cipher._IS_SAFETY_SCORE  # False here, True for the other
```

Contents: `scbe_aethermoore/` (74 files, the reference implementation), `geoseal/`, and `tests/`.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/symphonic_cipher.md`](../docs/file-index/symphonic_cipher.md).
