"""Define closed JSON value types for goal control-plane documents."""

from __future__ import annotations

from copy import deepcopy
from typing import TypeAlias, TypeGuard

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


def is_json_value(value: object) -> TypeGuard[JsonValue]:
    """Return whether a runtime value is representable by JSON.

    Args:
        value: Untrusted value from a direct API caller or JSON decoder.

    Returns:
        True when the complete recursive value has a closed JSON shape.
    """
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list):
        return all(is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and is_json_value(item) for key, item in value.items())
    return False


def copy_json_object(value: object) -> JsonObject | None:
    """Return an isolated JSON object copy when the boundary value is valid.

    Args:
        value: Untrusted external or direct-API value.

    Returns:
        A deep copy for a JSON object, otherwise None. The caller owns the copy.
    """
    if not isinstance(value, dict):
        return None
    copied: JsonObject = {}
    for key, item in value.items():
        if not isinstance(key, str) or not is_json_value(item):
            return None
        copied[key] = deepcopy(item)
    return copied


__all__ = ["JsonObject", "JsonScalar", "JsonValue", "copy_json_object", "is_json_value"]
