---
feature: 068-evidence-first-retry-contract
status: Implemented
updated: 2026-06-26
---

# Progress — Evidence-First Retry Contract

| Step | Status | Evidence |
|---|---|---|
| Add failing regression test | Done | Focused test failed before docs changed. |
| Add shared anti-drift retry contract | Done | `system/anti-drift-block.md` contains `retry_hypothesis`, `retry_evidence`, `retry_result`. |
| Add command-local reminders | Done | Six high-signal goal-locked command skills contain `STEP 0.8`. |
| Map feature artifacts | Done | `spec.md`, `plan.md`, `implementation.md`, `changelog.md`, `progress.md` created. |
| Verify | Done | `python3 -m pytest tests/test_conventions_pipeline_docs.py -q` passed; `python3 -m pytest tests/test_conventions_pipeline_docs.py tests/test_goal_contracts.py -q` passed; `ruff check tests/test_conventions_pipeline_docs.py` passed; `livespec validate .specs` passed. |
