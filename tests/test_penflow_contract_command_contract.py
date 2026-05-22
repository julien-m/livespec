"""Command documentation tests for the Penflow UI contract integration."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_system_penflow_contract_doc_exists() -> None:
    body = _read("system/testing/penflow-contract.md")

    assert "Penflow Contract Verdict: PASS | FAIL | BLOCKED | ABSENT" in body
    assert "penflow/semantic-ui-tree.json" in body
    assert "top-level `verdict`" in body
    assert "--require-actual" in body
    assert "runtime_comparison: BLOCKED" in body
    assert "screenshots remain visual regression gates" in body
    assert ".specs/design/ui.pen" in body
    assert ".specs/design/screens/<feature_slug>/" in body
    assert ".specs/design/baselines/<feature_slug>/" in body
    assert "Mockup Factory Validation" in body
    assert "--require-mockup-validation" in body
    assert ".mockup-validation/visual-evidence/manifest.json" in body
    assert "status: PASS" in body


def test_spec_init_supports_brainstorm_and_from_scratch_penflow() -> None:
    body = _read(".agent-sync/skills/spec-init/SKILL.md")

    assert "Step 3.5.5 — Penflow Contract Workspace Bootstrap" in body
    assert ".brainstorm/penflow/" in body
    assert "copy it to root `penflow/`" in body
    assert "continue from scratch" in body
    assert "state: absent" in body


def test_spec_init_requires_post_sync_command_asset_verification() -> None:
    body = _read(".agent-sync/skills/spec-init/SKILL.md")

    assert "Step 3.12 — Sync Agent Assets" in body
    assert "BLOCKED at step 3.12" in body
    assert "Post-sync verification" in body
    assert ".specs/.livespec-path" in body
    assert ".agent-sync.local/skills/spec-feature" in body
    assert ".claude/skills/spec-feature" in body
    assert ".agents/skills/spec-feature" in body
    assert ".codex/agents/livespec-verifier.toml" in body
    assert "Unknown command: /spec-feature" in body


def test_spec_init_from_code_autonomous_prompt_is_bounded_noninteractive() -> None:
    body = _read(".agent-sync/skills/spec-init/SKILL.md")

    assert "Non-Interactive Autonomous From-Code Mode" in body
    assert "Proceed autonomously" in body
    assert "normalize active flags to `--from-code --auto`" in body
    assert "Do not wait for human validation" in body
    assert "single-package Vite React app" in body
    assert "300 seconds" in body
    assert "Autonomous from-code: enabled" in body


def test_spec_init_expectations_require_autonomous_from_code_completion() -> None:
    body = _read(".agent-sync/skills/spec-init/expectations.md")

    assert "Autonomous from-code" in body
    assert "single-package Vite React" in body
    assert "300 seconds" in body
    assert "must_not hang" in body
    assert "Autonomous from-code: enabled" in body


def test_visual_feature_pipeline_requires_forward_penflow_generation() -> None:
    feature = _read(".agent-sync/skills/spec-feature/SKILL.md")
    specify = _read(".agent-sync/skills/spec-specify/SKILL.md")
    plan = _read(".agent-sync/skills/spec-plan/SKILL.md")
    implement = _read(".agent-sync/skills/spec-implement/SKILL.md")

    for body in (feature, specify, plan, implement):
        assert "From-Scratch Penflow Forward Contract" in body
        assert "penflow validate-flow-specs penflow/flow-ui-contract --json" in body
        assert (
            "penflow export-semantic-tree penflow/flow-ui-contract --out "
            "penflow/semantic-ui-tree.json --json"
        ) in body
        assert (
            "penflow draft-pen-from-tree penflow/semantic-ui-tree.json --out "
            "penflow/ui.pen --json"
        ) in body
        assert "penflow validate-pen penflow/ui.pen --json" in body
        assert (
            "penflow export-expected penflow/ui.pen --out "
            "penflow/expected-ui-tree.json --json"
        ) in body
        assert (
            "penflow code-ir --from-context penflow/ui.pen --semantic-tree "
            "penflow/semantic-ui-tree.json"
        ) in body
        assert "penflow/code-ir.json" in body
        assert "livespec penflow-contract status --project . --target web-desktop --json" in body
        assert "BLOCKED" in body


def test_spec_feature_blocks_specify_until_penflow_contract_passes() -> None:
    body = _read(".agent-sync/skills/spec-feature/SKILL.md")

    assert "Phase 0.5 is a synchronous hard gate" in body
    assert (
        "When a feature description is provided → resolve slug, initialize pipeline, "
        "then run Phase 0.5"
    ) in body
    assert "proceed to Phase 1 as before" not in body
    assert "Do not mark Specify `In Progress`" in body
    assert "do not spawn Specify" in body
    assert (
        "until `livespec penflow-contract status --project . --target web-desktop "
        "--require-design-registry --require-mockup-validation --feature NNN-feature-name --json` "
        "returns `PASS`"
    ) in body


def test_spec_feature_initializes_pipeline_with_atomic_flags_and_description() -> None:
    body = _read(".agent-sync/skills/spec-feature/SKILL.md")

    assert (
        'livespec pipeline init --feature NNN-feature-name --description "<original feature '
        'description>" --flags "<normalized active flags>"'
    ) in body
    assert "Do not write `pipeline.md` by hand" in body
    assert "preserve `--auto --mono` exactly" in body


def test_spec_feature_phase_35_requires_runtime_penflow_evidence_before_done() -> None:
    body = _read(".agent-sync/skills/spec-feature/SKILL.md")

    assert "Phase 3.5 Runtime Evidence Gate" in body
    assert (
        "Do not run `livespec pipeline update --feature NNN-feature-name --phase test "
        "--status done`"
    ) in body
    assert "penflow/actual-ui-tree.json" in body
    assert "penflow/compare-report.json" in body
    assert "penflow/compare-report.md" in body
    assert "Penflow Contract Verdict: PASS" in body
    assert "raw `penflow/compare-report.json` has `status: PASS`" in body
    assert "zero `issues`" in body
    assert "raw compare report is `FAIL`" in body
    assert "real browser at `1440x900`" in body
    assert "before emitting `PHASE_RESULT: OK`" in body


def test_spec_test_documents_web_runtime_adapter_for_actual_ui_tree() -> None:
    body = _read(".agent-sync/skills/spec-test/SKILL.md")

    assert "Web Runtime Adapter" in body
    assert "real browser at `1440x900`" in body
    assert "write `penflow/actual-ui-tree.json`" in body
    assert "capture screenshots" in body
    assert "data-semantic-id" in body
    assert "penflow validate-actual penflow/actual-ui-tree.json --schema --json" in body
    assert "penflow compare-tree penflow/expected-ui-tree.json penflow/actual-ui-tree.json" in body
    assert "Do not mark `/spec-test` successful" in body
    assert "raw `penflow/compare-report.json` has `status: PASS`" in body
    assert "zero `issues`" in body
    assert (
        "--require-design-registry --require-mockup-validation --feature <feature_slug> --json"
        in body
    )


def test_visual_feature_pipeline_loads_design_conventions_before_ui_work() -> None:
    body = _read(".agent-sync/skills/spec-feature/SKILL.md")

    assert "Convention Gate" in body
    assert "livespec conventions refresh --repo . --full" in body
    assert "before generating `flow-ui-contract`" in body
    assert "design-tokens" in body
    assert "design-components" in body
    assert "design-views" in body
    assert "design-quality" in body
    assert "before `penflow draft-pen-from-tree`" in body
    assert "before implementation and tests" in body
    assert "Set to `NONE` only if refresh fails" in body


def test_visual_feature_pipeline_requires_feature_local_design_proofs() -> None:
    body = _read(".agent-sync/skills/spec-feature/SKILL.md")

    assert ".specs/features/<feature_slug>/design/flow-ui-contract/" in body
    assert ".specs/features/<feature_slug>/design/ui.pen" in body
    assert ".specs/features/<feature_slug>/design/validation/" in body
    assert "root `penflow/` is compatibility/cache" in body
    assert "Do not continue to code against a bad mockup" in body


def test_visual_feature_pipeline_promotes_penflow_to_global_design_registry() -> None:
    body = _read(".agent-sync/skills/spec-feature/SKILL.md")
    expectations = _read(".agent-sync/skills/spec-feature/expectations.md")

    for text in (body, expectations):
        assert "Global LiveSpec Design Registry" in text
        assert ".specs/design/ui.pen" in text
        assert ".specs/design/screens/<feature_slug>/" in text
        assert ".specs/design/baselines/<feature_slug>/" in text
        assert ".specs/design/screens/index.md" in text
        assert ".specs/design/changelog.md" in text

    assert "BLOCKED at step 0.5 - design_registry_sync_failed" in body
    assert "Mockups missing for Penflow UI feature" in body


def test_spec_feature_requires_mockup_factory_before_code() -> None:
    body = _read(".agent-sync/skills/spec-feature/SKILL.md")
    expectations = _read(".agent-sync/skills/spec-feature/expectations.md")

    for text in (body, expectations):
        assert "Mockup Factory" in text
        assert ".mockup-validation/audit-report.md" in text
        assert ".mockup-validation/<feature_slug>/checklist.md" in text
        assert ".mockup-validation/visual-evidence/manifest.json" in text
        assert ".mockup-validation/visual-evidence/visual-report.md" in text

    assert "before Phase 1 and before any application code" in body
    assert "--require-mockup-validation" in body
    assert "status `PASS`" in body
    assert (
        "`PASSED_WITH_WARNINGS`, `ESCALATED`, `BLOCKED`, or "
        "`BLOCKED_VISUAL_NOT_RUN` blocks"
    ) in body


def test_spec_test_requires_global_design_registry_for_penflow_visual_runs() -> None:
    body = _read(".agent-sync/skills/spec-test/SKILL.md")
    expectations = _read(".agent-sync/skills/spec-test/expectations.md")

    for text in (body, expectations):
        assert "Global LiveSpec Design Registry" in text
        assert ".specs/design/ui.pen" in text
        assert ".specs/design/screens/<feature_slug>/" in text
        assert ".specs/design/baselines/<feature_slug>/" in text
        assert ".specs/design/screens/index.md" in text
        assert ".specs/design/changelog.md" in text

    assert "Penflow-backed UI features must never auto-approve when mockups are missing" in body
    assert "Visual Gate Verdict: BLOCKED" in body
    assert (
        "Sync every approved runtime screenshot to `.specs/design/baselines/<feature_slug>/`"
        in body
    )


def test_spec_test_requires_mockup_factory_proof_for_penflow_visual_runs() -> None:
    body = _read(".agent-sync/skills/spec-test/SKILL.md")
    expectations = _read(".agent-sync/skills/spec-test/expectations.md")

    for text in (body, expectations):
        assert ".mockup-validation/audit-report.md" in text
        assert ".mockup-validation/<feature_slug>/checklist.md" in text
        assert ".mockup-validation/visual-evidence/manifest.json" in text
        assert ".mockup-validation/visual-evidence/visual-report.md" in text

    assert "Require Mockup Factory proof" in body
    assert "--require-mockup-validation" in body
    assert "status must be `PASS`" in body


def test_spec_feature_requires_binding_safe_penflow_screen_ids() -> None:
    body = _read(".agent-sync/skills/spec-feature/SKILL.md")

    assert "binding-safe snake_case screen IDs" in body
    assert "Do not use kebab-case screen IDs" in body
    assert "`bookings_dashboard.appointment_card`" in body
    assert "`bookings-dashboard.appointment_card`" in body
    assert "Visible data bullets must start with a letter or underscore" in body
    assert "`Three-column appointment card grid`" in body
    assert "`3-column appointment card grid`" in body
    assert "binding_format" in body


def test_spec_feature_requires_desktop_viewport_and_non_visual_modal_transitions() -> None:
    body = _read(".agent-sync/skills/spec-feature/SKILL.md")

    assert "`platform: web-desktop`" in body
    assert "`viewport: \"1440x900\"`" in body
    assert "Escape/backdrop must be flow transitions only" in body
    assert "Do not add `Escape key`, `Backdrop click`, or `Click backdrop`" in body
    assert "visible action rows" in body


def test_spec_feature_blocks_instead_of_manual_penflow_fallback() -> None:
    body = _read(".agent-sync/skills/spec-feature/SKILL.md")

    assert "/Users/julienm/projects/penflow/.venv/bin/penflow" in body
    assert "penflow_cli_missing" in body
    assert "Never manually fabricate `ui.pen`" in body


def test_spec_feature_auto_mode_does_not_commit_without_explicit_authorization() -> None:
    body = _read(".agent-sync/skills/spec-feature/SKILL.md")
    expectations = _read(".agent-sync/skills/spec-feature/expectations.md")

    assert (
        "No commits are made by `/spec-feature` unless the user explicitly asks for a commit"
        in body
    )
    assert "Auto mode prepares commit context only" in body
    assert "Auto-commit" not in expectations
    assert "commits automatically" not in body
    assert "Auto-commit sequence" not in body
    assert "Branch proposal" not in body
    assert "git checkout -b" not in body
    assert "commit expectations" in expectations
    assert "none unless explicitly authorized" in expectations


def test_spec_feature_recovers_when_phase_agent_writes_artifact_without_result() -> None:
    body = _read(".agent-sync/skills/spec-feature/SKILL.md")

    assert "Phase Agent Timeout and Artifact Recovery" in body
    assert "plan.md exists but no PHASE_RESULT" in body
    assert (
        "livespec pipeline update --feature NNN-feature-name --phase plan --status done --timestamp"
        in body
    )
    assert "continue to Phase 2.5" in body
    assert "progress.md" in body and "implementation.md" in body
    assert "BLOCKED - phase_agent_timeout" in body


def test_ui_commands_reference_penflow_contract_artifacts() -> None:
    specify = _read(".agent-sync/skills/spec-specify/SKILL.md")
    plan = _read(".agent-sync/skills/spec-plan/SKILL.md")
    implement = _read(".agent-sync/skills/spec-implement/SKILL.md")
    test = _read(".agent-sync/skills/spec-test/SKILL.md")
    check = _read(".agent-sync/skills/spec-check/SKILL.md")

    assert "penflow/semantic-ui-tree.json" in specify
    assert "flow_id" in specify and "screen_id" in specify
    assert "penflow/code-ir.json" in plan
    assert "penflow/expected-ui-tree.json" in implement
    assert "Penflow Contract Gate" in test
    assert "--require-actual" in test
    assert "penflow compare-tree" in test
    assert "Penflow Contract Status" in check
    assert "do not read `.brainstorm/`" in check


def test_command_expectations_include_penflow_verdicts() -> None:
    for skill in ("spec-init", "spec-specify", "spec-plan"):
        body = _read(f".agent-sync/skills/{skill}/expectations.md")
        assert "Penflow Contract Verdict: ABSENT | BLOCKED | PASS" in body

    for skill in ("spec-implement", "spec-test", "spec-check"):
        body = _read(f".agent-sync/skills/{skill}/expectations.md")
        assert "Penflow Contract Verdict: ABSENT | PASS | FAIL | BLOCKED" in body
