from __future__ import annotations

import ctypes
from ctypes import POINTER, byref, c_bool, c_char_p, c_double, c_int32, c_long, c_void_p
from ctypes.util import find_library
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterator
import weakref

CFIndex = c_long
CFTypeID = c_long
CFStringEncoding = ctypes.c_uint32
AXErrorCode = c_int32
Boolean = c_bool
pid_t = c_int32
CGFloat = c_double

CFStringRef = c_void_p
CFArrayRef = c_void_p
CFDictionaryRef = c_void_p
CFTypeRef = c_void_p
CFNumberRef = c_void_p
CFBooleanRef = c_void_p
CFRunLoopRef = c_void_p
CFRunLoopSourceRef = c_void_p
AXUIElementRef = c_void_p
AXObserverRef = c_void_p
AXValueRef = c_void_p

K_CF_STRING_ENCODING_UTF8 = 0x08000100
K_CF_NUMBER_SINT64_TYPE = 4
K_CF_NUMBER_DOUBLE_TYPE = 13

K_AX_VALUE_ILLEGAL_TYPE = 0
K_AX_VALUE_POINT_TYPE = 1
K_AX_VALUE_SIZE_TYPE = 2
K_AX_VALUE_RECT_TYPE = 3
K_AX_VALUE_RANGE_TYPE = 4
K_AX_VALUE_ERROR_TYPE = 5

AX_ERROR_NAMES = {
    0: "kAXErrorSuccess",
    -25200: "kAXErrorFailure",
    -25201: "kAXErrorIllegalArgument",
    -25202: "kAXErrorInvalidUIElement",
    -25203: "kAXErrorInvalidUIElementObserver",
    -25204: "kAXErrorCannotComplete",
    -25205: "kAXErrorAttributeUnsupported",
    -25206: "kAXErrorActionUnsupported",
    -25207: "kAXErrorNotificationUnsupported",
    -25208: "kAXErrorNotImplemented",
    -25209: "kAXErrorNotificationAlreadyRegistered",
    -25210: "kAXErrorNotificationNotRegistered",
    -25211: "kAXErrorAPIDisabled",
    -25212: "kAXErrorNoValue",
    -25213: "kAXErrorParameterizedAttributeUnsupported",
    -25214: "kAXErrorNotEnoughPrecision",
}

ATTRIBUTE_NAMES = {
    "role": "AXRole",
    "subrole": "AXSubrole",
    "title": "AXTitle",
    "description": "AXDescription",
    "help": "AXHelp",
    "value": "AXValue",
    "value_description": "AXValueDescription",
    "enabled": "AXEnabled",
    "focused": "AXFocused",
    "position": "AXPosition",
    "size": "AXSize",
    "identifier": "AXIdentifier",
    "children": "AXChildren",
    "parent": "AXParent",
    "window": "AXWindow",
    "main_window": "AXMainWindow",
    "focused_window": "AXFocusedWindow",
    "focused_ui_element": "AXFocusedUIElement",
    "focused_application": "AXFocusedApplication",
}

ACTION_NAMES = {
    "press": "AXPress",
    "increment": "AXIncrement",
    "decrement": "AXDecrement",
    "confirm": "AXConfirm",
    "cancel": "AXCancel",
    "show_menu": "AXShowMenu",
    "raise": "AXRaise",
}

NOTIFICATION_NAMES = {
    "focused_ui_changed": "AXFocusedUIElementChanged",
    "focused_window_changed": "AXFocusedWindowChanged",
    "window_created": "AXWindowCreated",
    "ui_element_destroyed": "AXUIElementDestroyed",
    "title_changed": "AXTitleChanged",
    "value_changed": "AXValueChanged",
    "moved": "AXMoved",
    "resized": "AXResized",
    "selected_text_changed": "AXSelectedTextChanged",
}


class AXError(RuntimeError):
    def __init__(self, code: int, operation: str) -> None:
        self.code = int(code)
        self.operation = operation
        name = AX_ERROR_NAMES.get(self.code, f"AXError({self.code})")
        super().__init__(f"{operation} failed with {name}")


@dataclass(frozen=True, slots=True)
class CGPoint:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class CGSize:
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class CGRect:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class CFRange:
    location: int
    length: int


class _CGPoint(ctypes.Structure):
    _fields_ = [("x", CGFloat), ("y", CGFloat)]


