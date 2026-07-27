"""Marks `python/` as an explicit package so `python.scbe` resolves deterministically.

Without this file `python/` is an IMPLICIT NAMESPACE PACKAGE (PEP 420), resolved by
scanning every `sys.path` entry for a matching directory. That is ambiguous in exactly the
place it matters: PyInstaller's static analysis. All three platforms logged

    WARNING: collect_data_files - skipping data collection for module 'python.scbe'
             as it is not a package.

and on the macOS runner the built binary then died with
`ModuleNotFoundError: No module named 'python.scbe'` while Linux and Windows happened to
work. macOS's filesystem is case-insensitive by default, so a lookup for `python` can match
the interpreter's own `Python` directory in the hosted tool cache before it ever reaches the
repository's `python/`. An explicit `__init__.py` removes the ambiguity for every tool on
every platform — nothing has to guess which directory was meant.

This does not change how the package is imported (`python.scbe` either way), and setup.py's
`find_namespace_packages` finds regular packages too, so the wheel is unaffected.
"""
