---
command: spec-init
contract_version: "1.0"
last_reviewed: 2026-05-26
---

# Expectations — /spec-init

## 1. Purpose

Initialize LiveSpec in a project through a 3-phase conversational brainstorm.

## 2. Preconditions

- `Project directory exists (any structure).`
- `No existing `.specs/` directory (else use /spec-migrate).`

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
- `.claude/skills/spec-feature`
- `.agents/skills/spec-feature`
- `.codex/agents/livespec-verifier.toml`

**update:**
- `.gitignore`

**optional:**
- `.specs/stacks/_default.md`
- `penflow/` when `.brainstorm/penflow/` exists

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
- stdout marker: `Penflow Contract Verdict: ABSENT | BLOCKED | PASS`
  - `ABSENT`: no root `penflow/` workspace on a from-scratch/non-UI init
  - `BLOCKED`: copied or existing root `penflow/` misses required artifacts
  - `PASS`: root `penflow/` has required planning artifacts

## 7. Exit Codes

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
- Autonomous from-code for a single-package Vite React app must_not hang; it must complete within 300 seconds or return `BLOCKED at step from-code-autonomous-timeout`.

## 10. Post-run Checks

- [ ] `.specs/` directory present at repo root
- [ ] spec-system.md is the canonical version
- [ ] `/spec-feature` project command assets are present; missing assets are `BLOCKED`, not drift

## 11. Troubleshooting

- **Symptom:** `.specs/` already exists
  **Cause:** previous init
  **Fix:** run /spec-migrate instead
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
    - exists: ".specs/.livespec-path"
    - exists: ".claude/skills/spec-feature/SKILL.md"
  may:
    - contains: "stack"
  must_not:
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

- **Aligned:** `.specs/` exists, project.md has real values, ADR-001 + stack rationale present, preflight-report.md verdict READY. Exit 0.
- **Drift:** project.md still contains `[TBD]` placeholders, stack rationale empty, or no ADR generated despite stack choice. Exit 1 with a gap report.
- **Missing:** Tooling preconditions failed (no git, no Python). Exit 2 with the missing tool name.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Fresh repo (small) | 60–180s | brainstorm rounds |
| Autonomous from-code — single-package Vite React | <= 300s | bounded scan + Phase C/D/E |
| Existing codebase reverse-engineer | 180–600s | code scan size |
| Large monorepo | 300–900s | feature inference |

### Edge Cases

- Repo already contains a stale `.specs/` from a previous version: `/spec-migrate` is suggested before re-running init.
- No git remote configured: init proceeds, leaves a warning in `preflight-report.md`.
- LLM rate-limited mid-brainstorm: init resumes from the last saved checkpoint on next invocation.

### Post-run Actions

- **On success:** review `project.md`, then run `/spec-propose` to pick the first feature.
- **On drift:** open `.specs/checks/<today>.md`, fix the flagged blanks, re-run init.
- **On blocked:** install the missing tool from `preflight-report.md`, re-run init.
