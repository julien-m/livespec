"""Contain bootstrap writes and preserve prior artifacts before force recovery."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from .init_profile import InitError, ObservedProfile

BACKUP_ITEMS = (
    ".specs",
    ".conventions",
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    ".git/hooks/pre-commit",
)
WRITABLE_ROOTS = (
    *BACKUP_ITEMS,
    ".livespec-backups",
    ".agent-sync.local",
    ".agents",
    ".claude",
    ".codex",
)


def guard_path(root: Path, path: Path) -> None:
    """Refuse writable paths resolving outside the selected project."""
    if not path.resolve().is_relative_to(root):
        raise InitError(f"{path}: writable path escapes selected project")


def validate_destinations(root: Path) -> None:
    """Validate artifact roots and all existing generated-artifact links before mutation."""
    for relative in WRITABLE_ROOTS:
        guard_path(root, root / relative)
    # The official hook installer appends through normal files; symlinked hooks could mutate source.
    for relative in (".git", ".git/hooks", ".git/hooks/pre-commit"):
        if (root / relative).is_symlink():
            raise InitError(f"{relative}: writable hook path symlink is unsupported")
    for relative in (".specs", ".conventions"):
        directory = root / relative
        if directory.is_dir():
            for path in directory.rglob("*"):
                guard_path(root, path)


# @spec FR-003: Preserve force recovery bytes
#   — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-003
def backup_artifacts(root: Path) -> Path:
    """Snapshot existing integration/spec/convention files without following links."""
    destination = (
        root
        / ".livespec-backups"
        / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex)
    )
    guard_path(root, destination)
    destination.mkdir(parents=True)
    for relative in BACKUP_ITEMS:
        source = root / relative
        target = destination / relative
        if source.is_symlink():
            target.symlink_to(os.readlink(source), target_is_directory=source.is_dir())
        elif source.is_dir():
            shutil.copytree(source, target, symlinks=True)
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return destination


def write_atomic(root: Path, path: Path, content: str) -> None:
    """Replace one owned destination atomically, never write through a symlink."""
    guard_path(root, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Stage beside the final file so replacement stays atomic on the same filesystem.
    descriptor, temporary = tempfile.mkstemp(prefix=".livespec-init-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def preserve_custom_block(previous: str, generated: str) -> str:
    """Retain user-authored preflight content between its established markers."""
    # Match the existing explicit customization block, without treating arbitrary text as generated.
    pattern = r"<!-- preflight:custom:start -->.*?<!-- preflight:custom:end -->"
    match = re.search(pattern, previous, flags=re.DOTALL)
    return (
        re.sub(pattern, lambda _: match.group(0), generated, flags=re.DOTALL)
        if match
        else generated
    )


def merge_integration(previous: str) -> str:
    """Replace only the LiveSpec marked section and preserve surrounding user bytes."""
    section = """<!-- livespec:start -->
## LiveSpec

Read [the specification system](.specs/spec-system.md) before any spec command or code modification.
Use `$spec-init` (Codex) or `/spec-init` (Claude) for initialization.
<!-- livespec:end -->"""
    pattern = r"<!-- livespec:start -->.*?<!-- livespec:end -->"
    if re.search(pattern, previous, flags=re.DOTALL):
        return re.sub(pattern, lambda _: section, previous, flags=re.DOTALL)
    return previous + ("\n" if previous else "") + section + "\n"


def conventions_are_valid(root: Path) -> bool:
    """Check routing sources exist before choosing to preserve existing conventions."""
    index = root / ".conventions/index.md"
    manifest = root / ".conventions/manifest.yaml"
    if not index.is_file() or not manifest.is_file():
        return False
    text = index.read_text(encoding="utf-8")
    base = re.search(r"(?:\$AIRESOURCES|ai_resources_path)\s*[`]*\s*=\s*[`]*([^`\n]+)", text)
    manifest_base = re.search(
        r"^ai_resources_path:\s*(.+)$", manifest.read_text(encoding="utf-8"), flags=re.MULTILINE
    )
    if not base or not manifest_base:
        return False
    resources = Path(base.group(1).strip())
    if resources != Path(manifest_base.group(1).strip()):
        return False
    sources: list[Path] = []
    # A route's directory prefix applies to subsequent comma-separated filenames.
    for line in text.splitlines():
        if line.startswith("→ $AIRESOURCES/"):
            entries = line.removeprefix("→ $AIRESOURCES/").split(",")
            first = Path(entries[0].strip())
            sources.extend(
                [
                    resources / first,
                    *(resources / first.parent / entry.strip() for entry in entries[1:]),
                ]
            )
    return bool(sources) and all(path.is_file() for path in sources)


def render_conventions(resources: Path, name: str) -> dict[str, str]:
    """Build minimal routing against real current source files, never guessed paths."""
    files = ("general.md", "python.md", "javascript.md", "cli.md", "stack-commands.md")
    for name_part in files:
        if not (resources / "code-conventions" / name_part).is_file():
            raise InitError(
                f"conventions source missing: {resources / 'code-conventions' / name_part}"
            )
    index = f"""# Conventions — {name}

