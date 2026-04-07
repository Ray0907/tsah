from __future__ import annotations

from tsah.core.tree import AXNode, build_tree


class FakeElement:
    def __init__(
        self,
        ref: str,
        *,
        pid: int | None = None,
        attributes: dict[str, object] | None = None,
        actions: list[str] | None = None,
        children: list["FakeElement"] | None = None,
    ) -> None:
        self.ref = ref
        self._pid = pid
        self._attributes = attributes or {}
        self._actions = actions or []
        self._children = children or []

    @property
    def pointer(self) -> int:
        return int(self.ref, 16)

    def pid(self) -> int | None:
        return self._pid

    def attribute(self, name: str, default: object = None) -> object:
        return self._attributes.get(name, default)

    def action_names(self) -> list[str]:
        return list(self._actions)

    def children(self) -> list["FakeElement"]:
        return list(self._children)


def test_build_tree_collects_default_fields_and_children() -> None:
    button = FakeElement(
        "0x2",
        pid=77,
        attributes={"AXRole": "AXButton", "AXTitle": "Save", "AXEnabled": True},
        actions=["AXPress"],
    )
    window = FakeElement(
        "0x1",
        pid=77,
        attributes={"AXRole": "AXWindow", "AXTitle": "Editor"},
        children=[button],
    )

    node = build_tree(window, include_actions=True)

    assert isinstance(node, AXNode)
    assert node.role == "AXWindow"
    assert node.attributes["AXTitle"] == "Editor"
    assert node.children[0].actions == ["AXPress"]


def test_build_tree_marks_cycles_without_recursing_forever() -> None:
    root = FakeElement("0x1", pid=9, attributes={"AXRole": "AXGroup"})
    root._children = [root]

    node = build_tree(root)

    assert node.children[0].cycle is True
    assert node.children[0].children == []


def test_build_tree_enforces_child_limit() -> None:
    children = [
        FakeElement(hex(i), pid=1, attributes={"AXRole": "AXStaticText", "AXTitle": str(i)})
        for i in range(2, 7)
    ]
    root = FakeElement("0x1", pid=1, attributes={"AXRole": "AXGroup"}, children=children)

    node = build_tree(root, max_children=2)

    assert len(node.children) == 2
    assert node.truncated_children == 3
