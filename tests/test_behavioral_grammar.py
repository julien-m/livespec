# @spec FR-010: 5 mandatory unit tests
# .specs/features/044-behavioral-grammar-v1-shared/spec.md#fr-010
"""Unit tests for ``validator.behavioral_grammar``.

Covers the 5 cases mandated by AC-011 / FR-010:

1. flow valid → PASS
2. flow with optional ``Notes`` section absent → WARNING
3. flow with mandatory ``Règles métier`` section absent → FAIL
4. screen valid → PASS
5. screen missing mandatory ``Acteur`` section → FAIL
"""

from __future__ import annotations

from pathlib import Path

from validator.behavioral_grammar import (
    VALIDATION_RESULT,
    validate_behavioral,
)

# ─── Fixtures (inlined as string templates) ──────────────────────────────────

_FRONTMATTER = (
    "---\n"
    "brainstormSource: .brainstorm/specs/flows/booking.md\n"
    'brainstormGeneratedAt: "2026-04-29T10:00:00Z"\n'
    "specStatus: fresh\n"
    "---\n\n"
)

_FLOW_SECTIONS_FULL = (
    "## Acteur\n\nPraticienne connectée.\n\n"
    "## Préconditions\n\nCompte créé.\n\n"
    "## Déclencheur\n\nClic sur Confirmer.\n\n"
    "## Étapes nominales\n\n1. Validation. 2. Persistance.\n\n"
    "## Règles métier\n\nPas de chevauchement.\n\n"
    "## Erreurs & exceptions\n\nCréneau pris.\n\n"
    "## Side-effects\n\nInsertion DB.\n\n"
    "## Postconditions\n\nRéservation visible.\n"
)

_FLOW_SECTIONS_NO_REGLES = (
    "## Acteur\n\nPraticienne connectée.\n\n"
    "## Préconditions\n\nCompte créé.\n\n"
    "## Déclencheur\n\nClic sur Confirmer.\n\n"
    "## Étapes nominales\n\n1. Validation. 2. Persistance.\n\n"
    "## Erreurs & exceptions\n\nCréneau pris.\n\n"
    "## Side-effects\n\nInsertion DB.\n\n"
    "## Postconditions\n\nRéservation visible.\n"
)

_FLOW_OPTIONAL_NOTES = "\n## Notes\n\nQuelques clarifications.\n"

_SCREEN_FRONTMATTER = (
    "---\n"
    "brainstormSource: .brainstorm/specs/screens/booking_confirm.md\n"
    'brainstormGeneratedAt: "2026-04-29T10:00:00Z"\n'
    "specStatus: fresh\n"
    "---\n\n"
)

_SCREEN_SECTIONS_FULL = (
    "## Acteur\n\nPraticienne connectée.\n\n"
    "## Source d'entrée\n\nClic sur Réserver.\n\n"
    "## Sortie principale\n\nRéservation confirmée.\n\n"
    "## Données affichées\n\n- Date.\n- Client.\n\n"
    "## Actions\n\n| Élément | Type | Effet |\n|---|---|---|\n| Confirmer | button | POST. |\n\n"
    "## Validations\n\nDate dans le futur.\n\n"
    "## États UI\n\nchargement · prêt · confirmé\n\n"
    "## Erreurs\n\nCréneau pris → message.\n\n"
    "## Side effects locaux\n\nlocalStorage write.\n\n"
    "## Notes\n\nAucune.\n"
)

_SCREEN_SECTIONS_NO_ACTEUR = (
    "## Source d'entrée\n\nClic sur Réserver.\n\n"
    "## Sortie principale\n\nRéservation confirmée.\n\n"
    "## Données affichées\n\n- Date.\n- Client.\n\n"
    "## Actions\n\n| Élément | Type | Effet |\n|---|---|---|\n| Confirmer | button | POST. |\n\n"
    "## Validations\n\nDate dans le futur.\n\n"
    "## États UI\n\nchargement · prêt · confirmé\n\n"
    "## Erreurs\n\nCréneau pris → message.\n\n"
    "## Side effects locaux\n\nlocalStorage write.\n\n"
    "## Notes\n\nAucune.\n"
)


