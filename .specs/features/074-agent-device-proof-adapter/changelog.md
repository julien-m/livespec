# Changelog: Agent Device Proof Adapter (074)

## 2026-07-04 - [Feature]: Agent Device proof adapter

- **Type:** Feature
- **Spec modified:** Yes (new feature spec, plan, progress, implementation map)
- **Code modified:** validator/journeys/runner.py, validator/cli_commands/journey_cmd.py, validator/cli_commands/device_cmd.py, validator/cli_commands/__init__.py
- **AC impacted:** AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007, AC-008, AC-009, AC-010
- **Author:** tool-worker

### Highlights

- Journey runs now record destination/UDID metadata and write last-run receipts under `journey_runs_dir()`.
- `livespec journey run --json` exposes `runs[]` for replay/proof tooling.
- `livespec device proof` binds Agent Device calls with `--udid` and `--session`, rejects watchOS, checks installed bundles, guards foreground mismatch, and verifies screenshot output.