class _CGSize(ctypes.Structure):
    _fields_ = [("width", CGFloat), ("height", CGFloat)]


class _CGRect(ctypes.Structure):
    _fields_ = [("origin", _CGPoint), ("size", _CGSize)]


class _CFRange(ctypes.Structure):
    _fields_ = [("location", CFIndex), ("length", CFIndex)]


class _FinalizerAnchor:
    pass


def _load_framework(name: str) -> ctypes.CDLL:
    candidate = find_library(name)
    if candidate:
        return ctypes.CDLL(candidate)
    fallback = f"/System/Library/Frameworks/{name}.framework/{name}"
    return ctypes.CDLL(fallback)


cf = _load_framework("CoreFoundation")
app_services = _load_framework("ApplicationServices")


def _configure_signatures() -> None:
    cf.CFRetain.argtypes = [CFTypeRef]
    cf.CFRetain.restype = CFTypeRef
    cf.CFRelease.argtypes = [CFTypeRef]
    cf.CFRelease.restype = None
    cf.CFGetTypeID.argtypes = [CFTypeRef]
    cf.CFGetTypeID.restype = CFTypeID
    cf.CFHash.argtypes = [CFTypeRef]
    cf.CFHash.restype = ctypes.c_long

    cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, CFStringEncoding]
    cf.CFStringCreateWithCString.restype = CFStringRef
    cf.CFStringGetTypeID.argtypes = []
    cf.CFStringGetTypeID.restype = CFTypeID
    cf.CFStringGetLength.argtypes = [CFStringRef]
    cf.CFStringGetLength.restype = CFIndex
    cf.CFStringGetMaximumSizeForEncoding.argtypes = [CFIndex, CFStringEncoding]
    cf.CFStringGetMaximumSizeForEncoding.restype = CFIndex
    cf.CFStringGetCString.argtypes = [CFStringRef, c_char_p, CFIndex, CFStringEncoding]
    cf.CFStringGetCString.restype = Boolean

    cf.CFBooleanGetTypeID.argtypes = []
    cf.CFBooleanGetTypeID.restype = CFTypeID
    cf.CFBooleanGetValue.argtypes = [CFBooleanRef]
    cf.CFBooleanGetValue.restype = Boolean

    cf.CFNumberGetTypeID.argtypes = []
    cf.CFNumberGetTypeID.restype = CFTypeID
    cf.CFNumberIsFloatType.argtypes = [CFNumberRef]
    cf.CFNumberIsFloatType.restype = Boolean
    cf.CFNumberGetValue.argtypes = [CFNumberRef, CFIndex, c_void_p]
    cf.CFNumberGetValue.restype = Boolean
    cf.CFNumberCreate.argtypes = [c_void_p, CFIndex, c_void_p]
    cf.CFNumberCreate.restype = CFNumberRef

    cf.CFArrayGetTypeID.argtypes = []
    cf.CFArrayGetTypeID.restype = CFTypeID
    cf.CFArrayGetCount.argtypes = [CFArrayRef]
    cf.CFArrayGetCount.restype = CFIndex
    cf.CFArrayGetValueAtIndex.argtypes = [CFArrayRef, CFIndex]
    cf.CFArrayGetValueAtIndex.restype = CFTypeRef

    cf.CFDictionaryGetTypeID.argtypes = []
    cf.CFDictionaryGetTypeID.restype = CFTypeID
    cf.CFDictionaryGetCount.argtypes = [CFDictionaryRef]
    cf.CFDictionaryGetCount.restype = CFIndex
    cf.CFDictionaryGetKeysAndValues.argtypes = [CFDictionaryRef, POINTER(c_void_p), POINTER(c_void_p)]
    cf.CFDictionaryGetKeysAndValues.restype = None

    cf.CFNullGetTypeID.argtypes = []
    cf.CFNullGetTypeID.restype = CFTypeID

    cf.CFRunLoopGetCurrent.argtypes = []
    cf.CFRunLoopGetCurrent.restype = CFRunLoopRef
    cf.CFRunLoopAddSource.argtypes = [CFRunLoopRef, CFRunLoopSourceRef, CFStringRef]
    cf.CFRunLoopAddSource.restype = None
    cf.CFRunLoopRemoveSource.argtypes = [CFRunLoopRef, CFRunLoopSourceRef, CFStringRef]
    cf.CFRunLoopRemoveSource.restype = None
    cf.CFRunLoopStop.argtypes = [CFRunLoopRef]
    cf.CFRunLoopStop.restype = None
    cf.CFRunLoopRun.argtypes = []
    cf.CFRunLoopRun.restype = None

    app_services.AXIsProcessTrusted.argtypes = []
    app_services.AXIsProcessTrusted.restype = Boolean

    app_services.AXUIElementGetTypeID.argtypes = []
    app_services.AXUIElementGetTypeID.restype = CFTypeID
    app_services.AXUIElementCreateSystemWide.argtypes = []
    app_services.AXUIElementCreateSystemWide.restype = AXUIElementRef
    app_services.AXUIElementCreateApplication.argtypes = [pid_t]
    app_services.AXUIElementCreateApplication.restype = AXUIElementRef
    app_services.AXUIElementCopyAttributeNames.argtypes = [AXUIElementRef, POINTER(CFArrayRef)]
    app_services.AXUIElementCopyAttributeNames.restype = AXErrorCode
    app_services.AXUIElementCopyParameterizedAttributeNames.argtypes = [AXUIElementRef, POINTER(CFArrayRef)]
    app_services.AXUIElementCopyParameterizedAttributeNames.restype = AXErrorCode
    app_services.AXUIElementCopyAttributeValue.argtypes = [AXUIElementRef, CFStringRef, POINTER(CFTypeRef)]
    app_services.AXUIElementCopyAttributeValue.restype = AXErrorCode
    app_services.AXUIElementCopyAttributeValues.argtypes = [AXUIElementRef, CFStringRef, CFIndex, CFIndex, POINTER(CFArrayRef)]
    app_services.AXUIElementCopyAttributeValues.restype = AXErrorCode
    app_services.AXUIElementCopyParameterizedAttributeValue.argtypes = [AXUIElementRef, CFStringRef, CFTypeRef, POINTER(CFTypeRef)]
    app_services.AXUIElementCopyParameterizedAttributeValue.restype = AXErrorCode
    app_services.AXUIElementIsAttributeSettable.argtypes = [AXUIElementRef, CFStringRef, POINTER(Boolean)]
    app_services.AXUIElementIsAttributeSettable.restype = AXErrorCode
    app_services.AXUIElementSetAttributeValue.argtypes = [AXUIElementRef, CFStringRef, CFTypeRef]
    app_services.AXUIElementSetAttributeValue.restype = AXErrorCode
    app_services.AXUIElementCopyActionNames.argtypes = [AXUIElementRef, POINTER(CFArrayRef)]
    app_services.AXUIElementCopyActionNames.restype = AXErrorCode
    app_services.AXUIElementPerformAction.argtypes = [AXUIElementRef, CFStringRef]
    app_services.AXUIElementPerformAction.restype = AXErrorCode
    app_services.AXUIElementGetPid.argtypes = [AXUIElementRef, POINTER(pid_t)]
    app_services.AXUIElementGetPid.restype = AXErrorCode

    app_services.AXObserverGetTypeID.argtypes = []
    app_services.AXObserverGetTypeID.restype = CFTypeID
    app_services.AXObserverAddNotification.argtypes = [AXObserverRef, AXUIElementRef, CFStringRef, c_void_p]
    app_services.AXObserverAddNotification.restype = AXErrorCode
    app_services.AXObserverRemoveNotification.argtypes = [AXObserverRef, AXUIElementRef, CFStringRef]
    app_services.AXObserverRemoveNotification.restype = AXErrorCode
    app_services.AXObserverGetRunLoopSource.argtypes = [AXObserverRef]
    app_services.AXObserverGetRunLoopSource.restype = CFRunLoopSourceRef

    app_services.AXValueGetTypeID.argtypes = []
    app_services.AXValueGetTypeID.restype = CFTypeID
    app_services.AXValueCreate.argtypes = [ctypes.c_uint32, c_void_p]
    app_services.AXValueCreate.restype = AXValueRef
    app_services.AXValueGetType.argtypes = [AXValueRef]
    app_services.AXValueGetType.restype = ctypes.c_uint32
    app_services.AXValueGetValue.argtypes = [AXValueRef, ctypes.c_uint32, c_void_p]
    app_services.AXValueGetValue.restype = Boolean


