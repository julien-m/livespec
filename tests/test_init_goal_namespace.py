"""Match INIT goal evidence to official project-local installation outputs."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.verify_output import evaluate_rules

ROOT = Path(__file__).resolve().parents[1]


def _install(tmp_path: Path) -> Path:
    project = tmp_path / "installed project"
    project.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "cc-hub"
    # Keep external provider builds deterministic while exercising the official
    # installer, asset inventory, local copies and provider links as subprocesses.
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, shutil, sys\n"
        "args = sys.argv[1:]\n"
        "if args[:2] == ['skill', 'link']:\n"
        "    source = pathlib.Path(args[2]).absolute()\n"
        "    for provider in ('.claude', '.agents'):\n"
        "        path = pathlib.Path(provider) / 'skills' / source.name\n"
        "        path.parent.mkdir(parents=True, exist_ok=True)\n"
        "        path.symlink_to(source, target_is_directory=True)\n"
        "if args[:2] == ['agent', 'build']:\n"
        "    source = pathlib.Path('.agent-sync.local/agents') / args[2]\n"
        "    dist = source / 'dist'\n"
        "    dist.mkdir(exist_ok=True)\n"
        "    shutil.copyfile(source / 'prompt.md', dist / 'claude.md')\n"
        "    (dist / 'codex.toml').write_text('name = ' + repr(args[2]) + '\\n')\n"
        "if args[:2] == ['agent', 'link']:\n"
        "    source = pathlib.Path('.agent-sync.local/agents') / args[2] / 'dist'\n"
        "    for provider, suffix, built in "
        "(('.claude', '.md', 'claude.md'), ('.codex', '.toml', 'codex.toml')):\n"
        "        path = pathlib.Path(provider) / 'agents' / (args[2] + suffix)\n"
        "        path.parent.mkdir(parents=True, exist_ok=True)\n"
        "        path.symlink_to((source / built).absolute())\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/init.sh"), str(project), "--non-interactive"],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return project


def _hash_agents() -> dict[str, str]:
    return {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (ROOT / ".agent-sync/agents").rglob("*")
        if path.is_file()
    }


def _verified_paths(project: Path) -> list[str]:
    assets = ROOT / ".agent-sync"
    paths: list[str] = []
    for skill in [
        *sorted((assets / "skills").glob("spec-*")),
        assets / "skills/source-command-cli",
    ]:
        for namespace in (".agent-sync.local", ".claude", ".agents"):
            path = project / namespace / "skills" / skill.name / "SKILL.md"
            assert path.is_file(), path
            assert path.resolve() == (skill / "SKILL.md").resolve()
            paths.append(str(path))
    for agent in sorted((assets / "agents").glob("livespec-*")):
        local = project / ".agent-sync.local/agents" / agent.name
        assert local.is_dir() and not local.is_symlink()
        assert local.resolve().is_relative_to(project.resolve())
        for name in ("prompt.md", "agent.yaml"):
            path = local / name
            assert path.read_bytes() == (agent / name).read_bytes()
            paths.append(str(path))
        for provider, suffix in ((".claude", ".md"), (".codex", ".toml")):
            path = project / provider / "agents" / (agent.name + suffix)
            assert path.is_file() and path.resolve().is_relative_to(project.resolve())
            paths.append(str(path))
    assert not (project / ".agent-sync").exists()
    return paths


# @spec AC-006: INIT proof uses actual installation namespaces
#   — .specs/features/080-autonomous-from-code-recovery/spec.md#ac-006
@pytest.mark.parametrize("flags", ["", "--from-code --auto --force"])
def test_installed_namespaces_are_public_goal_provable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flags: str
) -> None:
    before = _hash_agents()
    project = _install(tmp_path)
    paths = _verified_paths(project)
    controls = tmp_path / "controls"
    controls.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(controls))
    runner = CliRunner()
    result = runner.invoke(
        app, ["goal", "render", "spec-init", "--flags", f'{flags} --dir "{project}"', "--save"]
    )
    assert result.exit_code == 0, result.output
    contract_path = next((controls / "livespec-goals").glob("*.contract.json"))
    state_path = next((controls / "livespec-goals").glob("*.state.json"))
    immutable = contract_path.read_bytes()
    contract = json.loads(immutable)
    tasks = [
        task
        for task in contract["tasks"]
        if task["id"].startswith("dod.") and ".agent-sync" in task["description"]
    ]
    assert len(tasks) == 3
    for task in tasks:
        assert ".agent-sync.local/" in task["description"], task["description"]
        assert ".agent-sync/" not in task["description"]
        proof = runner.invoke(
            app,
            [
                "goal",
                "prove",
                "--contract",
                str(contract_path),
                "--state",
                str(state_path),
                "--task",
                task["id"],
                "--evidence",
                json.dumps(
                    {
                        "output": f"Verified installed assets: {paths}",
                        "success_criteria_met": True,
                        "artifact_paths": paths,
                    }
                ),
            ],
        )
        assert proof.exit_code == 0 and "ACCEPTED" in proof.output, proof.output
    assert contract_path.read_bytes() == immutable
    assert _hash_agents() == before


def test_namespace_expectations_verify_real_outputs_and_detect_missing_local_agent(
    tmp_path: Path,
) -> None:
    project = _install(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "goal",
            "render",
            "spec-init",
            "--flags",
            f'--auto --from-code --dir "{project}"',
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    rules = json.loads(result.output)["canonical"]["verify_rules"]["must"]
    namespace_rules = [
        rule
        for rule in rules
        if rule["kind"] == "exists"
        and rule["payload"].startswith((".agent-sync", ".claude", ".agents", ".codex"))
    ]
    assert any(rule["payload"].startswith(".agent-sync.local/agents/") for rule in namespace_rules)
    report = evaluate_rules(
        {"must": namespace_rules},
        artifact={"exit_code": 0},
        active_flags=[],
        feature=None,
        project_root=project,
    )
    assert report.outcome == "success", report.to_dict()
    (project / ".agent-sync.local/agents/livespec-verifier/prompt.md").unlink()
    missing = evaluate_rules(
        {"must": namespace_rules},
        artifact={"exit_code": 0},
        active_flags=[],
        feature=None,
        project_root=project,
    )
    assert missing.outcome == "drift"
