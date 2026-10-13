# Changelog - 087-anchor-derived-acceptance

## 2026-10-13 — [Feature]: Acceptance mapping derived from @spec test anchors

- **Type:** Feature
- **Spec modified:** Yes (created: two stories, six AC, six FR, two SC)
- **Code modified:** validator/acceptance_anchors.py, validator/acceptance_anchors_rust.py, validator/execution_mapping.py, validator/execution_mapping_anchors.py, validator/execution_rust_source.py, validator/execution_evidence.py, validator/cli_commands/{test_cmd,execution_io,operation_options}.py, system/testing/execution-rules.md, spec-implement skill
- **AC impacted:** AC-001 through AC-006
- Read [spec](spec.md), [plan](plan.md) and [implementation](implementation.md): `livespec test --feature <f> --acceptance-mapping <path> --derive-mapping` writes the mapping from `@spec AC-xxx` anchors, refuses orphan ACs and unknown anchors, and certification re-derives it instead of requiring a mapping review. The anchors of 086, 087 and 088 on this repository derive with no issue.
