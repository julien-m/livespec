"""Versioned lifecycle-only normalization; raw source remains proof provenance (078 FR-004)."""

from __future__ import annotations

import hashlib
import re

from .lifecycle_metadata import lifecycle_metadata

NORMATIVE_IDENTITY_VERSION = "2"


def normative_text(text: str, *, lifecycle_document: bool = False) -> str:
    """Normalize only recognized metadata positions in selected spec/plan documents.

    Newlines and all normative body lines are preserved, including Status examples.
    Creation dates, titles, IDs and nonmetadata frontmatter remain bound.
    """
    if not lifecycle_document:
        return text
    try:
        metadata = lifecycle_metadata(text)
    except ValueError:
        return text
    fields = {
        field.index: field
        for field in (*metadata.frontmatter_fields, *metadata.header_fields)
        if _valid_scalar(field.key, field.value)
    }
    result: list[str] = []
    for index, line in enumerate(metadata.lines):
        if index in fields:
            # Keep line positions and endings stable for exact citation provenance.
            ending = line[len(line.rstrip("\r\n")) :]
            result.append("<lifecycle-metadata>" + ending)
        else:
            result.append(line)
    return "".join(result)


def normative_hash(text: str, *, lifecycle_document: bool = False) -> str:
    """Hash versioned normative bytes; callers separately retain the raw source hash."""
    data = (
        NORMATIVE_IDENTITY_VERSION
        + "\n"
        + normative_text(text, lifecycle_document=lifecycle_document)
    )
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _valid_scalar(key: str, value: str) -> bool:
    """Only ordinary lifecycle values can be omitted; structured/ambiguous data stays bound."""
    if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
        value = value[1:-1]
    if key.lower() == "status":
        return value in {
            "Draft",
            "Planned",
            "Approved",
            "In Progress",
            "Implemented",
            "Deprecated",
            "Blocked",
        }
    return bool(
        re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2}))?", value)
    )
