# @spec AC-001, AC-002, AC-003, AC-004: Gate signal tests
#   .specs/features/082-conventions-gate-signal/spec.md#ac-001

"""Signal tests for feature 082: fixture exclusion, family grouping, framework applicability."""

from __future__ import annotations

import re
import shutil
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from validator.conventions_ast.ars_applicability import FRAMEWORK_EVIDENCE, framework_for_source
from validator.conventions_ast.ars_rules import (
    EXPECTED_ARS_RULE_COUNT,
    INVENTORY_RELATIVE_PATH,
    ArsExecutableRule,
    ars_rule_by_id,
    load_ars_executable_rules,
    run_ars_executable_rules,
)
from validator.conventions_feature_scope import FeatureScope
from validator.conventions_gate import GateViolation, verify_conventions
from validator.conventions_gates import DEFAULT_SOURCE_EXCLUSIONS, inside_nested_checkout

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = "tests/fixtures/conventions_ast"
GO_FAMILY = "ars.family.go_code"
GO_SOURCE = 'package demo\n\nfunc Run() {\n\tpanic("boom")\n\tpanic("again")\n}\n'
NODE_SCRIPT = "const fs = require('node:fs');\nexport const read = fs.readFileSync;\n"
# Detector payloads are assembled so this test module does not match them itself.
SQL_STAR = "SEL" + "ECT * FROM users;\n"
PROSE_ANY = "// allow " + "any\n"
FRAMEWORK_DOCS = (
    "astro",
    "nextjs",
    "react",
    "remotion",
    "shadcn",
    "tanstack",
    "drizzle",
    "prisma",
    "tailwind",
    "cloudflare",
)


def _write_project(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir(parents=True)
    constitution = specs / "constitution.md"
    constitution.write_text("# Constitution\n", encoding="utf-8")
    gates: dict[str, object] = {
        "schema_version": 1,
        "generated_from": {
            "constitution": ".specs/constitution.md",
            "constitution_sha256": sha256(constitution.read_bytes()).hexdigest(),
            "stack": ".specs/stacks/_default.md",
        },
        "commands": {"lint": []},
        "builtin": {
            "max_file_lines": {"target": 1000, "limit": 2000},
            "max_function_lines": {"target": 1000, "limit": 2000},
            "file_header": {},
            "doc_coverage": {"require_public_api": False},
            "token_scale": {"scale": [2, 4, 8], "properties": []},
            "suppression_directives": {"budget": 1000, "whitelist": []},
            "import_rules": [],
        },
        "coverage": {},
        "exclusions": [".specs/**"],
        "scope": "repo",
    }
    (specs / "conventions-gates.yaml").write_text(yaml.safe_dump(gates), encoding="utf-8")
    inventory = tmp_path / INVENTORY_RELATIVE_PATH
    inventory.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / INVENTORY_RELATIVE_PATH, inventory)
    return tmp_path


def _write(project: Path, rel: str, text: str) -> None:
    path = project / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _ars(violations: list[GateViolation], rel: str) -> list[GateViolation]:
    return [item for item in violations if item.source == "ars" and item.path == rel]


def _reported_ids(violations: list[GateViolation], rel: str) -> set[str]:
    return {rule_id for item in _ars(violations, rel) for rule_id in item.rule_ids}


def _rules() -> tuple[ArsExecutableRule, ...]:
    return load_ars_executable_rules(REPO_ROOT)


def _doc_rule_ids(doc: str) -> set[str]:
    source = f"ai-ressources/code-conventions/{doc}.md"
    return {rule.runtime_rule_id for rule in _rules() if rule.source_path == source}


def _go_rule_ids() -> tuple[str, ...]:
    return tuple(sorted(rule.runtime_rule_id for rule in _rules() if rule.family_id == "go_code"))


