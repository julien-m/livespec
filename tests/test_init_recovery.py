"""Real autonomous subprocess recovery preserves source, history and current identity."""

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from tests.test_init_profile import hybrid

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "scripts/init-from-code-autonomous.sh"


def tree(root: Path) -> dict[str, str]:
    """Capture all target bytes and symlink identities for read-only assertions."""
    return {
        str(path.relative_to(root)): "link:" + os.readlink(path)
        if path.is_symlink()
        else hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }


def environment(tmp: Path) -> dict[str, str]:
    """Install controlled executable version and cc-hub fixtures."""
    bindir = tmp / "bin"
    bindir.mkdir()
    for tool in ("cc-hub", "bun", "cargo", "npm"):
        path = bindir / tool
        path.write_text(
            "#!/bin/sh\n" + ("exit 0\n" if tool == "cc-hub" else f'echo "{tool} fixture-version"\n')
        )
        path.chmod(0o755)
    return dict(os.environ, PATH=str(bindir) + ":" + os.environ["PATH"])


def execute(project: Path, env: dict[str, str], *flags: str) -> subprocess.CompletedProcess[str]:
    """Execute the real wrapper with closed stdin and a bounded subprocess."""
    return subprocess.run(
        ["bash", str(BACKEND), "--dir", str(project), "--timeout-seconds", "8", *flags],
        env=env,
        text=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=12,
    )


def test_ac001_ac004_force_backup_custom_history_source_and_readonly_verify(tmp_path: Path) -> None:
    project = tmp_path / "Handy project"
    project.mkdir()
    hybrid(project)
    source = tree(project)
    env = environment(tmp_path)
    first = execute(project, env)
    assert first.returncode == 0, first.stderr
    assert "Handy" in first.stdout and "Backend complete" in first.stdout
    for path in ("features/custom/spec.md", "hooks/after-init.local.md", ".runs/history.json"):
        target = project / ".specs" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("user history")
    (project / "AGENTS.md").write_text(
        "USER PREFIX\n" + (project / "AGENTS.md").read_text() + "USER SUFFIX\n"
    )
    preflight = project / ".specs/preflight.md"
    preflight.write_text(
        preflight.read_text().replace(
            "<!-- preflight:custom:start -->",
            "<!-- preflight:custom:start -->\nCustom credentials instructions",
        )
    )
    previous = tree(project / ".specs")
    prior_conventions = tree(project / ".conventions")
    original_agents = (project / "AGENTS.md").read_bytes()
    forced = execute(project, env, "--force")
    assert forced.returncode == 0, forced.stderr
    backups = list((project / ".livespec-backups").iterdir())
    assert len(backups) == 1 and tree(backups[0] / ".specs") == previous
    assert tree(backups[0] / ".conventions") == prior_conventions
    assert (backups[0] / "AGENTS.md").read_bytes() == original_agents
    assert tree(project / ".conventions") == prior_conventions
    assert all((project / relative).is_file() for relative in source)
    assert all(tree(project)[relative] == digest for relative, digest in source.items())
    assert all(
        (project / ".specs" / path).read_text() == "user history"
        for path in ("features/custom/spec.md", "hooks/after-init.local.md", ".runs/history.json")
    )
    assert "Custom credentials instructions" in preflight.read_text()
    assert (project / "AGENTS.md").read_bytes() == original_agents
    before = tree(project)
    verification = execute(project, env, "--verify-only")
    assert verification.returncode == 0 and "read-only" in verification.stdout
    assert tree(project) == before
    repeated = execute(project, env, "--force")
    assert repeated.returncode == 0 and len(list((project / ".livespec-backups").iterdir())) == 2


@pytest.mark.parametrize("change", ["manifest", "content"])
def test_ac003_current_verification_drift_writes_nothing(tmp_path: Path, change: str) -> None:
    project = tmp_path / "app"
    project.mkdir()
    hybrid(project)
    env = environment(tmp_path)
    assert execute(project, env).returncode == 0
    target = project / ("package.json" if change == "manifest" else ".specs/project.md")
    target.write_text(target.read_text() + "\n ")
    before = tree(project)
    result = execute(project, env, "--verify-only")
    assert result.returncode != 0 and "drift" in result.stderr
    assert "LiveSpec initialized" not in result.stdout and tree(project) == before


@pytest.mark.parametrize(
    "flags",
    [("--dry-run",), ("--deep",), ("--verify-only", "--force"), ("--timeout-seconds", "nan")],
)
def test_ac003_preview_invalid_options_do_not_mutate(
    tmp_path: Path, flags: tuple[str, ...]
) -> None:
    hybrid(tmp_path)
    env = environment(tmp_path)
    before = tree(tmp_path)
    result = execute(tmp_path, env, *flags)
    assert result.returncode == 0 if flags == ("--dry-run",) else result.returncode != 0
    assert tree(tmp_path) == before
    assert "LiveSpec initialized" not in result.stdout


