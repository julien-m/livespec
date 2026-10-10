"""Required v2 identity pairs use real review/finalizer APIs (078 AC-004)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tests.test_finalize import _implement_request, _make_specs_tree
from tests.test_review_feature_resolution import FEATURE, ROOT, _project, _raw
from validator.execution_scope import source_manifest
from validator.finalize import apply_finalization
from validator.lifecycle_metadata import lifecycle_metadata
from validator.semantic.review_api import ingest_feature_review, verify_feature_review
from validator.semantic.review_context import PreparedReview, prepare_review_context
from validator.semantic.review_contract import validate_review_result
from validator.semantic.review_files import prepare_feature_review
from validator.semantic.review_receipts import verify_review_receipt


# @spec AC-004: Only recognized lifecycle fields can change without invalidation.
#   — .specs/features/078-requirement-evidence-integrity/spec.md#ac-004
@pytest.mark.parametrize("band", ["explicit", "legacy"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["LF", "CRLF"])
@pytest.mark.parametrize("change", ["lifecycle", "retention", "threshold", "permission", "created"])
def test_review_identity_retains_every_non_lifecycle_byte(
    tmp_path: Path, band: str, newline: str, change: str
) -> None:
    """Both valid header formats bind business fields and retain raw provenance for CRLF too."""
    feature = _project(tmp_path)
    header = "## Header\n" if band == "explicit" else ""
    original = (
        "---\nstatus: Approved\nupdated: 2026-09-05\ncreated: 2026-09-01\n---\n"
        f"# Retention\n{header}- **Status:** Approved\n- **Updated:** 2026-09-05\n"
        "\n## FR-001\nDelete exports after 24 hours. Threshold is 10. Permission is admin.\n"
        "## AC-001\nExports older than 24 hours are absent.\n"
    ).replace("\n", newline)
    spec = feature / "spec.md"
    spec.write_bytes(original.encode())
    before = prepare_feature_review(tmp_path, FEATURE, "spec", "reviewer/actual")
    receipt, path = ingest_feature_review(
        tmp_path, FEATURE, "spec", [_raw(before)], model="reviewer/actual"
    )
    assert receipt.ready
    changes = {
        "lifecycle": ("Approved", "Implemented"),
        "retention": ("24 hours", "forever"),
        "threshold": ("10.", "99."),
        "permission": ("admin", "everyone"),
        "created": ("2026-09-01", "2026-09-02"),
    }
    updated = original.replace(*changes[change])
    if change == "lifecycle":
        updated = updated.replace("2026-09-05", "2026-09-06")
    spec.write_bytes(updated.encode())
    after = prepare_feature_review(tmp_path, "retention", "spec", "reviewer/actual")
    assert before.source_hashes != after.source_hashes
    assert (before.context_hash == after.context_hash) is (change == "lifecycle")
    assert verify_feature_review(
        tmp_path, "retention", path, model="reviewer/actual", expected_kind="spec"
    ) is (change == "lifecycle")


@pytest.mark.parametrize(
    "source_slug", ["001-auto-llm-review", "077-penflow-cumulative-verdict-consumer"]
)
@pytest.mark.parametrize("band", ["explicit", "legacy"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["LF", "CRLF"])
def test_first_and_subsequent_finalization_preserve_copied_header_body(
    tmp_path: Path, source_slug: str, band: str, newline: str
) -> None:
    """Real finalization changes only metadata, preserving immutable source copies and comments."""
    source = ROOT / ".specs/features" / source_slug / "spec.md"
    source_bytes = source.read_bytes()
    lines = source_bytes.decode().splitlines(keepends=True)
    if band == "explicit":
        title = next(index for index, line in enumerate(lines) if line.startswith("# "))
        lines.insert(title + 1, "\n## Header\n")
    copied = ("".join(lines) + "\n<!-- Historical body comment must remain. -->\n").replace(
        "\n", newline
    )
    specs = _make_specs_tree(tmp_path)
    request = replace(_implement_request(), status="In Progress", run_id="first")
    spec = specs / "features" / request.feature_slug / "spec.md"
    spec.write_bytes(copied.encode())

    def prepare() -> PreparedReview:
        return prepare_review_context(
            request.feature_slug,
            {"spec": spec.read_bytes().decode(), "plan": "Implement the declared contract."},
            model="reviewer/actual",
            max_chars=200000,
        )

    before = prepare()
    receipt = validate_review_result(before, [_raw(before)])
    assert receipt.ready
    metadata = lifecycle_metadata(copied)
    mutable = {field.index for field in (*metadata.frontmatter_fields, *metadata.header_fields)}
    original_lines = copied.encode().splitlines(keepends=True)
    for operation in (request, replace(request, status="Implemented", run_id="subsequent")):
        apply_finalization(tmp_path, operation)
        current_lines = spec.read_bytes().splitlines(keepends=True)
        assert len(current_lines) == len(original_lines)
        assert all(
            original_lines[index] == line
            for index, line in enumerate(current_lines)
            if index not in mutable
        )
        assert verify_review_receipt(receipt, prepare())
    assert before.source_hashes != prepare().source_hashes
    assert source.read_bytes() == source_bytes


@pytest.mark.parametrize(
    "relative",
    ["app/run/status.py", "tests/progress/test_result.py", "config/.execution/runtime.yaml"],
)
def test_generated_keyword_source_test_and_configuration_paths_remain_bound(
    tmp_path: Path, relative: str
) -> None:
    """Explicit real inputs retain raw identity despite generated-output words in their path."""
    feature = _project(tmp_path)
    source = tmp_path / relative
    source.parent.mkdir(parents=True)
    source.write_text("Original governed input.\n")
    spec = feature / "spec.md"

    def prepare() -> PreparedReview:
        key = spec.relative_to(tmp_path).as_posix()
        return prepare_review_context(
            FEATURE,
            {key: spec.read_bytes().decode(), relative: source.read_bytes().decode()},
            source_roles={key: "spec", relative: "plan"},
            model="reviewer/actual",
        )

    before = prepare()
    receipt = validate_review_result(before, [_raw(before)])
    manifest = source_manifest(tmp_path, FEATURE)
    assert receipt.ready
    assert relative in before.source_hashes
    assert relative in manifest
    source.write_text("Changed governed input.\n")
    after = prepare()
    assert before.context_hash != after.context_hash
    assert not verify_review_receipt(receipt, after)
    assert source_manifest(tmp_path, FEATURE)[relative] != manifest[relative]
