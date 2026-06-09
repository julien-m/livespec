#!/usr/bin/env python3
# LiveSpec traceability anchors
# @spec(FR-008)
# @spec(FR-009)

"""Pre-commit hook — enforce `last_reviewed` bump on skill expectations files.

# @spec FR-009: pre-commit hook
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-009
# @spec AC-008: hook contract
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#ac-008

For each staged ``.agent-sync/skills/<X>/SKILL.md``:

* Locate ``.agent-sync/skills/<X>/expectations.md``. If missing -> block with
  a message naming the missing file.
* Read its frontmatter ``last_reviewed`` value (stdlib only — no pyyaml dep).
* If absent or != today's date -> block with the EXACT recovery string from
  AC-008.

Exit codes: 0 OK, 1 block.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

RECOVERY_FMT = "Relis `.agent-sync/skills/{name}/expectations.md`, bump `last_reviewed`, recommit."


def _staged_paths() -> list[str]:
    """Return the list of staged file paths (relative to repo root)."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            text=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _command_targets(paths: list[str]) -> list[str]:
    """Filter staged paths down to agent-sync command skill sources."""
    out: list[str] = []
    for p in paths:
        if not p.startswith(".agent-sync/skills/"):
            continue
        if not p.endswith("/SKILL.md"):
            continue
        out.append(p)
    return out


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_LAST_REVIEWED_RE = re.compile(
    r"^\s*last_reviewed\s*:\s*['\"]?(\d{4}-\d{2}-\d{2})['\"]?\s*$",
    re.MULTILINE,
)


def _read_last_reviewed(path: Path) -> str | None:
    """Parse `last_reviewed` from frontmatter (stdlib regex only)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    inner = match.group(1)
    lr = _LAST_REVIEWED_RE.search(inner)
    return lr.group(1) if lr else None


def main(argv: list[str] | None = None) -> int:
    """Hook entry point. Returns the exit code."""
    _ = argv  # unused — git supplies staged set via `--cached`.
    repo_root = _git_top_level()
    if repo_root is None:
        return 0  # not in a git repo — nothing to enforce.

    today = date.today().isoformat()
    blockers: list[str] = []

    for rel in _command_targets(_staged_paths()):
        name = Path(rel).parent.name
        exp_rel = f".agent-sync/skills/{name}/expectations.md"
        exp_path = repo_root / exp_rel
        if not exp_path.exists():
            blockers.append(
                f"✘ .agent-sync/skills/{name}/SKILL.md modified but "
                f"{exp_rel} is missing.\n"
                f"  Create it from a neighboring skill expectations.md file."
            )
            continue
        last = _read_last_reviewed(exp_path)
        if last != today:
            blockers.append(
                f"✘ .agent-sync/skills/{name}/SKILL.md modified but {exp_rel} "
                f"last_reviewed is {last} (expected {today}).\n"
                f"  " + RECOVERY_FMT.format(name=name)
            )
    if blockers:
        print("\n".join(blockers), file=sys.stderr)
        return 1
    return 0


def _git_top_level() -> Path | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, OSError):
        return None
    return Path(out) if out else None


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
