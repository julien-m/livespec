---
title: Conventions Rulebook Semantic Implementation
feature: 062-conventions-rulebook-semantic
status: Implemented
created: 2026-06-12
updated: 2026-06-25
---

# Implementation - Conventions Rulebook Semantic

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Rulebook schema](spec.md#fr-001) | `validator/conventions_rules.py` | `@spec FR-001: Rulebook schema...` | Implemented | 2026-06-12 |
| [FR-002: Resolve sources](spec.md#fr-002) | `validator/conventions_rules.py` | `@spec FR-002: Resolve sources...` | Implemented | 2026-06-12 |
| [FR-003: Compile via provider](spec.md#fr-003) | `validator/conventions_rules.py` | `@spec FR-003: Compile via provider...` | Implemented | 2026-06-12 |
| [FR-004: Stale hashes](spec.md#fr-004) | `validator/conventions_rules.py` | `@spec FR-004: Stale hashes...` | Implemented | 2026-06-12 |
| [FR-005: Finding schema](spec.md#fr-005) | `validator/conventions_engine_c.py` | `@spec FR-005: Finding schema...` | Implemented | 2026-06-12 |
| [FR-006: Domain batching](spec.md#fr-006) | `validator/conventions_engine_c.py` | `@spec FR-006: Domain batching...` | Implemented | 2026-06-12 |
| [FR-007: Verdicts](spec.md#fr-007) | `validator/conventions_engine_c.py` | `@spec FR-007: Verdicts...` | Implemented | 2026-06-12 |
| [FR-008: Provider blocked](spec.md#fr-008) | `validator/conventions_engine_c.py` | `@spec FR-008: Provider blocked...` | Implemented | 2026-06-12 |
| [FR-009: Register compile and semantic CLI](spec.md#fr-009) | `validator/cli_commands/utility_cmd.py` | `@spec FR-009: Register conventions compile...`, `@spec FR-005: Engine C executable path...` | Implemented | 2026-06-12 |
| [FR-010: Pytest coverage](spec.md#fr-010) | `tests/test_conventions_compile.py`, `tests/test_conventions_semantic.py` | `@spec FR-010` | Implemented | 2026-06-12 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_conventions_compile.py`, `tests/test_conventions_semantic.py` | Implemented |
| AC-002 | `tests/test_conventions_semantic.py` | Implemented |
| AC-003 | `tests/test_conventions_compile.py` | Implemented |
| AC-004 | `tests/test_conventions_compile.py` | Implemented |
| AC-005 | `tests/test_conventions_compile.py` | Implemented |
| AC-006 | `tests/test_conventions_compile.py` | Implemented |
| AC-007 | `tests/test_conventions_compile.py` | Implemented |
| AC-008 | `tests/test_conventions_compile.py` | Implemented |
| AC-009 | `tests/test_conventions_semantic.py` | Implemented |
| AC-010 | `tests/test_conventions_semantic.py` | Implemented |
| AC-011 | `tests/test_conventions_semantic.py` | Implemented |
| AC-012 | `tests/test_conventions_semantic.py` | Implemented |
| AC-013 | `tests/test_conventions_semantic.py` | Implemented |
| AC-014 | `tests/test_conventions_semantic.py` | Implemented |
| AC-015 | `tests/test_conventions_semantic.py` | Implemented |
| AC-016 | `tests/test_conventions_semantic.py` | Implemented |
| AC-017 | `tests/test_conventions_semantic.py` | Implemented |
| AC-018 | `tests/test_conventions_semantic.py` | Implemented |
| AC-019 | `tests/test_conventions_compile.py`, `tests/test_conventions_semantic.py` | Implemented |
| AC-020 | `tests/test_conventions_compile.py`, `tests/test_conventions_semantic.py` | Implemented |
| AC-021 | `wc -l validator/conventions_rules.py validator/conventions_engine_c.py` | Implemented |
| AC-022 | `validator/conventions_rules.py`, `validator/conventions_engine_c.py`, `validator/cli_commands/utility_cmd.py` | Implemented |

## Files Created/Modified

- `validator/conventions_rules.py` - compiled rulebook schema, loader, source resolver, and provider compiler.
- `validator/conventions_engine_c.py` - Layer 4 semantic Engine C schemas, domain batching, waiver handling, and verdict calculation.
- `validator/cli_commands/utility_cmd.py` - `livespec conventions compile [--force]` command.
- `tests/test_conventions_compile.py` - compiler, stale hash, provider schema, and CLI tests.
- `tests/test_conventions_semantic.py` - Engine C batching, blocking, waiver, schema, and provider-down tests.
