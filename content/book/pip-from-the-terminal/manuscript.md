# pip from the Terminal

## Introduction. Name the Interpreter First

Most pip failures begin one command earlier than the error message. Someone
types `pip install`, sees a successful download, opens Python, and cannot import
the package. The installer worked. It changed a different Python.

This book uses one rule to prevent that class of mistake:

```text
Run pip through the Python interpreter you intend to change.
```

On Windows, that usually means `py -m pip` or
`.venv\Scripts\python.exe -m pip`. On macOS and Linux, it usually means
`python3 -m pip` or `.venv/bin/python -m pip`. Once a virtual environment is
active, `python -m pip` is the shortest reliable form.

The examples were checked on October 28, 2026, with Python 3.12.10 and pip
26.2.2. That release includes commands and options older installations lack:
the experimental `pip lock` command, dependency groups, PEP 723 script
requirements, build constraints, and newer wheel-selection controls. Every
version-sensitive section points to official documentation in the Sources
chapter.

This is a working guide, not a dump of `--help`. It follows the jobs a person
does at a terminal: identify Python, create an environment, install and inspect
packages, record dependencies, build wheels, make installs stricter, package a
project, and diagnose the layer that failed.

## Chapter 1. Python, pip, and the Environment in Front of You

pip installs Python distributions. Python imports modules. A distribution name
and an import name can differ: `Pillow` provides `PIL`, and
`beautifulsoup4` provides `bs4`. pip also resolves declared dependencies,
downloads archives, builds projects when needed, and writes files into an
environment's installation scheme.

pip does not choose the correct Python on your behalf. One machine may contain
a Microsoft Store alias, a python.org installation, Conda, an IDE-managed
interpreter, and several virtual environments. The shell resolves a command
name first. The interpreter then decides which site-packages directory and pip
module belong to it.

### The identity check

Run these commands before changing an unfamiliar machine:

```powershell
python --version
python -c "import sys; print(sys.executable)"
python -m pip --version
python -m site
python -m pip config debug
```

The first line names the language version. The second prints the executable
path. The third prints pip's version and import location. The fourth shows
Python's site directories. The fifth shows pip configuration files and loaded
values.

On Windows, list registered interpreters with the Python launcher:

```powershell
py -0p
py -3.12 -c "import sys; print(sys.executable)"
py -3.12 -m pip --version
```

On macOS or Linux:

```bash
command -v python3
python3 -c 'import sys; print(sys.executable)'
python3 -m pip --version
```

The paths should tell one coherent story. If Python and pip point to different
trees, stop and use an explicit interpreter path.

### Why `python -m pip` is safer

The bare `pip` command is a launcher script. Its path may be stale or may
resolve before the intended Python on PATH. `python -m pip` asks the selected
Python process to import and run its own pip module.

pip also has a `--python` option:

```powershell
python -m pip --python .venv install requests
```

The explicit interpreter form is easy to audit:

```powershell
.venv\Scripts\python.exe -m pip install requests
```

### Read errors in layers

- Shell resolution: the command was not found or pointed at the wrong file.
- Python startup: the interpreter or standard library is damaged.
- pip configuration: an index, proxy, certificate, or environment variable
  changed network behavior.
- Dependency resolution: requested versions cannot coexist.
- Build isolation: build dependencies failed before the project built.
- Native compilation: a compiler, header, SDK, or system library is absent.
- Installation: files cannot be written or another process holds them.
- Import time: installation finished, but runtime code cannot load.

Collect the interpreter path, pip version, exact command, and complete error
before changing anything.

## Chapter 2. Virtual Environments You Can Recreate

A virtual environment gives one project its own package directory and command
launchers. It does not create a new operating system or make untrusted packages
safe. Its value is separation and recreation.

PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip --version
```

Command Prompt:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
```

