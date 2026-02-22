"""
Concept Blocks — DECIDE
=======================

Behaviour-tree execution engine.  Maps to SCBE Layer 7 (decision routing).

Nodes
-----
- **Action**    : leaf that runs a callable → SUCCESS / FAILURE
- **Condition** : leaf that tests a predicate → SUCCESS / FAILURE
- **Sequence**  : ticks children left-to-right; fails on first FAILURE
- **Selector**  : ticks children left-to-right; succeeds on first SUCCESS

Blackboard
----------
Shared key-value store visible to every node in the tree.

DecideBlock
-----------
ConceptBlock wrapper — feed a blackboard dict into ``tick()`` and get
the tree result back.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .base import BlockResult, BlockStatus, ConceptBlock


# -- node status -------------------------------------------------------------

class NodeStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


# -- blackboard --------------------------------------------------------------

class Blackboard:
    """Shared data store for tree nodes."""

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def clear(self) -> None:
        self._data.clear()

    def snapshot(self) -> Dict[str, Any]:
        return dict(self._data)


# -- tree nodes --------------------------------------------------------------

class TreeNode(ABC):
    """Base class for all behaviour-tree nodes."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def tick(self, bb: Blackboard) -> NodeStatus:
        ...

    def reset(self) -> None:
        pass


class Action(TreeNode):
    """Leaf node that executes a callable."""

    def __init__(self, name: str, fn: Callable[[Blackboard], bool]) -> None:
        super().__init__(name)
        self._fn = fn

    def tick(self, bb: Blackboard) -> NodeStatus:
        return NodeStatus.SUCCESS if self._fn(bb) else NodeStatus.FAILURE


class Condition(TreeNode):
    """Leaf node that evaluates a predicate."""

    def __init__(self, name: str, predicate: Callable[[Blackboard], bool]) -> None:
        super().__init__(name)
        self._pred = predicate

    def tick(self, bb: Blackboard) -> NodeStatus:
        return NodeStatus.SUCCESS if self._pred(bb) else NodeStatus.FAILURE


class Sequence(TreeNode):
    """Composite: succeeds only if ALL children succeed (left-to-right)."""

    def __init__(self, name: str, children: Optional[List[TreeNode]] = None) -> None:
        super().__init__(name)
        self.children: List[TreeNode] = children or []

    def tick(self, bb: Blackboard) -> NodeStatus:
        for child in self.children:
            status = child.tick(bb)
            if status != NodeStatus.SUCCESS:
                return status
        return NodeStatus.SUCCESS

    def reset(self) -> None:
        for c in self.children:
            c.reset()


class Selector(TreeNode):
    """Composite: succeeds if ANY child succeeds (left-to-right)."""

    def __init__(self, name: str, children: Optional[List[TreeNode]] = None) -> None:
        super().__init__(name)
        self.children: List[TreeNode] = children or []

    def tick(self, bb: Blackboard) -> NodeStatus:
        for child in self.children:
            status = child.tick(bb)
            if status != NodeStatus.FAILURE:
                return status
        return NodeStatus.FAILURE

    def reset(self) -> None:
        for c in self.children:
            c.reset()


# -- concept block wrapper ---------------------------------------------------

class DecideBlock(ConceptBlock):
    """Concept block wrapping a behaviour tree.

    tick(inputs):
        inputs["blackboard"] — dict merged into the tree's blackboard
    returns:
        BlockResult with output={"decision": str, "blackboard": dict}
    """

    def __init__(self, root: TreeNode, name: str = "DECIDE") -> None:
        super().__init__(name)
        self._root = root
        self._bb = Blackboard()

    def _do_tick(self, inputs: Dict[str, Any]) -> BlockResult:
        bb_update = inputs.get("blackboard", {})
        for k, v in bb_update.items():
            self._bb.set(k, v)

        status = self._root.tick(self._bb)

        block_status = {
            NodeStatus.SUCCESS: BlockStatus.SUCCESS,
            NodeStatus.FAILURE: BlockStatus.FAILURE,
            NodeStatus.RUNNING: BlockStatus.RUNNING,
        }[status]

        return BlockResult(
            status=block_status,
            output={"decision": status.value, "blackboard": self._bb.snapshot()},
        )

    def _do_reset(self) -> None:
        self._bb.clear()
        self._root.reset()
