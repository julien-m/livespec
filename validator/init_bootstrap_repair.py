"""Repair bootstrap artifacts generated before the self-consistency correction (migration v23)."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

from .init_recovery import merge_integration, write_atomic

LIVESPEC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ".specs/bootstrap-profile.json"
LEGACY_HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2}) — LiveSpec initialized$", re.MULTILINE)
TOKENS_SECTION = "## Tokens\n\nUnknown. No application token or credential inferred.\n\n"
IGNORE_PATTERNS = (
    ".specs/hooks/*.local.md",
    ".agents/skills/spec-*",
    ".claude/skills/spec-*",
    ".claude/rules/*.md",
    ".codex/agents/livespec-*.toml",
    ".specs/.livespec-path",
    ".specs/.runs/",
    ".specs/preflight-report.md",
    "test-results/",
    "playwright-report/",
)
DESIGN_TEMPLATES = {
    ".specs/design/screens/index.md": "system/templates/screen-index-template.md",
    ".specs/design/changelog.md": "system/templates/design-changelog-template.md",
}
LIVESPEC_BLOCK = re.compile(r"<!-- livespec:start -->.*?<!-- livespec:end -->", re.DOTALL)


def _changelog(text: str) -> str:
    return LEGACY_HEADING.sub(r"## \1 — [Setup]: LiveSpec initialized", text)


def _preflight(text: str) -> str:
    headings = re.findall(r"^#{1,6} (.+)$", text, flags=re.MULTILINE)
    if any(
        word in heading.lower()
        for heading in headings
        for word in ("tokens", "credentials", "keys")
    ):
        return text
    marker = "<!-- preflight:custom:start -->"
    if marker in text:
        return text.replace(marker, TOKENS_SECTION + marker, 1)
    return text.rstrip("\n") + "\n\n" + TOKENS_SECTION.rstrip("\n") + "\n"


def _stack(text: str) -> str:
    if not text.startswith("---\n"):
        return f"---\ntitle: Default Stack\nupdated: {date.today().isoformat()}\n---\n\n" + text
    end = text.find("\n---\n", 3)
    if end == -1 or re.search(r"^title:", text[4:end], flags=re.MULTILINE):
        return text
    return "---\ntitle: Default Stack\n" + text[4:]


def _instructions(text: str) -> str:
    block = LIVESPEC_BLOCK.search(text)
    # Only the command-less block an older backend wrote is replaced; custom blocks stay.
    if block is None or "Commands:" in block.group(0):
        return text
    commands = tuple(
        path.name for path in (LIVESPEC_ROOT / ".agent-sync/skills").glob("spec-*") if path.is_dir()
    )
    return merge_integration(text, commands)


def _gitignore(text: str) -> str:
    lines = text.splitlines()
    missing = [pattern for pattern in IGNORE_PATTERNS if pattern not in lines]
    if not missing:
        return text
    return text + ("\n" if text and not text.endswith("\n") else "") + "\n".join(missing) + "\n"


REPAIRS = {
    ".specs/changelog.md": _changelog,
    ".specs/preflight.md": _preflight,
    ".specs/stacks/_default.md": _stack,
    "CLAUDE.md": _instructions,
    "AGENTS.md": _instructions,
    ".gitignore": _gitignore,
}


# @spec FR-006: Migration v23 repairs earlier bootstrap artifacts
#   — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-006
def repair_bootstrap(project: Path) -> list[str]:
    """Bring earlier bootstrap artifacts to the validated form; idempotent.

    Args:
        project: Initialized LiveSpec project root.
    Returns:
        Relative paths created or changed, in a stable order.
    """
    root = project.resolve()
    changed: list[str] = []
    for relative, repair in REPAIRS.items():
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        repaired = repair(text)
        if repaired != text:
            mode = path.stat().st_mode & 0o7777
            write_atomic(root, path, repaired)
            path.chmod(mode)  # the atomic temporary file would otherwise leave 0600
            changed.append(relative)
    for relative, template in DESIGN_TEMPLATES.items():
        path = root / relative
        if not path.exists():
            write_atomic(root, path, (LIVESPEC_ROOT / template).read_text(encoding="utf-8"))
            changed.append(relative)
    _refresh_profile(root, changed)
    return changed


def _refresh_profile(root: Path, changed: list[str]) -> None:
    """Keep autonomous --verify-only current for the documents this migration rewrote."""
    path = root / MANIFEST
    if not path.is_file():
        return
    mode = path.stat().st_mode & 0o7777
    manifest = json.loads(path.read_text(encoding="utf-8"))
    documents = manifest.get("documents")
    if not isinstance(documents, dict):
        return
    touched = [relative for relative in changed if relative in documents]
    for relative in touched:
        documents[relative] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    if touched:
        write_atomic(root, path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        path.chmod(mode)


def main(argv: list[str] | None = None) -> int:
    """Repair the project given as first argument and report each changed path."""
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("Usage: python -m validator.init_bootstrap_repair <project-dir>", file=sys.stderr)
        return 2
    changed = repair_bootstrap(Path(args[0]))
    for relative in changed:
        print(f"  repaired {relative}")
    if not changed:
        print("  bootstrap artifacts already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
