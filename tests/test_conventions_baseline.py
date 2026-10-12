# @spec AC-005, AC-006, AC-007, AC-008: Repo baseline ratchet tests
#   .specs/features/082-conventions-gate-signal/spec.md#ac-005

"""Repo-scope baseline ratchet tests for feature 082."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from validator.cli import app
from validator.cli_commands import conventions_cmd
from validator.conventions_baseline import (
    BASELINE_RELATIVE_PATH,
    BaselineError,
    load_baseline,
)
from validator.conventions_baseline_apply import apply_baseline
from validator.conventions_diffguard import changed_protected_conventions_paths
from validator.conventions_gate_types import GateResult, GateSeverity, GateVerdict, GateViolation
from validator.conventions_receipt import ConventionsReceiptError, verify_conventions_receipt

runner = CliRunner()
BASELINE = str(BASELINE_RELATIVE_PATH)
LONG_FILE = "".join(f"value_{index} = {index}\n" for index in range(8))
FUNC_RULE = "builtin.max_function_lines"


def _write_project(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    constitution = specs / "constitution.md"
    constitution.write_text("# Constitution\n", encoding="utf-8")
    gates: dict[str, object] = {
        "schema_version": 1,
        "generated_from": {
            "constitution": ".specs/constitution.md",
            "constitution_sha256": sha256(constitution.read_bytes()).hexdigest(),
            "stack": ".specs/stacks/_default.md",
        },
        "commands": {"lint": []},
        "builtin": {
            "max_file_lines": {"target": 4, "limit": 6},
            "max_function_lines": {"target": 1000, "limit": 2000},
            "file_header": {},
            "doc_coverage": {"require_public_api": False},
            "token_scale": {"scale": [2, 4, 8], "properties": []},
            "suppression_directives": {"budget": 1000, "whitelist": []},
            "import_rules": [],
        },
        "coverage": {},
        "exclusions": [".specs/**"],
        "scope": "repo",
    }
    (specs / "conventions-gates.yaml").write_text(yaml.safe_dump(gates), encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "old.py").write_text(LONG_FILE, encoding="utf-8")
    return tmp_path


def _verify(project: Path, *args: str) -> tuple[int, dict[str, object]]:
    result = runner.invoke(app, ["conventions", "verify", "--repo", str(project), "--json", *args])
    return result.exit_code, json.loads(result.stdout)


def _error(
    rule_id: str, path: str, line: int, message: str, rule_ids: tuple[str, ...] = ()
) -> GateViolation:
    return GateViolation(rule_id, path, line, GateSeverity.ERROR, message, "builtin", "", rule_ids)


def _write_baseline_file(project: Path, payload: object) -> None:
    path = project / BASELINE_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _baseline(project: Path, entries: list[dict[str, object]]):
    _write_baseline_file(project, {"schema_version": 1, "scope": "repo", "entries": entries})
    loaded = load_baseline(project)
    assert loaded is not None
    return loaded


def _errors(payload: dict[str, object]) -> list[dict[str, object]]:
    violations = payload["violations"]
    assert isinstance(violations, list)
    return [item for item in violations if item["severity"] == "error"]


def test_write_then_verify_passes_and_reports_debt(tmp_path: Path) -> None:
    project = _write_project(tmp_path)

    code_w, written = _verify(project, "--feature", "repo", "--write-baseline", "--run-id", "w1")
    code, payload = _verify(project, "--feature", "repo", "--run-id", "r1")

    assert (code_w, code) == (0, 0)
    assert written["baseline_write"] == {
        "path": BASELINE,
        "recorded": 1,
        "added": 1,
        "removed": 0,
        "previous": "absent",
    }
    assert payload["verdict"] == "PASS"
    assert _errors(payload) == []
    summary = payload["baseline"]
    assert isinstance(summary, dict)
    assert summary["path"] == BASELINE
    assert summary["sha256"] == sha256((project / BASELINE_RELATIVE_PATH).read_bytes()).hexdigest()
    assert (summary["baselined_count"], summary["new_count"], summary["resolved_count"]) == (
        1,
        0,
        0,
    )
    receipt = verify_conventions_receipt(Path(str(payload["receipt_path"])), project_root=project)
    assert receipt.verdict == "PASS"
    stored = json.loads((project / str(payload["receipt_path"])).read_text(encoding="utf-8"))
    assert stored["baseline"] == summary
    assert [item["path"] for item in stored["baselined_violations"]] == ["src/old.py"]


def test_new_violation_fails_while_debt_stays_separate(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    _verify(project, "--feature", "repo", "--write-baseline", "--run-id", "w1")
    (project / "src" / "new.py").write_text(LONG_FILE, encoding="utf-8")

    code, payload = _verify(project, "--feature", "repo", "--run-id", "r2")

    assert code == 1
    assert payload["verdict"] == "FAIL"
    assert [item["path"] for item in _errors(payload)] == ["src/new.py"]
    debt = payload["baselined_violations"]
    assert isinstance(debt, list)
    assert [item["path"] for item in debt] == ["src/old.py"]


def test_repo_scope_without_feature_applies_baseline_without_receipt(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    _verify(project, "--write-baseline")

    code, payload = _verify(project)

    assert code == 0
    summary = payload["baseline"]
    assert isinstance(summary, dict)
    assert summary["baselined_count"] == 1
    assert "receipt_path" not in payload


def test_absent_baseline_keeps_legacy_verdict(tmp_path: Path) -> None:
    project = _write_project(tmp_path)

    code, payload = _verify(project, "--feature", "repo", "--run-id", "legacy")

    assert code == 1
    assert "baseline" not in payload
    assert [item["path"] for item in _errors(payload)] == ["src/old.py"]


def test_matching_ignores_lines_and_is_bounded_by_count(tmp_path: Path) -> None:
    baseline = _baseline(
        tmp_path,
        [
            {
                "rule_id": FUNC_RULE,
                "path": "a.py",
                "count": 2,
                "messages": ["f has 70 lines > 60", "g has 65 lines > 60"],
                "rule_ids": [],
            }
        ],
    )
    shifted = [
        _error(FUNC_RULE, "a.py", 40, "f has 70 lines > 60"),
        _error(FUNC_RULE, "a.py", 90, "g has 80 lines > 60"),
    ]
    grown = [*shifted, _error(FUNC_RULE, "a.py", 120, "h has 61 lines > 60")]

    kept = apply_baseline(GateResult(GateVerdict.FAIL, shifted, []), baseline)
    extra = apply_baseline(GateResult(GateVerdict.FAIL, grown, []), baseline)

    assert kept.verdict is GateVerdict.PASS
    assert len(kept.baselined_violations) == 2
    assert extra.verdict is GateVerdict.FAIL
    assert [item.message for item in extra.violations] == ["h has 61 lines > 60"]


def test_identical_message_is_matched_before_count(tmp_path: Path) -> None:
    baseline = _baseline(
        tmp_path,
        [
            {
                "rule_id": FUNC_RULE,
                "path": "a.py",
                "count": 1,
                "messages": ["f has 70 lines > 60"],
                "rule_ids": [],
            }
        ],
    )
    current = [
        _error(FUNC_RULE, "a.py", 10, "new has 61 lines > 60"),
        _error(FUNC_RULE, "a.py", 40, "f has 70 lines > 60"),
    ]

    applied = apply_baseline(GateResult(GateVerdict.FAIL, current, []), baseline)

    assert [item.line for item in applied.baselined_violations] == [40]
    assert [item.message for item in applied.violations] == ["new has 61 lines > 60"]


def test_new_family_rule_is_new_and_resolved_is_counted(tmp_path: Path) -> None:
    baseline = _baseline(
        tmp_path,
        [
            {
                "rule_id": "ars.family.go_code",
                "path": "a.go",
                "count": 1,
                "messages": ["m"],
                "rule_ids": ["ars.rule.1"],
            },
            {
                "rule_id": "builtin.max_file_lines",
                "path": "gone.py",
                "count": 2,
                "messages": ["x", "y"],
                "rule_ids": [],
            },
        ],
    )
    current = [_error("ars.family.go_code", "a.go", 3, "m", ("ars.rule.1", "ars.rule.2"))]

    applied = apply_baseline(GateResult(GateVerdict.FAIL, current, []), baseline)

    assert applied.verdict is GateVerdict.FAIL
    assert applied.baseline is not None
    assert (applied.baseline["new_count"], applied.baseline["resolved_count"]) == (1, 3)


def test_warnings_system_and_tool_failures_are_never_baselined(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    tool_failure = GateViolation("linter.ruff", ".", 1, GateSeverity.ERROR, "crash", "linter")
    warning = GateViolation(FUNC_RULE, "a.py", 1, GateSeverity.WARNING, "w", "builtin")
    encoding = GateViolation("file_encoding_error", "b.py", 1, GateSeverity.ERROR, "e", "system")
    result = GateResult(GateVerdict.FAIL, [tool_failure, warning, encoding], [])

    from validator.conventions_baseline import write_baseline

    summary = write_baseline(project, result)
    applied = apply_baseline(result, _loaded(project))

    assert summary.recorded == 0
    assert applied.verdict is GateVerdict.FAIL
    assert applied.baselined_violations == []


def _loaded(project: Path):
    loaded = load_baseline(project)
    assert loaded is not None
    return loaded


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ("{not json", "unreadable"),
        ({"schema_version": 2, "scope": "repo", "entries": []}, "schema_version"),
        ({"schema_version": 1, "scope": "feature", "entries": []}, "scope must be repo"),
        (
            {
                "schema_version": 1,
                "scope": "repo",
                "entries": [
                    {"rule_id": "r", "path": "p", "count": 2, "messages": ["one"], "rule_ids": []}
                ],
            },
            "messages != count",
        ),
    ],
    ids=["malformed", "schema", "scope", "count"],
)
def test_invalid_baseline_blocks_with_path_reason_and_hint(
    tmp_path: Path, payload: object, reason: str
) -> None:
    project = _write_project(tmp_path)
    path = project / BASELINE_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")

    with pytest.raises(BaselineError):
        load_baseline(project)
    code, verified = _verify(project, "--feature", "repo", "--run-id", "bad")

    assert code == 2
    blockers = verified["blockers"]
    assert isinstance(blockers, list)
    blocker = blockers[-1]
    assert blocker["code"] == "baseline_invalid"
    assert BASELINE in blocker["message"]
    assert reason in blocker["message"]
    assert "--write-baseline" in blocker["fix_hint"]


def test_write_replaces_invalid_baseline(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    _write_baseline_file(project, "{not json")
    (project / BASELINE_RELATIVE_PATH).write_text("{not json", encoding="utf-8")

    code, written = _verify(project, "--feature", "repo", "--write-baseline", "--run-id", "fix")

    assert code == 0
    write = written["baseline_write"]
    assert isinstance(write, dict)
    assert (write["previous"], write["added"]) == ("invalid", 1)


def test_write_is_deterministic_and_reports_delta(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    _verify(project, "--feature", "repo", "--write-baseline", "--run-id", "a")
    first = (project / BASELINE_RELATIVE_PATH).read_bytes()
    _verify(project, "--feature", "repo", "--write-baseline", "--run-id", "b")
    same = (project / BASELINE_RELATIVE_PATH).read_bytes()
    (project / "src" / "new.py").write_text(LONG_FILE, encoding="utf-8")
    (project / "src" / "old.py").unlink()

    _code, written = _verify(project, "--feature", "repo", "--write-baseline", "--run-id", "c")

    assert first == same
    assert b"generated_at" not in first
    write = written["baseline_write"]
    assert isinstance(write, dict)
    assert (write["recorded"], write["added"], write["removed"]) == (1, 1, 1)


def test_written_baseline_entries_are_sorted(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    (project / "src" / "b.py").write_text(LONG_FILE, encoding="utf-8")
    (project / "src" / "a.py").write_text(LONG_FILE, encoding="utf-8")

    _verify(project, "--feature", "repo", "--write-baseline", "--run-id", "sorted")
    stored = json.loads((project / BASELINE_RELATIVE_PATH).read_text(encoding="utf-8"))

    assert [entry["path"] for entry in stored["entries"]] == ["src/a.py", "src/b.py", "src/old.py"]


def test_write_refused_when_blocked_or_with_feature_slug(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    (project / ".specs" / "constitution.md").write_text("# Changed\n", encoding="utf-8")

    blocked_code, blocked = _verify(
        project, "--feature", "repo", "--write-baseline", "--run-id", "x"
    )
    slug_code, slug = _verify(project, "--feature", "001-demo", "--write-baseline")

    assert blocked_code == 2
    assert blocked["verdict"] == "BLOCKED"
    assert slug_code == 2
    assert slug["receipt_path"] is None
    assert not (project / BASELINE_RELATIVE_PATH).exists()


def test_feature_scope_ignores_baseline(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    _verify(project, "--feature", "repo", "--write-baseline", "--run-id", "w1")
    feature_dir = project / ".specs" / "features" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "implementation.md").write_text(
        "| FR-001 | [`src/old.py`](../../../src/old.py) | x | Implemented | 2026-10-10 |\n",
        encoding="utf-8",
    )

    code, payload = _verify(project, "--feature", "001-demo", "--run-id", "f1")

    assert code == 1
    assert payload["verdict"] == "FAIL"
    assert "baseline" not in payload
    stored = json.loads((project / str(payload["receipt_path"])).read_text(encoding="utf-8"))
    assert "baseline" not in stored


@pytest.mark.parametrize("mutation", ["edit", "delete"])
def test_receipt_rejects_changed_or_deleted_baseline(tmp_path: Path, mutation: str) -> None:
    project = _write_project(tmp_path)
    _verify(project, "--feature", "repo", "--write-baseline", "--run-id", "w1")
    _code, payload = _verify(project, "--feature", "repo", "--run-id", "r1")
    path = project / BASELINE_RELATIVE_PATH
    if mutation == "edit":
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    else:
        path.unlink()

    with pytest.raises(ConventionsReceiptError) as rejected:
        verify_conventions_receipt(Path(str(payload["receipt_path"])), project_root=project)

    assert str(rejected.value) == "baseline_sha256_mismatch"


def test_receipt_without_baseline_still_verifies(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    (project / "src" / "old.py").write_text("value = 1\n", encoding="utf-8")
    _code, payload = _verify(project, "--feature", "repo", "--run-id", "plain")
    _write_baseline_file(project, {"schema_version": 1, "scope": "repo", "entries": []})

    receipt = verify_conventions_receipt(Path(str(payload["receipt_path"])), project_root=project)

    assert receipt.verdict == "PASS"


def test_baseline_path_is_protected_by_diff_guard(tmp_path: Path) -> None:
    project = _write_project(tmp_path)

    protected = changed_protected_conventions_paths(project, changed_paths=[BASELINE, "src/old.py"])

    assert protected == [BASELINE]


@pytest.mark.parametrize("slug", [None, "repo"])
def test_supervisor_repo_run_applies_baseline(tmp_path: Path, slug: str | None) -> None:
    project = _write_project(tmp_path)
    _verify(project, "--feature", "repo", "--write-baseline", "--run-id", "w1")

    result = conventions_cmd._run_supervisor_verify(project, slug)

    assert result.verdict is GateVerdict.PASS
    assert result.baseline is not None
    assert result.baseline["baselined_count"] == 1
