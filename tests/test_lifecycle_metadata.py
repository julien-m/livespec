"""Real legacy specification bands retain lifecycle compatibility without masking body text."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from tests.review_support import grounded_response
from tests.test_finalize import _implement_request, _make_specs_tree
from validator.finalize import apply_finalization
from validator.lifecycle_metadata import lifecycle_metadata
from validator.normative_identity import NORMATIVE_IDENTITY_VERSION, normative_hash
from validator.semantic.review_context import prepare_review_context
from validator.semantic.review_contract import validate_review_result
from validator.semantic.review_receipts import verify_review_receipt

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    "source_slug", ["001-auto-llm-review", "077-penflow-cumulative-verdict-consumer"]
)
def test_real_legacy_spec_finalization_keeps_review_current(
    tmp_path: Path, source_slug: str
) -> None:
    source = ROOT / ".specs/features" / source_slug / "spec.md"
    original = source.read_bytes()
    assert b"## Header\n" not in original
    specs = _make_specs_tree(tmp_path)
    request = replace(_implement_request(), status="In Progress", run_id="prepare")
    spec = specs / "features" / request.feature_slug / "spec.md"
    spec.write_bytes(original)

    def prepare():
        return prepare_review_context(
            request.feature_slug,
            {"spec": spec.read_text(), "plan": "# Plan\nImplement the declared contract.\n"},
            model="reviewer/v1",
            max_chars=200000,
        )

    before = prepare()
    receipt = validate_review_result(before, [grounded_response(before)])
    assert receipt.ready, receipt.errors
    metadata = lifecycle_metadata(spec.read_text())
    mutable = {field.index for field in (*metadata.frontmatter_fields, *metadata.header_fields)}
    apply_finalization(tmp_path, request, today=date(2026, 9, 6))
    first = spec.read_text().splitlines(keepends=True)
    for index, line in enumerate(original.decode().splitlines(keepends=True)):
        if index not in mutable:
            assert first[index] == line
    assert prepare().context_hash == before.context_hash
    assert verify_review_receipt(receipt, prepare())
    apply_finalization(tmp_path, replace(request, status="Implemented", run_id="complete"))
    assert verify_review_receipt(receipt, prepare())
    assert source.read_bytes() == original
    spec.write_text(spec.read_text() + "\n## FR-999\nRetain every export forever.\n")
    assert not verify_review_receipt(receipt, prepare())


@pytest.mark.parametrize("boundary", ["## Requirements", "---", "***", "___", "### Detail"])
def test_legacy_band_ends_before_body_status_and_fenced_examples(boundary: str) -> None:
    initial = (
        "---\nstatus: Approved\n---\n# Feature\n- **Status:** Approved\n"
        "```text\n- **Status:** In Progress\n```\n"
        f"{boundary}\n- **Status:** In Progress\n"
    )
    metadata_change = initial.replace("status: Approved", "status: Implemented").replace(
        "- **Status:** Approved", "- **Status:** Implemented"
    )
    assert normative_hash(initial, lifecycle_document=True) == normative_hash(
        metadata_change, lifecycle_document=True
    )
    assert normative_hash(initial, lifecycle_document=True) != normative_hash(
        initial.replace("In Progress", "Implemented"), lifecycle_document=True
    )


@pytest.mark.parametrize(
    "text",
    [
        "# Feature\n- **Status:** Approved\n- **Status:** Draft\n## Rules\n",
        "# Feature\n- **Status:** Draft\n## Header\n- **Status:** Approved\n",
        "# Feature\n## Rules\n## Header\n- **Status:** Approved\n",
        "---\nstatus: Approved\nstatus: Draft\n---\n# Feature\n",
        "---\nstatus: [Approved\n---\n# Feature\n- **Status:** Approved\n",
    ],
)
def test_ambiguous_or_malformed_bands_remain_fully_bound(text: str) -> None:
    with pytest.raises(ValueError):
        lifecycle_metadata(text)
    assert normative_hash(text, lifecycle_document=True) != normative_hash(
        text.replace("Approved", "Implemented"), lifecycle_document=True
    )


def test_identity_policy_version_invalidates_prior_receipts() -> None:
    assert NORMATIVE_IDENTITY_VERSION == "2"
