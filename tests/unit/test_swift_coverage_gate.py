"""Unit tests for the swift-coverage-gate.sh escape-hatch script."""

# @spec FR-006: Unit tests for swift-coverage-gate.sh
# — .specs/features/019-driver-swift/spec.md#fr-006

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "livespec"
    / "drivers"
    / "scripts"
    / "swift-coverage-gate.sh"
)


def _make_lcov(lines_total: int, lines_hit: int) -> str:
    """Build a minimal lcov payload with the requested DA: line counts."""
    lines: list[str] = ["TN:", "SF:Sources/Foo.swift"]
    for line_no in range(1, lines_total + 1):
        count = "1" if line_no <= lines_hit else "0"
        lines.append(f"DA:{line_no},{count}")
    lines.append("end_of_record")
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
        Completed subprocess result with stdout and stderr captured as text.
    """
    env = dict(os.environ)
    if env_overrides:
        env.update(env_overrides)
    # Run the shipped bash entrypoint exactly as the driver does so the test
    # covers argv, cwd-based project detection, and exit-code semantics.
    return subprocess.run(
        ["bash", str(_SCRIPT_PATH), *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_script_exists_and_executable() -> None:
    """The shipped script is on disk and executable."""
    assert _SCRIPT_PATH.is_file()
    assert os.access(_SCRIPT_PATH, os.X_OK)


def test_gate_passes_when_above_threshold() -> None:
    """Coverage above the threshold yields exit 0 and a PASS message."""
    # @spec AC-003 — .specs/features/019-driver-swift/spec.md#ac-003
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "Package.swift").write_text("// swift", encoding="utf-8")
        lcov_path = project_root / "lcov.info"
        lcov_path.write_text(_make_lcov(lines_total=100, lines_hit=82), encoding="utf-8")

        result = _run_gate(
            project_root,
            str(lcov_path),
            "75",
            env_overrides={"LIVESPEC_GATE_LCOV": str(lcov_path)},
        )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    assert "82%" in result.stdout


def test_gate_fails_when_below_threshold() -> None:
    """Coverage below the threshold yields exit 1 with a failure message."""
    # @spec AC-003
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "Package.swift").write_text("// swift", encoding="utf-8")
        lcov_path = project_root / "lcov.info"
        lcov_path.write_text(_make_lcov(lines_total=100, lines_hit=68), encoding="utf-8")

        result = _run_gate(
            project_root,
            str(lcov_path),
            "75",
            env_overrides={"LIVESPEC_GATE_LCOV": str(lcov_path)},
        )

    assert result.returncode == 1
    assert "Coverage gate failed" in result.stdout
    assert "68%" in result.stdout
    assert "75%" in result.stdout


def test_gate_default_threshold_is_75() -> None:
    """Omitting the threshold argument uses the documented default of 75."""
    # @spec AC-003
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "Package.swift").write_text("// swift", encoding="utf-8")
        lcov_path = project_root / "lcov.info"
        lcov_path.write_text(_make_lcov(lines_total=100, lines_hit=74), encoding="utf-8")

        result = _run_gate(
            project_root,
            str(lcov_path),
            env_overrides={"LIVESPEC_GATE_LCOV": str(lcov_path)},
        )

    assert result.returncode == 1
    assert "74%" in result.stdout
    assert "75%" in result.stdout


def test_gate_xcode_only_project_skips_with_hint() -> None:
    """When only a .xcodeproj exists the gate exits 0 with a redirect hint."""
    # @spec AC-004
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "MyApp.xcodeproj").mkdir()

        result = _run_gate(project_root, "lcov.info", "75")

    assert result.returncode == 0
    assert "Xcode project detected" in result.stdout


def test_gate_no_swift_project_fails() -> None:
    """Neither Package.swift nor .xcodeproj -> exit 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _run_gate(Path(tmpdir), "lcov.info", "75")

    assert result.returncode == 1
    assert "no Package.swift" in result.stdout


def test_gate_empty_lcov_reports_missing_data() -> None:
    """An lcov file with no DA: entries surfaces the crash hint."""
    # @spec EC-003 — .specs/features/019-driver-swift/spec.md#ec-003
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "Package.swift").write_text("// swift", encoding="utf-8")
        lcov_path = project_root / "lcov.info"
        lcov_path.write_text("TN:\nSF:Sources/Foo.swift\nend_of_record\n", encoding="utf-8")

        result = _run_gate(
            project_root,
            str(lcov_path),
            "75",
            env_overrides={"LIVESPEC_GATE_LCOV": str(lcov_path)},
        )

    assert result.returncode == 1
    assert "Coverage data not generated" in result.stdout


def test_gate_missing_lcov_file_reports_missing_data() -> None:
    """When the lcov path passed via env does not exist, exit 1 with a clear message."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "Package.swift").write_text("// swift", encoding="utf-8")
        missing = str(project_root / "missing.lcov")

        result = _run_gate(
            project_root,
            "lcov.info",
            "75",
            env_overrides={"LIVESPEC_GATE_LCOV": missing},
        )

    assert result.returncode == 1
    assert "Coverage data not generated" in result.stdout


def test_bash_available_for_test_environment() -> None:
    """Sanity check that the test environment has bash on PATH."""
    assert shutil.which("bash") is not None