_configure_signatures()


@lru_cache(maxsize=1)
def _type_ids() -> dict[str, int]:
    return {
        "string": int(cf.CFStringGetTypeID()),
        "boolean": int(cf.CFBooleanGetTypeID()),
        "number": int(cf.CFNumberGetTypeID()),
        "array": int(cf.CFArrayGetTypeID()),
        "dictionary": int(cf.CFDictionaryGetTypeID()),
        "null": int(cf.CFNullGetTypeID()),
        "ax_element": int(app_services.AXUIElementGetTypeID()),
        "ax_value": int(app_services.AXValueGetTypeID()),
    }


def _default_mode() -> CFStringRef:
    return c_void_p.in_dll(cf, "kCFRunLoopDefaultMode")


def retain(ref: c_void_p | int | None) -> c_void_p | None:
    pointer = _coerce_pointer(ref)
    if pointer is None:
        return None
    cf.CFRetain(pointer)
    return pointer


def release(ref: c_void_p | int | None) -> None:
    pointer = _coerce_pointer(ref)
    if pointer is not None:
        cf.CFRelease(pointer)


def managed_ref(ref: c_void_p | int | None, *, adopt: bool = False) -> weakref.finalize | None:
    pointer = _coerce_pointer(ref)
    if pointer is None:
        return None
    if not adopt:
        cf.CFRetain(pointer)
    return weakref.finalize(_FinalizerAnchor(), release, pointer)


