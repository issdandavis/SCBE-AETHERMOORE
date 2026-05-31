"""Run flake8 without the Windows WMI platform probe hanging startup."""

from __future__ import annotations

import sys

import flake8.utils


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--jobs" not in args and "-j" not in args:
        args = ["--jobs", "1", *args]

    flake8.utils.platform.system = lambda: "Windows"

    from flake8.main.cli import main as flake8_main

    return flake8_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
