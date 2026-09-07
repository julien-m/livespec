"""Execution input freshness, confinement and selected generated-artifact scope."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

import pytest

from tests.execution_evidence_support import FEATURE, run
from tests.execution_evidence_support import project as project
from validator.execution_evidence import verify_execution_receipt
from validator.execution_mapping import ingest_mapping_review, prepare_mapping_review


@pytest.mark.parametrize("change", ["source", "test", "config", "new", "delete"])
def test_any_conservative_input_change_invalidates_capture(project: Path, change: str) -> None:
    path = run(project)
    names = {"source": "app.py", "test": "test_app.py", "config": "pytest.ini", "new": "shared.py"}
    if change == "delete":
        (project / "app.py").unlink()
    else:
        with (project / names[change]).open("a") as stream:
            stream.write("\n# changed input\n")
    result = verify_execution_receipt(path, project, FEATURE)
    assert not result.valid
    assert any("stale" in gap for gap in result.gaps)


def test_changed_during_run_cannot_be_certified(project: Path) -> None:
    command = f"{shlex.quote(sys.executable)} -c " + shlex.quote(
        "from pathlib import Path; Path('app.py').write_text('changed')"
    )
    result = verify_execution_receipt(run(project, command), project, FEATURE)
    assert not result.valid


def test_supported_pytest_input_mutation_rejects_passing_assertion(project: Path) -> None:
    (project / "conftest.py").write_text(
        "from pathlib import Path\n\ndef pytest_runtest_call(item):\n"
        "    Path('app.py').write_text('def add(a, b):\\n    return 0\\n')\n"
    )
    path = run(project)
    capture = json.loads((path.parent / "capture.json").read_text())
    result = verify_execution_receipt(path, project, FEATURE)
    assert capture["exit_code"] == 0 and capture["runner_provenance"]
    assert capture["before"]["app.py"] != capture["after"]["app.py"]
    assert result.executed_tests[0].status == "passed"
    assert result.executed_tests[0].assertion_count == 1
    assert not result.valid and result.certified_acs == []
    assert "Execution inputs changed during invocation" in result.gaps


def test_foreign_feature_and_copy_are_rejected(project: Path) -> None:
    path = run(project)
    assert not verify_execution_receipt(path, project, "002-other").valid
    copied = project / "copied.json"
    copied.write_bytes(path.read_bytes())
    assert not verify_execution_receipt(copied, project, FEATURE).valid


def test_report_replacement_with_identical_bytes_is_rejected(project: Path) -> None:
    path = run(project)
    report = path.parent / "report"
    replacement = path.parent / "replacement"
    replacement.write_bytes(report.read_bytes())
    replacement.replace(report)
    result = verify_execution_receipt(path, project, FEATURE)
    assert not result.valid
    assert any("replaced" in gap for gap in result.gaps)


def test_parent_traversal_cannot_read_evidence(project: Path) -> None:
    from validator.execution_scope import read_regular

    with pytest.raises(ValueError, match="traverse"):
        read_regular(project / "../outside", project)


def test_internal_source_links_are_bound_without_following_external_links(project: Path) -> None:
    (project / "alias.py").symlink_to(project / "app.py")
    path = run(project)
    assert verify_execution_receipt(path, project, FEATURE).valid
    (project / "alias.py").unlink()
    (project / "alias.py").symlink_to(project / "test_app.py")
    assert not verify_execution_receipt(path, project, FEATURE).valid


def test_selected_lifecycle_metadata_preserves_execution_readiness(project: Path) -> None:
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text("---\nstatus: Approved\nupdated: 2026-09-05\n---\n" + spec.read_text())
    # Rebuild the fixture review against the changed initial source positions.
    mapping = project / "mapping.json"
    prepared = prepare_mapping_review(project, FEATURE, mapping)
    receipt_path = project / "acceptance-review.json"
    receipt = json.loads(receipt_path.read_text())
    response = json.loads(receipt["raw_results"][0])
    response["reviewed_section_ids"] = [s.section_id for s in prepared.sections]
    spec_section = next(s for s in prepared.sections if "AC-001" in s.text and s.role == "spec")
    response["conclusions"][0]["source_citations"][0]["section_id"] = spec_section.section_id
    assert ingest_mapping_review(prepared, [json.dumps(response)], receipt_path).ready
    path = run(project)
    spec.write_text(
        spec.read_text().replace("Approved", "Implemented").replace("2026-09-05", "2026-09-06")
    )
    result = verify_execution_receipt(path, project, FEATURE)
    assert result.valid, result.gaps
    spec.write_text(spec.read_text().replace("returns three", "returns four"))
    assert not verify_execution_receipt(path, project, FEATURE).valid


def test_application_execution_named_directory_remains_in_scope(project: Path) -> None:
    nested = project / "app/.execution"
    nested.mkdir(parents=True)
    source = nested / "config.json"
    source.write_text('{"enabled": true}')
    path = run(project)
    assert verify_execution_receipt(path, project, FEATURE).valid
    source.write_text('{"enabled": false}')
    assert not verify_execution_receipt(path, project, FEATURE).valid


def test_explicit_normative_reference_overrides_generated_exclusion(project: Path) -> None:
    from validator.execution_scope import source_manifest

    reference = project / ".specs/.runs/normative.md"
    reference.parent.mkdir()
    reference.write_text("Approved limits: 24 hours")
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(spec.read_text() + "\nRead [approved limits](../../.runs/normative.md).\n")
    before = source_manifest(project, FEATURE)
    assert ".specs/.runs/normative.md" in before
    reference.write_text("Approved limits: 48 hours")
    assert source_manifest(project, FEATURE) != before


def test_publication_parent_swap_cannot_redirect_writes(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import validator.execution_capture as capture

    original = capture._write_new
    outside = project.parent / (project.name + "-outside")
    outside.mkdir()
    moved = False

    def replace_parent(descriptor: int, name: str, data: bytes) -> None:
        nonlocal moved
        original(descriptor, name, data)
        if not moved:
            moved = True
            storage = project / ".specs/.execution"
            storage.rename(project / ".specs/execution-old")
            storage.symlink_to(outside, target_is_directory=True)

    monkeypatch.setattr(capture, "_write_new", replace_parent)
    path = run(project)
    assert not verify_execution_receipt(path, project, FEATURE).valid
    assert not list(outside.iterdir())


def test_generated_registry_and_selected_progress_do_not_invalidate(project: Path) -> None:
    path = run(project)
    for name in ("README.md", "changelog.md", "roadmap.md"):
        (project / ".specs" / name).write_text("Generated completed status")
    feature = project / ".specs/features" / FEATURE
    for name in ("progress.md", "implementation.md", "pipeline.md", "changelog.md"):
        (feature / name).write_text("Generated completed status")
    (feature / ".reviews").mkdir()
    (feature / ".reviews/generated.json").write_text("{}")
    (feature / "run").mkdir()
    (feature / "run/generated.json").write_text("{}")
    assert verify_execution_receipt(path, project, FEATURE).valid
    (project / "README.md").write_text("Actual application behavior changed")
    assert not verify_execution_receipt(path, project, FEATURE).valid


def test_other_feature_documents_remain_bound(project: Path) -> None:
    path = run(project)
    other = project / ".specs/features/002-other"
    other.mkdir()
    (other / "spec.md").write_text("AC-001: New cross-feature behavior")
    assert not verify_execution_receipt(path, project, FEATURE).valid


def test_selected_run_reference_overrides_generated_exclusion(project: Path) -> None:
    from validator.execution_scope import source_manifest

    feature = project / ".specs/features" / FEATURE
    reference = feature / "run/approved-contract.md"
    reference.parent.mkdir()
    reference.write_text("Approved retry limit: 1")
    spec = feature / "spec.md"
    spec.write_text(spec.read_text() + "\nRead [retry contract](run/approved-contract.md).\n")
    before = source_manifest(project, FEATURE)
    assert reference.relative_to(project).as_posix() in before
    reference.write_text("Approved retry limit: 2")
    assert source_manifest(project, FEATURE) != before


def _review_spec_fixture(project: Path, text: str) -> Path:
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(text)
    prepared = prepare_mapping_review(project, FEATURE, project / "mapping.json")
    receipt_path = project / "acceptance-review.json"
    response = json.loads(json.loads(receipt_path.read_text())["raw_results"][0])
    response["reviewed_section_ids"] = [section.section_id for section in prepared.sections]
    section = next(
        item for item in prepared.sections if item.role == "spec" and "AC-001" in item.text
    )
    response["conclusions"][0]["source_citations"][0]["section_id"] = section.section_id
    assert ingest_mapping_review(prepared, [json.dumps(response)], receipt_path).ready
    return spec


@pytest.mark.parametrize("band", ["explicit", "legacy"])
@pytest.mark.parametrize("change", ["lifecycle", "retention", "threshold", "permission", "created"])
def test_lifecycle_bands_preserve_only_status_updated_execution_identity(
    project: Path, band: str, change: str
) -> None:
    from validator.execution_scope import digest

    heading = "## Header\n" if band == "explicit" else ""
    text = (
        "---\nstatus: Approved\nupdated: 2026-09-05\ncreated: 2026-09-01\n---\n"
        f"# Addition\n{heading}- **Status:** Approved\n- **Updated:** 2026-09-05\n"
        "\n## AC-001\nAC-001: Adding one and two returns three.\n"
        "Retention is 24h. Threshold is 10. Permission is admin.\n"
    )
    spec = _review_spec_fixture(project, text)
    path = run(project)
    capture = json.loads((path.parent / "capture.json").read_text())
    changes = {
        "lifecycle": ("Approved", "Implemented"),
        "retention": ("24h", "forever"),
        "threshold": ("10.", "99."),
        "permission": ("admin", "everyone"),
        "created": ("2026-09-01", "2026-09-02"),
    }
    updated = text.replace(*changes[change])
    if change == "lifecycle":
        updated = updated.replace("2026-09-05", "2026-09-06")
    spec.write_text(updated)
    result = verify_execution_receipt(path, project, FEATURE)
    assert capture["raw_before"][spec.relative_to(project).as_posix()] != digest(spec.read_bytes())
    assert result.valid is (change == "lifecycle"), result.gaps
    assert bool(result.certified_acs) is (change == "lifecycle")
