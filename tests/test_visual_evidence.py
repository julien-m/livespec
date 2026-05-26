"""Tests for deterministic visual evidence receipts."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import pytest

from validator.visual_evidence import (
    VisualReceiptError,
    compare_visual_images,
    receipt_payload_hash,
    verify_visual_receipt,
    write_visual_receipt,
)


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


def test_visual_receipt_passes_for_identical_pngs(tmp_path: Path) -> None:
    mockup = tmp_path / ".specs/design/screens/001-visual/dash.png"
    runtime = tmp_path / ".specs/features/001-visual/run/manual/web/dash.png"
    _write_png(mockup, (20, 40, 60))
    _write_png(runtime, (20, 40, 60))

    comparison = compare_visual_images(
        project_root=tmp_path,
        feature_slug="001-visual",
        screen="dash",
        target="web",
        comparison_kind="mockup_runtime",
        reference_path=mockup,
        actual_path=runtime,
        threshold_percent=5.0,
        diff_path=tmp_path / ".specs/features/001-visual/run/manual/visual-evidence/dash.diff.png",
    )
    receipt_path = write_visual_receipt(
        project_root=tmp_path,
        feature_slug="001-visual",
        command="spec-check",
        target="web",
        run_id="manual",
        comparisons=[comparison],
        output_dir=tmp_path / ".specs/features/001-visual/run/manual/visual-evidence",
    )

    verified = verify_visual_receipt(receipt_path, project_root=tmp_path)

    assert verified.verdict == "PASS"
    assert verified.comparisons[0].actual_diff_percent == 0


def test_visual_receipt_fails_for_different_pngs(tmp_path: Path) -> None:
    mockup = tmp_path / ".specs/design/screens/001-visual/dash.png"
    runtime = tmp_path / ".specs/features/001-visual/run/manual/web/dash.png"
    _write_png(mockup, (20, 40, 60))
    _write_png(runtime, (200, 40, 60))

    comparison = compare_visual_images(
        project_root=tmp_path,
        feature_slug="001-visual",
        screen="dash",
        target="web",
        comparison_kind="mockup_runtime",
        reference_path=mockup,
        actual_path=runtime,
        threshold_percent=5.0,
        diff_path=tmp_path / ".specs/features/001-visual/run/manual/visual-evidence/dash.diff.png",
    )
    receipt_path = write_visual_receipt(
        project_root=tmp_path,
        feature_slug="001-visual",
        command="spec-check",
        target="web",
        run_id="manual",
        comparisons=[comparison],
        output_dir=tmp_path / ".specs/features/001-visual/run/manual/visual-evidence",
    )

    verified = verify_visual_receipt(receipt_path, project_root=tmp_path)

    assert verified.verdict == "FAIL"
    assert verified.comparisons[0].actual_diff_percent == 100


def test_visual_receipt_rejects_tampered_sha(tmp_path: Path) -> None:
    mockup = tmp_path / ".specs/design/screens/001-visual/dash.png"
    runtime = tmp_path / ".specs/features/001-visual/run/manual/web/dash.png"
    _write_png(mockup, (20, 40, 60))
    _write_png(runtime, (20, 40, 60))
    comparison = compare_visual_images(
        project_root=tmp_path,
        feature_slug="001-visual",
        screen="dash",
        target="web",
        comparison_kind="mockup_runtime",
        reference_path=mockup,
        actual_path=runtime,
        threshold_percent=5.0,
        diff_path=tmp_path / ".specs/features/001-visual/run/manual/visual-evidence/dash.diff.png",
    )
    receipt_path = write_visual_receipt(
        project_root=tmp_path,
        feature_slug="001-visual",
        command="spec-check",
        target="web",
        run_id="manual",
        comparisons=[comparison],
        output_dir=tmp_path / ".specs/features/001-visual/run/manual/visual-evidence",
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload["comparisons"][0]["reference_sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(VisualReceiptError, match="reference_sha256"):
        verify_visual_receipt(receipt_path, project_root=tmp_path)


def test_visual_receipt_rejects_tampered_or_missing_diff(tmp_path: Path) -> None:
    mockup = tmp_path / ".specs/design/screens/001-visual/dash.png"
    runtime = tmp_path / ".specs/features/001-visual/run/manual/web/dash.png"
    _write_png(mockup, (20, 40, 60))
    _write_png(runtime, (20, 40, 60))
    diff_path = tmp_path / ".specs/features/001-visual/run/manual/visual-evidence/dash.diff.png"
    comparison = compare_visual_images(
        project_root=tmp_path,
        feature_slug="001-visual",
        screen="dash",
        target="web",
        comparison_kind="mockup_runtime",
        reference_path=mockup,
        actual_path=runtime,
        threshold_percent=5.0,
        diff_path=diff_path,
    )
    receipt_path = write_visual_receipt(
        project_root=tmp_path,
        feature_slug="001-visual",
        command="spec-check",
        target="web",
        run_id="manual",
        comparisons=[comparison],
        output_dir=tmp_path / ".specs/features/001-visual/run/manual/visual-evidence",
    )
    diff_path.unlink()

    with pytest.raises(VisualReceiptError, match="path_missing"):
        verify_visual_receipt(receipt_path, project_root=tmp_path)


def test_visual_receipt_rejects_escaping_paths(tmp_path: Path) -> None:
    mockup = tmp_path / ".specs/design/screens/001-visual/dash.png"
    runtime = tmp_path / ".specs/features/001-visual/run/manual/web/dash.png"
    _write_png(mockup, (20, 40, 60))
    _write_png(runtime, (20, 40, 60))
    comparison = compare_visual_images(
        project_root=tmp_path,
        feature_slug="001-visual",
        screen="dash",
        target="web",
        comparison_kind="mockup_runtime",
        reference_path=mockup,
        actual_path=runtime,
        threshold_percent=5.0,
        diff_path=tmp_path / ".specs/features/001-visual/run/manual/visual-evidence/dash.diff.png",
    )
    payload = {
        "schema_version": "1",
        "oracle": "livespec-visual-evidence",
        "oracle_version": "1",
        "feature_slug": "001-visual",
        "command": "spec-check",
        "target": "web",
        "run_id": "manual",
        "verdict": "PASS",
        "comparisons": [
            {
                **comparison.to_dict(),
                "actual_path": "../outside.png",
            }
        ],
    }
    payload["receipt_hash"] = receipt_payload_hash(payload)
    receipt_path = tmp_path / ".specs/features/001-visual/run/manual/visual-evidence/receipt.json"
    receipt_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(VisualReceiptError, match="path_outside_project"):
        verify_visual_receipt(receipt_path, project_root=tmp_path)


def test_visual_receipt_wraps_malformed_numeric_fields(tmp_path: Path) -> None:
    mockup = tmp_path / ".specs/design/screens/001-visual/dash.png"
    runtime = tmp_path / ".specs/features/001-visual/run/manual/web/dash.png"
    _write_png(mockup, (20, 40, 60))
    _write_png(runtime, (20, 40, 60))
    comparison = compare_visual_images(
        project_root=tmp_path,
        feature_slug="001-visual",
        screen="dash",
        target="web",
        comparison_kind="mockup_runtime",
        reference_path=mockup,
        actual_path=runtime,
        threshold_percent=5.0,
        diff_path=tmp_path / ".specs/features/001-visual/run/manual/visual-evidence/dash.diff.png",
    )
    receipt_path = write_visual_receipt(
        project_root=tmp_path,
        feature_slug="001-visual",
        command="spec-check",
        target="web",
        run_id="manual",
        comparisons=[comparison],
        output_dir=tmp_path / ".specs/features/001-visual/run/manual/visual-evidence",
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload["comparisons"][0]["width"] = "not-an-int"
    payload["receipt_hash"] = receipt_payload_hash(payload)
    receipt_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(VisualReceiptError, match="comparison_field_invalid:width"):
        verify_visual_receipt(receipt_path, project_root=tmp_path)


def test_visual_receipt_rejects_loosened_design_threshold(tmp_path: Path) -> None:
    mockup = tmp_path / ".specs/design/screens/001-visual/dash.png"
    runtime = tmp_path / ".specs/features/001-visual/run/manual/web/dash.png"
    _write_png(mockup, (20, 40, 60))
    _write_png(runtime, (200, 40, 60))
    comparison = compare_visual_images(
        project_root=tmp_path,
        feature_slug="001-visual",
        screen="dash",
        target="web",
        comparison_kind="mockup_runtime",
        reference_path=mockup,
        actual_path=runtime,
        threshold_percent=100.0,
        diff_path=tmp_path / ".specs/features/001-visual/run/manual/visual-evidence/dash.diff.png",
    )
    receipt_path = write_visual_receipt(
        project_root=tmp_path,
        feature_slug="001-visual",
        command="spec-check",
        target="web",
        run_id="manual",
        comparisons=[comparison],
        output_dir=tmp_path / ".specs/features/001-visual/run/manual/visual-evidence",
    )

    with pytest.raises(VisualReceiptError, match="threshold_policy_invalid"):
        verify_visual_receipt(receipt_path, project_root=tmp_path)
