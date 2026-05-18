---
title: Implementation — F045 Native Behavioral Specs
feature: 045-native-behavioral-specs
spec_ref: .specs/features/045-native-behavioral-specs/spec.md
plan_ref: .specs/features/045-native-behavioral-specs/plan.md
created: 2026-05-14
updated: 2026-05-14
status: Done
---

# Implementation: Native Behavioral Specs Generation (F045)

<!-- @spec FR-001..FR-017: Full F045 implementation — .specs/features/045-native-behavioral-specs/spec.md -->


## Status Legend

- ✅ Implemented & verified
- ⚠️ Partial / placeholder (upgrade hook documented in code)
- ⛔ Blocked

## Requirement Mapping

| FR | Status | Files | Notes |
|----|--------|-------|-------|
| FR-001 | ✅ | `validator/behavioral_grammar.py` (`detect_mode`) · `commands/spec-specify.md` Step 4.5 | Precedence A > C > B implemented; `override` parameter added |
| FR-002 | ✅ | `commands/spec-specify.md` Step 4.5 (Mode A falls through to existing Step 5) | Zero edits to F042 spec.md or transcription path |
| FR-003 | ✅ | `validator/native_behavioral_templates.py` (`FLOW_QUESTIONS`) · `validator/native_behavioral.py` (`run_native_interview`) | 8 frozen prompts in F044 canonical order |
| FR-004 | ✅ | same module (`SCREEN_QUESTIONS`) | 8 frozen prompts for screens |
| FR-005 | ✅ | `validator/native_behavioral.py` (`_normalise_answer`) | Empty / `skip` → `(to fill later)` |
| FR-006 | ✅ ⚠️ | `validator/native_behavioral.py` (`run_mockup_derived`) · `MOCKUP_DERIVED_QUESTIONS` | 5 prompts over the remaining canonical screen sections (`Acteur`, `Source d'entrée`, `Sortie principale`, `Validations`, `Erreurs`); visual sections use `(to fill later — populated from mockup analysis)` placeholder (no decoder in stack — documented hook) |
| FR-007 | ✅ | `run_native_interview`, `run_mockup_derived` | Mode B: `specStatus: manual`. Mode C: + `derivedFrom: native-mockups` |
| FR-008 | ✅ | `apply_validation_gate` | Structured JSON log line per artefact |
| FR-009 | ✅ | `apply_validation_gate` | FAIL → discard tmp + write `error.md` + print `BLOCKED` + return 1 |
| FR-010 | ✅ | `apply_validation_gate` | PASS silent · WARNING write + log all diagnostics |
| FR-011 | ✅ | `_render_body` | H2 headings byte-identical to F044 mandatory section names + canonical order |
| FR-012 | ✅ | git diff verification | Zero bytes diff against F041–F044 spec.md |
| FR-013 | ✅ | `run_mockup_derived` | Empty / unreadable mockup → fallback to Mode B + warning + no `derivedFrom` |
| FR-014 | ✅ | `commands/spec-specify.md` Step 4.5 §4 (producer-side guard documented; module exposes parseable frontmatter) | Slash-command level guard |
| FR-015 | ✅ | `commands/spec-specify.md` Step 4.5 §1 + §5 | `--native` / `--from-mockups` overrides; `--from-mockups` with no mockup → BLOCKED |
| FR-016 | ✅ | `tests/test_native_behavioral_specs.py` | 4 detection branches covered |
| FR-017 | ✅ | `tests/integration/test_native_behavioral_e2e.py` | E2E smoke asserts WARNING |

## Acceptance Criteria Mapping

