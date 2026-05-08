"""SCBE CLI parameter-binding framework.

Lifts PowerShell's `[Parameter()]` + `ParameterSetName` + `Validate*`
attribute pattern onto pydantic models so subcommands declare their
contract in one place and argparse, validation, and `--help` all derive
from it.
"""

from .param_binding import (  # noqa: F401
    BoundCommand,
    ParameterSetError,
    bind_subparser,
)
