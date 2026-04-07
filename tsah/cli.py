from __future__ import annotations

import argparse
from dataclasses import replace
import sys
from typing import Any, Iterable, Sequence

from rich.console import Console
from rich.tree import Tree

from tsah import __version__
from tsah.core import ax_raw
from tsah.core.apps import AppInfo, find_app, list_apps
from tsah.core.ax import AXElement
from tsah.core.observer import AXEvent, AXObserver
from tsah.core.tree import AXNode, build_tree
from tsah.serializer import dumps, to_data, to_llm_tuples


DEFAULT_WATCH_NOTIFICATIONS = [
    ax_raw.NOTIFICATION_NAMES["focused_ui_changed"],
    ax_raw.NOTIFICATION_NAMES["focused_window_changed"],
    ax_raw.NOTIFICATION_NAMES["window_created"],
    ax_raw.NOTIFICATION_NAMES["value_changed"],
    ax_raw.NOTIFICATION_NAMES["title_changed"],
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tsah", description="macOS Accessibility tree and observer toolkit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List running applications as JSON")

    snapshot = subparsers.add_parser("snapshot", aliases=["tree"], help="Snapshot an app accessibility tree")
    snapshot.add_argument("app_name")
    snapshot.add_argument("--llm", action="store_true", help="Emit flat tuple JSON for LLM consumption")
    snapshot.add_argument("--filter", help="Only include nodes whose role contains this text")
    snapshot.add_argument("--json", action="store_true", help="Emit the full JSON tree")

    watch = subparsers.add_parser("watch", help="Observe accessibility notifications for an app")
    watch.add_argument("app_name")
    watch.add_argument("--notification", action="append", default=[])

    act = subparsers.add_parser("act", help="Act on the first matching labeled element")
    act.add_argument("app_name")
    act.add_argument("action", choices=["press", "focus"])
    act.add_argument("label")

    trust = subparsers.add_parser("trust", help="Report whether the process is trusted for AX access")
    trust.add_argument("--quiet", action="store_true")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "trust":
        trusted = ax_raw.is_process_trusted()
        if not args.quiet:
            print("trusted" if trusted else "untrusted")
        return 0 if trusted else 1

    try:
        if args.command == "list":
            return _run_list()
        if args.command in {"snapshot", "tree"}:
            _require_trust()
            return _run_snapshot(args)
        if args.command == "watch":
            _require_trust()
            return _run_watch(args)
        if args.command == "act":
            _require_trust()
            return _run_act(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _run_list() -> int:
    print(dumps([{"name": app.name, "pid": app.pid} for app in list_apps()]))
    return 0


def _run_snapshot(args: argparse.Namespace) -> int:
    app = find_app(args.app_name)
    root = build_tree(AXElement.application(app.pid))
    matches = _filter_nodes(root, args.filter)

    if args.llm:
        tuples = to_llm_tuples(root)
        if args.filter:
            needle = args.filter.lower()
            tuples = [entry for entry in tuples if len(entry) > 1 and needle in str(entry[1]).lower()]
        print(dumps(tuples))
        return 0

    if args.json:
        payload: Any = matches if args.filter else root
        print(dumps(payload))
        return 0

    _print_rich_tree(app, matches if args.filter else root)
    return 0


def _run_watch(args: argparse.Namespace) -> int:
    app = find_app(args.app_name)
    notifications = args.notification or DEFAULT_WATCH_NOTIFICATIONS

    def emit(event: AXEvent) -> None:
        role = event.element.attribute(ax_raw.ATTRIBUTE_NAMES["role"], "") or ""
        payload = {
            "type": event.notification,
            "ts": event.timestamp,
            "pid": event.pid,
            "role": role.removeprefix("AX") if isinstance(role, str) else role,
            "label": _element_label(event.element),
        }
        print(dumps(payload, indent=None))
        sys.stdout.flush()

    observer = AXObserver(app.pid, callback=emit, notifications=notifications)
    try:
        observer.run()
    finally:
        observer.close()
    return 0


def _run_act(args: argparse.Namespace) -> int:
    app = find_app(args.app_name)
    app_element = AXElement.application(app.pid)
    target = _find_live_element(app_element, args.label)
    if target is None:
        print(f"No element found matching label {args.label!r}", file=sys.stderr)
        return 1

    if args.action == "press":
        ax_raw.perform_action(target.pointer, ax_raw.ACTION_NAMES["press"])
        print(f"OK: pressed {args.label!r}")
        return 0

    ax_raw.set_attribute_value(target.pointer, ax_raw.ATTRIBUTE_NAMES["focused"], True)
    print(f"OK: focused {args.label!r}")
    return 0


def _require_trust() -> None:
    if not ax_raw.is_process_trusted():
        print("tsah needs Accessibility access.")
        print("Open: System Settings > Privacy & Security > Accessibility")
        print("Then re-run your command.")
        raise SystemExit(1)


def _filter_nodes(root: AXNode, role_filter: str | None) -> list[AXNode]:
    if not role_filter:
        return [root]

    needle = role_filter.lower()
    matches: list[AXNode] = []
    for node in _iter_nodes(root):
        role = node.role or ""
        if needle in role.lower():
            matches.append(replace(node, children=[]))
    return matches


def _iter_nodes(root: AXNode) -> Iterable[AXNode]:
    yield root
    for child in root.children:
        yield from _iter_nodes(child)


def _find_node_by_label(root: AXNode, label: str) -> AXNode | None:
    needle = label.lower()
    for node in _iter_nodes(root):
        if needle in _label_for_node(node).lower():
            return node
    return None


def _find_live_element(element: AXElement, label: str) -> AXElement | None:
    needle = label.lower()

    def label_for_element(current: AXElement) -> str:
        for key in ("title", "description", "identifier"):
            attr = ax_raw.ATTRIBUTE_NAMES[key]
            try:
                value = current.attribute(attr, "")
            except Exception:
                continue
            if value is not None and str(value).strip():
                return str(value)
        return ""

    def search(current: AXElement, depth: int = 0) -> AXElement | None:
        if depth > 15:
            return None
        if needle in label_for_element(current).lower():
            return current
        try:
            children = current.children()
        except Exception:
            return None
        for child in children:
            result = search(child, depth + 1)
            if result is not None:
                return result
        return None

    return search(element)


def _label_for_node(node: AXNode) -> str:
    attributes = node.attributes or {}
    for key in ("AXTitle", "AXDescription", "AXIdentifier"):
        value = attributes.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return ""


def _value_for_node(node: AXNode) -> str:
    attributes = node.attributes or {}
    for key in ("AXValue", "AXValueDescription"):
        value = attributes.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return ""


def _display_label(node: AXNode, fallback: str) -> str:
    return _label_for_node(node) or fallback


def _print_rich_tree(app: AppInfo, payload: AXNode | list[AXNode]) -> None:
    console = Console()
    if isinstance(payload, list):
        tree = Tree(f"{app.name} ({app.pid})")
        for node in payload:
            branch = tree.add(_node_summary(node))
            _append_children(branch, node)
        console.print(tree)
        return

    tree = Tree(f"{app.name} ({app.pid})")
    branch = tree.add(_node_summary(payload))
    _append_children(branch, payload)
    console.print(tree)


def _append_children(branch: Tree, node: AXNode) -> None:
    for child in node.children:
        child_branch = branch.add(_node_summary(child))
        _append_children(child_branch, child)
    if node.truncated_children:
        branch.add(f"... {node.truncated_children} more children")


def _node_summary(node: AXNode) -> str:
    role = (node.role or "Node").removeprefix("AX")
    parts = [role]
    label = _label_for_node(node)
    value = _value_for_node(node)
    if label:
        parts.append(f"[{label}]")
    if value:
        parts.append(f"= {value}")
    return " ".join(parts)


def _element_label(element: AXElement) -> str:
    for key in ("title", "description", "identifier"):
        attr = ax_raw.ATTRIBUTE_NAMES[key]
        value = element.attribute(attr, "")
        if value is not None and str(value).strip():
            return str(value)
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
