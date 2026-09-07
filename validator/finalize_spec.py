"""Strict lifecycle-only specification updates without normative body mutations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from .finalize_receipt import FinalizeError
from .lifecycle_metadata import lifecycle_metadata, scalar_value

if TYPE_CHECKING:  # ApplyRequest imports builders through finalize_registry.
    from .finalize import ApplyRequest


@dataclass(frozen=True)
class _LifecycleSlots:
    lines: tuple[str, ...]
    status: int
    header: int
    updated: int | None
    status_value: str


def _lifecycle_slots(content: str) -> _LifecycleSlots:
    metadata = lifecycle_metadata(content)
    frontmatter = {field.key: field for field in metadata.frontmatter_fields}
    header = {field.key: field for field in metadata.header_fields}
    status = frontmatter.get("status")
    if metadata.frontmatter_end is None or status is None or "status" not in header:
        raise ValueError("missing initial YAML or recognized header status")
    value = scalar_value(status)
    if value is None or not value.strip() or scalar_value(header["status"]) is None:
        raise ValueError("non-scalar lifecycle status")
    updated = frontmatter.get("updated")
    return _LifecycleSlots(
        metadata.lines,
        status.index,
        header["status"].index,
        updated.index if updated is not None else None,
        value,
    )


def _read_slots(path: Path) -> _LifecycleSlots:
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            return _lifecycle_slots(stream.read())
    except (OSError, UnicodeError, ValueError) as exc:
        raise FinalizeError(
            f"spec status anchors missing or non-standard in {path}: {exc}",
            subtype="state_invalid",
        ) from exc


def spec_status_pending(path: Path, request: ApplyRequest) -> bool:
    """Check whether either actual lifecycle status slot needs updating."""
    slots = _read_slots(path)
    return (
        slots.status_value != request.status
        or slots.lines[slots.header].rstrip("\r\n") != f"- **Status:** {request.status}"
    )


# @spec FR-002: Preserve every normative body byte during lifecycle finalization
# — .specs/features/058-deterministic-finalization/spec.md#fr-002
def build_spec_status(path: Path, request: ApplyRequest, marker: str, today: date) -> str:
    """Update recognized lifecycle slots only; preserve all historical comments.

    The marker argument remains for builder-call compatibility but is intentionally
    unused: payload markers belong only to generated registries, never spec.md.
    """
    slots = _read_slots(path)
    lines = list(slots.lines)
    replacements = {
        slots.status: f"status: {request.status or ''}",
        slots.header: f"- **Status:** {request.status or ''}",
    }
    if slots.updated is not None:
        replacements[slots.updated] = f"updated: {today.isoformat()}"
    for index, value in replacements.items():
        # Preserve original line endings and every non-lifecycle byte.
        ending = lines[index][len(lines[index].rstrip("\r\n")) :]
        lines[index] = value + ending
    return "".join(lines)