def _coerce_pointer(value: c_void_p | int | None) -> c_void_p | None:
    if value is None:
        return None
    if isinstance(value, c_void_p):
        return value if value.value else None
    if isinstance(value, int):
        return c_void_p(value) if value else None
    raise TypeError(f"Unsupported pointer type: {type(value)!r}")


def _check(status: int, operation: str, *, allow: tuple[int, ...] = ()) -> None:
    if status != 0 and status not in allow:
        raise AXError(status, operation)


def cf_string(text: str) -> CFStringRef:
    encoded = text.encode("utf-8")
    ref = cf.CFStringCreateWithCString(None, encoded, K_CF_STRING_ENCODING_UTF8)
    if not ref:
        raise RuntimeError("CFStringCreateWithCString returned NULL")
    return ref


def string_to_python(ref: CFStringRef) -> str:
    length = int(cf.CFStringGetLength(ref))
    capacity = int(cf.CFStringGetMaximumSizeForEncoding(length, K_CF_STRING_ENCODING_UTF8)) + 1
    buffer = ctypes.create_string_buffer(capacity)
    ok = cf.CFStringGetCString(ref, buffer, capacity, K_CF_STRING_ENCODING_UTF8)
    if not ok:
        raise RuntimeError("CFStringGetCString failed")
    return buffer.value.decode("utf-8")


def python_to_cf(value: Any) -> CFTypeRef:
    if value is None:
        return c_void_p()
    if isinstance(value, bool):
        name = "kCFBooleanTrue" if value else "kCFBooleanFalse"
        return c_void_p.in_dll(cf, name)
    if isinstance(value, int) and not isinstance(value, bool):
        number = ctypes.c_longlong(value)
        return cf.CFNumberCreate(None, K_CF_NUMBER_SINT64_TYPE, byref(number))
    if isinstance(value, float):
        number = c_double(value)
        return cf.CFNumberCreate(None, K_CF_NUMBER_DOUBLE_TYPE, byref(number))
    if isinstance(value, str):
        return cf_string(value)
    if isinstance(value, CGPoint):
        native = _CGPoint(value.x, value.y)
        return app_services.AXValueCreate(K_AX_VALUE_POINT_TYPE, byref(native))
    if isinstance(value, CGSize):
        native = _CGSize(value.width, value.height)
        return app_services.AXValueCreate(K_AX_VALUE_SIZE_TYPE, byref(native))
    if isinstance(value, CGRect):
        native = _CGRect(_CGPoint(value.x, value.y), _CGSize(value.width, value.height))
        return app_services.AXValueCreate(K_AX_VALUE_RECT_TYPE, byref(native))
    if isinstance(value, CFRange):
        native = _CFRange(value.location, value.length)
        return app_services.AXValueCreate(K_AX_VALUE_RANGE_TYPE, byref(native))
    raise TypeError(f"Unsupported Accessibility value: {type(value)!r}")


