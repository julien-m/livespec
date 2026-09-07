"""Independent runtime capture never promotes missing source authority to PASS."""

import json
import shutil
from pathlib import Path

import pytest

from tests.integration.helpers.witness_penflow import REPO, capture_penflow


def test_capture_rejects_evidence_inside_generator_workspace(tmp_path: Path) -> None:
    result = capture_penflow(tmp_path, tmp_path / "evidence")
    assert result.manifest is None
    assert result.diagnostic == "capture_requires_independent_confined_paths"


def test_capture_rejects_candidate_symlink_escape(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "escape").symlink_to(tmp_path)
    result = capture_penflow(candidate, tmp_path / "evidence")
    assert result.manifest is None
    assert not (candidate / ".witness-runner").exists()


def test_real_browser_capture_retains_missing_penflow_authority(tmp_path: Path) -> None:
    if not shutil.which("node") or not (REPO / "node_modules/@playwright/test").exists():
        pytest.skip("Node/Playwright unavailable")
    candidate = tmp_path / "candidate"
    shutil.copytree(REPO / "tests/integration/fixtures/witness-ui-form/seed", candidate)
    result = capture_penflow(candidate, tmp_path / "evidence")
    if result.diagnostic == "browser_capture_failed":
        transcript = json.loads((tmp_path / "evidence/browser-process.json").read_text())
        if "Executable doesn't exist" in transcript["stderr"]:
            pytest.skip("Chromium unavailable")
    raw = json.loads((tmp_path / "evidence/browser.json").read_text())
    assert raw["source_kind"] == "runtime-capture"
    assert raw["invalid"]["submissions"] == 0
    assert raw["valid"]["submissions"] == 1
    assert raw["valid"]["nodes"][-1]["text"] == "Atelier du jeudi"
    assert result.manifest is None
    assert result.diagnostic in {
        "penflow_unavailable",
        "penflow_source_authority_unavailable",
        "penflow_local_submit_requires_unsupported_request_semantics",
    }
    assert result.receipt is None
    if result.diagnostic != "penflow_unavailable":
        authority = json.loads((tmp_path / "evidence/source-authority.json").read_text())
        assert authority["exit_code"] != 0
        assert (tmp_path / "evidence/penflow-run.json").is_file()
        assert (tmp_path / "evidence/penflow-validation.json").is_file()
        capability = json.loads((tmp_path / "evidence/local-submit-capability.json").read_text())
        if result.diagnostic == "penflow_local_submit_requires_unsupported_request_semantics":
            assert capability["exit_code"] != 0
            assert "mutation" in capability["stdout"]


def test_capture_does_not_follow_candidate_root_symlink(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.symlink_to(tmp_path, target_is_directory=True)
    assert capture_penflow(candidate, tmp_path / "external").manifest is None
    assert not (tmp_path / ".witness-runner").exists()


def test_missing_generated_entrypoint_stays_explicit(tmp_path: Path) -> None:
    if not shutil.which("node"):
        pytest.skip("Node unavailable")
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    result = capture_penflow(candidate, tmp_path / "evidence")
    assert result.diagnostic == "candidate_entrypoint_missing"
    assert result.manifest is None


def _semantic_source(duplicate: bool) -> str:
    source = (REPO / "tests/integration/fixtures/witness-ui-form/seed/index.html").read_text()
    source = source.replace(
        "<body>",
        '<body><main data-semantic-id="form" data-screen="form" '
        'data-state="default" data-actor="operator">',
    )
    source = source.replace("</body>", "</main></body>")
    source = source.replace(
        'data-semantic-id="item-name"', 'data-semantic-id="item-name" data-action="edit_name"'
    )
    source = source.replace(
        'data-semantic-id="submit-item"', 'data-semantic-id="submit-item" data-action="submit_item"'
    )
    source = source.replace(
        "success.hidden = false;",
        "success.hidden = false; document.querySelector('main').dataset.state = 'success';",
    )
    if duplicate:
        source = source.replace(
            "success.hidden = false;",
            "success.hidden = false; "
            "if (!window.duplicated) {window.duplicated = true; "
            "form.dispatchEvent(new Event('submit', {bubbles:true}));}",
        )
    return source


def _measured_candidate(tmp_path: Path, *, duplicate: bool = False) -> tuple[Path, Path]:
    """Run a small actual browser fixture; no fake observation packets."""
    from tests.integration.helpers.witness_penflow import ADAPTER, _execute
    from tests.integration.helpers.witness_penflow_runtime import SCENARIOS

    candidate, runner = tmp_path / "candidate", tmp_path / "candidate/runner"
    runner.mkdir(parents=True)
    source = _semantic_source(duplicate)
    (candidate / "index.html").write_text(source)
    contract = candidate / "penflow/flow-ui-contract/contract.json"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        json.dumps(
            {
                "outcome_expectations": [
                    {"obligation_id": identifier, "category": identifier.split(":")[0]}
                    for identifier in SCENARIOS
                ]
            }
        )
    )
    assert (
        _execute(
            [
                shutil.which("node") or "node",
                str(ADAPTER),
                str(candidate),
                str(runner / "browser.json"),
                str(REPO / "package.json"),
            ],
            candidate,
            tmp_path / "browser-process.json",
        )
        == 0
    )
    return candidate, runner


def test_typed_observations_preserve_actual_events_and_states(tmp_path: Path) -> None:
    from tests.integration.helpers.witness_penflow_runtime import convert_runtime

    candidate, runner = _measured_candidate(tmp_path)
    paths = convert_runtime(candidate, runner, "actual-build")
    observations = [
        json.loads(path.read_text()) for path in paths if path.parent.name == "outcome-observations"
    ]
    assert len(observations) == 5
    transition = next(item for item in observations if item["category"] == "transition")
    assert transition["before"]["state"] == "default"
    assert transition["after"]["state"] == "success"
    assert transition["after"]["properties"]["submissions"] == 1
    raw = json.loads((runner / "browser.json").read_text())
    assert any(event["trusted"] and event["type"] == "submit" for event in raw["valid"]["events"])


def test_duplicate_submit_is_retained_for_authority_rejection(tmp_path: Path) -> None:
    from tests.integration.helpers.witness_penflow_runtime import convert_runtime

    candidate, runner = _measured_candidate(tmp_path, duplicate=True)
    convert_runtime(candidate, runner, "duplicate-build")
    transition = json.loads(
        (candidate / "penflow/outcome-observations/transition--show_success.json").read_text()
    )
    assert transition["after"]["properties"]["submissions"] == 2


def test_unmapped_actual_action_is_never_invented(tmp_path: Path) -> None:
    from tests.integration.helpers.witness_penflow_runtime import convert_runtime

    candidate, runner = _measured_candidate(tmp_path)
    raw = json.loads((runner / "browser.json").read_text())
    for snapshot in (raw[key] for key in ("before", "invalid", "edited", "valid")):
        for node in snapshot["nodes"]:
            node["context"].pop("action", None)
    (runner / "browser.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="No actual trusted action"):
        convert_runtime(candidate, runner, "unmapped-build")
