"""Documents preserve observed facts and leave unsupported business facts unknown."""

from pathlib import Path

import pytest

from tests.test_init_profile import hybrid
from validator.init_documents import render_documents, render_preflight
from validator.init_probes import ProbeResult
from validator.init_profile import detect_profile


def test_ac001_documents_have_no_invented_business_or_template(tmp_path: Path) -> None:
    hybrid(tmp_path)
    documents = render_documents(detect_profile(tmp_path))
    combined = "\n".join(documents.values())
    assert "Handy" in documents["constitution.md"]
    assert all(
        family in documents["stacks/_default.md"]
        for family in ["Rust", "Tauri", "React", "Vite", "TypeScript"]
    )
    assert "Package manager: bun" in documents["project.md"]
    assert documents["testing/strategy.md"].count("- vitest") == 1
    assert all(
        text not in combined for text in ["SaaS", "United States", "Operator", "[TBD]", "dashboard"]
    )
    assert "**Deployment:** Unknown" in combined


def test_ac003_report_records_failed_real_output() -> None:
    report = render_preflight((ProbeResult(("bun", "--version"), "", "unavailable", 127, 0.01),))
    assert "Verdict: BLOCKED" in report and "unavailable" in report
    assert "Verdict: READY" not in report


def test_bootstrap_conventions_use_configured_resource_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A worktree uses the same explicit resource configuration as CI."""
    from validator.init_from_code import _prepare_documents

    resources = tmp_path / "reference sources"
    sources = resources / "code-conventions"
    sources.mkdir(parents=True)
    for name in ("general.md", "python.md", "javascript.md", "cli.md", "stack-commands.md"):
        (sources / name).write_text("# Genuine configured source\n")
    project = tmp_path / "app"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname = "app"\nversion = "1"\n')
    monkeypatch.setenv("AIRESOURCES", str(resources))
    docs = _prepare_documents(detect_profile(project), project)
    assert str(resources) in docs[".conventions/index.md"]
    assert str(resources) in docs[".conventions/manifest.yaml"]
