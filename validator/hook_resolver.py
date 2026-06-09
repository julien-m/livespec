# LiveSpec traceability anchors
# @spec(FR-006)

"""Hook-injection chain resolver (Level 0 → Level 1 → Level 2 → Level 3).

This module is the SINGLE source of truth for the runtime resolution of
LiveSpec hooks + Level 0 user integrations. It is consumed by:

* the runtime CLI ``livespec hooks resolve`` (invoked by command skills via
  the directive in ``system/anti-drift-block.md``);
* the diagnostic CLI ``/spec-hooks`` (tabular display of the chain).

The pseudo-code in ``plan-C.md`` Phase 2 is the implementation of reference.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, cast

import yaml

from validator.command_registry import normalize_command_name, short_command_name
from validator.integrations import (
    VALID_PHASES,
    discover_integrations,
)

GLOBAL_HOOKS_DIR = Path.home() / ".claude" / "livespec" / "hooks"
PROJECT_HOOKS_DIR_NAME = ".specs/hooks"


_TEMPLATE_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _safe_yaml_dict(block: str) -> dict[str, Any]:
    """Best-effort YAML→dict parser. Returns empty dict on any error."""
    try:
        raw: Any = yaml.safe_load(block) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(raw, dict):
        return {}
    result: dict[str, Any] = {}
    for k, v in cast(dict[Any, Any], raw).items():
        result[str(k)] = v
    return result


def _read_if_exists(path: Path) -> tuple[dict[str, Any], str] | None:
    """Read a hook file and split frontmatter / body. Returns None if missing."""
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    fm: dict[str, Any] = {}
    body = text
    m = _FRONTMATTER_RE.match(text)
    if m:
        fm = _safe_yaml_dict(m.group(1))
        body = text[m.end() :]
    return fm, body


def _read_stack_primary(cwd: Path) -> str | None:
    """Read primary stack from ``.specs/stacks/_default.md`` (best effort)."""
    candidate = cwd / ".specs" / "stacks" / "_default.md"
    if not candidate.is_file():
        return None
    try:
        text = candidate.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm = _safe_yaml_dict(m.group(1))
    for key in ("primary_stack", "stack", "name"):
        val: Any = fm.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def _read_project_name(cwd: Path) -> str | None:
    """Read project name from ``.specs/project.md`` (frontmatter or H1)."""
    candidate = cwd / ".specs" / "project.md"
    if not candidate.is_file():
        return None
    try:
        text = candidate.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _FRONTMATTER_RE.match(text)
    if m:
        fm = _safe_yaml_dict(m.group(1))
        name: Any = fm.get("name")
        if isinstance(name, str) and name:
            return name
        text = text[m.end() :]
    for line in text.splitlines():
        if line.startswith("# "):
            stripped = line[2:].strip()
            if stripped:
                return stripped
    return None


def _build_feature_ctx(
    command: str,
    feature_slug: str | None,
    cwd: Path,
) -> dict[str, str]:
    """Build the template-variable substitution context.

    Variables that cannot be resolved are *omitted* from the dict — the
    ``render_template`` function leaves them literally as ``{{var}}``.
    """
    ctx: dict[str, str] = {"command": command}
    if feature_slug:
        ctx["feature_name"] = feature_slug
        m = re.match(r"^(\d{3})-", feature_slug)
        if m:
            ctx["feature_number"] = m.group(1)
        ctx["feature_path"] = f".specs/features/{feature_slug}/"
    stack = _read_stack_primary(cwd)
    if stack:
        ctx["stack"] = stack
    project_name = _read_project_name(cwd) or cwd.name
    ctx["project_name"] = project_name
    return ctx


def render_template(text: str, ctx: dict[str, str]) -> str:
    """Substitute ``{{var}}`` placeholders from ``ctx``; leave unknowns intact."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return ctx.get(key, match.group(0))

    return _TEMPLATE_VAR_RE.sub(repl, text)


def resolve_injection_chain(
    event: str,
    command: str,
    feature_ctx: dict[str, str] | None = None,
    *,
    integrations_dir: Path | None = None,
    global_hooks_dir: Path | None = None,
    project_root: Path | None = None,
    commands_dir: Path | None = None,
) -> list[str]:
    """Resolve the full ordered chain of bodies to inject for ``event-command``.

    Returns the list of rendered (template-substituted) markdown bodies in
    the order: Level 0 (user integrations) → Level 1 (global) → Level 2
    (project) → Level 3 (local).

    Mode rules:
    * ``override`` at Level 0 → only that L0 file is kept (L1/L2/L3 still injected).
    * ``override`` at Level 3 → only L3 is kept among L1/L2/L3 (L0 still injected).
    """
    if event not in VALID_PHASES:
        raise ValueError(f"event must be one of {sorted(VALID_PHASES)}, got: {event!r}")
    command = normalize_command_name(command)

    cwd = project_root if project_root is not None else Path.cwd()
    ctx = feature_ctx if feature_ctx is not None else _build_feature_ctx(command, None, cwd)

    # --- Level 0 -----------------------------------------------------------
    all_l0 = discover_integrations(
        integrations_dir=integrations_dir,
        commands_dir=commands_dir,
    )
    l0_matching = [i for i in all_l0 if i.applies_to(event, command)]

    overrides = [i for i in l0_matching if i.mode == "override"]
    if len(overrides) > 1:
        paths = ", ".join(str(o.path) for o in overrides)
        raise ValueError(f"Multiple override integrations for event {event}-{command}: {paths}")

    l0_bodies = [overrides[0].body] if overrides else [i.body for i in l0_matching]

    # --- Level 1/2/3 -------------------------------------------------------
    global_dir = global_hooks_dir if global_hooks_dir is not None else GLOBAL_HOOKS_DIR
    hook_name = short_command_name(command)
    l1 = _read_if_exists(global_dir / f"{event}-{hook_name}.md")
    project_hooks = cwd / PROJECT_HOOKS_DIR_NAME
    l2 = _read_if_exists(project_hooks / f"{event}-{hook_name}.md")
    l3 = _read_if_exists(project_hooks / f"{event}-{hook_name}.local.md")

    higher_chain: list[str] = []
    if l3 is not None and l3[0].get("mode") == "override":
        higher_chain = [l3[1]]
    else:
        for entry in (l1, l2, l3):
            if entry is not None:
                higher_chain.append(entry[1])

    chain = l0_bodies + higher_chain
    return [render_template(text, ctx) for text in chain]


def render_chain_for_stdout(
    event: str,
    command: str,
    feature_slug: str | None = None,
    *,
    integrations_dir: Path | None = None,
    global_hooks_dir: Path | None = None,
    project_root: Path | None = None,
    commands_dir: Path | None = None,
) -> str:
    """Concatenate the chain with ``\\n\\n---\\n\\n`` separators for stdout emission.

    Returns the empty string when no fragment applies — exit code stays 0
    (absence-tolerance contract).
    """
    cwd = project_root if project_root is not None else Path.cwd()
    command = normalize_command_name(command)
    ctx = _build_feature_ctx(command, feature_slug, cwd)
    chain = resolve_injection_chain(
        event,
        command,
        feature_ctx=ctx,
        integrations_dir=integrations_dir,
        global_hooks_dir=global_hooks_dir,
        project_root=cwd,
        commands_dir=commands_dir,
    )
    return "\n\n---\n\n".join(chain)


__all__ = [
    "GLOBAL_HOOKS_DIR",
    "PROJECT_HOOKS_DIR_NAME",
    "render_chain_for_stdout",
    "render_template",
    "resolve_injection_chain",
]
