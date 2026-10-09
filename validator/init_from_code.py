"""Initialize observed project facts with bounded installation and safe recovery."""

from __future__ import annotations

import argparse
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .init_documents import render_documents, render_preflight
from .init_probes import require_success, run_command, run_probes
from .init_profile import InitError, ObservedProfile, detect_profile
from .init_recovery import (
    backup_artifacts,
    conventions_are_valid,
    merge_integration,
    observed_adr_path,
    preserve_custom_block,
    refresh_registry,
    render_conventions,
    validate_destinations,
    write_atomic,
)
from .init_verification import MANIFEST, render_manifest, verify_current_profile

LIVESPEC_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT_SECONDS = 300.0
INCOMPLETE_RECAP = """---
status: blocked
---

Initialization is incomplete; no application runtime certification.
"""


@dataclass(frozen=True)
class InitOptions:
    """Validated target, recovery mode and total process budget."""

    project: Path
    force: bool = False
    dry_run: bool = False
    verify_only: bool = False
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS


def _read_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _prepare_documents(profile: ObservedProfile, root: Path) -> dict[str, str]:
    documents = {f".specs/{path}": text for path, text in render_documents(profile).items()}
    adr = documents.pop(".specs/stacks/decisions/ADR-bootstrap-observed.md")
    # Source-specific ADR names retain historical observations across force recovery.
    documents[f".specs/{observed_adr_path(profile)}"] = adr
    documents[".specs/README.md"] = refresh_registry(
        _read_if_exists(root / ".specs/README.md"), profile
    )
    previous = _read_if_exists(root / ".specs/preflight.md")
    documents[".specs/preflight.md"] = preserve_custom_block(
        previous, documents[".specs/preflight.md"]
    )
    if (root / ".specs/roadmap.md").is_file():
        documents.pop(".specs/roadmap.md")
    if not conventions_are_valid(root):
        documents.update(
            {
                f".conventions/{path}": text
                for path, text in render_conventions(
                    Path(
                        os.environ.get("AIRESOURCES", str(LIVESPEC_ROOT.parent / "ai-ressources"))
                    ),
                    profile.product_name,
                ).items()
            }
        )
    for filename in ("AGENTS.md", "CLAUDE.md"):
        documents[filename] = merge_integration(_read_if_exists(root / filename))
    patterns = (
        ".specs/.livespec-path",
        ".specs/.runs/",
        ".specs/preflight-report.md",
        ".livespec-backups/",
    )
    ignore = _read_if_exists(root / ".gitignore")
    documents[".gitignore"] = (
        ignore
        + ("\n" if ignore and not ignore.endswith("\n") else "")
        + "".join(pattern + "\n" for pattern in patterns if pattern not in ignore.splitlines())
    )
    return documents


def _install(root: Path, options: InitOptions, deadline: float) -> None:
    argv: tuple[str, ...] = (
        "bash",
        str(LIVESPEC_ROOT / "scripts/init.sh"),
        str(root),
        "--non-interactive",
    )
    # The public force check/backup ran before our initial blocked marker created .specs.
    argv += ("--force",)
    require_success(run_command(argv, root, deadline), "installer/sync")


def _install_hooks(root: Path, deadline: float) -> None:
    """Run the official installer before integration capture, within the same run budget."""
    argv = ("bash", str(LIVESPEC_ROOT / "scripts/install-hooks.sh"), str(root), str(LIVESPEC_ROOT))
    require_success(run_command(argv, root, deadline), "install pre-commit hooks")


def _integration_artifacts(root: Path) -> dict[str, str]:
    files: tuple[str, ...] = (
        ".specs/spec-system.md",
        ".specs/livespec-version",
        ".specs/.livespec-path",
        ".conventions/index.md",
        ".conventions/manifest.yaml",
        "AGENTS.md",
        "CLAUDE.md",
        ".gitignore",
        ".specs/README.md",
    )
    if (root / ".git").is_dir():
        files += (".git/hooks/pre-commit",)
    for relative in files:
        if not (root / relative).is_file():
            raise InitError(f"integration missing after installer: {relative}")
    return {relative: (root / relative).read_text(encoding="utf-8") for relative in files}


def _ensure_core(root: Path) -> None:
    write_atomic(
        root,
        root / ".specs/livespec-version",
        (LIVESPEC_ROOT / "VERSION").read_text(encoding="utf-8"),
    )
    write_atomic(root, root / ".specs/.livespec-path", str(LIVESPEC_ROOT) + "\n")


