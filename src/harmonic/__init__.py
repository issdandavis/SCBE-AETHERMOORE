"""SCBE harmonic package — 14-layer pipeline reference modules.

This marker file makes ``src/harmonic`` a real package so setuptools'
``find_packages("src", include=[..., "harmonic*", ...])`` (see setup.py)
actually discovers and ships the ``harmonic.*`` modules on ``pip install .``.
Without it the directory is skipped and ``from harmonic.<module> import ...``
fails post-install with ModuleNotFoundError.
"""
