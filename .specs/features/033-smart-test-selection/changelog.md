## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

# Changelog — Smart Test Selection

---

### 2026-05-07 — In Progress: Core SmartTestSelector module

- **Type:** Implementation
- **Spec modified:** Yes (status corrected to In Progress)
- **Code modified:** Added `validator/selector.py` and `tests/test_selector.py` (22 unit tests)
- **AC impacted:** AC-001, AC-002, AC-003, AC-005, AC-006, AC-007, AC-010, AC-011
- **Author:** claude-code

**Key deliverables:**
- Core `SmartTestSelector` class with anchor parsing, heuristic fallback, cache handling, and git diff integration
- Test target resolution from `implementation.md`, plus fallback project test scanning
- 22 unit tests covering selector behavior and failure paths
- Hook integration, CLI wiring, and `.gitignore` migration remain separate follow-up work
