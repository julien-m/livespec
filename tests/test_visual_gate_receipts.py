# LiveSpec traceability anchors
# @spec(AC-016)

"""CLI tests for visual-gate receipt certification."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

from typer.testing import CliRunner

from validator.cli import app
from validator.visual_evidence import verify_visual_receipt
from validator.visual_gate import certify_visual_evidence, validate_gate


def _write_png(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 4
    height = 4
    row = bytes((*color, 255)) * width
    raw = b"".join(b"\x00" + row for _ in range(height))
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def test_visual_gate_certify_writes_receipt(tmp_path: Path) -> None:
    feature = "001-visual"
    _write_png(tmp_path / ".specs/design/screens" / feature / "dash.png", (10, 20, 30))
    _write_png(
        tmp_path / ".specs/features" / feature / "run/manual/web/dash.png",
        (10, 20, 30),
    )

    result = CliRunner().invoke(
        app,
        [
            "visual-gate",
            "certify",
            "--feature",
            feature,
            "--command",
            "spec-check",
            "--target",
            "web",
            "--run-id",
            "manual",
            "--project",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    receipt_path = tmp_path / payload["receipt_path"]
    receipt = verify_visual_receipt(receipt_path, project_root=tmp_path)
    assert receipt.verdict == "PASS"


def test_visual_gate_certify_blocks_missing_runtime_capture(tmp_path: Path) -> None:
    feature = "001-visual"
    _write_png(tmp_path / ".specs/design/screens" / feature / "dash.png", (10, 20, 30))

    payload = certify_visual_evidence(
        project_root=tmp_path,
        feature_slug=feature,
        command="spec-check",
        target="web",
        run_id="manual",
    )

    assert payload["verdict"] == "BLOCKED"
    assert payload["receipt_path"] is None
    assert any("run/manual/web/dash.png" in item for item in payload["missing_artifacts"])


def test_visual_gate_certify_includes_baseline_comparisons(tmp_path: Path) -> None:
    feature = "001-visual"
    _write_png(tmp_path / ".specs/design/screens" / feature / "dash.png", (10, 20, 30))
    _write_png(
        tmp_path / ".specs/features" / feature / "run/manual/web/dash.png",
        (10, 20, 30),
    )
    _write_png(
        tmp_path / ".specs/design/baselines" / feature / "web/dash.png",
        (10, 20, 30),
    )

    payload = certify_visual_evidence(
        project_root=tmp_path,
        feature_slug=feature,
        command="spec-check",
        target="web",
        run_id="manual",
    )

    assert payload["verdict"] == "PASS"
    assert payload["comparison_count"] == 3


def test_visual_gate_validate_accepts_receipt(tmp_path: Path) -> None:
    feature = "001-visual"
    feature_dir = tmp_path / ".specs/features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "---\nvisual: true\nsurface: web\n---\n# Spec\n\n## Screens\n\n- Dash\n",
        encoding="utf-8",
    )
    _write_png(tmp_path / ".specs/design/screens" / feature / "dash.png", (10, 20, 30))
    _write_png(
        tmp_path / ".specs/features" / feature / "run/manual/web/dash.png",
        (10, 20, 30),
    )
    (tmp_path / ".specs/design/baselines" / feature / "web").mkdir(
        parents=True,
        exist_ok=True,
    )
    certify = CliRunner().invoke(
        app,
        [
            "visual-gate",
            "certify",
            "--feature",
            feature,
            "--command",
            "spec-check",
            "--target",
            "web",
            "--run-id",
            "manual",
            "--project",
            str(tmp_path),
            "--json",
        ],
    )
    receipt_path = json.loads(certify.output)["receipt_path"]

    result = CliRunner().invoke(
        app,
        [
            "visual-gate",
            "validate",
            "--feature",
            feature,
            "--command",
            "spec-check",
            "--target",
            "web",
            "--receipt",
            receipt_path,
            "--project",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "PASS"
    assert payload["visual_evidence"]["receipt_path"] == receipt_path


def test_visual_gate_validate_blocks_receipt_for_wrong_command(tmp_path: Path) -> None:
    feature = "001-visual"
    feature_dir = tmp_path / ".specs/features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "---\nvisual: true\nsurface: web\n---\n# Spec\n",
        encoding="utf-8",
    )
    _write_png(tmp_path / ".specs/design/screens" / feature / "dash.png", (10, 20, 30))
    _write_png(
        tmp_path / ".specs/features" / feature / "run/manual/web/dash.png",
        (10, 20, 30),
    )
    certify = certify_visual_evidence(
        project_root=tmp_path,
        feature_slug=feature,
        command="spec-check",
        target="web",
        run_id="manual",
    )

    report = validate_gate(
        project_root=tmp_path,
        feature_slug=feature,
        command="spec-test",
        target="web",
        strict_links=True,
        receipt_path=tmp_path / str(certify["receipt_path"]),
    )

    assert report.verdict == "BLOCKED"
    assert report.visual_evidence is not None
    assert report.visual_evidence["error"] == "command_mismatch"


def test_visual_gate_certify_blocks_loosened_threshold(tmp_path: Path) -> None:
    feature = "001-visual"
    _write_png(tmp_path / ".specs/design/screens" / feature / "dash.png", (10, 20, 30))
    _write_png(
        tmp_path / ".specs/features" / feature / "run/manual/web/dash.png",
        (10, 20, 30),
    )

    result = CliRunner().invoke(
        app,
        [
            "visual-gate",
            "certify",
            "--feature",
            feature,
            "--command",
            "spec-check",
            "--target",
            "web",
            "--run-id",
            "manual",
            "--project",
            str(tmp_path),
            "--threshold-percent",
            "100",
            "--json",
        ],
    )

    assert result.exit_code == 7, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "BLOCKED"
    assert payload["receipt_path"] is None
    assert "threshold_percent" in payload["missing_artifacts"][0]


def test_visual_gate_validate_blocks_visual_feature_without_receipt(
    tmp_path: Path,
) -> None:
    feature = "001-visual"
    feature_dir = tmp_path / ".specs/features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "---\nvisual: true\nsurface: web\n---\n# Spec\n",
        encoding="utf-8",
    )
    _write_png(tmp_path / ".specs/design/screens" / feature / "dash.png", (10, 20, 30))
    _write_png(
        tmp_path / ".specs/design/baselines" / feature / "web/dash.png",
        (20, 30, 40),
    )
    _write_png(
        tmp_path / ".specs/features" / feature / "run/manual/web/dash.png",
        (10, 20, 30),
    )

    report = validate_gate(
        project_root=tmp_path,
        feature_slug=feature,
        command="spec-check",
        target="web",
        strict_links=True,
    )

    assert report.verdict == "BLOCKED"
    assert any("visual-evidence/receipt.json" in item for item in report.missing_artifacts)
