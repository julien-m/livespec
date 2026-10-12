"""Scoped bugfix gate: READY, ELIGIBLE and every fallback reason (084 AC-003 to AC-011)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.bugfix_support import FEATURE, FIXED, SPEC, TEST, BugfixProject, git, make_project
from validator.bugfix.requirements import changed_requirements, requirement_definitions
from validator.semantic.review_contract import Citation, GroundedFinding, ReviewReceipt


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BugfixProject:
    built = make_project(tmp_path)
    built.write("tests/test_calc.py", TEST)
    monkeypatch.chdir(built.root)
    return built


def _red(project: BugfixProject) -> str:
    code, receipt = project.capture("red")
    assert code == 0
    return receipt


def _fixed(project: BugfixProject) -> tuple[str, str]:
    red = _red(project)
    project.write("calc.py", FIXED)
    code, green = project.capture("green")
    assert code == 0
    return red, green


def _gate(project: BugfixProject, *args: str) -> tuple[int, dict[str, Any]]:
    result = project.run("bugfix", "gate", "--feature", FEATURE, "--json", *args)
    return result.exit_code, json.loads(result.output)


def _codes(payload: dict[str, Any]) -> set[str]:
    return {reason["code"] for reason in payload["reasons"]}


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def test_pre_edit_gate_is_ready_without_any_review(
    project: BugfixProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*_: object, **__: object) -> None:
        raise AssertionError("whole-feature readiness or review must not run")

    monkeypatch.setattr("validator.progression_gate.require_progression", forbidden)
    monkeypatch.setattr("validator.semantic.review_files.prepare_feature_review", forbidden)
    red = _red(project)
    before = _tree_hashes(project.root)

    code, payload = _gate(project, "--red", red)

    assert (code, payload["verdict"], payload["reasons"]) == (0, "READY", [])
    assert _tree_hashes(project.root) == before


def test_whole_lane_runs_without_any_review_or_llm_call(
    project: BugfixProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-001: capture, both gates and record never prepare a review or call a model."""

    def forbidden(*_: object, **__: object) -> None:
        raise AssertionError("review preparation, readiness or LLM call must not run")

    for target in (
        "validator.progression_gate.require_progression",
        "validator.semantic.review_files.prepare_feature_review",
        "validator.llm_provider.call_llm",
    ):
        monkeypatch.setattr(target, forbidden)
    red = _red(project)
    assert _gate(project, "--red", red)[1]["verdict"] == "READY"
    project.write("calc.py", FIXED)
    _, green = project.capture("green")
    assert _gate(project, "--red", red, "--green", green)[1]["verdict"] == "ELIGIBLE"

    args = ("--feature", FEATURE, "--red", red, "--green", green, "--summary", "sum")
    assert project.run("bugfix", "record", *args).exit_code == 0


def test_closing_gate_is_eligible_with_measured_diff(project: BugfixProject) -> None:
    red, green = _fixed(project)
    before = _tree_hashes(project.root)

    code, payload = _gate(project, "--red", red, "--green", green)

    assert (code, payload["verdict"]) == (0, "ELIGIBLE"), payload["reasons"]
    assert payload["regression_tests"] == ["tests/test_calc.py::test_add"]
    assert payload["counted_files"] == ["calc.py", "tests/test_calc.py"]
    assert payload["counted_lines"] == 2 + 5
    assert payload["limits"]["max_files"] == 8 and payload["limits"]["max_lines"] == 300
    assert _tree_hashes(project.root) == before


def test_text_output_names_verdict_and_fallback_command(project: BugfixProject) -> None:
    red = _red(project)
    project.write(f".specs/features/{FEATURE}/spec.md", SPEC.replace("their sum", "a total"))

    result = project.run("bugfix", "gate", "--feature", FEATURE, "--red", red)

    assert result.exit_code == 1
    assert "Bugfix gate: FALLBACK" in result.output
    assert "spec_requirement_text_changed" in result.output and "AC-001" in result.output
    assert f"livespec validate .specs/features/{FEATURE} --progression implement" in result.output


