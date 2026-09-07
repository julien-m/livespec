"""Recognize bounded current and legacy lifecycle metadata, never body examples."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

import yaml

_YAML_FIELD = re.compile(r"^(status|updated|Status|Updated):\s*(.*?)\s*$")
_HEADER_FIELD = re.compile(r"^(?:- )?\*\*(Status|Updated|status|updated):\*\*\s*(.*?)\s*$")
_HEADING = re.compile(r"^ {0,3}(#{1,6}) (.+?)\s*$")
_THEMATIC = re.compile(r"^ {0,3}(?:-\s*){3,}$|^ {0,3}(?:\*\s*){3,}$|^ {0,3}(?:_\s*){3,}$")


@dataclass(frozen=True)
class LifecycleField:
    """One complete lifecycle field at its exact original line position."""

    index: int
    key: str
    value: str


@dataclass(frozen=True)
class LifecycleMetadata:
    """Recognized fields shared by finalization and normative identity."""

    lines: tuple[str, ...]
    frontmatter_end: int | None
    frontmatter_fields: tuple[LifecycleField, ...]
    header_fields: tuple[LifecycleField, ...]


def _frontmatter(lines: tuple[str, ...]) -> int | None:
    if not lines or lines[0].rstrip("\r\n") != "---":
        return None
    endings = [i for i in range(1, len(lines)) if lines[i].rstrip("\r\n") == "---"]
    if not endings:
        raise ValueError("unclosed initial YAML frontmatter")
    end = endings[0]
    raw = "".join(lines[1:end])
    try:
        value = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError("malformed YAML frontmatter") from exc
    if not isinstance(value, dict):
        raise ValueError("frontmatter must be a mapping")
    keys = re.findall(r"^([A-Za-z_][A-Za-z_0-9-]*):", raw, re.MULTILINE)
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate YAML metadata")
    return end


def _visible_lines(lines: tuple[str, ...], start: int) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    fence: str | None = None
    comment = False
    for index in range(start, len(lines)):
        bare = lines[index].rstrip("\r\n")
        if fence is not None:
            if re.fullmatch(
                r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*", bare
            ):
                fence = None
            continue
        if comment or "<!--" in bare:
            comment = "-->" not in bare
            continue
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})", bare)
        if opening:
            fence = opening.group(1)
        else:
            result.append((index, bare))
    return result


def _band(visible: list[tuple[int, str]], begin: int, explicit: bool) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    for index, bare in visible:
        if index <= begin:
            continue
        heading = _HEADING.fullmatch(bare)
        if _THEMATIC.fullmatch(bare) or (heading and (not explicit or len(heading.group(1)) <= 2)):
            break  # The first section/rule boundary ends this metadata band.
        result.append((index, bare))
    return result


def _fields(visible: list[tuple[int, str]], pattern: re.Pattern[str]) -> tuple[LifecycleField, ...]:
    fields = tuple(
        LifecycleField(index, match.group(1).lower(), match.group(2))
        for index, bare in visible
        if (match := pattern.fullmatch(bare))
    )
    keys = [field.key for field in fields]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate lifecycle metadata")
    return fields


def lifecycle_metadata(text: str) -> LifecycleMetadata:
    """Return exact fields in valid YAML and one explicit or legacy header band.

    Raises ValueError for malformed or duplicate metadata; callers must retain
    every source byte or block, rather than guess which field is authoritative.
    """
    lines = tuple(text.splitlines(keepends=True))
    end = _frontmatter(lines)
    visible = _visible_lines(lines, end + 1 if end is not None else 0)
    headings = [(i, match) for i, line in visible if (match := _HEADING.fullmatch(line))]
    explicit = [i for i, match in headings if match.group(1) == "##" and match.group(2) == "Header"]
    if len(explicit) > 1:
        raise ValueError("duplicate Header section")
    title = headings[0][0] if headings and headings[0][1].group(1) == "#" else None
    if explicit:
        position = 1 if title is not None else 0
        if len(headings) <= position or headings[position][0] != explicit[0]:
            raise ValueError("Header section is outside introductory metadata")
    legacy = _fields(_band(visible, title, False), _HEADER_FIELD) if title is not None else ()
    if explicit and legacy:
        raise ValueError("competing explicit and legacy lifecycle headers")
    header = _fields(_band(visible, explicit[0], True), _HEADER_FIELD) if explicit else legacy
    yaml_fields = _fields([(i, lines[i].rstrip("\r\n")) for i in range(1, end or 0)], _YAML_FIELD)
    return LifecycleMetadata(lines, end, yaml_fields, header)


def scalar_value(field: LifecycleField) -> str | None:
    """Return a single scalar field value, rejecting YAML containers/block scalars."""
    try:
        value = yaml.safe_load(field.value)
    except yaml.YAMLError:
        return None
    return cast(str, value) if isinstance(value, str) else None
