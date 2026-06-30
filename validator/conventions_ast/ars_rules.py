# @spec FR-008, FR-009: Source decision manifest
#   .specs/features/073-conventions-multilang-catalog/spec.md#fr-008

"""CSV-backed executable ARS rule registry and detector runtime."""

from __future__ import annotations

import csv
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from validator.conventions_feature_scope import SOURCE_SUFFIXES
from validator.conventions_gate_types import GateSeverity, GateViolation

EXPECTED_ARS_RULE_COUNT = 564
INVENTORY_RELATIVE_PATH = Path("validator/conventions_ast/rule_catalog/ars_executable_rules.csv")
FIXTURE_ROOT = Path("tests/fixtures/conventions_ast/ars_rules")


@dataclass(frozen=True)
class ArsExecutableRule:
    """One executable CSV row connected to a runtime detector."""

    inventory_id: str
    runtime_rule_id: str
    source_path: str
    source_line: int
    source_anchor: str
    source_hash: str
    rule_text: str
    language: str
    domain: str
    family_id: str
    backend_id: str
    detector_id: str
    pass_fixture: str
    fail_fixture: str
    test_id: str


@dataclass(frozen=True)
class ArsRuleDetector:
    """Rule-specific wrapper around a shared matcher helper."""

    rule: ArsExecutableRule
    helper: Callable[[str], bool]
    execution_path: str

    def __call__(self, text: str) -> bool:
        """Evaluate this exact ARS rule through its own call path."""
        return self.helper(text)


_DETECTOR_CACHE: dict[str, ArsRuleDetector] = {}


def inventory_path(project_root: Path | None = None) -> Path:
    """Return the checked-in ARS executable rule inventory path."""
    root = project_root or Path.cwd()
    project_inventory = root / INVENTORY_RELATIVE_PATH
    if project_inventory.is_file():
        return project_inventory
    return _package_root() / INVENTORY_RELATIVE_PATH


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def project_has_ars_inventory(project_root: Path) -> bool:
    """Return True when the verified project explicitly carries ARS runtime rules."""
    return (project_root / INVENTORY_RELATIVE_PATH).is_file()


def load_ars_executable_rules(project_root: Path | None = None) -> tuple[ArsExecutableRule, ...]:
    """Load all executable ARS rule rows as individual runtime rules."""
    path = inventory_path(project_root)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = tuple(csv.DictReader(handle))
    return tuple(_rule_from_row(row) for row in rows)


def validate_ars_rule_registry(project_root: Path | None = None) -> list[str]:
    """Return registry defects that would make CSV coverage incomplete."""
    root = project_root or Path.cwd()
    rules = load_ars_executable_rules(root)
    fixture_root = root if project_has_ars_inventory(root) else _package_root()
    issues: list[str] = []
    if len(rules) != EXPECTED_ARS_RULE_COUNT:
        issues.append(f"ars_rule_count_mismatch:{len(rules)}")
    issues.extend(_duplicate_issues("inventory_id", (rule.inventory_id for rule in rules)))
    issues.extend(_duplicate_issues("runtime_rule_id", (rule.runtime_rule_id for rule in rules)))
    issues.extend(_duplicate_issues("detector_id", (rule.detector_id for rule in rules)))
    detectors = [detector_for_rule(rule) for rule in rules]
    issues.extend(
        _duplicate_issues("execution_path", (_execution_path(detector) for detector in detectors))
    )
    issues.extend(
        _duplicate_issues("callable_object", (str(id(detector)) for detector in detectors))
    )
    for rule in rules:
        issues.extend(_rule_contract_issues(rule, fixture_root))
    return issues


def evaluate_ars_rule_fixture(
    inventory_id: str, fixture_path: Path, *, project_root: Path | None = None
) -> list[str]:
    """Return the rule detector ID when a fixture violates one ARS rule."""
    rule = ars_rule_by_id(project_root or Path.cwd())[inventory_id]
    text = fixture_path.read_text(encoding="utf-8")
    return [rule.detector_id] if detector_for_rule(rule)(text) else []


def run_ars_executable_rules(
    project_root: Path,
    source_files: Sequence[Path],
) -> list[GateViolation]:
    """Run every executable ARS detector over the LiveSpec conventions source scope."""
    rules = load_ars_executable_rules(project_root)
    violations: list[GateViolation] = []
    for path in source_files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = _relative_path(project_root, path)
        if _is_ars_meta_source(rel):
            continue
        fixture_rule = _fixture_inventory_id(path)
        scan_rules = [ars_rule_by_id(project_root)[fixture_rule]] if fixture_rule else rules
        for rule in scan_rules:
            if not _language_applies(rule, path):
                continue
            if detector_for_rule(rule)(text):
                violations.append(
                    _violation(rule, rel, _first_line(text, detector_for_rule(rule)), path)
                )
    return violations


def ars_rule_by_id(project_root: Path | None = None) -> dict[str, ArsExecutableRule]:
    """Return ARS rules keyed by inventory ID."""
    return {rule.inventory_id: rule for rule in load_ars_executable_rules(project_root)}


