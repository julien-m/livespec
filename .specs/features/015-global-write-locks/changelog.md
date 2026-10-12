## 2026-10-12 — [Refactor]: Lock tests exercise the real resume and timeout paths

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_locks.py
- **AC impacted:** None
- **Author:** claude-code (test-suite cleanup lot 3)

`test_resumes_when_reserved_marker_present` never reached the resume branch (it asserted a new slot); it now forces the scan/mkdir race and asserts `resumed=True`, and the next-slot case keeps its own honest test. The collision test lost its dead setup; the 10 s default timeout is proved with a held lock and a fake clock instead of a constant comparison.

## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

# Changelog — Feature 015: Global Write Locks & Atomic NNN Reservation

### 2026-05-06 — Fix: implementation.md created (post-merge bookkeeping)

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** None — only `implementation.md` produced from existing `@spec` anchors
- **Gaps closed:** Missing FR→file mapping document. Code shipped via PR #23 without running `/spec.implement`.
- **Remaining:** None
- **Author:** spec.fix

### 2026-05-03 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-010 (all defined)
- **Author:** /spec.specify --auto (Chantier 3 from AUDIT.md)
