<!-- @spec FR-003, FR-004, FR-005, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012: Reference doc — .specs/features/039-command-expectations-and-verify-output/spec.md -->

# Command Expectations & Verify Output — Reference

> The canonical reference for the `commands/<X>.expectations.md` contract files,
> the `RunArtifact` JSON schema, the `verify:` YAML grammar, the override
> resolver, the pre-commit `last_reviewed` hook, and the 4-state outcome
> classifier consumed by `/spec.verify-output`.

## 1. File Layout

| File | Owner | Purpose |
|------|-------|---------|
| `system/templates/command-expectations.template.md` | LiveSpec | Canonical 12-section template + `verify:` YAML stub. |
| `commands/<X>.expectations.md` | LiveSpec (builtin) | One per slash-command. Source of truth absent a project override. |
| `.specs/expectations/<X>.md` | Per-project (override) | Totally replaces the builtin (no merge). |
| `.specs/.runs/<X>-<ISO>.json` | Per-project (runtime) | Run artifact written by every `/spec.*` command. Gitignored. |

## 2. Frontmatter Schema

```yaml
---
command: <name>           # required, snake or hyphen-case
contract_version: "1.0"   # required string
last_reviewed: YYYY-MM-DD # required ISO date — enforced by pre-commit hook
---
```

The pre-commit hook (`hooks/livespec-last-reviewed.py`) blocks any commit that
modifies `commands/<X>.md` unless the corresponding
`commands/<X>.expectations.md` frontmatter `last_reviewed` equals today's date.

## 3. The 12 Prose Sections

Each expectations file MUST contain these 12 sections, in order, with the
exact level-2 headings shown below (numeric prefix included):

1. `## 1. Purpose`
2. `## 2. Preconditions`
3. `## 3. Observable Signals`
4. `## 4. Filesystem Effects`
5. `## 5. Git Effects`
6. `## 6. Produced Artifacts`
7. `## 7. Exit Codes`
8. `## 8. Outcome Matrix`
9. `## 9. Runtime Profile`
10. `## 10. Post-run Checks`
11. `## 11. Troubleshooting`
12. `## 12. Verify Contract`

The parser (`validator/expectations.py`) raises `ExpectationsInvalid` when any
section is missing.

## 4. `verify:` YAML Grammar

Section 12 embeds a fenced ` ```yaml ` block whose top-level key is `verify:`.

```yaml
verify:
  must:        # list of Rule
  may:         # list of Rule
  must_not:    # list of Rule
  when:        # list of WhenBranch (optional)
```

### Rule kinds

| Kind                | Payload                                                       |
|---------------------|---------------------------------------------------------------|
| `contains`          | substring expected in stdout+stderr                           |
| `exists`            | filesystem path that must exist after the run                 |
| `exit_code`         | integer exit code                                             |
| `produces_artifact` | `{produces_artifact: <path>, contains_sections: [<header>…]}` |

### WhenBranch

```yaml
- flag: "--visual"
  must: []
  may: []
  must_not: []
