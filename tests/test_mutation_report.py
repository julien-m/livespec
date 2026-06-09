"""Unit tests for the on-demand mutation report module (feature 025)."""

# @spec FR-005: Unit tests for write_mutation_report
# — .specs/features/025-mutation-testing-on-demand/spec.md#fr-005

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from validator.drivers import (
    CapabilityResult,
    DriverCapability,
    DriverManifest,
    MutationResult,
    SurvivorRef,
    alternative_for,
    normalise_cargo_mutants,
    normalise_muter,
    normalise_mutmut,
    normalise_pitest,
    normalise_stryker,
    render_report_entry,
    run_mutation,
    write_mutation_report,
)

# ---------------------------------------------------------------------------
# Normalisers
# ---------------------------------------------------------------------------


def test_normalise_mutmut_round_trip() -> None:
    """FR-005 — mutmut JSON payloads produce a usable MutationResult."""
    parsed: dict[str, Any] = {
        "killed": 12,
        "survived": 3,
        "timeout": 1,
        "score": 80.0,
        "survivors": [
            {"file": "validator/foo.py", "line": 7, "description": "x>0 → x>=0"},
        ],
    }
    result = normalise_mutmut(parsed, today="2026-05-07")  # type: ignore[arg-type]
    assert result.driver == "python"
    assert result.killed == 12
    assert result.survived == 3
    assert result.timeout == 1
    assert result.kill_rate == pytest.approx(80.0)  # type: ignore[arg-type]
    assert result.date == "2026-05-07"
    assert len(result.survivors) == 1
    assert result.survivors[0].file == "validator/foo.py"
    assert result.survivors[0].line == 7


def test_normalise_stryker_from_metrics_block() -> None:
    """Stryker payload normalisation preserves no-coverage and timeout."""
    parsed: dict[str, Any] = {
        "killed": 30,
        "survived": 10,
        "timeout": 2,
        "no_coverage": 5,
        "kill_rate": 76.19,
    }
    result = normalise_stryker(parsed, today="2026-05-07")  # type: ignore[arg-type]
    assert result.driver == "typescript"
    assert result.killed == 30
    assert result.survived == 10
    assert result.timeout == 2
    assert result.no_coverage == 5
    assert result.kill_rate == pytest.approx(76.19)  # type: ignore[arg-type]


def test_normalise_pitest_counts_errors_as_kills() -> None:
    """pitest memory/run errors are counted as kills (suite reproduced them)."""
    counts = {
        "killed": 50,
        "survived": 5,
        "timed_out": 2,
        "no_coverage": 3,
        "memory_error": 1,
        "run_error": 1,
    }
    result = normalise_pitest(counts, today="2026-05-07")
    assert result.killed == 52  # 50 + 1 + 1
    assert result.survived == 5
    assert result.timeout == 2
    assert result.no_coverage == 3
    # kill_rate = (52 + 2) / (52 + 5 + 2) = 54/59
    assert result.kill_rate == pytest.approx(54 / 59 * 100.0)  # type: ignore[arg-type]


def test_normalise_cargo_mutants_outcomes() -> None:
    """cargo-mutants outcomes are mapped to the canonical fields."""
    counts = {"caught": 40, "missed": 5, "timeout": 1, "unviable": 3}
    result = normalise_cargo_mutants(counts, today="2026-05-07")
    assert result.killed == 40
    assert result.survived == 5
    assert result.timeout == 1
    # unviable mutants are excluded from the denominator.
    assert result.kill_rate == pytest.approx((40 + 1) / 46 * 100.0)  # type: ignore[arg-type]


def test_normalise_muter_extracts_counts_from_stdout() -> None:
    """muter stdout regex parsing produces a usable MutationResult."""
    stdout = "Mutation score: 73.0 (killed 73, survived 27, timed out 0)"
    result = normalise_muter(stdout, today="2026-05-07")
    assert result.killed == 73
    assert result.survived == 27
    assert result.timeout == 0
    assert result.kill_rate == pytest.approx(73.0)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def test_render_report_entry_truncates_to_max_survivors() -> None:
    """EC-002 — survivor lists exceeding 20 entries are truncated."""
    survivors = [SurvivorRef(file=f"src/f{i}.py", line=i) for i in range(1, 31)]
    result = MutationResult(
        date="2026-05-07",
        driver="python",
        kill_rate=10.0,
        killed=1,
        survived=30,
        timeout=0,
        survivors=survivors,
    )
    rendered = render_report_entry(result, max_survivors=20)
    # The first heading, the truncated count, and the "more survivors" note.
    assert rendered.startswith("## 2026-05-07 — python\n")
    assert "showing 20 of 30" in rendered
    assert "10 more survivors" in rendered
    # Only the first 20 survivors appear in the body.
    assert "`src/f20.py:20`" in rendered
    assert "`src/f21.py:21`" not in rendered


def test_render_report_entry_threshold_pass_and_fail() -> None:
    """Threshold gate is rendered as PASS / FAIL when configured."""
    result = MutationResult(
        date="2026-05-07",
        driver="rust",
        kill_rate=85.0,
        killed=85,
        survived=15,
        timeout=0,
        threshold=70.0,
        gate_failed=False,
    )
    assert "Threshold: 70.0 % (PASS)" in render_report_entry(result)

    failing = MutationResult(
        date="2026-05-07",
        driver="rust",
        kill_rate=50.0,
        killed=50,
        survived=50,
        timeout=0,
        threshold=70.0,
        gate_failed=True,
    )
    assert "Threshold: 70.0 % (FAIL)" in render_report_entry(failing)