| AC | Test |
|----|------|
| AC-001 | `test_detect_mode_reuse_when_flow_exists` |
| AC-002 | `test_detect_mode_native_when_nothing_exists` |
| AC-003 | `test_detect_mode_mockup_derived_when_png_exists`, `…pen_exists` |
| AC-004 | `test_native_interview_8_questions_canonical_order_flow` |
| AC-005 | `test_native_interview_8_questions_canonical_order_screen` |
| AC-006 | `test_skip_becomes_to_fill_later`, `test_empty_answer_becomes_to_fill_later`, `test_validator_gate_WARNING_writes_and_logs` |
| AC-007 | `test_mockup_derived_max_5_questions`, `test_mockup_derived_non_visual_answers_are_preserved` |
| AC-008 | `test_mockup_derived_frontmatter_has_derivedFrom_native_mockups`, `test_native_frontmatter_specStatus_manual_no_brainstormSource` |
| AC-009 | `test_native_frontmatter_specStatus_manual_no_brainstormSource` |
| AC-010 | `test_validator_invoked_per_artefact_log_line` |
| AC-011 | `test_validator_gate_FAIL_discards_and_blocks` |
| AC-012 | `test_validator_gate_PASS_writes_silently`, `test_validator_gate_WARNING_writes_and_logs` |
| AC-013 | `test_body_byte_equivalent_to_f041_import` |
| AC-014 | `git diff --stat main` produces empty output (verified at finalisation) |
| AC-015 | `test_e2e_smoke_no_brainstorm_no_mockups_skip_all` |
| AC-016 | `test_detect_mode_native_when_mockup_zero_bytes`, `test_mockup_zero_bytes_falls_back_to_modeb_no_derivedFrom` |
| AC-017 | `test_specStatus_manual_target_protected` (producer side) + Step 4.5 spec (slash-command side) |
| AC-018 | All `test_detect_mode_*` together (precedence is encoded in `detect_mode`) |
| AC-019 | No new top-level CLI command, no new agent (verified by file changes list below) |
| AC-020 | All 4 `test_detect_mode_*` branches |

## Files Created

- `validator/native_behavioral_templates.py` — 8+8+5 frozen `InterviewQuestion` templates
- `validator/native_behavioral.py` — `run_native_interview`, `run_mockup_derived`, `apply_validation_gate`, `NativeArtefact`
- `tests/test_native_behavioral_specs.py` — 22 unit tests
- `tests/integration/test_native_behavioral_e2e.py` — 1 E2E smoke

## Files Modified

- `validator/behavioral_grammar.py` — appended `GenerationMode`, `MOCKUP_EXTENSIONS`, `detect_mode()` and helpers; added `os` import; updated `__all__`. **Existing F044 behaviour and signatures untouched.**
- `commands/spec-specify.md` — inserted **Step 4.5 — Native Behavioral Mode Detection** between existing Step 4 and Step 5. (`.claude/commands/spec.specify.md` is a symlink to this file — single source of truth.)

## Verification

```
pytest tests/test_native_behavioral_specs.py tests/integration/test_native_behavioral_e2e.py -v
# → 23 passed

pytest -q
# → baseline suite + 23 focused behavioral tests pass; full-project count depends on unrelated repository state

git diff --stat main -- .specs/features/041-*/spec.md .specs/features/042-*/spec.md .specs/features/043-*/spec.md .specs/features/044-*/spec.md
# → empty (FR-012 / AC-014 satisfied)

livespec validate .specs/features/045-native-behavioral-specs/
# → 100/100 on pipeline.md, plan.md, progress.md, spec.md
```

## Notes

- **No new dependency** added to `pyproject.toml`. Mode C uses `pathlib` + `os.stat` only (no Pillow). The visual-section placeholder is the explicit upgrade hook for a future iteration that wires real mockup analysis.
- **No new top-level CLI command**, no new agent type. Behaviour change ships entirely as Step 4.5 inside `/spec.specify`.
- **F044 grammar v1.0 imported verbatim** via `MANDATORY_FLOW_SECTIONS`, `MANDATORY_SCREEN_SECTIONS`, `VALIDATION_RESULT`, `validate_behavioral`. F044 module signatures and tests are untouched.
- The `apply_validation_gate` writes a `<canonical>.md.tmp` then `os.replace`s on success, so a FAIL never leaves a malformed artefact at the canonical path.
- Empty / `skip` answers naturally produce a WARNING (not PASS) because the optional `Notes` section is absent — matching AC-015's expectation that PASS is impossible for an all-skip artefact.
