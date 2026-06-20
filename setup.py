"""Dynamic package discovery for the mixed src/ + python.scbe layout.

Metadata, deps, and entry points live in pyproject.toml. This handles the one thing
a static [tool.setuptools.packages.find] can't: ship BOTH the src-layout packages
(installed by their bare name, e.g. `crypto`) AND the cube engine at python/scbe/
(imported as `python.scbe`). A single find rooted at "." would name-collide with the
duplicate root packages (symphonic_cipher/, api/), so we run two finds and merge.
"""

from setuptools import find_namespace_packages, find_packages, setup

SRC_INCLUDE = [
    "neurogolf*", "scbe_aethermoore*", "code_prism*", "flow_router*",
    "symphonic_cipher*", "api*", "crypto*", "harmonic*", "spiralverse*",
    "minimal*", "storage*",
]
SRC_EXCLUDE = [
    "tests*", "agents*", "training*", "scripts*", "*.tests", "*.tests.*",
    "api.github_app*", "api.billing*", "api.keys*", "symphonic_cipher.geoseal*",
]

# src-layout packages (installed by bare name, mapped back to src/)
src_pkgs = find_packages("src", include=SRC_INCLUDE, exclude=SRC_EXCLUDE)
# the cube engine — a namespace package so python/ needs no __init__.py; the tight
# include keeps the root-package collisions out.
engine_pkgs = find_namespace_packages(".", include=["python.scbe", "python.scbe.*"])

package_dir = {p: "src/" + p.replace(".", "/") for p in src_pkgs}
package_dir["python.scbe"] = "python/scbe"

setup(
    py_modules=["scbe"],                       # the CLI entry (scbe.py at repo root)
    packages=src_pkgs + engine_pkgs,
    package_dir=package_dir,
    package_data={"python.scbe": ["*.json", "data/*"]},
    include_package_data=True,
)