def test_requirement_text_change_falls_back_but_other_spec_lines_do_not(
    project: BugfixProject,
) -> None:
    red, green = _fixed(project)
    spec = project.feature_dir / "spec.md"
    spec.write_text(SPEC.replace("- **Status:** Implemented", "- **Status:** In Progress"))
    assert _gate(project, "--red", red, "--green", green)[0] == 0

    spec.write_text(SPEC.replace("their difference", "a - b"))
    code, payload = _gate(project, "--red", red, "--green", green)
    assert code == 1 and payload["verdict"] == "FALLBACK"
    assert "spec_requirement_text_changed" in _codes(payload)
    assert payload["fallback_command"].endswith(f"{FEATURE} --progression implement")


def test_heading_definitions_include_their_body() -> None:
    assert "their sum" in requirement_definitions(SPEC)["AC-001"]
    assert changed_requirements(SPEC, SPEC.replace("their sum", "a total")) == ["AC-001"]
    assert changed_requirements(SPEC, SPEC + "\n- **SC-001:** new\n") == ["SC-001"]


def test_invalid_or_foreign_red_receipt(project: BugfixProject, tmp_path: Path) -> None:
    project.write("calc.py", FIXED)
    _, passing = project.capture("green")
    assert "red_receipt_invalid" in _codes(_gate(project, "--red", passing)[1])
    assert "red_receipt_invalid" in _codes(_gate(project, "--red", str(tmp_path / "x.json"))[1])


def test_red_stays_valid_after_the_fix_but_green_must_be_current(
    project: BugfixProject,
) -> None:
    red, green = _fixed(project)
    assert _gate(project, "--red", red)[0] == 0  # historical RED survives the fix
    project.write("calc.py", FIXED + "\n# later edit\n")
    assert "green_receipt_invalid" in _codes(_gate(project, "--red", red, "--green", green)[1])


def test_changed_regression_test_and_test_support(project: BugfixProject) -> None:
    red = _red(project)
    project.write("calc.py", FIXED)
    project.write("tests/test_calc.py", TEST + "\n\ndef test_more():\n    assert add(1, 1) == 2\n")
    _, green = project.capture("green")
    assert "regression_test_changed" in _codes(_gate(project, "--red", red, "--green", green)[1])

    project.write("tests/test_calc.py", TEST)
    project.write("tests/conftest.py", "# helper\n")
    _, green = project.capture("green")
    assert "test_support_changed" in _codes(_gate(project, "--red", red, "--green", green)[1])


def test_order_and_missing_fix(project: BugfixProject) -> None:
    red, green = _fixed(project)
    codes = _codes(_gate(project, "--red", green, "--green", red)[1])
    assert "red_receipt_invalid" in codes and "green_receipt_invalid" in codes

    project.write("calc.py", FIXED)
    _, green_again = project.capture("green")
    _, payload = _gate(project, "--red", red, "--green", green_again)
    assert payload["verdict"] == "ELIGIBLE"


def test_no_regression_test_when_red_test_is_not_rerun(project: BugfixProject) -> None:
    red = _red(project)
    project.write("calc.py", FIXED)
    project.write("tests/test_other.py", "def test_other():\n    assert True\n")
    _, green = project.capture("green", "tests/test_other.py")
    codes = _codes(_gate(project, "--red", red, "--green", green)[1])
    assert "no_regression_test" in codes


def test_diff_too_large_binary_and_base_config(project: BugfixProject) -> None:
    project.write(".specs/bugfix.yaml", "max_files: 2\n")
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "limits")
    red, green = _fixed(project)
    assert _gate(project, "--red", red, "--green", green)[0] == 0

    project.write(".specs/bugfix.yaml", "max_files: 50\n")  # working-tree change is ignored
    project.write("notes.txt", "x\n")
    code, payload = _gate(project, "--red", red, "--green", green)
    assert code == 1 and "diff_too_large" in _codes(payload)
    assert payload["limits"]["max_files"] == 2

    (project.root / "blob.bin").write_bytes(b"\0\1")
    assert "diff_binary" in _codes(_gate(project, "--red", red, "--green", green)[1])


