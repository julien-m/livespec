# Command Validation Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every `/spec.*` command auditable to a 5/5 standard: deterministic registry, deterministic contract checks, mandatory run-artifact verification, and no stale command documentation.

**Architecture:** Keep slash commands as the user-facing orchestration layer, but move all "can this command be trusted?" checks into Python/Bash validators. A command may still use LLM orchestration for generation or implementation, but it cannot report success unless deterministic validators prove required files, output signals, exit status, hooks, routing docs, and run artifacts are aligned.

**Tech Stack:** Python 3.11+ Typer CLI, pytest, Bash scripts, existing LiveSpec `validator.*` modules, existing `commands/*.md` and `commands/*.expectations.md` contracts.

---

## Audit Baseline

Commands already run during audit:

```bash
python3 -m pytest tests/test_builtin_expectations_corpus.py tests/test_expectations.py tests/test_verify_output.py tests/test_verify_output_cli.py tests/test_cli_unified.py
# 124 passed

python3 -m pytest tests/test_run_artifact.py tests/test_verify_output_end_to_end.py tests/test_hooks_cli.py tests/test_integrations.py tests/test_atomic_command_hooks.py tests/test_coherence_cli.py tests/test_contracts.py tests/test_state_files.py
# 94 passed

bash scripts/audit-antidrift-coverage.sh
# exit 0

bash scripts/check-coherence.sh
# exit 1: obsolete COMMANDS/AGENTS extraction and stale hook docs check
```

Facts found:

- There are 20 canonical slash commands, from `validator.integrations.valid_command_names()`.
- Every command has `commands/<name>.md` and `commands/<name>.expectations.md`.
- Every command imports `system/anti-drift-block.md`.
- `livespec verify-output` and `livespec run` are implemented and tested.
- `scripts/check-coherence.sh` is stale: it expects `COMMANDS=(...)` and `AGENTS=(...)`, but `scripts/install.sh` now has `BOOTSTRAP_COMMANDS=(init migrate)`.
- Several docs are stale: `system/spec-system.md` says 19 commands, `scripts/init.sh` lists only 13 commands, `commands/hooks.md` omits `verify-output`.
- `/spec.play-coverage` expectations describe server/data artifacts that the actual `scripts/play-coverage.sh` does not create.
- Only `/spec.feature` and `/spec.verify-output` currently mention run-artifact finalization. Most commands can finish without producing `.specs/.runs/<command>-*.json`.

## 5/5 Definition

A command is 5/5 only when all checks below pass:

1. `commands/<name>.md` exists and imports `system/anti-drift-block.md`.
2. `commands/<name>.expectations.md` exists, parses, has fresh `last_reviewed`, Section 13, `must_not: Traceback`, and at least one `exit_code` rule.
3. `.claude/rules/livespec-commands.md` has exactly one `### /spec.<name>` entry.
4. Hook/integration resolution accepts the command through the dynamic registry.
5. The command either has a deterministic CLI backend or a documented deterministic gate after LLM orchestration.
6. The command records a `RunArtifact` and verifies it with `verify-output` or the new finalization command before reporting success.
7. Static audit scripts and pytest tests fail when any command is missing from docs, routing, hooks, expectations, or finalization gates.

## File Map

Create:

- `validator/command_registry.py` - canonical command inventory and metadata.
- `validator/cli_commands/command_audit_cmd.py` - deterministic audit CLI for command/docs/contracts.
- `tests/test_command_registry.py` - registry and docs sync tests.
- `tests/test_command_audit_cli.py` - CLI behavior for clean and broken fixtures.
- `tests/test_command_finalization_contract.py` - every command must include the finalization gate through the anti-drift block.
- `tests/test_play_coverage_cli.py` - deterministic play-coverage behavior.
- `tests/test_status_cli.py` - deterministic status output.
- `tests/test_conventions_cli.py` - deterministic refresh-conventions behavior.
- `migrations/14/migrate.md` - downstream migration documentation.
- `tests/integration/test_migration_v14.py` - migration idempotency and command sync checks.

Modify:

