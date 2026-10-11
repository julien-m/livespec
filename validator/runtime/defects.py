"""Project-local LiveSpec tool defect reports that block a feature phase.

Writes only inside the target project (``.specs/tool-defects/`` and the feature
``pipeline.md``) and never invokes git, so no LiveSpec snapshot or checkout changes.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import typer

from validator.pipeline import PHASE_UPDATE_ERRORS, write_phase_update

from .errors import RuntimeDefectError
from .home import RuntimeHome, executing_root, require_project_root
from .models import JsonObject
from .project import read_lock
from .shim_core import dev_source_root

DEFECTS_RELPATH = Path(".specs") / "tool-defects"
STATUS_BLOCKED = "blocked-by-tool"
# D-12: slugs keep [a-z0-9-] and at most 60 characters so filenames stay portable.
_SLUG_MAX = 60
_NON_SLUG_RE = re.compile(r"[^a-z0-9]+")
# Bound on same-day collisions; far beyond any realistic number of reports per day.
_MAX_SUFFIX = 1000


@dataclass(frozen=True)
class DefectRequest:
    """Inputs of ``livespec runtime defect`` after CLI validation."""

    start: Path
    command: str
    error: str
    home: RuntimeHome
    clock: Callable[[], datetime]
    feature: str | None = None
    phase: str | None = None
    title: str | None = None


@dataclass(frozen=True)
class DefectResult:
    """Outcome of a defect report."""

    report: Path
    identity: JsonObject
    pipeline_updated: bool

    def to_dict(self) -> JsonObject:
        """Return the JSON payload printed by ``defect --json``."""
        return {
            "report": str(self.report),
            "identity": self.identity,
            "status": STATUS_BLOCKED,
            "pipeline_updated": self.pipeline_updated,
        }


def slugify(text: str) -> str:
    """Return a ``[a-z0-9-]`` slug of at most 60 characters (``defect`` when empty)."""
    slug = _NON_SLUG_RE.sub("-", text.lower()).strip("-")[:_SLUG_MAX].strip("-")
    return slug or "defect"


def runtime_identity(project: Path, home: RuntimeHome) -> JsonObject:
    """Freeze the runtime identity recorded in a defect report.

    Args:
        project: Project root.
        home: Runtime home used to resolve an unpinned runtime.

    Returns:
        Lock identity (pinned), dev source (dev), ``invalid-lock`` or ``unpinned`` with
        the resolved runtime path.
    """
    lock, previous = read_lock(project)
    if previous == "invalid":
        return {"mode": "invalid-lock"}
    if lock is None:
        resolved = home.current.resolve() if home.current.is_dir() else executing_root()
        return {"mode": "unpinned", "runtime_path": str(resolved)}
    if lock["mode"] == "dev":
        source = dev_source_root(project, str(lock["source"]))
        return {"mode": "dev", "source": str(source)}
    return {key: lock[key] for key in ("mode", "runtime_id", "livespec_version", "commit")}


def _resume_steps(identity: JsonObject, feature: str | None, phase: str | None) -> list[str]:
    mode = identity["mode"]
    # D-03: the fix ships in LiveSpec separately; each lock mode has its own way back.
    if mode == "pinned":
        first = "`livespec runtime upgrade --to <fixed runtime>` once a fixed runtime is installed"
    elif mode == "dev":
        first = f"update the dev checkout {identity['source']} to a commit containing the fix"
    else:
        first = "`livespec runtime pin --runtime <fixed runtime>` once a fixed runtime is installed"
    if feature and phase:
        resume = f"resume phase `{phase}` of `{feature}` (`livespec pipeline update --feature "
        resume += f"{feature} --phase {phase} --status in_progress`)"
    else:
        resume = "resume the blocked work"
    return [first, resume]


def _fence(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def render_report(request: DefectRequest, identity: JsonObject, date: str) -> str:
    """Render the Markdown defect report.

    The document has a title, a metadata bullet list (status, date, command,
    feature, phase, runtime identity), the verbatim error inside a fence longer
    than any backtick run it contains, and the numbered resume steps.

    Args:
        request: Defect inputs.
        identity: Frozen runtime identity.
        date: UTC date ``YYYY-MM-DD``.

    Returns:
        Report Markdown.
    """
    title = request.title or request.command
    lines = [f"# Tool defect: {title}", "", f"- **Status:** {STATUS_BLOCKED}"]
    lines += [f"- **Date:** {date}", f"- **Command:** `{request.command}`"]
    lines += [f"- **Feature:** {request.feature or '—'}", f"- **Phase:** {request.phase or '—'}"]
    lines += [f"- **Runtime {key}:** {value}" for key, value in identity.items()]
    fence = _fence(request.error)
    lines += ["", "## Error", "", f"{fence}text", request.error, fence, "", "## Resume", ""]
    steps = _resume_steps(identity, request.feature, request.phase)
    lines += [f"{index}. {step}" for index, step in enumerate(steps, start=1)]
    return "\n".join(lines) + "\n"


def _write_unique(directory: Path, stem: str, content: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for index in range(1, _MAX_SUFFIX):
        name = f"{stem}.md" if index == 1 else f"{stem}-{index}.md"
        try:
            # Exclusive create: an existing report is never opened for writing.
            with (directory / name).open("x", encoding="utf-8") as handle:
                handle.write(content)
        except FileExistsError:
            continue
        return directory / name
    raise RuntimeDefectError(f"too many defect reports named {stem}", str(directory))


def _block_phase(project: Path, feature: str, phase: str, report: Path) -> None:
    feature_dir = project / ".specs" / "features" / feature
    pipeline = feature_dir / "pipeline.md"
    if not pipeline.is_file():
        raise RuntimeDefectError(
            f"phase update failed: pipeline not found: {pipeline}", str(report)
        )
    try:
        write_phase_update(
            feature_dir,
            pipeline,
            feature,
            phase,
            "blocked",
            False,
            None,
            "",
            None,
            None,
            report=False,
        )
    except (typer.Exit, *PHASE_UPDATE_ERRORS) as exc:
        raise RuntimeDefectError(
            f"phase update failed for {feature}/{phase}: {exc}", str(report)
        ) from exc


# @spec FR-011: Report and blocked phase
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-011
def report_defect(request: DefectRequest) -> DefectResult:
    """Write a never-overwritten defect report, then block the feature phase if given.

    Args:
        request: Defect inputs; the CLI checks that ``phase`` is a known slug and
            requires ``feature``.

    Returns:
        The report path, frozen identity and whether the pipeline was updated.

    Raises:
        RuntimeLockError: No project root.
        RuntimeDefectError: The report was kept but the phase update failed.
    """
    project = require_project_root(request.start)
    identity = runtime_identity(project, request.home)
    date = request.clock().astimezone(UTC).strftime("%Y-%m-%d")
    stem = f"{date}-{slugify(request.title or request.command)}"
    report = _write_unique(project / DEFECTS_RELPATH, stem, render_report(request, identity, date))
    if request.feature and request.phase:
        _block_phase(project, request.feature, request.phase, report)
        return DefectResult(report, identity, True)
    return DefectResult(report, identity, False)
