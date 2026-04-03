# Convention Fixes — Design Spec

## Scope

Fix all 32 convention violations found in `validator/` source code (10 HIGH, 11 MEDIUM, 12 LOW).

## Architecture Changes

### 1. Extract CLI business logic → `validator/orchestrator.py` (HIGH)
Move contradiction detection logic (cli.py:71-121) into a new `run_contradiction_check()` function in `validator/orchestrator.py`. CLI only calls it and reports.

### 2. Type the CoherenceRule protocol (HIGH)
- Change `CoherenceRule.check(graph: Any)` → `check(graph: SpecGraph)` in violation.py
- Add `specs_root` to the protocol as optional attribute
- Type `ALL_RULES: list[CoherenceRule]` and `get_rules() -> list[CoherenceRule]`
- Make all rule classes explicitly reference the protocol

### 3. Replace `hasattr` injection (HIGH)
- Add `specs_root: Path` parameter to `CoherenceRule.check()` signature
- Update all rule classes to accept it
- Remove monkey-patching in rule_engine.py

### 4. Fix `extra="allow"` (HIGH)
- BaseFrontmatter: `extra="ignore"` (forward-compat for base)
- All leaf models keep current behavior but inherit from base

### 5. Replace silent exception swallowing (HIGH × 5)
- `fixer.py:119`: catch specific `(yaml.YAMLError, OSError)`, log warning, return empty list with explanation
- `graph_builder.py:137,152`: catch `(yaml.YAMLError, OSError)`, log via `logging.warning()`
- `scorecard.py:115`: catch specific parse errors, log
- `mutations.py:208,221`: separate `ImportError` from `Exception`

## Typing Fixes

- `parser.py:ParsedFile`: `metadata: dict[str, Any]`, `code_blocks: list[dict[str, str]]`
- `violation.py:Violation.context`: `dict[str, str]`
- `coherence/report.py:groups`: `dict[str, list[Violation]]`
- `rules/__init__.py:code_blocks`: already typed elsewhere
- `scorecard.py:FeatureScore.axes/weights`: keep as `dict[str, int]`/`dict[str, float]` (acceptable)

## Naming/Style Fixes

- `fixer.py:62`: "A completer" → "To be completed."
- `reporter.py:54,62,84,86`: "ERREUR" → "ERROR", "AVERT." → "WARN"
- `graph_builder.py:44`: `f` → `feature`
- `graph_builder.py:80-81`: `i` → `line_number`, `m` → `match`
- `schemas/base.py:13`: `title_not_empty` → `validate_title_not_empty`
- `schemas/spec.py:19`: `updated_not_before_created` → `validate_updated_not_before_created`
- `coherence/report.py:28`: `format` → `output_format`
- `semantic/report.py:41`: `format` → `output_format`
- `llm_provider.py:55`: `print()` → `logging.warning()`
- `config.py:50`: add `encoding="utf-8"` to `open()`
- `fixer.py:225`: add `encoding="utf-8"` to `open()`
- `cli.py:40-54`: `Optional[str]` → `str | None` (consistency)

## Dead Code

- `rule_engine.py:68`: remove unused `flagged_features`

## Out of Scope

- Test file violations (naming, type hints, helpers/ directory)
- Function length refactoring beyond cli.py extraction
- LLM provider registry refactor (acceptable for now)
