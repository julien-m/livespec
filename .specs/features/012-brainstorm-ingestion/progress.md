# Progress: 012-brainstorm-ingestion

| Step | Description | Status | Tests | Notes |
|---|---|---|---|---|
| 0 | Infrastructure Setup | Skipped | n/a | No cloud resources |
| 1 | Define ingestion schemas | Done | n/a | `validator/brainstorm/schemas.py` — incl. ScreenAnnex (Finding #5) |
| 2 | Slug & NNN allocation | Done | 10/10 | `validator/brainstorm/slug.py` |
| 3 | Flow grammar validator | Done | 8/8 | incl. `test_empty_surfaces_rejected` (Finding #4) |
| 4 | Flow → spec converter | Done | 8/8 | `validator/brainstorm/convert.py` |
| 5 | Project profile & roadmap | Done | 5/5 | `project_seed.py` + `roadmap.py` |
| 6 | Two-phase atomic writer | Done | 6/6 | `apply.py` — partial-apply hint in refine (Finding #1); rationale docstring (Finding #2/#3) |
| 7 | Detection & CLI subcommand | Done | smoke | `detect.py`, `cli.py` (rationale docstring); registered in `validator/cli.py` |
| 8 | Wire /spec.init | Done | manual | `commands/init.md` Pre-Check Brainstorm Ingestion |
| 9 | Wire /spec.refine --import-brainstorm | Done | manual | `commands/refine.md` Step 0.5 + flag table |
| 10 | Documentation sync | Done | n/a | README.md workflow section added |
| 11 | Tests | Done | 37/37 | 501/501 full unit suite green |

## Verification summary

- `ruff check validator/brainstorm/ tests/test_brainstorm_*.py` → all checks passed
- `pytest tests/ --ignore=tests/integration --ignore=tests/visual --ignore=tests/feature-010` → 501 passed
- `python3 -m validator.cli brainstorm --help` → CLI registers detect / validate / plan / apply
