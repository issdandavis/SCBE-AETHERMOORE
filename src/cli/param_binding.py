"""PowerShell-style parameter binding for SCBE CLI subcommands.

Subcommands declare their full contract as a pydantic `BoundCommand`
subclass: required vs optional fields, `Literal[...]` for `ValidateSet`,
`Field(ge=, le=)` for `ValidateRange`, `Field(pattern=)` for
`ValidatePattern`, and a `model_config["parameter_sets"]` mapping for
mutually-exclusive sets (PowerShell `ParameterSetName`). The framework
then derives the argparse subparser, validation, and `--help` text from
the model.

What this is and is not
-----------------------
This is the migration target for the existing argparse-everywhere
geoseal_cli. It is *not* a wholesale rewrite — register a new subcommand
through `bind_subparser()` and the rest of the CLI keeps working
unchanged. Migrate one subcommand at a time.

The PowerShell parallel:

  PowerShell                       this framework
  ────────────────────────────────────────────────────────────────────
  [Parameter(Mandatory=$true)]     pydantic `Field(...)` (no default)
  [Parameter(ParameterSetName=)]   `model_config["parameter_sets"]`
  [ValidateSet("a","b","c")]       `Literal["a","b","c"]`
  [ValidateRange(0, 100)]          `Field(ge=0, le=100)`
  [ValidatePattern("^\\d+$")]      `Field(pattern="^\\d+$")`
  [ValidateScript({...})]          `@field_validator`
  Get-Command -Syntax              `BoundCommand.syntax_help()`
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
    Mapping,
    Sequence,
    Type,
    get_args,
    get_origin,
)

from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_core import PydanticUndefined


class ParameterSetError(ValueError):
    """Raised when the bound arguments don't match exactly one parameter set."""


def _is_literal(annotation: Any) -> bool:
    return get_origin(annotation) is not None and "Literal" in str(
        get_origin(annotation)
    )


def _literal_choices(annotation: Any) -> list[Any]:
    return list(get_args(annotation))


def _is_optional_type(annotation: Any) -> bool:
    """True for `Optional[X]` / `X | None`."""
    args = get_args(annotation)
    return get_origin(annotation) is not None and type(None) in args


def _peel_optional(annotation: Any) -> Any:
    args = [a for a in get_args(annotation) if a is not type(None)]
    return args[0] if len(args) == 1 else annotation


def _has_default(info: Any) -> bool:
    """True if the pydantic field declares a default (value or factory)."""
    if info.default is not PydanticUndefined:
        return True
    return getattr(info, "default_factory", None) is not None


def _resolve_default(info: Any) -> Any:
    """Materialize a field's default, calling default_factory if set."""
    if info.default is not PydanticUndefined:
        return info.default
    factory = getattr(info, "default_factory", None)
    if factory is not None:
        return factory()
    return None


def _argparse_kwargs_for_field(name: str, info: Any) -> dict[str, Any]:
    """Translate one pydantic FieldInfo into argparse `add_argument` kwargs."""
    annotation = info.annotation
    is_optional = _is_optional_type(annotation)
    if is_optional:
        annotation = _peel_optional(annotation)

    kwargs: dict[str, Any] = {}
    description = info.description or ""
    if description:
        kwargs["help"] = description

    # Booleans become flags. argparse's store_true defaults to False, but
    # respect a pydantic default of True if the user declared one.
    if annotation is bool:
        if _has_default(info) and info.default is True:
            kwargs["action"] = "store_false"
        else:
            kwargs["action"] = "store_true"
        return kwargs

    if _is_literal(annotation):
        kwargs["choices"] = _literal_choices(annotation)
        kwargs["type"] = type(kwargs["choices"][0]) if kwargs["choices"] else str
        if _has_default(info):
            kwargs["default"] = _resolve_default(info)
        return kwargs

    # Lists become repeatable args.
    origin = get_origin(annotation)
    if origin is list:
        elem_type = get_args(annotation)[0] if get_args(annotation) else str
        if elem_type is Path:
            elem_type = str
        kwargs["action"] = "append"
        kwargs["type"] = elem_type
        kwargs["default"] = _resolve_default(info) if _has_default(info) else []
        return kwargs

    if annotation is Path:
        kwargs["type"] = str  # we coerce to Path inside the model
        if _has_default(info):
            kwargs["default"] = _resolve_default(info)
        return kwargs

    if annotation in (int, float, str):
        kwargs["type"] = annotation
        if _has_default(info):
            kwargs["default"] = _resolve_default(info)
        return kwargs

    # Fallback: accept as string and let pydantic coerce.
    kwargs["type"] = str
    if _has_default(info):
        kwargs["default"] = info.default
    return kwargs


