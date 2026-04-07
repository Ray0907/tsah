from __future__ import annotations

import json

from tsah.serializer import dumps, to_data, to_llm_tuples
from tsah.core.tree import AXNode


def test_to_data_serializes_nested_dataclasses() -> None:
    child = AXNode(
        ref="0x2",
        pid=42,
        role="AXButton",
        attributes={"AXTitle": "OK"},
        actions=["AXPress"],
    )
    parent = AXNode(
        ref="0x1",
        pid=42,
        role="AXWindow",
        attributes={"AXTitle": "Dialog"},
        children=[child],
        truncated_children=3,
    )

    data = to_data(parent)

    assert data["ref"] == "0x1"
    assert data["children"][0]["role"] == "AXButton"
    assert data["truncated_children"] == 3


def test_dumps_emits_pretty_json() -> None:
    node = AXNode(ref="0x1", role="AXApplication", attributes={"AXTitle": "Demo"})

    payload = dumps(node)
    decoded = json.loads(payload)

    assert decoded["role"] == "AXApplication"
    assert '"AXTitle": "Demo"' in payload


def test_to_llm_tuples_flattens_role_label_and_value() -> None:
    node = AXNode(
        ref="0x1",
        role="AXWindow",
        attributes={"AXTitle": "Main"},
        children=[
            AXNode(
                ref="0x2",
                role="AXButton",
                attributes={"AXTitle": "Reload", "AXValue": "Ready"},
            )
        ],
    )

    payload = to_llm_tuples(node)

    assert payload == [
        ["0", "Window", "Main"],
        ["0.0", "Button", "Reload", "Ready"],
    ]