def cf_to_python(ref: CFTypeRef, *, preserve_ax_elements: bool = False) -> Any:
    pointer = _coerce_pointer(ref)
    if pointer is None:
        return None

    type_id = int(cf.CFGetTypeID(pointer))
    ids = _type_ids()

    if type_id == ids["string"]:
        return string_to_python(pointer)
    if type_id == ids["boolean"]:
        return bool(cf.CFBooleanGetValue(pointer))
    if type_id == ids["number"]:
        if bool(cf.CFNumberIsFloatType(pointer)):
            out = c_double()
            cf.CFNumberGetValue(pointer, K_CF_NUMBER_DOUBLE_TYPE, byref(out))
            return float(out.value)
        out = ctypes.c_longlong()
        cf.CFNumberGetValue(pointer, K_CF_NUMBER_SINT64_TYPE, byref(out))
        return int(out.value)
    if type_id == ids["array"]:
        return [cf_to_python(c_void_p(cf.CFArrayGetValueAtIndex(pointer, i)), preserve_ax_elements=preserve_ax_elements) for i in range(int(cf.CFArrayGetCount(pointer)))]
    if type_id == ids["dictionary"]:
        count = int(cf.CFDictionaryGetCount(pointer))
        keys = (c_void_p * count)()
        values = (c_void_p * count)()
        cf.CFDictionaryGetKeysAndValues(pointer, keys, values)
        result: dict[str, Any] = {}
        for index in range(count):
            key = cf_to_python(c_void_p(keys[index]))
            result[str(key)] = cf_to_python(c_void_p(values[index]), preserve_ax_elements=preserve_ax_elements)
        return result
    if type_id == ids["null"]:
        return None
    if type_id == ids["ax_value"]:
        return ax_value_to_python(pointer)
    if type_id == ids["ax_element"]:
        if preserve_ax_elements:
            retain(pointer)
            return pointer.value
        return f"0x{pointer.value:x}"
    return pointer.value


def ax_value_to_python(value: AXValueRef) -> Any:
    value_type = int(app_services.AXValueGetType(value))

    if value_type == K_AX_VALUE_POINT_TYPE:
        point = _CGPoint()
        app_services.AXValueGetValue(value, value_type, byref(point))
        return {"x": float(point.x), "y": float(point.y)}
    if value_type == K_AX_VALUE_SIZE_TYPE:
        size = _CGSize()
        app_services.AXValueGetValue(value, value_type, byref(size))
        return {"width": float(size.width), "height": float(size.height)}
    if value_type == K_AX_VALUE_RECT_TYPE:
        rect = _CGRect()
        app_services.AXValueGetValue(value, value_type, byref(rect))
        return {
            "x": float(rect.origin.x),
            "y": float(rect.origin.y),
            "width": float(rect.size.width),
            "height": float(rect.size.height),
        }
    if value_type == K_AX_VALUE_RANGE_TYPE:
        range_value = _CFRange()
        app_services.AXValueGetValue(value, value_type, byref(range_value))
        return {"location": int(range_value.location), "length": int(range_value.length)}
    if value_type == K_AX_VALUE_ERROR_TYPE:
        raw = c_int32()
        app_services.AXValueGetValue(value, value_type, byref(raw))
        return {"error": AX_ERROR_NAMES.get(int(raw.value), int(raw.value))}
    return None


def copy_string_array(value: CFArrayRef) -> list[str]:
    count = int(cf.CFArrayGetCount(value))
    items: list[str] = []
    for index in range(count):
        item = c_void_p(cf.CFArrayGetValueAtIndex(value, index))
        items.append(string_to_python(item))
    return items


def is_process_trusted() -> bool:
    return bool(app_services.AXIsProcessTrusted())


def system_wide_element() -> AXUIElementRef:
    element = app_services.AXUIElementCreateSystemWide()
    if not element:
        raise RuntimeError("AXUIElementCreateSystemWide returned NULL")
    return c_void_p(element)


def application_element(pid: int) -> AXUIElementRef:
    element = app_services.AXUIElementCreateApplication(pid)
    if not element:
        raise RuntimeError(f"AXUIElementCreateApplication({pid}) returned NULL")
    return c_void_p(element)


def hash_ref(ref: AXUIElementRef) -> int:
    return int(cf.CFHash(ref))


def pid_for_element(element: AXUIElementRef) -> int | None:
    output = pid_t()
    status = int(app_services.AXUIElementGetPid(element, byref(output)))
    if status == -25212:
        return None
    _check(status, "AXUIElementGetPid")
    return int(output.value)


