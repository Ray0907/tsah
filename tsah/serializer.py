from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
from typing import Any


def to_data(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_data(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_data(item) for item in value]
    if isinstance(value, set):
        return [to_data(item) for item in sorted(value, key=repr)]
    if isinstance(value, Path):
        return str(value)
    return value


def dumps(value: Any, *, indent: int = 2, sort_keys: bool = False) -> str:
    return json.dumps(to_data(value), indent=indent, sort_keys=sort_keys, ensure_ascii=False)


def to_llm_tuples(node: Any, path: str = "0") -> list[list[Any]]:
    """Flatten a UI tree into [path, role, label?, value?] tuples."""
    result: list[list[Any]] = []
    role = (getattr(node, "role", "") or "").removeprefix("AX")
    label = _node_label(node)
    value = _node_value(node)

    if role or label or value:
        entry: list[Any] = [path, role]
        if label:
            entry.append(label)
        if value and str(value).strip():
            if len(entry) == 2:
                entry.append("")
            entry.append(str(value))
        result.append(entry)

    children = getattr(node, "children", []) or []
    for index, child in enumerate(children):
        result.extend(to_llm_tuples(child, f"{path}.{index}"))
    return result


def _node_label(node: Any) -> str:
    explicit = getattr(node, "label", "") or ""
    if explicit:
        return str(explicit)

    attributes = getattr(node, "attributes", {}) or {}
    for key in ("AXTitle", "AXDescription", "AXIdentifier"):
        value = attributes.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return ""


def _node_value(node: Any) -> Any:
    explicit = getattr(node, "value", None)
    if explicit is not None and str(explicit).strip():
        return explicit

    attributes = getattr(node, "attributes", {}) or {}
    for key in ("AXValue", "AXValueDescription"):
        value = attributes.get(key)
        if value is not None and str(value).strip():
            return value
    return None
