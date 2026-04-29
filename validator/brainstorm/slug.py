"""Slug normalization and NNN feature-number allocation.

Implements the slug normalization contract documented in plan.md:
`lowercase → NFKD ASCII fold → [^a-z0-9]+ collapse to '-' →
strip leading/trailing '-'`. Empty result raises SlugEmptyError.

NNN allocation walks an `existing_dirs` list of `.specs/features/`
directories, parses leading 3-digit numbers, then assigns the
lowest free NNN >= max(existing)+1 to each proposed slug in the
order dictated by `index_order` (or alphabetical fallback).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from pathlib import Path


class SlugEmptyError(ValueError):
    """Raised when slug normalization yields an empty string."""


_NON_SLUG = re.compile(r"[^a-z0-9]+")


# @spec FR-009: Slug normalization — .specs/features/012-brainstorm-ingestion/spec.md#fr-009
def normalize_slug(raw: str) -> str:
    """Normalize a raw flow name to a kebab-case ASCII slug.

    Steps: lowercase → NFKD Unicode fold (drop combining marks) →
    replace any non-[a-z0-9] run with '-' → strip leading/trailing '-'.
    """
    if not raw:
        raise SlugEmptyError("empty input")
    folded = unicodedata.normalize("NFKD", raw)
    ascii_only = "".join(c for c in folded if not unicodedata.combining(c))
    lowered = ascii_only.lower()
    slug = _NON_SLUG.sub("-", lowered).strip("-")
    if not slug:
        raise SlugEmptyError(f"slug empty after normalization: {raw!r}")
    return slug


def _parse_existing_nnns(existing_dirs: Sequence[Path]) -> set[int]:
    """Extract leading NNN numbers from feature dir names."""
    used: set[int] = set()
    for d in existing_dirs:
        m = re.match(r"^(\d{3})-", d.name)
        if m:
            used.add(int(m.group(1)))
    return used


# @spec FR-009: NNN allocation — .specs/features/012-brainstorm-ingestion/spec.md#fr-009
def allocate_nnn(
    existing_dirs: Sequence[Path],
    proposed_slugs: list[str],
    index_order: list[str] | None = None,
) -> dict[str, str]:
    """Map each proposed slug to a 3-digit NNN string.

    Honors `index_order` when provided (entries not in order are
    appended in their original order at the end). Skips NNNs already
    consumed by `existing_dirs`. Slugs already present in
    `existing_dirs` (matching `NNN-<slug>`) are NOT included in the
    result map (caller decides skip/replace policy).
    """
    used = _parse_existing_nnns(existing_dirs)
    existing_slugs = {
        d.name.split("-", 1)[1]
        for d in existing_dirs
        if re.match(r"^\d{3}-", d.name)
    }

    if index_order:
        ordered: list[str] = []
        seen: set[str] = set()
        for s in index_order:
            ns = normalize_slug(s)
            if ns in proposed_slugs and ns not in seen:
                ordered.append(ns)
                seen.add(ns)
        for s in proposed_slugs:
            if s not in seen:
                ordered.append(s)
                seen.add(s)
    else:
        ordered = sorted(proposed_slugs)

    result: dict[str, str] = {}
    next_n = 1
    for slug in ordered:
        if slug in existing_slugs:
            continue
        while next_n in used:
            next_n += 1
        result[slug] = f"{next_n:03d}"
        used.add(next_n)
        next_n += 1
    return result
