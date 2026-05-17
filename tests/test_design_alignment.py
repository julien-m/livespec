"""Tests for ui.pen-to-runtime design alignment.

# @spec FR-007: Alignment regression tests
#   — .specs/features/047-design-alignment-gate/spec.md#fr-007
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner
from validator.design_alignment import compare_contract_files

from validator.cli import app

runner = CliRunner()


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _design_payload(*, width: int = 393, padding: str = "12px 16px") -> dict:
    return {
        "screens": [
            {
                "id": "dashboard",
                "support": {
                    "width": width,
                    "height": 852,
                    "dpr": 3,
                    "orientation": "portrait",
                    "shape": "rectangular",
                    "safe_area_top": 47,
                    "header_height": 44,
                    "decorative_shell": False,
                },
                "nodes": [
                    {
                        "id": "dashboard.primary-action",
                        "name": "PrimaryButton",
                        "type": "button",
                        "bounds": {"x": 24, "y": 120, "width": 180, "height": 44},
                        "styles": {
                            "fill": "#0066FF",
                            "text_color": "#FFFFFF",
                            "font_size": 14,
                            "font_weight": 600,
                            "padding": padding,
                            "corner_radius": 6,
                        },
                        "text": "Continue",
                        "states": {"disabled": {"opacity": 0.5}},
                    }
                ],
            }
        ]
    }


def _runtime_payload(*, width: int = 393, padding: str = "12px 16px") -> dict:
    return {
        "screen": "dashboard",
        "support": {
            "width": width,
            "height": 852,
            "dpr": 3,
            "orientation": "portrait",
            "shape": "rectangular",
            "safe_area_top": 47,
            "header_height": 44,
            "decorative_shell": False,
        },
        "nodes": [
            {
                "id": "dashboard.primary-action",
                "name": "PrimaryButton",
                "type": "button",
                "bounds": {"x": 24, "y": 120, "width": 180, "height": 44},
                "styles": {
                    "fill": "#0066FF",
                    "text_color": "#FFFFFF",
                    "font_size": 14,
                    "font_weight": 600,
                    "padding": padding,
                    "corner_radius": 6,
                },
                "text": "Continue",
                "states": {"disabled": {"opacity": 0.5}},
            }
        ],
    }


def test_matching_contracts_pass_and_write_artifacts(tmp_path: Path) -> None:
    design = _write_json(tmp_path / "ui.pen", _design_payload())
    runtime = _write_json(tmp_path / "runtime.json", _runtime_payload())
    out_dir = tmp_path / "out"

    result = compare_contract_files(
        design_path=design,
        runtime_path=runtime,
        screen="dashboard",
        output_dir=out_dir,
    )

    assert result.verdict == "PASS"
    assert result.exit_code == 0
    assert result.issues == []
    assert (out_dir / "dashboard.report.md").exists()
    manifest = json.loads((out_dir / "design-alignment.manifest.json").read_text())
    assert manifest["screen"] == "dashboard"
    assert manifest["verdict"] == "PASS"
    assert manifest["design_hash"]
    assert manifest["runtime_hash"]


def test_support_mismatch_is_blocked(tmp_path: Path) -> None:
    design = _write_json(tmp_path / "ui.pen", _design_payload(width=393))
    runtime = _write_json(tmp_path / "runtime.json", _runtime_payload(width=390))

    result = compare_contract_files(
        design_path=design,
        runtime_path=runtime,
        screen="dashboard",
        output_dir=tmp_path / "out",
    )

    assert result.verdict == "BLOCKED"
    assert result.exit_code == 2
    assert any(issue.field == "support.width" for issue in result.issues)


def test_property_mismatch_fails_with_actionable_issue(tmp_path: Path) -> None:
    design = _write_json(tmp_path / "ui.pen", _design_payload(padding="12px 16px"))
    runtime = _write_json(tmp_path / "runtime.json", _runtime_payload(padding="8px 16px"))

    result = compare_contract_files(
        design_path=design,
        runtime_path=runtime,
        screen="dashboard",
        output_dir=tmp_path / "out",
    )

    assert result.verdict == "FAIL"
    assert result.exit_code == 1
    assert any(
        issue.node_id == "dashboard.primary-action" and issue.field == "styles.padding"
        for issue in result.issues
    )


def test_cli_compare_emits_json_and_exit_codes(tmp_path: Path) -> None:
    design = _write_json(tmp_path / "ui.pen", _design_payload(padding="12px 16px"))
    runtime = _write_json(tmp_path / "runtime.json", _runtime_payload(padding="8px 16px"))

    result = runner.invoke(
        app,
        [
            "design-alignment",
            "compare",
            "--design",
            str(design),
            "--runtime",
            str(runtime),
            "--screen",
            "dashboard",
            "--output-dir",
            str(tmp_path / "out"),
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "FAIL"
    assert "Design Alignment Verdict: FAIL" in payload["summary"]


def test_cli_compare_blocks_missing_runtime_contract(tmp_path: Path) -> None:
    design = _write_json(tmp_path / "ui.pen", _design_payload())

    result = runner.invoke(
        app,
        [
            "design-alignment",
            "compare",
            "--design",
            str(design),
            "--runtime",
            str(tmp_path / "missing.json"),
            "--screen",
            "dashboard",
            "--output-dir",
            str(tmp_path / "out"),
            "--json",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "BLOCKED"
