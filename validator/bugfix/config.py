"""Parse the optional `.specs/bugfix.yaml` diff thresholds (feature 084 FR-006)."""

from __future__ import annotations

import yaml

from .models import DEFAULT_MAX_FILES, DEFAULT_MAX_LINES, BugfixConfigError, BugfixLimits

CONFIG_PATH = ".specs/bugfix.yaml"
_KEYS = ("max_files", "max_lines")


# @spec FR-006: Configurable diff thresholds
#   — .specs/features/084-bugfix-lane/spec.md#fr-006
def parse_limits(text: str | None, source: str) -> BugfixLimits:
    """Return thresholds from the configuration text, or the defaults when it is absent.

    The caller passes the file content at the base revision, so a correction can
    never raise the limits that judge it.

    Args:
        text: YAML content, or None when the file does not exist.
        source: Human-readable origin used in errors and reports.

    Returns:
        Limits tagged with their source, or the defaults.

    Raises:
        BugfixConfigError: Unreadable YAML, unknown key, or a non-positive-integer value.
    """
    if text is None:
        return BugfixLimits()
    raw = _mapping(text, source)
    values: dict[str, int] = {"max_files": DEFAULT_MAX_FILES, "max_lines": DEFAULT_MAX_LINES}
    for key, value in raw.items():  # pyright: ignore[reportUnknownVariableType]
        if key not in _KEYS:
            raise BugfixConfigError(f"{source}: unknown key {key!r}")
        # bool is an int subclass; `max_files: true` must not mean 1.
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise BugfixConfigError(f"{source}: {key} must be a positive integer")
        values[str(key)] = value
    return BugfixLimits(values["max_files"], values["max_lines"], source)


def _mapping(text: str, source: str) -> dict[object, object]:
    try:
        raw: object = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise BugfixConfigError(f"{source}: unreadable ({exc})") from exc
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise BugfixConfigError(f"{source}: expected a mapping of {', '.join(_KEYS)}")
    return dict(raw)  # pyright: ignore[reportUnknownArgumentType]
