"""Exercise installer containment and mutable-agent isolation with real subprocesses."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = REPO_ROOT / "scripts/sync-agent-assets.sh"
INIT_SCRIPT = REPO_ROOT / "scripts/init.sh"


def _fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    project = tmp_path / "project with spaces"
    project.mkdir()
    source = tmp_path / "livespec"
    agent = source / ".agent-sync/agents/livespec-verifier"
    agent.mkdir(parents=True)
    (agent / "prompt.md").write_text("shared prompt\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "cc-hub"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import os, pathlib, sys\n"
        "if sys.argv[1:3] == ['agent', 'build']:\n"
        "    path = pathlib.Path('.agent-sync.local/agents') / sys.argv[3]\n"
        "    (path / 'dist').mkdir(exist_ok=True)\n"
        "    (path / 'dist/codex.toml').write_text('built locally\\n')\n"
        "    (path / 'prompt.md').write_text('mutated by actual build\\n')\n"
        "if os.environ.get('SYNC_FAIL'):\n"
        "    sys.exit(23)\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    return project, source, env


def _sync(
    project: Path, source: Path, env: dict[str, str], *flags: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SYNC_SCRIPT), str(project), str(source), *flags],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        env=env,
    )


def _install(project: Path, env: dict[str, str], *flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(INIT_SCRIPT), str(project), *flags],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=env,
    )


@pytest.mark.parametrize("legacy", [False, True])
def test_agent_build_mutates_local_copy_and_preserves_shared_source(
    tmp_path: Path, legacy: bool
) -> None:
    project, source, env = _fixture(tmp_path)
    shared_agent = source / ".agent-sync/agents/livespec-verifier"
    shared_before = hashlib.sha256((shared_agent / "prompt.md").read_bytes()).hexdigest()
    local = project / ".agent-sync.local/agents/livespec-verifier"
    if legacy:
        local.parent.mkdir(parents=True)
        local.symlink_to(shared_agent, target_is_directory=True)

    result = _sync(project, source, env)

    assert result.returncode == 0, result.stderr
    assert not local.is_symlink()
    assert (local / "prompt.md").read_text() == "mutated by actual build\n"
    assert (local / "dist/codex.toml").read_text() == "built locally\n"
    assert hashlib.sha256((shared_agent / "prompt.md").read_bytes()).hexdigest() == shared_before
    assert not (shared_agent / "dist").exists()


@pytest.mark.parametrize("escape", [".agent-sync.local", ".claude", ".codex/agents", ".agents"])
def test_sync_rejects_escaping_ancestors_before_any_project_write(
    tmp_path: Path, escape: str
) -> None:
    project, source, env = _fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_text("untouched", encoding="utf-8")
    dest = project / escape
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(outside, target_is_directory=True)

    result = _sync(project, source, env)

    assert result.returncode != 0
    assert "escaping" in result.stderr.lower()
    assert sentinel.read_text() == "untouched"
    assert sorted(path.name for path in outside.iterdir()) == ["sentinel"]
    assert not (project / ".agent-sync.local/agents").exists()


def test_dry_run_creates_no_local_assets(tmp_path: Path) -> None:
    project, source, env = _fixture(tmp_path)
    result = _sync(project, source, env, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert list(project.iterdir()) == []


def test_sync_failure_propagates_without_success_claim(tmp_path: Path) -> None:
    project, source, env = _fixture(tmp_path)
    env["SYNC_FAIL"] = "1"
    result = _sync(project, source, env)
    assert result.returncode == 23
    assert "assets synced" not in result.stdout


def test_legacy_agents_root_is_detached_without_writing_shared_directory(tmp_path: Path) -> None:
    project, source, env = _fixture(tmp_path)
    local_root = project / ".agent-sync.local"
    local_root.mkdir()
    shared_root = source / ".agent-sync/agents"
    (local_root / "agents").symlink_to(shared_root, target_is_directory=True)
    result = _sync(project, source, env)
    assert result.returncode == 0, result.stderr
    assert not (local_root / "agents").is_symlink()
    assert (shared_root / "livespec-verifier/prompt.md").read_text() == "shared prompt\n"
    assert not (shared_root / "livespec-verifier/dist").exists()


@pytest.mark.parametrize("direct_shared", [False, True])
def test_known_legacy_provider_links_are_detached_safely(
    tmp_path: Path, direct_shared: bool
) -> None:
    project, source, env = _fixture(tmp_path)
    shared = source / ".agent-sync/agents/livespec-verifier"
    local = project / ".agent-sync.local/agents/livespec-verifier"
    local.parent.mkdir(parents=True)
    local.symlink_to(shared, target_is_directory=True)
    for provider, filename in [(".claude", "claude.md"), (".codex", "codex.toml")]:
        output = project / provider / "agents" / f"livespec-verifier{Path(filename).suffix}"
        output.parent.mkdir(parents=True)
        output.symlink_to((shared if direct_shared else local) / "dist" / filename)
    result = _sync(project, source, env)
    assert result.returncode == 0, result.stderr
    assert shared.joinpath("prompt.md").read_text() == "shared prompt\n"
    assert not shared.joinpath("dist").exists()
    assert not (project / ".claude/agents/livespec-verifier.md").is_symlink()
    assert not (project / ".codex/agents/livespec-verifier.toml").is_symlink()


@pytest.mark.parametrize(
    "escape",
    [
        ".agent-sync.local/agents/livespec-verifier/dist",
        ".codex/config.toml",
        ".claude/agents/livespec-verifier.md",
        "AGENTS.md",
        "CLAUDE.md",
        ".gitignore",
    ],
)
def test_sync_rejects_nested_mutable_and_integration_targets(tmp_path: Path, escape: str) -> None:
    project, source, env = _fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "existing"
    marker.write_text("before", encoding="utf-8")
    dest = project / escape
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(outside if escape.endswith("/dist") else marker)
    result = _sync(project, source, env)
    assert result.returncode != 0
    assert "escaping" in result.stderr.lower()
    assert marker.read_text() == "before"
    assert list(outside.iterdir()) == [marker]
    assert not (project / ".agent-sync.local/agents/livespec-verifier/prompt.md").exists()


def test_read_only_skill_and_rule_links_remain_supported(tmp_path: Path) -> None:
    project, source, env = _fixture(tmp_path)
    skill = source / ".agent-sync/skills/spec-init"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("immutable skill", encoding="utf-8")
    rule = source / ".agent-sync/rules/livespec/routing.md"
    rule.parent.mkdir(parents=True)
    rule.write_text("immutable rule", encoding="utf-8")
    provider_skill = project / ".agents/skills/spec-init"
    provider_skill.parent.mkdir(parents=True)
    provider_skill.symlink_to(skill, target_is_directory=True)
    result = _sync(project, source, env)
    assert result.returncode == 0, result.stderr
    assert provider_skill.is_symlink()
    assert (project / ".agent-sync.local/skills/spec-init").is_symlink()
    assert (project / ".agent-sync.local/rules/routing.md").is_symlink()
    assert rule.read_text() == "immutable rule"


@pytest.mark.parametrize("flags", [("--scope", "wrong"), ("--targets", "wrong")])
def test_invalid_scope_or_targets_rejected_before_projection(
    tmp_path: Path, flags: tuple[str, str]
) -> None:
    project, source, env = _fixture(tmp_path)
    result = _sync(project, source, env, *flags)
    assert result.returncode == 2
    assert list(project.iterdir()) == []


@pytest.mark.parametrize(
    "flags",
    [
        ("--scope", "project", "--targets", "claude"),
        ("--scope", "global", "--targets", "codex"),
        ("--scope", "all", "--targets", "all"),
    ],
)
def test_supported_scope_and_target_arguments_are_preserved(
    tmp_path: Path, flags: tuple[str, ...]
) -> None:
    project, source, env = _fixture(tmp_path)
    result = _sync(project, source, env, *flags)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("force", [False, True])
def test_installer_preview_existing_project_never_prompts_or_mutates(
    tmp_path: Path, force: bool
) -> None:
    project, _source, env = _fixture(tmp_path)
    specs = project / ".specs"
    specs.mkdir()
    sentinel = specs / "changelog.md"
    sentinel.write_text("preserved", encoding="utf-8")
    flags = ["--dry-run"]
    if force:
        flags.append("--force")
    result = _install(project, env, *flags)
    assert result.returncode == 0, result.stderr
    assert "[y/N]" not in result.stdout
    assert "installed successfully" not in result.stdout
    assert list(project.iterdir()) == [specs]
    assert list(specs.iterdir()) == [sentinel]
    assert sentinel.read_text() == "preserved"


def test_noninteractive_without_force_refuses_existing_specs_without_writes(tmp_path: Path) -> None:
    project, _source, env = _fixture(tmp_path)
    (project / ".specs").mkdir()
    result = _install(project, env, "--non-interactive")
    assert result.returncode != 0
    assert "requires --force" in result.stderr
    assert "[y/N]" not in result.stdout
    assert list((project / ".specs").iterdir()) == []


def test_installer_rejects_escape_before_creating_specs(tmp_path: Path) -> None:
    project, _source, env = _fixture(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    (project / "CLAUDE.md").symlink_to(outside)
    result = _install(project, env, "--non-interactive")
    assert result.returncode != 0
    assert "escaping" in result.stderr
    assert outside.read_text() == "outside"
    assert not (project / ".specs").exists()


def test_noninteractive_force_preserves_custom_documents_and_history(tmp_path: Path) -> None:
    project, _source, env = _fixture(tmp_path)
    preserved = [
        "constitution.md",
        "project.md",
        "changelog.md",
        "stacks/_default.md",
        "testing/strategy.md",
        "features/custom/spec.md",
        "hooks/after-init.md",
        ".runs/history.json",
    ]
    for relative in preserved:
        path = project / ".specs" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"custom {relative}\n", encoding="utf-8")
    result = _install(project, env, "--non-interactive", "--force")
    assert result.returncode == 0, result.stderr
    assert "[y/N]" not in result.stdout
    for relative in preserved:
        assert (project / ".specs" / relative).read_text() == f"custom {relative}\n"