def _generate(
    root: Path,
    options: InitOptions,
    profile: ObservedProfile,
    documents: dict[str, str],
    deadline: float,
) -> None:
    # Invalidate an old success BEFORE installer/sync/probes can fail or time out.
    write_atomic(root, root / ".specs/bootstrap-recap.md", INCOMPLETE_RECAP)
    write_atomic(
        root,
        root / ".specs/preflight-report.md",
        "# Preflight Report\n\nVerdict: BLOCKED\n\n"
        "Initialization in progress; tooling not yet verified.\n",
    )
    _install(root, options, deadline)
    _ensure_core(root)
    for relative, content in documents.items():
        write_atomic(root, root / relative, content)
    # Hooks append ignore lines: complete their mutations before snapshotting integrations.
    _install_hooks(root, deadline)
    results = run_probes(profile, root, deadline)
    report = render_preflight(results)
    write_atomic(root, root / ".specs/preflight-report.md", report)
    for result in results:
        require_success(result, "required tooling")
    if detect_profile(root) != profile:
        raise InitError("current source/profile identity drift during initialization")
    if time.monotonic() >= deadline:
        raise InitError("total initialization deadline exhausted before completion")
    documents.update(_integration_artifacts(root))
    documents[".specs/preflight-report.md"] = report
    recap = """---
status: completed
---

Backend artifacts and observed tooling verified.
Native command goal proof, after-init hooks and archive remain required.
Application build/UI/runtime not executed.
"""
    documents[".specs/bootstrap-recap.md"] = recap
    write_atomic(root, root / MANIFEST, render_manifest(profile, documents))
    write_atomic(root, root / ".specs/bootstrap-recap.md", recap)
    verify_current_profile(root)


# @spec FR-003: Autonomous safe selected-target dispatch
#   — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-003
def initialize_from_code(options: InitOptions) -> ObservedProfile:
    """Generate verified backend artifacts; command closure remains a separate goal.

    Args:
        options: Validated directory, modes and finite total deadline.
    Returns:
        Source-backed observed profile after current content verification.
    Raises:
        InitError: Evidence, recovery, installation, tooling or verification fails.
    """
    deadline = time.monotonic() + options.timeout_seconds
    root = options.project.resolve()
    validate_destinations(root)
    profile = detect_profile(root)
    if options.verify_only:
        return verify_current_profile(root)
    # The sync guard understands only narrowly recognized legacy agent links.
    check = (
        "bash",
        str(LIVESPEC_ROOT / "scripts/sync-agent-assets.sh"),
        str(root),
        str(LIVESPEC_ROOT),
        "--check-paths-only",
    )
    require_success(run_command(check, root, deadline), "integration path validation")
    documents = _prepare_documents(profile, root)
    if options.dry_run:
        return profile
    if (root / ".specs").exists() and not options.force:
        raise InitError(
            ".specs already exists; explicit --force required for noninteractive recovery"
        )
    if options.force or (root / ".git/hooks/pre-commit").is_file():
        # Preserve a custom hook even during the first installation into a fresh Git project.
        backup_artifacts(root)
    try:
        _generate(root, options, profile, documents, deadline)
    except (InitError, OSError):
        write_atomic(root, root / ".specs/bootstrap-recap.md", INCOMPLETE_RECAP)
        raise
    return profile


def _parse_options(argv: list[str] | None) -> InitOptions:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?")
    parser.add_argument("--dir", dest="directory")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)
    if (
        args.project
        and args.directory
        and Path(args.project).resolve() != Path(args.directory).resolve()
    ):
        parser.error("positional project conflicts with --dir")
    if args.verify_only and (args.force or args.dry_run):
        parser.error("--verify-only cannot be combined with --force or --dry-run")
    if not math.isfinite(args.timeout_seconds) or args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be finite and positive")
    return InitOptions(
        Path(args.directory or args.project or "."),
        args.force,
        args.dry_run,
        args.verify_only,
        args.timeout_seconds,
    )


def main(argv: list[str] | None = None) -> int:
    """Parse CLI modes, report contextual errors and return a process exit code."""
    options = _parse_options(argv)
    try:
        profile = initialize_from_code(options)
    except (InitError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if options.dry_run:
        print(f"Preview: {profile.product_name}; no changes applied")
    elif options.verify_only:
        print(f"Current profile verified: {profile.product_name}; read-only")
    else:
        print(
            f"Autonomous from-code: enabled\nLiveSpec initialized: {profile.product_name}\n"
            "Penflow Contract Verdict: ABSENT\n"
            "Backend complete; prove native command goal and archive before command completion."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
