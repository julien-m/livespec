"""Static tests for conventions migration v22 and enforcement docs."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def test_migration_v22_manifest_contains_required_steps() -> None:
    text = _text("migrations/22/migrate.md")

    required = [
        "SET_VERSION 22",
        "RUN migrate-agent-sync.sh",
        "RUN migrate-conventions-gates-init.sh",
        "RUN migrate-conventions-compile.sh",
        "RUN migrate-conventions-scaffold.sh",
        "RUN migrate-conventions-first-verify.sh",
    ]
    for step in required:
        assert step in text


def test_migration_v22_sets_version_after_all_run_steps() -> None:
    text = _text("migrations/22/migrate.md")
    instructions = [
        line.strip() for line in text.splitlines() if line.startswith(("RUN ", "SET_VERSION "))
    ]

    assert instructions[-1] == "SET_VERSION 22"
    assert all(instruction.startswith("RUN ") for instruction in instructions[:-1])


def test_migration_v22_scripts_exist_and_are_executable() -> None:
    scripts = [
        "scripts/migrate-conventions-gates-init.sh",
        "scripts/migrate-conventions-compile.sh",
        "scripts/migrate-conventions-scaffold.sh",
        "scripts/migrate-conventions-first-verify.sh",
    ]

    for script in scripts:
        path = REPO_ROOT / script
        assert path.is_file(), f"missing script: {script}"
        assert os.access(path, os.X_OK), f"not executable: {script}"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("#!/usr/bin/env bash\n")
        assert "set -euo pipefail" in text


def test_migration_v22_scripts_use_advisory_livespec_commands() -> None:
    assert "livespec conventions gates init --force || true" in _text(
        "scripts/migrate-conventions-gates-init.sh"
    )
    assert "livespec conventions compile --force || true" in _text(
        "scripts/migrate-conventions-compile.sh"
    )
    assert "livespec conventions scaffold --apply || true" in _text(
        "scripts/migrate-conventions-scaffold.sh"
    )


def test_first_verify_uses_supported_verify_flags() -> None:
    text = _text("scripts/migrate-conventions-first-verify.sh")

    assert "--semantic-full" not in text
    assert "livespec conventions verify --report || true" in text


def test_conventions_enforcement_reference_has_required_sections() -> None:
    text = _text("system/conventions-enforcement.md")

    assert "## Architecture: Three Engines" in text
    assert "## Human Operations" in text
    assert "## Anti-Bypass Locks" in text
    assert "## CLI Reference" in text
    for engine in (
        "Engine A: Deterministic subprocess",
        "Engine B: Visual receipt",
        "Engine C: Layer 4 LLM review",
    ):
        assert engine in text