def _write_flow(tmp_path: Path, body: str, name: str = "booking.md") -> Path:
    """Write a flow fixture into a synthetic ``.specs/flows/`` tree.

    Args:
        tmp_path: Pytest temporary directory root.
        body: Markdown body to write after the shared frontmatter block.
        name: Fixture filename to create.

    Returns:
        The path to the created fixture file.
    """
    flows_dir = tmp_path / ".specs" / "flows"
    flows_dir.mkdir(parents=True, exist_ok=True)
    target = flows_dir / name
    target.write_text(_FRONTMATTER + body, encoding="utf-8")
    return target


def _write_screen(tmp_path: Path, body: str, name: str = "booking_confirm.md") -> Path:
    """Write a screen fixture into a synthetic ``.specs/design/screens/`` tree.

    Args:
        tmp_path: Pytest temporary directory root.
        body: Markdown body to write after the shared frontmatter block.
        name: Fixture filename to create.

    Returns:
        The path to the created fixture file.
    """
    screens_dir = tmp_path / ".specs" / "design" / "screens"
    screens_dir.mkdir(parents=True, exist_ok=True)
    target = screens_dir / name
    target.write_text(_SCREEN_FRONTMATTER + body, encoding="utf-8")
    return target


# ─── Tests (AC-011 / FR-010) ─────────────────────────────────────────────────


def test_flow_valid_returns_pass(tmp_path: Path) -> None:
    """Flow file with all 8 mandatory sections + optional Notes → PASS.

    PASS requires both all mandatory sections AND any documented optional
    sections to be present (no deviation). See plan Step 2 / spec FR-007.
    """
    path = _write_flow(tmp_path, _FLOW_SECTIONS_FULL + _FLOW_OPTIONAL_NOTES)

    outcome = validate_behavioral(path)

    assert outcome.result == VALIDATION_RESULT.PASS, outcome.diagnostics
    assert outcome.diagnostics == []
    assert outcome.kind == "flow"


def test_flow_optional_section_absent_returns_warning(tmp_path: Path) -> None:
    """Flow with all 8 mandatory but missing optional ``Notes`` → WARNING."""
    # Full mandatory body; do NOT add the optional Notes section.
    path = _write_flow(tmp_path, _FLOW_SECTIONS_FULL)

    outcome = validate_behavioral(path)

    assert outcome.result == VALIDATION_RESULT.WARNING, outcome.diagnostics
    assert any("Notes" in d for d in outcome.diagnostics), outcome.diagnostics
    assert outcome.kind == "flow"


def test_flow_mandatory_section_absent_returns_fail(tmp_path: Path) -> None:
    """Flow missing mandatory ``Règles métier`` → FAIL with named diagnostic."""
    path = _write_flow(tmp_path, _FLOW_SECTIONS_NO_REGLES)

    outcome = validate_behavioral(path)

    assert outcome.result == VALIDATION_RESULT.FAIL, outcome.diagnostics
    assert any("Règles métier" in d for d in outcome.diagnostics), outcome.diagnostics
    assert any(str(path) in d for d in outcome.diagnostics), outcome.diagnostics
    assert outcome.kind == "flow"


def test_screen_valid_returns_pass(tmp_path: Path) -> None:
    """Screen file with all 8 mandatory screen sections + Acteur → PASS."""
    path = _write_screen(tmp_path, _SCREEN_SECTIONS_FULL)

    outcome = validate_behavioral(path)

    assert outcome.result == VALIDATION_RESULT.PASS, outcome.diagnostics
    assert outcome.diagnostics == []
    assert outcome.kind == "screen"


def test_screen_missing_actor_returns_fail(tmp_path: Path) -> None:
    """Screen missing mandatory ``Acteur`` section → FAIL with named diagnostic."""
    path = _write_screen(tmp_path, _SCREEN_SECTIONS_NO_ACTEUR)

    outcome = validate_behavioral(path)

    assert outcome.result == VALIDATION_RESULT.FAIL, outcome.diagnostics
    assert any("Acteur" in d for d in outcome.diagnostics), outcome.diagnostics
    assert outcome.kind == "screen"