def copy_attribute_names(element: AXUIElementRef) -> list[str]:
    result = CFArrayRef()
    status = int(app_services.AXUIElementCopyAttributeNames(element, byref(result)))
    _check(status, "AXUIElementCopyAttributeNames")
    try:
        return copy_string_array(result)
    finally:
        release(result)


def copy_parameterized_attribute_names(element: AXUIElementRef) -> list[str]:
    result = CFArrayRef()
    status = int(app_services.AXUIElementCopyParameterizedAttributeNames(element, byref(result)))
    _check(status, "AXUIElementCopyParameterizedAttributeNames", allow=(-25205, -25213))
    if not result:
        return []
    try:
        return copy_string_array(result)
    finally:
        release(result)


def _copy_value(element: AXUIElementRef, attribute: str) -> CFTypeRef | None:
    key = cf_string(attribute)
    try:
        output = CFTypeRef()
        status = int(app_services.AXUIElementCopyAttributeValue(element, key, byref(output)))
        _check(status, f"AXUIElementCopyAttributeValue({attribute})", allow=(-25212, -25205))
        return c_void_p(output.value) if output.value else None
    finally:
        release(key)


def copy_attribute_value(element: AXUIElementRef, attribute: str) -> Any:
    value = _copy_value(element, attribute)
    if value is None:
        return None
    try:
        return cf_to_python(value)
    finally:
        release(value)


def copy_attribute_value_preserving_elements(element: AXUIElementRef, attribute: str) -> Any:
    value = _copy_value(element, attribute)
    if value is None:
        return None
    try:
        return cf_to_python(value, preserve_ax_elements=True)
    finally:
        release(value)


def copy_attribute_values(element: AXUIElementRef, attribute: str, start: int = 0, count: int = 1024) -> list[Any]:
    key = cf_string(attribute)
    try:
        output = CFArrayRef()
        status = int(app_services.AXUIElementCopyAttributeValues(element, key, start, count, byref(output)))
        _check(status, f"AXUIElementCopyAttributeValues({attribute})", allow=(-25212, -25205))
        if not output:
            return []
        try:
            return cf_to_python(output, preserve_ax_elements=True)
        finally:
            release(output)
    finally:
        release(key)


def copy_action_names(element: AXUIElementRef) -> list[str]:
    output = CFArrayRef()
    status = int(app_services.AXUIElementCopyActionNames(element, byref(output)))
    _check(status, "AXUIElementCopyActionNames", allow=(-25206,))
    if not output:
        return []
    try:
        return copy_string_array(output)
    finally:
        release(output)


def perform_action(element: AXUIElementRef, action: str) -> None:
    value = cf_string(action)
    try:
        status = int(app_services.AXUIElementPerformAction(element, value))
        _check(status, f"AXUIElementPerformAction({action})")
    finally:
        release(value)


def is_attribute_settable(element: AXUIElementRef, attribute: str) -> bool:
    key = cf_string(attribute)
    try:
        out = Boolean()
        status = int(app_services.AXUIElementIsAttributeSettable(element, key, byref(out)))
        _check(status, f"AXUIElementIsAttributeSettable({attribute})", allow=(-25205, -25212))
        return bool(out.value)
    finally:
        release(key)


def set_attribute_value(element: AXUIElementRef, attribute: str, value: Any) -> None:
    key = cf_string(attribute)
    native_value = python_to_cf(value)
    created = bool(native_value)
    try:
        status = int(app_services.AXUIElementSetAttributeValue(element, key, native_value))
        _check(status, f"AXUIElementSetAttributeValue({attribute})")
    finally:
        if created and not isinstance(value, bool):
            release(native_value)
        release(key)


def copy_parameterized_attribute_value(element: AXUIElementRef, attribute: str, parameter: Any) -> Any:
    key = cf_string(attribute)
    native_parameter = python_to_cf(parameter)
    created = bool(native_parameter)
    try:
        output = CFTypeRef()
        status = int(app_services.AXUIElementCopyParameterizedAttributeValue(element, key, native_parameter, byref(output)))
        _check(status, f"AXUIElementCopyParameterizedAttributeValue({attribute})")
        try:
            return cf_to_python(output, preserve_ax_elements=True)
        finally:
            release(output)
    finally:
        if created and not isinstance(parameter, bool):
            release(native_parameter)
        release(key)


