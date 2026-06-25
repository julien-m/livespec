"""XCUITest xcresult export helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

from validator.runner_xcuitest_impl import XCRESULTTOOL_TIMEOUT_SECONDS


def convert_heic_to_png(heic_path: Path, png_path: Path) -> bool:
    """Convert a HEIC image to PNG using macOS `sips`."""
    try:
        result = subprocess.run(
            ["sips", "-s", "format", "png", str(heic_path), "--out", str(png_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and png_path.exists()


def extract_attachments_from_xcresult_json(
    data: Any, attachments: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Recursively extract ActionTestAttachment nodes from xcresulttool JSON."""
    attachments = [] if attachments is None else attachments
    if isinstance(data, dict):
        data_dict = cast(dict[str, Any], data)
        if _is_action_attachment(data_dict):
            attachments.append(data_dict)
        for value in data_dict.values():
            extract_attachments_from_xcresult_json(value, attachments)
    elif isinstance(data, list):
        for item in cast(list[Any], data):
            extract_attachments_from_xcresult_json(item, attachments)
    return attachments


def _is_action_attachment(data: dict[str, Any]) -> bool:
    """Return True when a JSON mapping is an ActionTestAttachment."""
    type_field = data.get("_type")
    return (
        isinstance(type_field, dict)
        and cast(dict[str, Any], type_field).get("_name") == "ActionTestAttachment"
    )


def parse_xcresult(bundle_path: Path, output_dir: Path, destination_id: str) -> list[Path]:
    """Extract screenshots from an .xcresult bundle."""
    dest_dir = output_dir / destination_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        if not _export_attachments(bundle_path, Path(tmp_dir)):
            return exported
        manifest = _load_manifest(Path(tmp_dir) / "manifest.json")
        if manifest is None:
            return exported
        for entry in iter_manifest_attachments(manifest):
            exported.extend(_copy_manifest_entry(Path(tmp_dir), dest_dir, entry))
    return exported


def _export_attachments(bundle_path: Path, tmp_dir: Path) -> bool:
    """Export all xcresult attachments into a temporary directory."""
    try:
        subprocess.run(
            [
                "xcrun",
                "xcresulttool",
                "export",
                "attachments",
                "--path",
                str(bundle_path),
                "--output-path",
                str(tmp_dir),
            ],
            capture_output=True,
            text=True,
            timeout=XCRESULTTOOL_TIMEOUT_SECONDS,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return True


def _load_manifest(manifest_path: Path) -> object | None:
    """Load exported attachments manifest JSON."""
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _copy_manifest_entry(tmp_dir: Path, dest_dir: Path, entry: dict[str, str]) -> list[Path]:
    """Copy or convert one exported attachment manifest entry."""
    exported_file = tmp_dir / entry["exportedFileName"]
    if not exported_file.exists() or exported_file.suffix.lower() not in {
        ".png",
        ".heic",
        ".jpg",
        ".jpeg",
    }:
        return []
    png_path = dest_dir / f"{entry.get('attachmentName', exported_file.stem)}.png"
    if exported_file.suffix.lower() == ".heic":
        return [png_path] if convert_heic_to_png(exported_file, png_path) else []
    shutil.copy2(exported_file, png_path)
    return [png_path]


def iter_manifest_attachments(manifest: object) -> list[dict[str, str]]:
    """Flatten `xcresulttool export attachments` manifest into one list."""
    flat: list[dict[str, str]] = []
    if not isinstance(manifest, list):
        return flat
    for test_entry in cast(list[Any], manifest):
        flat.extend(_entries_from_test_manifest(test_entry))
    return flat


def _entries_from_test_manifest(test_entry: object) -> list[dict[str, str]]:
    """Return attachment entries from one test manifest item."""
    if not isinstance(test_entry, dict):
        return []
    attachments = cast(dict[str, Any], test_entry).get("attachments")
    if not isinstance(attachments, list):
        return []
    return [_entry_from_attachment(att) for att in attachments if _entry_from_attachment(att)]


def _entry_from_attachment(attachment: object) -> dict[str, str]:
    """Convert one attachment payload into exported filename + attachment name."""
    if not isinstance(attachment, dict):
        return {}
    data = cast(dict[str, Any], attachment)
    exported_file = data.get("exportedFileName")
    if not isinstance(exported_file, str):
        return {}
    suggested = data.get("suggestedHumanReadableName")
    screen_name = (
        strip_attachment_suffix(suggested)
        if isinstance(suggested, str)
        else exported_file.rsplit(".", 1)[0]
    )
    return {"exportedFileName": exported_file, "attachmentName": screen_name}


def strip_attachment_suffix(suggested_name: str) -> str:
    """Recover the user-set attachment name from Xcode's filename."""
    stem = suggested_name.rsplit(".", 1)[0]
    parts = stem.split("_")
    if len(parts) >= 3 and parts[-1].count("-") >= 4 and parts[-2].isdigit():
        stem = "_".join(parts[:-2])
    return stem[: -len(".tree")] if stem.endswith(".tree") else stem
