"""`cargo test` commands are classified without weakening what the runner observes."""

from __future__ import annotations

import pytest

from validator.execution_cargo_command import (
    LibtestSelection,
    is_cargo,
    parse_cargo_test,
    runner_variable,
)


def test_handy_command_is_recognized_with_its_selection() -> None:
    argv = ["cargo", "test", "--manifest-path", "src-tauri/Cargo.toml"]
    argv += ["--test", "settings_platform"]
    command = parse_cargo_test(argv)
    assert command.cargo_args == tuple(argv[2:])
    assert command.libtest == LibtestSelection()
    assert command.build_argv()[-2:] == ["--no-run", "--message-format=json-render-diagnostics"]


def test_filters_and_libtest_arguments_reproduce_the_selection() -> None:
    argv = [
        "cargo",
        "+stable",
        "test",
        "-p",
        "app",
        "--target=aarch64-apple-darwin",
        "unix::",
        "--",
        "--skip",
        "slow",
        "--exact",
        "--include-ignored",
        "--test-threads=2",
        "--nocapture",
    ]
    command = parse_cargo_test(argv)
    assert command.toolchain == "+stable"
    assert command.targets == ("aarch64-apple-darwin",)
    assert command.libtest.threads == 2
    assert command.libtest.list_args() == [
        "unix::",
        "--skip",
        "slow",
        "--exact",
        "--include-ignored",
    ]
    assert command.build_argv()[:3] == ["cargo", "+stable", "test"]


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["cargo", "test", "--no-run"], "--no-run"),
        (["cargo", "test", "--doc"], "--doc"),
        (["cargo", "test", "--message-format=json"], "--message-format"),
        (["cargo", "test", "--config", "a=1"], "--config"),
        (["cargo", "test", "-Zbuild-std"], "-Z"),
        (["cargo", "test", "--frobnicate"], "Unsupported cargo test option"),
        (["cargo", "test", "a", "b"], "single TESTNAME"),
        (["cargo", "test", "--", "--format", "json"], "Unsupported libtest format"),
        (["cargo", "test", "--", "--bench"], "Unsupported libtest option"),
        (["cargo", "test", "--", "--ignored", "--include-ignored"], "exclusive"),
        (["cargo", "test", "--", "--test-threads", "0"], "Invalid --test-threads"),
    ],
)
def test_options_the_runner_cannot_observe_are_refused(argv: list[str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_cargo_test(argv)


def test_only_cargo_test_is_routed() -> None:
    assert is_cargo(["/usr/local/bin/cargo", "test"])
    assert is_cargo(["cargo", "+nightly", "test"])
    assert not is_cargo(["cargo", "build"])
    assert not is_cargo(["python", "-m", "pytest"])
    assert runner_variable("aarch64-apple-darwin") == "CARGO_TARGET_AARCH64_APPLE_DARWIN_RUNNER"