def focused_application() -> AXUIElementRef | None:
    system = system_wide_element()
    try:
        pointer = copy_attribute_value_preserving_elements(system, ATTRIBUTE_NAMES["focused_application"])
        return c_void_p(pointer) if pointer else None
    finally:
        release(system)


def focused_ui_element() -> AXUIElementRef | None:
    system = system_wide_element()
    try:
        pointer = copy_attribute_value_preserving_elements(system, ATTRIBUTE_NAMES["focused_ui_element"])
        return c_void_p(pointer) if pointer else None
    finally:
        release(system)


def children_for_element(element: AXUIElementRef, *, max_children: int | None = None) -> list[AXUIElementRef]:
    count = max_children if max_children is not None else 4096
    try:
        raw_values = copy_attribute_values(element, ATTRIBUTE_NAMES["children"], 0, count)
    except AXError as exc:
        if exc.code != -25201:  # kAXErrorIllegalArgument
            raise
        # Batched API unsupported — fall back to singular copy
        raw_values = copy_attribute_value_preserving_elements(element, ATTRIBUTE_NAMES["children"])
        if not isinstance(raw_values, list):
            return []
    result = [c_void_p(item) for item in raw_values if item]
    if max_children is not None:
        result = result[:max_children]
    return result


def current_run_loop() -> CFRunLoopRef:
    return cf.CFRunLoopGetCurrent()


def add_run_loop_source(run_loop: CFRunLoopRef, source: CFRunLoopSourceRef) -> None:
    cf.CFRunLoopAddSource(run_loop, source, _default_mode())


def remove_run_loop_source(run_loop: CFRunLoopRef, source: CFRunLoopSourceRef) -> None:
    cf.CFRunLoopRemoveSource(run_loop, source, _default_mode())


def run_loop_run() -> None:
    cf.CFRunLoopRun()


def run_loop_stop(run_loop: CFRunLoopRef) -> None:
    cf.CFRunLoopStop(run_loop)


AXObserverCallback = ctypes.CFUNCTYPE(None, AXObserverRef, AXUIElementRef, CFStringRef, c_void_p)


def create_observer(pid: int, callback: AXObserverCallback) -> AXObserverRef:
    observer = AXObserverRef()
    create = getattr(app_services, "AXObserverCreate")
    create.argtypes = [pid_t, AXObserverCallback, POINTER(AXObserverRef)]
    create.restype = AXErrorCode
    status = int(create(pid, callback, byref(observer)))
    _check(status, f"AXObserverCreate({pid})")
    return c_void_p(observer.value)


def observer_source(observer: AXObserverRef) -> CFRunLoopSourceRef:
    source = app_services.AXObserverGetRunLoopSource(observer)
    if not source:
        raise RuntimeError("AXObserverGetRunLoopSource returned NULL")
    return c_void_p(source)


def add_notification(observer: AXObserverRef, element: AXUIElementRef, notification: str) -> None:
    name = cf_string(notification)
    try:
        status = int(app_services.AXObserverAddNotification(observer, element, name, None))
        _check(status, f"AXObserverAddNotification({notification})", allow=(-25209,))
    finally:
        release(name)


def remove_notification(observer: AXObserverRef, element: AXUIElementRef, notification: str) -> None:
    name = cf_string(notification)
    try:
        status = int(app_services.AXObserverRemoveNotification(observer, element, name))
        _check(status, f"AXObserverRemoveNotification({notification})", allow=(-25210,))
    finally:
        release(name)


def borrowed_element(ref: int) -> AXUIElementRef:
    pointer = c_void_p(ref)
    retain(pointer)
    return pointer


def iter_default_attributes() -> Iterator[str]:
    yield from (
        ATTRIBUTE_NAMES["role"],
        ATTRIBUTE_NAMES["subrole"],
        ATTRIBUTE_NAMES["title"],
        ATTRIBUTE_NAMES["description"],
        ATTRIBUTE_NAMES["help"],
        ATTRIBUTE_NAMES["value"],
        ATTRIBUTE_NAMES["value_description"],
        ATTRIBUTE_NAMES["enabled"],
        ATTRIBUTE_NAMES["focused"],
        ATTRIBUTE_NAMES["position"],
        ATTRIBUTE_NAMES["size"],
        ATTRIBUTE_NAMES["identifier"],
    )
