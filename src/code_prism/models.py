from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PrismFunction:
    name: str
    args: List[str]
    body: List[str]
    returns: Optional[str] = None
    docstring: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PrismModule:
    module_name: str
    source_language: str
    imports: List[str] = field(default_factory=list)
    functions: List[PrismFunction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

