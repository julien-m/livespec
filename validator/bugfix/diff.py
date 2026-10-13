"""Read-only git view of the bugfix diff against a base revision (feature 084 FR-004, FR-006)."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Matches LiveSpec bookkeeping files that a bugfix updates for traceability only:
# global registries, runner-owned receipts, and per-feature maps, changelogs, state
# files, checks and reviews.
_TRACEABILITY = re.compile(
    r"^\.specs/(?:changelog\.md|README\.md|\.execution/.+"
    r"|features/[^/]+/(?:implementation\.md|changelog\.md|progress\.md|pipeline\.md"
    r"|checks/.+|\.reviews/.+))$"
)
# Generous bound for local read-only git queries; a hung git must not hang the gate.
_GIT_TIMEOUT_SECONDS = 60


class DiffUnavailableError(RuntimeError):
    """The project is not a git work tree or the base revision does not resolve."""


@dataclass(frozen=True)
class DiffEntry:
    """One path of the bugfix diff with its added and deleted line counts."""

    path: str
    added: int
    deleted: int
    binary: bool

    @property
    def lines(self) -> int:
        """Return added plus deleted lines."""
        return self.added + self.deleted


def is_traceability_artifact(path: str) -> bool:
    """Return True for LiveSpec bookkeeping paths excluded from the counted diff."""
    return bool(_TRACEABILITY.match(path))


def _git(root: Path, *args: str) -> bytes:
    # Contract: read-only queries with optional locks disabled, so the index is
    # never written; a non-zero exit or missing git means the diff is unavailable.
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(root), *args],
            capture_output=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiffUnavailableError(f"git {' '.join(args)} failed: {exc}") from exc
    if completed.returncode != 0:
        message = completed.stderr.decode(errors="replace").strip()
        raise DiffUnavailableError(f"git {' '.join(args)} failed: {message}")
    return completed.stdout


def resolve_commit(root: Path, base: str) -> str:
    """Return the full commit id of ``base``.

    Raises:
        DiffUnavailableError: Not a work tree, or ``base`` resolves to no commit.
    """
    return _git(root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").decode().strip()


# @spec FR-006: Bugfix diff collection
#   — .specs/features/084-bugfix-lane/spec.md#fr-006
def collect_diff(root: Path, base: str) -> list[DiffEntry]:
    """Return tracked changes versus `base` (staged or not) plus untracked non-ignored files.

    Raises:
        DiffUnavailableError: Not a work tree, or `base` resolves to no commit.
    """
    _git(root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    entries: dict[str, DiffEntry] = {}
    # --relative keeps paths project-relative (and scoped) when .specs/ lives in a
    # subdirectory of a larger repository, matching ls-files and receipt manifests.
    numstat = _git(root, "diff", "--numstat", "-z", "--no-renames", "--relative", base, "--")
    for record in numstat.split(b"\0"):
        if not record:
            continue
        added, deleted, path = record.decode().split("\t", 2)
        binary = added == "-" or deleted == "-"
        entries[path] = DiffEntry(
            path, 0 if binary else int(added), 0 if binary else int(deleted), binary
        )
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
    for raw in untracked.split(b"\0"):
        if raw:
            path = raw.decode()
            entries[path] = _untracked_entry(root, path)
    return [entries[path] for path in sorted(entries)]


def _untracked_entry(root: Path, path: str) -> DiffEntry:
    data = (root / path).read_bytes()
    if b"\0" in data:
        return DiffEntry(path, 0, 0, True)
    return DiffEntry(path, len(data.decode(errors="replace").splitlines()), 0, False)


def base_text(root: Path, base: str, path: str) -> str | None:
    """Return the text of `path` at `base`, or None when it did not exist there."""
    try:
        # `<rev>:./<path>` resolves relative to the project root, not the repository top.
        return _git(root, "show", f"{base}:./{path}").decode(errors="replace")
    except DiffUnavailableError:
        return None


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    """True when ``ancestor`` is ``descendant`` or one of its ancestors."""
    try:
        _git(root, "merge-base", "--is-ancestor", ancestor, descendant)
    except DiffUnavailableError:
        return False
    return True


def default_branch_commit(root: Path) -> str | None:
    """Commit of the remote default branch, else local `main` or `master`, else None."""
    for name in ("refs/remotes/origin/HEAD", "refs/heads/main", "refs/heads/master"):
        try:
            return resolve_commit(root, name)
        except DiffUnavailableError:
            continue
    return None
