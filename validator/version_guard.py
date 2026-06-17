"""Blocking migration guard for project-scoped LiveSpec commands."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from validator.cli_resolvers import detect_specs_root
from validator.migration_planner import MigrationPlannerError

RECOVERY_HINT = "Run /spec-migrate or livespec migrate before running this command."
MIGRATION_IN_PROGRESS_ENV = "LIVESPEC_MIGRATION_IN_PROGRESS"
MIGRATION_LIVESPEC_ENV = "LIVESPEC_MIGRATION_LIVESPEC"
MIGRATION_PROJECT_ENV = "LIVESPEC_MIGRATION_PROJECT"


@dataclass(frozen=True)
class ProjectVersionState:
    """Version comparison for a LiveSpec project."""

    project_root: Path
    project_version: int
    target_version: int

    @property
    def is_stale(self) -> bool:
        """Return whether the project must be migrated before normal commands run."""
        return self.project_version < self.target_version


class ProjectMigrationRequiredError(RuntimeError):
    """Raised when a project is older than the running LiveSpec version."""

    def __init__(self, state: ProjectVersionState) -> None:
        self.state = state
        super().__init__(
            "\n".join(
                (
                    "Error: LiveSpec project is not migrated.",
                    f"Project version: v{state.project_version}",
                    f"Required version: v{state.target_version}",
                    RECOVERY_HINT,
                )
            )
        )


def find_project_for_guard(args: list[str], *, cwd: Path | None = None) -> Path | None:
    """Resolve the project root that a command should be guarded against.

    Args:
        args: Root command arguments after the executable name.
        cwd: Current working directory used when no explicit project option exists.

    Returns:
        Project root containing `.specs/`, or `None` when the command is not
        running against an initialized LiveSpec project.
    """
    explicit_project = _option_value(args, "--project") or _option_value(args, "--repo")
    start = Path(explicit_project) if explicit_project is not None else cwd
    root = detect_specs_root(start)
    if root is None:
        return None
    if not _is_initialized_livespec_project(root):
        return None
    return root


def read_project_version_state(
    project_root: Path, *, livespec_root: Path | None = None
) -> ProjectVersionState:
    """Read project and target LiveSpec versions for migration enforcement.

    Args:
        project_root: Root directory containing `.specs/`.
        livespec_root: Optional LiveSpec repository root. Defaults to the
            installed package repository.

    Returns:
        Parsed project and target versions.

    Raises:
        MigrationPlannerError: If either version file contains an invalid value.
    """
    resolved_project = project_root.resolve()
    target_root = _resolve_livespec_root(resolved_project, livespec_root)
    return ProjectVersionState(
        project_root=resolved_project,
        project_version=_read_project_version(resolved_project),
        target_version=_read_target_version(target_root),
    )


def enforce_project_migrated(
    args: list[str],
    *,
    cwd: Path | None = None,
    livespec_root: Path | None = None,
) -> None:
    """Raise when a command targets a stale LiveSpec project."""
    project_root = find_project_for_guard(args, cwd=cwd)
    if project_root is None:
        return
    if _is_scoped_migration_subprocess(project_root, livespec_root):
        return
    state = read_project_version_state(project_root, livespec_root=livespec_root)
    if state.is_stale:
        raise ProjectMigrationRequiredError(state)


def _is_initialized_livespec_project(project_root: Path) -> bool:
    specs_root = project_root / ".specs"
    return (specs_root / "livespec-version").exists() or (specs_root / "spec-system.md").exists()


def _option_value(args: list[str], option: str) -> str | None:
    for index, arg in enumerate(args):
        if arg == option and index + 1 < len(args):
            return args[index + 1]
        prefix = f"{option}="
        if arg.startswith(prefix):
            return arg[len(prefix) :]
    return None


def _resolve_livespec_root(project_root: Path, explicit_root: Path | None) -> Path:
    if explicit_root is not None:
        return explicit_root.resolve()
    path_file = project_root / ".specs" / ".livespec-path"
    if path_file.is_file():
        candidate = Path(path_file.read_text(encoding="utf-8").strip()).expanduser()
        if candidate.is_dir():
            return candidate.resolve()
    return Path(__file__).resolve().parents[1]


def _read_project_version(project_root: Path) -> int:
    path = project_root / ".specs" / "livespec-version"
    if not path.exists():
        return 1
    return _parse_int(path.read_text(encoding="utf-8").strip(), field="project_version")


def _read_target_version(livespec_root: Path) -> int:
    path = livespec_root / "VERSION"
    if not path.is_file():
        raise MigrationPlannerError(f"VERSION file not found: {path}")
    return _parse_int(path.read_text(encoding="utf-8").strip(), field="target_version")


def _is_scoped_migration_subprocess(project_root: Path, livespec_root: Path | None) -> bool:
    if os.environ.get(MIGRATION_IN_PROGRESS_ENV) != "1":
        return False

    raw_project = os.environ.get(MIGRATION_PROJECT_ENV)
    raw_livespec = os.environ.get(MIGRATION_LIVESPEC_ENV)
    if raw_project is None or raw_livespec is None:
        return False

    try:
        env_project = Path(raw_project).expanduser().resolve()
        env_livespec = Path(raw_livespec).expanduser().resolve()
        target_livespec = _resolve_livespec_root(project_root, livespec_root)
    except OSError:
        return False

    return env_project == project_root.resolve() and env_livespec == target_livespec


def _parse_int(raw: object, *, field: str) -> int:
    try:
        return int(str(raw).strip())
    except ValueError as exc:
        raise MigrationPlannerError(f"{field} must be an integer: {raw!r}") from exc


# Export only the migration guard API used by CLI entry points and tests.
__all__ = [
    "ProjectMigrationRequiredError",
    "ProjectVersionState",
    "enforce_project_migrated",
    "find_project_for_guard",
    "read_project_version_state",
]
