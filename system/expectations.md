<!-- LiveSpec traceability anchors -->
<!-- @spec(AC-010) -->
<!-- @spec(FR-011) -->

<!-- @spec FR-003, FR-004, FR-005, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012: Reference doc — .specs/features/039-command-expectations-and-verify-output/spec.md -->
<!-- @spec FR-011: Shared command runtime docs — .specs/features/052-deterministic-command-goal-contracts/spec.md#fr-011 -->

# Command Expectations & Verify Output — Reference

> The canonical reference for `.agent-sync/skills/<X>/expectations.md` contract files,
> the `verify:` YAML grammar, the override resolver, the pre-commit `last_reviewed`
> hook, and the 4-state outcome classifier used by the goal contract system.

## 1. File Layout

| File | Owner | Purpose |
|------|-------|---------|
| `system/templates/command-expectations.template.md` | LiveSpec | Canonical 12-section template + `verify:` YAML stub. |
| `.agent-sync/skills/<X>/expectations.md` | LiveSpec (builtin) | One per slash-command skill. Source of truth absent a project override. |
| `.specs/expectations/<X>.md` | Per-project (override) | Totally replaces the builtin (no merge). |

## 2. Frontmatter Schema

```yaml
---
command: <name>           # required, snake or hyphen-case
contract_version: "1.0"   # required string
last_reviewed: YYYY-MM-DD # required ISO date — enforced by pre-commit hook
---
```

The pre-commit hook (`hooks/livespec-last-reviewed.py`) blocks any commit that
modifies `.agent-sync/skills/<X>/SKILL.md` unless the corresponding
`.agent-sync/skills/<X>/expectations.md` frontmatter `last_reviewed` equals
today's date.

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

A `WhenBranch` activates only when the command's active flags contain the declared
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
output — no short-circuit.

## 6. Override Lookup

```
1. <project_root>/.specs/expectations/<command>.md   ← project override (total)
2. <livespec_root>/.agent-sync/skills/<command>/expectations.md ← builtin
```

First file found wins. The override **totally replaces** the builtin —
no prose merge, no YAML merge. If the override is malformed, the goal compiler raises `ExpectationsInvalid`
and the command is blocked — it does **NOT** silently fall back to the builtin.

## 7. Pre-commit Hook Contract

`hooks/livespec-last-reviewed.py` is invoked by `.git/hooks/pre-commit` (via
`scripts/install-hooks.sh`). For each staged `.agent-sync/skills/<X>/SKILL.md`:

1. Locate `.agent-sync/skills/<X>/expectations.md`. If missing → block with message
   naming the missing file.
2. Read frontmatter `last_reviewed`. If missing or `!= today` → block with the
   exact recovery message:

   ```
   Relis `.agent-sync/skills/<X>/expectations.md`, bump `last_reviewed`, recommit.
   ```

3. Exit 0 if all checks pass.

The hook is portable Python stdlib (no `pyyaml` import) so it runs in any
environment with Python 3.11+.

### Renaming a command

Renaming `.agent-sync/skills/<old>/` → `.agent-sync/skills/<new>/` is a multi-file ceremony.
All of these MUST be done **in the same commit**:

1. Rename `.agent-sync/skills/<old>/` → `.agent-sync/skills/<new>/`.
2. Update `SKILL.md` frontmatter name/description if needed.
3. Update the `command:` frontmatter field inside `expectations.md`.
4. Bump `last_reviewed` to today.
5. Update `.specs/spec-system.md` `### Command discovery` paragraph to list the
   new name and drop the old one.
6. Search tests for references to the old name (`grep -rn "<old>"`) and update.
7. Add a changelog entry summarising the rename.

The command inventory invariant is enforced against the **current** list in
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

## 8.5 Deterministic Command Goals

Feature 052 layers deterministic runtime goals on top of this expectations system.
The goal compiler reads the same expectations file resolved by §6, extracts the
command Definition of Done from `.agent-sync/skills/<X>/SKILL.md`, normalizes
active flags, and writes a canonical JSON payload with sorted keys and no
wall-clock fields. Runtime completion is stateful: the immutable `contract.json`
lists ordered tasks and required evidence, while the mutable `state.json` can
only be updated by `livespec goal prove`.

CLI:

```bash
livespec goal render <command> --feature <feature> --flags "<flags>" --save
```

- Same project state + command + feature + flags + expectations + SKILL.md → same canonical JSON and SHA-256 hash.
- `--save` writes `$TMPDIR/livespec-goals/goal-<cmd>-<hash8>.contract.json` and `$TMPDIR/livespec-goals/goal-<cmd>-<hash8>.state.json`, then prints `hash:<sha256> | contract-file:<path> | state-file:<path>`.
- `livespec goal prove --contract <contract-file> --state <state-file> --task <task-id> --evidence '<json>'` is the only mechanism allowed to mark a task `complete`; missing proof returns `REJECTED_NEEDS_ACTION`.
- `livespec goal status --state <state-file>` reports aggregate completion before a command may emit `DONE`.
- If `.conventions/index.md` exists, the goal embeds selected convention domains, source paths, source content, and content hashes. `code` is selected by default; `design-*` domains are selected for UI/mockup/visual/CSS/screen/theme/baseline/Penflow signals.

## 9. Placeholders & Edge Cases (summary)

- EC-001: whitespace-only diff to `.agent-sync/skills/X/SKILL.md` still triggers the hook.
- EC-002: malformed override → blocked, no fallback to builtin.
- EC-003: multiple active `when:` branches accumulate (ANDed).
- EC-004: overlapping substrings are evaluated independently — no short-circuit.
- EC-005: command rename → multi-file ceremony (§7).
- EC-006: `when:` flag never accepted by command → branch never activates (no error).
