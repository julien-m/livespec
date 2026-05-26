"""Deterministic PNG comparison and visual evidence receipts."""

from __future__ import annotations

import hashlib
import json
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

ORACLE_NAME = "livespec-visual-evidence"
ORACLE_VERSION = "1"
RECEIPT_SCHEMA_VERSION = "1"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PIXEL_CHANNEL_DIFF_THRESHOLD = 0
MAX_DESIGN_FIDELITY_THRESHOLD_PERCENT = 5.0
BASELINE_RUNTIME_THRESHOLD_PERCENT = 0.0
MAX_VISUAL_FILE_BYTES = 100 * 1024 * 1024

ComparisonKind = Literal["mockup_runtime", "baseline_runtime", "mockup_baseline"]
VisualVerdict = Literal["PASS", "FAIL", "BLOCKED"]


class VisualReceiptError(ValueError):
    """Raised when a visual evidence receipt is missing, malformed, or stale."""


@dataclass(frozen=True)
class _VisualMetrics:
    width: int
    height: int
    total_pixels: int
    diff_pixels: int
    actual_percent: float
    issues: tuple[str, ...]
    dimension_mismatch: bool


@dataclass(frozen=True)
class _PngImage:
    width: int
    height: int
    rgba: bytes


@dataclass(frozen=True)
class VisualComparison:
    """One deterministic PNG comparison recorded in a visual receipt."""

    feature_slug: str
    screen: str
    target: str
    comparison_kind: ComparisonKind
    reference_path: str
    actual_path: str
    diff_path: str
    reference_sha256: str
    actual_sha256: str
    diff_sha256: str
    width: int
    height: int
    total_pixels: int
    diff_pixels: int
    threshold_percent: float
    actual_diff_percent: float
    verdict: VisualVerdict
    issues: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the JSON payload for this comparison."""
        return {
            "feature_slug": self.feature_slug,
            "screen": self.screen,
            "target": self.target,
            "comparison_kind": self.comparison_kind,
            "reference_path": self.reference_path,
            "actual_path": self.actual_path,
            "diff_path": self.diff_path,
            "reference_sha256": self.reference_sha256,
            "actual_sha256": self.actual_sha256,
            "diff_sha256": self.diff_sha256,
            "width": self.width,
            "height": self.height,
            "total_pixels": self.total_pixels,
            "diff_pixels": self.diff_pixels,
            "threshold_percent": self.threshold_percent,
            "actual_diff_percent": self.actual_diff_percent,
            "verdict": self.verdict,
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class VisualReceipt:
    """Verified visual evidence receipt produced by the LiveSpec oracle."""

    schema_version: str
    oracle: str
    oracle_version: str
    feature_slug: str
    command: str
    target: str
    run_id: str
    verdict: VisualVerdict
    comparisons: tuple[VisualComparison, ...]
    receipt_hash: str
    path: Path | None = None


def compare_visual_images(
    *,
    project_root: Path,
    feature_slug: str,
    screen: str,
    target: str,
    comparison_kind: ComparisonKind,
    reference_path: Path,
    actual_path: Path,
    threshold_percent: float,
    diff_path: Path,
) -> VisualComparison:
    """Compare two PNG files and return a deterministic comparison record.

    Args:
        project_root: Root used to normalize paths in the receipt.
        feature_slug: Feature directory slug.
        screen: Screen identifier.
        target: UI target, for example `web`.
        comparison_kind: Semantic comparison type.
        reference_path: Expected PNG path.
        actual_path: Actual PNG path.
        threshold_percent: Maximum allowed changed-pixel percentage.
        diff_path: Destination for the generated diff PNG.

    Returns:
        A comparison object with hashes, dimensions, diff metrics, and verdict.

    Raises:
        VisualReceiptError: If a path is missing, outside the project,
            oversized, unreadable, not a supported PNG, or hash verification
            fails during receipt validation.
    """
    reference_abs = _resolve_project_path(project_root, reference_path)
    actual_abs = _resolve_project_path(project_root, actual_path)
    diff_abs = _resolve_project_path(project_root, diff_path, must_exist=False)
    reference_sha = sha256_file(reference_abs)
    actual_sha = sha256_file(actual_abs)
    reference_img = _read_png_rgba(reference_abs)
    actual_img = _read_png_rgba(actual_abs)

    metrics = _calculate_metrics(reference_img, actual_img)
    if metrics.dimension_mismatch:
        _write_dimension_mismatch_diff(reference_img, diff_abs)
    else:
        _write_diff_image(reference_img, actual_img, diff_abs)
    diff_sha = sha256_file(diff_abs)

    verdict: VisualVerdict = (
        "PASS"
        if metrics.actual_percent <= threshold_percent and not metrics.issues
        else "FAIL"
    )
    return VisualComparison(
        feature_slug=feature_slug,
        screen=screen,
        target=target,
        comparison_kind=comparison_kind,
        reference_path=_project_relative(project_root, reference_abs),
        actual_path=_project_relative(project_root, actual_abs),
        diff_path=_project_relative(project_root, diff_abs),
        reference_sha256=reference_sha,
        actual_sha256=actual_sha,
        diff_sha256=diff_sha,
        width=metrics.width,
        height=metrics.height,
        total_pixels=metrics.total_pixels,
        diff_pixels=metrics.diff_pixels,
        threshold_percent=float(threshold_percent),
        actual_diff_percent=round(metrics.actual_percent, 8),
        verdict=verdict,
        issues=metrics.issues,
    )


def write_visual_receipt(
    *,
    project_root: Path,
    feature_slug: str,
    command: str,
    target: str,
    run_id: str,
    comparisons: list[VisualComparison],
    output_dir: Path,
) -> Path:
    """Write a visual evidence receipt and matching report JSON.

    Args:
        project_root: Root used to normalize the receipt path.
        feature_slug: Feature directory slug.
        command: Calling LiveSpec command.
        target: UI target.
        run_id: Runtime capture run id.
        comparisons: Comparison records produced by `compare_visual_images`.
        output_dir: Directory where receipt/report files are written.

    Returns:
        Path to the written receipt JSON.
    """
    output_abs = _resolve_project_path(project_root, output_dir)
    output_abs.mkdir(parents=True, exist_ok=True)
    verdict = _aggregate_verdict(comparisons)
    payload: dict[str, object] = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "oracle": ORACLE_NAME,
        "oracle_version": ORACLE_VERSION,
        "feature_slug": feature_slug,
        "command": command,
        "target": target,
        "run_id": run_id,
        "verdict": verdict,
        "comparisons": [comparison.to_dict() for comparison in comparisons],
    }
    payload["receipt_hash"] = receipt_payload_hash(payload)
    receipt_path = output_abs / "receipt.json"
    report_path = output_abs / "report.json"
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    receipt_path.write_text(text, encoding="utf-8")
    report_path.write_text(text, encoding="utf-8")
    return receipt_path


def verify_visual_receipt(
    receipt_path: Path,
    *,
    project_root: Path,
    expected_feature_slug: str | None = None,
    expected_command: str | None = None,
    expected_target: str | None = None,
    expected_run_id: str | None = None,
) -> VisualReceipt:
    """Verify a receipt by recalculating hashes and PNG diffs from disk.

    Args:
        receipt_path: Path to the receipt JSON.
        project_root: Project root used to resolve receipt-relative paths.

    Returns:
        A verified receipt object.

    Raises:
        VisualReceiptError: If the receipt is malformed, stale, or not emitted
            by the LiveSpec visual evidence oracle.
    """
    receipt_abs = _resolve_project_path(project_root, receipt_path)
    try:
        raw_payload: object = json.loads(receipt_abs.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VisualReceiptError(f"receipt_unreadable: {receipt_abs}") from exc
    if not isinstance(raw_payload, dict):
        raise VisualReceiptError("receipt_root_must_be_object")
    payload = cast(dict[str, Any], raw_payload)
    if payload.get("oracle") != ORACLE_NAME:
        raise VisualReceiptError("oracle_mismatch")
    if payload.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise VisualReceiptError("schema_version_mismatch")
    feature_slug = _string_field(payload, "feature_slug")
    command = _string_field(payload, "command")
    target = _string_field(payload, "target")
    run_id = _string_field(payload, "run_id")
    if expected_feature_slug is not None and feature_slug != expected_feature_slug:
        raise VisualReceiptError("feature_slug_mismatch")
    if expected_command is not None and command != expected_command:
        raise VisualReceiptError("command_mismatch")
    if expected_target is not None and target != expected_target:
        raise VisualReceiptError("target_mismatch")
    if expected_run_id is not None and run_id != expected_run_id:
        raise VisualReceiptError("run_id_mismatch")
    comparisons = _parse_comparisons(payload)
    for comparison in comparisons:
        if comparison.feature_slug != feature_slug:
            raise VisualReceiptError("comparison_feature_slug_mismatch")
        if comparison.target != target:
            raise VisualReceiptError("comparison_target_mismatch")
    for comparison in comparisons:
        _verify_comparison(comparison, project_root=project_root)
    expected_hash = str(payload.get("receipt_hash", ""))
    actual_hash = receipt_payload_hash(payload)
    if expected_hash != actual_hash:
        raise VisualReceiptError("receipt_hash_mismatch")
    verdict = _aggregate_verdict(list(comparisons))
    if payload.get("verdict") != verdict:
        raise VisualReceiptError("verdict_mismatch")
    return VisualReceipt(
        schema_version=str(payload["schema_version"]),
        oracle=str(payload["oracle"]),
        oracle_version=str(payload.get("oracle_version", "")),
        feature_slug=feature_slug,
        command=command,
        target=target,
        run_id=run_id,
        verdict=verdict,
        comparisons=comparisons,
        receipt_hash=expected_hash,
        path=receipt_abs,
    )


def receipt_payload_hash(payload: dict[str, object]) -> str:
    """Return the canonical hash for a receipt payload."""
    without_hash = {k: v for k, v in payload.items() if k != "receipt_hash"}
    canonical = json.dumps(
        without_hash,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    try:
        stat = path.stat()
    except OSError as exc:
        raise VisualReceiptError(f"path_unreadable:{path}") from exc
    if not path.is_file():
        raise VisualReceiptError(f"path_not_regular_file:{path}")
    if stat.st_size > MAX_VISUAL_FILE_BYTES:
        raise VisualReceiptError(f"path_too_large:{path}")
    h = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
    except OSError as exc:
        raise VisualReceiptError(f"path_unreadable:{path}") from exc
    return h.hexdigest()


def _parse_comparisons(payload: dict[str, Any]) -> tuple[VisualComparison, ...]:
    raw: object = payload.get("comparisons")
    if not isinstance(raw, list) or not raw:
        raise VisualReceiptError("comparisons_missing")
    comparisons: list[VisualComparison] = []
    for item in cast(list[object], raw):
        if not isinstance(item, dict):
            raise VisualReceiptError("comparison_must_be_object")
        comparisons.append(_comparison_from_dict(cast(dict[str, Any], item)))
    return tuple(comparisons)


def _comparison_from_dict(data: dict[str, Any]) -> VisualComparison:
    required = (
        "feature_slug",
        "screen",
        "target",
        "comparison_kind",
        "reference_path",
        "actual_path",
        "diff_path",
        "reference_sha256",
        "actual_sha256",
        "diff_sha256",
        "width",
        "height",
        "total_pixels",
        "diff_pixels",
        "threshold_percent",
        "actual_diff_percent",
        "verdict",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise VisualReceiptError(f"comparison_missing:{','.join(missing)}")
    comparison_kind = _string_field(data, "comparison_kind")
    if comparison_kind not in ("mockup_runtime", "baseline_runtime", "mockup_baseline"):
        raise VisualReceiptError("comparison_kind_invalid")
    verdict = _string_field(data, "verdict")
    if verdict not in ("PASS", "FAIL", "BLOCKED"):
        raise VisualReceiptError("comparison_verdict_invalid")
    issues_raw: object = data.get("issues", [])
    issues = (
        tuple(str(issue) for issue in cast(list[object], issues_raw))
        if isinstance(issues_raw, list)
        else ()
    )
    return VisualComparison(
        feature_slug=_string_field(data, "feature_slug"),
        screen=_string_field(data, "screen"),
        target=_string_field(data, "target"),
        comparison_kind=comparison_kind,
        reference_path=_string_field(data, "reference_path"),
        actual_path=_string_field(data, "actual_path"),
        diff_path=_string_field(data, "diff_path"),
        reference_sha256=_string_field(data, "reference_sha256"),
        actual_sha256=_string_field(data, "actual_sha256"),
        diff_sha256=_string_field(data, "diff_sha256"),
        width=_int_field(data, "width"),
        height=_int_field(data, "height"),
        total_pixels=_int_field(data, "total_pixels"),
        diff_pixels=_int_field(data, "diff_pixels"),
        threshold_percent=_float_field(data, "threshold_percent"),
        actual_diff_percent=_float_field(data, "actual_diff_percent"),
        verdict=verdict,
        issues=issues,
    )


def _string_field(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise VisualReceiptError(f"comparison_field_invalid:{key}")
    return value


def _int_field(data: dict[str, Any], key: str) -> int:
    value: object = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise VisualReceiptError(f"comparison_field_invalid:{key}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise VisualReceiptError(f"comparison_field_invalid:{key}") from exc


def _float_field(data: dict[str, Any], key: str) -> float:
    value: object = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise VisualReceiptError(f"comparison_field_invalid:{key}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise VisualReceiptError(f"comparison_field_invalid:{key}") from exc


def _verify_comparison(comparison: VisualComparison, *, project_root: Path) -> None:
    _validate_threshold_policy(comparison)
    reference_path = _resolve_project_path(project_root, Path(comparison.reference_path))
    actual_path = _resolve_project_path(project_root, Path(comparison.actual_path))
    diff_path = _resolve_project_path(project_root, Path(comparison.diff_path))
    if sha256_file(reference_path) != comparison.reference_sha256:
        raise VisualReceiptError("reference_sha256_mismatch")
    if sha256_file(actual_path) != comparison.actual_sha256:
        raise VisualReceiptError("actual_sha256_mismatch")
    if sha256_file(diff_path) != comparison.diff_sha256:
        raise VisualReceiptError("diff_sha256_mismatch")
    reference_img = _read_png_rgba(reference_path)
    actual_img = _read_png_rgba(actual_path)
    metrics = _calculate_metrics(reference_img, actual_img)
    actual_diff_percent = round(metrics.actual_percent, 8)
    recalculated_verdict: VisualVerdict = (
        "PASS"
        if actual_diff_percent <= comparison.threshold_percent and not metrics.issues
        else "FAIL"
    )
    if metrics.width != comparison.width or metrics.height != comparison.height:
        raise VisualReceiptError("dimension_mismatch")
    if metrics.total_pixels != comparison.total_pixels:
        raise VisualReceiptError("total_pixels_mismatch")
    if metrics.diff_pixels != comparison.diff_pixels:
        raise VisualReceiptError("diff_pixels_mismatch")
    if actual_diff_percent != comparison.actual_diff_percent:
        raise VisualReceiptError("actual_diff_percent_mismatch")
    if recalculated_verdict != comparison.verdict:
        raise VisualReceiptError("comparison_verdict_mismatch")


def _validate_threshold_policy(comparison: VisualComparison) -> None:
    """Reject receipts that try to loosen canonical visual-gate thresholds."""
    if comparison.threshold_percent < 0:
        raise VisualReceiptError("threshold_policy_invalid")
    if (
        comparison.comparison_kind == "baseline_runtime"
        and comparison.threshold_percent != BASELINE_RUNTIME_THRESHOLD_PERCENT
    ):
        raise VisualReceiptError("threshold_policy_invalid")
    if (
        comparison.comparison_kind in ("mockup_runtime", "mockup_baseline")
        and comparison.threshold_percent > MAX_DESIGN_FIDELITY_THRESHOLD_PERCENT
    ):
        raise VisualReceiptError("threshold_policy_invalid")


def _count_changed_pixels(reference_img: _PngImage, actual_img: _PngImage) -> int:
    rgba = _diff_rgba(reference_img, actual_img)
    return sum(
        1
        for index in range(0, len(rgba), 4)
        if max(rgba[index : index + 4]) > PIXEL_CHANNEL_DIFF_THRESHOLD
    )


def _calculate_metrics(reference_img: _PngImage, actual_img: _PngImage) -> _VisualMetrics:
    issues: list[str] = []
    width, height = reference_img.width, reference_img.height
    total_pixels = width * height
    if (reference_img.width, reference_img.height) != (actual_img.width, actual_img.height):
        issues.append("dimension_mismatch")
        return _VisualMetrics(
            width=width,
            height=height,
            total_pixels=total_pixels,
            diff_pixels=total_pixels,
            actual_percent=100.0,
            issues=tuple(issues),
            dimension_mismatch=True,
        )
    diff_pixels = _count_changed_pixels(reference_img, actual_img)
    actual_percent = (diff_pixels / total_pixels * 100.0) if total_pixels else 0.0
    return _VisualMetrics(
        width=width,
        height=height,
        total_pixels=total_pixels,
        diff_pixels=diff_pixels,
        actual_percent=actual_percent,
        issues=(),
        dimension_mismatch=False,
    )


def _write_diff_image(reference_img: _PngImage, actual_img: _PngImage, diff_path: Path) -> None:
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    diff = _diff_rgba(reference_img, actual_img)
    output = bytearray()
    for index in range(0, len(diff), 4):
        changed = max(diff[index : index + 4]) > PIXEL_CHANNEL_DIFF_THRESHOLD
        output.extend((255, 0, 0, 255) if changed else (0, 0, 0, 0))
    _write_png_rgba(diff_path, reference_img.width, reference_img.height, bytes(output))


def _write_dimension_mismatch_diff(reference_img: _PngImage, diff_path: Path) -> None:
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    _write_png_rgba(
        diff_path,
        reference_img.width,
        reference_img.height,
        bytes((255, 0, 0, 255)) * (reference_img.width * reference_img.height),
    )


def _diff_rgba(reference_img: _PngImage, actual_img: _PngImage) -> bytes:
    return bytes(
        abs(reference_img.rgba[index] - actual_img.rgba[index])
        for index in range(len(reference_img.rgba))
    )


def _read_png_rgba(path: Path) -> _PngImage:
    """Read a non-interlaced 8-bit PNG and return RGBA bytes."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise VisualReceiptError(f"png_unreadable: {path}") from exc
    if not data.startswith(PNG_SIGNATURE):
        raise VisualReceiptError(f"png_unreadable: {path}")
    offset = len(PNG_SIGNATURE)
    width = 0
    height = 0
    bit_depth = 0
    color_type = 0
    interlace = 0
    palette = b""
    transparency = b""
    idat = bytearray()
    while offset < len(data):
        if offset + 8 > len(data):
            raise VisualReceiptError(f"png_malformed:{path}")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_start = offset + 8
        chunk_end = chunk_start + length
        if chunk_end + 4 > len(data):
            raise VisualReceiptError(f"png_malformed:{path}")
        chunk_data = data[chunk_start:chunk_end]
        offset = chunk_end + 4
        if chunk_type == b"IHDR":
            if length != 13:
                raise VisualReceiptError(f"png_malformed:{path}")
            width, height, bit_depth, color_type, _compression, _filter, interlace = (
                struct.unpack(">IIBBBBB", chunk_data)
            )
        elif chunk_type == b"PLTE":
            palette = chunk_data
        elif chunk_type == b"tRNS":
            transparency = chunk_data
        elif chunk_type == b"IDAT":
            idat.extend(chunk_data)
        elif chunk_type == b"IEND":
            break
    if width <= 0 or height <= 0 or not idat:
        raise VisualReceiptError(f"png_malformed:{path}")
    if bit_depth != 8 or interlace != 0:
        raise VisualReceiptError(f"png_unsupported:{path}")
    channels = _png_channels(color_type)
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error as exc:
        raise VisualReceiptError(f"png_unreadable: {path}") from exc
    scanlines = _unfilter_scanlines(
        raw,
        width=width,
        height=height,
        channels=channels,
    )
    rgba = _scanlines_to_rgba(
        scanlines,
        width=width,
        height=height,
        color_type=color_type,
        palette=palette,
        transparency=transparency,
    )
    return _PngImage(width=width, height=height, rgba=rgba)


