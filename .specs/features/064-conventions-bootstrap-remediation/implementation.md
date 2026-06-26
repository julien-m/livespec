---
title: Conventions Bootstrap Remediation Implementation
feature: 064-conventions-bootstrap-remediation
status: Implemented
created: 2026-06-13
updated: 2026-06-25
---

<!-- @spec FR-001: Preflight binary checks — .specs/features/064-conventions-bootstrap-remediation/spec.md#fr-001 -->
<!-- @spec FR-005: Scaffold preflight action — .specs/features/064-conventions-bootstrap-remediation/spec.md#fr-005 -->
<!-- @spec FR-010: Conventions CLI extraction — .specs/features/064-conventions-bootstrap-remediation/spec.md#fr-010 -->

# Implementation — Conventions Bootstrap Remediation

## Summary

Implemented conventions bootstrap remediation for existing projects:

- Preflight now adds conventions-derived checks when `.specs/conventions-gates.yaml` exists.
- `preflight --fix` can run `livespec conventions scaffold --apply` through the trusted auto-fix dispatcher.
- `conventions scaffold --apply` renders Python Ruff and TypeScript ESLint templates from gates limits and skips existing configs unless `--sync-limits` is set. The Ruff template enables `PLR` for statement-count checks and leaves file line-count enforcement to the LiveSpec gate instead of setting Ruff `line-length`.
- `spec-fix --conventions` is documented as a worst-first debt burn-down mode with a strict non-regression gate.
- Conventions CLI routes moved from `utility_cmd.py` into `validator/cli_commands/conventions_cmd.py`; `utility_cmd.py` now keeps only utility commands and wiring.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001](spec.md#fr-001), [FR-002](spec.md#fr-002), [FR-003](spec.md#fr-003), [FR-004](spec.md#fr-004), [FR-005](spec.md#fr-005) | `validator/preflight_autofix.py`, `validator/cli_commands/preflight_cmd.py` | `@spec FR-001`, `@spec FR-005` | ✅ Implemented | 2026-06-13 |
| [FR-006](spec.md#fr-006), [FR-007](spec.md#fr-007), [FR-008](spec.md#fr-008) | `templates/conventions/python_ruff.toml.tmpl`, `templates/conventions/typescript_eslint.json.tmpl`, `validator/cli_commands/conventions_scaffold.py` | `@spec FR-006`, `@spec FR-008` | ✅ Implemented | 2026-06-13 |
| [FR-009](spec.md#fr-009) | `.agent-sync/skills/spec-fix/SKILL.md` | `@spec FR-009` | ✅ Implemented | 2026-06-13 |
| [FR-010](spec.md#fr-010), [FR-011](spec.md#fr-011), [FR-012](spec.md#fr-012) | `validator/cli_commands/conventions_cmd.py`, `validator/cli_commands/utility_cmd.py` | `@spec FR-010` | ✅ Implemented | 2026-06-13 |

## Acceptance Criteria Mapping

| AC | Implementation |
|---|---|
| AC-001, AC-002, AC-003 | **Read** [`validator/preflight_autofix.py`](../../../validator/preflight_autofix.py) for `conventions_preflight_items`. |
| AC-004 | **Read** [`validator/preflight_autofix.py`](../../../validator/preflight_autofix.py) for blocking rulebook provider checks. |
| AC-005 | **Read** [`validator/preflight_autofix.py`](../../../validator/preflight_autofix.py) and [`validator/cli_commands/preflight_cmd.py`](../../../validator/cli_commands/preflight_cmd.py) for scaffold auto-fix wiring. |
| AC-006, AC-007 | **Read** [`templates/conventions/python_ruff.toml.tmpl`](../../../templates/conventions/python_ruff.toml.tmpl) and [`templates/conventions/typescript_eslint.json.tmpl`](../../../templates/conventions/typescript_eslint.json.tmpl). |
| AC-008, AC-009 | **Read** [`validator/cli_commands/conventions_scaffold.py`](../../../validator/cli_commands/conventions_scaffold.py) for language detection, rendering, and overwrite policy. |
| AC-010, AC-011, AC-012 | **Read** [`.agent-sync/skills/spec-fix/SKILL.md`](../../../.agent-sync/skills/spec-fix/SKILL.md) for `--conventions` mode. |
| AC-013, AC-014, AC-015, AC-016 | **Read** [`validator/cli_commands/conventions_cmd.py`](../../../validator/cli_commands/conventions_cmd.py), [`validator/cli_commands/conventions_scaffold.py`](../../../validator/cli_commands/conventions_scaffold.py), and [`validator/cli_commands/utility_cmd.py`](../../../validator/cli_commands/utility_cmd.py) for the split and route preservation. |

## Tests

- **Read** [`tests/test_preflight_autofix.py`](../../../tests/test_preflight_autofix.py) for preflight-derived gates checks.
- **Read** [`tests/test_status_play_conventions_cli.py`](../../../tests/test_status_play_conventions_cli.py) for scaffold behavior and split line-limit coverage.
- **Read** [`tests/test_conventions_pipeline_docs.py`](../../../tests/test_conventions_pipeline_docs.py) for `spec-fix --conventions` documentation coverage.
