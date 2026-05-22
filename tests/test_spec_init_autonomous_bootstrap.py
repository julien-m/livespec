"""Executable regression tests for autonomous /spec-init --from-code bootstrap."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _fake_cc_hub(bin_dir: Path, log_path: Path) -> None:
    bin_dir.mkdir(parents=True)
    script = bin_dir / "cc-hub"
    script.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"${CC_HUB_LOG}\"\n",
        encoding="utf-8",
    )
    script.chmod(0o755)


def _vite_react_app(project: Path) -> None:
    (project / "src").mkdir(parents=True)
    (project / "package.json").write_text(
        """{
  "name": "proof-app",
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build"
  },
  "dependencies": {
    "@vitejs/plugin-react": "latest",
    "react": "latest",
    "react-dom": "latest",
    "typescript": "latest",
    "vite": "latest"
  },
  "devDependencies": {}
}
""",
        encoding="utf-8",
    )
    (project / "package-lock.json").write_text("{}", encoding="utf-8")
    (project / "tsconfig.json").write_text("{}", encoding="utf-8")
    (project / "src" / "App.tsx").write_text(
        "export function App() { return <main>Proof app</main>; }\n",
        encoding="utf-8",
    )


def test_from_code_autonomous_bootstrap_script_completes_vite_react(
    tmp_path: Path,
) -> None:
    project = tmp_path / "app"
    project.mkdir()
    _vite_react_app(project)

    log_path = tmp_path / "cc-hub.log"
    bin_dir = tmp_path / "bin"
    _fake_cc_hub(bin_dir, log_path)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CC_HUB_LOG"] = str(log_path)

    result = subprocess.run(
        [
            "bash",
            str(ROOT / "scripts/init-from-code-autonomous.sh"),
            str(project),
            "--timeout-seconds",
            "60",
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Autonomous from-code: enabled" in result.stdout
    assert "LiveSpec initialized" in result.stdout
    assert "Penflow Contract Verdict: ABSENT" in result.stdout
    assert (project / ".specs/spec-system.md").exists()
    assert (project / ".specs/project.md").exists()
    assert (project / ".specs/roadmap.md").exists()
    assert (project / ".specs/stacks/_default.md").read_text(
        encoding="utf-8"
    ).startswith("---\nupdated:")
    readme = (project / ".specs/README.md").read_text(encoding="utf-8")
    assert "<!-- readme:features:start -->" in readme
    assert "<!-- readme:decisions:start -->" in readme
    assert "<!-- readme:activity:start -->" in readme
    assert (project / ".specs/preflight.md").exists()
    assert (project / ".specs/preflight-report.md").exists()
    assert (project / ".specs/bootstrap-recap.md").read_text(
        encoding="utf-8"
    ).startswith("---\nstatus: completed")
    assert not (project / "bootstrap-recap.md").exists()
    assert list((project / ".specs/stacks/decisions").glob("ADR-*.md"))
    assert (project / ".specs/.livespec-path").read_text(encoding="utf-8").strip()
    assert (project / ".conventions/index.md").exists()
    assert ".specs/.livespec-path" in (project / ".gitignore").read_text(
        encoding="utf-8"
    )
    assert "skill link" in log_path.read_text(encoding="utf-8")


def test_spec_init_skill_uses_concrete_autonomous_bootstrap_command() -> None:
    body = (ROOT / ".agent-sync/skills/spec-init/SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "scripts/init-from-code-autonomous.sh" in body
    assert "bash \"$LIVESPEC_ROOT/scripts/init-from-code-autonomous.sh\" \"$PWD\"" in body
    assert "--timeout-seconds 300" in body
    assert "run this command before any manual file creation" in body
    assert "If this command exits 0, do not manually rewrite `.specs/` artifacts" in body
    assert "return immediately with the command output summary" in body
    assert "Do not call `Write`, `Edit`, or `MultiEdit` afterward" in body