bash and zsh:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip --version
```

Activation prepends the environment's command directory to PATH. Automation is
clearer when it calls the interpreter directly:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Python's documentation says virtual environments are not movable or copyable
in the general case because generated scripts contain absolute interpreter
paths. Recreate an environment from declared inputs instead of moving
`.venv` to another machine. [S12]

If PowerShell policy blocks `Activate.ps1`, activation is optional:

```powershell
.venv\Scripts\python.exe -m pip --version
```

Add `.venv/` to version-control ignore rules. Commit the metadata,
requirements, constraints, or lock files that can recreate it.

The standard-library `venv` module is enough for most projects. The
open-source `virtualenv` project adds discovery, seeding, and compatibility
features. Choose it for those features, not by reflex. [S19]

## Chapter 3. Install, Upgrade, Inspect, and Remove

An install command has a target interpreter, an operation, and a requirement:

```powershell
python -m pip install requests
```

The requirement can be a name, version range, local directory, archive, VCS
URL, requirements file, dependency group, lock file, or PEP 723 script.

### Version specifiers

```powershell
python -m pip install "requests>=2.32,<3"
python -m pip install "Django~=5.2.0"
python -m pip install "rich==14.2.0"
```

Quote comparison operators so the shell does not interpret them. Exact pins
are useful for controlled applications. Ranges are often better in reusable
library metadata.

### Local projects

```powershell
python -m pip install .
python -m pip install --editable .
```

Editable mode connects development imports to the source tree. Test a regular
wheel before release; editable success does not prove the built package
contains every required file.

### Upgrade with intent

```powershell
python -m pip install --upgrade requests
python -m pip install --upgrade --upgrade-strategy eager requests
```

The default strategy is `only-if-needed`. `eager` permits broader dependency
upgrades. Broader movement requires broader tests. [S3]

### Inspect the result

```powershell
python -m pip show requests
python -m pip list
python -m pip list --outdated
python -m pip check
python -m pip inspect > environment.json
```

`show` answers questions about one distribution. `list` shows the
environment. `check` verifies installed dependency compatibility. `inspect`
emits machine-readable JSON.

Confirm import identity from Python:

```powershell
python -c "import requests; print(requests.__version__)"
python -c "import requests; print(requests.__file__)"
```

Remove a distribution and recheck the environment:

```powershell
python -m pip uninstall requests
python -m pip check
```

pip does not decide that every former dependency is now unused. Disposable
environments are cleaner when recreated from declared inputs.

## Chapter 4. Requirements, Constraints, Groups, and Scripts

A requirements file is a pip input:

```text
# requirements.in
requests>=2.32,<3
rich>=14,<15
```

```powershell
python -m pip install -r requirements.in
```

`pip freeze` reports installed distributions in requirements syntax:

```powershell
python -m pip freeze > requirements-frozen.txt
```

A freeze is a snapshot, not a statement of design intent. It may contain
transitive, platform-specific, and incidental packages.

### Constraints

A constraints file limits versions selected for other requirements. Naming a
package there does not request its installation.

```text
# constraints.txt
urllib3==2.5.0
certifi>=2026.8.3
```

```powershell
python -m pip install -c constraints.txt -r requirements.in
```

Record why unusual constraints exist and which test permits their removal.

### Dependency groups

The standardized `[dependency-groups]` table stores development requirements
without adding them to built project metadata. [S10]

```toml
[dependency-groups]
test = ["pytest>=9,<10", "coverage[toml]>=7,<8"]
docs = ["sphinx>=8,<9"]
quality = [
  { include-group = "test" },
  "ruff>=0.14,<0.15",
]
```

pip 26.2.2 installs named groups:

```powershell
python -m pip install --group test
python -m pip install --group quality
```

Groups describe requirement sets. They do not lock every selected artifact.

### PEP 723 inline metadata

A single Python script can declare its Python range and dependencies. The
canonical format is maintained by PyPA. [S13]

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "requests>=2.32,<3",
#   "rich>=14,<15",
# ]
# ///

import requests
from rich import print

print(requests.get("https://example.com", timeout=10).status_code)
```

pip 26.2.2 installs those requirements:

```powershell
python -m pip install --requirements-from-script demo.py
```

That command installs dependencies; it does not run the script. Read an
untrusted script before installing anything it names.

## Chapter 5. Lock Files and Their Boundary

pip 26.2.2 includes the experimental `pip lock` command. Its default output is
`pylock.toml`, the standard filename defined by PyPA. [S5, S11]

```powershell
python -m pip lock -r requirements.in -o pylock.toml
python -m pip lock -e . -o pylock.toml
```

Install support for `pylock.toml` is also marked experimental:

```powershell
python -m pip install -r pylock.toml
```

Record the pip version that created the file, review diffs, and test a clean
install. A lock still has a target: Python version, operating system, CPU,
implementation, ABI, and environment markers can change valid artifacts. One
Windows lock is not proof for Linux or macOS.

### A reproducibility ladder

1. Direct requirements record intent but allow future compatible releases.
2. Exact pins reduce version movement.
3. Complete transitive resolution records more of the environment.
4. Hashes bind requirements to approved archives.
5. A wheelhouse preserves built artifacts for a platform.
6. A lock records structured artifacts, markers, and hashes.
7. A clean-room install test proves those inputs work now.

