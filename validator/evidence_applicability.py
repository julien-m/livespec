"""Explicit task predicates over approved feature artifacts (078 FR-009)."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from pathlib import Path
from typing import Any


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
_ABSENT = {"n/a", "not applicable", "not run", "none", "—", "-"}


def _command_rows(commands: str) -> list[tuple[str, str]]:
    """Read action/command cells; command arguments never declare a suite."""
    rows = []
    fenced = False
    for line in commands.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        if fenced:
            continue
        cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
        cells = [cell.strip().strip("`").replace("\\|", "|") for cell in cells]
        if len(cells) < 2 or cells[0].casefold() == "action":
            continue
        if re.fullmatch(r":?-{3,}:?", cells[0]):
            continue
        rows.append((cells[0], cells[1]))
    return rows


def _action_suites(action: str) -> set[str] | None:
    """Classify declared purposes; unknown execution actions stay unresolved."""
    text = " ".join(action.casefold().split())
    explicit = {name for name in ("unit", "integration", "e2e") if re.search(rf"\b{name}\b", text)}
    if explicit:
        return explicit
    non_test = (
        r"\b(?:lint|format(?:ting)?|types?|type[- ]?check(?:s|ing)?|"
        r"static (?:analysis|checks?)|install(?:ation)?|build|bootstrap|"
        r"(?:package|code) generation|conventions?)\b"
    )
    if re.search(non_test, text) or text in {"spec", "spec validation"}:
        return set()
    if re.search(r"^focused\b|\b(?:tests?|regressions?|compatibility)\b", text):
        return {"unit"}
    return None


def _declares_command(commands: str, token: str) -> bool:
    """Require an action declaration, retaining unresolved commands conservatively."""
    return any(
        command.casefold() not in _ABSENT
        and ((labels := _action_suites(action)) is None or token in labels)
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
        plan = (root / ".specs/features" / feature / "plan.md").read_text()
        commands = []
        for action, command in _command_rows(section(plan, "Resolved Test Commands") or ""):
            if command.casefold() in _ABSENT:
                continue
            labels = _action_suites(action)
            if labels is None:
                raise ValueError(f"suite_action_unresolved:{action}")
            if not labels or (suite != "all" and suite not in labels):
                continue
            match = re.search(r"\s+\(([^()]+)\)$", command)
            cwd = root if not match or match[1] == "root" else root / match[1]
            text = command[: match.start()] if match else command
            commands.append(_command_key(root, shlex.split(text.strip("`")), cwd))
        if not commands:
            raise ValueError("suite_commands_missing")
        return {
            "suite": suite,
            "plan_sha256": hashlib.sha256(plan.encode()).hexdigest(),
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
    name = "spec.md" if predicate == "behavioral-ac" else "plan.md"
    path = root / ".specs/features" / feature / name
    if not path.is_file():
        return {"predicate": predicate, "applicable": True, "reason": "prerequisite_missing"}
    text = path.read_text(encoding="utf-8")
    if predicate == "behavioral-ac":
        applicable = section(text, "Behavioral AC") is not None
    else:
        commands = section(text, "Resolved Test Commands")
        if commands is None:
            return {"predicate": predicate, "applicable": True, "reason": "test_discovery_required"}
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
