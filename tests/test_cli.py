from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import tsah.cli as cli
from tsah.core import ax_raw
from tsah.core.tree import AXNode
from tsah.cli import build_parser, main


def test_cli_snapshot_command_parses_flags() -> None:
    parser = build_parser()

    args = parser.parse_args(["snapshot", "Safari", "--llm", "--filter", "Button"])

    assert args.command == "snapshot"
    assert args.app_name == "Safari"
    assert args.llm is True
    assert args.filter == "Button"


def test_cli_watch_defaults_notifications() -> None:
    parser = build_parser()

    args = parser.parse_args(["watch", "Safari"])

    assert args.command == "watch"
    assert args.app_name == "Safari"
    assert args.notification == []


def test_watch_default_notifications_include_value_and_title_changes() -> None:
    assert ax_raw.NOTIFICATION_NAMES["value_changed"] in cli.DEFAULT_WATCH_NOTIFICATIONS
    assert ax_raw.NOTIFICATION_NAMES["title_changed"] in cli.DEFAULT_WATCH_NOTIFICATIONS


def test_list_command_prints_running_apps_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        "tsah.cli.list_apps",
        lambda: [SimpleNamespace(name="Safari", pid=123), SimpleNamespace(name="Mail", pid=456)],
    )

    exit_code = main(["list"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == [
        {"name": "Safari", "pid": 123},
        {"name": "Mail", "pid": 456},
    ]


def test_snapshot_llm_outputs_flat_tuples(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    root = AXNode(
        ref="0x1",
        pid=123,
        role="AXWindow",
        attributes={"AXTitle": "Main"},
        children=[
            AXNode(
                ref="0x2",
                pid=123,
                role="AXButton",
                attributes={"AXTitle": "Reload", "AXValue": "Ready"},
            )
        ],
    )
    monkeypatch.setattr("tsah.cli.find_app", lambda name: SimpleNamespace(name="Safari", pid=123))
    monkeypatch.setattr("tsah.cli.ax_raw.is_process_trusted", lambda: True)
    monkeypatch.setattr("tsah.cli.AXElement.application", lambda pid: SimpleNamespace(pid=lambda: pid))
    monkeypatch.setattr("tsah.cli.build_tree", lambda element: root)

    exit_code = main(["snapshot", "Safari", "--llm"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == [
        ["0", "Window", "Main"],
        ["0.0", "Button", "Reload", "Ready"],
    ]


def test_snapshot_filter_limits_json_output(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    root = AXNode(
        ref="0x1",
        pid=123,
        role="AXWindow",
        children=[
            AXNode(ref="0x2", pid=123, role="AXButton", attributes={"AXTitle": "Reload"}),
            AXNode(ref="0x3", pid=123, role="AXStaticText", attributes={"AXTitle": "Status"}),
        ],
    )
    monkeypatch.setattr("tsah.cli.find_app", lambda name: SimpleNamespace(name="Safari", pid=123))
    monkeypatch.setattr("tsah.cli.ax_raw.is_process_trusted", lambda: True)
    monkeypatch.setattr("tsah.cli.AXElement.application", lambda pid: SimpleNamespace(pid=lambda: pid))
    monkeypatch.setattr("tsah.cli.build_tree", lambda element: root)

    exit_code = main(["snapshot", "Safari", "--json", "--filter", "button"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == [
        {
            "ref": "0x2",
            "pid": 123,
            "role": "AXButton",
            "subrole": None,
            "attributes": {"AXTitle": "Reload"},
            "actions": [],
            "children": [],
            "cycle": False,
            "truncated_children": 0,
        }
    ]


def test_act_press_matches_label_and_calls_action(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[int, str]] = []
    live_element = SimpleNamespace(pointer=0xBEEF, ref="live-ref")
    monkeypatch.setattr("tsah.cli.find_app", lambda name: SimpleNamespace(name="Safari", pid=123))
    monkeypatch.setattr("tsah.cli.ax_raw.is_process_trusted", lambda: True)
    monkeypatch.setattr("tsah.cli.AXElement.application", lambda pid: SimpleNamespace(pid=lambda: pid))
    monkeypatch.setattr("tsah.cli.build_tree", lambda element: (_ for _ in ()).throw(AssertionError("stale tree path used")))
    monkeypatch.setattr("tsah.cli._find_live_element", lambda element, label: live_element, raising=False)
    monkeypatch.setattr("tsah.cli.ax_raw.perform_action", lambda ref, action: calls.append((ref, action)))

    exit_code = main(["act", "Safari", "press", "reload"])

    assert exit_code == 0
    assert calls == [(0xBEEF, "AXPress")]
    assert "OK: pressed 'reload'" in capsys.readouterr().out


def test_find_live_element_matches_descendant_label() -> None:
    class FakeElement:
        def __init__(
            self,
            *,
            title: str = "",
            description: str = "",
            identifier: str = "",
            children: list["FakeElement"] | None = None,
        ) -> None:
            self._children = children or []
            self._attrs = {
                ax_raw.ATTRIBUTE_NAMES["title"]: title,
                ax_raw.ATTRIBUTE_NAMES["description"]: description,
                ax_raw.ATTRIBUTE_NAMES["identifier"]: identifier,
            }

        def attribute(self, name: str, default: str = "") -> str:
            return self._attrs.get(name, default)

        def children(self) -> list["FakeElement"]:
            return self._children

    target = FakeElement(description="Reload page")
    root = FakeElement(children=[FakeElement(title="Cancel"), FakeElement(children=[target])])

    assert cli._find_live_element(root, "reload") is target