@pytest.mark.parametrize(
    "relative",
    [
        ".specs",
        ".conventions",
        "AGENTS.md",
        ".gitignore",
        ".claude",
        ".agents",
        ".codex",
        ".agent-sync.local",
    ],
)
def test_ac004_outside_targets_unchanged(tmp_path: Path, relative: str) -> None:
    project = tmp_path / "app"
    project.mkdir()
    hybrid(project)
    env = environment(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "original").write_text("unchanged")
    (project / relative).symlink_to(outside, target_is_directory=True)
    before = tree(outside)
    result = execute(project, env, "--force")
    assert result.returncode != 0 and "escapes" in result.stderr
    assert tree(outside) == before and not (project / ".livespec-backups").exists()


@pytest.mark.parametrize("failure", ["exit", "timeout", "missing"])
def test_ac003_failed_required_tool_no_completed_ready(tmp_path: Path, failure: str) -> None:
    project = tmp_path / "app"
    project.mkdir()
    hybrid(project)
    env = environment(tmp_path)
    bun = tmp_path / "bin/bun"
    if failure == "exit":
        bun.write_text("#!/bin/sh\necho real-rejection >&2\nexit 9\n")
    elif failure == "timeout":
        bun.write_text("#!/bin/sh\nsleep 3\n")
    else:
        bun.unlink()
        package = json.loads((project / "package.json").read_text())
        package["packageManager"] = "pnpm@1"
        (project / "package.json").write_text(json.dumps(package))
        (project / "bun.lock").unlink()
        (project / "pnpm-lock.yaml").write_text("fixture")
        (project / "src-tauri/tauri.conf.json").write_text('{"productName":"Handy"}')
        env["PATH"] = str(tmp_path / "bin") + ":/usr/bin:/bin"
    result = execute(project, env, "--timeout-seconds", "2")
    assert result.returncode != 0, result.stdout
    assert "LiveSpec initialized" not in result.stdout
    assert "status: completed" not in (project / ".specs/bootstrap-recap.md").read_text()
    assert "Verdict: READY" not in (project / ".specs/preflight-report.md").read_text()


def test_ac003_sync_stall_cancels_late_child_and_clears_prior_success(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    hybrid(project)
    env = environment(tmp_path)
    assert execute(project, env).returncode == 0
    hub = tmp_path / "bin/cc-hub"
    hub.write_text("#!/bin/sh\n(sleep 1; echo late > late-write) & wait\n")
    result = execute(project, env, "--force", "--timeout-seconds", ".3")
    assert result.returncode != 0 and "timeout" in result.stderr
    time.sleep(1.1)
    assert not (project / "late-write").exists()
    assert "status: completed" not in (project / ".specs/bootstrap-recap.md").read_text()
    assert "Verdict: READY" not in (project / ".specs/preflight-report.md").read_text()


@pytest.mark.parametrize(
    ("manifest", "content", "family", "tool"),
    [
        (
            "package.json",
            '{"name":"web","packageManager":"npm@10","devDependencies":{"vite":"6"}}',
            "Vite",
            "npm",
        ),
        ("pyproject.toml", '[project]\nname="py-cli"\nversion="1"\n', "Python", "python3"),
        ("Cargo.toml", '[package]\nname="rust-cli"\nversion="1"\n', "Rust", "cargo"),
    ],
)
def test_ac002_real_generation_standalone_families(
    tmp_path: Path, manifest: str, content: str, family: str, tool: str
) -> None:
    project = tmp_path / "app"
    project.mkdir()
    (project / manifest).write_text(content)
    env = environment(tmp_path)
    result = execute(project, env)
    assert result.returncode == 0, result.stderr
    profile = json.loads((project / ".specs/bootstrap-profile.json").read_text())["profile"]
    assert family in {fact["name"] for fact in profile["facts"]}
    assert profile["tools"] == [tool]
    assert "**Deployment:** Unknown" in (project / ".specs/project.md").read_text()
    assert "exit" not in result.stdout.lower()


def test_ac005_invalid_conventions_backed_up_and_repaired(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    hybrid(project)
    env = environment(tmp_path)
    assert execute(project, env).returncode == 0
    (project / ".conventions/index.md").write_text(
        "# bad generated routing\n→ $AIRESOURCES/conventions/code/general.md\n"
    )
    before = tree(project / ".conventions")
    result = execute(project, env, "--force")
    assert result.returncode == 0, result.stderr
    backup = next((project / ".livespec-backups").iterdir())
    assert tree(backup / ".conventions") == before
    index = (project / ".conventions/index.md").read_text()
    assert "code-conventions/general.md" in index and "/conventions/code/" not in index
    resources = Path(env.get("AIRESOURCES", str(ROOT.parent / "ai-ressources")))
    assert (resources / "code-conventions/general.md").is_file()


def test_ac003_nested_escape_refused_before_backup_or_write(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    hybrid(project)
    env = environment(tmp_path)
    (project / ".claude").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / ".claude/agents").symlink_to(outside, target_is_directory=True)
    before = tree(project)
    result = execute(project, env, "--force")
    assert result.returncode != 0 and "escape" in result.stderr
    assert tree(project) == before and not (project / ".livespec-backups").exists()
