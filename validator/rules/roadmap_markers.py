"""Validate roadmap HTML marker pairs in roadmap files."""

from __future__ import annotations

MARKER_PAIRS = [
    ("<!-- roadmap:mvp:start -->", "<!-- roadmap:mvp:end -->"),
    ("<!-- roadmap:postmvp:start -->", "<!-- roadmap:postmvp:end -->"),
    ("<!-- roadmap:future:start -->", "<!-- roadmap:future:end -->"),
    ("<!-- roadmap:deferred:start -->", "<!-- roadmap:deferred:end -->"),
]


def validate_roadmap_markers(content: str) -> list[str]:
    """Return errors for missing roadmap marker pairs.

    Args:
        content: Raw markdown content of the roadmap file.

    Returns:
        List of error messages for each missing start/end marker.
    """
    errors: list[str] = []
    for start, end in MARKER_PAIRS:
        if start not in content:
            errors.append(f"Missing marker: {start}")
        if end not in content:
            errors.append(f"Missing marker: {end}")
    return errors