def test_invalid_config_exits_3(project: BugfixProject) -> None:
    project.write(".specs/bugfix.yaml", "max_files: 0\n")
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "bad limits")
    red = _red(project)
    result = project.run("bugfix", "gate", "--feature", FEATURE, "--red", red)
    assert result.exit_code == 3 and "max_files" in result.output


def test_diff_unavailable_in_both_modes(project: BugfixProject) -> None:
    red, green = _fixed(project)
    assert "diff_unavailable" in _codes(_gate(project, "--red", red, "--base", "nope")[1])
    closing = _gate(project, "--red", red, "--green", green, "--base", "nope")[1]
    assert "diff_unavailable" in _codes(closing)


def test_owner_not_identified(project: BugfixProject) -> None:
    red = _red(project)
    (project.feature_dir / "implementation.md").unlink()
    code, payload = _gate(project, "--red", red)
    assert code == 1 and "owner_not_identified" in _codes(payload)


def _receipt_with_blocking_finding(project: BugfixProject, requirement: str) -> None:
    receipt = ReviewReceipt(
        context_hash="x",
        reviewer_model="m",
        complete=True,
        ready=False,
        errors=[],
        findings=[
            GroundedFinding(
                category="consistency",
                severity="blocking",
                description=f"{requirement} contradicts the plan",
                suggestion="fix",
                citations=[Citation(section_id="s", excerpt=requirement)],
            )
        ],
    )
    (project.feature_dir / ".reviews").mkdir()
    (project.feature_dir / ".reviews" / "spec.json").write_text(receipt.model_dump_json())


def test_cited_requirement_is_checked_alone(project: BugfixProject) -> None:
    red = _red(project)
    assert _gate(project, "--red", red, "--requirement", "AC-001")[0] == 0  # no receipt
    _receipt_with_blocking_finding(project, "AC-002")

    assert _gate(project, "--red", red, "--requirement", "AC-001")[0] == 0
    code, payload = _gate(project, "--red", red, "--requirement", "AC-002")
    assert code == 1 and "requirement_blocking_finding" in _codes(payload)
    assert "requirement_unknown" in _codes(
        _gate(project, "--red", red, "--requirement", "FR-009")[1]
    )


def test_green_captured_before_red_is_out_of_order(project: BugfixProject) -> None:
    project.write("calc.py", FIXED)
    _, green = project.capture("green")
    project.write("calc.py", FIXED.replace("a + b", "a - b"))
    red = _red(project)
    project.write("calc.py", FIXED)  # GREEN inputs are current again

    code, payload = _gate(project, "--red", red, "--green", green)

    assert code == 1 and _codes(payload) == {"receipt_order_invalid"}


def test_committed_fix_needs_the_base_before_it(project: BugfixProject) -> None:
    red, green = _fixed(project)
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "fix")

    assert "fix_not_in_diff" in _codes(_gate(project, "--red", red, "--green", green)[1])
    assert _gate(project, "--red", red, "--green", green, "--base", "HEAD~1")[0] == 0


def test_green_with_a_different_test_command(project: BugfixProject) -> None:
    red = _red(project)
    project.write("calc.py", FIXED)
    command = f"{sys.executable} -m pytest -q -p no:cacheprovider -x tests/test_calc.py"
    result = project.run(
        "bugfix", "capture", "--feature", FEATURE, "--expect", "green", "--command", command
    )
    green = result.output.splitlines()[0].split(": ", 1)[1]

    codes = _codes(_gate(project, "--red", red, "--green", green)[1])

    assert codes == {"command_mismatch"}