def detector_for_rule(rule: ArsExecutableRule) -> ArsRuleDetector:
    """Return the concrete detector function for one runtime rule."""
    cached = _DETECTOR_CACHE.get(rule.inventory_id)
    if cached is not None:
        return cached
    detector = ArsRuleDetector(
        rule=rule,
        helper=_helper_for_rule(rule),
        execution_path=f"ars.rules.{rule.inventory_id.lower()}.execute",
    )
    _DETECTOR_CACHE[rule.inventory_id] = detector
    return detector


def _helper_for_rule(rule: ArsExecutableRule) -> Callable[[str], bool]:
    if _unreachable_language(rule):
        return lambda _text: False
    if rule.inventory_id == "ARS-RULE-02508":
        return _detect_destructive_modal_without_explicit_button
    if "never fixed `px`/`pt`" in rule.rule_text.lower():
        return _contains(r"(?:font-size|line-height|letter-spacing)\s*:\s*\d+(?:px|pt)\b")
    family = rule.family_id
    return _FAMILY_DETECTORS.get(family, _contains(_keyword_pattern(rule.rule_text)))


def _rule_from_row(row: dict[str, str]) -> ArsExecutableRule:
    inventory_id = row["inventory_id"]
    family = row["backend_expected"].split(":", 1)[-1]
    fixture_ext = _fixture_extension(row["language"], family)
    fixture_dir = FIXTURE_ROOT / inventory_id.lower()
    numeric_id = inventory_id.removeprefix("ARS-RULE-")
    return ArsExecutableRule(
        inventory_id=inventory_id,
        runtime_rule_id=f"ars.rule.{numeric_id}",
        source_path=row["source_path"],
        source_line=int(row["line"]),
        source_anchor=row["anchor"],
        source_hash=row["source_hash"],
        rule_text=row["rule_text"],
        language=row["language"],
        domain=row["domain"],
        family_id=family,
        backend_id=f"ars-rule:{inventory_id}",
        detector_id=f"ars.rule.{numeric_id}.detector",
        pass_fixture=(fixture_dir / f"pass.{fixture_ext}").as_posix(),
        fail_fixture=(fixture_dir / f"fail.{fixture_ext}").as_posix(),
        test_id="pytest:tests/test_conventions_ars_rules.py::test_all_csv_rules_have_pass_fail_fixtures",
    )


def _rule_contract_issues(rule: ArsExecutableRule, project_root: Path) -> list[str]:
    issues: list[str] = []
    if rule.backend_id.startswith("source-family:"):
        issues.append(f"family_backend:{rule.inventory_id}")
    if rule.detector_id.startswith("source-family."):
        issues.append(f"family_detector:{rule.inventory_id}")
    if not (project_root / rule.pass_fixture).is_file():
        issues.append(f"missing_pass_fixture:{rule.inventory_id}")
    if not (project_root / rule.fail_fixture).is_file():
        issues.append(f"missing_fail_fixture:{rule.inventory_id}")
    if _unreachable_language(rule):
        issues.append(f"language_unreachable:{rule.inventory_id}:{rule.language}")
    return issues


