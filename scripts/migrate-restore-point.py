#!/usr/bin/env python3
"""Record or restore the restore point of a format migration (``RUN`` target of migrate.sh).

Usage:
    migrate-restore-point.py <project-dir> <livespec-dir> record <version> <scope>...
    migrate-restore-point.py <project-dir> <livespec-dir> restore <version>
"""

from __future__ import annotations

import sys
from pathlib import Path

USAGE = (
    "Usage: migrate-restore-point.py <project-dir> <livespec-dir> record <version> <scope>...\n"
    "       migrate-restore-point.py <project-dir> <livespec-dir> restore <version>"
)

# These paths are written directly by the generators, so a linked destination
# is unsafe even when the backup itself can record links without following them.
V22_WRITABLE_CHILDREN = (
    ".agent-sync/agents",
    ".agent-sync/rules",
    ".agent-sync/skills",
    ".agents/skills",
    ".claude/agents",
    ".claude/commands",
    ".claude/rules",
    ".claude/skills",
    ".codex/agents",
    ".specs/conventions/debt-report.md",
    ".specs/conventions/debt.json",
)


def _guard_writes(project: Path, version: int, scope: list[str]) -> None:
    for relative in (*scope, *(V22_WRITABLE_CHILDREN if version == 22 else ())):
        target = project / relative
        if target.is_symlink():
            raise ValueError(f"refusing linked migration destination: {relative}")


def main(argv: list[str]) -> int:
    """Run one action; exit 0 on success, 1 on a refusal, 2 on a usage error."""
    if (
        len(argv) < 4
        or argv[2] not in ("record", "restore")
        or not argv[3].isascii()
        or not argv[3].isdigit()
    ):
        print(USAGE, file=sys.stderr)
        return 2
    project, livespec, action, version = Path(argv[0]), Path(argv[1]), argv[2], int(argv[3])
    # The executing LiveSpec tree provides the module; python3 is the one on PATH.
    sys.path.insert(0, str(livespec.resolve()))
    from validator.migration_restore import RestorePointError, record, restore

    try:
        if action == "record":
            scope = argv[4:]
            _guard_writes(project, version, scope)
            outcome = record(project.resolve(), version, scope)
        else:
            outcome = restore(project.resolve(), version)
    except (RestorePointError, OSError, ValueError) as exc:
        print(f"ERROR: restore point {version}: {exc}", file=sys.stderr)
        return 1
    print(
        f"  restore point {version} {outcome.status} "
        f"({outcome.entries} entries, {outcome.removed} removed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
