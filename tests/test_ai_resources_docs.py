# @spec FR-007: README and documents reference AIRESOURCES
#   .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-007

"""Documentation checks for the ai-ressources location (feature 085, AC-010, SC-001)."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from tests.test_ai_resources_guard import FORBIDDEN_FALLBACK_RE

REPO = Path(__file__).resolve().parents[1]
PROTOCOL = "`$AIRESOURCES/design/references/design-read-protocol.md`"
PRIVATE_PATH = "/Users/julienm/projects/ai-ressources"
DOCUMENTS = (
    ".specs/spec-system.md",
    ".agent-sync/skills/spec-specify/SKILL.md",
    "system/templates/spec-template.md",
)
GREP_SCOPE = ("validator", ".agent-sync", "system", ".specs/spec-system.md", "README.md")
FIX = (
    "Run ./setup.sh from your ai-ressources clone, "
    "or export AIRESOURCES=<absolute path of the clone>."
)


def _readme_section() -> str:
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    start = readme.index("### ai-ressources location (`AIRESOURCES`)")
    return readme[start : readme.index("\n---\n", start)]


def test_readme_documents_airesources_role_order_and_fix() -> None:
    section = _readme_section()

    assert "https://github.com/julien-m/ai-ressources" in section
    assert "setup.sh" in section
    order = [
        section.index("the `AIRESOURCES` environment variable"),
        section.index("`ai_resources_path` key of the project's `.conventions/manifest.yaml`"),
        section.index("declaration of the project's `.conventions/index.md`"),
    ]
    assert order == sorted(order)
    assert "existing directory" in section
    assert FIX in section


def test_readme_no_longer_mentions_a_default_sibling_directory() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8")

    assert "default sibling" not in readme
    assert "#ai-ressources-location-airesources" in readme


@pytest.mark.parametrize("relative", DOCUMENTS)
def test_documents_reference_the_variable_path(relative: str) -> None:
    text = (REPO / relative).read_text(encoding="utf-8")

    assert f"**Read** {PROTOCOL}" in text
    assert PRIVATE_PATH not in text


def test_spec_specify_expectations_were_reviewed() -> None:
    text = (REPO / ".agent-sync/skills/spec-specify/expectations.md").read_text(encoding="utf-8")
    match = re.search(r"^last_reviewed: (\d{4}-\d{2}-\d{2})$", text, flags=re.MULTILINE)

    assert match is not None
    assert date.fromisoformat(match.group(1)) >= date(2026, 10, 13)


def test_request_grep_scope_has_no_forbidden_location() -> None:
    findings: list[str] = []
    for relative in GREP_SCOPE:
        target = REPO / relative
        files = (
            [target] if target.is_file() else sorted(p for p in target.rglob("*") if p.is_file())
        )
        for path in files:
            text = path.read_text(encoding="utf-8", errors="replace")
            findings.extend(
                f"{path.relative_to(REPO)}:{number}"
                for number, line in enumerate(text.splitlines(), start=1)
                if FORBIDDEN_FALLBACK_RE.search(line)
            )

    assert findings == []
