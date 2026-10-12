# Changelog - 045-native-behavioral-specs

## 2026-10-12 — [Refactor]: specStatus guard test reads the producer's file

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_native_behavioral_specs.py
- **AC impacted:** AC-017
- **Author:** claude-code (test-suite cleanup lot 3)

`test_specStatus_manual_target_protected` parsed a file written by the test itself (python-frontmatter only); it now writes the artefact through `apply_validation_gate` and reads the marker from that file.
