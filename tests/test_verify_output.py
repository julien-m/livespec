"""Tests for validator/verify_output.py.

# @spec FR-007, FR-010, AC-009, AC-011 — .specs/features/039-command-expectations-and-verify-output/spec.md
"""

from __future__ import annotations

from pathlib import Path

from validator.expectations import (
    ExpectationsFile,
    Rule,
    VerifyBlock,
    WhenBranch,
)
from validator.run_artifact import FsChange, GitState, RunArtifact
from validator.verify_output import (
    activate_when_branches,
    evaluate,
    render_human,
    render_json,
)


def _expectations(
    must=None,
    may=None,
    must_not=None,
    when=None,
    command="demo",
) -> ExpectationsFile:
    return ExpectationsFile(
        command=command,
        contract_version="1.0",
        last_reviewed="2026-05-12",
        prose_sections={},
        verify=VerifyBlock(
            must=list(must or []),
            may=list(may or []),
            must_not=list(must_not or []),
            when=list(when or []),
        ),
        source_path=Path("commands/demo.expectations.md"),
    )


def _artifact(
    stdout="hello world",
    stderr="",
    exit_code=0,
    flags=None,
    timestamp="2026-05-12T10:00:00Z",
    cwd="/tmp",
) -> RunArtifact:
    return RunArtifact(
        command="demo",
        timestamp=timestamp,
        flags=list(flags or []),
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration_ms=10,
        cwd=cwd,
        git_state_before=GitState(),
        git_state_after=GitState(),
        fs_observed=[FsChange(path="x", change="create")],
    )


# ---------- happy / drift / error ----------


def test_happy_path_all_must_pass_success():
    exp = _expectations(
        must=[
            Rule("must", "contains", "hello"),
            Rule("must", "exit_code", 0),
        ],
        must_not=[Rule("must_not", "contains", "Traceback")],
    )
    art = _artifact()
    report = evaluate(exp, art)
    assert report.outcome == "success"
    assert report.exit_code == 0
    assert all(r.status == "PASS" for r in report.results)


def test_drift_when_must_fails_but_command_exited_0():
    exp = _expectations(must=[Rule("must", "contains", "missing-marker")])
    art = _artifact()
    report = evaluate(exp, art)
    assert report.outcome == "drift"
    assert report.exit_code == 1


def test_error_when_artifact_exit_code_nonzero():
    exp = _expectations(must=[Rule("must", "contains", "hello")])
    art = _artifact(exit_code=2)
    report = evaluate(exp, art)
    assert report.outcome == "error"
    assert report.exit_code == 1


# ---------- when: branches ----------


def test_when_branch_activates_only_when_flag_present():
    branch = WhenBranch(
        flag="--visual",
        must=[Rule("must", "contains", "Visual baselines updated")],
    )
    exp = _expectations(
        must=[Rule("must", "contains", "hello")],
        when=[branch],
    )
    # Flag absent: branch inactive => only base rule evaluated, PASS.
    art = _artifact(flags=[])
    rep = evaluate(exp, art)
    assert rep.outcome == "success"
    assert len(rep.results) == 1  # only the base rule

    # Flag present: branch active, marker missing => drift.
    art2 = _artifact(flags=["--visual"])
    rep2 = evaluate(exp, art2)
    assert rep2.outcome == "drift"
    # Both base + branch rules evaluated.
    assert len(rep2.results) == 2


def test_when_branch_multiple_flags_resolution_order():
    """AC-009: multiple active when: branches accumulate (logical AND with base)."""
    b1 = WhenBranch(flag="--visual", must=[Rule("must", "contains", "v-marker")])
    b2 = WhenBranch(flag="--strict", must=[Rule("must", "contains", "s-marker")])
    exp = _expectations(
        must=[Rule("must", "contains", "base-marker")],
        when=[b1, b2],
    )
    art = _artifact(
        stdout="base-marker v-marker s-marker",
        flags=["--visual", "--strict"],
    )
    rep = evaluate(exp, art)
    assert rep.outcome == "success"
    # Both branches activated alongside base rule.
    assert len(rep.results) == 3


def test_when_branch_irrelevant_flag_no_error():
    """EC-010: when: branch for unknown flag is silently ignored."""
    exp = _expectations(when=[WhenBranch(flag="--never-used")])
    art = _artifact()
    rep = evaluate(exp, art)
    assert rep.outcome == "success"


def test_scenario_flags_activate_branch():
    branch = WhenBranch(flag="--json", must=[Rule("must", "contains", "{")])
    exp = _expectations(when=[branch])
    art = _artifact(stdout="{}")
    rep = evaluate(exp, art, scenario_flags=["--json"])
    assert rep.outcome == "success"