The open-source pip-tools project provides `pip-compile` and `pip-sync`.
Teams with a tested compile-and-sync workflow need not switch to an experimental
native command merely because it exists. [S16]

## Chapter 6. Wheels and `pip wheel`

A wheel is a built distribution archive. Installing a compatible wheel avoids
building the project from source on every target. Wheels can be pure Python or
specific to an implementation, ABI, operating system, and architecture. [S14]

Build requirements into a wheelhouse:

```powershell
python -m pip wheel -r requirements.txt --wheel-dir wheelhouse
```

Build the current project, with or without dependencies:

```powershell
python -m pip wheel . --wheel-dir dist
python -m pip wheel . --no-deps --wheel-dir dist
```

Install without contacting an index:

```powershell
python -m pip install --no-index --find-links wheelhouse -r requirements.txt
```

### Current wheel inputs

pip 26.2.2 accepts requirement specifiers, requirements files, VCS projects,
local projects, and archives. It also accepts dependency groups and PEP 723
script metadata:

```powershell
python -m pip wheel --group build -w wheelhouse
python -m pip wheel --requirements-from-script demo.py -w wheelhouse
```

`--only-deps` builds only dependencies of a supplied target. It cannot be
combined with `--no-deps`, `--group`, `--requirement`, or
`--requirements-from-script` in this release.

```powershell
python -m pip wheel --only-deps . -w wheelhouse
```

### Build isolation and constraints

Modern source builds normally run in an isolated environment populated from
`[build-system].requires`.

```powershell
python -m pip wheel . --build-constraint build-constraints.txt -w wheelhouse
```

A build constraint limits packages used to prepare the build. It is separate
from runtime requirements.

`--no-build-isolation` makes the caller provide every build dependency:

```powershell
python -m pip wheel . --no-build-isolation -w wheelhouse
```

That can help in a controlled offline image. It can also make a build depend on
undeclared machine state.

### Selection controls

- `--only-binary :all:` refuses source distributions.
- `--no-binary :all:` forces source distributions.
- `--prefer-binary` prefers wheels over newer source releases.
- `--pre` permits prereleases.
- `--all-releases` and `--only-final` add release-type controls.
- `--uploaded-prior-to` sets an upload-time boundary when the index exposes
  metadata.
- `--refresh-package` refreshes index data for named packages.

```powershell
python -m pip wheel -r requirements.txt --uploaded-prior-to 2026-10-01T00:00:00Z -w wheelhouse
```

pip validates built wheels by default. `--no-verify` disables that check and
should not be a routine speed switch. `--no-clean` preserves build directories
for diagnosis but leaves state behind.

## Chapter 7. Repeatable and Safer Installs

Exact versions answer “which release?” Hashes answer “which archive?” A
wheelhouse answers “which already-built files are available here?”

### Hash-checking mode

```text
requests==2.32.5 \
  --hash=sha256:REPLACE_WITH_APPROVED_ARCHIVE_HASH
```

```powershell
python -m pip install --require-hashes -r requirements-hashed.txt
```

Hash-checking mode requires every requirement and transitive dependency to be
pinned and hashed. Multiple hashes may cover approved wheels for several
platforms. The official secure-install guide pairs `--require-hashes` with
`--only-binary :all:` when source builds are forbidden. [S7]

```powershell
python -m pip install --require-hashes --only-binary :all: -r requirements-hashed.txt
```

Compute a local archive hash:

```powershell
python -m pip hash wheelhouse\some_package-1.2.3-py3-none-any.whl
```

Build and test an offline wheelhouse:

```powershell
python -m pip wheel -r requirements-hashed.txt --require-hashes -w wheelhouse
py -3.12 -m venv .venv-offline
.venv-offline\Scripts\python.exe -m pip install --no-index --find-links wheelhouse --require-hashes -r requirements-hashed.txt
.venv-offline\Scripts\python.exe -m pip check
```

Wheelhouses with native extensions are usually platform-specific. Label them
with Python version, platform, architecture, and build date. [S6]

### Index safety

pip evaluates candidates from indexes and `--find-links` locations together.
The pip install documentation warns that `--extra-index-url` for private
packages is unsafe because a public package with the same name can win through
dependency confusion. [S3]

Prefer one controlled index that proxies approved public packages and hosts
private ones. If separate sources are unavoidable, use unique private names,
strict pins, hashes, and repository policy. Do not use `--trusted-host` to
silence a certificate error; repair the chain or configure the approved CA.