# ---------------------------------------------------------------------------
# Writer (create + prepend)
# ---------------------------------------------------------------------------


def _make_result(date: str, driver: str = "python") -> MutationResult:
    return MutationResult(
        date=date,
        driver=driver,
        kill_rate=80.0,
        killed=8,
        survived=2,
        timeout=0,
    )


def test_write_mutation_report_creates_file_with_header(tmp_path: Path) -> None:
    """AC-003 — the report file is created with a header and one entry."""
    report = tmp_path / ".specs" / "testing" / "mutation-report.md"
    write_mutation_report(_make_result("2026-05-07"), report_path=report)

    text = report.read_text(encoding="utf-8")
    assert text.startswith("# Mutation Report")
    assert "Auto-generated by /spec-test --mutation" in text
    assert "## 2026-05-07 — python" in text


def test_write_mutation_report_prepends_subsequent_runs(tmp_path: Path) -> None:
    """AC-004 — newer runs are prepended; older entries are preserved."""
    report = tmp_path / ".specs" / "testing" / "mutation-report.md"
    write_mutation_report(_make_result("2026-05-06"), report_path=report)
    write_mutation_report(_make_result("2026-05-07"), report_path=report)

    text = report.read_text(encoding="utf-8")
    idx_new = text.find("## 2026-05-07 — python")
    idx_old = text.find("## 2026-05-06 — python")
    assert idx_new != -1
    assert idx_old != -1
    assert idx_new < idx_old, "newest entry must appear before older ones"
    # Header is preserved exactly once.
    assert text.count("# Mutation Report") == 1


def test_write_mutation_report_creates_parent_directory(tmp_path: Path) -> None:
    """EC-003 — missing .specs/testing/ is created automatically."""
    report = tmp_path / "missing" / "deep" / "mutation-report.md"
    assert not report.parent.exists()
    write_mutation_report(_make_result("2026-05-07"), report_path=report)
    assert report.exists()


# ---------------------------------------------------------------------------
# Orchestration — run_mutation
# ---------------------------------------------------------------------------


def _driver(
    name: str,
    *,
    with_mutation: bool = True,
    threshold: float | None = None,
) -> DriverManifest:
    """Build a minimal driver manifest for tests."""
    mutation = (
        DriverCapability(command="mock-mutation-command", threshold=threshold)
        if with_mutation
        else None
    )
    return DriverManifest(name=name, mutation=mutation)


def test_run_mutation_returns_none_when_capability_absent() -> None:
    """AC-002 — drivers without a mutation block return None."""
    driver = _driver("go", with_mutation=False)
    assert run_mutation(driver, report_path=None) is None


def test_run_mutation_emits_install_hint_on_127(tmp_path: Path) -> None:
    """AC-007 — exit code 127 (command not found) yields an install hint."""
    driver = _driver("python")
    cap_result = CapabilityResult(
        capability_name="mutation",
        exit_code=127,
        stdout="",
        stderr="command not found: mutmut",
    )
    with mock.patch(
        "validator.drivers.mutation_report.run_capability",
        return_value=cap_result,
    ):
        result = run_mutation(driver, report_path=None)
    assert result is not None
    assert "tool not installed" in result.note
    assert result.kill_rate == 0.0


def test_run_mutation_writes_report_when_path_provided(tmp_path: Path) -> None:
    """AC-001/AC-003 — successful runs parse output and append a report entry."""
    driver = _driver("python")
    stdout = json.dumps({"killed": 9, "survived": 1, "timeout": 0})
    cap_result = CapabilityResult(
        capability_name="mutation",
        exit_code=0,
        stdout=stdout,
        stderr="",
    )
    report_path = tmp_path / ".specs" / "testing" / "mutation-report.md"

    # The mutmut parser also calls into a subprocess to extract survivors via
    # `mutmut results`; stub the helper so the test stays hermetic.
    with (
        mock.patch(
            "validator.drivers.mutation_report.run_capability",
            return_value=cap_result,
        ),
        mock.patch(
            "validator.drivers.mutmut_parser.extract_surviving_mutants",
            return_value=[],
        ),
    ):
        result = run_mutation(driver, report_path=report_path)

    assert result is not None
    assert result.killed == 9
    assert result.survived == 1
    assert result.kill_rate == pytest.approx(90.0)  # type: ignore[arg-type]
    assert report_path.exists()
    assert "## " in report_path.read_text(encoding="utf-8")


def test_run_mutation_applies_threshold_gate() -> None:
    """AC-005 — kill rate below threshold flips gate_failed to True."""
    driver = _driver("python", threshold=95.0)
    stdout = json.dumps({"killed": 9, "survived": 1, "timeout": 0})  # 90 %
    cap_result = CapabilityResult(
        capability_name="mutation",
        exit_code=0,
        stdout=stdout,
        stderr="",
    )
    with (
        mock.patch(
            "validator.drivers.mutation_report.run_capability",
            return_value=cap_result,
        ),
        mock.patch(
            "validator.drivers.mutmut_parser.extract_surviving_mutants",
            return_value=[],
        ),
    ):
        result = run_mutation(driver, report_path=None)

    assert result is not None
    assert result.threshold == pytest.approx(95.0)  # type: ignore[arg-type]
    assert result.gate_failed is True


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def test_alternative_for_known_and_unknown() -> None:
    """alternative_for returns the canonical hint per stack."""
    assert "gopter" in alternative_for("go")
    # Unknown driver falls back to the generic hint.
    assert "property-based testing" in alternative_for("haskell")
