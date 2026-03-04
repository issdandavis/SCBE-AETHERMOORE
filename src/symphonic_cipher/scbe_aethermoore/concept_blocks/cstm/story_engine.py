"""
CSTM — StoryEngine
===================

Parse interactive fiction source files into traversable StoryGraph DAGs.

Supported formats:
- **Twee/Twine** (``.twee``, ``.tw``) — ``:: PassageName`` syntax with
  ``[[link]]`` and ``[[label->target]]`` navigation.
- **JSON** (``.json``) — Native CSTM schema with explicit scenes/choices.

ChoiceScript is intentionally omitted (non-commercial licence).  Ink/inkjs
support can be added later via an adapter.

Also provides ``ConditionEvaluator`` for safe runtime evaluation of choice
conditions (restricted AST — no function calls, no attribute access).
"""

from __future__ import annotations

import ast
import json
import operator
import re
import uuid
from pathlib import Path
from typing import Any, Dict, FrozenSet, IO, List, Optional, Protocol, Tuple, Union

from .models import Choice, Scene, StoryGraph, ValidationError


# ---------------------------------------------------------------------------
#  Parser protocol
# ---------------------------------------------------------------------------

class StoryParser(Protocol):
    """All parsers implement this interface."""

    def parse(self, source: Union[str, Path, IO]) -> StoryGraph:
        ...

    def supported_extensions(self) -> Tuple[str, ...]:
        ...


# ---------------------------------------------------------------------------
#  Condition evaluator (safe restricted expressions)
# ---------------------------------------------------------------------------

class ConditionEvaluator:
    """
    Safe evaluation of choice condition expressions over agent stats.

    Allowed grammar:
        expr     := compare | bool_op
        compare  := name  (< | <= | > | >= | == | !=)  constant
        bool_op  := expr  (and | or)  expr
        name     := stat name  (resolved from stats dict)
        constant := int | float | bool

    No function calls, no attribute access, no imports.
    """

    _ALLOWED_NODES = {
        ast.Expression, ast.BoolOp, ast.And, ast.Or,
        ast.Compare, ast.Name, ast.Constant, ast.Load,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.UnaryOp, ast.Not, ast.USub,
        ast.BinOp, ast.Add, ast.Sub, ast.Mult,
    }

    _CMP_OPS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }

    def evaluate(self, expression: str, stats: Dict[str, float]) -> bool:
        """Evaluate *expression* against *stats*.  Returns False on error."""
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError:
            return False
        if not self._is_safe(tree):
            return False
        try:
            return bool(self._eval_node(tree.body, stats))
        except Exception:
            return False

    def _is_safe(self, tree: ast.AST) -> bool:
        for node in ast.walk(tree):
            if type(node) not in self._ALLOWED_NODES:
                return False
        return True

    def _eval_node(self, node: ast.AST, stats: Dict[str, float]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return stats.get(node.id, 0.0)
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, stats)
            if isinstance(node.op, ast.Not):
                return not operand
            if isinstance(node.op, ast.USub):
                return -operand
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, stats)
            right = self._eval_node(node.right, stats)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, stats)
            for op_node, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, stats)
                op_fn = self._CMP_OPS.get(type(op_node))
                if op_fn is None or not op_fn(left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval_node(v, stats) for v in node.values)
            if isinstance(node.op, ast.Or):
                return any(self._eval_node(v, stats) for v in node.values)
        return False


# ---------------------------------------------------------------------------
#  JSON parser
# ---------------------------------------------------------------------------

class JSONParser:
    """
    Parse the native CSTM JSON schema::

        {
          "story_id": "...",
          "metadata": {...},
          "scenes": [
            {
              "scene_id": "...",
              "title": "...",
              "text": "...",
              "is_entry": true,
              "is_exit": false,
              "scene_type": "narrative",
              "choices": [
                {
                  "choice_id": "...",
                  "label": "...",
                  "next_scene_id": "...",
                  "condition": null,
                  "stat_effects": {"courage": 0.1},
                  "tags": ["ethical"],
                  "difficulty": 0.3
                }
              ]
            }
          ]
        }
    """

    def supported_extensions(self) -> Tuple[str, ...]:
        return (".json",)

    def parse(self, source: Union[str, Path, IO]) -> StoryGraph:
        if isinstance(source, (str, Path)):
            path = Path(source)
            raw = path.read_text(encoding="utf-8")
        else:
            raw = source.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")

        data = json.loads(raw)
        story_id = data.get("story_id", str(uuid.uuid4())[:8])
        metadata = data.get("metadata", {})

        scenes: Dict[str, Scene] = {}
        for s in data.get("scenes", []):
            choices = []
            for c in s.get("choices", []):
                choices.append(Choice(
                    choice_id=c.get("choice_id", str(uuid.uuid4())[:8]),
                    label=c["label"],
                    next_scene_id=c["next_scene_id"],
                    condition=c.get("condition"),
                    stat_effects=c.get("stat_effects", {}),
                    tags=frozenset(c.get("tags", [])),
                    difficulty=c.get("difficulty", 0.0),
                ))
            scene = Scene(
                scene_id=s["scene_id"],
                title=s.get("title", s["scene_id"]),
                text=s.get("text", ""),
                choices=choices,
                metadata=s.get("metadata", {}),
                is_entry=s.get("is_entry", False),
                is_exit=s.get("is_exit", False),
                scene_type=s.get("scene_type", "narrative"),
            )
            scenes[scene.scene_id] = scene

        return StoryGraph(scenes, story_id, metadata)


# ---------------------------------------------------------------------------
#  Twee / Twine parser
# ---------------------------------------------------------------------------

