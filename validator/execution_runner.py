"""Resolve trusted local pytest transport and inject actual assertion capture."""

from __future__ import annotations

import importlib.util
import shutil
import sys
import sysconfig
from pathlib import Path

from .execution_scope import digest


def _pytest_args(argv: list[str]) -> list[str] | None:
    if not argv:
        return None
    executable = shutil.which(argv[0])
    if executable is None:
        return None
    resolved = Path(executable).resolve()
    if resolved == Path(sys.executable).resolve() and argv[1:3] == ["-m", "pytest"]:
        return argv[3:]
    # Only the installed distribution's entry point qualifies. Similar names
    # and arbitrary wrappers still run but cannot certify their own XML.
    entry = Path(sysconfig.get_path("scripts")) / "pytest"
    if entry.exists() and resolved == entry.resolve():
        return argv[1:]
    return None


def runner_provenance() -> dict[str, str]:
    """Bind the actual interpreter, pytest distribution and trace plugin bytes."""
    spec = importlib.util.find_spec("pytest")
    if spec is None or not spec.origin:
        raise ValueError("Trusted pytest distribution unavailable")
    pytest_file = Path(spec.origin).resolve()
    installed_roots = {Path(sysconfig.get_path(name)).resolve() for name in ("purelib", "platlib")}
    if not any(pytest_file.is_relative_to(root) for root in installed_roots):
        raise ValueError("pytest must resolve to the installed interpreter distribution")
    plugin = Path(__file__).with_name("execution_pytest.py").resolve()
    return {
        "interpreter": str(Path(sys.executable).resolve()),
        "pytest_path": str(pytest_file),
        "pytest_sha256": digest(pytest_file.read_bytes()),
        "plugin_path": str(plugin),
        "plugin_sha256": digest(plugin.read_bytes()),
    }


def prepare_runner(argv: list[str], adapter: str, report: Path) -> tuple[list[str], dict[str, str]]:
    """Use explicit trusted import paths while preserving ordinary pytest arguments."""
    args = _pytest_args(argv)
    if args is None or adapter not in {"junit", "pytest-json"}:
        return argv, {}
    provenance = runner_provenance()
    options = ("--junitxml", "--junit-xml", "--json-report-file")
    if any(arg.startswith(options) for arg in args):
        raise ValueError("Runner owns test report location; remove the fixed report option")
    report_args = (
        [f"--junitxml={report}"]
        if adapter == "junit"
        else ["--json-report", f"--json-report-file={report}"]
    )
    # Import pytest before adding the candidate cwd, avoiding pytest.py shadowing.
    # The plugin is loaded by its bound absolute source, outside candidate control.
    bootstrap = (
        "import sys, importlib.util; "
        f"sys.path.insert(0, {str(Path(provenance['pytest_path']).parent.parent)!r}); "
        "import pytest; "
        "spec = importlib.util.spec_from_file_location('livespec_execution_trace', "
        f"{provenance['plugin_path']!r}); "
        "plugin = importlib.util.module_from_spec(spec); spec.loader.exec_module(plugin); "
        "raise SystemExit(pytest.main(sys.argv[1:], plugins=[plugin]))"
    )
    return [
        sys.executable,
        "-c",
        bootstrap,
        *args,
        *report_args,
        "-o",
        "enable_assertion_pass_hook=true",
    ], provenance
