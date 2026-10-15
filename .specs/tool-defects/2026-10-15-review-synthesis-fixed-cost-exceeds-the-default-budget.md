# Tool defect: Review synthesis fixed cost exceeds the default budget

- **Status:** blocked-by-tool
- **Date:** 2026-10-15
- **Feature:** —
- **Phase:** —
- **Runtime mode:** unpinned
- **Runtime runtime_path:** /Users/julienm/.livespec/versions/21-71f1e0d1b3d3

## Command

```text
livespec validate .specs/features/083-pinned-runtime-isolation --ingest-review <bundle> --review-kind plan --model claude-opus-5-5 (prepared with --review-max-chars 60000)
```

## Error

```text
synthesis_context_over_budget (validate_review_result on the 4 actual plan batch results: synthesis_prompt 67069 chars > max_chars 60000; fixed cost with empty batch results 34559 chars: invariants 22462, requirements 6131, section ids 1759; per-batch floor ~2.9k-10.2k because ids under 48 chars are not shared, keys are escaped, plan_citations are mandatory and unapproved extra_scope is copied into the issue ledger)
```

## Resume

1. `livespec runtime pin --runtime <fixed runtime>` once a fixed runtime is installed
2. resume the blocked work
