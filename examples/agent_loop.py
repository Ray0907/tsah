#!/usr/bin/env python3
"""
tsah agent loop demo

Usage:
    python examples/agent_loop.py <APP_NAME>
    python examples/agent_loop.py Xcode
    python examples/agent_loop.py Safari

Watches an app's accessibility events and for each event prints:
  - The event type
  - A compact LLM-ready snapshot of the current UI state

With --llm-pipe flag, pipes each event+snapshot to `claude` CLI for agent reasoning.

This demonstrates the core pattern:
  OS push event -> structured UI context -> LLM action -> tsah act
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from tsah.core import ax_raw
from tsah.core.apps import find_app
from tsah.core.ax import AXElement
from tsah.core.observer import AXEvent, AXObserver
from tsah.core.tree import build_tree
from tsah.serializer import to_llm_tuples


def get_snapshot(pid: int, max_nodes: int = 50) -> list[list[object]]:
    """Get compact LLM-ready snapshot of app UI state."""
    try:
        root = build_tree(AXElement.application(pid))
        tuples = to_llm_tuples(root)
        return tuples[:max_nodes]
    except Exception as exc:
        return [["error", str(exc)]]


def handle_event(event: AXEvent, app_name: str, llm_pipe: bool) -> None:
    role = event.element.attribute(ax_raw.ATTRIBUTE_NAMES["role"], "") or ""
    role = role.removeprefix("AX") if isinstance(role, str) else str(role)

    label = ""
    for key in ("title", "description", "identifier"):
        value = event.element.attribute(ax_raw.ATTRIBUTE_NAMES[key], "")
        if value is not None and str(value).strip():
            label = str(value)
            break

    snapshot = get_snapshot(event.pid)
    payload = {
        "app": app_name,
        "event": event.notification.removeprefix("AX"),
        "element_role": role,
        "element_label": label,
        "ts": round(event.timestamp, 3),
        "ui_snapshot": snapshot,
    }

    print(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()

    if not llm_pipe:
        return

    prompt = f"""You are an AI agent watching {app_name} via the accessibility API.

Event: {payload["event"]}
Element: {role} "{label}"

Current UI state (compact):
{json.dumps(snapshot, ensure_ascii=False, indent=2)}

What action should be taken, if any? Reply with one of:
- OBSERVE (no action needed)
- ACT: tsah act "{app_name}" press "<label>"
- ACT: tsah act "{app_name}" focus "<label>"
"""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"[agent] (claude not available: {exc})", flush=True)
        return

    if result.stdout.strip():
        print(f"[agent] {result.stdout.strip()}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="tsah agent loop demo")
    parser.add_argument("app_name", help="App to watch (e.g. Safari, Xcode, Slack)")
    parser.add_argument(
        "--llm-pipe",
        action="store_true",
        help="Pipe events to claude CLI for agent reasoning",
    )
    parser.add_argument("--notifications", nargs="+", help="Override notification list")
    args = parser.parse_args()

    if not ax_raw.is_process_trusted():
        print("tsah needs Accessibility access.")
        print("System Settings > Privacy & Security > Accessibility")
        raise SystemExit(1)

    try:
        app = find_app(args.app_name)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"[tsah] Watching: {app.name} (pid {app.pid})", flush=True)
    print(f"[tsah] Mode: {'LLM agent' if args.llm_pipe else 'observe only'}", flush=True)
    print("[tsah] Press Ctrl+C to stop\n", flush=True)

    notifications = args.notifications or [
        ax_raw.NOTIFICATION_NAMES["focused_ui_changed"],
        ax_raw.NOTIFICATION_NAMES["focused_window_changed"],
        ax_raw.NOTIFICATION_NAMES["value_changed"],
        ax_raw.NOTIFICATION_NAMES["title_changed"],
        ax_raw.NOTIFICATION_NAMES["window_created"],
    ]

    def on_event(event: AXEvent) -> None:
        try:
            handle_event(event, app.name, args.llm_pipe)
        except Exception as exc:
            print(f"[tsah] Event handler error: {exc}", file=sys.stderr, flush=True)

    observer = AXObserver(app.pid, callback=on_event, notifications=notifications)
    try:
        observer.run()
    except KeyboardInterrupt:
        print("\n[tsah] Stopped.", flush=True)
    finally:
        observer.close()


if __name__ == "__main__":
    main()
