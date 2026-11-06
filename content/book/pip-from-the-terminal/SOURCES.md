# Source Ledger

All web sources below were reachable and checked on 2026-10-28. The manuscript
paraphrases them; it does not reproduce their documentation. Version-specific
claims were also checked against local `python -m pip help` output from Python
3.12.10 and pip 26.2.2.

## pip and Python packaging

- **S1 — pip 26.2.2 project release.** Version and release metadata.
  https://pypi.org/project/pip/
- **S2 — pip User Guide.** Interpreter management, requirements files, and
  general command behavior. https://pip.pypa.io/en/stable/user_guide/
- **S3 — pip install.** Install inputs, upgrade strategy, dependency groups,
  PEP 723 script requirements, and the `--extra-index-url` dependency-confusion
  warning. https://pip.pypa.io/en/stable/cli/pip_install/
- **S4 — pip wheel.** Wheel-building inputs and current options including build
  constraints, dependency groups, PEP 723 scripts, hashes, `--only-deps`, and
  upload-time filtering. https://pip.pypa.io/en/stable/cli/pip_wheel/
- **S5 — pip lock.** Experimental native lock command and `pylock.toml` output.
  https://pip.pypa.io/en/stable/cli/pip_lock/
- **S6 — Repeatable installs.** Pinning, hashes, and wheelhouse installation
  bundles. https://pip.pypa.io/en/stable/topics/repeatable-installs/
- **S7 — Secure installs.** Hash-checking mode and binary-only installs.
  https://pip.pypa.io/en/stable/topics/secure-installs/
- **S8 — Installing Packages.** PyPA beginner workflow and platform launchers.
  https://packaging.python.org/en/latest/tutorials/installing-packages/
- **S9 — Writing pyproject.toml.** Build-system and project metadata guidance.
  https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- **S10 — Dependency Groups specification.** Standardized development groups
  that are not included in built project metadata.
  https://packaging.python.org/en/latest/specifications/dependency-groups/
- **S11 — pylock.toml specification.** Standard lock-file name and reproducible
  environment data model.
  https://packaging.python.org/en/latest/specifications/pylock-toml/
- **S12 — Python venv.** Creation, activation, interpreter paths, and the rule
  that environments should be recreated instead of moved.
  https://docs.python.org/3/library/venv.html
- **S13 — Inline script metadata.** Canonical PyPA specification reached from
  PEP 723. https://packaging.python.org/en/latest/specifications/inline-script-metadata/
- **S14 — Wheel documentation.** Wheel format and command-line project guide.
  https://wheel.readthedocs.io/en/stable/

## Open-source companion terminal guides

- **S15 — pipx.** Isolated installation and execution of Python applications.
  https://pipx.pypa.io/stable/
- **S16 — pip-tools 7.6.2.** `pip-compile` and `pip-sync` workflows.
  https://pip-tools.pypa.io/en/stable/
- **S17 — build 1.6.1.** Standards-based source and wheel builds.
  https://build.pypa.io/en/stable/
- **S18 — Twine 7.0.0.** Distribution checks and uploads.
  https://twine.readthedocs.io/en/stable/
- **S19 — virtualenv.** Alternative virtual-environment implementation.
  https://virtualenv.pypa.io/en/latest/
- **S20 — pip-audit.** PyPA vulnerability audit tool and automatic-fix option.
  https://pypa.github.io/pip-audit/
- **S21 — Packaging Python Projects.** End-to-end PyPA package tutorial.
  https://packaging.python.org/en/latest/tutorials/packaging-projects/

## Amazon KDP

- **K1 — Paperback submission guidelines.** PDF, image resolution, bleed, and
  spine-text rules. https://kdp.amazon.com/help/topic/G201857950
- **K2 — Trim size and margins.** 6 x 9 availability, page ranges, and gutter
  guidance. https://kdp.amazon.com/help/topic/GVBQ3CMEQW3W2VL6
- **K3 — eBook manuscript formats.** EPUB and DOCX support.
  https://kdp.amazon.com/en_US/help/topic/G200634390
- **K4 — Upload and preview.** KDP upload steps and print/online previewers.
  https://kdp.amazon.com/en_US/help/topic/G200641240
- **K5 — Kindle Previewer.** Supported formats and device preview workflow.
  https://kdp.amazon.com/en_US/help/topic/G202131170
- **K6 — AI content disclosure.** KDP definitions of AI-generated and
  AI-assisted content. https://kdp.amazon.com/help/topic/G200672390
- **K7 — Official cover calculator and template generator.** Final cover
  dimensions after page count is locked. https://kdp.amazon.com/cover-calculator
