# Progress — Conventions Bootstrap Remediation

## Status

| Step | Status | Evidence |
|---|---|---|
| Specify feature behavior | Complete | `spec.md` defines AC-001..AC-016 and FR-001..FR-012 |
| Plan implementation approach | Complete | `plan.md` records implementation and verification strategy |
| Add RED tests for preflight conventions items | Complete | `tests/test_preflight_autofix.py` covers gates-derived checks |
| Implement preflight conventions items | Complete | `validator/preflight_autofix.py` derives conventions preflight requirements |
| Add RED tests for scaffold templates | Complete | `tests/test_status_play_conventions_cli.py` covers scaffold behavior |
| Implement scaffold templates | Complete | `templates/conventions/` contains Python and TypeScript templates |
| Add RED tests for `$spec-fix --conventions` docs | Complete | `tests/test_conventions_pipeline_docs.py` covers command docs |
| Document `$spec-fix --conventions` | Complete | `.agent-sync/skills/spec-fix/SKILL.md` documents the mode |
| Add RED tests for CLI split and line limits | Complete | Static tests cover route preservation and module size |
| Split conventions CLI | Complete | `validator/cli_commands/conventions_cmd.py` owns conventions routes |
| Run full verification | Complete | `implementation.md` records verification evidence |
