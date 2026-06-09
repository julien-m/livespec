# LiveSpec traceability anchors
# @spec(FR-005)

"""Unit tests for the go-coverage-gate.sh escape-hatch script."""

# @spec FR-005: Unit tests for go-coverage-gate.sh
# — .specs/features/020-driver-go/spec.md#fr-005

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "livespec" / "drivers" / "scripts" / "go-coverage-gate.sh"
)


def _make_coverprofile(stmts_total: int, stmts_hit: int) -> str:
    """Build a minimal Go coverprofile with the requested statement counts.

    Each line is `<file>:<from>.<col>,<to>.<col> <num_stmts> <count>` per the
    Go coverprofile format. We emit one statement per logical line and place
    hit lines first so callers can dial the percentage precisely.
    """
    lines: list[str] = ["mode: set"]
    file_path = "github.com/example/myapp/foo.go"
    for line_no in range(1, stmts_total + 1):
        count = "1" if line_no <= stmts_hit else "0"
        lines.append(f"{file_path}:{line_no}.0,{line_no}.10 1 {count}")
    return "\n".join(lines) + "\n"


def _run_gate(
    cwd: Path,
    *args: str,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke the gate script with ``args`` from ``cwd``.

    Args:
        cwd: Working directory used for project detection.
        args: Extra positional arguments to forward to the script.
        env_overrides: Optional environment variable overrides.

    Returns:
        Completed subprocess result with stdout + stderr captured as text.
    """
    env = dict(os.environ)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(_SCRIPT_PATH), *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _seed_go_mod(project_root: Path) -> None:
    """Create a minimal ``go.mod`` so the gate's project check passes."""
    (project_root / "go.mod").write_text("module example.com/test\n\ngo 1.22\n", encoding="utf-8")


def test_script_exists_and_executable() -> None:
    """The shipped gate script is on disk and executable."""
    assert _SCRIPT_PATH.is_file()
    assert os.access(_SCRIPT_PATH, os.X_OK)


def test_gate_passes_when_above_threshold() -> None:
    """Coverage above the threshold yields exit 0 and a PASS message."""
    # @spec AC-002, AC-003 — .specs/features/020-driver-go/spec.md#ac-003
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _seed_go_mod(project_root)
        coverprofile = project_root / "coverage.out"
        coverprofile.write_text(_make_coverprofile(stmts_total=100, stmts_hit=78), encoding="utf-8")
        lcov_path = project_root / "coverage" / "lcov.info"

        result = _run_gate(
            project_root,
            str(coverprofile),
            str(lcov_path),
            "70",
            env_overrides={"LIVESPEC_GATE_COVERPROFILE": str(coverprofile)},
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert "PASS" in result.stdout
        assert "78%" in result.stdout
        assert lcov_path.is_file()
        lcov_text = lcov_path.read_text(encoding="utf-8")
        assert "DA:1,1" in lcov_text
        assert "SF:github.com/example/myapp/foo.go" in lcov_text


def test_gate_fails_when_below_threshold() -> None:
    """Coverage below the threshold yields exit 1 with a failure message."""
    # @spec AC-003
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _seed_go_mod(project_root)
        coverprofile = project_root / "coverage.out"
        coverprofile.write_text(_make_coverprofile(stmts_total=100, stmts_hit=55), encoding="utf-8")
        lcov_path = project_root / "coverage" / "lcov.info"

        result = _run_gate(
            project_root,
            str(coverprofile),
            str(lcov_path),
            "70",
            env_overrides={"LIVESPEC_GATE_COVERPROFILE": str(coverprofile)},
        )

    assert result.returncode == 1
    assert "Coverage gate failed" in result.stdout
    assert "55%" in result.stdout
    assert "70%" in result.stdout


def test_gate_default_threshold_is_70() -> None:
    """Omitting the threshold argument uses the documented default of 70."""
    # @spec AC-003
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _seed_go_mod(project_root)
        coverprofile = project_root / "coverage.out"
        coverprofile.write_text(_make_coverprofile(stmts_total=100, stmts_hit=69), encoding="utf-8")
        lcov_path = project_root / "coverage" / "lcov.info"

        result = _run_gate(
            project_root,
            str(coverprofile),
            str(lcov_path),
            env_overrides={"LIVESPEC_GATE_COVERPROFILE": str(coverprofile)},
        )

    assert result.returncode == 1
    assert "69%" in result.stdout
    assert "70%" in result.stdout


def test_gate_no_go_mod_fails() -> None:
    """No ``go.mod`` -> exit 1 with a clear hint."""
    # @spec AC-001, AC-002
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _run_gate(Path(tmpdir), "coverage.out", "coverage/lcov.info", "70")

    assert result.returncode == 1
    assert "no go.mod" in result.stdout


def test_gate_empty_coverprofile_reports_missing_data() -> None:
    """A coverprofile with only the ``mode:`` header surfaces the no-tests hint."""
    # @spec EC-002 — .specs/features/020-driver-go/spec.md#ec-002
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _seed_go_mod(project_root)
        coverprofile = project_root / "coverage.out"
        coverprofile.write_text("mode: set\n", encoding="utf-8")
        lcov_path = project_root / "coverage" / "lcov.info"

        result = _run_gate(
            project_root,
            str(coverprofile),
            str(lcov_path),
            "70",
            env_overrides={"LIVESPEC_GATE_COVERPROFILE": str(coverprofile)},
        )

    assert result.returncode == 1
    assert "No coverage data" in result.stdout


def test_gate_missing_coverprofile_reports_missing_data() -> None:
    """Missing coverprofile path -> exit 1 with a clear message."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _seed_go_mod(project_root)
        missing = str(project_root / "missing.out")

        result = _run_gate(
            project_root,
            "coverage.out",
            "coverage/lcov.info",
            "70",
            env_overrides={"LIVESPEC_GATE_COVERPROFILE": missing},
        )

    assert result.returncode == 1
    assert "Coverage data not generated" in result.stdout


def test_gate_lcov_groups_lines_per_file() -> None:
    """The lcov output groups DA: lines per SF: block (EC-004 inline conversion)."""
    # @spec EC-004 — .specs/features/020-driver-go/spec.md#ec-004
    coverprofile_text = (
        "mode: set\n"
        "github.com/example/myapp/a.go:1.0,1.10 1 1\n"
        "github.com/example/myapp/a.go:2.0,2.10 1 0\n"
        "github.com/example/myapp/b.go:1.0,1.10 1 1\n"
        # Same starting line on a.go: counts must sum.
        "github.com/example/myapp/a.go:1.5,1.15 1 1\n"
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _seed_go_mod(project_root)
        coverprofile = project_root / "coverage.out"
        coverprofile.write_text(coverprofile_text, encoding="utf-8")
        lcov_path = project_root / "coverage" / "lcov.info"

        result = _run_gate(
            project_root,
            str(coverprofile),
            str(lcov_path),
            "0",  # threshold 0: we only care about the lcov shape here.
            env_overrides={"LIVESPEC_GATE_COVERPROFILE": str(coverprofile)},
        )

        assert result.returncode == 0
        lcov_text = lcov_path.read_text(encoding="utf-8")
    # Two distinct files emitted, each as its own SF: block.
    assert lcov_text.count("SF:github.com/example/myapp/a.go") == 1
    assert lcov_text.count("SF:github.com/example/myapp/b.go") == 1
    # Counts are summed for repeated start-lines on the same file (1 + 1 = 2).
    assert "DA:1,2" in lcov_text
    assert "DA:2,0" in lcov_text


def test_bash_available_for_test_environment() -> None:
    """Sanity check that the test environment has bash on PATH."""
    assert shutil.which("bash") is not None
