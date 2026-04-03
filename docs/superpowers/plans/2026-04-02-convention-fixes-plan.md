# Convention Fixes — Implementation Plan

## Phase 1: Type safety & protocol fixes (5 files)
1. `validator/coherence/violation.py` — Type `check(graph: SpecGraph, specs_root: Path)`, remove `Any`
2. `validator/coherence/rules/__init__.py` — Type `ALL_RULES: list[CoherenceRule]`, `get_rules() -> list[CoherenceRule]`
3. `validator/coherence/rule_engine.py` — Pass `specs_root` as parameter to `check()`, remove `hasattr` injection, remove dead `flagged_features`
4. All rule files (r1-r6) — Update `check()` signature to accept `specs_root: Path`
5. `validator/parser.py` — Type `metadata: dict[str, Any]`, `code_blocks: list[dict[str, str]]`

## Phase 2: Error handling fixes (4 files)
1. `validator/fixer.py` — Catch `(yaml.YAMLError, OSError)` instead of bare `Exception`
2. `validator/coherence/graph_builder.py` — Add `logging.warning()` for parse failures
3. `validator/semantic/scorecard.py` — Catch specific exceptions in `_score_axis1`
4. `validator/semantic/mutations.py` — Separate `ImportError` from `Exception`

## Phase 3: CLI extraction (2 files)
1. Create `validator/orchestrator.py` — Extract contradiction detection from cli.py
2. `validator/cli.py` — Call orchestrator, fix `Optional` → `|`, fix `format` shadow

## Phase 4: Schema & naming fixes (5 files)
1. `validator/schemas/base.py` — `extra="ignore"`, rename validator
2. `validator/schemas/spec.py` — Rename validator
3. `validator/fixer.py` — French → English, add encoding
4. `validator/reporter.py` — French labels → English
5. `validator/config.py` — Add encoding to `open()`

## Phase 5: Remaining naming & style (5 files)
1. `validator/coherence/graph_builder.py` — Rename single-letter vars
2. `validator/coherence/report.py` — `format` → `output_format`, type `groups`
3. `validator/coherence/violation.py` — `context: dict[str, str]`
4. `validator/semantic/report.py` — `format` → `output_format`
5. `validator/llm_provider.py` — `print()` → `logging.warning()`
