"""Explicit task predicates over approved feature artifacts (078 FR-009)."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from pathlib import Path
from typing import Any

from .normative_identity import normative_hash


def section(text: str, title: str) -> str | None:
    """Read one exact level-two heading outside fenced examples."""
    active = False
    fenced = False
    lines: list[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            if active:
                break
            active = line[3:].strip() == title
            continue
        if active:
            lines.append(line)
    return "\n".join(lines) if active else None


# @spec FR-009: Explicit execution applicability
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-009
_ABSENT = {
    "n/a",
    "n/a — no ui",
    "not applicable",
    "not run",
    "none",
    "—",
    "-",
    "not applicable to bootstrap fixtures",
}


def _is_absent(command: str) -> bool:
    """Accept only closed positive forms; every other qualifier stays required."""
    return command.casefold().strip() in _ABSENT


def _resolved_commands(root: Path, feature: str) -> tuple[Path, str, str] | None:
    """Prefer an explicit plan section, otherwise use the approved testing strategy."""
    for path in [
        root / ".specs/features" / feature / "plan.md",
        root / ".specs/testing/strategy.md",
    ]:
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            commands = section(text, "Resolved Test Commands")
            if commands is not None:
                return path, text, commands
    return None


def _fenced_action(command: str) -> str:
    """Exclude only positive direct quality commands; every unknown invocation stays required."""
    try:
        if any(char in command for char in ";|<>$`#") or re.search(r"(?<!&)&(?!&)", command):
            return "Declared command"
        parts = [shlex.split(part) for part in command.split("&&")]
        if all(
            part
            and (
                part[0] in {"pyright", "mypy"}
                or part[:2] in [["ruff", "check"], ["ruff", "format"]]
            )
            for part in parts
        ):
            return "Static quality"
    except ValueError:
        pass
    return "Declared command"


def _command_rows(commands: str) -> list[tuple[str, str]]:
    """Read named table cells and fenced invocations without inferring suites from argv."""
    rows = []
    fence = ""
    action_column, command_column = 0, 1
    for line in commands.splitlines():
        stripped = line.strip()
        if fence and re.fullmatch(re.escape(fence[0]) + "{" + str(len(fence)) + ",}", stripped):
            fence = ""
            continue
        opening = re.fullmatch(r"(`{3,}|~{3,})(?:[A-Za-z0-9_+-]+)?", stripped)
        if not fence and opening:
            fence = opening[1]
            continue
        if fence:
            if stripped and not stripped.startswith("#"):
                rows.append((_fenced_action(stripped), stripped))
            continue
        cells = re.split(r"(?<!\\)\|", stripped.strip("|"))
        cells = [cell.strip().strip("`").replace("\\|", "|") for cell in cells]
        if len(cells) < 2:
            continue
        names = [re.sub(r"\s+\([^()]*\)$", "", cell.casefold()) for cell in cells]
        purpose = [i for i, name in enumerate(names) if name in {"action", "purpose"}]
        if "command" in names and len(purpose) == 1:
            action_column, command_column = purpose[0], names.index("command")
            continue
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        if max(action_column, command_column) >= len(cells):
            rows.append(("Unresolved command table row", line.strip()))
            continue
        rows.append((cells[action_column], cells[command_column]))
    return rows


def _action_suites(action: str) -> set[str]:
    """Classify explicit suites; every remaining test purpose stays required as unit."""
    text = " ".join(action.casefold().split())
    if re.match(r"^(?:install|build|bootstrap)\b", text) and not re.search(
        r"\b(?:tests?|suites?)\b", text
    ):
        return set()
    explicit = {name for name in ("unit", "integration", "e2e") if re.search(rf"\b{name}\b", text)}
    if explicit:
        return explicit
    non_test = (
        r"\b(?:lint|format(?:ting)?|types?|type[- ]?check(?:s|ing)?|"
        r"quality|static(?: (?:analysis|checks?))?|install(?:ation)?|build|bootstrap|"
        r"(?:package|code) generation|conventions?|structural (?:validation|spec check)|"
        r"(?:ts|typescript) checks?|doc(?:umentation)? grep|(?:command|docs?) file modified|"
        r"zero \w+ changes|untouched gate)\b"
    )
    if re.search(non_test, text) or text in {"spec", "spec validation"}:
        return set()
    return {"unit"}


def _declares_command(commands: str, token: str) -> bool:
    """Require an action declaration, retaining unresolved commands conservatively."""
    return any(
        not _is_absent(command) and token in _action_suites(action)
        for action, command in _command_rows(commands)
    )


# @spec FR-011: Preserve custom execution without fabricated proof.
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-011
def _command_key(root: Path, argv: list[str], cwd: Path, *, alias: bool = True) -> list[str]:
    """Normalize supported real aliases without executing scripts or inventing selections."""
    from .execution_cargo_command import is_cargo, parse_cargo_test
    from .execution_runner import _pytest_args
    from .execution_vitest import is_vitest

    cwd = cwd.resolve(strict=True)
    cwd.relative_to(root)
    if not argv or not argv[0].strip():
        raise ValueError("suite_command_unresolved")
    if argv[0] == "npm" and alias:
        if argv != ["npm", "test"] and not (len(argv) == 3 and argv[1] == "run"):
            raise ValueError("suite_npm_arguments_require_explicit_resolved_command")
        name = argv[2] if argv[1] == "run" else "test" if argv[1:] == ["test"] else ""
        scripts = json.loads((cwd / "package.json").read_text())["scripts"]
        if any(prefix + name in scripts for prefix in ("pre", "post")):
            raise ValueError("suite_npm_lifecycle_requires_explicit_resolved_command")
        script = scripts[name]
        if re.search(r"[;&|`$<>\r\n#*?\[\]{}()!~]", script):
            raise ValueError("suite_script_requires_explicit_resolved_command")
        resolved = shlex.split(script)
        if not resolved or resolved[0] != "vitest":
            raise ValueError("suite_npm_script_requires_literal_local_vitest")
        return _command_key(root, resolved, cwd, alias=False)
    if argv[0] == "vitest" and alias:
        raise ValueError("suite_direct_vitest_requires_explicit_resolved_command")
    if argv[0] == "vitest" or is_vitest(argv):
        return _vitest_command_key(root, argv, cwd)
    if is_cargo(argv):
        parse_cargo_test(argv)
        import os
        import shutil

        candidate = str(cwd / argv[0]) if "/" in argv[0] else argv[0]
        search = os.pathsep.join(str(cwd / entry) for entry in os.get_exec_path())
        program = shutil.which(candidate, path=search)
        if program is None:
            raise ValueError("suite_cargo_proxy_unresolved")
        return ["cargo", str(Path(program).absolute()), cwd.relative_to(root).as_posix(), *argv[1:]]
    args = _pytest_args(argv)
    if args is not None:
        return ["pytest", cwd.relative_to(root).as_posix(), *args]
    # Identity does not grant an assertion adapter: custom commands still execute
    # through the existing boundary, whose observed-proof check precedes matching.
    return ["opaque", cwd.relative_to(root).as_posix(), *argv]


def _vitest_command_key(root: Path, argv: list[str], cwd: Path) -> list[str]:
    """Keep direct transport identity; only the literal Vitest alias leaves Node unspecified."""
    import os
    import shutil

    from .execution_vitest import _selection

    alias = argv[0] == "vitest"
    raw = ["node", str(cwd / "node_modules/vitest/vitest.mjs"), *argv[1:]] if alias else argv
    package, config, selected = _selection(raw, root, cwd)
    modules = (package / "node_modules").resolve(strict=True)
    cli = (cwd / raw[1]).resolve(strict=True)
    if not modules.is_relative_to(package) or cli != (modules / "vitest/vitest.mjs").resolve(
        strict=True
    ):
        raise ValueError("suite_requires_selected_package_local_vitest_entry")
    shim = cwd / "node_modules/.bin/vitest"
    if alias and (not shim.is_file() or shim.resolve(strict=True) != cli):
        raise ValueError("suite_npm_vitest_shim_requires_canonical_local_entry")
    candidate = str(cwd / raw[0]) if "/" in raw[0] else raw[0]
    search = os.pathsep.join(str(cwd / entry) for entry in os.get_exec_path())
    executable = shutil.which(candidate, path=search) if not alias else None
    transport = "native-node22"
    if not alias:
        if executable is None:
            raise ValueError("suite_direct_node_executable_unresolved")
        transport = str(Path(executable).resolve(strict=True))
    return [
        "vitest",
        transport,
        cli.relative_to(root).as_posix(),
        cwd.relative_to(root).as_posix(),
        package.relative_to(root).as_posix(),
        config.relative_to(root).as_posix() if config else "",
        *selected,
        "config-sha256",
        hashlib.sha256(config.read_bytes()).hexdigest() if config else "",
        "package-sha256",
        hashlib.sha256((package / "package.json").read_bytes()).hexdigest(),
    ]


def suite_binding(root: Path | None, feature: str | None, suite: str) -> dict[str, Any]:
    """Freeze plan bytes and every applicable command/selection in canonical goal JSON."""
    try:
        if root is None or not feature or suite not in {"unit", "integration", "e2e", "all"}:
            raise ValueError("suite_context_unresolved")
        plan_path = root / ".specs/features" / feature / "plan.md"
        plan = plan_path.read_text() if plan_path.is_file() else ""
        resolved = _resolved_commands(root, feature)
        if resolved is None:
            raise ValueError("suite_commands_missing")
        source, source_text, declared = resolved
        commands = []
        for action, command in _command_rows(declared):
            if _is_absent(command):
                continue
            labels = _action_suites(action)
            if not labels or (suite != "all" and suite not in labels):
                continue
            match = re.search(r"\s+\(([^()]+)\)$", command)
            cwd = root if not match or match[1] == "root" else root / match[1]
            command_text = command[: match.start()] if match else command
            commands.append(_command_key(root, shlex.split(command_text.strip("`")), cwd))
        if not commands:
            raise ValueError("suite_commands_missing")
        return {
            "suite": suite,
            "plan_sha256": normative_hash(plan, lifecycle_document=True),
            "commands_source": source.relative_to(root).as_posix(),
            "commands_source_sha256": (
                normative_hash(source_text, lifecycle_document=True)
                if source == plan_path
                else hashlib.sha256(source_text.encode()).hexdigest()
            ),
            "commands": commands,
        }
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        return {"suite": suite, "error": str(exc)}


def suite_evidence_missing(
    binding: dict[str, Any], receipt: Path | None, root: Path, feature: str, evidence: Any
) -> list[str]:
    """Require genuine passing receipts covering every frozen original invocation."""
    from .execution_evidence import _read_capture, verify_execution_observation
    from .execution_working_directory import capture_execution_cwd

    unsupported = [
        f"suite_assertion_adapter_unsupported:{command[2]}"
        for command in binding.get("commands", [])
        if command[0] == "opaque"
    ]
    if receipt is None:
        return ["execution_receipt_path", *unsupported]
    if binding != suite_binding(root, feature, binding["suite"]):
        return ["suite_commands_changed_recompile_required"]
    if "error" in binding:
        return ["suite_command_unresolved:" + binding["error"]]
    observed = []
    for path in [receipt, *[root / p for p in (evidence or {}).get("execution_receipt_paths", [])]]:
        result = verify_execution_observation(path, root, feature, "passed", evidence_policy="2")
        if not result.valid:
            return [*unsupported, *result.gaps]
        capture, _ = _read_capture(path.absolute(), root, feature)
        argv = capture.budget.get("scope") if capture.budget else None
        if not isinstance(argv, list) or not all(isinstance(arg, str) for arg in argv):
            return ["suite_original_command_missing"]
        from .execution_vitest import is_vitest

        if is_vitest(argv):
            node = capture.runner_provenance.get("node_path")
            if not isinstance(node, str) or not Path(node).is_absolute():
                return ["suite_actual_node_provenance_missing"]
            argv = [node, *argv[1:]]
        elif capture.runner_provenance.get("runner") == "cargo":
            cargo = capture.runner_provenance.get("cargo_path")
            if not isinstance(cargo, str) or not Path(cargo).is_absolute():
                return ["suite_actual_cargo_provenance_missing"]
            argv = [cargo, *argv[1:]]
        key = _command_key(root, argv, capture_execution_cwd(capture))
        observed.append(key)
        if key[0] == "vitest":
            # The independently verified receipt establishes native Node22 for literal npm aliases.
            observed.append([key[0], "native-node22", *key[2:]])
    return (
        []
        if not unsupported and all(command in observed for command in binding["commands"])
        else [*unsupported, "suite_commands_unproven"]
    )


def resolve_applicability(
    root: Path | None, feature: str | None, predicate: str
) -> dict[str, object]:
    """Missing prerequisites remain required; only an observed absent declaration is N/A."""
    if predicate not in {"behavioral-ac", "integration-command", "e2e-command"}:
        raise ValueError(f"unknown_evidence_applicability:{predicate}")
    if root is None or not feature:
        return {"predicate": predicate, "applicable": True, "reason": "context_unresolved"}
    if predicate == "e2e-command":
        from .visual_gate import detect_visual_feature

        if (
            detect_visual_feature(project_root=root, feature_slug=feature).classification
            != "NON_VISUAL"
        ):
            return {
                "predicate": predicate,
                "applicable": True,
                "reason": "visual_execution_required",
            }
    path = root / ".specs/features" / feature / "spec.md"
    if predicate == "behavioral-ac":
        if not path.is_file():
            return {"predicate": predicate, "applicable": True, "reason": "prerequisite_missing"}
        text = path.read_text(encoding="utf-8")
        applicable = section(text, "Behavioral AC") is not None
    else:
        resolved = _resolved_commands(root, feature)
        if resolved is None:
            return {"predicate": predicate, "applicable": True, "reason": "test_discovery_required"}
        path, text, commands = resolved
        token = "integration" if predicate == "integration-command" else "e2e"
        # This is an explicit declaration predicate, not task-purpose inference.
        applicable = _declares_command(commands, token)
    return {
        "predicate": predicate,
        "applicable": applicable,
        "source": path.relative_to(root).as_posix(),
        "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "reason": "declared" if applicable else "not_declared",
    }