def test_gherkin_change_leaves_the_lane(project: BugfixProject) -> None:
    gherkin = "\n```gherkin\nFeature: Calc\n  Scenario: Add\n    Then add returns 5\n```\n"
    project.write(f".specs/features/{FEATURE}/spec.md", SPEC + gherkin)
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "gherkin")
    red = _red(project)
    project.write(f".specs/features/{FEATURE}/spec.md", SPEC + gherkin.replace("5", "6"))

    _, payload = _gate(project, "--red", red)

    assert "Gherkin scenarios" in payload["reasons"][0]["detail"]


def test_unreadable_review_receipt_is_not_ignored(project: BugfixProject) -> None:
    red = _red(project)
    (project.feature_dir / ".reviews").mkdir()
    (project.feature_dir / ".reviews" / "spec.json").write_text("{not json")

    assert _gate(project, "--red", red)[0] == 0  # uncited: the receipt is never read
    codes = _codes(_gate(project, "--red", red, "--requirement", "AC-001")[1])
    assert codes == {"review_receipt_unreadable"}


def test_editing_an_existing_test_leaves_the_lane(project: BugfixProject) -> None:
    project.write("tests/test_old.py", "def test_old():\n    assert True\n")
    git(project.root, "add", "tests/test_old.py")
    git(project.root, "commit", "-qm", "old test")
    project.write("tests/test_old.py", "def test_old():\n    pass\n")  # weakened before RED
    red, green = _fixed(project)

    codes = _codes(_gate(project, "--red", red, "--green", green)[1])

    assert codes == {"existing_test_changed"}


def test_unignored_receipts_do_not_count_against_the_limits(project: BugfixProject) -> None:
    project.write(".gitignore", "__pycache__/\n")
    git(project.root, "commit", "-qam", "receipts visible to git")
    red, green = _fixed(project)

    code, payload = _gate(project, "--red", red, "--green", green)

    assert code == 0 and payload["counted_files"] == ["calc.py", "tests/test_calc.py"]


def test_partial_config_overrides_declared_keys_only(project: BugfixProject) -> None:
    project.write(".specs/bugfix.yaml", "max_lines: 1\n")
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "lines only")
    red, green = _fixed(project)
    _, payload = _gate(project, "--red", red, "--green", green)
    assert payload["limits"]["max_files"] == 8 and payload["limits"]["max_lines"] == 1
    assert "diff_too_large" in _codes(payload)

    project.write(".specs/bugfix.yaml", "max_lines: 1\nmax_lnes: 9\n")
    git(project.root, "commit", "-qam", "typo key")
    result = project.run("bugfix", "gate", "--feature", FEATURE, "--red", red, "--base", "HEAD")
    assert result.exit_code == 3 and "max_lnes" in result.output


def test_project_nested_in_a_larger_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    nested = make_project(tmp_path, nested=True)
    nested.write(".specs/bugfix.yaml", "max_files: 1\n")
    git(nested.root, "add", "-A")
    git(nested.root, "commit", "-qm", "limits")
    nested.write("tests/test_calc.py", TEST)
    monkeypatch.chdir(nested.root)
    red, green = _fixed(nested)

    _, payload = _gate(nested, "--red", red, "--green", green)

    assert payload["counted_files"] == ["calc.py", "tests/test_calc.py"]
    assert payload["limits"]["max_files"] == 1 and "diff_too_large" in _codes(payload)
    nested.write(f".specs/features/{FEATURE}/spec.md", SPEC.replace("their sum", "a total"))
    assert "spec_requirement_text_changed" in _codes(_gate(nested, "--red", red)[1])


def test_ambiguous_cited_requirement(project: BugfixProject) -> None:
    project.write(
        f".specs/features/{FEATURE}/spec.md",
        SPEC.replace("their sum.", "their sum [NEEDS CLARIFICATION: overflow]."),
    )
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "marked")
    red = _red(project)
    codes = _codes(_gate(project, "--red", red, "--requirement", "AC-001")[1])
    assert codes == {"requirement_ambiguous"}