_PASSAGE_RE = re.compile(r'^::\s*(.+?)\s*(?:\[(.*?)\])?\s*$', re.MULTILINE)
_LINK_RE = re.compile(r'\[\[([^\]]+)\]\]')


class TweeParser:
    """
    Parse Twee2 / Twine source files.

    Twee syntax::

        :: Passage Title [tags]
        Narrative text here.
        [[Choice label->TargetPassage]]
        [[Simple link]]

    Tags in brackets are mapped to scene metadata.
    """

    def supported_extensions(self) -> Tuple[str, ...]:
        return (".twee", ".tw", ".txt")

    def parse(self, source: Union[str, Path, IO]) -> StoryGraph:
        if isinstance(source, (str, Path)):
            path = Path(source)
            raw = path.read_text(encoding="utf-8")
        else:
            raw = source.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")

        # Split into passages
        passages = self._split_passages(raw)
        if not passages:
            return StoryGraph({}, "empty", {})

        scenes: Dict[str, Scene] = {}
        first_passage = True

        for title, tags, body in passages:
            scene_id = self._slugify(title)
            choices = self._extract_choices(body, scene_id)

            # Strip link markup from display text
            clean_text = _LINK_RE.sub('', body).strip()

            is_exit = len(choices) == 0
            is_entry = first_passage
            first_passage = False

            scene = Scene(
                scene_id=scene_id,
                title=title,
                text=clean_text,
                choices=choices,
                metadata={"tags": tags} if tags else {},
                is_entry=is_entry,
                is_exit=is_exit,
            )
            scenes[scene.scene_id] = scene

        story_id = self._slugify(passages[0][0]) if passages else "twee_story"
        return StoryGraph(scenes, story_id, {"format": "twee"})

    def _split_passages(self, raw: str) -> List[Tuple[str, List[str], str]]:
        """Return list of (title, tags, body_text)."""
        matches = list(_PASSAGE_RE.finditer(raw))
        results: List[Tuple[str, List[str], str]] = []
        for i, m in enumerate(matches):
            title = m.group(1)
            tags = m.group(2).split() if m.group(2) else []
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
            body = raw[start:end].strip()
            results.append((title, tags, body))
        return results

    def _extract_choices(self, body: str, parent_id: str) -> List[Choice]:
        choices: List[Choice] = []
        for m in _LINK_RE.finditer(body):
            link_text = m.group(1)
            if "->" in link_text:
                label, target = link_text.split("->", 1)
                label = label.strip()
                target = target.strip()
            elif "|" in link_text:
                label, target = link_text.split("|", 1)
                label = label.strip()
                target = target.strip()
            else:
                label = link_text.strip()
                target = link_text.strip()

            target_id = self._slugify(target)
            choice_id = f"{parent_id}_to_{target_id}"
            choices.append(Choice(
                choice_id=choice_id,
                label=label,
                next_scene_id=target_id,
            ))
        return choices

    @staticmethod
    def _slugify(title: str) -> str:
        """Convert passage title to a safe scene_id."""
        s = title.lower().strip()
        s = re.sub(r'[^a-z0-9]+', '_', s)
        return s.strip('_')


# ---------------------------------------------------------------------------
#  StoryEngine — main orchestrator
# ---------------------------------------------------------------------------

class StoryEngine:
    """
    Load, parse, validate, and serve interactive fiction stories.

    Usage::

        engine = StoryEngine()
        graph = engine.load("path/to/story.json")
        errors = graph.validate()
    """

    def __init__(self) -> None:
        self._parsers: Dict[str, StoryParser] = {}
        self._cache: Dict[str, StoryGraph] = {}

        # Register built-in parsers
        self.register_parser(JSONParser())
        self.register_parser(TweeParser())

    def register_parser(self, parser: StoryParser) -> None:
        for ext in parser.supported_extensions():
            self._parsers[ext] = parser

    def load(self, source: Union[str, Path], story_id: Optional[str] = None) -> StoryGraph:
        """Load a story from file path.  Returns cached graph if already loaded."""
        path = Path(source)
        cache_key = story_id or str(path.resolve())

        if cache_key in self._cache:
            return self._cache[cache_key]

        ext = path.suffix.lower()
        parser = self._parsers.get(ext)
        if parser is None:
            raise ValueError(f"No parser registered for extension '{ext}'")

        graph = parser.parse(path)
        if story_id:
            graph.story_id = story_id

        self._cache[cache_key] = graph
        return graph

    def load_from_string(self, text: str, fmt: str = "json", story_id: Optional[str] = None) -> StoryGraph:
        """Parse a story from a string.  *fmt* is 'json' or 'twee'."""
        import io
        ext = f".{fmt}"
        parser = self._parsers.get(ext)
        if parser is None:
            raise ValueError(f"No parser for format '{fmt}'")
        graph = parser.parse(io.StringIO(text))
        if story_id:
            graph.story_id = story_id
        return graph

    def load_directory(self, directory: Union[str, Path]) -> List[StoryGraph]:
        """Load all supported story files from a directory."""
        dirpath = Path(directory)
        graphs: List[StoryGraph] = []
        for f in sorted(dirpath.iterdir()):
            if f.suffix.lower() in self._parsers:
                graphs.append(self.load(f))
        return graphs

    def validate_all(self) -> Dict[str, List[ValidationError]]:
        """Validate all cached stories.  Returns {story_id: [errors]}."""
        results: Dict[str, List[ValidationError]] = {}
        for sid, graph in self._cache.items():
            errors = graph.validate()
            if errors:
                results[graph.story_id] = errors
        return results

    def clear_cache(self) -> None:
        self._cache.clear()
