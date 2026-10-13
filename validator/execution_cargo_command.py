"""Parse a `cargo test` command for the trusted Cargo runner (stdlib only).

The runner re-executes the user's exact `cargo test` arguments, so parsing only
classifies them: options the runner owns or cannot observe are refused, test
selection is kept for libtest listing, and output-only options are dropped from
the per-test processes the runner spawns itself.
"""

# @spec FR-001: Recognize cargo test commands
#   — .specs/features/085-cargo-execution-runner/spec.md#fr-001

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Options whose value is the next argument (or after `=`).
_VALUE_OPTIONS = frozenset(
    {
        "-p",
        "--package",
        "--exclude",
        "--bin",
        "--example",
        "--test",
        "--bench",
        "-F",
        "--features",
        "--target",
        "--target-dir",
        "--profile",
        "-j",
        "--jobs",
        "--color",
        "--manifest-path",
        "--lockfile-path",
    }
)
_FLAGS = frozenset(
    {
        "--lib",
        "--bins",
        "--tests",
        "--benches",
        "--examples",
        "--all-targets",
        "--workspace",
        "--all",
        "--no-fail-fast",
        "--release",
        "-r",
        "--all-features",
        "--no-default-features",
        "-q",
        "--quiet",
        "-v",
        "-vv",
        "--verbose",
        "--frozen",
        "--locked",
        "--offline",
        "--ignore-rust-version",
        "--future-incompat-report",
        "--timings",
    }
)
# Refused: they change what Cargo builds or runs behind the runner's back.
_OWNED = {
    "--no-run": "the runner must execute the tests",
    "--doc": "doctests run outside libtest binaries and cannot be traced",
    "--message-format": "the runner owns Cargo's message format",
    "--config": "inline configuration could replace the runner or wrapper",
    "-Z": "unstable Cargo flags are not supported",
    "--unit-graph": "the runner must execute the tests",
    "--build-plan": "the runner must execute the tests",
}
_SHORT_ATTACHED = frozenset({"-p", "-j", "-F"})
_LIBTEST_VALUE_DROPPED = frozenset({"--color", "--format"})
_LIBTEST_FLAGS_DROPPED = frozenset(
    {"--nocapture", "--no-capture", "--show-output", "-q", "--quiet", "--test"}
)


@dataclass(frozen=True)
class LibtestSelection:
    """Libtest arguments that decide which tests run, plus the requested parallelism."""

    filters: tuple[str, ...] = ()
    skips: tuple[str, ...] = ()
    exact: bool = False
    ignored: str = ""  # "", "--ignored" or "--include-ignored"
    threads: int | None = None

    def list_args(self) -> list[str]:
        """Libtest arguments reproducing this selection for `--list`."""
        args = [*self.filters]
        for skip in self.skips:
            args += ["--skip", skip]
        if self.exact:
            args.append("--exact")
        if self.ignored:
            args.append(self.ignored)
        return args


@dataclass(frozen=True)
class CargoTestCommand:
    """A classified `cargo test` invocation."""

    program: str
    toolchain: str | None
    cargo_args: tuple[str, ...]
    libtest: LibtestSelection
    targets: tuple[str, ...] = field(default_factory=tuple)

    def build_argv(self) -> list[str]:
        """The same selection compiled without running, with JSON artifact messages."""
        prefix = [self.program, *([self.toolchain] if self.toolchain else []), "test"]
        return [*prefix, *self.cargo_args, "--no-run", "--message-format=json-render-diagnostics"]


def is_cargo(argv: list[str]) -> bool:
    """True when argv invokes Cargo's `test` subcommand."""
    if not argv or os.path.basename(argv[0]) not in {"cargo", "cargo.exe"}:
        return False
    rest = argv[1:]
    if rest and rest[0].startswith("+"):
        rest = rest[1:]
    return bool(rest) and rest[0] == "test"


def parse_cargo_test(argv: list[str]) -> CargoTestCommand:
    """Classify a `cargo [+toolchain] test ...` argv.

    Raises:
        ValueError: The command is not `cargo test`, or uses an option the runner
            owns or cannot faithfully observe.
    """
    if not is_cargo(argv):
        raise ValueError("Not a cargo test command")
    toolchain = argv[1] if argv[1].startswith("+") else None
    rest = argv[2:] if toolchain is None else argv[3:]
    split = rest.index("--") if "--" in rest else len(rest)
    cargo_args, libtest_args = rest[:split], rest[split + 1 :]
    testname, targets = _cargo_options(cargo_args)
    libtest = parse_libtest(([testname] if testname else []) + libtest_args)
    return CargoTestCommand(argv[0], toolchain, tuple(cargo_args), libtest, tuple(targets))


def _cargo_options(args: list[str]) -> tuple[str | None, list[str]]:
    testname: str | None = None
    targets: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        name, has_value, value = arg.partition("=")
        owned = "-Z" if name.startswith("-Z") else name
        if owned in _OWNED:
            raise ValueError(f"Unsupported cargo test option {owned}: {_OWNED[owned]}")
        if name[:2] in _SHORT_ATTACHED and len(name) > 2 and not has_value:
            name, has_value, value = name[:2], "=", name[2:]
        if name in _VALUE_OPTIONS:
            if not has_value:
                index += 1
                if index >= len(args):
                    raise ValueError(f"Missing value for cargo test option {name}")
                value = args[index]
            if name == "--target":
                targets.append(value)
        elif arg not in _FLAGS and not arg.startswith("--timings="):
            if arg.startswith("-"):
                raise ValueError(f"Unsupported cargo test option for the trusted runner: {arg}")
            if testname is not None:
                raise ValueError("cargo test accepts a single TESTNAME filter")
            testname = arg
        index += 1
    return testname, targets


def parse_libtest(args: list[str]) -> LibtestSelection:
    """Classify libtest harness arguments.

    Raises:
        ValueError: An option would change execution in a way the runner cannot trace.
    """
    filters: list[str] = []
    skips: list[str] = []
    exact, ignored, threads = False, "", None
    index = 0
    while index < len(args):
        arg = args[index]
        name, has_value, value = arg.partition("=")
        takes_value = name in {"--skip", "--test-threads"} | _LIBTEST_VALUE_DROPPED
        if takes_value and not has_value:
            index += 1
            if index >= len(args):
                raise ValueError(f"Missing value for libtest option {name}")
            value = args[index]
        if name == "--skip":
            skips.append(value)
        elif name == "--test-threads":
            threads = _threads(value)
        elif name == "--format" and value not in {"pretty", "terse"}:
            raise ValueError(f"Unsupported libtest format: {value}")
        elif name in {"--ignored", "--include-ignored"}:
            if ignored and ignored != name:
                raise ValueError("--ignored and --include-ignored are exclusive")
            ignored = name
        elif name == "--exact":
            exact = True
        elif not arg.startswith("-"):
            filters.append(arg)
        elif name not in _LIBTEST_FLAGS_DROPPED and name not in _LIBTEST_VALUE_DROPPED:
            raise ValueError(f"Unsupported libtest option for the trusted runner: {arg}")
        index += 1
    return LibtestSelection(tuple(filters), tuple(skips), exact, ignored, threads)


def _threads(value: str) -> int:
    if not value.isdigit() or int(value) < 1:
        raise ValueError(f"Invalid --test-threads value: {value}")
    return int(value)


def runner_variable(triple: str) -> str:
    """Cargo's environment variable naming the runner of one target triple."""
    return "CARGO_TARGET_" + triple.upper().replace("-", "_").replace(".", "_") + "_RUNNER"
