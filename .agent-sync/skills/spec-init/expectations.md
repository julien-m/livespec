---
command: spec-init
contract_version: "1.0"
last_reviewed: 2026-10-09
---

<!-- @spec(FR-001) -->

# Expectations — /spec-init

## 1. Purpose

Initialize LiveSpec interactively or from observed code with safe autonomous recovery and complete current goal proof.

## 2. Preconditions

- `Project directory exists (any structure).`
- No existing `.specs/` directory, or explicit `--from-code --auto --force` for backed-up recovery. Migration remains `/spec-migrate`.
- Normalize noninteractive from-code intent and aliases before rendering the new goal; preserve the selected `--dir` target and explicit force/preview flags. Reject unsupported autonomous `--deep`, `--stack` and incompatible combinations before mutation.
- Observe independent supported manifests; malformed/conflicting facts or escaping writable paths block initialization.

## 3. Observable Signals

**stdout must_contain:**
- "LiveSpec initialized"
- "`.specs/`"
- "Penflow contract:"
- "Autonomous from-code: enabled" when `/spec-init --from-code` is made non-interactive by `--auto`, command-stream execution, or an instruction such as "Proceed autonomously"

**stdout must_not_contain:**
- "Traceback"
- "waiting for human validation" in autonomous from-code mode

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/`
- `.specs/spec-system.md`
- `.specs/project.md`
- `.specs/constitution.md`
- `.specs/roadmap.md`
- `.specs/.livespec-path`
- `.agent-sync.local/skills/spec-feature`
- `.agent-sync.local/skills/source-command-cli`
- `.agent-sync.local/agents/livespec-*` — mutable project-local copies (`agent.yaml` + `prompt.md`) for every source agent
- `.claude/skills/spec-feature`
- `.agents/skills/spec-feature`
- `.claude/agents/livespec-*.md`
- `.codex/agents/livespec-verifier.toml`

**update:**
- `.gitignore`
- `AGENTS.md` / `CLAUDE.md` LiveSpec markers, preserving user text

**autonomous recovery:**
- Unique project-local backup of prior specs, conventions, `.gitignore` and integration documents before overwrites
- Custom features/hooks/runs/history and all source/shared-target bytes remain unchanged
- Mutable local agents are copies before `cc-hub agent build`; valid conventions survive
- All source `spec-*` skills and `source-command-cli` resolve under `.agent-sync.local/skills/`, `.claude/skills/` and `.agents/skills/`; source `.agent-sync/` is not a required target directory. Generated agent outputs stay within the project.
- `--dry-run` previews with no project writes and no initialization-success claim; current `--verify-only` backend inspection is read-only

**optional:**
- `.specs/stacks/_default.md`
- `penflow/` when `handoff/penflow/` or legacy `penflow/` exists

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/`
- `.gitignore`

**forbidden changes:**
- `any source files`

**commit expectations:**
- none unless explicitly authorized by the user

## 6. Produced Artifacts

- path: `.specs/project.md`
  must_contain_sections:
  - "Vision"
  - "Users"
  - "Constraints"
- stdout marker: `Penflow Contract Verdict: ABSENT | READY | FAIL | BLOCKED`
  - `ABSENT`: unrequired non-UI inspection has no workspace.
  - `READY`: required planning artifacts and ID mappings are available; `certified: false`.
  - `FAIL` / `BLOCKED`: invalid or missing required preparation input; no certification is implied.

### C51 stage evidence

- This command prepares inputs; no runtime report/build manifest or final certificate is required before its producing/test stage.

## 7. Exit Codes

- A provided Brainstorm source is authenticated with `bootstrap --source-project <brainstorm-project>` even when root `penflow/` exists; the workspace is preserved. Failed source import stays noncertifying and cannot silently publish ancestry.
- Successful ancestry is local, immutable and hash-bound; moving the original source does not remove its obligations. An old copy without provenance remains inspectable only.

| Code | Meaning | Operator action |
|------|---------|-----------------|
| 0    | success | nothing |
| 1    | drift   | inspect report, fix divergence |
| 2    | blocked | restore precondition, retry |

## 8. Outcome Matrix

- **success:** every `must` rule passes, exit_code == 0
- **drift:** at least one `must` rule fails, command exited 0
- **blocked:** precondition missing or artifact missing
- **error:** command itself crashed (exit_code != 0)

## 9. Runtime Profile

- Typical range: 60–600 seconds
- Factors: Brainstorm interactivity, number of clarifying turns, design tool detection
- Autonomous external bootstrap work uses one finite deadline (default 300 seconds, explicit timeout supported), including installer, sync, version probes and hook subprocesses. Exhaustion returns `BLOCKED at step from-code-autonomous-timeout`; no budget resets between calls.
- Backend exit zero and `bootstrap-recap.md` completed status are generated-artifact evidence only. Current profile verification after hooks, integration proof, authentic goal evidence and archive remain required for command completion. Tooling READY never certifies application runtime.

## 10. Post-run Checks

- [ ] `.specs/` directory present at repo root
- [ ] spec-system.md is the canonical version
- [ ] `/spec-feature` project command assets are present; missing assets are `BLOCKED`, not drift
- [ ] Every source skill resolves in the local and provider namespaces; every source agent has a local copy and generated Claude/Codex output. Check canonical read-only links explicitly; confined filesystem rules check local namespace roots and local agent files.
- [ ] Autonomous profiles retain observed native/frontend families and manager evidence; unobserved roles/scale/geography/budget/deployment are Unknown
- [ ] Constitution, observed stack ADR and testing strategy are project-specific; required bounded version probes have actual outputs/exits
- [ ] Current `--verify-only` succeeds after hooks; source or generated content drift prevents completion
- [ ] The immutable goal includes the applicable branch, every required task is proved and the actual run archive is verified

