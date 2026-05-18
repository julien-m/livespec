"""AC-15 — economy mode must NOT inject sub-phase integrations.

The `--economy` mode in `commands/spec-feature.md` runs specify/plan/implement
inline in the main context (no subagent spawn). Because the
anti-drift runtime directive resolves under the outer command name
(`feature`), sub-phase integrations (e.g. `commands: [specify, plan]`)
CANNOT be injected in this mode by construction.

This contract is enforced by ensuring the `--economy` paragraphs in
`commands/spec-feature.md`:

1. do NOT contain `livespec hooks resolve --event before --command specify`
2. do NOT contain `livespec hooks resolve --event before --command plan`
3. do NOT prepend a synthetic `/spec-specify` or `/spec-plan` header.

Any future modification that adds such CLI calls in the economy paths
would silently re-introduce sub-phase injection — this test prevents that.
"""

from __future__ import annotations

import re
from pathlib import Path

FEATURE_MD = Path(__file__).parent.parent / "commands" / "spec-feature.md"


def _economy_blockquote_sections() -> list[str]:
    """Extract every economy-mode blockquote (full block, not just heading line)."""
    text = FEATURE_MD.read_text(encoding="utf-8")
    # The economy notes appear as blockquotes at the top of Phase 1, 2, 3 etc.
    # Find the line matching the pattern, then accumulate all subsequent lines that
    # are part of the blockquote (start with '> ' or are blank).
    lines = text.splitlines()
    pattern = re.compile(r"^> \*\*Economy mode \(`--economy`\):?\*\*.*$")

    blockquotes = []
    i = 0
    while i < len(lines):
        if pattern.match(lines[i]):
            # Found a matching line; accumulate the blockquote
            block_lines = [lines[i]]
            i += 1
            # Continue while lines start with '> ' or are blank lines (part of blockquote)
            while i < len(lines) and (lines[i].startswith("> ") or lines[i].strip() == ""):
                block_lines.append(lines[i])
                i += 1
            blockquotes.append("\n".join(block_lines))
        else:
            i += 1

    return blockquotes


def test_economy_paragraphs_present() -> None:
    """Sanity — the economy mode blockquotes still exist."""
    paragraphs = _economy_blockquote_sections()
    assert paragraphs, "no economy mode blockquote found in commands/spec-feature.md"


def test_economy_paragraphs_do_not_call_hooks_resolve_for_subphases() -> None:
    for paragraph in _economy_blockquote_sections():
        assert "livespec hooks resolve --event before --command specify" not in paragraph
        assert "livespec hooks resolve --event before --command plan" not in paragraph
        assert "livespec hooks resolve --event before --command implement" not in paragraph
        assert "livespec hooks resolve --event before --command test" not in paragraph


def test_economy_paragraphs_do_not_prepend_subcmd_headers() -> None:
    for paragraph in _economy_blockquote_sections():
        # Economy mode may reference canonical command source files such as
        # `commands/spec-specify.md`; it must not inject a standalone slash
        # command header because no subagent prompt is spawned.
        lines = [line.strip() for line in paragraph.splitlines()]
        assert "/spec-specify" not in lines, paragraph
        assert "/spec-plan" not in lines, paragraph
        assert "/spec-implement" not in lines, paragraph
