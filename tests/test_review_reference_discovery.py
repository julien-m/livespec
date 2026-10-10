"""Real Markdown dependency edges preserve full normative review context (078 AC-002)."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.semantic.review_context import PreparedReview, content_hash
from validator.semantic.review_files import prepare_feature_review


def _write(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _project(root: Path, spec: str) -> str:
    feature = "001-discovery"
    for name, text in {
        f".specs/features/{feature}/spec.md": spec,
        ".specs/constitution.md": "Keep canonical contracts authoritative.",
        ".specs/project.md": "Review references completely.",
        ".specs/stacks/_default.md": "Python with existing Markdown parser.",
    }.items():
        _write(root, name, text)
    return feature


def _prepare(root: Path, spec: str) -> PreparedReview:
    return prepare_feature_review(root, _project(root, spec), "spec", "reviewer/test")


@pytest.mark.parametrize(
    "literal",
    [
        "```md\n[example](missing.md)\n```",
        "~~~md\n[example](missing.md)\n~~~",
        "````md\n```\n[example](missing.md)\n```\n````",
        "   ```md\n[example](missing.md)\n   ```",
        "    [example](missing.md)",
        "`[example](missing.md)`",
        "``[example](missing.md)``",
        r"\[example](missing.md)",
        "<!-- [example](missing.md) -->",
        "<div>\n[example](missing.md)\n</div>",
        "> ```md\n> [example](missing.md)\n> ```",
    ],
)
def test_literal_examples_are_retained_without_dependency_edges(
    tmp_path: Path, literal: str
) -> None:
    original = "# Contract\nFR-001 Retain source exactly.\n\n" + literal
    prepared = _prepare(tmp_path, original)
    assert prepared.complete, prepared.errors
    assert len(prepared.source_hashes) == 4
    source = f".specs/features/{prepared.feature}/spec.md"
    assert "".join(s.text for s in prepared.sections if s.source == source) == original


@pytest.mark.parametrize(
    "link",
    [
        "Read [contract](../../../contract.md).",
        "Read [contract][contract-ref].\n\n[contract-ref]: ../../../contract.md",
        "Read [contract].\n\n[contract]: ../../../contract.md",
        "| Purpose | Contract |\n|---|---|\n| Rule | [contract](../../../contract.md) |",
    ],
)
def test_real_inline_reference_and_table_links_load_complete_closure(
    tmp_path: Path, link: str
) -> None:
    tail = "# Contract\n" + "Full context. " * 800 + "\n## Late rule\nFR-099 Retain 24 hours."
    _write(tmp_path, "contract.md", "Read [nested](nested.md).\nFR-002 First rule.")
    _write(tmp_path, "nested.md", tail)
    prepared = _prepare(tmp_path, "FR-001 Canonical source.\n\n" + link)
    assert prepared.complete, prepared.errors
    assert prepared.source_hashes["nested.md"] == content_hash(tail)
    assert "".join(s.text for s in prepared.sections if s.source == "nested.md") == tail
    assert f"{prepared.feature}:FR-099" in {r.requirement_id for r in prepared.requirements}


@pytest.mark.parametrize(
    ("link", "error"),
    [
        ("Read [missing](../../../missing.md).", "unread_source:missing.md:FileNotFoundError"),
        ("Read [outside](../../../../outside.md).", "contract_outside_project:"),
        ("Read [remote](https://example.org/contract.md).", "external_contract_not_loaded:"),
    ],
)
def test_true_unavailable_normative_contracts_fail_closed(
    tmp_path: Path, link: str, error: str
) -> None:
    prepared = _prepare(tmp_path, "FR-001 Canonical rule.\n\n" + link)
    assert not prepared.complete
    assert any(error in item for item in prepared.errors)


def test_inspected_source_is_full_bound_context_without_recursive_contracts(tmp_path: Path) -> None:
    inspected = "# Source\nFR-099 Descriptive source ID.\nRead [internal](missing.md).\n"
    _write(tmp_path, "source.md", inspected)
    prepared = _prepare(tmp_path, "FR-001 Rule.\n\nInspect **[source](../../../source.md)**.")
    assert prepared.complete, prepared.errors
    assert prepared.source_hashes["source.md"] == content_hash(inspected)
    assert "".join(s.text for s in prepared.sections if s.source == "source.md") == inspected
    assert {s.role for s in prepared.sections if s.source == "source.md"} == {"context"}
    assert f"{prepared.feature}:FR-099" not in {r.requirement_id for r in prepared.requirements}
    _write(tmp_path, "source.md", inspected + "Changed source evidence.\n")
    changed = prepare_feature_review(tmp_path, prepared.feature, "spec", "reviewer/test")
    assert changed.context_hash != prepared.context_hash


def test_later_normative_edge_promotes_inspected_source_and_traverses_it(tmp_path: Path) -> None:
    _write(tmp_path, "source.md", "FR-099 Contract rule.\nRead [nested](nested.md).")
    _write(tmp_path, "nested.md", "FR-098 Nested mandatory rule.")
    prepared = _prepare(
        tmp_path,
        "FR-001 Rule.\n\nInspect [source](../../../source.md).\n\n"
        "Read [contract](../../../source.md).",
    )
    assert prepared.complete, prepared.errors
    assert {s.role for s in prepared.sections if s.source == "source.md"} == {"reference"}
    assert "nested.md" in prepared.source_hashes
    assert f"{prepared.feature}:FR-098" in {r.requirement_id for r in prepared.requirements}


def test_canonical_sources_are_never_demoted_by_inspection_links(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path, "FR-001 Rule.\n\nInspect [constitution](../../constitution.md).")
    assert prepared.complete
    assert {s.role for s in prepared.sections if s.source == ".specs/constitution.md"} == {
        "constitution"
    }


def test_fragment_keeps_full_target_including_unselected_late_contract(tmp_path: Path) -> None:
    target = "# Early\nFR-002 Early.\n\n# Late\nFR-099 Late mandatory exception."
    _write(tmp_path, "contract.md", target)
    prepared = _prepare(tmp_path, "FR-001 Rule.\nRead [early](../../../contract.md#early).")
    assert prepared.complete
    assert "".join(s.text for s in prepared.sections if s.source == "contract.md") == target
    assert f"{prepared.feature}:FR-099" in {r.requirement_id for r in prepared.requirements}


def test_explicit_informative_external_link_is_not_an_unloaded_contract(tmp_path: Path) -> None:
    prepared = _prepare(
        tmp_path, "FR-001 Rule.\n\nInformative: [guide](https://example.org/guide.md)."
    )
    assert prepared.complete, prepared.errors
    assert "https://example.org/guide.md" in prepared.batches[0].prompt


def test_mandatory_inspection_still_requires_normative_dependency_closure(tmp_path: Path) -> None:
    _write(tmp_path, "contract.md", "Read [required](missing.md).")
    prepared = _prepare(
        tmp_path, "FR-001 Rule.\n\nYou MUST inspect [contract](../../../contract.md)."
    )
    assert not prepared.complete
    assert any("unread_source:missing.md:" in error for error in prepared.errors)


def test_normative_cycles_terminate_without_losing_contracts(tmp_path: Path) -> None:
    _write(tmp_path, "one.md", "FR-002 First. Read [two](two.md).")
    _write(tmp_path, "two.md", "FR-003 Second. Read [one](one.md).")
    prepared = _prepare(tmp_path, "FR-001 Rule. Read [one](../../../one.md).")
    assert prepared.complete
    assert {"one.md", "two.md"}.issubset(prepared.source_hashes)
