"""Deterministic audit for LiveSpec command contracts.

# @spec FR-003: deterministic command audit
#   — .specs/features/048-command-validation-hardening/spec.md#fr-003
# @spec FR-004: command scorecard
#   — .specs/features/048-command-validation-hardening/spec.md#fr-004
# @spec FR-006: stale routing detection
#   — .specs/features/048-command-validation-hardening/spec.md#fr-006
# @spec FR-006: hyphenated naming audit
#   — .specs/features/049-command-naming-normalization/spec.md#fr-006
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .command_registry import CommandInfo, CommandNamingPolicy, discover_commands
from .expectations import ExpectationsInvalid, parse_expectations


@dataclass(frozen=True)
class AuditCheck:
    """One check inside a command audit entry."""

    name: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-safe representation."""
        return {"name": self.name, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class CommandAuditEntry:
    """Audit result for one command."""

    command: CommandInfo
    checks: tuple[AuditCheck, ...]

    @property
    def score(self) -> int:
        """Return the 0-5 score for this command."""
        if not self.passed:
            return min(4, sum(1 for check in self.checks if check.status == "PASS"))
        passed = sum(1 for check in self.checks if check.status == "PASS")
        return min(5, passed)

    @property
    def passed(self) -> bool:
        """Return True when all required checks pass."""
        return all(check.status == "PASS" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""
        return {
            "name": self.command.name,
            "canonical_slash": self.command.canonical_slash,
            "legacy_slashes": list(self.command.legacy_slashes),
            "command_path": str(self.command.command_path),
            "expectations_path": str(self.command.expectations_path),
            "score": self.score,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True)
class CommandAuditReport:
    """Full command audit report."""

    repo_root: Path
    naming_policy: CommandNamingPolicy
    entries: tuple[CommandAuditEntry, ...]

    @property
    def passed(self) -> bool:
        """Return True when every command reaches score 5."""
        return bool(self.entries) and all(entry.passed for entry in self.entries)

    @property
    def failed_count(self) -> int:
        """Return number of commands below score 5."""
        return sum(1 for entry in self.entries if not entry.passed)

    @property
    def score(self) -> int:
        """Return aggregate score, capped at 5."""
        if not self.entries:
            return 0
        return min(entry.score for entry in self.entries)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""
        return {
            "summary": {
                "repo_root": str(self.repo_root),
                "naming_policy": self.naming_policy.value,
                "commands": len(self.entries),
                "failed": self.failed_count,
                "score": self.score,
            },
            "commands": [entry.to_dict() for entry in self.entries],
        }


def audit_commands(
    repo_root: Path,
    *,
    naming_policy: CommandNamingPolicy = CommandNamingPolicy.HYPHENATED,
) -> CommandAuditReport:
    """Audit all command contracts in ``repo_root``."""
    commands_dir = repo_root / "commands"
    entries = tuple(
        _audit_command(repo_root, command, naming_policy=naming_policy)
        for command in discover_commands(commands_dir, naming_policy=naming_policy)
    )
    return CommandAuditReport(
        repo_root=repo_root,
        naming_policy=naming_policy,
        entries=entries,
    )


def _audit_command(
    repo_root: Path,
    command: CommandInfo,
    *,
    naming_policy: CommandNamingPolicy,
) -> CommandAuditEntry:
    checks = [
        _check_command_file(command),
        _check_source_filename(command),
        _check_expectations(command),
        _check_expectations_identity(command),
        _check_docs_reference(repo_root, command),
        _check_finalization_policy(repo_root, command),
        _check_naming(command, naming_policy),
    ]
    return CommandAuditEntry(command=command, checks=tuple(checks))


def _check_source_filename(command: CommandInfo) -> AuditCheck:
    expected_command = f"{command.name}.md"
    expected_expectations = f"{command.name}.expectations.md"
    if command.command_path.name != expected_command:
        return AuditCheck(
            "source_filename",
            "FAIL",
            f"expected commands/{expected_command}",
        )
    if command.expectations_path.name != expected_expectations:
        return AuditCheck(
            "source_filename",
            "FAIL",
            f"expected commands/{expected_expectations}",
        )
    return AuditCheck("source_filename", "PASS", "source files match command name")


def _check_command_file(command: CommandInfo) -> AuditCheck:
    if not command.command_path.is_file():
        return AuditCheck("command_file", "FAIL", "command Markdown is missing")
    text = command.command_path.read_text(encoding="utf-8")
    if "system/anti-drift-block.md" not in text:
        return AuditCheck("command_file", "FAIL", "anti-drift import missing")
    return AuditCheck("command_file", "PASS", "command Markdown and anti-drift import exist")


def _check_expectations(command: CommandInfo) -> AuditCheck:
    if not command.expectations_path.is_file():
        return AuditCheck("expectations_file", "FAIL", "expectations sidecar missing")
    try:
        expectations = parse_expectations(command.expectations_path)
    except ExpectationsInvalid as exc:
        return AuditCheck("expectations_file", "FAIL", exc.reason)
    rules = (
        list(expectations.verify.must)
        + list(expectations.verify.may)
        + list(expectations.verify.must_not)
    )
    for branch in expectations.verify.when:
        rules.extend(branch.must)
        rules.extend(branch.may)
        rules.extend(branch.must_not)
    has_exit_code = any(rule.kind == "exit_code" for rule in rules)
    has_traceback_guard = any(
        rule.verb == "must_not"
        and rule.kind == "contains"
        and str(rule.payload) == "Traceback"
        for rule in rules
    )
    if not has_exit_code:
        return AuditCheck("expectations_file", "FAIL", "missing exit_code rule")
    if not has_traceback_guard:
        return AuditCheck("expectations_file", "FAIL", "missing must_not Traceback rule")
    return AuditCheck("expectations_file", "PASS", "expectations parse with stable guards")


def _check_expectations_identity(command: CommandInfo) -> AuditCheck:
    if not command.expectations_path.is_file():
        return AuditCheck("expectations_identity", "FAIL", "expectations sidecar missing")
    try:
        expectations = parse_expectations(command.expectations_path)
    except ExpectationsInvalid as exc:
        return AuditCheck("expectations_identity", "FAIL", exc.reason)
    if expectations.command != command.name:
        return AuditCheck(
            "expectations_identity",
            "FAIL",
            f"frontmatter command={expectations.command!r}",
        )
    return AuditCheck("expectations_identity", "PASS", "frontmatter command matches")


def _check_docs_reference(repo_root: Path, command: CommandInfo) -> AuditCheck:
    doc_paths = [
        repo_root / "commands" / "spec-hooks.md",
        repo_root / "commands" / "spec-init.md",
        repo_root / ".claude" / "rules" / "livespec-commands.md",
        repo_root / "system" / "hooks.md",
        repo_root / "system" / "spec-system.md",
        repo_root / "scripts" / "init.sh",
    ]
    existing = [path for path in doc_paths if path.is_file()]
    if not existing:
        return AuditCheck("routing_docs", "PASS", "routing docs absent in fixture")
    missing = [
        path.relative_to(repo_root).as_posix()
        for path in existing
        if command.name not in path.read_text(encoding="utf-8")
    ]
    if missing:
        return AuditCheck("routing_docs", "FAIL", f"missing in {', '.join(missing)}")
    return AuditCheck("routing_docs", "PASS", "routing docs mention command")


def _check_finalization_policy(repo_root: Path, command: CommandInfo) -> AuditCheck:
    policy_path = repo_root / "system" / "anti-drift-block.md"
    if not policy_path.is_file():
        return AuditCheck("finalization_policy", "FAIL", "anti-drift policy missing")
    text = policy_path.read_text(encoding="utf-8")
    if "livespec run finalize" not in text:
        return AuditCheck("finalization_policy", "FAIL", "run finalization policy missing")
    return AuditCheck("finalization_policy", "PASS", "run finalization policy present")


def _check_naming(
    command: CommandInfo,
    naming_policy: CommandNamingPolicy,
) -> AuditCheck:
    if naming_policy.is_canonical(command.canonical_slash):
        return AuditCheck("naming_policy", "PASS", command.canonical_slash)
    return AuditCheck("naming_policy", "FAIL", command.canonical_slash)


__all__ = [
    "AuditCheck",
    "CommandAuditEntry",
    "CommandAuditReport",
    "audit_commands",
]
