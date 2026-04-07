from __future__ import annotations

from tsah.core.actions import perform_action, press, set_attribute
from tsah.core.ax import AXElement
from tsah.core.observer import AXEvent, AXObserver
from tsah.core.tree import AXNode, build_tree
from tsah.serializer import dumps, to_data

__all__ = [
    "AXElement",
    "AXEvent",
    "AXNode",
    "AXObserver",
    "build_tree",
    "dumps",
    "perform_action",
    "press",
    "set_attribute",
    "to_data",
]

__version__ = "0.1.0"
