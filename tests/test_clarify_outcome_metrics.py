# @spec(FR-002)
# @spec(AC-002)
# .specs/features/069-clarify-gate/spec.md#fr-002
"""Security counts and reliability rates quantify only their own quality clause."""

from pathlib import Path

import pytest

from validator.clarify_gate import scan_clarification_opportunities


@pytest.mark.parametrize(
    "claim",
    [
        "The export is secure with 0 critical vulnerabilities.",
        "La sortie est sécurisée avec 0 vulnérabilités critiques.",
        "The export is secure with 1 critical vulnerability.",
        "La sortie est sécurisée avec 1 vulnérabilité critique.",
        "The export is robust with an error rate below 1%.",
        "La sortie est robuste avec un taux d'erreurs < 1%.",
        "The export is robust with an error rate less than 0.1%.",
        "La sortie est robuste avec un taux d\u2019erreurs inférieur à 0,1%.",
        "La sortie est robuste avec un taux erreurs < 1%.",
        "The export is secure with 0 vulnerabilities.",
        "La sortie est sécurisée avec 0 vulnérabilités.",
        "The export is secure with 1 vulnerability.",
        "La sortie est sécurisée avec 1 vulnérabilité.",
        "The export is robust with an error rate 1%.",
        "The export is robust with an error rate <=1%.",
        "The export is robust with an error rate<=1%.",
        "La sortie est robuste avec un taux d'erreurs<1%.",
        "La sortie est robuste avec un taux d'erreur 1%.",
        "La sortie est robuste avec un taux d'erreurs <=0,1%.",
        "The export is secure with TLS 1.3.",
        "La sortie est sécurisée avec AES-256.",
        "The export is robust with 99.9% availability.",
        "La sortie est robuste avec 99,9% disponibilité.",
    ],
)
def test_quantified_security_and_reliability_outcomes_need_no_clarification(
    tmp_path: Path, claim: str
) -> None:
    path = tmp_path / "spec.md"
    path.write_text(f"### FR-001\n{claim}\n")
    assert scan_clarification_opportunities(path) == []


@pytest.mark.parametrize(
    "claim,group",
    [
        ("The export is secure for 0 users.", "security"),
        ("La sortie est sécurisée pour 0 utilisateurs.", "security"),
        ("The export is robust with a 1% discount.", "reliability"),
        ("La sortie est robuste avec 1% de réduction.", "reliability"),
        ("The export is secure with an error rate below 1%.", "security"),
        ("La sortie est sécurisée avec un taux d'erreurs < 1%.", "security"),
        ("The export is robust with 0 critical vulnerabilities.", "reliability"),
        ("La sortie est robuste avec 0 vulnérabilités critiques.", "reliability"),
        ("The export is secure or another service has 0 critical vulnerabilities.", "security"),
        ("La sortie est sécurisée ou un autre service a 0 vulnérabilités critiques.", "security"),
        ("The export is robust and another service has an error rate below 1%.", "reliability"),
        ("La sortie est robuste et un autre service a un taux d'erreurs < 1%.", "reliability"),
        ("The export is robust with an error rate below 1 ms.", "reliability"),
        ("The export is robust with error rate1%.", "reliability"),
        ("La sortie est robuste avec un taux d'erreurs1%.", "reliability"),
        ("The export is robust with 1%.", "reliability"),
        ("La sortie est robuste avec 1%.", "reliability"),
        ("The export is secure with an error rate 1%.", "security"),
        ("La sortie est sécurisée avec un taux d'erreur 1%.", "security"),
        ("The export is robust with 0 vulnerabilities.", "reliability"),
        ("La sortie est robuste avec 0 vulnérabilités.", "reliability"),
        ("The export is robust or another service has an error rate 1%.", "reliability"),
        ("La sortie est robuste ou un autre service a un taux d'erreur 1%.", "reliability"),
        ("The export is secure with 0 critical users.", "security"),
    ],
)
def test_unrelated_quantities_rates_or_clauses_remain_critical(
    tmp_path: Path, claim: str, group: str
) -> None:
    path = tmp_path / "spec.md"
    path.write_text(f"### FR-001\n{claim}\n")
    items = scan_clarification_opportunities(path)
    assert len(items) == 1
    assert items[0].critical and not items[0].resolution
    assert items[0].requirement_id == f"{tmp_path.name}:FR-001"
    assert items[0].decision_key.startswith(f"quality:{group}:")
