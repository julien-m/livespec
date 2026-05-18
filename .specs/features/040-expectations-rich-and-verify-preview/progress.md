---
created_at: '2026-05-12'
current_state: Done
feature_slug: 040-expectations-rich-and-verify-preview
owner_command: spec-implement
schema_version: 1
updated_at: '2026-05-12'
---

# Progress — Feature 040

| Step | Status | Notes |
|------|--------|-------|
| 1. Enrich template | Done | system/templates/command-expectations.template.md |
| 2. Parser Section 13 | Done | validator/expectations.py |
| 3. Migrate 20 expectations files | Done | scripts/migrate_expectations_section13.py |
| 4. Preview module | Done | validator/preview.py |
| 5. CLI --preview / --save | Done | validator/cli_commands/verify_output_cmd.py |
| 6. Tests (preview unit + CLI + snapshot) | Done | 12 + 6 + 3 tests, all pass |
| 7. Docs (verify-output.md) | Done | triad workflow documented |