- `validator/cli.py` - register `command-audit`; register any new deterministic CLI helpers.
- `validator/cli_commands/run_cmd.py` - add `finalize` subcommand that records and verifies in one step.
- `validator/cli_commands/__init__.py` - register new short-form helper commands if needed.
- `scripts/check-coherence.sh` - delegate command consistency to `livespec command-audit`.
- `scripts/play-coverage.sh` - either delegate to `livespec play-coverage` or align behavior with expectations.
- `system/anti-drift-block.md` - require finalization before success reporting.
- `system/expectations.md` - document mandatory finalization.
- `system/spec-system.md` - fix command count and stale "No hooks" language.
- `commands/*.md` - update only where command-specific finalization details are required beyond the shared anti-drift block.
- `commands/*.expectations.md` - strengthen weak rules and align with actual outputs/artifacts.
- `commands/hooks.md` - remove hardcoded stale command list or include all 20 from the registry.
- `commands/init.md` and `scripts/init.sh` - include `verify-output` in command lists.
- `.claude/checks/livespec-routing-sync.md` - point to `livespec command-audit`.
- `VERSION` - bump to `14` when migration 14 is added.

---

### Task 1: Create The Feature Spec Before Code

**Files:**
- Create: `.specs/features/048-command-validation-hardening/spec.md`
- Create: `.specs/features/048-command-validation-hardening/plan.md`
- Modify: `.specs/roadmap.md`
- Modify: `.specs/README.md`
- Modify: `.specs/changelog.md`

- [ ] **Step 1: Create feature directory**

Run:

```bash
mkdir -p .specs/features/048-command-validation-hardening
```

Expected: directory exists.

- [ ] **Step 2: Write spec with explicit acceptance criteria**

The spec must include these acceptance criteria:

