"""Compare a Pencil-derived design contract with a runtime UI contract."""

# @spec FR-003: Design alignment module
#   — .specs/features/047-design-alignment-gate/spec.md#fr-003

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

from .models import AlignmentIssue, AlignmentResult, NormalizedContract, Verdict

SUPPORT_FIELDS: tuple[str, ...] = (
    "width",
    "height",
    "dpr",
    "orientation",
    "shape",
    "safe_area_top",
    "header_height",
    "decorative_shell",
)
NODE_TOP_LEVEL_FIELDS: tuple[str, ...] = ("name", "type", "text")
BOUND_FIELDS: tuple[str, ...] = ("x", "y", "width", "height")
NUMERIC_TOLERANCE = 1


def compare_contract_files(
    *,
    design_path: Path,
    runtime_path: Path,
    screen: str,
    output_dir: Path,
) -> AlignmentResult:
    """Compare normalized design/runtime contracts and write report artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)

    blocked = _preflight_paths(design_path=design_path, runtime_path=runtime_path)
    if blocked:
        result = AlignmentResult(screen=screen, verdict="BLOCKED", issues=blocked)
        return _write_outputs(
            result,
            output_dir=output_dir,
            design_path=design_path,
            runtime_path=runtime_path,
        )

    try:
        design = _load_contract(design_path, screen=screen, kind="design")
        runtime = _load_contract(runtime_path, screen=screen, kind="runtime")
    except ValueError as exc:
        result = AlignmentResult(
            screen=screen,
            verdict="BLOCKED",
            issues=[
                AlignmentIssue(
                    severity="BLOCKED",
                    field="contract",
                    expected="valid normalized contract",
                    actual=str(exc),
                    message=str(exc),
                )
            ],
        )
        return _write_outputs(
            result,
            output_dir=output_dir,
            design_path=design_path,
            runtime_path=runtime_path,
        )

    issues = _compare_support(design.support, runtime.support)
    if issues:
        result = AlignmentResult(screen=screen, verdict="BLOCKED", issues=issues)
        return _write_outputs(
            result,
            output_dir=output_dir,
            design_path=design_path,
            runtime_path=runtime_path,
            design=design,
            runtime=runtime,
        )

    issues = _compare_nodes(design.nodes, runtime.nodes)
    verdict: Verdict = "FAIL" if issues else "PASS"
    result = AlignmentResult(screen=screen, verdict=verdict, issues=issues)
    return _write_outputs(
        result,
        output_dir=output_dir,
        design_path=design_path,
        runtime_path=runtime_path,
        design=design,
        runtime=runtime,
    )


def _preflight_paths(*, design_path: Path, runtime_path: Path) -> list[AlignmentIssue]:
    issues: list[AlignmentIssue] = []
    for label, path in (("design", design_path), ("runtime", runtime_path)):
        if not path.exists():
            issues.append(
                AlignmentIssue(
                    severity="BLOCKED",
                    field=f"{label}_path",
                    expected="readable file",
                    actual=str(path),
                    message=f"{label} contract is missing: {path}",
                )
            )
    return issues


def _load_contract(path: Path, *, screen: str, kind: str) -> NormalizedContract:
    raw = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    payload = _select_screen(raw, screen=screen)
    support = payload.get("support")
    nodes = payload.get("nodes")
    if not isinstance(support, dict):
        raise ValueError(f"{kind} contract missing support object")
    if not isinstance(nodes, list):
        raise ValueError(f"{kind} contract missing nodes list")
    support_contract = cast(dict[str, Any], support)
    node_list = cast(list[Any], nodes)
    return NormalizedContract(
        screen=str(payload.get("id") or payload.get("screen") or screen),
        support=support_contract,
        nodes=_flatten_nodes(node_list),
        source_path=path,
        source_hash=_sha256(path),
    )


def _select_screen(raw: dict[str, Any], *, screen: str) -> dict[str, Any]:
    screens = raw.get("screens")
    if isinstance(screens, list):
        for item in cast(list[Any], screens):
            if not isinstance(item, dict):
                continue
            item_dict = cast(dict[str, Any], item)
            if item_dict.get("id") == screen:
                return item_dict
        raise ValueError(f"screen {screen!r} not found")
    return raw


def _flatten_nodes(nodes: list[Any]) -> dict[str, dict[str, Any]]:
    flattened: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node = cast(dict[str, Any], node)
        node_id = node.get("id") or node.get("name")
        if not isinstance(node_id, str) or not node_id:
            continue
        flattened[node_id] = node
        children = node.get("children")
        if isinstance(children, list):
            flattened.update(_flatten_nodes(cast(list[Any], children)))
    return flattened


def _compare_support(
    design: dict[str, Any],
    runtime: dict[str, Any],
) -> list[AlignmentIssue]:
    issues: list[AlignmentIssue] = []
    for field in SUPPORT_FIELDS:
        expected = design.get(field)
        actual = runtime.get(field)
        if expected == actual:
            continue
        issues.append(
            AlignmentIssue(
                severity="BLOCKED",
                field=f"support.{field}",
                expected=expected,
                actual=actual,
                message=f"Support mismatch for {field}: expected {expected}, got {actual}",
            )
        )
    return issues


def _compare_nodes(
    design_nodes: dict[str, dict[str, Any]],
    runtime_nodes: dict[str, dict[str, Any]],
) -> list[AlignmentIssue]:
    issues: list[AlignmentIssue] = []
    for node_id, design_node in design_nodes.items():
        runtime_node = runtime_nodes.get(node_id)
        if runtime_node is None:
            issues.append(
                AlignmentIssue(
                    severity="FAIL",
                    node_id=node_id,
                    field="node",
                    expected="present",
                    actual="missing",
                    message=f"Runtime node missing: {node_id}",
                )
            )
            continue
        issues.extend(_compare_node(node_id, design_node, runtime_node))
    return issues


def _compare_node(
    node_id: str,
    design_node: dict[str, Any],
    runtime_node: dict[str, Any],
) -> list[AlignmentIssue]:
    issues: list[AlignmentIssue] = []
    for field in NODE_TOP_LEVEL_FIELDS:
        issues.extend(
            _compare_value(
                node_id,
                field,
                design_node.get(field),
                runtime_node.get(field),
            )
        )
    for field in BOUND_FIELDS:
        issues.extend(
            _compare_value(
                node_id,
                f"bounds.{field}",
                _mapping_value(design_node.get("bounds"), field),
                _mapping_value(runtime_node.get("bounds"), field),
                numeric_tolerance=NUMERIC_TOLERANCE,
            )
        )
    issues.extend(_compare_mapping(node_id, "styles", design_node, runtime_node))
    issues.extend(_compare_mapping(node_id, "states", design_node, runtime_node))
    return issues


def _compare_mapping(
    node_id: str,
    key: str,
    design_node: dict[str, Any],
    runtime_node: dict[str, Any],
) -> list[AlignmentIssue]:
    issues: list[AlignmentIssue] = []
    expected_raw = design_node.get(key)
    actual_raw = runtime_node.get(key)
    if not isinstance(expected_raw, dict) or not isinstance(actual_raw, dict):
        return _compare_value(
            node_id,
            key,
            cast(object, expected_raw),
            cast(object, actual_raw),
        )
    expected_map = cast(dict[str, object], expected_raw)
    actual_map = cast(dict[str, object], actual_raw)
    for field, expected in expected_map.items():
        actual = actual_map.get(field)
        issues.extend(_compare_value(node_id, f"{key}.{field}", expected, actual))
    return issues


def _mapping_value(value: object, field: str) -> object:
    if not isinstance(value, dict):
        return None
    return cast(dict[str, object], value).get(field)


def _compare_value(
    node_id: str,
    field: str,
    expected: object,
    actual: object,
    *,
    numeric_tolerance: int = 0,
) -> list[AlignmentIssue]:
    if _values_match(expected, actual, numeric_tolerance=numeric_tolerance):
        return []
    return [
        AlignmentIssue(
            severity="FAIL",
            node_id=node_id,
            field=field,
            expected=expected,
            actual=actual,
            message=f"{node_id}.{field}: expected {expected}, got {actual}",
        )
    ]


def _values_match(expected: object, actual: object, *, numeric_tolerance: int) -> bool:
    if isinstance(expected, int | float) and isinstance(actual, int | float):
        return abs(float(expected) - float(actual)) <= numeric_tolerance
    return expected == actual


def _write_outputs(
    result: AlignmentResult,
    *,
    output_dir: Path,
    design_path: Path,
    runtime_path: Path,
    design: NormalizedContract | None = None,
    runtime: NormalizedContract | None = None,
) -> AlignmentResult:
    report_path = output_dir / f"{result.screen}.report.md"
    manifest_path = output_dir / "design-alignment.manifest.json"
    diff_path = output_dir / f"{result.screen}.diff.json"
    report_path.write_text(_render_report(result), encoding="utf-8")
    diff_path.write_text(
        json.dumps([issue.to_dict() for issue in result.issues], indent=2),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            _manifest_payload(
                result,
                design_path=design_path,
                runtime_path=runtime_path,
                design=design,
                runtime=runtime,
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    return AlignmentResult(
        screen=result.screen,
        verdict=result.verdict,
        issues=result.issues,
        report_path=report_path,
        manifest_path=manifest_path,
    )


def _render_report(result: AlignmentResult) -> str:
    lines = [
        f"# Design Alignment Report - {result.screen}",
        "",
        result.summary,
        "",
    ]
    if not result.issues:
        lines.append("No issues found.")
    else:
        lines.extend(["| Severity | Node | Field | Expected | Actual |", "|---|---|---|---|---|"])
        for issue in result.issues:
            lines.append(
                "| "
                f"{issue.severity} | {issue.node_id or '-'} | {issue.field} | "
                f"{issue.expected} | {issue.actual} |"
            )
    lines.append("")
    return "\n".join(lines)


def _manifest_payload(
    result: AlignmentResult,
    *,
    design_path: Path,
    runtime_path: Path,
    design: NormalizedContract | None,
    runtime: NormalizedContract | None,
) -> dict[str, object]:
    return {
        "screen": result.screen,
        "verdict": result.verdict,
        "design_source": str(design_path),
        "runtime_source": str(runtime_path),
        "design_hash": design.source_hash if design else _sha256_or_none(design_path),
        "runtime_hash": runtime.source_hash if runtime else _sha256_or_none(runtime_path),
        "support": {
            "design": design.support if design else None,
            "runtime": runtime.support if runtime else None,
        },
        "issues": [issue.to_dict() for issue in result.issues],
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_or_none(path: Path) -> str | None:
    return _sha256(path) if path.exists() else None
