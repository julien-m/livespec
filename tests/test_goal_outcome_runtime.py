"""Real stop conditions must use their caller's validator package (feature 081).

@spec FR-001, AC-002 — .specs/features/081-lightweight-outcome-goals/spec.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.goal_outcome import run_stop_condition


@pytest.mark.real_stop_condition
@pytest.mark.parametrize(
    ("argv", "expected_error"),
    [
        (["livespec", "validate", ".specs/features/001-shadow"], "spec.md"),
        (["livespec", "init-from-code", "--verify-only"], ".specs/bootstrap-profile.json"),
    ],
    ids=["validate", "init-from-code"],
)
def test_stop_condition_rejects_consumer_validator_shadow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str], expected_error: str
) -> None:
    """Reject invalid consumer artifacts even when its homonymous CLI exits zero."""
    project = tmp_path / "consumer"
    feature = project / ".specs/features/001-shadow"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Invalid spec\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        '[project]\nname = "consumer"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    shadow = project / "validator"
    shadow.mkdir()
    (shadow / "__init__.py").write_text("", encoding="utf-8")
    for module in ("cli", "init_from_code"):
        (shadow / f"{module}.py").write_text(
            "from pathlib import Path\n"
            "Path('shadow-executed').write_text('executed')\n"
            "print('SHADOW_VALIDATOR_EXECUTED')\n",
            encoding="utf-8",
        )
    monkeypatch.setenv("PYTHONPATH", str(project))

    code, output = run_stop_condition(argv, project)

    assert code != 0, output
    assert expected_error in output
    assert "SHADOW_VALIDATOR_EXECUTED" not in output
    assert not (project / "shadow-executed").exists()
