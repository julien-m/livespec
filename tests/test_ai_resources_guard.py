# @spec FR-003: No forbidden fallback, FR-006: Guard test
#   .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-003

"""Guard against hard-coded ai-ressources locations in ``validator/`` (feature 085, AC-009).

The patterns are the request grep: they match a home-relative ``projects/ai-ressources``
location and a ``<something>.parent / "ai-ressources"`` sibling of the checkout, but not
the logical ``ai-ressources/<path>`` identifiers of the rule catalogs.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Alternatives: the textual path, the pathlib home form, and the checkout-sibling form.
FORBIDDEN_FALLBACK_RE = re.compile(
    r'projects/ai-ressources|"projects" / "ai-ressources"|parent / "ai-ressources"'
)


def forbidden_fallbacks(tree: Path) -> list[str]:
    """Return ``file:line`` for every forbidden fallback in the Python files of ``tree``.

    Args:
        tree: Directory scanned recursively for ``*.py`` files.

    Returns:
        One ``<path relative to tree>:<line>`` entry per matching line, sorted.
    """
    findings: list[str] = []
    for path in sorted(tree.rglob("*.py")):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for number, line in enumerate(lines, start=1):
            if FORBIDDEN_FALLBACK_RE.search(line):
                findings.append(f"{path.relative_to(tree).as_posix()}:{number}")
    return findings


def test_validator_has_no_forbidden_fallback() -> None:
    assert forbidden_fallbacks(REPO / "validator") == []


def test_reintroduced_fallback_is_reported_with_file_and_line(tmp_path: Path) -> None:
    module = tmp_path / "validator" / "conventions_ast" / "corpus.py"
    module.parent.mkdir(parents=True)
    module.write_text(
        "from pathlib import Path\n\n"
        "def root() -> Path:\n"
        '    return Path.home() / "projects" / "ai-ressources"\n'
        "\n"
        "LIVESPEC_ROOT = Path(__file__).parent\n"
        'SIBLING = LIVESPEC_ROOT.parent / "ai-ressources"\n',
        encoding="utf-8",
    )

    assert forbidden_fallbacks(tmp_path / "validator") == [
        "conventions_ast/corpus.py:4",
        "conventions_ast/corpus.py:7",
    ]


def test_logical_catalog_identifiers_do_not_match() -> None:
    assert not FORBIDDEN_FALLBACK_RE.search(
        'source_path: "ai-ressources/code-conventions/general.md"'
    )
    assert not FORBIDDEN_FALLBACK_RE.search("ai-ressources/design/index.yaml")