> `$AIRESOURCES` = `{resources}`

## code [code, tests, architecture, Python, Rust, TypeScript]
→ $AIRESOURCES/code-conventions/{", ".join(files)}
"""
    manifest = (
        f"ai_resources_path: {resources}\nproject: {name}\ndomains:\n  code:\n    sources:\n"
        + "".join(f"      - code-conventions/{filename}\n" for filename in files)
    )
    return {"index.md": index, "manifest.yaml": manifest}


def observed_adr_path(profile: ObservedProfile) -> str:
    """Return the stable source-specific ADR path used by generation and verification."""
    identity = hashlib.sha256(repr(profile.sources).encode()).hexdigest()[:12]
    return f"stacks/decisions/ADR-bootstrap-{identity}.md"


def _new_registry(name: str) -> str:
    # A fresh registry has no user rows; recovery merges into existing bytes instead.
    return (
        f"# .specs — {name}\n\n"
        f"> Specification registry for {name}. "
        "All artifacts produced by LiveSpec are indexed here.\n\n"
        "## Features\n\n<!-- readme:features:start -->\n"
        "| Feature | Status |\n|---|---|\n<!-- readme:features:end -->\n\n"
        "## Architecture Decisions\n\n<!-- readme:decisions:start -->\n"
        "| ADR | Decision | Date | Status |\n|---|---|---|---|\n"
        "<!-- readme:decisions:end -->\n\n## Recent Activity\n\n"
        "<!-- readme:activity:start -->\n<!-- readme:activity:end -->\n"
    )


# @spec FR-003: Refresh metadata without losing registry history
#   — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-003
def refresh_registry(previous: str, profile: ObservedProfile) -> str:
    """Merge current observed name and ADR into generated slots, retaining other bytes.

    Args:
        previous: Existing registry including user feature, ADR and custom content.
        profile: Current observed product identity and manifest sources.
    Returns:
        Updated registry with all historical rows and custom sections retained.
    Raises:
        InitError: Existing decisions markers are incomplete or contradictory.
    """
    text = previous or _new_registry(profile.product_name)
    # Only recognized generated title/intro slots are replaced; custom prose is untouched.
    title = r"(?m)^# (?:\.specs [—-] .*|Specification Registry)$"
    text = re.sub(title, lambda _: f"# .specs — {profile.product_name}", text, count=1)
    intro = (
        r"(?m)^> Specification registry for .*?\. "
        r"All artifacts produced by LiveSpec are indexed here\.$"
    )
    replacement = f"> Specification registry for {profile.product_name}. "
    text = re.sub(
        intro,
        lambda _: replacement + "All artifacts produced by LiveSpec are indexed here.",
        text,
        count=1,
    )
    if f"# .specs — {profile.product_name}" not in text.splitlines():
        # Preserve a custom title and add a bounded owned identity slot rather than replace it.
        identity = r"<!-- init:project:start -->.*?<!-- init:project:end -->"
        block = (
            f"<!-- init:project:start -->\nObserved project: {profile.product_name}\n"
            "<!-- init:project:end -->"
        )
        text = (
            re.sub(identity, lambda _: block, text, flags=re.DOTALL)
            if re.search(identity, text, flags=re.DOTALL)
            else text + "\n" + block + "\n"
        )
    start, end = "<!-- readme:decisions:start -->", "<!-- readme:decisions:end -->"
    if start not in text and end not in text:
        text += "\n## Architecture Decisions\n\n" + start + "\n" + end + "\n"
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) > text.index(end):
        raise InitError("README registry: ambiguous or incomplete decisions markers")
    before, after = text.split(end, 1)
    if f"]({observed_adr_path(profile)})" not in before.split(start, 1)[1]:
        row = (
            f"| [Observed stack]({observed_adr_path(profile)}) | "
            f"Observed stack retention | {date.today().isoformat()} | Accepted |\n"
        )
        before += ("\n" if not before.endswith("\n") else "") + row
    return before + end + after


def verify_registry(text: str, profile: ObservedProfile) -> None:
    """Require current product identity and its observed ADR in the generated registry."""
    title = f"# .specs — {profile.product_name}"
    identity = (
        f"<!-- init:project:start -->\nObserved project: {profile.product_name}\n"
        "<!-- init:project:end -->"
    )
    if title not in text.splitlines() and identity not in text:
        raise InitError("README registry: current observed product name missing")
    start, end = "<!-- readme:decisions:start -->", "<!-- readme:decisions:end -->"
    if start not in text or end not in text or text.index(start) > text.index(end):
        raise InitError("README registry: decisions markers missing or invalid")
    decisions = text.split(start, 1)[1].split(end, 1)[0]
    if f"]({observed_adr_path(profile)})" not in decisions:
        raise InitError("README registry: current observed stack ADR missing")
