"""A fresh autonomous bootstrap satisfies its validator, definition of done and verify contract."""

import re
import subprocess
import sys
from pathlib import Path

import yaml

from tests.test_init_recovery import ROOT, environment, execute

EXPECTATIONS = ROOT / ".agent-sync/skills/spec-init/expectations.md"
IGNORED = (
    ".specs/hooks/*.local.md",
    ".agents/skills/spec-*",
    ".claude/skills/spec-*",
    ".claude/rules/*.md",
    ".codex/agents/livespec-*.toml",
    ".specs/preflight-report.md",
    ".specs/.livespec-path",
    "test-results/",
    "playwright-report/",
)


def bootstrap(tmp_path: Path) -> tuple[Path, subprocess.CompletedProcess[str]]:
    """Initialize a fresh Python fixture through the real backend wrapper."""
    project = tmp_path / "app"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="py-cli"\nversion="1"\n')
    result = execute(project, environment(tmp_path))
    assert result.returncode == 0, result.stderr
    return project, result


def verify_contains(section: str) -> list[str]:
    """Return the base ``must contains`` needles of the spec-init verify contract."""
    block = re.search(r"## 12\. Verify Contract\s+```yaml\n(.*?)```", section, re.DOTALL)
    assert block, "spec-init verify contract missing"
    rules = yaml.safe_load(block.group(1))["verify"]["must"]
    return [rule["contains"] for rule in rules if "contains" in rule]


def test_ac008_generated_specs_pass_structural_validation(tmp_path: Path) -> None:
    project, _ = bootstrap(tmp_path)
    validated = subprocess.run(
        [sys.executable, "-m", "validator.cli", "validate", str(project / ".specs")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert validated.returncode == 0, validated.stdout + validated.stderr
    assert "ERROR" not in validated.stdout


def test_ac008_definition_of_done_artifacts_survive_the_backend(tmp_path: Path) -> None:
    project, _ = bootstrap(tmp_path)
    assert (project / ".specs/design/screens/index.md").is_file()
    assert (project / ".specs/design/changelog.md").is_file()
    ignored = (project / ".gitignore").read_text().splitlines()
    assert [pattern for pattern in IGNORED if pattern not in ignored] == []
    commands = sorted(
        f"/{path.name}" for path in (ROOT / ".agent-sync/skills").glob("spec-*") if path.is_dir()
    )
    for document in ("CLAUDE.md", "AGENTS.md"):
        text = (project / document).read_text()
        assert text.count("<!-- livespec:start -->") == 1
        assert [command for command in commands if f"`{command}`" not in text] == []
    # The installer's integration survives: read-only verification still matches the bytes.
    again = tmp_path / "again"
    again.mkdir()
    verified = execute(project, environment(again), "--verify-only")
    assert verified.returncode == 0, verified.stderr


def test_ac008_backend_stdout_carries_every_verify_contract_marker(tmp_path: Path) -> None:
    _, result = bootstrap(tmp_path)
    needles = verify_contains(EXPECTATIONS.read_text())
    assert "Penflow contract" in needles
    assert [needle for needle in needles if needle not in result.stdout] == []
    assert "Penflow contract: absent" in result.stdout
    assert "Penflow Contract Verdict: ABSENT" in result.stdout
