"""Keep capacity criteria and accepted decisions attached to their actual quality claim."""

from pathlib import Path

import pytest

from validator.clarify_decisions import persist_clarification_decision
from validator.clarify_gate import scan_clarification_opportunities
from validator.clarify_inventory import collect_clarification_inventory


def _spec(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "001-capacity" / "spec.md"
    path.parent.mkdir()
    path.write_text(f"# Feature\n### FR-001\n{body}\n")
    return path


@pytest.mark.parametrize(
    "claim",
    [
        "Scalable to 10,000 users.",
        "Scalable to 10,000 concurrent users.",
        "Scalable to 10 simultaneous requests.",
        "Scalable to 10 jobs.",
        "Scalable to 10 workers.",
        "Évolutif pour 10 000 utilisateurs.",
        "Évolutif pour 10\u202f000 requêtes.",
        "Évolutif pour 10 requêtes/s.",
    ],
)
def test_explicit_capacity_nouns_resolve_only_scale(tmp_path: Path, claim: str) -> None:
    path = _spec(tmp_path, claim)
    assert scan_clarification_opportunities(path) == []


@pytest.mark.parametrize(
    "claim",
    [
        "Scalable to 10 concurrent.",
        "Scalable to 10,000 simultaneous.",
        "Évolutif pour 10 simultanés.",
        "Évolutif pour 10 000 simultanes.",
    ],
)
def test_concurrency_without_a_capacity_noun_remains_ambiguous(tmp_path: Path, claim: str) -> None:
    item = scan_clarification_opportunities(_spec(tmp_path, claim))
    assert len(item) == 1
    assert item[0].critical


@pytest.mark.parametrize(
    "claim",
    [
        "Fast under 0,2 s.",
        "Rapide sous 0,2 s.",
        "Robust with 99,9% availability.",
        "Robuste avec 99,9% disponibilité.",
        "Secure with TLS 1.3.",
        "Sécurisé avec TLS 1.3.",
    ],
)
def test_existing_decimal_metrics_remain_in_the_same_clause(tmp_path: Path, claim: str) -> None:
    assert scan_clarification_opportunities(_spec(tmp_path, claim)) == []


@pytest.mark.parametrize("separator", (". ", " and ", " et ", "; ", ", "))
def test_distinct_same_quality_claims_survive_inventory_merge(
    tmp_path: Path, separator: str
) -> None:
    path = _spec(tmp_path, f"Search must be fast{separator}Export must be fast.")
    inventory = collect_clarification_inventory(path)
    assert len(inventory.inventory) == 2
    assert len({item.decision_key for item in inventory.inventory}) == 2
    assert {item.evidence_text.strip().rstrip(".") for item in inventory.inventory} == {
        "Search must be fast",
        "Export must be fast",
    }
    assert inventory.blocking
    assert not inventory.review_complete


@pytest.mark.parametrize(
    "body,unresolved",
    [
        ("Search is fast under 200 ms and export must be fast.", "export must be fast"),
        ("La recherche est rapide sous 200 ms et l'export est rapide.", "l'export est rapide"),
        ("Scalable to 10,000 users, but reporting must be scalable.", "reporting must be scalable"),
    ],
)
def test_one_measured_claim_cannot_resolve_a_second_vague_claim(
    tmp_path: Path, body: str, unresolved: str
) -> None:
    items = collect_clarification_inventory(_spec(tmp_path, body)).inventory
    assert len(items) == 1
    assert items[0].evidence_text.strip().rstrip(".") == unresolved


def test_identical_claim_dedup_keeps_full_distinct_inventory(tmp_path: Path) -> None:
    body = "\n".join([f"Operation {i} must be fast." for i in range(6)])
    path = _spec(tmp_path, body + "\nOperation 0 must be fast.")
    inventory = collect_clarification_inventory(path)
    assert len(scan_clarification_opportunities(path)) == 7
    assert len(inventory.inventory) == 6
    assert len(inventory.presented) == 5
    assert inventory.blocking


def test_accepted_decision_resolves_only_exact_claim_and_rejects_stale_source(
    tmp_path: Path,
) -> None:
    path = _spec(tmp_path, "Search must be fast and export must be fast.")
    initial = collect_clarification_inventory(path)
    search = next(item for item in initial.inventory if "Search" in item.evidence_text)
    export = next(item for item in initial.inventory if "export" in item.evidence_text)
    persist_clarification_decision(path, search, "Search latency p95 under 200 ms.")
    updated = collect_clarification_inventory(path)
    assert sum(bool(item.resolution) for item in updated.inventory) == 1
    assert any("export" in item.evidence_text and not item.resolution for item in updated.inventory)
    assert updated.blocking
    with pytest.raises(ValueError, match="stale_clarification_source"):
        persist_clarification_decision(path, export, "Export latency under 1 s.")
    path.write_text(path.read_text().replace("Search must be fast", "Search must be very fast", 1))
    changed = collect_clarification_inventory(path)
    assert not any(item.resolution for item in changed.inventory)
    assert changed.source_hash != updated.source_hash
