"""Auto-fix missing preflight tools and runner resources.

This module implements the ``--fix`` mode of ``/spec.preflight``. It:

* dispatches install commands for missing tools through trusted package
  managers (``brew``, ``cargo``, ``npm``, ``pip``, allowlisted curl-pipe
  installers);
* initialises ephemeral resources (iOS simulators, Android AVDs, Xcode
  license acceptance);
* performs *smart scoping* by inspecting ``git diff HEAD~1..HEAD`` and
  filtering checks to drivers/UI runners impacted by the most recent
  commit;
* emits step-by-step guides for manual actions that cannot be safely
  automated;
* renders a final summary table.

The module is intentionally pure-Python with subprocess shelling - there
is no implicit dependency on the rest of the validator package so that
``/spec.preflight`` (a Claude Code command) can shell out to it from any
context.
"""

from __future__ import annotations

import dataclasses
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Final, Literal

# --- Models -----------------------------------------------------------------

InstallerKind = Literal[
    "brew",
    "cargo",
    "npm",
    "pip",
    "pipx",
    "curl",
    "manual",
    "xcode-select",
    "simctl",
    "avdmanager",
    "sdkmanager",
    "xcode-license",
]

ItemStatus = Literal[
    "ok",
    "installed",
    "manual_required",
    "failed",
    "skipped",
    "would_install",
]


FILE_PATTERN_MAP: Final[tuple[tuple[re.Pattern[str], str, str | None], ...]] = (
    # These regexes infer the minimum toolchain scope from changed filenames so
    # `--fix` can stay narrow by default and only expand to `--full` when git
    # cannot provide a usable diff.
    (re.compile(r"\.py$"), "python", None),
    (re.compile(r"\.swift$"), "swift", "ios"),
    (re.compile(r"\.kt$|\.kts$"), "kotlin", "android"),
    (re.compile(r"\.java$"), "java", "android"),
    (re.compile(r"\.rs$"), "rust", "tauri"),
    (re.compile(r"\.go$"), "go", None),
    (re.compile(r"\.tsx?$|\.jsx?$"), "node", "web"),
    (re.compile(r"\.dart$"), "dart", "flutter"),
)


@dataclasses.dataclass(frozen=True)
class PreflightItem:
    """Describe one fixable preflight requirement.

    Attributes:
        name: Human-readable label rendered in the summary.
        binary: Binary expected on `PATH` when the item is satisfied.
        installer: Install or init strategy used when verification fails.
        install_arg: Installer-specific argument payload.
        verify_cmd: Optional shell-free verification command override.
        driver: Optional driver tag used by smart scoping.
        runner: Optional runner tag used by smart scoping.
        manual_steps: Ordered steps shown when the fix requires a human.
        safe_for_auto: Whether non-interactive `--auto` may run the fix.
    """

    name: str
    binary: str | None
    installer: InstallerKind
    install_arg: str
    verify_cmd: Sequence[str] | None = None
    driver: str | None = None
    runner: str | None = None
    manual_steps: tuple[str, ...] = ()
    safe_for_auto: bool = True


@dataclasses.dataclass
class FixResult:
    """Capture the result of a single fix attempt.

    Attributes:
        item: Preflight item that was processed.
        status: Final status for the item.
        message: User-facing explanation of the outcome.
        command: Installer command that ran or would run.
        stderr: Captured stderr, or stdout fallback, for failed commands.
    """

    item: PreflightItem
    status: ItemStatus
    message: str = ""
    command: str = ""
    stderr: str = ""


# --- Trusted curl-pipe allowlist -------------------------------------------

CURL_ALLOWLIST: Final[dict[str, str]] = {
    "maestro": "https://get.maestro.mobile.dev",
    "rustup": "https://sh.rustup.rs",
    "starship": "https://starship.rs/install.sh",
    "bun": "https://bun.sh/install",
}

# --- Subprocess helpers ----------------------------------------------------


def _which(binary: str) -> str | None:
    """Resolve a binary from `PATH`.

    Args:
        binary: Binary name to locate.

    Returns:
        Absolute path when found, otherwise `None`.
    """

    return shutil.which(binary)


