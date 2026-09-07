"""Lifecycle finalization preserves normative bytes and exact registry audit history."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from tests.test_finalize import _implement_request, _make_specs_tree, _registry_snapshot
from validator.finalize import (
    FinalizeError,
    FinalizeReceiptError,
    apply_finalization,
    verify_finalize_receipt,
)
from validator.normative_identity import normative_hash


# @spec FR-002: Lifecycle-only specification updates without new body markers
# — .specs/features/058-deterministic-finalization/spec.md#fr-002
def test_status_completion_preserves_normative_body_and_current_receipt(tmp_path: Path) -> None:
    specs = _make_specs_tree(tmp_path)
    request = replace(_implement_request(), status="In Progress", run_id="prepare")
    spec = specs / "features" / request.feature_slug / "spec.md"
    initial = spec.read_text()
    first = apply_finalization(tmp_path, request, today=date(2026, 9, 6))
    prepared = spec.read_text()
    assert normative_hash(initial, lifecycle_document=True) == normative_hash(
        prepared, lifecycle_document=True
    )
    assert "<!-- finalize:" not in prepared

    completed = replace(request, status="Implemented", run_id="complete")
    final = apply_finalization(tmp_path, completed, today=date(2026, 9, 7))
    observed = spec.read_text()
    assert observed == prepared.replace("In Progress", "Implemented").replace(
        "updated: 2026-09-06", "updated: 2026-09-07"
    )
    assert normative_hash(observed, lifecycle_document=True) == normative_hash(
        prepared, lifecycle_document=True
    )
    assert completed.hash8() != request.hash8()
    assert completed.hash8() not in observed
    receipt = verify_finalize_receipt(final.receipt_path, project_root=tmp_path)
    assert receipt.payload_hash == completed.payload_hash()
    for path in (spec.parent / "changelog.md", specs / "changelog.md", specs / "README.md"):
        assert request.hash8() in path.read_text()
        assert completed.hash8() in path.read_text()
    with pytest.raises(FinalizeReceiptError, match="sha256_mismatch"):
        verify_finalize_receipt(first.receipt_path, project_root=tmp_path)
    before = _registry_snapshot(specs)
    repeated = apply_finalization(
        tmp_path, replace(completed, run_id="repeat"), today=date(2026, 9, 8)
    )
    assert repeated.outcome == "already_finalized"
    assert repeated.written == ()
    assert _registry_snapshot(specs) == before


def test_new_entry_has_registry_history_without_mutating_spec_body(tmp_path: Path) -> None:
    specs = _make_specs_tree(tmp_path)
    request = _implement_request()
    apply_finalization(tmp_path, request)
    spec = specs / "features" / request.feature_slug / "spec.md"
    before = spec.read_bytes()
    changed = replace(request, entry_body="Fix: correct a real behavior", run_id="new-entry")
    result = apply_finalization(tmp_path, changed)
    assert spec.read_bytes() == before
    assert "spec_status" in result.skipped
    changelog = (spec.parent / "changelog.md").read_text()
    assert request.entry_body.splitlines()[0] in changelog
    assert changed.entry_body in changelog
    assert changed.hash8() in changelog
    assert verify_finalize_receipt(result.receipt_path, project_root=tmp_path).payload_hash == (
        changed.payload_hash()
    )


@pytest.mark.parametrize(
    "marker",
    [
        "<!-- finalize:spec-plan:2026-09-06:1234abcd -->",
        "<!-- finalize:spec-implement-extra:2026-09-06:1234abcd -->",
        "<!-- finalize:spec-implement:bad-date:1234abcd -->",
        "<!-- finalize:spec-implement:2026-99-99:1234abcd -->",
        "<!-- finalize:spec-implement:2026-09-06:1234 -->",
        "<!-- finalize:spec-implement:2026-09-06:abcdefgh -->",
        "<!-- finalize:spec-implement:2026-09-06:1234abcd",
        "```gherkin\n<!-- finalize:spec-implement:2026-09-06:1234abcd -->\n```",
        "~~~markdown\n<!-- finalize:spec-implement:2026-09-06:1234abcd -->\n~~~",
    ],
)
def test_existing_comments_and_examples_are_preserved_verbatim(tmp_path: Path, marker: str) -> None:
    specs = _make_specs_tree(tmp_path)
    request = _implement_request()
    spec = specs / "features" / request.feature_slug / "spec.md"
    spec.write_text(spec.read_text() + "\n" + marker + "\n")
    before = spec.read_text()
    result = apply_finalization(tmp_path, request, today=date(2026, 9, 6))
    assert spec.read_text() == before.replace("Planned", "Implemented").replace(
        "updated: 2026-06-01", "updated: 2026-09-06"
    )
    assert "spec_status" in result.written


def test_header_only_status_drift_is_repaired_despite_existing_marker(tmp_path: Path) -> None:
    specs = _make_specs_tree(tmp_path)
    request = _implement_request()
    apply_finalization(tmp_path, request)
    spec = specs / "features" / request.feature_slug / "spec.md"
    good = spec.read_text()
    spec.write_text(good.replace("- **Status:** Implemented", "- **Status:** In Progress"))
    result = apply_finalization(tmp_path, request)
    assert spec.read_text() == good
    assert "spec_status" in result.written


def test_new_command_preserves_body_but_normative_edits_still_invalidate(tmp_path: Path) -> None:
    specs = _make_specs_tree(tmp_path)
    request = _implement_request()
    apply_finalization(tmp_path, request)
    spec = specs / "features" / request.feature_slug / "spec.md"
    body = spec.read_bytes()
    before = normative_hash(spec.read_text(), lifecycle_document=True)
    result = apply_finalization(tmp_path, replace(request, command="spec-test", run_id="test"))
    after = normative_hash(spec.read_text(), lifecycle_document=True)
    assert before == after
    assert spec.read_bytes() == body
    assert "<!-- finalize:spec-test:" not in spec.read_text()
    assert "<!-- finalize:spec-test:" in (spec.parent / "changelog.md").read_text()
    spec.write_text(spec.read_text() + "\n## FR-001\nRetain data forever.\n")
    assert normative_hash(spec.read_text(), lifecycle_document=True) != after
    with pytest.raises(FinalizeReceiptError, match="sha256_mismatch"):
        verify_finalize_receipt(result.receipt_path, project_root=tmp_path)


def test_desired_status_in_body_cannot_mask_real_lifecycle_transition(tmp_path: Path) -> None:
    specs = _make_specs_tree(tmp_path)
    request = replace(_implement_request(), status="In Progress")
    spec = specs / "features" / request.feature_slug / "spec.md"
    examples = (
        "\n## Examples\n```gherkin\nstatus: Implemented\n- **Status:** Implemented\n```\n"
        "status: Implemented\n- **Status:** Implemented\nupdated: 2000-01-01\n"
    )
    spec.write_text(spec.read_text() + examples)
    apply_finalization(tmp_path, request)
    before = spec.read_text()
    result = apply_finalization(tmp_path, replace(request, status="Implemented"))
    after = spec.read_text()
    assert "spec_status" in result.written
    assert after.split("## Examples", 1)[1] == before.split("## Examples", 1)[1]
    assert "status: Implemented" in after.split("---", 2)[1]
    assert "- **Status:** Implemented" in after.split("## Examples", 1)[0]


@pytest.mark.parametrize("missing", ["frontmatter", "yaml_status", "header", "header_status"])
def test_body_examples_cannot_replace_missing_lifecycle_anchors(
    tmp_path: Path, missing: str
) -> None:
    specs = _make_specs_tree(tmp_path)
    request = _implement_request()
    spec = specs / "features" / request.feature_slug / "spec.md"
    content = spec.read_text()
    if missing == "frontmatter":
        content = content.split("---", 2)[2]
    elif missing == "yaml_status":
        content = content.replace("status: Planned\n", "", 1)
    elif missing == "header":
        content = content.replace("## Header", "## Example")
    else:
        content = content.replace("- **Status:** Planned\n", "", 1)
    content += "\n## Body\nstatus: Planned\n- **Status:** Planned\n"
    spec.write_text(content)
    before = _registry_snapshot(specs)
    with pytest.raises(FinalizeError, match="status anchors"):
        apply_finalization(tmp_path, request)
    assert _registry_snapshot(specs) == before


def test_crlf_non_lifecycle_bytes_survive_status_transition(tmp_path: Path) -> None:
    specs = _make_specs_tree(tmp_path)
    request = replace(_implement_request(), status="In Progress", run_id="prepare")
    spec = specs / "features" / request.feature_slug / "spec.md"
    body = "\n## FR-001\nKeep exact source bytes.\n```text\nstatus: In Progress\n```\n"
    spec.write_bytes((spec.read_text() + body).replace("\n", "\r\n").encode())
    apply_finalization(tmp_path, request, today=date(2026, 9, 6))
    before = spec.read_bytes()
    apply_finalization(tmp_path, replace(request, status="Implemented"), today=date(2026, 9, 6))
    after = spec.read_bytes()
    expected = before.replace(b"status: In Progress\r\n", b"status: Implemented\r\n", 1)
    expected = expected.replace(
        b"- **Status:** In Progress\r\n", b"- **Status:** Implemented\r\n", 1
    )
    assert after == expected
    assert after.split(b"## FR-001", 1)[1] == before.split(b"## FR-001", 1)[1]
