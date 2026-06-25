"""Focused XCUITest hash and baseline helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from validator.runner_xcuitest_impl import UICapabilityResult


def compute_swift_hash(project_dir: Path, only_testing: str | None) -> str | None:
    """Return a hash of Swift files in the requested test target."""
    if not only_testing:
        return None
    target_dir = project_dir / only_testing
    if not target_dir.is_dir():
        return None
    digest = hashlib.sha256()
    for swift in sorted(target_dir.rglob("*.swift")):
        if not _hash_swift_file(digest, target_dir, swift):
            return None
    return digest.hexdigest()


def capture_paths(project_dir: Path, only_testing: str | None) -> dict[str, Path]:
    """Return stable paths for the reusable xcresult bundle and hash."""
    bundles_dir = project_dir / ".specs" / ".test-bundles"
    bundle_name = (only_testing or "default").replace("/", "_") + ".xcresult"
    return {"bundle": bundles_dir / bundle_name, "hash": bundles_dir / f"{bundle_name}.hash"}


def _hash_swift_file(digest: Any, target_dir: Path, swift: Path) -> bool:
    """Hash one Swift file path and bytes."""
    try:
        digest.update(str(swift.relative_to(target_dir)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(swift.read_bytes())
        digest.update(b"\0")
    except OSError:
        return False
    return True


def compare_baseline(
    project_dir: Path, baseline: str, screenshot: str, threshold: float
) -> UICapabilityResult:
    """Compare two PNGs with the project pixelmatch helper."""
    from validator.web_runner_core import compare_pixel_baseline

    result = compare_pixel_baseline(project_dir, baseline, screenshot, threshold)
    return UICapabilityResult(
        success=result.success,
        output_path=result.output_path,
        error=result.error,
        metadata=result.metadata,
    )