class BoundCommand(BaseModel):
    """Base for parameter-bound subcommands.

    Subclass and declare fields. Optional class-level config:

      class MyCommand(BoundCommand):
          model_config = ConfigDict(parameter_sets={
              "from-files":  ["forward_path", "reverse_path"],
              "from-stdin":  ["inline_forward", "inline_reverse"],
          })

          forward_path: Optional[str] = Field(None, description="...")
          reverse_path: Optional[str] = Field(None, description="...")
          inline_forward: Optional[str] = Field(None, description="...")
          inline_reverse: Optional[str] = Field(None, description="...")
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    parameter_sets: ClassVar[Mapping[str, Sequence[str]]] = {}

    @classmethod
    def _resolve_parameter_sets(cls) -> Mapping[str, Sequence[str]]:
        """Read parameter_sets from either class attribute or model_config."""
        if cls.parameter_sets:
            return cls.parameter_sets
        cfg = getattr(cls, "model_config", None)
        if isinstance(cfg, dict):
            sets = cfg.get("parameter_sets")
            if sets:
                return sets  # type: ignore[return-value]
        return {}

    @classmethod
    def from_namespace(cls, ns: argparse.Namespace) -> "BoundCommand":
        """Build an instance from an argparse Namespace, validating parameter sets."""
        # argparse turns dashes into underscores; pydantic field names already
        # match (we declare them with underscores).
        raw = {k: v for k, v in vars(ns).items() if k in cls.model_fields}
        try:
            inst = cls.model_validate(raw)
        except ValidationError as exc:
            raise ParameterSetError(str(exc)) from exc

        sets = cls._resolve_parameter_sets()
        if sets:
            # A field discriminates its parameter set only when the user
            # actually supplied a value. Defaults of None/empty/False are
            # treated as absent so a `bool=False` discriminator (a flag the
            # user didn't pass) doesn't force its set into present_sets.
            absent = (None, [], "", False)
            present_sets = []
            for set_name, members in sets.items():
                if any(getattr(inst, m, None) not in absent for m in members):
                    present_sets.append(set_name)
            if len(present_sets) == 0:
                raise ParameterSetError(
                    f"no parameter set satisfied; supply args for one of: {list(sets.keys())}"
                )
            if len(present_sets) > 1:
                raise ParameterSetError(
                    f"parameter sets are mutually exclusive; saw multiple: {present_sets}"
                )
        return inst

    @classmethod
    def syntax_help(cls) -> str:
        """PowerShell-style `Get-Command -Syntax` summary string."""
        sets = cls._resolve_parameter_sets()
        lines: list[str] = []
        if sets:
            for name, members in sets.items():
                parts = [f"--{m.replace('_','-')}" for m in members]
                lines.append(f"[{name}]  " + " ".join(parts))
        else:
            field_names = [f"--{n.replace('_','-')}" for n in cls.model_fields]
            lines.append(" ".join(field_names))
        return "\n".join(lines)


def bind_subparser(
    parser: argparse.ArgumentParser,
    model: Type[BoundCommand],
    handler: Callable[[BoundCommand, argparse.Namespace], int],
) -> None:
    """Wire `model`'s fields onto an argparse parser and dispatch to `handler`.

    The handler receives both the validated `BoundCommand` instance and the
    raw `argparse.Namespace` (so it can read flags that aren't part of the
    bound model — e.g. `--json`).
    """
    for name, info in model.model_fields.items():
        flag = "--" + name.replace("_", "-")
        kw = _argparse_kwargs_for_field(name, info)
        is_optional = _is_optional_type(info.annotation) or _has_default(info)
        if not is_optional and kw.get("action") not in ("store_true", "store_false"):
            kw["required"] = True
        parser.add_argument(flag, dest=name, **kw)

    def _dispatch(ns: argparse.Namespace) -> int:
        try:
            bound = model.from_namespace(ns)
        except ParameterSetError as exc:
            parser.error(str(exc))
            return 2  # parser.error() raises SystemExit; this is unreachable
        return handler(bound, ns)

    parser.set_defaults(func=_dispatch)


__all__ = [
    "BoundCommand",
    "ParameterSetError",
    "bind_subparser",
]
