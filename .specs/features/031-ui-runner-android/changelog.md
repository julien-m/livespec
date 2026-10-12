## 2026-10-12 — [Refactor]: Android manifest tests consolidated around the production loader

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_maestro_manifest.py, implementation.md (AC-001 row)
- **AC impacted:** AC-001, AC-003
- **Author:** claude-code (test-suite cleanup lot 3)

37 one-line key/value checks became one structural test loaded through `load_maestro_runner_manifest`, the AC-003 priority test, and a new check that every declared detect file/dir is honoured by `MaestroRunnerHandler.detect()`.

## 2026-05-06 — [Spec Update]: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-013 (all defined)
- **Author:** spec.specify

## 2026-10-12 — [Refactor]: Surface generator tests assert parsed output

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/integration/test_surfaces_maestro.py, tests/integration/helpers/surfaces_script.py (new)
- **AC impacted:** None
- **Author:** Claude Code (test-suite cleanup, lot 1)
- Tests parse the generated surfaces (runner, platform, path, testDir) instead of searching stdout for 'maestro'; explicit skip when `node` is absent.
