# Migration Version Bump

## When
Staged files match `migrations/**`

## Verify
When any file under `migrations/` is added or modified, the `VERSION` file at the repo root must be updated to match the highest migration number present in `migrations/`. Verify that `VERSION` equals `ls migrations/ | sort -n | tail -1`.
