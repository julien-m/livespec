<!-- @spec(FR-003) -->

# Conventions Enforcement

> Reference for the blocking conventions pipeline introduced by features 061-065.

## Architecture: Three Engines

| Engine | Scope | Source | Output | Blocks |
|---|---|---|---|---|
| Engine A: Deterministic subprocess | Repo code and config | `.specs/conventions-gates.yaml` command groups and builtins | conventions receipt + `debt.json` | Yes, when deterministic gates fail |
| Engine B: Visual receipt | Runtime/design evidence | visual-gate receipts and Penflow/design registry artifacts | verified visual evidence receipt | Yes, for visual commands and visual features |
| Engine C: Layer 4 LLM review | Semantic convention review | compiled conventions rulebook + waivers | semantic verdict and violations | Yes, when blocking semantic rules fail |

Engine A is the default path for code conventions. It runs declared lint,
format, and typecheck subprocesses plus built-in deterministic checks.
Engine B proves visual evidence separately because screenshots and design
contracts need receipt integrity. Engine C handles rules that cannot be
deterministically checked and requires a configured LLM provider when blocking
rules exist.

## Gates And Rulebook Schemas

### `conventions-gates.yaml`

The gates file lives at `.specs/conventions-gates.yaml` and owns deterministic
enforcement:

- `generated_from.constitution` and `constitution_sha256` bind gates to the project constitution.
- `commands.lint`, `commands.format`, and `commands.typecheck` declare subprocesses plus optional version and config requirements.
- `builtin.max_file_lines` and `builtin.max_function_lines` define target and blocking limits.
- `coverage` declares which language families are covered.
- `exclusions` protects generated, cached, or intentionally ignored paths.
- `scope: repo` means receipts are repo-wide, not feature-local.

### `conventions-rules.yaml`

The compiled semantic rulebook is stored as
`.specs/conventions-rulebook.yaml`. Older docs may call it
`conventions-rules.yaml`; the active file is the rulebook YAML.

- `sources` records every convention source and hash.
- `rules` contains enforceable semantic rules, including `blocking: true` where violations block.
- `unenforceable` explains source rules that cannot run in Engine C.
- `waivers` records temporary false-positive exemptions with expiry and optional path scope.

## Human Operations

| Operation | Command / Action | Notes |
|---|---|---|
| Constitution change | `livespec conventions gates init --force` | Rebuild gates so the recorded constitution hash matches `.specs/constitution.md`. |
| `ai-ressources` change | `livespec conventions compile --force` | Recompile the semantic rulebook after reviewing changed source conventions. |
| False-positive waiver | Edit `.specs/conventions-rulebook.yaml` waiver entry | Include rule id, reason, expiry, and path scope when possible. |
| Linter config missing | `livespec conventions scaffold --apply` | Writes supported linter templates without overwriting existing configs unless sync is requested. |
| Add a language | Extend gates commands and coverage | Add command adapter coverage before making the language blocking. |
| Deblock dirty project | `livespec conventions verify --report` then `/spec-fix --conventions` | Burn down worst-first; pre-existing debt is not an exemption for new pipeline completion. |

## Anti-Bypass Locks

| # | Lock | Enforcement |
|---|---|---|
| 1 | Repo-scope receipt | `livespec conventions verify` must PASS for implement/test/fix success. |
| 2 | Receipt artifacts | Run artifacts store conventions receipt paths for verification. |
| 3 | Verify-output rule | Expectations require `receipt_verdict` when conventions gates exist. |
| 4 | Goal contracts | `conventions_receipt_path` is required for implementation commands. |
| 5 | Supervisor diff guard | Protected convention files cannot change inside a worker pipeline. |
| 6 | Base hash guard | Supervisor compares base gates/rulebook hashes before accepting output. |
| 7 | Fresh supervisor run | Supervisor reruns conventions verify instead of trusting worker declarations. |
| 8 | R7 coherence | Coherence rules detect stale gates/rulebook sources and hash drift. |
| 9 | Waiver expiry | Semantic waivers are explicit, scoped, and temporary. |
| 10 | No pre-existing exemption | Existing debt still blocks new OK phase results until burned down. |

## CLI Reference

| Command | Purpose |
|---|---|
| `livespec conventions gates init --force` | Generate or refresh deterministic gates from constitution and stack. |
| `livespec conventions compile --force` | Compile the semantic rulebook from `.conventions/` sources. |
| `livespec conventions scaffold --apply` | Write supported linter config templates from gates limits. |
| `livespec conventions verify --report` | Run conventions gates and write debt/report artifacts. |
| `livespec conventions verify --json --feature <slug> [--run-id <id>]` | Run conventions gates and write a project-local receipt under `.specs/conventions/runs/`. Use `--feature repo` for repo-scope goal proof. |
| `livespec conventions supervisor-gate --base-ref <ref> --head-ref <ref>` | Run supervisor-only diff/hash/freshness locks. |
| `/spec-fix --conventions` | Burn down conventions debt worst-first and require no new violations. |

## Pipeline Rule

Before any `PHASE_RESULT: OK` for implement, test, or fix, the repo-scope
conventions receipt must be `PASS`. Commands that need repo-scope proof call
`livespec conventions verify --json --feature repo`; `verify --json` without
`--feature` remains a compatibility path and does not emit a receipt.
Pre-existing debt never justifies skipping the receipt or downgrading a failed
conventions gate.
