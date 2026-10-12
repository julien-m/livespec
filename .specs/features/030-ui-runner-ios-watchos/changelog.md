## 2026-05-06 — [Spec Update]: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-014 (all defined)
- **Author:** spec.specify

## 2026-10-12 — [Refactor]: Surface generator tests assert parsed output

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/integration/test_surfaces_xcuitest.py, tests/integration/helpers/surfaces_script.py (new)
- **AC impacted:** None
- **Author:** Claude Code (test-suite cleanup, lot 1)
- Tests parse the YAML that generate-surfaces.js would write instead of searching stdout for 'xcuitest'; three Android cases duplicated from test_surfaces_maestro.py removed; explicit skip when `node` is absent.
