"""Versioned execution projection of bounded, generated registry bookkeeping."""

from __future__ import annotations

import re

REGISTRY_PROJECTION_VERSION = "1"
_MARKER = r"<!-- finalize:spec-[a-z-]+:\d{4}-\d{2}-\d{2}:[0-9a-f]{8} -->"
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_STATUSES = "Draft|Planned|Approved|In Progress|Implemented|Deprecated|Review|Blocked"


def registry_text(relative: str, text: str, feature: str) -> str:
    """Project only the two finalizer registries; prose and fenced examples stay bound.

    README activity is a generated table; feature identity, title, creation date and
    spec link remain inputs. Only the selected row's lifecycle cells are normalized.
    Changelog summaries immediately paired with finalize markers are generated history.
    Unmarked entries, bodies and all links outside projected history remain normative.
    """
    if relative not in {".specs/README.md", ".specs/changelog.md"}:
        return text
    chunks: list[str] = []
    plain: list[str] = []
    fence: str | None = None
    for line in text.splitlines(keepends=True):
        opening = _FENCE.match(line)
        if fence is None and opening:
            chunks.append(_project(relative, "".join(plain), feature))
            plain = []
            fence = opening.group(1)
            chunks.append(line)
        elif fence is not None:
            chunks.append(line)
            if re.fullmatch(
                r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*", line
            ):
                fence = None
        else:
            plain.append(line)
    chunks.append(_project(relative, "".join(plain), feature))
    return "".join(chunks).rstrip() + "\n"


def _project(relative: str, text: str, feature: str) -> str:
    if relative == ".specs/changelog.md":
        # Match the exact two-line global summary emitted by build_global_changelog,
        # including its adjacent spacing; any manual body remains in the projection.
        return re.sub(
            rf"(?:\n\n)?^## \d{{4}}-\d{{2}}-\d{{2}} — [^\n]+\n{_MARKER}\n(?:\n)?",
            "",
            text,
            flags=re.M,
        )
    text = re.sub(rf"\n\n{_MARKER}\n", "\n", text)
    text = re.sub(
        r"^> Last updated: \d{4}-\d{2}-\d{2}$", "> Last updated: <generated>", text, flags=re.M
    )
    number = re.escape(feature.split("-", 1)[0])
    # Exact six-column registry row, bounded to the selected feature section.
    row = (
        rf"^(\| {number} \| [^|\n]+ \| )(?:{_STATUSES})"
        r"( \| \d{4}-\d{2}-\d{2} \| )\d{4}-\d{2}-\d{2}( \| [^|\n]+ \|)$"
    )
    features = r"(<!-- readme:features:start -->\n)(.*?)(<!-- readme:features:end -->)"
    text = re.sub(
        features,
        lambda m: m[1] + re.sub(row, r"\1<status>\2<updated>\3", m[2], flags=re.M) + m[3],
        text,
        flags=re.S,
    )
    # Preserve malformed/non-table content rather than silently dropping prose.
    activity = (
        r"(<!-- readme:activity:start -->\n)((?:\|[^\n]*\|\n)*)(<!-- readme:activity:end -->)"
    )
    return re.sub(activity, r"\1<generated-activity>\n\3", text)
