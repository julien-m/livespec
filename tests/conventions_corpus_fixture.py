"""Public synthetic corpus for deterministic convention classification tests.

These twelve sources exercise classification, not the private full corpus.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from tests.test_conventions_taxonomy import _enforce_project, _write_ai_resources_fixture
from validator.conventions_ast.ars_rules import INVENTORY_RELATIVE_PATH

CORPUS_SOURCE_PATHS = frozenset(
    f"ai-ressources/{source}"
    for source in (
        "architecture/webhook-patterns.md",
        "code-conventions/database.md",
        "code-conventions/general.md",
        "code-conventions/javascript.md",
        "code-conventions/rust.md",
        "code-conventions/swift-kotlin.md",
        "code-conventions/tailwind.md",
        "copywriting/landing-page.md",
        "design/components/payment-flows.md",
        "legal/privacy-policy.md",
        "pricing-models/usage-based.md",
        "stack-ref/databases/postgres.md",
    )
)


# @spec FR-003: Deterministic CI fixtures — 079-validator-ci-prerequisites
def convention_corpus_project(tmp_path: Path) -> Path:
    """Build an explicit twelve-source corpus with the public ARS inventory."""
    ai_root = tmp_path / "ai-ressources"
    _write_ai_resources_fixture(ai_root)
    for name, text in {
        "general.md": "# General conventions\nKeep functions focused.\n",
        "tailwind.md": "# Tailwind\nUse named spacing utilities.\n",
    }.items():
        (ai_root / "code-conventions" / name).write_text(text, encoding="utf-8")
    project = _enforce_project(tmp_path / "project", ai_resources_path=ai_root)
    inventory = project / INVENTORY_RELATIVE_PATH
    inventory.parent.mkdir(parents=True)
    # Keep rule-level metadata coverage without reading a user's private corpus.
    shutil.copyfile(Path(__file__).resolve().parents[1] / INVENTORY_RELATIVE_PATH, inventory)
    return project