def _png_channels(color_type: int) -> int:
    if color_type == 0:
        return 1
    if color_type == 2:
        return 3
    if color_type == 3:
        return 1
    if color_type == 4:
        return 2
    if color_type == 6:
        return 4
    raise VisualReceiptError("png_unsupported_color_type")


def _unfilter_scanlines(
    raw: bytes,
    *,
    width: int,
    height: int,
    channels: int,
) -> list[bytes]:
    row_len = width * channels
    stride = row_len + 1
    if len(raw) != stride * height:
        raise VisualReceiptError("png_malformed_scanlines")
    rows: list[bytes] = []
    previous = bytes(row_len)
    for row_index in range(height):
        start = row_index * stride
        filter_type = raw[start]
        source = raw[start + 1 : start + stride]
        row = _unfilter_row(filter_type, source, previous, channels)
        rows.append(row)
        previous = row
    return rows


def _unfilter_row(filter_type: int, source: bytes, previous: bytes, bpp: int) -> bytes:
    output = bytearray(len(source))
    for index, value in enumerate(source):
        left = output[index - bpp] if index >= bpp else 0
        up = previous[index]
        upper_left = previous[index - bpp] if index >= bpp else 0
        if filter_type == 0:
            predictor = 0
        elif filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = up
        elif filter_type == 3:
            predictor = (left + up) // 2
        elif filter_type == 4:
            predictor = _paeth(left, up, upper_left)
        else:
            raise VisualReceiptError("png_unsupported_filter")
        output[index] = (value + predictor) & 0xFF
    return bytes(output)


