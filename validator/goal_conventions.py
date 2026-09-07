"""Goal conventions responsibilities behind the public contract facade."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from . import goal_contracts as _contracts

__all__ = [
    "_build_convention_signal_text",
    "_canonical_json",
    "_canonical_rules",
    "_compile_conventions_payload",
    "_extract_airesources_root",
    "_normalize_section_lines",
    "_parse_convention_domains",
    "_parse_convention_refs",
    "_parse_keyword_list",
    "_render_convention_domain",
    "_render_convention_file",
    "_resolve_convention_ref",
    "_should_select_convention_domain",
    "_stable_path",
]


def _compile_conventions_payload(
    *,
    command: str,
    expectations: _contracts.ExpectationsFile,
    project_root: Path,
    feature: str | None,
    normalized_flags: list[str],
) -> dict[str, Any]:
    """Compile convention domains and source contents into the goal payload."""
    index_path = project_root / ".conventions" / "index.md"
    if not index_path.exists():
        return {
            "available": False,
            "index_path": None,
            "selected_domains": [],
        }
    index_text = index_path.read_text(encoding="utf-8")
    ai_root = _contracts._extract_airesources_root(index_text)
    domains = _contracts._parse_convention_domains(index_text, ai_root)
    signal_text = _contracts._build_convention_signal_text(
        command=command,
        expectations=expectations,
        project_root=project_root,
        feature=feature,
        normalized_flags=normalized_flags,
    )
    selected = [
        domain
        for domain in domains
        if _contracts._should_select_convention_domain(domain, signal_text)
    ]
    return {
        "available": True,
        "index_path": ".conventions/index.md",
        "selected_domains": [
            _contracts._render_convention_domain(domain, ai_root) for domain in selected
        ],
    }


def _extract_airesources_root(index_text: str) -> Path | None:
    match = re.search(r"\$AIRESOURCES`?\s*=\s*`([^`]+)`", index_text)
    if match is None:
        return None
    return Path(match.group(1))


def _parse_convention_domains(
    index_text: str,
    ai_root: Path | None,
) -> list[dict[str, Any]]:
    domains: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in index_text.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^##\s+([^\s\[]+)(?:\s+\[(.*?)\])?", line)
        if heading:
            current = {
                "name": heading.group(1),
                "keywords": _contracts._parse_keyword_list(heading.group(2) or ""),
                "refs": [],
            }
            domains.append(current)
            continue
        if current is None or not line.startswith("→"):
            continue
        current["refs"].extend(_contracts._parse_convention_refs(line[1:].strip(), ai_root))
    return domains


def _parse_keyword_list(raw_keywords: str) -> list[str]:
    return [keyword.strip() for keyword in raw_keywords.split(",") if keyword.strip()]


def _parse_convention_refs(raw_refs: str, ai_root: Path | None) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    base_dir = ""
    for raw_item in raw_refs.split(","):
        item = raw_item.strip()
        if not item:
            continue
        if item.startswith("$AIRESOURCES/"):
            display_path = item
            base_dir = str(Path(item.removeprefix("$AIRESOURCES/")).parent)
        elif base_dir:
            display_path = f"$AIRESOURCES/{base_dir}/{item}"
        else:
            display_path = item
        refs.append(
            {
                "display_path": display_path,
                "real_path": _contracts._resolve_convention_ref(display_path, ai_root),
            }
        )
    return refs


def _resolve_convention_ref(display_path: str, ai_root: Path | None) -> Path | None:
    if display_path.startswith("$AIRESOURCES/"):
        if ai_root is None:
            return None
        return ai_root / display_path.removeprefix("$AIRESOURCES/")
    path = Path(display_path)
    return path if path.is_absolute() else None


# @spec FR-014: Select convention domains from task signal
# — .specs/features/052-deterministic-command-goal-contracts/spec.md#fr-014
def _build_convention_signal_text(
    *,
    command: str,
    expectations: _contracts.ExpectationsFile,
    project_root: Path,
    feature: str | None,
    normalized_flags: list[str],
) -> str:
    chunks = [
        command,
        feature or "",
        " ".join(normalized_flags),
        *expectations.prose_sections.values(),
    ]
    if feature:
        feature_dir = project_root / ".specs" / "features" / feature
        for filename in _contracts.CONVENTION_SIGNAL_FILES:
            path = feature_dir / filename
            if path.exists():
                chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks).lower()


def _should_select_convention_domain(domain: dict[str, Any], signal_text: str) -> bool:
    name = str(domain["name"]).lower()
    keywords = [str(keyword).lower() for keyword in domain["keywords"]]
    if name == "code":
        return True
    if name.startswith("design") and (
        any(word in signal_text for word in _contracts.DESIGN_SIGNAL_WORDS)
        or any(keyword in signal_text for keyword in keywords)
    ):
        return True
    return any(keyword in signal_text for keyword in keywords)


# @spec FR-015: Embed selected conventions in canonical goal JSON
# — .specs/features/052-deterministic-command-goal-contracts/spec.md#fr-015
def _render_convention_domain(
    domain: dict[str, Any],
    ai_root: Path | None,
) -> dict[str, Any]:
    rendered_files = [_contracts._render_convention_file(ref) for ref in domain["refs"]]
    return {
        "name": domain["name"],
        "keywords": list(domain["keywords"]),
        "paths": [str(file["path"]) for file in rendered_files],
        "source_files": rendered_files,
        "airesources_root": ai_root.as_posix() if ai_root is not None else None,
    }


def _render_convention_file(ref: dict[str, Any]) -> dict[str, Any]:
    display_path = str(ref["display_path"])
    real_path = ref["real_path"]
    content = ""
    if isinstance(real_path, Path) and real_path.exists():
        content = real_path.read_text(encoding="utf-8").rstrip()
    return {
        "path": display_path,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content": content,
    }


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _canonical_rules(rules: list[_contracts.Rule]) -> list[dict[str, Any]]:
    return [
        {
            "verb": rule.verb,
            "kind": rule.kind,
            "payload": rule.payload,
        }
        for rule in rules
    ]


def _normalize_section_lines(section: str) -> list[str]:
    """Normalize prose expectation sections into stable, hashable lines."""
    lines: list[str] = []
    for raw_line in section.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        lines.append(line)
    return lines


def _stable_path(path: Path, *, project_root: Path, livespec_root: Path) -> str:
    for root in (project_root, livespec_root):
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
    return path.as_posix()