def test_fixture_root_is_excluded_at_repo_and_feature_scope(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    fixture_rel = f"{FIXTURE_ROOT}/generated/go_code/fail.go"
    _write(project, fixture_rel, GO_SOURCE)
    _write(project, "src/run.go", GO_SOURCE)

    repo = verify_conventions(project)
    scoped = verify_conventions(
        project, feature_scope=FeatureScope("001-demo", frozenset({fixture_rel, "src/run.go"}))
    )

    assert f"{FIXTURE_ROOT}/**" not in DEFAULT_SOURCE_EXCLUSIONS
    for result in (repo, scoped):
        assert not [item for item in result.violations if item.path.startswith(FIXTURE_ROOT)]
        assert _ars(result.violations, "src/run.go")


def test_every_declared_fixture_triggers_exactly_its_rule() -> None:
    rules = _rules()
    assert len(rules) == EXPECTED_ARS_RULE_COUNT
    for rule in rules:
        fail = run_ars_executable_rules(REPO_ROOT, [REPO_ROOT / rule.fail_fixture])
        passing = run_ars_executable_rules(REPO_ROOT, [REPO_ROOT / rule.pass_fixture])

        assert [item.rule_ids for item in fail] == [(rule.runtime_rule_id,)], rule.inventory_id
        assert passing == [], rule.inventory_id


def test_ast_fixtures_satisfy_configured_language_headers() -> None:
    gates = yaml.safe_load((REPO_ROOT / ".specs/conventions-gates.yaml").read_text("utf-8"))
    patterns = {lang: rx for lang, rx in gates["builtin"]["file_header"].items() if rx}
    suffixes = {"swift": ".swift", "kotlin": ".kt", "rust": ".rs", "typescript": ".ts"}

    assert patterns
    for language, pattern in patterns.items():
        fixtures = sorted((REPO_ROOT / FIXTURE_ROOT).rglob(f"*{suffixes[language]}"))
        ast_fixtures = [path for path in fixtures if language in path.parts]
        assert ast_fixtures, language
        for path in ast_fixtures:
            assert re.search(pattern, path.read_text("utf-8")), path


def test_shared_family_match_produces_one_grouped_violation(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    _write(project, "src/run.go", GO_SOURCE)

    for scope in (None, FeatureScope("001-demo", frozenset({"src/run.go"}))):
        violations = _ars(verify_conventions(project, feature_scope=scope).violations, "src/run.go")

        assert len(violations) == 1
        assert violations[0].rule_id == GO_FAMILY
        assert violations[0].rule_ids == _go_rule_ids()
        assert len(violations[0].rule_ids) == 10
        assert violations[0].line == 4
        assert violations[0].message.startswith("ARS family go_code: 10 matched rule(s)")


def test_single_rule_fixture_keeps_family_identity() -> None:
    rule = next(rule for rule in _rules() if rule.family_id == "go_code")

    violations = run_ars_executable_rules(REPO_ROOT, [REPO_ROOT / rule.fail_fixture])

    assert [(item.rule_id, item.rule_ids) for item in violations] == [
        (GO_FAMILY, (rule.runtime_rule_id,))
    ]


def test_rule_specific_detector_keeps_runtime_rule_id() -> None:
    rule = ars_rule_by_id(REPO_ROOT)["ARS-RULE-02508"]

    violations = run_ars_executable_rules(REPO_ROOT, [REPO_ROOT / rule.fail_fixture])

    assert [(item.rule_id, item.rule_ids) for item in violations] == [
        (rule.runtime_rule_id, (rule.runtime_rule_id,))
    ]


def test_plain_node_script_reports_no_framework_rule(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    rel = "tests/integration/oracles/ui-oracle.mjs"
    _write(project, rel, NODE_SCRIPT)
    framework_ids = set().union(*(_doc_rule_ids(doc) for doc in FRAMEWORK_DOCS))

    for scope in (None, FeatureScope("001-demo", frozenset({rel}))):
        reported = _reported_ids(verify_conventions(project, feature_scope=scope).violations, rel)

        assert not reported & framework_ids


def test_nextjs_file_reports_nextjs_rules(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    rel = "app/page.tsx"
    _write(project, rel, "import Link from 'next/link';\n" + NODE_SCRIPT)

    for scope in (None, FeatureScope("001-demo", frozenset({rel}))):
        reported = _reported_ids(verify_conventions(project, feature_scope=scope).violations, rel)

        assert _doc_rule_ids("nextjs") <= reported


FRAMEWORK_CASES = [
    ("astro", "a.ts", "import { z } from 'astro:content';\n" + NODE_SCRIPT, "a.ts", NODE_SCRIPT),
    ("nextjs", "a.ts", "import Image from 'next/image';\n" + NODE_SCRIPT, "a.ts", NODE_SCRIPT),
    ("react", "a.ts", "import { useState } from 'react';\n" + NODE_SCRIPT, "a.ts", NODE_SCRIPT),
    ("react", "a.tsx", NODE_SCRIPT, "a.ts", NODE_SCRIPT),
    (
        "remotion",
        "a.ts",
        "import { Player } from '@remotion/player';\n" + NODE_SCRIPT,
        "a.ts",
        NODE_SCRIPT,
    ),
    (
        "shadcn",
        "a.ts",
        "import { Button } from '@/components/ui/button';\n" + NODE_SCRIPT,
        "a.ts",
        NODE_SCRIPT,
    ),
    (
        "tanstack",
        "a.ts",
        "import { useQuery } from '@tanstack/react-query';\n" + NODE_SCRIPT,
        "a.ts",
        NODE_SCRIPT,
    ),
    ("drizzle", "drizzle/0001.sql", SQL_STAR, "db/0001.sql", SQL_STAR),
    ("prisma", "prisma/migrations/1.sql", SQL_STAR, "db/1.sql", SQL_STAR),
    (
        "tailwind",
        "a.css",
        "@tailwind base;\n.card { color: #ff0000; }\n",
        "a.css",
        ".card { color: #ff0000; }\n",
    ),
    (
        "cloudflare",
        "a.ts",
        "import { env } from 'cloudflare:workers';\n" + PROSE_ANY,
        "a.ts",
        PROSE_ANY,
    ),
]


@pytest.mark.parametrize(
    ("doc", "pos_rel", "pos_text", "neg_rel", "neg_text"),
    FRAMEWORK_CASES,
    ids=[f"{case[0]}-{index}" for index, case in enumerate(FRAMEWORK_CASES)],
)
def test_framework_evidence_rows_gate_rules_at_runtime(
    tmp_path: Path, doc: str, pos_rel: str, pos_text: str, neg_rel: str, neg_text: str
) -> None:
    positive = _write_project(tmp_path / "positive")
    negative = _write_project(tmp_path / "negative")
    _write(positive, pos_rel, pos_text)
    _write(negative, neg_rel, neg_text)
    doc_ids = _doc_rule_ids(doc)

    assert _reported_ids(verify_conventions(positive).violations, pos_rel) & doc_ids
    assert not _reported_ids(verify_conventions(negative).violations, neg_rel) & doc_ids


def test_framework_table_covers_framework_sources_with_prefix_normalization() -> None:
    expected = {f"code-conventions/{doc}.md" for doc in FRAMEWORK_DOCS}
    framework_sources = {
        rule.source_path
        for rule in _rules()
        if rule.source_path.removeprefix("ai-ressources/") in expected
    }

    assert set(FRAMEWORK_EVIDENCE) == expected
    assert len(framework_sources) == len(expected)
    assert all(framework_for_source(source) is not None for source in framework_sources)


def test_non_root_ars_rules_directory_is_not_a_fixture(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    rel = "src/ars_rules/ars-rule-00735/app.ts"
    _write(project, rel, NODE_SCRIPT)

    reported = _reported_ids(verify_conventions(project).violations, rel)

    assert not reported & _doc_rule_ids("nextjs")


def test_nested_worktrees_are_never_sources(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    agent_rel = ".claude/worktrees/agent-1/src/run.go"
    nested_rel = "vendor/other-checkout/src/run.go"
    _write(project, agent_rel, GO_SOURCE)
    _write(project, ".claude/worktrees/agent-1/.git", "gitdir: ../../../.git/worktrees/a\n")
    _write(project, nested_rel, GO_SOURCE)
    _write(project, "vendor/other-checkout/.git", "gitdir: /elsewhere/.git/worktrees/b\n")
    _write(project, "src/run.go", GO_SOURCE)

    violations = verify_conventions(project).violations

    assert not [item for item in violations if item.path.startswith((".claude/", "vendor/"))]
    assert _ars(violations, "src/run.go")
    assert inside_nested_checkout(project, nested_rel)
    assert not inside_nested_checkout(project, "src/run.go")
    assert not inside_nested_checkout(project, str(project / "src/run.go"))
