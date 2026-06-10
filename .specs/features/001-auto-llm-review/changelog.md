## 2026-04-13 — [Check]: Spec-code alignment verified

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **Coverage:** 11/11 FR verified (100%), 14/14 AC verified (100%)
- **Report:** `checks/2026-04-13.md`
- **Author:** spec.check

---

## 2026-04-13 — [Feature]: Initial implementation of auto LLM review

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** validator/semantic/spec_review.py (new), validator/semantic/review_api.py (new), validator/orchestrator.py, validator/cli.py, validator/exceptions.py, tests/test_spec_review.py (new), tests/test_review_api.py (new), tests/test_cli.py
- **AC impacted:** AC-001 through AC-014 (all satisfied)
- **Author:** claude-code

---

## 2026-04-13 — [Plan]: Technical plan generated

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** None (plan.md created)
- **AC impacted:** None (pre-implementation)
- **Author:** spec.plan

---

## 2026-04-13 — [Spec]: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created -- all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-014 (all defined)
- **Author:** spec.specify

### 2026-06-10 — ## [Bugfix]: cc-hub codex provider — schema passing repaired

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** examples/provider-cchub.py
- **AC impacted:** none (provider bridge example)
- **Author:** claude
- **Detail:** `_call_codex` passed the JSON schema inline to `cc-hub codex --schema`, which only accepts a file path (os error 63). Now writes the schema to a temp file, unwraps the response_format envelope, and normalizes `additionalProperties: false` for OpenAI strict mode. Verified end-to-end with the real plan-review `_REVIEW_SCHEMA`.

<!-- finalize:spec-fix:2026-06-10:24ee3265 -->
