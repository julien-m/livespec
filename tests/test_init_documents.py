"""Documents preserve observed facts and leave unsupported business facts unknown."""

from pathlib import Path

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
