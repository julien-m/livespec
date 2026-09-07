# @spec(FR-002)
# @spec(AC-002)
# .specs/features/069-clarify-gate/spec.md#fr-002
"""Alternative quality claims cannot borrow each other's measurements or resolutions."""

from pathlib import Path

import pytest

from validator.clarify_decisions import persist_clarification_decision
from validator.clarify_gate import scan_clarification_opportunities
from validator.clarify_inventory import collect_clarification_inventory


def _spec(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "001-search" / "spec.md"
    path.parent.mkdir()
    path.write_text(f"### FR-001\n{body}\n")
    return path


@pytest.mark.parametrize(
    "conjunction,measured,vague",
    [(word, "Search is fast under 200 ms", "export must be fast") for word in ("and", "or", "but")]
    + [
        (word, "La recherche est rapide sous 200 ms", "l'export doit être rapide")
        for word in ("et", "ou", "mais")
    ],
)
@pytest.mark.parametrize("measured_first", [True, False])
def test_same_quality_alternative_metric_resolves_only_its_own_claim(
    tmp_path: Path, conjunction: str, measured: str, vague: str, measured_first: bool
) -> None:
    clauses = [measured, vague] if measured_first else [vague, measured]
    path = _spec(tmp_path, f" {conjunction} ".join(clauses))
    inventory = collect_clarification_inventory(path)
    assert len(inventory.inventory) == 1
    item = inventory.inventory[0]
    assert item.evidence_text.strip() == vague
    assert item.requirement_id == "001-search:FR-001"
    assert item.decision_key == f"quality:speed:{vague.casefold()}"
    assert item.critical and not item.resolution and inventory.blocking


@pytest.mark.parametrize(
    "body",
    [
        "Search is fast under 0,2 s or export is fast under 200 ms",
        "La recherche est rapide sous 0,2 s ou l'export est rapide sous 200 ms",
        "Search is scalable to 10,000 users or export is scalable to 1,000 jobs",
        "La recherche est évolutive pour 10 000 utilisateurs ou l'export est évolutif pour 10 jobs",
    ],
)
def test_alternative_claims_with_own_metrics_keep_numeric_commas(tmp_path: Path, body: str) -> None:
    assert scan_clarification_opportunities(_spec(tmp_path, body)) == []


@pytest.mark.parametrize("conjunction", ["or", "ou"])
def test_alternative_decision_resolves_only_its_claim_and_old_source_is_rejected(
    tmp_path: Path, conjunction: str
) -> None:
    path = _spec(tmp_path, f"Search must be fast {conjunction} export must be fast")
    initial = collect_clarification_inventory(path)
    assert len(initial.inventory) == 2
    search = next(item for item in initial.inventory if "Search" in item.evidence_text)
    export = next(item for item in initial.inventory if "export" in item.evidence_text)
    assert search.decision_key != export.decision_key
    persist_clarification_decision(path, search, "Search latency below 200 ms")
    updated = collect_clarification_inventory(path)
    assert len(updated.inventory) == 2
    assert sum(bool(item.resolution) for item in updated.inventory) == 1
    assert any("export" in item.evidence_text and not item.resolution for item in updated.inventory)
    assert updated.blocking and updated.source_hash != initial.source_hash
    with pytest.raises(ValueError, match="stale_clarification_source"):
        persist_clarification_decision(path, export, "Export latency below 1 s")
