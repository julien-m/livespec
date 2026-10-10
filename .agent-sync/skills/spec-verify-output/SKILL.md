---
name: spec-verify-output
description: LiveSpec slash command /spec-verify-output
---
<!-- LiveSpec traceability anchors -->
<!-- @spec(AC-010) -->
<!-- @spec(FR-005) -->
<!-- @spec(FR-006) -->
<!-- @spec(FR-007) -->


# /spec-verify-output

---
description: "Verify a command run artifact against its expectations"
argument-hint: "<command-name>"
---

> **Read** [`system/anti-drift-block.md`](../../../system/anti-drift-block.md) before starting — 6-field step shape (§1), ERROR/BLOCKED format (§2).

# Command: /spec-verify-output

Verify a LiveSpec command output artifact against the command's `expectations.md` contract.

---

## Internal Command Invocations

_(none — this command calls the `livespec verify-output` CLI, not nested `/spec-*` commands.)_

## Usage

```bash
/spec-verify-output <command>
/spec-verify-output <command> --scenario "<flags>"
/spec-verify-output <command> --run <path>
/spec-verify-output <command> --json
/spec-verify-output <command> --feature <name>
/spec-verify-output <command> --preview --save
```

## Execution Tasks

> Machine-readable task inventory parsed by `livespec goal render`.
> Format: `- [branch] task description`

- [always] Resolve target command name and normalize active scenario flags <!-- evidence:documentary -->
- [always] Locate builtin or project override expectations for the target command <!-- evidence:documentary -->
- [always] Locate the latest `.specs/.runs/<command>-*.json` artifact, unless `--run` or `--preview` is provided <!-- evidence:documentary -->
- [always] Execute `livespec verify-output <command>` with the resolved flags/run/preview options <!-- evidence:documentary -->
- [always] Surface outcome `success`, `drift`, `error`, or `blocked` exactly as reported by the CLI <!-- evidence:documentary -->
- [always] If `--json` is active, return the JSON envelope without prose rewriting <!-- evidence:documentary -->
- [always] If `--preview --save` is active, report the `.specs/.previews/<command>-*.md` path <!-- evidence:documentary -->

## Definition of Done (Command-Level)

`/spec-verify-output` is complete only if all are true:

- [ ] Target command expectations were resolved or canonical BLOCKED was emitted <!-- evidence:documentary -->
- [ ] Run artifact was resolved, or preview mode was explicitly active <!-- evidence:documentary -->
- [ ] `livespec verify-output` executed with the requested flags <!-- evidence:documentary -->
- [ ] Outcome was reported exactly <!-- evidence:documentary -->
- [ ] No source, spec, or expectation files were modified <!-- evidence:documentary -->
