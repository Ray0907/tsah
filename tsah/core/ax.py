from __future__ import annotations

from dataclasses import dataclass
import weakref
from typing import Any

from tsah.core import ax_raw


@dataclass(slots=True)
class AXElement:
    _ref: ax_raw.AXUIElementRef
    _anchor: object
    _finalizer: weakref.finalize | None

    def __init__(self, ref: int | ax_raw.AXUIElementRef, *, adopt: bool = False) -> None:
        pointer = ax_raw._coerce_pointer(ref)
        if pointer is None:
            raise ValueError("AXElement requires a non-null AXUIElementRef")
        self._ref = pointer
        if not adopt:
            ax_raw.retain(pointer)
        self._anchor = ax_raw._FinalizerAnchor()
        self._finalizer = weakref.finalize(self._anchor, ax_raw.release, pointer)

    @classmethod
    def system_wide(cls) -> "AXElement":
        return cls(ax_raw.system_wide_element(), adopt=True)

    @classmethod
    def application(cls, pid: int) -> "AXElement":
        return cls(ax_raw.application_element(pid), adopt=True)

    @classmethod
    def focused_application(cls) -> "AXElement":
        ref = ax_raw.focused_application()
        if ref is None:
            raise RuntimeError("No focused application is currently available")
        return cls(ref, adopt=True)

    @classmethod
    def focused_ui_element(cls) -> "AXElement":
        ref = ax_raw.focused_ui_element()
        if ref is None:
            raise RuntimeError("No focused UI element is currently available")
        return cls(ref, adopt=True)

    @property
    def ref(self) -> ax_raw.AXUIElementRef:
        return self._ref

    @property
    def pointer(self) -> int:
        if not self._ref.value:
            raise RuntimeError("AXElement pointer is NULL")
        return int(self._ref.value)

    def hex_ref(self) -> str:
        return f"0x{self.pointer:x}"

    def pid(self) -> int | None:
        return ax_raw.pid_for_element(self._ref)

    def attribute_names(self) -> list[str]:
        return ax_raw.copy_attribute_names(self._ref)

    def parameterized_attribute_names(self) -> list[str]:
        return ax_raw.copy_parameterized_attribute_names(self._ref)

    def attribute(self, name: str, default: Any = None) -> Any:
        value = ax_raw.copy_attribute_value(self._ref, name)
        return default if value is None else value

    def action_names(self) -> list[str]:
        return ax_raw.copy_action_names(self._ref)

    def children(self, *, max_children: int | None = None) -> list["AXElement"]:
        refs = ax_raw.children_for_element(self._ref, max_children=max_children)
        return [AXElement(ref, adopt=True) for ref in refs]

    def is_settable(self, attribute: str) -> bool:
        return ax_raw.is_attribute_settable(self._ref, attribute)

    def set_attribute(self, attribute: str, value: Any) -> None:
        ax_raw.set_attribute_value(self._ref, attribute, value)

    def perform_action(self, action: str) -> None:
        ax_raw.perform_action(self._ref, action)

    def parameterized_attribute(self, attribute: str, parameter: Any) -> Any:
        return ax_raw.copy_parameterized_attribute_value(self._ref, attribute, parameter)

    def focused_window(self) -> "AXElement | None":
        pointer = ax_raw.copy_attribute_value_preserving_elements(self._ref, ax_raw.ATTRIBUTE_NAMES["focused_window"])
        return AXElement(pointer, adopt=True) if pointer else None

    def focused_ui_element(self) -> "AXElement | None":
        pointer = ax_raw.copy_attribute_value_preserving_elements(self._ref, ax_raw.ATTRIBUTE_NAMES["focused_ui_element"])
        return AXElement(pointer, adopt=True) if pointer else None

    def snapshot(self, **kwargs: Any):
        from tsah.core.tree import build_tree

        return build_tree(self, **kwargs)

    def close(self) -> None:
        if self._finalizer is not None and self._finalizer.alive:
            self._finalizer()

    def __enter__(self) -> "AXElement":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __repr__(self) -> str:
        role = self.attribute(ax_raw.ATTRIBUTE_NAMES["role"], None)
        return f"AXElement(ref={self.hex_ref()}, role={role!r})"
