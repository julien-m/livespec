"""Static markdown verification for atomic-command hook resolver coverage.

The atomic commands `/spec-specify` and `/spec-plan` are invoked directly
by users (not only as subagents of `/spec-feature`). Their markdown
must document the full 4-level resolution chain — including Level 0
user-level integrations from `~/.config/livespec/*.md` — and reference
the `livespec hooks resolve` CLI rather than the legacy "read 3 levels"
manual instruction.

These tests parse the markdown statically and assert the contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
ATOMIC_COMMANDS: list[tuple[str, Path]] = [
    ("specify", REPO_ROOT / ".agent-sync" / "skills" / "spec-specify" / "SKILL.md"),
    ("plan", REPO_ROOT / ".agent-sync" / "skills" / "spec-plan" / "SKILL.md"),
]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("cmd,path", ATOMIC_COMMANDS)
def test_atomic_command_invokes_hooks_resolve_cli(cmd: str, path: Path) -> None:
    """The command file must reference `livespec hooks resolve` for its name."""
    text = _read(path)
    needle = f"livespec hooks resolve --event before --command {cmd}"
    assert needle in text, (
        f"{path.name} does not document `{needle}` — atomic commands must "
        f"invoke the resolver CLI so Level 0 integrations are included."
    )
    after_needle = "--event after"
    assert after_needle in text, (
        f"{path.name} does not document the `--event after` invocation."
    )


@pytest.mark.parametrize("cmd,path", ATOMIC_COMMANDS)
def test_atomic_command_documents_level_0_integrations(
    cmd: str, path: Path
) -> None:
    """The command file must mention `~/.config/livespec/` Level 0 integrations."""
    _ = cmd  # parametrized for symmetry / failure messages
    text = _read(path)
    assert "~/.config/livespec/" in text, (
        f"{path.name} does not mention Level 0 integrations path."
    )
    assert "system/integrations.md" in text, (
        f"{path.name} does not link to `system/integrations.md`."
    )


@pytest.mark.parametrize("cmd,path", ATOMIC_COMMANDS)
def test_atomic_command_documents_all_four_levels(cmd: str, path: Path) -> None:
    """The command file must enumerate all 4 levels (0 → 3) of the chain."""
    text = _read(path)
    assert "~/.config/livespec/" in text
    assert f"~/.claude/livespec/hooks/before-{cmd}.md" in text
    assert f".specs/hooks/before-{cmd}.md" in text
    assert f".specs/hooks/before-{cmd}.local.md" in text


@pytest.mark.parametrize("cmd,path", ATOMIC_COMMANDS)
def test_atomic_command_does_not_use_legacy_3_levels_phrasing(
    cmd: str, path: Path
) -> None:
    """Guard against regression to the legacy 3-level callout."""
    text = _read(path)
    legacy = f"**Read** `before-{cmd}` hooks from all 3 levels"
    assert legacy not in text, (
        f"{path.name} still contains the legacy 3-level callout — should be "
        f"replaced with the 4-level resolver-CLI callout."
    )
