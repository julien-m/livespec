"""Runtime drift scanner shared by ``livespec runtime status`` and ``livespec doctor``.

Every applicable rule is evaluated and all findings are reported cumulatively.
Git is only queried read-only (``status`` with optional locks disabled), so a
checked checkout keeps its index and files unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import RuntimeSnapshotError, RuntimeSourceError
from .git_tree import dirty_paths
from .home import RuntimeHome, is_livespec_root, is_snapshot_root
from .links import owned_links
from .manifest import verify_snapshot
from .models import LIVESPEC_PATH_RELPATH, LOCK_RELPATH, FindingSeverity, JsonObject, RuntimeFinding
from .project import read_lock
from .shim_core import LockData, dev_source_root

Reference = tuple[str, Path]
INSTALL_HINT = "livespec runtime install --source {root} && livespec runtime pin"


@dataclass(frozen=True)
class StatusReport:
    """Payload of ``livespec runtime status``."""

    mode: str
    lock: JsonObject | None
    resolved_root: Path | None
    executing_root: Path
    executing_validator: Path
    findings: tuple[RuntimeFinding, ...]

    @property
    def has_error(self) -> bool:
        """Return whether any ERROR finding exists (status exits 1 exactly then)."""
        return any(item.severity == FindingSeverity.ERROR for item in self.findings)

    def to_dict(self) -> JsonObject:
        """Return the JSON payload printed by ``status --json``."""
        return {
            "mode": self.mode,
            "lock": self.lock,
            "resolved_root": None if self.resolved_root is None else str(self.resolved_root),
            "executing_root": str(self.executing_root),
            "executing_validator": str(self.executing_validator),
            "findings": [item.to_dict() for item in self.findings],
        }


def _references(project: Path) -> list[Reference]:
    references: list[Reference] = []
    path_file = project / LIVESPEC_PATH_RELPATH
    try:
        text = path_file.read_text(encoding="utf-8").strip() if path_file.is_file() else ""
        if text:
            references.append((str(LIVESPEC_PATH_RELPATH), Path(text).expanduser().resolve()))
    except (OSError, UnicodeError, ValueError, RuntimeError):
        # Unreadable metadata is drift to report, not a crash that hides the diagnostics.
        references.append((str(LIVESPEC_PATH_RELPATH), path_file.absolute() / "<unreadable>"))
    for link in owned_links(project):
        references.append((link.path.relative_to(project).as_posix(), link.root.resolve()))
    return references


def _checkout_finding(root: Path, labels: list[str]) -> RuntimeFinding:
    try:
        dirty: list[str] | None = dirty_paths(root)
    except RuntimeSourceError:
        # Not a git working tree: dirtiness is unknown, so report the mutable-root warning.
        dirty = None
    names = ", ".join(labels)
    if dirty:
        return RuntimeFinding(
            "runtime_checkout_dirty",
            FindingSeverity.ERROR,
            f"runtime references ({names}) point into dirty LiveSpec checkout {root} "
            f"({len(dirty)} dirty paths)",
            str(root),
            INSTALL_HINT.format(root=root),
        )
    return RuntimeFinding(
        "runtime_checkout_reference",
        FindingSeverity.WARNING,
        f"runtime references ({names}) point into LiveSpec checkout {root}",
        str(root),
        INSTALL_HINT.format(root=root),
    )


def _checkout_findings(references: list[Reference]) -> list[RuntimeFinding]:
    grouped: dict[Path, list[str]] = {}
    for label, root in references:
        if is_livespec_root(root) and not is_snapshot_root(root):
            grouped.setdefault(root, []).append(label)
    return [_checkout_finding(root, labels) for root, labels in sorted(grouped.items())]


def _unpinned_findings(references: list[Reference]) -> list[RuntimeFinding]:
    findings = _checkout_findings(references)
    snapshots = [label for label, root in references if is_snapshot_root(root)]
    broken = [label for label, root in references if not is_livespec_root(root)]
    if snapshots:
        findings.append(
            RuntimeFinding(
                "runtime_snapshot_links_unpinned",
                FindingSeverity.WARNING,
                f"snapshot references without {LOCK_RELPATH}: {', '.join(snapshots)}",
                suggested_action="livespec runtime pin",
            )
        )
    if broken:
        findings.append(
            RuntimeFinding(
                "runtime_reference_broken",
                FindingSeverity.WARNING,
                f"runtime references point to no LiveSpec root: {', '.join(broken)}",
                suggested_action="livespec runtime pin",
            )
        )
    return findings


def _snapshot_findings(lock: LockData, home: RuntimeHome, running: Path) -> list[RuntimeFinding]:
    runtime_id = str(lock["runtime_id"])
    snapshot = home.snapshot(runtime_id).resolve()
    findings: list[RuntimeFinding] = []
    try:
        verify_snapshot(home, runtime_id, str(lock["commit"]))
    except RuntimeSnapshotError as exc:
        code = "runtime_snapshot_invalid" if snapshot.is_dir() else "runtime_snapshot_missing"
        recovery = f"livespec runtime install --source <livespec repo> --ref {lock['commit']}"
        findings.append(
            RuntimeFinding(code, FindingSeverity.ERROR, exc.message, str(snapshot), recovery)
        )
    if running != snapshot:
        findings.append(
            RuntimeFinding(
                "runtime_executing_mismatch",
                FindingSeverity.ERROR,
                f"executing LiveSpec runtime {running} is not the pinned snapshot {snapshot}",
                str(running),
                f"put {home.shim.parent} before any other livespec on PATH "
                "(for example before /opt/homebrew/bin/livespec)",
            )
        )
    return findings


def _pinned_findings(
    lock: LockData, references: list[Reference], home: RuntimeHome, running: Path
) -> list[RuntimeFinding]:
    findings = _snapshot_findings(lock, home, running)
    snapshot = home.snapshot(str(lock["runtime_id"])).resolve()
    mismatched = [(label, root) for label, root in references if root != snapshot]
    if mismatched:
        findings.append(
            RuntimeFinding(
                "runtime_reference_mismatch",
                FindingSeverity.WARNING,
                "runtime references do not match the pinned snapshot: "
                + ", ".join(f"{label} -> {root}" for label, root in mismatched),
                str(snapshot),
                f"livespec runtime pin --runtime {lock['runtime_id']}",
            )
        )
    return findings + _missing_path_findings(lock, references) + _checkout_findings(mismatched)


# @spec FR-012: Missing .livespec-path drift
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-012
def _missing_path_findings(lock: LockData, references: list[Reference]) -> list[RuntimeFinding]:
    """Warn when a pinned project lacks the machine-local ``.specs/.livespec-path``."""
    if any(label == str(LIVESPEC_PATH_RELPATH) for label, _root in references):
        return []
    return [
        RuntimeFinding(
            "runtime_reference_missing",
            FindingSeverity.WARNING,
            f"pinned project has no {LIVESPEC_PATH_RELPATH} (fresh machine or deleted file)",
            str(LIVESPEC_PATH_RELPATH),
            f"livespec runtime pin --runtime {lock['runtime_id']}",
        )
    ]


def _dev_findings(project: Path, lock: LockData) -> list[RuntimeFinding]:
    root = dev_source_root(project, str(lock["source"]))
    if is_livespec_root(root):
        return [
            RuntimeFinding("runtime_dev_mode", FindingSeverity.INFO, f"dev mode executes {root}")
        ]
    return [
        RuntimeFinding(
            "runtime_dev_source_invalid",
            FindingSeverity.ERROR,
            f"dev source in {LOCK_RELPATH} is not a LiveSpec root: {root}",
            str(root),
            "livespec runtime dev --source <checkout> or livespec runtime pin",
        )
    ]


# @spec FR-012: Runtime scanner and doctor
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-012
def runtime_findings(project: Path, home: RuntimeHome, running: Path) -> list[RuntimeFinding]:
    """Classify lock state, references and the executing runtime of one project.

    Args:
        project: Project root.
        home: Runtime home.
        running: LiveSpec root executing this scan.

    Returns:
        All applicable findings (none for a LiveSpec root or an untouched project).
    """
    # The LiveSpec repository itself is the development source: never a consumer finding.
    if is_livespec_root(project):
        return []
    lock_path = project / LOCK_RELPATH
    lock, previous = read_lock(project)
    if previous == "invalid":
        return [
            RuntimeFinding(
                "runtime_lock_invalid",
                FindingSeverity.ERROR,
                f"invalid runtime lock: {lock_path}",
                str(lock_path),
                "livespec runtime pin",
            )
        ]
    if lock is not None and lock["mode"] == "dev":
        return _dev_findings(project, lock)
    references = _references(project)
    if lock is not None:
        return _pinned_findings(lock, references, home, running.resolve())
    return _unpinned_findings(references)


def _resolved_root(project: Path, lock: LockData | None, home: RuntimeHome) -> Path | None:
    if lock is None:
        return home.current.resolve() if home.current.is_dir() else None
    if lock["mode"] == "dev":
        return dev_source_root(project, str(lock["source"]))
    return home.snapshot(str(lock["runtime_id"])).resolve()


def inspect_project(
    project: Path, home: RuntimeHome, running: Path, validator_path: Path
) -> StatusReport:
    """Build the ``livespec runtime status`` report.

    Args:
        project: Project root.
        home: Runtime home.
        running: LiveSpec root executing the status command.
        validator_path: Path of the executing ``validator`` package.

    Returns:
        The status report (mode ``pinned``, ``dev``, ``unpinned`` or ``invalid``).
    """
    lock, previous = read_lock(project)
    if previous == "invalid":
        mode, root = "invalid", None
    else:
        mode = "unpinned" if lock is None else str(lock["mode"])
        root = _resolved_root(project, lock, home)
    lock_json: JsonObject | None = None if lock is None else dict(lock)
    findings = tuple(runtime_findings(project, home, running))
    return StatusReport(mode, lock_json, root, running, validator_path, findings)
