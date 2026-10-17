"""Prepare confined direct Node/Vitest invocations with owned observation assets."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .execution_deadline import run_owned
from .execution_vitest_provenance import vitest_provenance


def is_vitest(argv: list[str]) -> bool:
    """Recognize direct Node/Vitest commands, including invalid candidates to reject."""
    return len(argv) > 1 and Path(argv[1]).name in {"vitest.mjs", "vitest.js"}


# @spec FR-004: Confine validated file and name selections without shell interpolation
# — .specs/features/096-node-vitest-execution/spec.md#fr-004
def _selection(
    argv: list[str], project: Path, cwd: Path | None = None
) -> tuple[Path, Path | None, list[str]]:
    if len(argv) < 3 or argv[2] != "run":
        raise ValueError("Vitest observations require direct node <local-vitest.mjs> run")
    cwd = cwd or project
    package = cwd
    config: Path | None = None
    selected: list[str] = []
    index = 3
    while index < len(argv):
        arg = argv[index]
        option, separator, inline = arg.partition("=")
        if option in {"--root", "--config", "-c", "--testNamePattern", "-t"}:
            if not separator:
                index += 1
                if index >= len(argv):
                    raise ValueError(f"Missing Vitest selection value: {option}")
            value = inline if separator else argv[index]
            if not value or "\0" in value:
                raise ValueError("Empty or invalid Vitest selection")
            if option == "--root":
                package = (cwd / value).resolve(strict=True)
            elif option in {"--config", "-c"}:
                config = (cwd / value).resolve(strict=True)
            else:
                selected.extend(["--testNamePattern", value])
        elif arg.startswith("-"):
            raise ValueError(f"Unsupported Vitest option {arg}; use file/name selections only")
        else:
            if "\0" in arg or ".." in Path(arg).parts or Path(arg).is_absolute():
                raise ValueError("Vitest file selections must be confined relative paths")
            selected.append(arg)
        index += 1
    if not package.is_dir() or not package.is_relative_to(project):
        raise ValueError("Vitest root must be confined to the execution project")
    if config and (not config.is_file() or not config.is_relative_to(project)):
        raise ValueError("Vitest configuration must be confined to the execution project")
    if config is None:
        for stem in ("vitest.config", "vite.config"):
            matches = [
                package / f"{stem}.{suffix}" for suffix in ("ts", "mts", "cts", "js", "mjs", "cjs")
            ]
            existing = [path for path in matches if path.is_file()]
            if existing:
                if len(existing) != 1:
                    raise ValueError("Ambiguous Vitest configuration; select --config explicitly")
                config = existing[0].resolve(strict=True)
                if not config.is_relative_to(project):
                    raise ValueError("Vitest configuration symlink escapes the project")
                break
    return package, config, selected


def _validate_vitest_runtime(
    argv: list[str], project: Path, package: Path, env: dict[str, str]
) -> tuple[Path, Path]:
    """Verify the confined local entry and native Node identity within the shared deadline."""
    # Resolve executable paths and relative PATH entries as the actual child would from cwd.
    candidate = str(project / argv[0]) if "/" in argv[0] else argv[0]
    search_path = os.pathsep.join(str(project / entry) for entry in os.get_exec_path(env))
    executable = shutil.which(candidate, path=search_path)
    if executable is None:
        raise ValueError("Node 22 executable is unavailable")
    node = Path(executable).resolve(strict=True)
    cli = (project / argv[1]).resolve(strict=True)
    modules = (package / "node_modules").resolve(strict=True)
    if not modules.is_relative_to(package):
        raise ValueError("Vitest local node_modules cannot escape the selected package")
    expected = (modules / "vitest/vitest.mjs").resolve(strict=True)
    if cli != expected:
        raise ValueError("Vitest entry must be the selected package's local vitest/vitest.mjs")
    # A native executable plus execPath verification excludes script/CLI wrappers.
    with node.open("rb") as stream:
        magic = stream.read(4)
    if magic not in {b"\x7fELF", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe"}:
        raise ValueError("Node must be a native Node 22 executable, not a wrapper")
    if env.get("NODE_OPTIONS") or env.get("NODE_PATH"):
        raise ValueError("Vitest observer owns Node loading; remove NODE_OPTIONS/NODE_PATH")
    code, stdout, stderr = run_owned(
        [
            str(node),
            "-e",
            "console.log(JSON.stringify({version:process.version,path:process.execPath}))",
        ],
        project,
        env,
    )
    if code:
        raise ValueError(f"Cannot verify Node runtime: {stderr}")
    runtime = json.loads(stdout)
    if not str(runtime.get("version", "")).startswith("v22.") or runtime.get("path") != str(node):
        raise ValueError("Vitest observations require genuine Node 22 with matching execPath")
    return node, cli


# @spec FR-001: Observe genuine direct Node 22 and local Vitest execution
# — .specs/features/096-node-vitest-execution/spec.md#fr-001
def prepare_vitest(
    argv: list[str],
    adapter: str,
    report: Path,
    project: Path,
    env: dict[str, str],
    *,
    execution_cwd: Path | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Validate the local runtime, freeze dependencies and inject only owned paths."""
    if adapter != "junit":
        raise ValueError("Vitest observations require --report-adapter junit")
    project = project.resolve(strict=True)
    cwd = execution_cwd or project
    package, config, selected = _selection(argv, project, cwd)
    node, cli = _validate_vitest_runtime(argv, cwd, package, env)
    provenance = vitest_provenance(node, package, config, project, execution_cwd=cwd)
    assets = Path(__file__).with_name("vitest")
    env.update(
        LIVESPEC_VITEST_ROOT=str(package),
        LIVESPEC_VITEST_ASSETS=str(assets),
        LIVESPEC_VITEST_JUNIT=str(report),
        LIVESPEC_VITEST_MODULES=str(package / "node_modules"),
        LIVESPEC_VITEST_ORIGINAL_CONFIG=str(config) if config else "",
        LIVESPEC_VITEST_INVENTORY=str(report.with_name("runner-inventory")),
        LIVESPEC_VITEST_INPUTS=str(report.with_name("runner-inputs")),
        LIVESPEC_VITEST_WORKERS=str(report.with_name("vitest-workers")),
        LIVESPEC_VITEST_TEST_TIMEOUT="10000",
        LIVESPEC_VITEST_HOOK_TIMEOUT="10000",
    )
    report.with_name("vitest-workers").mkdir(mode=0o700)
    budget = json.loads(env.get("LIVESPEC_TEST_BUDGET", "{}"))
    defaults = budget.get("defaults", {})
    if isinstance(defaults, dict):
        seconds = defaults.get("unit", 2)
        env["LIVESPEC_VITEST_TEST_TIMEOUT"] = str(int(float(seconds) * 1000))
        env["LIVESPEC_VITEST_HOOK_TIMEOUT"] = env["LIVESPEC_VITEST_TEST_TIMEOUT"]
    return [
        str(node),
        str(cli),
        "run",
        *selected,
        "--root",
        str(package),
        "--config",
        str(assets / "config.ts"),
    ], provenance