# ---------- placeholders ----------


def test_placeholder_feature_resolves_from_arg():
    exp = _expectations(
        must=[Rule("must", "exists", "<feature>/spec.md")],
    )
    art = _artifact()
    rep = evaluate(exp, art, feature="001-foo")
    # No file exists -> FAIL. We just need to confirm the rule got the
    # resolved path in its detail string.
    detail = rep.results[0].detail
    assert "001-foo/spec.md" in detail


def test_placeholder_date_uses_artifact_timestamp_not_today():
    """AC-010 / EC-006: <date> resolves from artifact timestamp."""
    exp = _expectations(must=[Rule("must", "exists", "checks/<date>-x.md")])
    art = _artifact(timestamp="2025-12-25T00:00:00Z")
    rep = evaluate(exp, art)
    assert "2025-12-25" in rep.results[0].detail


# ---------- rule independence (no short-circuit) — AC-011 ----------


def test_must_not_rules_are_independent_of_must_rules_no_short_circuit():
    """AC-011: must / must_not are independent buckets. NO short-circuit.

    With overlapping substrings (must: "error", must_not: "fatal error"),
    both rules evaluate against the raw output. Failing one does not skip
    the other. Both rule results appear; never SKIPPED.
    """
    exp = _expectations(
        must=[Rule("must", "contains", "error")],
        must_not=[Rule("must_not", "contains", "fatal error")],
    )
    # Output contains "fatal error" — `must` rule passes (substring "error"
    # IS present), `must_not` rule fails (the forbidden "fatal error" IS
    # present). Both must be evaluated independently.
    art = _artifact(stdout="something fatal error happened")
    rep = evaluate(exp, art)
    statuses = {r.rule.verb: r.status for r in rep.results}
    assert statuses["must"] == "PASS"
    assert statuses["must_not"] == "FAIL"
    assert all(r.status != "SKIPPED" for r in rep.results)
    # Outcome: drift (must_not fail with exit_code 0).
    assert rep.outcome == "drift"


def test_must_not_evaluated_even_with_no_must_rules():
    """Group independence: must_not works even when must is empty."""
    exp = _expectations(must_not=[Rule("must_not", "contains", "Traceback")])
    art = _artifact(stdout="Traceback (oh no)")
    rep = evaluate(exp, art)
    assert len(rep.results) == 1
    assert rep.results[0].status == "FAIL"


# ---------- rule kinds ----------


def test_exists_rule_against_cwd(tmp_path):
    target = tmp_path / "spec.md"
    target.write_text("hi", encoding="utf-8")
    exp = _expectations(must=[Rule("must", "exists", "spec.md")])
    art = _artifact(cwd=str(tmp_path))
    rep = evaluate(exp, art)
    assert rep.outcome == "success"


def test_produces_artifact_with_sections(tmp_path):
    art_file = tmp_path / "report.md"
    art_file.write_text("# Header\n## Findings\nbody", encoding="utf-8")
    exp = _expectations(
        must=[
            Rule(
                "must",
                "produces_artifact",
                {"path": "report.md", "contains_sections": ["Findings"]},
            )
        ]
    )
    art = _artifact(cwd=str(tmp_path))
    rep = evaluate(exp, art)
    assert rep.outcome == "success"

    # Missing section -> FAIL.
    art_file.write_text("# Header\nbody", encoding="utf-8")
    rep2 = evaluate(exp, art)
    assert rep2.outcome == "drift"


# ---------- rendering ----------


def test_render_human_contains_outcome_line():
    exp = _expectations(must=[Rule("must", "contains", "hello")])
    art = _artifact()
    rep = evaluate(exp, art)
    out = render_human(rep)
    assert "outcome" in out
    assert "success" in out


def test_render_json_payload():
    exp = _expectations(must=[Rule("must", "contains", "hello")])
    art = _artifact()
    rep = evaluate(exp, art)
    data = render_json(rep)
    assert data["outcome"] == "success"
    assert data["exit_code"] == 0
    assert isinstance(data["results"], list)


def test_activate_when_branches_accumulates():
    b1 = WhenBranch(flag="--a", must=[Rule("must", "contains", "A")])
    b2 = WhenBranch(flag="--b", must=[Rule("must", "contains", "B")])
    block = VerifyBlock(must=[], when=[b1, b2])
    active = activate_when_branches(block, ["--a", "--b"])
    assert len(active.must) == 2
    assert {"--a", "--b"} == set(active.activated_flags)
