from __future__ import annotations

from typing import Any

from tsah.core import ax_raw
from tsah.core.ax import AXElement


def _coerce_element(element: AXElement | int) -> AXElement:
    if isinstance(element, AXElement):
        return element
    return AXElement(element)


def perform_action(element: AXElement | int, action: str) -> None:
    target = _coerce_element(element)
    target.perform_action(action)


def press(element: AXElement | int) -> None:
    perform_action(element, ax_raw.ACTION_NAMES["press"])


def increment(element: AXElement | int) -> None:
    perform_action(element, ax_raw.ACTION_NAMES["increment"])


def decrement(element: AXElement | int) -> None:
    perform_action(element, ax_raw.ACTION_NAMES["decrement"])


def confirm(element: AXElement | int) -> None:
    perform_action(element, ax_raw.ACTION_NAMES["confirm"])


def raise_window(element: AXElement | int) -> None:
    perform_action(element, ax_raw.ACTION_NAMES["raise"])


def set_attribute(element: AXElement | int, attribute: str, value: Any) -> None:
    target = _coerce_element(element)
    target.set_attribute(attribute, value)
