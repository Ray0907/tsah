from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from tsah.core import ax_raw


class SnapshotElement(Protocol):
    @property
    def pointer(self) -> int: ...

    def pid(self) -> int | None: ...

    def attribute(self, name: str, default: Any = None) -> Any: ...

    def action_names(self) -> list[str]: ...

    def children(self) -> list["SnapshotElement"]: ...


@dataclass(slots=True)
class AXNode:
    ref: str
    pid: int | None = None
    role: str | None = None
    subrole: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    actions: list[str] = field(default_factory=list)
    children: list["AXNode"] = field(default_factory=list)
    cycle: bool = False
    truncated_children: int = 0


DEFAULT_ATTRIBUTES = tuple(ax_raw.iter_default_attributes())


def build_tree(
    root: SnapshotElement,
    *,
    max_depth: int | None = None,
    max_children: int | None = None,
    include_actions: bool = False,
    include_attributes: tuple[str, ...] | list[str] | None = None,
) -> AXNode:
    attribute_names = tuple(include_attributes) if include_attributes is not None else DEFAULT_ATTRIBUTES
    seen: set[int] = set()
    return _build_node(
        root,
        depth=max_depth,
        max_children=max_children,
        include_actions=include_actions,
        attribute_names=attribute_names,
        seen=seen,
    )


def _build_node(
    element: SnapshotElement,
    *,
    depth: int | None,
    max_children: int | None,
    include_actions: bool,
    attribute_names: tuple[str, ...],
    seen: set[int],
) -> AXNode:
    pointer = element.pointer
    role = _attribute(element, ax_raw.ATTRIBUTE_NAMES["role"])
    subrole = _attribute(element, ax_raw.ATTRIBUTE_NAMES["subrole"])

    if pointer in seen:
        return AXNode(
            ref=f"0x{pointer:x}",
            pid=element.pid(),
            role=role,
            subrole=subrole,
            attributes=_collect_attributes(element, attribute_names),
            cycle=True,
        )

    seen.add(pointer)
    attributes = _collect_attributes(element, attribute_names)
    actions = element.action_names() if include_actions else []
    children = element.children()
    truncated = 0

    if max_children is not None and len(children) > max_children:
        truncated = len(children) - max_children
        children = children[:max_children]

    frame = _frame_from_attributes(attributes)
    if frame is not None:
        attributes.setdefault("AXFrame", frame)

    if depth == 0:
        child_nodes: list[AXNode] = []
    else:
        next_depth = None if depth is None else depth - 1
        child_nodes = [
            _build_node(
                child,
                depth=next_depth,
                max_children=max_children,
                include_actions=include_actions,
                attribute_names=attribute_names,
                seen=seen.copy(),
            )
            for child in children
        ]

    return AXNode(
        ref=f"0x{pointer:x}",
        pid=element.pid(),
        role=role,
        subrole=subrole,
        attributes=attributes,
        actions=actions,
        children=child_nodes,
        truncated_children=truncated,
    )


def _collect_attributes(element: SnapshotElement, names: tuple[str, ...]) -> dict[str, Any]:
    attributes: dict[str, Any] = {}
    for name in names:
        value = _attribute(element, name)
        if value is not None:
            attributes[name] = value
    return attributes


def _attribute(element: SnapshotElement, name: str) -> Any:
    try:
        return element.attribute(name, None)
    except Exception as exc:
        return {"error": str(exc)}


def _frame_from_attributes(attributes: dict[str, Any]) -> dict[str, float] | None:
    position = attributes.get(ax_raw.ATTRIBUTE_NAMES["position"])
    size = attributes.get(ax_raw.ATTRIBUTE_NAMES["size"])
    if not isinstance(position, dict) or not isinstance(size, dict):
        return None
    if {"x", "y"} <= position.keys() and {"width", "height"} <= size.keys():
        return {
            "x": float(position["x"]),
            "y": float(position["y"]),
            "width": float(size["width"]),
            "height": float(size["height"]),
        }
    return None