### Vulnerability audits

pip resolves compatibility; it is not a vulnerability database. pip-audit
checks environments or requirements against known advisories. [S20]

```powershell
python -m pip install pip-audit
python -m pip_audit
python -m pip_audit -r requirements.txt
```

Automatic fixes still require tests:

```powershell
python -m pip_audit --fix
python -m pip check
python -m pytest
```

No known finding is not proof that every package is safe. Provenance,
maintainer compromise, malicious releases, and undisclosed vulnerabilities are
separate risks.

## Chapter 8. Build and Check Your Own Package

A modern project declares its backend and metadata in `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "hello-terminal"
version = "0.1.0"
description = "A small packaging example"
readme = "README.md"
requires-python = ">=3.12"
license = "MIT"
authors = [{ name = "Your Name" }]
dependencies = []

[project.scripts]
hello-terminal = "hello_terminal:main"

[tool.setuptools]
package-dir = { "" = "src" }

[tool.setuptools.packages.find]
where = ["src"]
```

The module:

```python
# src/hello_terminal/__init__.py
def main() -> None:
    print("hello from an installed command")
```

Build and check distributions:

```powershell
python -m pip install build twine
python -m build
python -m twine check dist\*
python -m pip install --force-reinstall dist\hello_terminal-0.1.0-py3-none-any.whl
hello-terminal
```

Test the wheel in a clean environment, not only beside the source tree. The
PyPA packaging tutorial and build and Twine docs maintain the release workflow.
[S17, S18, S21]

Upload to TestPyPI before production:

```powershell
python -m twine upload --repository testpypi dist\*
```

Never place an API token in a command, source tree, screenshot, or shell
history.

### Isolated Python applications

Tools such as Ruff and HTTPie are applications. Installing every app into one
global Python creates dependency collisions. pipx gives each app an isolated
environment and exposes its commands on PATH. [S15]

```powershell
python -m pip install --user pipx
python -m pipx ensurepath
pipx install ruff
pipx run cowsay "temporary command"
```

Use project environments for project dependencies and pipx for standalone
applications. Keep global interpreter modification rare.

## Chapter 9. Diagnose Without Random Upgrades

Start with facts:

```powershell
python -c "import sys, platform; print(sys.executable); print(platform.platform())"
python -m pip --version
python -m pip config debug
python -m pip debug --verbose
python -m pip check
```

Re-run with verbosity:

```powershell
python -m pip install -vvv package-name
```

Verbose output can contain private URLs, usernames, paths, or tokens. Redact it
before posting.

### No matching distribution

Check the name, requested version, `Requires-Python`, prerelease status, wheel
tags, index configuration, and upload-time boundaries.

```powershell
python -m pip index versions package-name
python -m pip debug --verbose
```

### Build backend failed

Look above the final failure line for the backend, compiler invocation, missing
header, and isolated build requirements.

```powershell
python -m pip wheel -vvv . -w diagnostic-wheelhouse
```

Do not disable build isolation first. If `--no-build-isolation` changes the
result, compare declared build requirements with the machine state.

### SSL, access, and import failures

For certificate failures, confirm system time, proxy behavior, interception,
and CA configuration. Use `--cert` for an approved CA bundle. Avoid permanent
`--trusted-host` settings.

For access errors, close Python processes holding package files and create a
fresh user-owned environment before escalating privileges.

If installation succeeded but import fails:

```powershell
python -m pip show package-name
python -c "import sys; print(*sys.path, sep='\n')"
python -c "import import_name; print(import_name.__file__)"
```

Check whether a local file such as `requests.py` or `typing.py` shadows the
installed package.

### Recreate instead of excavating

```powershell
py -3.12 -m venv .venv-new
.venv-new\Scripts\python.exe -m pip install -r requirements.txt
.venv-new\Scripts\python.exe -m pip check
.venv-new\Scripts\python.exe -m pytest
```

Switch only after tests pass. Keep the old environment until comparison is
complete.

## Chapter 10. Working Recipes

Start a small project:

```powershell
New-Item -ItemType Directory my-app
Set-Location my-app
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install requests
python -m pip freeze > requirements-frozen.txt
python -m pip check
```

Install only wheels:

```powershell
python -m pip install --only-binary :all: -r requirements.txt
```

Download without installing:

```powershell
python -m pip download -r requirements.txt -d downloads
```

Build and use a wheelhouse:

```powershell
python -m pip wheel -r requirements.txt -w wheelhouse
python -m pip install --no-index --find-links wheelhouse -r requirements.txt
```

Check before release:

```powershell
python -m pip check
python -m pip list --outdated
python -m pip_audit
python -m pytest
```

“Outdated” does not mean broken. Upgrade through a reviewed change.

Read help from the installed pip:

```powershell
python -m pip help
python -m pip install --help
python -m pip wheel --help
python -m pip lock --help
```

Installed help governs the executable in front of you. If online stable docs
describe a different version, use the versioned docs for your local command.

## Appendix A. Command Map

- `install` resolves and installs requirements.
- `lock` generates an experimental `pylock.toml`.
- `download` fetches distributions without installing.
- `uninstall` removes named distributions.
- `freeze` prints installed distributions in requirements syntax.
- `inspect` emits a JSON environment report.
- `list` lists installed or outdated distributions.
- `show` displays distribution metadata and location.
- `check` verifies declared dependency compatibility.
- `config` manages pip configuration.
- `cache` inspects and manages pip's cache.
- `index` inspects package-index information.
- `wheel` builds wheels.
- `hash` computes archive hashes.
- `completion` helps configure shell completion.
- `debug` reports interpreter and compatibility data.
- `help` shows command help.

pip 26.2.2 also lists `search`. Index-side search support has changed over
pip's history, so test the target index and version before automating it.

## Appendix B. Platform Equivalents

```text
Create:
  Windows       py -3.12 -m venv .venv
  macOS/Linux   python3 -m venv .venv

Activate:
  PowerShell    .venv\Scripts\Activate.ps1
  cmd.exe       .venv\Scripts\activate.bat
  bash/zsh      source .venv/bin/activate

Run without activation:
  Windows       .venv\Scripts\python.exe -m pip --version
  macOS/Linux   .venv/bin/python -m pip --version
```

## Sources and Version Boundary

Checked October 28, 2026:

- [S1] pip 26.2.2: https://pypi.org/project/pip/
- [S2] pip User Guide: https://pip.pypa.io/en/stable/user_guide/
- [S3] pip install: https://pip.pypa.io/en/stable/cli/pip_install/
- [S4] pip wheel: https://pip.pypa.io/en/stable/cli/pip_wheel/
- [S5] pip lock: https://pip.pypa.io/en/stable/cli/pip_lock/
- [S6] Repeatable installs:
  https://pip.pypa.io/en/stable/topics/repeatable-installs/
- [S7] Secure installs:
  https://pip.pypa.io/en/stable/topics/secure-installs/
- [S8] Installing Packages:
  https://packaging.python.org/en/latest/tutorials/installing-packages/
- [S9] Writing pyproject.toml:
  https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- [S10] Dependency Groups:
  https://packaging.python.org/en/latest/specifications/dependency-groups/
- [S11] pylock.toml:
  https://packaging.python.org/en/latest/specifications/pylock-toml/
- [S12] Python venv: https://docs.python.org/3/library/venv.html
- [S13] Inline script metadata:
  https://packaging.python.org/en/latest/specifications/inline-script-metadata/
- [S14] Wheel: https://wheel.readthedocs.io/en/stable/
- [S15] pipx: https://pipx.pypa.io/stable/
- [S16] pip-tools: https://pip-tools.pypa.io/en/stable/
- [S17] build: https://build.pypa.io/en/stable/
- [S18] Twine: https://twine.readthedocs.io/en/stable/
- [S19] virtualenv: https://virtualenv.pypa.io/en/latest/
- [S20] pip-audit: https://pypa.github.io/pip-audit/
- [S21] Packaging Python Projects:
  https://packaging.python.org/en/latest/tutorials/packaging-projects/

KDP production sources:

- Paperback submission: https://kdp.amazon.com/help/topic/G201857950
- Trim sizes: https://kdp.amazon.com/help/topic/GVBQ3CMEQW3W2VL6
- eBook formats: https://kdp.amazon.com/en_US/help/topic/G200634390
- Upload and preview: https://kdp.amazon.com/en_US/help/topic/G200641240
- Kindle Previewer: https://kdp.amazon.com/en_US/help/topic/G202131170
- AI disclosure: https://kdp.amazon.com/help/topic/G200672390
- Cover calculator: https://kdp.amazon.com/cover-calculator

The command surface will change. Before relying on a newer pip, run
`python -m pip --version`, read the installed help, and check the versioned
official documentation. The interpreter path remains the first fact to verify.