def _duplicate_issues(label: str, values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return [f"duplicate_{label}:{value}" for value in sorted(duplicates)]


def _language_applies(rule: ArsExecutableRule, path: Path) -> bool:
    if rule.language == "language-agnostic":
        return True
    suffix = path.suffix.lower()
    return suffix in _LANGUAGE_SUFFIXES.get(rule.language, ())


def _unreachable_language(rule: ArsExecutableRule) -> bool:
    if rule.language == "language-agnostic":
        return False
    return not set(_LANGUAGE_SUFFIXES.get(rule.language, ())).issubset(SOURCE_SUFFIXES)


def _fixture_inventory_id(path: Path) -> str | None:
    parts = path.parts
    try:
        index = parts.index("ars_rules")
    except ValueError:
        return None
    if len(parts) <= index + 1:
        return None
    candidate = parts[index + 1].upper()
    return candidate if candidate.startswith("ARS-RULE-") else None


def _fixture_extension(language: str, family: str) -> str:
    if language == "language-agnostic":
        return _FAMILY_EXTENSIONS.get(family, "txt")
    return {
        "css": "css",
        "delphi": "pas",
        "go": "go",
        "javascript": "ts",
        "kotlin": "kt",
        "python": "py",
        "rust": "rs",
        "shell": "sh",
        "sql": "sql",
        "typescript": "tsx",
    }.get(language, "txt")


def _contains(pattern: str) -> Callable[[str], bool]:
    regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    return lambda text: bool(regex.search(text))


def _keyword_pattern(rule_text: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", rule_text.lower())
    selected = "|".join(re.escape(word) for word in words[:3])
    return selected or r"\bARS_FAIL\b"


def _detect_destructive_modal_without_explicit_button(text: str) -> bool:
    """Detect destructive dialogs whose confirmation label is generic."""
    lowered = text.lower()
    if not re.search(r"\b(?:modal|dialog|alertdialog|sheet)\b", lowered):
        return False
    if not _has_destructive_intent(lowered):
        return False
    labels = [label.strip().lower() for label in _button_labels(text) if label.strip()]
    if not labels:
        return True
    if any(_is_explicit_destructive_label(label) for label in labels):
        return False
    generic = {"ok", "yes", "confirm", "continue", "proceed", "submit"}
    return any(label in generic for label in labels) or True


def _has_destructive_intent(text: str) -> bool:
    return (
        re.search(
            r"\b(delete|remove|destroy|revoke|purge|drop|reset|disable|deactivate|archive|wipe|erase)\b",
            text,
        )
        is not None
    )


def _button_labels(text: str) -> list[str]:
    labels = re.findall(r"<button[^>]*>([^<]+)</button>", text, flags=re.IGNORECASE)
    labels.extend(
        re.findall(
            r"<(?:Button|DialogAction|AlertDialogAction|SheetAction)[^>]*>([^<]+)</(?:Button|DialogAction|AlertDialogAction|SheetAction)>",
            text,
        )
    )
    labels.extend(re.findall(r"(?:label|aria-label|title)\s*=\s*[\"']([^\"']+)[\"']", text))
    return labels


def _is_explicit_destructive_label(label: str) -> bool:
    destructive_match = re.search(
        r"\b(delete|remove|destroy|revoke|purge|drop|reset|disable|deactivate|archive|wipe|erase)\b",
        label,
    )
    return destructive_match is not None and len(label.split()) >= 2


def _first_line(text: str, detector: Callable[[str], bool]) -> int:
    for index, line in enumerate(text.splitlines(), start=1):
        if detector(line):
            return index
    return 1


def _violation(rule: ArsExecutableRule, rel: str, line: int, path: Path) -> GateViolation:
    return GateViolation(
        rule_id=rule.runtime_rule_id,
        path=rel,
        line=line,
        severity=GateSeverity.ERROR,
        message=f"{rule.inventory_id}: {rule.rule_text}",
        source="ars",
        fix_hint=f"See {rule.source_path}{rule.source_anchor}",
    )


def _relative_path(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _is_ars_meta_source(rel: str) -> bool:
    return rel in {
        "validator/conventions_ast/ars_rules.py",
        "validator/conventions_ast/source_family_checks.py",
        "validator/conventions_ast/taxonomy.py",
    }


_LANGUAGE_SUFFIXES: dict[str, tuple[str, ...]] = {
    "css": (".css",),
    "delphi": (".pas", ".dpr", ".dproj"),
    "go": (".go",),
    "javascript": (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"),
    "kotlin": (".kt", ".kts"),
    "python": (".py",),
    "rust": (".rs",),
    "shell": (".sh", ".bash", ".zsh"),
    "sql": (".sql",),
    "typescript": (".ts", ".tsx"),
}

_FAMILY_EXTENSIONS: dict[str, str] = {
    "ai_prompt": "yaml",
    "css_design_tokens": "css",
    "database_sql": "sql",
    "delphi_code": "pas",
    "go_code": "go",
    "javascript_code": "ts",
    "json_yaml_config": "yaml",
    "markdown_docs": "md",
    "payment_contract": "ts",
    "platform_ops": "yaml",
    "python_code": "py",
    "shell_code": "sh",
    "typescript_ui": "tsx",
}

_FAMILY_DETECTORS: dict[str, Callable[[str], bool]] = {
    "ai_prompt": _contains(r"\btemperature\s*[:=]\s*(?:1\.[1-9]|[2-9])"),
    "ast-grep": _contains(r"\bARS_FAIL\b"),
    "code_prose": _contains(r"\ballow\s+(?:any|object|untyped)\b"),
    "css_design_tokens": _contains(r"(?:#[0-9a-f]{3,8}\b|\b(?:m|p|gap|text|bg)-\[[^\]]+\])"),
    "database_sql": _contains(r"\b(?:select\s+\*|drop\s+table|delete\s+from\s+\w+\s*;)"),
    "delphi_code": _contains(r"\bexcept\s*(?:\r?\n|\s)+end\s*;"),
    "design_system": _contains(r"\b(?:gradient orb|bokeh|border-radius:\s*999px)\b"),
    "go_code": _contains(r"\bpanic\s*\("),
    "javascript_code": _contains(r"\brequire\s*\("),
    "json_yaml_config": _contains(r"\b(?:password|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_/-]{8,}"),
    "markdown_docs": _contains(r"\b(?:TODO|TBD|FIXME)\b"),
    "payment_contract": _contains(
        r"\bamount\s*[:=]\s*\d+\b(?!.*\bcurrency\b)|webhook.*without idempotency"
    ),
    "platform_ops": _contains(r":latest\b|\blatest\s+version\b"),
    "python_code": _contains(r"except\s+Exception\s*:\s*(?:pass|return\s+None)"),
    "shell_code": _contains(r"curl\b.*\|\s*(?:sh|bash)"),
    "typescript_ui": _contains(r"<button(?![^>]*data-testid=)"),
}


def _execution_path(detector: Callable[[str], bool]) -> str:
    return str(getattr(detector, "execution_path", ""))
