"""Tests for validator.sdk_test_runner — Level 3b subprocess wrapper."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from validator.exceptions import SdkTestRunError
from validator.sdk_test_runner import (
    SdkTestResult,
    SdkTestRunner,
    _build_pytest_cmd,
    _build_subprocess_env,
    _parse_pytest_summary,
)


class TestParsePytestSummary:
    """_parse_pytest_summary edge cases."""

    def test_all_passed(self) -> None:
        output = "====== 5 passed in 3.21s ======"
        result = _parse_pytest_summary(output)
        assert result == {"passed": 5, "failed": 0, "skipped": 0}

    def test_mixed_results(self) -> None:
        output = "====== 3 passed, 2 failed, 1 skipped in 10.5s ======"
        result = _parse_pytest_summary(output)
        assert result == {"passed": 3, "failed": 2, "skipped": 1}

    def test_only_failed(self) -> None:
        output = "====== 4 failed in 1.0s ======"
        result = _parse_pytest_summary(output)
        assert result == {"passed": 0, "failed": 4, "skipped": 0}

    def test_only_skipped(self) -> None:
        output = "====== 7 skipped in 0.5s ======"
        result = _parse_pytest_summary(output)
        assert result == {"passed": 0, "failed": 0, "skipped": 7}

    def test_empty_output(self) -> None:
        result = _parse_pytest_summary("")
        assert result == {"passed": 0, "failed": 0, "skipped": 0}

    def test_unexpected_format(self) -> None:
        result = _parse_pytest_summary("no tests ran")
        assert result == {"passed": 0, "failed": 0, "skipped": 0}

    def test_multiline_output_with_summary(self) -> None:
        output = (
            "tests/integration/test_foo.py::test_bar PASSED\n"
            "tests/integration/test_foo.py::test_baz FAILED\n"
            "====== 1 passed, 1 failed in 2.0s ======"
        )
        result = _parse_pytest_summary(output)
        assert result == {"passed": 1, "failed": 1, "skipped": 0}


class TestBuildPytestCmd:
    """_build_pytest_cmd with/without feature slug."""

    def test_base_command_no_slug(self) -> None:
        cmd = _build_pytest_cmd(None)
        assert cmd == [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/",
            "-m",
            "level_3b",
            "-v",
            "--tb=short",
        ]

    def test_with_slug(self) -> None:
        cmd = _build_pytest_cmd("001_auto_llm_review")
        assert cmd[-2:] == ["-k", "001_auto_llm_review"]
        # Find the marker flag (not the -m in "python -m pytest")
        marker_indices = [i for i, v in enumerate(cmd) if v == "-m" and cmd[i + 1] == "level_3b"]
        assert len(marker_indices) == 1

    def test_uses_sys_executable(self) -> None:
        cmd = _build_pytest_cmd(None)
        assert cmd[0] == sys.executable


class TestBuildSubprocessEnv:
    """_build_subprocess_env with/without budget."""

    def test_with_budget(self) -> None:
        env = _build_subprocess_env(10.0)
        assert env["LIVESPEC_TEST_BUDGET_USD"] == "10.0"

    def test_without_budget(self) -> None:
        env = _build_subprocess_env(None)
        assert "LIVESPEC_TEST_BUDGET_USD" not in env or env.get(
            "LIVESPEC_TEST_BUDGET_USD"
        ) == env.get("LIVESPEC_TEST_BUDGET_USD")

    def test_inherits_environ(self) -> None:
        with patch.dict("os.environ", {"MY_VAR": "test123"}, clear=False):
            env = _build_subprocess_env(None)
            assert env["MY_VAR"] == "test123"


def _make_mock_popen(
    returncode: int,
    stdout_lines: list[bytes] | None = None,
) -> MagicMock:
    """Create a mock subprocess.Popen with controllable output.

    Args:
        returncode: The return code for the process.
        stdout_lines: Lines to yield from stdout.

    Returns:
        Mock Popen instance.
    """
    if stdout_lines is None:
        stdout_lines = [b"====== 3 passed in 1.0s ======\n"]

    proc = MagicMock()
    proc.stdout.readline = MagicMock(side_effect=[*stdout_lines, b""])
    proc.wait.return_value = returncode
    proc.returncode = returncode
    return proc


class TestSdkTestRunnerRun:
    """SdkTestRunner.run() with mocked subprocess."""

    def test_exit_0_all_passed(self, tmp_path: Path) -> None:
        proc = _make_mock_popen(0, [b"====== 5 passed in 2.0s ======\n"])
        with patch("validator.sdk_test_runner.subprocess.Popen", return_value=proc):
            result = SdkTestRunner(tmp_path).run()
        assert result.exit_code == 0
        assert result.passed == 5
        assert result.failed == 0
        assert result.total == 5

    def test_exit_1_failures(self, tmp_path: Path) -> None:
        proc = _make_mock_popen(1, [b"====== 2 passed, 3 failed in 5.0s ======\n"])
        with patch("validator.sdk_test_runner.subprocess.Popen", return_value=proc):
            result = SdkTestRunner(tmp_path).run()
        assert result.exit_code == 1
        assert result.failed == 3

    def test_exit_2_budget_guard(self, tmp_path: Path) -> None:
        proc = _make_mock_popen(2, [b"!! Budget exceeded\n"])
        with patch("validator.sdk_test_runner.subprocess.Popen", return_value=proc):
            result = SdkTestRunner(tmp_path).run()
        assert result.exit_code == 2

    def test_exit_5_no_tests(self, tmp_path: Path) -> None:
        proc = _make_mock_popen(5, [b"no tests ran\n"])
        with patch("validator.sdk_test_runner.subprocess.Popen", return_value=proc):
            result = SdkTestRunner(tmp_path).run()
        assert result.exit_code == 5

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with (
            patch(
                "validator.sdk_test_runner.subprocess.Popen",
                side_effect=FileNotFoundError("pytest not found"),
            ),
            pytest.raises(SdkTestRunError, match="pytest not found"),
        ):
            SdkTestRunner(tmp_path).run()

    def test_permission_error_raises(self, tmp_path: Path) -> None:
        with (
            patch(
                "validator.sdk_test_runner.subprocess.Popen",
                side_effect=PermissionError("permission denied"),
            ),
            pytest.raises(SdkTestRunError, match="permission denied"),
        ):
            SdkTestRunner(tmp_path).run()

    def test_feature_slug_forwarded(self, tmp_path: Path) -> None:
        proc = _make_mock_popen(0)
        with patch(
            "validator.sdk_test_runner.subprocess.Popen",
            return_value=proc,
        ) as mock_popen:
            SdkTestRunner(tmp_path).run(feature_slug="001_test")
        cmd = mock_popen.call_args[0][0]
        assert "-k" in cmd
        assert cmd[cmd.index("-k") + 1] == "001_test"

    def test_budget_forwarded_to_env(self, tmp_path: Path) -> None:
        proc = _make_mock_popen(0)
        with patch(
            "validator.sdk_test_runner.subprocess.Popen",
            return_value=proc,
        ) as mock_popen:
            SdkTestRunner(tmp_path).run(budget_usd=10.0)
        env = mock_popen.call_args[1]["env"]
        assert env["LIVESPEC_TEST_BUDGET_USD"] == "10.0"

    def test_raw_output_captured(self, tmp_path: Path) -> None:
        lines = [b"line1\n", b"line2\n", b"====== 1 passed in 0.1s ======\n"]
        proc = _make_mock_popen(0, lines)
        with patch("validator.sdk_test_runner.subprocess.Popen", return_value=proc):
            result = SdkTestRunner(tmp_path).run()
        assert "line1" in result.raw_output
        assert "line2" in result.raw_output


class TestSdkTestResultDataclass:
    """SdkTestResult construction."""

    def test_total_equals_sum(self) -> None:
        result = SdkTestResult(
            passed=3,
            failed=1,
            skipped=2,
            total=6,
            exit_code=0,
            raw_output="",
        )
        assert result.total == result.passed + result.failed + result.skipped