def _paeth(left: int, up: int, upper_left: int) -> int:
    p = left + up - upper_left
    pa = abs(p - left)
    pb = abs(p - up)
    pc = abs(p - upper_left)
    if pa <= pb and pa <= pc:
        return left
    if pb <= pc:
        return up
    return upper_left


def _scanlines_to_rgba(
    rows: list[bytes],
    *,
    width: int,
    height: int,
    color_type: int,
    palette: bytes,
    transparency: bytes,
) -> bytes:
    output = bytearray(width * height * 4)
    out_index = 0
    for row in rows:
        for pixel_index in range(width):
            in_index = pixel_index * _png_channels(color_type)
            if color_type == 0:
                gray = row[in_index]
                rgba = (gray, gray, gray, 255)
            elif color_type == 2:
                rgba = (row[in_index], row[in_index + 1], row[in_index + 2], 255)
            elif color_type == 3:
                palette_index = row[in_index]
                palette_offset = palette_index * 3
                if palette_offset + 2 >= len(palette):
                    raise VisualReceiptError("png_palette_index_invalid")
                alpha = transparency[palette_index] if palette_index < len(transparency) else 255
                rgba = (
                    palette[palette_offset],
                    palette[palette_offset + 1],
                    palette[palette_offset + 2],
                    alpha,
                )
            elif color_type == 4:
                gray = row[in_index]
                rgba = (gray, gray, gray, row[in_index + 1])
            elif color_type == 6:
                rgba = (
                    row[in_index],
                    row[in_index + 1],
                    row[in_index + 2],
                    row[in_index + 3],
                )
            else:
                raise VisualReceiptError("png_unsupported_color_type")
            output[out_index : out_index + 4] = bytes(rgba)
            out_index += 4
    return bytes(output)