## 11. Troubleshooting

- **Symptom:** `.specs/` already exists
  **Cause:** previous init
  **Fix:** use `/spec-migrate` for version migration, or explicit `--from-code --auto --force` for preserved autonomous regeneration
- **Symptom:** `Unknown command: /spec-feature` after init
  **Cause:** Step 3.12 agent asset sync did not complete
  **Fix:** rerun `/spec-init` after resolving `BLOCKED at step 3.12`

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "LiveSpec initialized"
    - contains: "Penflow contract"
    - exists: ".specs/spec-system.md"
    - exists: ".specs/project.md"
    - exists: ".specs/constitution.md"
    - exists: ".specs/stacks/_default.md"
    - exists: ".specs/stacks/decisions"
    - exists: ".specs/testing/strategy.md"
    - exists: ".specs/preflight.md"
    - exists: ".specs/preflight-report.md"
    - exists: ".specs/.livespec-path"
    - exists: ".agent-sync.local/skills"
    - exists: ".claude/skills"
    - exists: ".agents/skills"
    - exists: ".agent-sync.local/agents/livespec-documenter/agent.yaml"
    - exists: ".agent-sync.local/agents/livespec-documenter/prompt.md"
    - exists: ".agent-sync.local/agents/livespec-implementer/agent.yaml"
    - exists: ".agent-sync.local/agents/livespec-implementer/prompt.md"
    - exists: ".agent-sync.local/agents/livespec-supervisor/agent.yaml"
    - exists: ".agent-sync.local/agents/livespec-supervisor/prompt.md"
    - exists: ".agent-sync.local/agents/livespec-verifier/agent.yaml"
    - exists: ".agent-sync.local/agents/livespec-verifier/prompt.md"
    - exists: ".claude/agents/livespec-documenter.md"
    - exists: ".claude/agents/livespec-implementer.md"
    - exists: ".claude/agents/livespec-supervisor.md"
    - exists: ".claude/agents/livespec-verifier.md"
    - exists: ".codex/agents/livespec-documenter.toml"
    - exists: ".codex/agents/livespec-implementer.toml"
    - exists: ".codex/agents/livespec-supervisor.toml"
    - exists: ".codex/agents/livespec-verifier.toml"
  may:
    - contains: "stack"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--dry-run"
      replace_base: true
      must:
        - exit_code: 0
        - contains: "no changes applied"
      must_not:
        - contains: "LiveSpec initialized"
        - contains: "Traceback"
    - flag: "-d"
      replace_base: true
      must:
        - exit_code: 0
        - contains: "no changes applied"
      must_not:
        - contains: "LiveSpec initialized"
        - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-init
> Phase 1 — Project discovery: detecting language, framework, tests
> Phase 2 — Stack proposal: <stack> (confidence: high)
> Phase 3 — Brainstorm: 4 user-story candidates, 1 ADR draft
> Wrote .specs/project.md, stacks/_default.md, roadmap.md, preflight.md
exit 0
```

### Files Produced

```
.specs/
├── README.md                    # spec registry index
├── spec-system.md               # universal rules (this project)
├── constitution.md              # architecture principles
├── project.md                   # vision, users, constraints
├── roadmap.md                   # MVP / Post-MVP / Future
├── stacks/_default.md           # chosen stack + rationale
├── stacks/decisions/ADR-001-*.md
├── testing/strategy.md
├── preflight.md                 # preflight manifest
└── preflight-report.md          # first run report
```

### Aligned / Drift / Missing

- **Aligned:** Current observed values match artifacts, observed ADR and project-specific documents exist, required probes actually pass, after-init hooks/integrations are verified, and the goal proof/archive is complete. Tooling READY certifies availability only. Exit 0.
- **Drift:** project.md still contains `[TBD]` placeholders, stack rationale empty, or no ADR generated despite stack choice. Exit 1 with a gap report.
- **Missing:** Tooling preconditions failed (no git, no Python). Exit 2 with the missing tool name.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Fresh repo (small) | 60–180s | brainstorm rounds |
| Autonomous from-code — supported hybrid/web/Python/Cargo | default <= 300s external budget | bounded installer/sync/probes/hooks + current verification; full goal proof required |
| Existing codebase reverse-engineer | 180–600s | code scan size |
| Large monorepo | 300–900s | feature inference |

### Edge Cases

- Repo already contains a stale `.specs/` from a previous version: `/spec-migrate` is suggested before re-running init.
- Explicit autonomous force recovery preserves prior generated files in a unique local backup and overlays only bootstrap-owned artifacts; no interview or product invention.
- Missing/failed/timed-out tools and manifest/content drift return a contextual nonzero exit without completed initialization. Preview writes nothing and does not claim success.
- No git remote configured: init proceeds, leaves a warning in `preflight-report.md`.
- LLM rate-limited mid-brainstorm: init resumes from the last saved checkpoint on next invocation.

### Post-run Actions

- **On success:** review `project.md`, then run `/spec-propose` to pick the first feature.
- **On drift:** open `.specs/checks/<today>.md`, fix the flagged blanks, re-run init.
- **On blocked:** install the missing tool from `preflight-report.md`, re-run init.
