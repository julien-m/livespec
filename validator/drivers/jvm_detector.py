# LiveSpec traceability anchors
# @spec(FR-004)

"""Parse pitest ``mutations.xml`` output for the JVM mutation report."""

# @spec FR-004: pitest XML parser exposing KILLED/SURVIVED/TIMED_OUT counts.
# — .specs/features/022-driver-jvm/spec.md#fr-004
# FR-002 / FR-003 Python helpers were removed on 2026-10-12: build-tool and
# plugin detection is owned by livespec/drivers/scripts/jvm-*.sh.

from __future__ import annotations

import re

# pitest emits these status strings inside <mutation status="..."> elements.
# We normalise to lowercase keys; pitest uses uppercase in practice.
_PITEST_STATUSES: tuple[str, ...] = (
    "killed",
    "survived",
    "timed_out",
    "no_coverage",
    "memory_error",
    "run_error",
)

# Regex extraction avoids xml.etree.ElementTree because some Python
# distributions ship a broken pyexpat and pitest reports are shallow.
_MUTATION_STATUS_RE = re.compile(
    r"<mutation\b[^>]*\bstatus\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
# Sniff for tags that look like XML at all so we can short-circuit malformed
# input back to "no data" rather than emit accidental matches.
_XML_TAG_RE = re.compile(r"<\s*[A-Za-z]")


def parse_pitest_xml(xml_text: str) -> dict[str, int]:
    """Extract mutation counts from a pitest ``mutations.xml`` report.

    pitest emits one ``<mutation status="...">`` element per mutation under a
    root ``<mutations>`` document. Recognised status strings (case-insensitive)
    are KILLED, SURVIVED, TIMED_OUT, NO_COVERAGE, MEMORY_ERROR, RUN_ERROR.

    The parser is regex-based — pitest XML is shallow (no nested information
    we care about) and the stdlib ElementTree backend depends on pyexpat
    which is unavailable on some Python distributions.

    Args:
        xml_text: Captured contents of ``mutations.xml``.

    Returns:
        A dictionary with integer counts for every recognised status. Missing
        statuses default to ``0``. Returns all-zero counts when the input is
        empty, doesn't look like XML, or has no recognised status attributes.
    """
    counts: dict[str, int] = {status: 0 for status in _PITEST_STATUSES}
    text = xml_text.strip()
    if not text:
        return counts
    # Bail when the input contains no XML-shaped tags at all so junk strings
    # never accidentally produce non-zero counts.
    if not _XML_TAG_RE.search(text):
        return counts

    for match in _MUTATION_STATUS_RE.finditer(text):
        normalised = match.group(1).strip().lower()
        if normalised in counts:
            counts[normalised] += 1

    return counts