def _write_png_rgba(path: Path, width: int, height: int, rgba: bytes) -> None:
    if len(rgba) != width * height * 4:
        raise VisualReceiptError("png_rgba_length_mismatch")
    raw = bytearray()
    row_len = width * 4
    for row_index in range(height):
        start = row_index * row_len
        raw.append(0)
        raw.extend(rgba[start : start + row_len])
    payload = (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(bytes(raw)))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def _aggregate_verdict(
    comparisons: list[VisualComparison] | tuple[VisualComparison, ...],
) -> VisualVerdict:
    if not comparisons:
        return "BLOCKED"
    if any(comparison.verdict == "BLOCKED" for comparison in comparisons):
        return "BLOCKED"
    if any(comparison.verdict == "FAIL" for comparison in comparisons):
        return "FAIL"
    return "PASS"


def _resolve_project_path(
    project_root: Path,
    path: Path,
    *,
    must_exist: bool = True,
) -> Path:
    root = project_root.resolve()
    resolved = path.resolve() if path.is_absolute() else (project_root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise VisualReceiptError(f"path_outside_project:{path}") from exc
    if must_exist and not resolved.exists():
        raise VisualReceiptError(f"path_missing:{path}")
    return resolved


def _project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


__all__ = [
    "ORACLE_NAME",
    "ORACLE_VERSION",
    "ComparisonKind",
    "VisualComparison",
    "VisualReceipt",
    "VisualReceiptError",
    "VisualVerdict",
    "compare_visual_images",
    "receipt_payload_hash",
    "sha256_file",
    "verify_visual_receipt",
    "write_visual_receipt",
]