```markdown
- **AC-001** - The command registry reports exactly the same command set as `commands/*.md` excluding `*.expectations.md`.
- **AC-002** - Every command has an expectations file with Section 13 and at least one `exit_code` verify rule.
- **AC-003** - Every command imports the anti-drift block and therefore inherits the finalization gate.
- **AC-004** - Routing docs, hooks docs, `system/spec-system.md`, and init bootstrap docs are synchronized with the registry.
- **AC-005** - `livespec command-audit` exits 0 on the current repo and exits non-zero on a fixture with a missing expectations file, stale route entry, or missing finalization gate.
- **AC-006** - `/spec.play-coverage`, `/spec.status`, and `/spec.refresh-conventions` have deterministic CLI-backed paths or explicit deterministic gates.
- **AC-007** - `scripts/check-coherence.sh` passes on the current repo and fails on a generated broken fixture.
- **AC-008** - Migration 14 updates downstream projects idempotently.
```

- [ ] **Step 3: Write plan.md mapping each AC to tasks below**

Include a testing matrix with:

```markdown
| Gate | Command |
|---|---|
| Registry audit | `python3 -m validator.cli command-audit --repo .` |
| Expectations corpus | `python3 -m pytest tests/test_builtin_expectations_corpus.py tests/test_command_registry.py` |
| Runtime verifier | `python3 -m pytest tests/test_verify_output.py tests/test_command_finalization_contract.py` |
| Coherence script | `bash scripts/check-coherence.sh` |
| Full non-external suite | `python3 -m pytest -m "not slow and not android and not macos"` |
```

- [ ] **Step 4: Validate spec artifacts**

Run:

```bash
python3 -m validator.cli validate .specs/features/048-command-validation-hardening/spec.md --format compact
```

Expected: exit 0.

### Task 2: Add A Canonical Command Registry

**Files:**
- Create: `validator/command_registry.py`
- Create: `tests/test_command_registry.py`

- [ ] **Step 1: Write failing tests**

Add tests that assert:

```python
from validator.command_registry import discover_commands, command_names

def test_registry_has_20_commands():
    assert len(command_names()) == 20
    assert "verify-output" in command_names()

def test_every_command_has_md_and_expectations():
    for command in discover_commands():
        assert command.command_file.exists()
        assert command.expectations_file.exists()

def test_routing_headings_match_registry():
    names = command_names()
    headings = set(parse_routing_headings(Path(".claude/rules/livespec-commands.md")))
    assert headings == names
```

Run:

```bash
python3 -m pytest tests/test_command_registry.py -q
```

Expected: fail because `validator.command_registry` does not exist.

- [ ] **Step 2: Implement registry**

Create a dataclass with fields:

```python
@dataclass(frozen=True)
class CommandInfo:
    name: str
    command_file: Path
    expectations_file: Path
    linked_locally: bool
    bootstrap_global: bool
```

Implementation rules:

- Source command names from `commands/*.md`, excluding `*.expectations.md`.
- `bootstrap_global` is true only for `init` and `migrate`.
- `linked_locally` is true for all non-bootstrap slash commands.
- Expose `command_names()`, `discover_commands()`, and `parse_routing_headings(path)`.

- [ ] **Step 3: Run tests**

```bash
python3 -m pytest tests/test_command_registry.py tests/test_integrations.py -q
```

Expected: pass.

### Task 3: Add `livespec command-audit`

**Files:**
- Create: `validator/cli_commands/command_audit_cmd.py`
- Modify: `validator/cli.py`
- Create: `tests/test_command_audit_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Required scenarios:

```python
def test_command_audit_clean_repo_exits_zero():
    result = runner.invoke(app, ["command-audit", "--repo", "."])
    assert result.exit_code == 0
    assert "LIVESPEC command-audit · OK" in result.output

def test_command_audit_missing_expectations_exits_one(tmp_path):
    project = copy_minimal_livespec_repo(tmp_path)
    (project / "commands/status.expectations.md").unlink()
    result = runner.invoke(app, ["command-audit", "--repo", str(project)])
    assert result.exit_code == 1
    assert "status.expectations.md" in result.output
```

- [ ] **Step 2: Implement checks**

The command must verify:

- registry command files exist
- expectations files exist and parse
- every expectations file has Section 13
- every expectations file has `must_not contains Traceback`
- every expectations file has at least one `exit_code` rule
- every command file imports `system/anti-drift-block.md`
- routing headings equal registry names
- `scripts/install.sh` declares only bootstrap commands `init`, `migrate`
- `scripts/link-local.sh` links every non-bootstrap command and excludes expectations sidecars
- `commands/hooks.md`, `system/spec-system.md`, `commands/init.md`, `scripts/init.sh` mention `verify-output`
- no stale phrase `19 available commands` remains

- [ ] **Step 3: Register in Typer**

In `validator/cli.py`, import and register:

```python
from .cli_commands.command_audit_cmd import register as register_command_audit
register_command_audit(app)
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_command_audit_cli.py tests/test_command_registry.py -q
```

Expected: pass.

### Task 4: Replace The Obsolete Coherence Script

**Files:**
- Modify: `scripts/check-coherence.sh`
- Create or extend: `tests/test_command_audit_cli.py`

- [ ] **Step 1: Add test for the old failure mode**

Create a test that runs:

```bash
bash scripts/check-coherence.sh
```

Expected after fix: exit 0 and no false `install.sh declares 0 commands` error.

- [ ] **Step 2: Replace command-count extraction**

Remove `extract_commands()` and `extract_agents()` from `scripts/check-coherence.sh`. Delegate command consistency to:

```bash
python3 -m validator.cli command-audit --repo "$ROOT"
```

Keep non-command checks only if they are still current.

- [ ] **Step 3: Run**

```bash
bash scripts/check-coherence.sh
python3 -m pytest tests/test_command_audit_cli.py -q
```

Expected: both pass.

### Task 5: Make Runtime Finalization Mandatory

**Files:**
- Modify: `validator/cli_commands/run_cmd.py`
- Modify: `system/anti-drift-block.md`
- Modify: `system/expectations.md`
- Create: `tests/test_command_finalization_contract.py`

- [ ] **Step 1: Add failing tests for finalization command**

Test API:

```bash
livespec run finalize --command status --exit-code 0 --stdout-file out.txt --stderr-file err.txt --feature 001-auth
```

Expected behavior:

- Writes `.specs/.runs/status-<ISO>.json`.
- Immediately evaluates the artifact against `status.expectations.md`.
- Exits 0 for success, 1 for drift, 2 for blocked.

- [ ] **Step 2: Implement `run finalize`**

Use existing functions:

- `record_from_streams()` from `validator.run_artifact`
- `load_expectations()` from `validator.expectations`
- `evaluate()` from `validator.verify_output`

Do not duplicate verifier logic.

- [ ] **Step 3: Update the anti-drift block**

Add a mandatory final phase:

```markdown
Before reporting a `/spec.<command>` invocation as successful, write a RunArtifact
for the command and run the finalization verifier. If finalization exits 1 or 2,
report DRIFT or BLOCKED instead of success.
```

- [ ] **Step 4: Add corpus test**

`tests/test_command_finalization_contract.py` must assert:

```python
for command_file in Path("commands").glob("*.md"):
    if command_file.name.endswith(".expectations.md"):
        continue
    assert "@import system/anti-drift-block.md" in command_file.read_text()
assert "run finalize" in Path("system/anti-drift-block.md").read_text()
```

### Task 6: Strengthen Every Expectations Contract

**Files:**
- Modify: `commands/*.expectations.md`
- Modify: `tests/test_builtin_expectations_corpus.py`

- [ ] **Step 1: Add stricter corpus tests**

Add tests:

```python
def test_all_builtins_have_exit_code_rule():
    for cmd in EXPECTED_COMMANDS:
        exp = parse_expectations(COMMANDS_DIR / f"{cmd}.expectations.md")
        assert any(r.kind == "exit_code" for r in exp.verify.must), cmd

def test_all_builtins_have_command_specific_signal():
    for cmd in EXPECTED_COMMANDS:
        exp = parse_expectations(COMMANDS_DIR / f"{cmd}.expectations.md")
        payloads = [str(r.payload) for r in exp.verify.must]
        assert any(cmd in p or "LIVESPEC" in p or "spec" in p for p in payloads), cmd
```

- [ ] **Step 2: Update weak contracts**

For every command, ensure the verify block has:

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "<command-specific stable marker>"
  must_not:
    - contains: "Traceback"
```

For visual/test commands, include conditional `when:` branches for flags such as `--visual`, `--json`, `--fix`, `--preview`, and `--auto`.

- [ ] **Step 3: Align Section 13 with reality**

Fix known bad contract:

- `/spec.play-coverage`: either implement the promised server/data artifacts or update expectations to match the actual CLI.

Run:

```bash
python3 -m pytest tests/test_builtin_expectations_corpus.py tests/test_expectations.py tests/test_demo_session_snapshot.py -q
```

Expected: pass.

### Task 7: Determinize `/spec.status`

**Files:**
- Create: `validator/cli_commands/status_cmd.py`
- Modify: `validator/cli.py`
- Modify: `commands/status.md`
- Modify: `commands/status.expectations.md`
- Create: `tests/test_status_cli.py`

- [ ] **Step 1: Add tests**

Test readable and JSON output:

```python
result = runner.invoke(app, ["status"], catch_exceptions=False)
assert result.exit_code == 0
assert "LIVESPEC status · OK" in result.output

result = runner.invoke(app, ["status", "--json"], catch_exceptions=False)
payload = json.loads(result.output.split("LIVESPEC")[0])
assert "features" in payload
```

- [ ] **Step 2: Implement using existing graph builder**

Use `validator.coherence.graph_builder.build_graph()` to compute:

- project name
- roadmap counts
- feature status counts
- missing plan/implementation gaps

- [ ] **Step 3: Update slash command**

`commands/status.md` must say the slash command invokes:

```bash
livespec status "$@"
```

and then finalizes with `livespec run finalize`.

### Task 8: Determinize `/spec.play-coverage`

**Files:**
- Create: `validator/cli_commands/play_coverage_cmd.py`
- Modify: `validator/cli.py`
- Modify: `scripts/play-coverage.sh`
- Modify: `commands/play-coverage.md`
- Modify: `commands/play-coverage.expectations.md`
- Create: `tests/test_play_coverage_cli.py`

- [ ] **Step 1: Add tests for non-GUI mode**

Required command:

```bash
livespec play-coverage --feature 001-auth --source-dir src --once --json --no-open
```

Expected:

- exit 0
- JSON includes `feature`, `source_dir`, `anchor_count`, `file_count`
- no browser is opened
- summary line `LIVESPEC play-coverage · OK`

- [ ] **Step 2: Implement CLI**

Use `rg` when available, fallback to Python file traversal. Do not shell-inject feature/source paths into Python strings.

- [ ] **Step 3: Keep Bash wrapper as compatibility shim**

`scripts/play-coverage.sh` should call:

```bash
python3 -m validator.cli play-coverage --feature "$FEATURE" --source-dir "$SOURCE_DIR"
```

- [ ] **Step 4: Align expectations**

Remove false claims about `playground/coverage/data.json` unless the new CLI actually creates it.

### Task 9: Determinize `/spec.refresh-conventions`

**Files:**
- Create: `validator/cli_commands/conventions_cmd.py`
- Modify: `validator/cli.py`
- Modify: `commands/refresh-conventions.md`
- Modify: `commands/refresh-conventions.expectations.md`
- Create: `tests/test_conventions_cli.py`

- [ ] **Step 1: Add tests**

Required behavior:

```bash
livespec conventions refresh --dry-run
livespec conventions refresh --force
```

Expected:

- reads `.specs/stacks/_default.md`
- writes or previews `.conventions/index.md`
- preserves existing custom blocks
- emits `LIVESPEC conventions · OK`

- [ ] **Step 2: Implement deterministic core**

Do not depend on external `/conventions.init` or `/conventions.refresh` for the core gate. External convention skills may remain optional, but the command must have a local deterministic fallback.

- [ ] **Step 3: Reuse existing test-config support**

Call existing `validator.drivers.test_config.update_conventions_testing_domain()` for the testing domain.

### Task 10: Fix Stale Command Documentation

**Files:**
- Modify: `system/spec-system.md`
- Modify: `commands/hooks.md`
- Modify: `commands/init.md`
- Modify: `scripts/init.sh`
- Modify: `.claude/rules/livespec-commands.md` only if command names change
- Create or extend: `tests/test_command_registry.py`

- [ ] **Step 1: Replace hardcoded counts**

Change stale text:

- `19 available commands` -> `20 available commands`
- command list must include `/spec.verify-output`
- `scripts/init.sh` bootstrap block must include the current command list or explicitly say it is a reduced legacy display.

- [ ] **Step 2: Fix hooks docs**

`commands/hooks.md` must include `verify-output`, or must state the valid command list is resolved dynamically by `validator.integrations.valid_command_names()`.

- [ ] **Step 3: Fix system hooks language**

Do not claim `hooks`, `play-coverage`, `status`, and `refresh-conventions` skip hooks if the anti-drift policy says every command resolves hooks. Either:

- all commands resolve hooks, including utilities, or
- the command registry marks explicit exceptions and `command-audit` verifies them.

Preferred: all commands resolve hooks.

### Task 11: Add Migration 14

**Files:**
- Create: `migrations/14/migrate.md`
- Modify: `VERSION`
- Modify: `scripts/migrate.sh`
- Create: `tests/integration/test_migration_v14.py`

- [ ] **Step 1: Write migration test**

Fixture starts with:

- `.claude/commands/` lacking `spec.verify-output.md`
- stale command docs
- missing `.specs/.runs/` gitignore entry

Migration must:

- relink commands through `scripts/link-local.sh`
- preserve project-local command overrides
- add `.specs/.runs/` and `.specs/.previews/` if missing
- be idempotent

- [ ] **Step 2: Add migration doc**

`migrations/14/migrate.md` must document:

```markdown
# Migration 14 - Command validation hardening

Actions:
- refresh local command symlinks
- ensure verify-output is linked
- ensure runtime artifact directories are gitignored
- run command-audit after migration
```

- [ ] **Step 3: Bump VERSION**

Set `VERSION` to `14`.

### Task 12: Final Verification Gate

**Files:**
- Modify: CI/docs only if needed

- [ ] **Step 1: Run deterministic audit suite**

```bash
python3 -m validator.cli command-audit --repo .
bash scripts/audit-antidrift-coverage.sh
bash scripts/check-coherence.sh
python3 -m pytest tests/test_command_registry.py tests/test_command_audit_cli.py tests/test_command_finalization_contract.py tests/test_builtin_expectations_corpus.py tests/test_verify_output.py tests/test_verify_output_cli.py tests/test_run_artifact.py tests/test_status_cli.py tests/test_play_coverage_cli.py tests/test_conventions_cli.py -q
```

Expected: all pass.

- [ ] **Step 2: Run broad suite excluding external device requirements**

```bash
python3 -m pytest -m "not slow and not android and not macos"
```

Expected: pass. If any test requires unavailable local services despite markers, mark or isolate it before claiming completion.

- [ ] **Step 3: Produce command scorecard**

Run:

```bash
python3 -m validator.cli command-audit --repo . --json > /tmp/livespec-command-audit.json
```

Expected: JSON has 20 commands and every command has:

```json
{
  "score": 5,
  "has_expectations": true,
  "has_exit_code_rule": true,
  "has_finalization_gate": true,
  "routing_synced": true,
  "anti_drift": true
}
```

## Acceptance Criteria For Completion

- `livespec command-audit --repo .` exits 0.
- `scripts/check-coherence.sh` exits 0.
- All 20 commands score 5/5 in the JSON scorecard.
- `/spec.play-coverage`, `/spec.status`, and `/spec.refresh-conventions` no longer rely on unverified manual/LLM-only behavior.
- Every command has a mandatory finalization path to `RunArtifact` plus `verify-output`.
- Stale command counts/lists are removed or generated from the registry.
- Migration 14 exists and is idempotent.

## Execution Choice

Plan complete and saved to `docs/superpowers/plans/2026-05-17-command-validation-hardening.md`.

1. Subagent-Driven - dispatch independent workers for registry/audit, finalization, deterministic utility CLIs, docs/migration, then review integration.
2. Inline Execution - execute the tasks in this session with checkpoints after each task group.
