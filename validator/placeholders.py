"""Placeholder resolver for verify-output rules.

# @spec FR-011: placeholder resolver — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-011
"""

from __future__ import annotations

import re

_PLACEHOLDER_RE = re.compile(r"<(feature|date|path)>")


def resolve(s: str, *, feature: str | None, run_date: str) -> str:
    """Substitute placeholders ``<feature>``, ``<date>``, ``<path>``.

    ``<path>`` is a documented passthrough (left as-is) because rules use it
    inside larger path templates (e.g. ``<path>/spec.md``) where the caller
    supplies the prefix.

    The ``<date>`` value MUST come from the run artifact's timestamp
    (EC-006). The caller passes ``run_date`` for that purpose.

    Args:
        s: Raw rule payload string.
        feature: Active feature directory name or None.
        run_date: Date portion of the artifact timestamp (YYYY-MM-DD).

    Returns:
        The string with all known placeholders substituted.
    """

    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
        if token == "feature":
            return feature or "<feature>"
        if token == "date":
            return run_date
        # token == "path" — passthrough.
        return "<path>"

    return _PLACEHOLDER_RE.sub(repl, s)


def run_date_from_timestamp(timestamp: str) -> str:
    """Extract the YYYY-MM-DD date portion from an ISO timestamp."""
    if "T" in timestamp:
        return timestamp.split("T", 1)[0]
    return timestamp[:10]


__all__ = ["resolve", "run_date_from_timestamp"]
