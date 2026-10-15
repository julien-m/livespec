"""Evidence classes of plan steps: proof required locally or pending release (feature 090).

A plan step may declare ``**Evidence class:** local`` (the default) or ``release``. Steps are
``Step N`` headings inside the Implementation Plan (or Steps) section, or its top-level
numbered items when it has no ``Step`` heading. A step is identified by the number in its
title. Every pattern here is linear in the line length: plans and implementation maps are
read on every goal render.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

EVIDENCE_CLASSES = ("local", "release")
# Code fence of up to three spaces of indentation and its info string (checked in Python).
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
# ATX heading marker; the closing hashes are removed in Python (no regex backtracking).
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.*)$")
_PLAN_SECTION = re.compile(r"implementation (plan|steps)", re.IGNORECASE)
# "Step 2 — Title", "3. Step 2.5: Title" or "Step — Title" (numbered by position). A number
# part has at most nine digits, like a Markdown list marker; a longer one is not a label.
_STEP_HEADING = re.compile(r"^(?:\d+[.)] +)?step\b *(\d{1,9}(?:\.\d{1,9})*(?!\d))?", re.IGNORECASE)
# Top-level numbered item "1. Title" or "1) Title".
_NUMBERED_ITEM = re.compile(r"^(\d{1,9})[.)] +(\S.*)$")
# The one declaration syntax; the value runs to the end of the line and is stripped after.
_CLASS = r"\*\*Evidence class:?\*\*:?(.*)"
_CLASS_LINE = re.compile(r"^ *(?:> *)*(?:[-*] +)?" + _CLASS, re.IGNORECASE)
_INLINE_CLASS = re.compile(_CLASS, re.IGNORECASE)
# Any other "Evidence class:" mention (hyphen, no-break space, HTML tags before the colon) is
# a declaration the parser cannot bind to a step.
_ANY_CLASS = re.compile(r"[eé]vidence[\s_-]*class(?:[*_\s]|</?\w+>)*:", re.IGNORECASE)
_INLINE_CODE = re.compile(r"`[^`]*`")  # Quoted syntax in prose is not a declaration.


@dataclass(frozen=True)
class PlanStep:
    """One step of the implementation plan and its declared evidence classes."""

    label: str
    title: str
    name: str
    classes: tuple[str, ...]

    @property
    def evidence_class(self) -> str:
        """The single declared class, ``local`` when the step declares none."""
        return self.classes[0] if self.classes else "local"


def plain(text: str) -> str:
    """Text without emphasis or code marks and with single spaces."""
    return " ".join(re.sub(r"[*`_~]", "", text).split())


def title_text(text: str) -> str:
    """A title without emphasis marks; underscores in names are kept."""
    return " ".join(re.sub(r"[*`]", "", text).split())


def normalize_label(label: str) -> str:
    """``02.50`` and ``2.50`` are the same step label (leading zeros dropped)."""
    return ".".join(part.lstrip("0") or "0" for part in label.split(".")) if label else label


def heading(line: str) -> tuple[int, str] | None:
    """Depth and title of an ATX heading line, closing hashes removed."""
    match = _HEADING.match(line)
    if not match:
        return None
    title = match.group(2).rstrip()
    bare = title.rstrip("#")
    if bare != title and (not bare or bare[-1] in " \t"):
        title = bare.rstrip()
    return len(match.group(1)), title


def _strip_comments(line: str, comment: bool) -> tuple[str, bool]:
    """Remove HTML comments from one line; ``comment`` is True inside a multi-line comment.

    Linear ``str.find`` scan (no regex). An unclosed ``<!--`` opens a multi-line comment
    only at the start of a line, as in rendered Markdown; elsewhere (inline code) it stays text.
    """
    kept: list[str] = []
    position = 0
    if comment:
        end = line.find("-->")
        if end < 0:
            return "", True
        position = end + 3
    while True:
        start = line.find("<!--", position)
        if start < 0:
            kept.append(line[position:])
            return "".join(kept), False
        end = line.find("-->", start + 4)
        if end >= 0:
            kept.append(line[position:start])
            position = end + 3
        elif not "".join(kept).strip() and not line[position:start].strip():
            return "".join(kept), True
        else:
            kept.append(line[position:])
            return "".join(kept), False


def unfenced(text: str) -> Iterator[str]:
    """Rendered lines of a Markdown document: no code fence or HTML comment content."""
    fence, comment = "", False
    for line in text.splitlines():
        opening = _FENCE.match(line)
        marker, info = opening.groups() if opening else ("", "")
        if fence:
            # A closing fence repeats the opening character and has nothing after it.
            if marker[:1] == fence[0] and len(marker) >= len(fence) and not info.strip():
                fence = ""
            continue
        # A backtick info string cannot hold a backtick: such a line is text, not a fence.
        if marker and not comment and not (marker[0] == "`" and "`" in info):
            fence = marker
            continue
        visible, comment = _strip_comments(line, comment)
        yield visible


def _step_name(title: str) -> str:
    """The title without its ``Step N`` prefix and separator: what a proof row must name."""
    rest = _STEP_HEADING.sub("", title, count=1)
    return rest.lstrip(" -\u2014\u2013:.").strip() or title


class _StepReader:
    """Line-by-line reader of the Implementation Plan section."""

    def __init__(self) -> None:
        self.steps: list[PlanStep] = []
        self.orphans: list[str] = []
        self.unbound: list[str] = []
        self._label, self._title, self._name = "", "", ""
        self._classes: list[str] = []
        self._section_level = 0
        self._step_headings = False  # Step headings found: numbered items are their content.

    def finish(self) -> None:
        """Close the step being read at the end of the section or document."""
        if self._title:
            label = normalize_label(self._label) or str(len(self.steps) + 1)
            self.steps.append(PlanStep(label, self._title, self._name, tuple(self._classes)))
        self._label, self._title, self._name, self._classes = "", "", "", []

    def _open(self, label: str, title: str, name: str) -> None:
        self.finish()
        self._label, self._title, self._name = label, title, name

    def heading(self, depth: int, title: str) -> None:
        """Enter or leave the plan section, or open a step on a ``Step`` heading."""
        self._flag_unbound(title)
        if self._section_level and depth <= self._section_level:
            self.finish()
            self._section_level = 0
        if not self._section_level and _PLAN_SECTION.search(title):
            self._section_level, self._step_headings = depth, False
            return
        step = _STEP_HEADING.match(plain(title)) if self._section_level else None
        if step:
            label = step.group(1) or ""
            self._open(label, title_text(title), _step_name(title_text(title)))
            self._step_headings = True

    def line(self, line: str) -> None:
        """Record an evidence class line, or open a step on a top-level numbered item."""
        declared = _CLASS_LINE.match(line)
        if declared:
            self._declare(declared.group(1))
            return
        numbered = self._section_level and not self._step_headings
        item = _NUMBERED_ITEM.match(line) if numbered else None
        if not item:
            self._flag_unbound(line)
            return
        inline = _INLINE_CLASS.search(item.group(2))
        text = item.group(2)[: inline.start()] if inline else item.group(2)
        self._flag_unbound(text)
        self._open(item.group(1), title_text(text), title_text(text))
        if inline:
            self._declare(inline.group(1))

    def _flag_unbound(self, text: str) -> None:
        if _ANY_CLASS.search(_INLINE_CODE.sub("", text)):
            self.unbound.append(text.strip())

    def _declare(self, value: str) -> None:
        target = self._classes if self._title else self.orphans
        target.append(plain(value).lower())


def _read_steps(text: str) -> _StepReader:
    reader = _StepReader()
    for line in unfenced(text):
        parsed = heading(line)
        if parsed:
            reader.heading(*parsed)
        else:
            reader.line(line)
    reader.finish()
    return reader


def plan_steps(text: str) -> tuple[list[PlanStep], list[str]]:
    """Steps of the Implementation Plan section and evidence classes declared outside a step."""
    reader = _read_steps(text)
    return reader.steps, reader.orphans


# @spec FR-002: Evidence class parsing and validation
#   — .specs/features/090-minimal-plan-scope/spec.md#fr-002
def evidence_class_errors(text: str) -> list[str]:
    """Validation errors: unknown or repeated class, unbound declaration, duplicate step."""
    reader = _read_steps(text)
    steps = reader.steps
    errors = [
        f"Evidence class '{value}' is declared outside an implementation plan step"
        for value in reader.orphans
    ]
    errors.extend(
        f"Evidence class declaration not recognised: '{line[:80]}' "
        "(write `**Evidence class:** local|release` on its own line under the step)"
        for line in reader.unbound
    )
    labels = [step.label for step in steps]
    errors.extend(
        f"Step {label} appears {labels.count(label)} times; number plan steps uniquely"
        for label in sorted(set(labels))
        if labels.count(label) > 1 and any(s.classes for s in steps if s.label == label)
    )
    for step in steps:
        if len(step.classes) > 1:
            errors.append(
                f"Step {step.label} declares {len(step.classes)} evidence classes; "
                "split the step so each has one"
            )
        errors.extend(
            f"Step {step.label} has unknown evidence class '{value}' "
            f"(expected one of: {', '.join(EVIDENCE_CLASSES)})"
            for value in step.classes
            if value not in EVIDENCE_CLASSES
        )
    return errors
