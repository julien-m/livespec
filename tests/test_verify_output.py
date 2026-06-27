# @spec(AC-003)

# LiveSpec traceability anchors
# @spec(AC-005)
# @spec(AC-008)
# @spec(AC-009)

"""Unit tests for the shared verify-output rule engine (``validator/verify_output.py``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from validator.verify_output import evaluate_rules, render_report, to_json_envelope


def make_artifact(
    *,
    exit_code: int | None = 0,
    flags: list[str] | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    timestamp: str = "2026-06-10T10:00:00+00:00",
) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "schema_version": "2.0",
        "goal_hash": "a" * 64,
        "command": "spec-specify",
        "feature": None,
        "flags": flags or [],
        "exit_code": exit_code,
        "timestamp": timestamp,
    }
    if stdout is not None:
        artifact["stdout"] = stdout
    if stderr is not None:
        artifact["stderr"] = stderr
    return artifact


def rules_of(**buckets: list[dict[str, Any]]) -> dict[str, Any]:
    base: dict[str, Any] = {"must": [], "may": [], "must_not": [], "when": []}
    base.update(buckets)
    return base


class TestOutcomeMatrix:
    def test_all_must_pass_is_success(self, tmp_path: Path) -> None:
        rules = rules_of(must=[{"verb": "must", "kind": "exit_code", "payload": 0}])
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert report.outcome == "success"
        assert [r.status for r in report.rules] == ["PASS"]

    def test_failed_must_with_exit_zero_is_drift(self, tmp_path: Path) -> None:
        rules = rules_of(
            must=[{"verb": "must", "kind": "contains", "payload": "absent text"}],
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0, stdout="something else"),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert report.outcome == "drift"

    def test_nonzero_exit_is_error(self, tmp_path: Path) -> None:
        report = evaluate_rules(
            rules_of(),
            artifact=make_artifact(exit_code=3),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert report.outcome == "error"

    def test_goal_incomplete_with_exit_zero_is_drift(self, tmp_path: Path) -> None:
        report = evaluate_rules(
            rules_of(),
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
            goal_incomplete=True,
        )
        assert report.outcome == "drift"

    def test_receipt_error_forces_error(self, tmp_path: Path) -> None:
        report = evaluate_rules(
            rules_of(),
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
            receipt_error=True,
        )
        assert report.outcome == "error"


class TestWhenBranches:
    def test_branches_accumulate_for_all_active_flags(self, tmp_path: Path) -> None:
        rules = rules_of(
            must=[{"verb": "must", "kind": "exit_code", "payload": 0}],
            when=[
                {
                    "flag": "--visual",
                    "must": [{"verb": "must", "kind": "contains", "payload": "visual gate"}],
                    "may": [],
                    "must_not": [],
                },
                {
                    "flag": "--strict",
                    "must": [{"verb": "must", "kind": "contains", "payload": "strict mode"}],
                    "may": [],
                    "must_not": [],
                },
            ],
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(
                exit_code=0,
                flags=["--visual", "--strict"],
                stdout="visual gate on, strict mode on",
            ),
            active_flags=["--visual", "--strict"],
            feature=None,
            project_root=tmp_path,
        )
        # Base rule + both branch rule sets are evaluated (039 AC-009).
        assert len(report.rules) == 3
        assert report.outcome == "success"

    def test_inactive_branch_not_evaluated(self, tmp_path: Path) -> None:
        rules = rules_of(
            when=[
                {
                    "flag": "--visual",
                    "must": [{"verb": "must", "kind": "contains", "payload": "visual"}],
                    "may": [],
                    "must_not": [],
                }
            ],
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0, stdout="text"),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert report.rules == ()
        assert report.outcome == "success"


class TestPreImplBucket:
    """H2: the spec-check `--pre-impl` verify bucket must actually evaluate."""

    def test_pre_impl_branch_evaluates_must_and_must_not(self, tmp_path: Path) -> None:
        rules = rules_of(
            when=[
                {
                    "flag": "--pre-impl",
                    "must": [
                        {
                            "verb": "must",
                            "kind": "contains",
                            "payload": "Specification Analysis Report",
                        }
                    ],
                    "may": [],
                    "must_not": [{"verb": "must_not", "kind": "contains", "payload": "checks/"}],
                }
            ],
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(
                exit_code=0,
                flags=["--pre-impl"],
                stdout="## Specification Analysis Report\n| ID | Severity |",
            ),
            active_flags=["--pre-impl"],
            feature=None,
            project_root=tmp_path,
        )
        # Both branch rules (must + must_not) are evaluated and pass.
        assert len(report.rules) == 2
        assert all(r.status == "PASS" for r in report.rules)

    def test_pre_impl_branch_inert_without_flag(self, tmp_path: Path) -> None:
        rules = rules_of(
            when=[
                {
                    "flag": "--pre-impl",
                    "must": [
                        {
                            "verb": "must",
                            "kind": "contains",
                            "payload": "Specification Analysis Report",
                        }
                    ],
                    "may": [],
                    "must_not": [],
                }
            ],
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0, stdout="something else"),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert report.rules == ()


class TestReplaceBaseBranch:
    """C14: a `--pre-impl` when-branch with replace_base drops base rules and the
    exit-code→error classification, so a legitimate blocking analysis (exit 1) is
    NOT misread as a verifier error."""

    def test_pre_impl_exit1_with_replace_base_is_not_error(self, tmp_path: Path) -> None:
        rules = rules_of(
            must=[
                {"verb": "must", "kind": "exit_code", "payload": 0},
                {"verb": "must", "kind": "contains", "payload": "gap report"},
            ],
            when=[
                {
                    "flag": "--pre-impl",
                    "replace_base": True,
                    "must": [
                        {
                            "verb": "must",
                            "kind": "contains",
                            "payload": "Specification Analysis Report",
                        }
                    ],
                    "may": [],
                    "must_not": [],
                }
            ],
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(
                exit_code=1,
                flags=["--pre-impl"],
                stdout="## Specification Analysis Report\n| ID | Severity |",
            ),
            active_flags=["--pre-impl"],
            feature=None,
            project_root=tmp_path,
        )
        # Exit 1 is a legitimate blocking analysis, not a verifier error.
        assert report.outcome != "error"
        assert report.outcome == "success"
        # Base rules (exit_code:0, gap report) are NOT applied in --pre-impl mode.
        assert all(r.kind != "exit_code" for r in report.rules)
        assert len(report.rules) == 1
        assert report.rules[0].kind == "contains" and report.rules[0].status == "PASS"

    def test_without_pre_impl_base_exit_code_still_required(self, tmp_path: Path) -> None:
        rules = rules_of(
            must=[{"verb": "must", "kind": "exit_code", "payload": 0}],
            when=[
                {
                    "flag": "--pre-impl",
                    "replace_base": True,
                    "must": [
                        {
                            "verb": "must",
                            "kind": "contains",
                            "payload": "Specification Analysis Report",
                        }
                    ],
                    "may": [],
                    "must_not": [],
                }
            ],
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=1, stdout="anything"),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        # Base behavior is unchanged when the replace_base branch is inactive.
        assert report.outcome == "error"
        assert any(r.kind == "exit_code" for r in report.rules)


class TestProducesArtifactDirectory:
    """C15: produces_artifact on a directory path must evaluate, never crash."""

    def test_must_produces_artifact_on_existing_directory_passes(self, tmp_path: Path) -> None:
        (tmp_path / "checks").mkdir()
        rules = rules_of(
            must=[{"verb": "must", "kind": "produces_artifact", "payload": "checks"}],
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert [r.status for r in report.rules] == ["PASS"]
        assert report.outcome == "success"

    def test_must_not_produces_artifact_on_existing_directory_does_not_crash(
        self, tmp_path: Path
    ) -> None:
        # Reproduces the --pre-impl crash: a feature with a preexisting checks/ dir.
        (tmp_path / "checks").mkdir()
        rules = rules_of(
            when=[
                {
                    "flag": "--pre-impl",
                    "must_not": [
                        {"verb": "must_not", "kind": "produces_artifact", "payload": "checks"}
                    ],
                    "must": [],
                    "may": [],
                }
            ],
        )
        # Must not raise IsADirectoryError; the rule evaluates (FAIL since dir exists).
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0, flags=["--pre-impl"]),
            active_flags=["--pre-impl"],
            feature=None,
            project_root=tmp_path,
        )
        assert [r.kind for r in report.rules] == ["produces_artifact"]
        assert report.rules[0].status == "FAIL"  # dir exists -> must_not fails, but no crash

    def test_produces_artifact_directory_with_sections_is_explicit_not_crash(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "out").mkdir()
        rules = rules_of(
            must=[
                {
                    "verb": "must",
                    "kind": "produces_artifact",
                    "payload": {"path": "out", "contains_sections": ["Findings"]},
                }
            ],
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        # Sections cannot be checked on a directory -> explicit FAIL, never a crash.
        assert report.rules[0].status == "FAIL"
        assert "directory" in report.rules[0].detail


def test_pre_impl_spec_check_branch_no_crash_with_preexisting_checks_dir(tmp_path: Path) -> None:
    """C15 end-to-end: the real spec-check --pre-impl verify branch evaluates without
    crashing when a feature's checks/ directory already exists, yielding a non-error
    outcome on a legitimate blocking analysis (exit 1)."""
    from validator.goal_contracts import compile_command_goal

    repo_root = Path(__file__).resolve().parents[1]
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    (project_root / ".specs" / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    feature_dir = project_root / ".specs" / "features" / "001-x"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("- FR-001: A.\n", encoding="utf-8")
    # Preexisting checks/ from a prior normal /spec-check run — the crash trigger.
    (feature_dir / "checks").mkdir()

    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=repo_root,
        feature="001-x",
        flags="--pre-impl",
    )

    report = evaluate_rules(
        goal.payload["verify_rules"],
        artifact=make_artifact(
            exit_code=1,
            flags=["--pre-impl"],
            stdout="## Specification Analysis Report\n| ID | Severity |",
        ),
        active_flags=["--pre-impl"],
        feature="001-x",
        project_root=project_root,
    )

    assert report.outcome != "error"
    assert report.outcome == "success"


class TestNoShortCircuit:
    def test_every_rule_evaluated_after_first_failure(self, tmp_path: Path) -> None:
        rules = rules_of(
            must=[
                {"verb": "must", "kind": "contains", "payload": "missing one"},
                {"verb": "must", "kind": "contains", "payload": "present"},
            ],
            must_not=[{"verb": "must_not", "kind": "contains", "payload": "fatal error"}],
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0, stdout="present text"),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        # 039 AC-011: all three rules carry a status, even after the FAIL.
        assert [r.status for r in report.rules] == ["FAIL", "PASS", "PASS"]


class TestSkipSemantics:
    def test_contains_skip_without_transcript(self, tmp_path: Path) -> None:
        rules = rules_of(must=[{"verb": "must", "kind": "contains", "payload": "anything"}])
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert report.rules[0].status == "SKIP"
        assert "transcript" in report.rules[0].detail
        # EC-005: all-contains, no transcript -> may legitimately be success.
        assert report.outcome == "success"

    def test_exit_code_rule_skips_when_exit_code_null(self, tmp_path: Path) -> None:
        rules = rules_of(must=[{"verb": "must", "kind": "exit_code", "payload": 0}])
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=None),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert report.rules[0].status == "SKIP"
        assert report.outcome == "success"

    def test_contains_pass_fail_with_transcript(self, tmp_path: Path) -> None:
        rules = rules_of(
            must=[
                {"verb": "must", "kind": "contains", "payload": "in stdout"},
                {"verb": "must", "kind": "contains", "payload": "in stderr"},
                {"verb": "must", "kind": "contains", "payload": "nowhere"},
            ]
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0, stdout="found in stdout", stderr="found in stderr"),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert [r.status for r in report.rules] == ["PASS", "PASS", "FAIL"]


class TestMayAndMustNot:
    def test_may_rules_never_affect_outcome(self, tmp_path: Path) -> None:
        rules = rules_of(may=[{"verb": "may", "kind": "contains", "payload": "absent"}])
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0, stdout="text"),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert report.rules[0].status == "FAIL"
        assert report.outcome == "success"

    def test_must_not_fails_when_substring_present(self, tmp_path: Path) -> None:
        rules = rules_of(
            must_not=[{"verb": "must_not", "kind": "contains", "payload": "Traceback"}]
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0, stdout="Traceback (most recent call last)"),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert report.rules[0].status == "FAIL"
        assert report.outcome == "drift"


class TestPathRules:
    def test_exists_rule_checks_project_root(self, tmp_path: Path) -> None:
        (tmp_path / "present.md").write_text("x", encoding="utf-8")
        rules = rules_of(
            must=[
                {"verb": "must", "kind": "exists", "payload": "present.md"},
                {"verb": "must", "kind": "exists", "payload": "absent.md"},
            ]
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert [r.status for r in report.rules] == ["PASS", "FAIL"]

    def test_exists_rule_cannot_escape_project_root(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / "outside.md"
        outside.write_text("x", encoding="utf-8")
        rules = rules_of(must=[{"verb": "must", "kind": "exists", "payload": "../outside.md"}])
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert report.rules[0].status == "FAIL"
        assert "escapes project root" in report.rules[0].detail

    def test_produces_artifact_checks_sections(self, tmp_path: Path) -> None:
        doc = tmp_path / "report.md"
        doc.write_text("## Summary\ncontent\n## Details\nmore\n", encoding="utf-8")
        rules = rules_of(
            must=[
                {
                    "verb": "must",
                    "kind": "produces_artifact",
                    "payload": {"path": "report.md", "contains_sections": ["## Summary"]},
                },
                {
                    "verb": "must",
                    "kind": "produces_artifact",
                    "payload": {"path": "report.md", "contains_sections": ["## Missing"]},
                },
            ]
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert [r.status for r in report.rules] == ["PASS", "FAIL"]

    def test_produces_artifact_cannot_escape_project_root(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / "outside-report.md"
        outside.write_text("# Gap Report\n", encoding="utf-8")
        rules = rules_of(
            must=[
                {
                    "verb": "must",
                    "kind": "produces_artifact",
                    "payload": {"path": "../outside-report.md", "contains_sections": ["Gap"]},
                }
            ]
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        assert report.rules[0].status == "FAIL"
        assert "escapes project root" in report.rules[0].detail


class TestPlaceholders:
    def test_date_resolved_from_artifact_timestamp_not_clock(self, tmp_path: Path) -> None:
        (tmp_path / "report-2020-01-02.md").write_text("x", encoding="utf-8")
        rules = rules_of(must=[{"verb": "must", "kind": "exists", "payload": "report-<date>.md"}])
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0, timestamp="2020-01-02T08:00:00+00:00"),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        # 040 EC-006: re-verifying an old artifact later yields identical results.
        assert report.rules[0].status == "PASS"


class TestReceiptVerdictRules:
    def test_conventions_rule_skips_when_gates_absent(self, tmp_path: Path) -> None:
        rules = rules_of(
            must=[
                {
                    "verb": "must",
                    "kind": "receipt_verdict",
                    "payload": {
                        "kind": "conventions",
                        "verdict": "PASS",
                        "required_if_exists": True,
                    },
                }
            ]
        )

        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )

        assert report.rules[0].status == "SKIP"
        assert "conventions gates absent" in report.rules[0].detail
        assert report.outcome == "success"

    def test_conventions_rule_defaults_to_required_if_exists_when_gates_absent(
        self,
        tmp_path: Path,
    ) -> None:
        rules = rules_of(
            must=[
                {
                    "verb": "must",
                    "kind": "receipt_verdict",
                    "payload": {
                        "kind": "conventions",
                        "verdict": "PASS",
                    },
                }
            ]
        )

        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )

        assert report.rules[0].status == "SKIP"
        assert "conventions gates absent" in report.rules[0].detail
        assert report.outcome == "success"

    def test_conventions_rule_fails_when_gates_exist_and_receipt_missing(
        self,
        tmp_path: Path,
    ) -> None:
        (tmp_path / ".specs").mkdir()
        (tmp_path / ".specs" / "conventions-gates.yaml").write_text("schema_version: 1\n")
        rules = rules_of(
            must=[
                {
                    "verb": "must",
                    "kind": "receipt_verdict",
                    "payload": {
                        "kind": "conventions",
                        "verdict": "PASS",
                        "required_if_exists": True,
                    },
                }
            ]
        )

        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )

        assert report.rules[0].status == "FAIL"
        assert "receipt conventions missing" in report.rules[0].detail
        assert report.outcome == "drift"

    def test_conventions_rule_passes_for_pass_receipt(self, tmp_path: Path) -> None:
        (tmp_path / ".specs").mkdir()
        (tmp_path / ".specs" / "conventions-gates.yaml").write_text("schema_version: 1\n")
        artifact = make_artifact(exit_code=0)
        artifact["receipts"] = [
            {
                "kind": "conventions",
                "path": ".specs/conventions/runs/r1/receipt.json",
                "verified": True,
                "verdict": "PASS",
                "error": None,
            }
        ]
        rules = rules_of(
            must=[
                {
                    "verb": "must",
                    "kind": "receipt_verdict",
                    "payload": {
                        "kind": "conventions",
                        "verdict": "PASS",
                        "required_if_exists": True,
                    },
                }
            ]
        )

        report = evaluate_rules(
            rules,
            artifact=artifact,
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )

        assert report.rules[0].status == "PASS"
        assert report.outcome == "success"

    def test_conventions_rule_fails_for_unverified_pass_receipt(self, tmp_path: Path) -> None:
        (tmp_path / ".specs").mkdir()
        (tmp_path / ".specs" / "conventions-gates.yaml").write_text("schema_version: 1\n")
        artifact = make_artifact(exit_code=0)
        artifact["receipts"] = [
            {
                "kind": "conventions",
                "path": ".specs/conventions/runs/r1/receipt.json",
                "verified": False,
                "verdict": "PASS",
                "error": "receipt_hash_mismatch",
            }
        ]
        rules = rules_of(
            must=[
                {
                    "verb": "must",
                    "kind": "receipt_verdict",
                    "payload": {
                        "kind": "conventions",
                        "verdict": "PASS",
                        "required_if_exists": True,
                    },
                }
            ]
        )

        report = evaluate_rules(
            rules,
            artifact=artifact,
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )

        assert report.rules[0].status == "FAIL"
        assert "receipt conventions unverified" in report.rules[0].detail
        assert report.outcome == "drift"

    def test_feature_placeholder_resolved(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / ".specs" / "features" / "004-demo"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text("# spec", encoding="utf-8")
        rules = rules_of(
            must=[
                {
                    "verb": "must",
                    "kind": "exists",
                    "payload": ".specs/features/<feature>/spec.md",
                }
            ]
        )
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature="004-demo",
            project_root=tmp_path,
        )
        assert report.rules[0].status == "PASS"


class TestRendering:
    def test_render_report_table_format(self, tmp_path: Path) -> None:
        rules = rules_of(must=[{"verb": "must", "kind": "exit_code", "payload": 0}])
        report = evaluate_rules(
            rules,
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        text = render_report(
            report,
            command="spec-specify",
            artifact_path=tmp_path / "a.json",
        )
        assert "verb" in text and "kind" in text and "status" in text and "detail" in text
        assert "outcome   success" in text
        assert "exit_code 0" in text

    def test_to_json_envelope(self, tmp_path: Path) -> None:
        report = evaluate_rules(
            rules_of(),
            artifact=make_artifact(exit_code=0),
            active_flags=[],
            feature=None,
            project_root=tmp_path,
        )
        envelope = to_json_envelope(
            report,
            command="spec-specify",
            artifact_path=tmp_path / "a.json",
        )
        assert envelope["outcome"] == "success"
        assert envelope["command"] == "spec-specify"
        assert envelope["rules"] == []
        assert envelope["exit_code"] == 0