def _run(
    cmd: Sequence[str] | str,
    *,
    shell: bool = False,
    timeout: int = 600,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run an external command with consistent defaults for preflight checks.

    Args:
        cmd: Command vector or shell string.
        shell: Whether to execute through the shell.
        timeout: Maximum runtime in seconds.
        capture: Whether to capture stdout and stderr.

    Returns:
        Completed process result for the spawned command.
    """

    return subprocess.run(
        cmd,
        shell=shell,
        check=False,
        text=True,
        capture_output=capture,
        timeout=timeout,
    )


# --- Smart scoping ---------------------------------------------------------


def changed_files(repo: Path, *, base: str = "HEAD~1", head: str = "HEAD") -> list[str]:
    """Return file paths changed between `base` and `head`.

    Args:
        repo: Repository root to diff.
        base: Base revision for the diff.
        head: Head revision for the diff.

    Returns:
        Changed file paths, or an empty list when git cannot provide a diff.
    """

    # `git diff --name-only` returns one relative path per line and a non-zero
    # exit code when the revision range is unavailable, which `run_fix()` treats
    # as "scope information unavailable, fall back to the full item set".
    proc = _run(
        ["git", "-C", str(repo), "diff", "--name-only", f"{base}..{head}"],
        capture=True,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def impacted_drivers(files: Iterable[str]) -> set[str]:
    """Map changed files to driver identifiers.

    Args:
        files: Changed file paths.

    Returns:
        Driver identifiers inferred from file extensions and locations.
    """

    out: set[str] = set()
    for file_path in files:
        for pattern, driver, _runner in FILE_PATTERN_MAP:
            if pattern.search(file_path):
                out.add(driver)
    return out


def impacted_runners(files: Iterable[str]) -> set[str]:
    """Map changed files to runner identifiers.

    Args:
        files: Changed file paths.

    Returns:
        Runner identifiers inferred from file extensions and locations.
    """

    out: set[str] = set()
    for file_path in files:
        for pattern, _driver, runner in FILE_PATTERN_MAP:
            if runner and pattern.search(file_path):
                out.add(runner)
    return out


def filter_items(
    items: Sequence[PreflightItem],
    *,
    drivers: set[str],
    runners: set[str],
) -> list[PreflightItem]:
    """Keep only items relevant to the impacted drivers and runners.

    Args:
        items: Parsed manifest items.
        drivers: Driver identifiers impacted by the current diff.
        runners: Runner identifiers impacted by the current diff.

    Returns:
        Filtered items to verify in scoped mode.
    """

    kept: list[PreflightItem] = []
    for item in items:
        if item.driver is None and item.runner is None:
            kept.append(item)
            continue
        if item.driver and item.driver in drivers:
            kept.append(item)
            continue
        if item.runner and item.runner in runners:
            kept.append(item)
    return kept


# --- Install dispatchers ---------------------------------------------------


def build_install_cmd(item: PreflightItem) -> tuple[Sequence[str] | str, bool]:
    """Build the installer command for one preflight item.

    Args:
        item: Item that needs installation or resource initialization.

    Returns:
        A `(command, shell)` pair for `_run()`.

    Raises:
        ValueError: If the installer kind cannot be dispatched safely.
    """

    arg = item.install_arg
    kind = item.installer

    if kind == "brew":
        return (["brew", "install", arg], False)
    if kind == "cargo":
        return (["cargo", "install", arg], False)
    if kind == "npm":
        manager = "pnpm" if _which("pnpm") else "npm"
        return ([manager, "install", "-g", arg], False)
    if kind == "pip":
        return (["pip", "install", "--user", arg], False)
    if kind == "pipx":
        return (["pipx", "install", arg], False)
    if kind == "xcode-select":
        return (["xcode-select", "--install"], False)
    if kind == "xcode-license":
        return (["sudo", "xcodebuild", "-license", "accept"], False)
    if kind == "simctl":
        # The arguments stay positional because `simctl create` binds them to
        # simulator name, device type, and runtime in this exact order.
        name, device, runtime = arg.split("|", 2)
        return (["xcrun", "simctl", "create", name, device, runtime], False)
    if kind == "avdmanager":
        # `avdmanager create avd` needs the AVD name before the system-image
        # package, so the serialized payload preserves that ordering.
        name, package = arg.split("|", 1)
        return (
            ["avdmanager", "create", "avd", "-n", name, "-k", package, "-d", "pixel"],
            False,
        )
    if kind == "sdkmanager":
        return (["sdkmanager", arg], False)
    if kind == "curl":
        url = CURL_ALLOWLIST.get(arg)
        if not url:
            raise ValueError(f"Untrusted curl-pipe installer: {arg!r}")
        return (f"curl -fsSL {url} | sh", True)
    if kind == "manual":
        raise ValueError("manual installer cannot be dispatched")
    raise ValueError(f"Unknown installer kind: {kind!r}")


def _verify(item: PreflightItem) -> bool:
    """Check whether an item is already satisfied.

    Args:
        item: Item to verify.

    Returns:
        `True` when the binary or explicit verification command succeeds.
    """

    if item.verify_cmd:
        proc = _run(list(item.verify_cmd), capture=True, timeout=15)
        return proc.returncode == 0
    if item.binary:
        return _which(item.binary) is not None
    return False


def verify_item(item: PreflightItem) -> bool:
    """Public wrapper around :func:`_verify` for external callers (Feature 035)."""
    return _verify(item)


# --- Guide rendering -------------------------------------------------------


def render_guide(item: PreflightItem) -> str:
    """Render numbered manual steps for an item.

    Args:
        item: Item that requires manual intervention.

    Returns:
        User-facing manual-action guidance.
    """

    if not item.manual_steps:
        return f"Manual action required for {item.name}: see project docs."
    lines = [f"Manual action required for {item.name}:"]
    for idx, step in enumerate(item.manual_steps, 1):
        lines.append(f"  {idx}. {step}")
    return "\n".join(lines)


# --- Main fix loop ---------------------------------------------------------


PromptFn = Callable[[str], bool]


def _default_prompt(message: str) -> bool:  # pragma: no cover - interactive
    """Prompt the user before running a non-automatic fix.

    Args:
        message: Prompt body shown to the user.

    Returns:
        `True` when the user explicitly accepts the action.
    """

    answer = input(f"{message} [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def fix_item(
    item: PreflightItem,
    *,
    auto: bool = False,
    dry_run: bool = False,
    prompt: PromptFn = _default_prompt,
) -> FixResult:
    """Attempt to fix a single preflight item.

    Args:
        item: Item to verify and possibly install.
        auto: Whether to skip confirmation prompts.
        dry_run: Whether to report actions without executing them.
        prompt: Prompt function used for interactive confirmation.

    Returns:
        Result describing the verification or install outcome.
    """

    if _verify(item):
        return FixResult(item, status="ok", message="already satisfied")

    if item.installer == "manual":
        return FixResult(
            item,
            status="manual_required",
            message=render_guide(item),
        )

    # Unsafe fixes require an explicit opt-in unless `--auto` was requested,
    # because the CLI contract says non-interactive mode is the deliberate
    # override for package-manager and shell side effects.
    if not item.safe_for_auto and not auto and not prompt(f"Install {item.name}?"):
        return FixResult(
            item,
            status="skipped",
            message="declined by user",
        )

    try:
        cmd, shell = build_install_cmd(item)
    except ValueError as exc:
        return FixResult(item, status="manual_required", message=str(exc))

    cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)

    if dry_run:
        return FixResult(
            item,
            status="would_install",
            command=cmd_str,
            message=f"would run: {cmd_str}",
        )

    proc = _run(cmd, shell=shell, capture=True)
    if proc.returncode != 0:
        return FixResult(
            item,
            status="failed",
            command=cmd_str,
            stderr=proc.stderr or proc.stdout,
            message=f"install failed (exit {proc.returncode}). Retry: {cmd_str}",
        )

    if _verify(item):
        return FixResult(
            item,
            status="installed",
            command=cmd_str,
            message="install verified",
        )

    return FixResult(
        item,
        status="failed",
        command=cmd_str,
        stderr=proc.stderr,
        message=(
            "installer succeeded but verify still fails - binary may not be on "
            "PATH; add the installer's bin directory to your shell profile."
        ),
    )


def run_fix(
    items: Sequence[PreflightItem],
    *,
    repo: Path | None = None,
    full: bool = False,
    auto: bool = False,
    dry_run: bool = False,
    prompt: PromptFn = _default_prompt,
) -> list[FixResult]:
    """Run `--fix` over the parsed manifest items.

    Args:
        items: Parsed preflight items.
        repo: Repository root used for smart scoping.
        full: Whether to disable smart scoping.
        auto: Whether to skip confirmation prompts.
        dry_run: Whether to report actions without executing them.
        prompt: Prompt function used for interactive confirmation.

    Returns:
        Results for every processed item.
    """

    scoped = list(items)
    if not full and repo is not None:
        files = changed_files(repo)
        if files:
            drivers = impacted_drivers(files)
            runners = impacted_runners(files)
            scoped = filter_items(items, drivers=drivers, runners=runners)

    return [
        fix_item(item, auto=auto, dry_run=dry_run, prompt=prompt) for item in scoped
    ]


# --- Summary ---------------------------------------------------------------


def render_summary(results: Sequence[FixResult]) -> str:
    """Render the final fix summary table.

    Args:
        results: Item-level fix results.

    Returns:
        Plain-text summary table.
    """

    counts: dict[ItemStatus, int] = {
        "ok": 0,
        "installed": 0,
        "would_install": 0,
        "manual_required": 0,
        "failed": 0,
        "skipped": 0,
    }
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    lines = [
        "Preflight Summary",
        "-----------------",
        f"  Verified:        {counts['ok']}",
        f"  Installed:       {counts['installed']}",
        f"  Would install:   {counts['would_install']}",
        f"  Manual required: {counts['manual_required']}",
        f"  Failed:          {counts['failed']}",
        f"  Skipped:         {counts['skipped']}",
    ]
    return "\n".join(lines)


def exit_code_for(results: Sequence[FixResult]) -> int:
    """Return the process exit code for a fix run.

    Args:
        results: Item-level fix results.

    Returns:
        `1` for failures, `2` for manual blockers, otherwise `0`.
    """

    if any(r.status == "failed" for r in results):
        return 1
    if any(r.status == "manual_required" for r in results):
        return 2
    return 0


# --- Manifest helpers ------------------------------------------------------


def parse_preflight_manifest(text: str) -> list[PreflightItem]:
    """Parse a preflight manifest into fixable items.

    Args:
        text: Raw `.specs/preflight.md` contents.

    Returns:
        Parsed items that can be verified or fixed automatically.
    """

    items: list[PreflightItem] = []
    blocks = re.split(r"^### ", text, flags=re.MULTILINE)
    for block in blocks[1:]:
        head, _, body = block.partition("\n")
        name = head.strip()
        if not name:
            continue
        binary = _extract_field(body, "binary") or _extract_field(body, "tool")
        install = (
            _extract_field(body, "install")
            or _extract_field(body, "auto_resolve")
            or ""
        )
        verify = _extract_field(body, "verify") or _extract_field(body, "check")
        installer, arg = _classify_install(install)
        if installer is None:
            continue
        verify_cmd: tuple[str, ...] | None
        verify_cmd = ("sh", "-c", verify) if verify else None
        items.append(
            PreflightItem(
                name=name,
                binary=binary,
                installer=installer,
                install_arg=arg,
                verify_cmd=verify_cmd,
            )
        )
    return items


def _extract_field(body: str, field: str) -> str | None:
    # This regex accepts both bullet-based markdown fields and YAML-style
    # `key: value` lines so the parser can tolerate the two manifest dialects
    # that exist in this repository today.
    pattern = re.compile(
        rf"(?:^[-*]\s*\*\*{field}:\*\*|^{field}:)\s*`?([^`\n]+)`?",
        flags=re.MULTILINE | re.IGNORECASE,
    )
    m = pattern.search(body)
    if not m:
        return None
    return m.group(1).strip().strip("`").strip()


def _classify_install(cmd: str) -> tuple[InstallerKind | None, str]:
    """Classify an install command into a supported installer kind.

    Args:
        cmd: Raw install or auto-resolve command from the manifest.

    Returns:
        Installer kind plus its argument payload.
    """

    cmd = cmd.strip()
    if not cmd or cmd.lower() in {"human", "false", "manual"}:
        return ("manual", "")
    parts = cmd.split()
    if not parts:
        return (None, "")
    if parts[0] == "brew":
        return ("brew", parts[-1])
    if parts[0] == "cargo" and len(parts) > 1 and parts[1] == "install":
        return ("cargo", parts[-1])
    if parts[0] in {"npm", "pnpm"} and "install" in parts:
        return ("npm", parts[-1])
    if parts[0] == "pip" or parts[0:2] == ["pip", "install"]:
        return ("pip", parts[-1])
    if parts[0] == "pipx":
        return ("pipx", parts[-1])
    if parts[0] == "xcode-select":
        return ("xcode-select", "")
    return ("manual", cmd)

# `__all__` keeps the small public surface stable for the CLI entrypoint and
# for tests that intentionally import the autofix primitives directly.
__all__ = [
    "CURL_ALLOWLIST",
    "FILE_PATTERN_MAP",
    "FixResult",
    "PreflightItem",
    "build_install_cmd",
    "changed_files",
    "exit_code_for",
    "filter_items",
    "fix_item",
    "impacted_drivers",
    "impacted_runners",
    "parse_preflight_manifest",
    "render_guide",
    "render_summary",
    "run_fix",
]


# --- CLI entrypoint --------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - CLI
    """Run the autofix CLI.

    Args:
        argv: Optional argument vector without the program name.

    Returns:
        Process exit code for the CLI invocation.
    """

    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="livespec-preflight-fix")
    parser.add_argument("--manifest", default=".specs/preflight.md")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repo", default=os.getcwd())
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    items = parse_preflight_manifest(manifest_path.read_text(encoding="utf-8"))
    results = run_fix(
        items,
        repo=Path(args.repo),
        full=args.full,
        auto=args.auto,
        dry_run=args.dry_run,
    )
    for r in results:
        print(f"[{r.status:>16}] {r.item.name}: {r.message}")
    print()
    print(render_summary(results))
    return exit_code_for(results)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
