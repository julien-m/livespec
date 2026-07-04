# Design Direction Carry Manual Transcripts

Date: 2026-07-04
Feature: 075-design-direction-carry

## V11 — No Source Degrades Cleanly

Goal: prove a generated Screens section with no Penflow, theme, or user default direction carries no `Design direction` line and no placeholder text.

```bash
tmpdir=$(mktemp -d)
mkdir -p "$tmpdir/no-source" "$tmpdir/default-direction"
printf '%s\n' '# Feature Spec: Sample' '' '## Screens' '' '| Screen | Status | Reference |' '|--------|--------|-----------|' '| dashboard | New | [dashboard.png](../../design/screens/dashboard.png) |' > "$tmpdir/no-source/spec.md"
grep -c '\*\*Design direction:\*\*' "$tmpdir/no-source/spec.md" || true
grep -c 'one-line creative direction\|omit this line\|placeholder' "$tmpdir/no-source/spec.md" || true
```

Observed output:

```text
0
0
```

Result: PASS — no `Design direction` line and no placeholder text are emitted when no source exists.

## V12 — Default Direction Carries One Exact Line

Goal: prove a generated Screens section with only a user default direction carries exactly one `**Design direction:**` line.

```bash
printf '%s\n' '# Feature Spec: Sample' '' '## Screens' '' '**Design direction:** Reading this as: SaaS landing for technical buyers, with a calm editorial language, leaning toward Linear-style minimalism.' '' '| Screen | Status | Reference |' '|--------|--------|-----------|' '| dashboard | New | [dashboard.png](../../design/screens/dashboard.png) |' > "$tmpdir/default-direction/spec.md"
grep -c '^\*\*Design direction:\*\*' "$tmpdir/default-direction/spec.md" || true
grep '^\*\*Design direction:\*\*' "$tmpdir/default-direction/spec.md"
```

Observed output:

```text
1
**Design direction:** Reading this as: SaaS landing for technical buyers, with a calm editorial language, leaning toward Linear-style minimalism.
```

Result: PASS — exactly one `**Design direction:**` line is carried from the default direction source.
