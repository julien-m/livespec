# @spec FR-008, FR-009: Source decision manifest
#   .specs/features/073-conventions-multilang-catalog/spec.md#fr-008

"""Source path/hash helpers for ARS source decision manifests."""

from __future__ import annotations

from pathlib import Path

from validator.visual_evidence import sha256_file


def source_hash(root: Path, rel: str) -> str:
    source_file = root / rel
    if not source_file.is_file():
        return "sha256:missing"
    return f"sha256:{sha256_file(source_file)}"


def anchor_policy(source_file: Path) -> str:
    return "yaml-key-path" if source_file.suffix in {".yaml", ".yml"} else "heading-or-line-range"


def source_anchor(source_file: Path) -> str:
    if source_file.suffix in {".yaml", ".yml"}:
        return "$"
    try:
        return first_markdown_anchor(source_file)
    except OSError:
        return "line:1"


def first_markdown_anchor(source_file: Path) -> str:
    for line in source_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            return markdown_anchor(line)
    return "line:1"


def markdown_anchor(line: str) -> str:
    title = line.lstrip("#").strip().lower()
    slug = "".join(char if char.isalnum() or char in " -" else "" for char in title)
    return "#" + "-".join(slug.split())
