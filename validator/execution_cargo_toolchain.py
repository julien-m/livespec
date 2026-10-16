"""Resolve and pin the trusted Cargo runner's tools (parent side, stdlib only).

Provenance binds the interpreter, every runner source file and the exact Cargo,
llvm-profdata and llvm-cov executables. Verification later re-hashes the same
recorded files, so a changed tool or runner invalidates earlier captures.
"""

# @spec FR-007: Pinned Cargo runner provenance
#   — .specs/features/085-cargo-execution-runner/spec.md#fr-007

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from contextlib import suppress
from pathlib import Path

_HERE = Path(__file__).resolve().parent
RUNNER_FILES = (
    "execution_cargo.py",
    "execution_cargo_command.py",
    "execution_cargo_driver.py",
    "execution_cargo_hook.py",
    "execution_cargo_coverage.py",
    "execution_cargo_rustc.sh",
    "execution_cargo_toolchain.py",
    "execution_rust_source.py",
    "execution_test_budget.py",
)
_TOOL_KEYS = ("cargo", "llvm_profdata", "llvm_cov")


class CargoRunnerUnavailable(Exception):
    """The trusted Cargo runner cannot run here; the command still runs uncertified."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(argv: list[str], root: Path, env: dict[str, str]) -> str:
    try:
        completed = subprocess.run(
            argv, cwd=root, env=env, capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CargoRunnerUnavailable(f"cannot run {argv[0]}: {exc}") from exc
    if completed.returncode != 0:
        raise CargoRunnerUnavailable(f"{' '.join(argv)} failed: {completed.stderr.strip()}")
    return completed.stdout


def _rustc(toolchain: str | None, env: dict[str, str]) -> list[str]:
    return [env.get("RUSTC", "rustc"), *([toolchain] if toolchain else [])]


def host_triple(root: Path, env: dict[str, str], toolchain: str | None = None) -> str:
    """The host triple of the rustc Cargo will use in this project."""
    output = _run([*_rustc(toolchain, env), "-vV"], root, env)
    for line in output.splitlines():
        if line.startswith("host: "):
            return line.removeprefix("host: ").strip()
    raise CargoRunnerUnavailable("rustc -vV does not report a host triple")


def llvm_tools(root: Path, env: dict[str, str], toolchain: str | None = None) -> tuple[Path, Path]:
    """Locate llvm-profdata and llvm-cov able to read this toolchain's profiles.

    Order: the toolchain's `llvm-tools` component, Xcode on macOS, then PATH.
    """
    sysroot = Path(_run([*_rustc(toolchain, env), "--print", "sysroot"], root, env).strip())
    host = host_triple(root, env, toolchain)
    component = sysroot / "lib/rustlib" / host / "bin"
    candidates = [(component / "llvm-profdata", component / "llvm-cov")]
    if sys.platform == "darwin" and shutil.which("xcrun", path=env.get("PATH")):
        with suppress(CargoRunnerUnavailable):
            candidates.append(
                (
                    Path(_run(["xcrun", "--find", "llvm-profdata"], root, env).strip()),
                    Path(_run(["xcrun", "--find", "llvm-cov"], root, env).strip()),
                )
            )
    found = [shutil.which(name, path=env.get("PATH")) for name in ("llvm-profdata", "llvm-cov")]
    if all(found):
        candidates.append((Path(str(found[0])), Path(str(found[1]))))
    for profdata, cov in candidates:
        if profdata.is_file() and cov.is_file():
            return profdata.resolve(), cov.resolve()
    raise CargoRunnerUnavailable(
        "assertion tracing needs llvm-profdata and llvm-cov "
        "(install with: rustup component add llvm-tools)"
    )


def cargo_provenance(
    program: str, toolchain: str | None, root: Path, env: dict[str, str]
) -> dict[str, str]:
    """Pin the interpreter, runner files and tools for one capture.

    Raises:
        CargoRunnerUnavailable: Cargo or the LLVM coverage tools are missing.
    """
    cargo = shutil.which(program, path=env.get("PATH"))
    if cargo is None:
        raise CargoRunnerUnavailable(f"{program} not found")
    profdata, cov = llvm_tools(root, env, toolchain)
    # Keep the proxy path itself: rustup dispatches on the executable name.
    tools = {"cargo": Path(cargo).absolute(), "llvm_profdata": profdata, "llvm_cov": cov}
    provenance = {"runner": "cargo", "interpreter": str(Path(sys.executable).resolve())}
    for name in RUNNER_FILES:
        provenance[f"file:{name}"] = _sha256(_HERE / name)
    for key, path in tools.items():
        provenance[f"{key}_path"] = str(path)
        provenance[f"{key}_sha256"] = _sha256(path)
    return provenance


def current_cargo_provenance(recorded: dict[str, str]) -> dict[str, str]:
    """Recompute a recorded provenance from the files it names, now."""
    current = {"runner": "cargo", "interpreter": str(Path(sys.executable).resolve())}
    for name in RUNNER_FILES:
        current[f"file:{name}"] = _sha256(_HERE / name)
    for key in _TOOL_KEYS:
        path = Path(recorded.get(f"{key}_path", ""))
        current[f"{key}_path"] = str(path)
        current[f"{key}_sha256"] = _sha256(path) if path.is_file() else "missing"
    return current


def runner_paths() -> tuple[Path, Path]:
    """The driver script executed with `python -I` and the rustc workspace wrapper."""
    return _HERE / "execution_cargo.py", _HERE / "execution_cargo_rustc.sh"
