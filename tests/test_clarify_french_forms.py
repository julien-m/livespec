"""Common French gender and plural forms keep the same claim-specific quality rules."""

from pathlib import Path

import pytest

from validator.clarify_gate import scan_clarification_opportunities
from validator.clarify_inventory import collect_clarification_inventory

FORMS = (
    ("sécurisée", "security", "TLS 1.3"),
    ("sécurisés", "security", "TLS 1.3"),
    ("sécurisées", "security", "TLS 1.3"),
    ("securisee", "security", "TLS 1.3"),
    ("securises", "security", "TLS 1.3"),
    ("securisees", "security", "TLS 1.3"),
    ("évolutive", "scale", "10 000 utilisateurs"),
    ("évolutifs", "scale", "10 requêtes/s"),
    ("évolutives", "scale", "10 000 utilisateurs"),
    ("rapides", "speed", "200 ms"),
    ("robustes", "reliability", "99,9% disponibilité"),
)


def _spec(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "spec.md"
    path.write_text("### FR-001\n" + text + "\n")
    return path


@pytest.mark.parametrize("adjective,group,metric", FORMS)
def test_french_variant_is_critical_without_its_own_metric(
    tmp_path: Path, adjective: str, group: str, metric: str
) -> None:
    items = scan_clarification_opportunities(_spec(tmp_path, f"Exigence {adjective}."))
    assert len(items) == 1
    assert items[0].critical
    assert items[0].decision_key.startswith(f"quality:{group}:")
    assert (
        scan_clarification_opportunities(_spec(tmp_path, f"Exigence {adjective}: {metric}.")) == []
    )


@pytest.mark.parametrize("adjective,group,metric", FORMS)
def test_inflected_claim_keeps_its_identity_and_cannot_borrow_neighbour_metric(
    tmp_path: Path, adjective: str, group: str, metric: str
) -> None:
    path = _spec(tmp_path, f"Entrées {adjective}: {metric} et sorties {adjective}.")
    inventory = collect_clarification_inventory(path)
    assert len(inventory.inventory) == 1
    item = inventory.inventory[0]
    assert item.evidence_text.strip() == f"sorties {adjective}."
    assert item.decision_key.startswith(f"quality:{group}:")
    assert inventory.blocking
    assert not inventory.review_complete