```

A `WhenBranch` activates only when `RunArtifact.flags` contains the declared
flag. Multiple matching branches accumulate — their rules are logically ANDed
with the base rules.

### Placeholders

Resolved at evaluation time:

- `<feature>` → active feature directory name (derived from cwd or `--feature`).
- `<date>` → run artifact `timestamp` (date portion only, YYYY-MM-DD). **Never
  commit date** — see EC-006.
- `<path>` → passthrough; used inside larger path templates.

### Rule independence (no short-circuit)

The verifier evaluates `must`, `may`, and `must_not` as **independent buckets**.
Failing a `must` rule does not skip `must_not` evaluation, and vice versa.
Overlapping substrings (e.g. `must: contains "error"` and
`must_not: contains "fatal error"`) are both evaluated against the same raw
output. Enforced by `tests/test_verify_output.py::test_must_not_rules_are_independent_of_must_rules_no_short_circuit`.

## 5. `RunArtifact` JSON Schema

Written under `.specs/.runs/<command>-<ISO>.json`.

```json
{
  "command": "specify",
  "timestamp": "2026-05-12T10:00:00Z",
  "flags": ["--visual"],
  "exit_code": 0,
  "duration_ms": 312000,
  "cwd": "/abs/path",
  "git_state_before": {"branch": "main", "head_sha": "abc123", "dirty": []},
  "git_state_after":  {"branch": "main", "head_sha": "abc123", "dirty": [".specs/features/001/spec.md"]},
  "fs_observed": [
    {"path": ".specs/features/001/spec.md", "change": "create"}
  ],
  "stdout": "...",
  "stderr": "..."
}
```

Required keys: `command`, `timestamp`, `flags`, `stdout`, `stderr`,
`exit_code`, `duration_ms`, `cwd`, `git_state_before`, `git_state_after`,
`fs_observed`.

Artifacts are atomic-written (`.tmp` then `os.replace`). Lexicographically
sortable timestamps; the verifier picks the latest filename (EC-009).
Rotation: 21st artifact triggers move-to-`_archive/` of the oldest.

## 6. Override Lookup

```
1. <project_root>/.specs/expectations/<command>.md   ← project override (total)
2. <livespec_root>/commands/<command>.expectations.md ← builtin
```

First file found wins. The override **totally replaces** the builtin —
no prose merge, no YAML merge. If the override is malformed,
`/spec.verify-output` exits 2 with `Blocked By: override missing verify: block`
(or similar) — it does **NOT** silently fall back to the builtin (AC-007).

## 7. Pre-commit Hook Contract

`hooks/livespec-last-reviewed.py` is invoked by `.git/hooks/pre-commit` (via
`scripts/install-hooks.sh`). For each staged `commands/<X>.md` (excluding
`*.expectations.md` itself):

1. Locate `commands/<X>.expectations.md`. If missing → block with message
   naming the missing file.
2. Read frontmatter `last_reviewed`. If missing or `!= today` → block with the
   exact recovery message:

   ```
   Relis `commands/<X>.expectations.md`, bump `last_reviewed`, recommit.
   ```

3. Exit 0 if all checks pass.

The hook is portable Python stdlib (no `pyyaml` import) so it runs in any
environment with Python 3.11+.

### Renaming a command

Renaming `commands/<old>.md` → `commands/<new>.md` is a multi-file ceremony.
All of these MUST be done **in the same commit**:

1. Rename `commands/<old>.md` → `commands/<new>.md`.
2. Rename `commands/<old>.expectations.md` → `commands/<new>.expectations.md`.
3. Update the `command:` frontmatter field inside the renamed expectations file.
4. Bump `last_reviewed` to today.
5. Update `.specs/spec-system.md` `### Command discovery` paragraph to list the
   new name and drop the old one.
6. Search tests for references to the old name (`grep -rn "<old>"`) and update.
7. Add a changelog entry summarising the rename.

The 19-file invariant (AC-002) is enforced against the **current** list in
`.specs/spec-system.md`; commits that rename a command without updating the
discovery list will fail downstream coherence checks.

## 8. Outcome Classifier (4 states)

`validator/outcome.py` maps the final result to one of four states:

| State     | Conditions                                                   | verify exit |
|-----------|--------------------------------------------------------------|-------------|
| `success` | every `must` rule passes AND artifact exit_code == 0         | 0           |
| `drift`   | at least one `must` rule fails AND artifact exit_code == 0   | 1           |
| `error`   | artifact exit_code != 0                                      | 1           |
| `blocked` | artifact missing, override malformed, expectations missing   | 2           |

`drift` and `error` are explicitly distinguished in the report and JSON
output: drift = command succeeded but contract diverged; error = command itself
crashed.

## 9. Placeholders & Edge Cases (summary)

- EC-001: whitespace-only diff to `commands/X.md` still triggers the hook.
- EC-002: malformed override → blocked, no fallback to builtin.
- EC-003: no run artifact → blocked.
- EC-004: multiple active `when:` branches accumulate (ANDed).
- EC-005: overlapping substrings are evaluated independently — no short-circuit.
- EC-006: `<date>` placeholder resolves from artifact timestamp, never commit date.
- EC-007: malformed artifact JSON → blocked with `ArtifactMalformed`.
- EC-008: command rename → multi-file ceremony (§7).
- EC-009: multiple artifacts → lexicographically latest wins.
- EC-010: `when:` flag never accepted by command → branch never activates (no error).
