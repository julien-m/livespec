# Initialization technical reference

Read [review led delivery](../../../system/review-led-delivery.md) first. Read only the sections needed for the authorized setup; these procedures do not create certification prerequisites. The original extended procedure remains in [the historical diagnostic](certification.md).

## Discovery and stack decisions

- Resolve supplied Brainstorm context from `handoff/livespec/project-profile.md` and `handoff/livespec/*.md`, then legacy `.brainstorm/project-profile.md`; inspect sibling Markdown as context. Preserve existing answers and ask about real ambiguity rather than silently selecting an unrelated project.
- For an interview, establish vision, users/roles and actions, core scope, constraints (scale, regions, budget, compliance), integrations and existing code. Confirm meaningful product/stack choices before writing them as decisions.
- For autonomous `--from-code`, use supported manifests and real code only. Retain Unknown business fields, conflicting/malformed observations and unavailable tools; do not infer a backlog or a working deployment.
- Read the applicable stack decisions and testing conventions; choose required test types from observed components. Keep ADRs for substantive choices, with alternatives and rationale. Developer tooling and design tools remain optional unless the user made them requirements.
- Preserve existing design, screen indexes, themes and source files. Supplied Penflow/design artifacts are context, not automatic behavioral certification. Authenticated `penflow-contract bootstrap` is a separate explicitly requested operation: preserve its actual refusal and ancestry result without making that certificate an init prerequisite. Never overwrite an existing workspace or invent authority.

## Design imports and optional direction

- Inspect an existing design-tool choice as context; configuring a global tool/provider is a separate explicit choice, never an automatic bootstrap action. Preserve an explicit `tool: none`.
- For supplied design exports, prefer `handoff/livespec/mockups/` and sibling `ui.fig`/`ui.excalidraw`/`ui.html`, then legacy `.brainstorm` equivalents. Preserve original files, imported screen metadata/index and optional theme CSS/metadata; do not overwrite an existing import without the selected force authority and backup.
- Keep Penflow `.pen` sources at root `penflow/ui.pen`, distinct from screen exports. An absent source stays `ABSENT`, not a fabricated contract or imported ancestry.
- Design direction extraction carries only supplied text: optional `default-direction` and an imported `## Design direction` in `.specs/design/theme.md` are informative creative context, never validation criteria. Omit absent direction rather than adding placeholders.
- Prefer `handoff/livespec/theme.css`, then legacy `.brainstorm/theme.css`; import supplied CSS into `.specs/design/theme.css` and document its source and informative direction in `.specs/design/theme.md`. Preserve existing theme files unless an authorized overwrite has its backup; absent themes stay absent. Downstream commands use the imported project files, not a continuing Brainstorm dependency.

### Penflow workspace import

- Inspect the Brainstorm `handoff/penflow/` or legacy `penflow/` directory, in that order: `<brainstorm-project>/handoff/penflow`, then `<brainstorm-project>/penflow`. Preserve an existing root `penflow/`; a copy alone proves no ancestry.
- When the user's request or selected design setup authorizes the import, run `livespec penflow-contract bootstrap --project . --source <brainstorm-project>/handoff/penflow --source-project <brainstorm-project>` from the target project; for the legacy source substitute `--source <brainstorm-project>/penflow`. No additional literal confirmation is required for that already authorized operation. The existing CLI owns source validation, archive/identity checks and atomic publication; preserve its refusal without overwriting the workspace or inventing ancestry. This operation is not a required certificate for initialization or feature work.
- If neither source exists, continue from scratch: create no Brainstorm dependency or fabricated contract. Run `livespec penflow-contract status --project . --json` only within the authorized design scope, retain its real `state: absent` when observed and continue; an unexecuted status is `NOT_RUN`, not an observed absence. The first UI feature may establish root `penflow/` artifacts. After an authorized import, inspect actual status; screens remain visual exports, not the behavioral contract.

## Phase C — Installation (Automatic)

- Use [the core installer](../../../scripts/init.sh) and [the project templates](../../../system/templates/) for the selected setup; preserve observed project-specific content. The installer accepts a positional target, `--non-interactive`, `--force` and `--dry-run`; do not invent a CLI flag.
- Generate `.specs/spec-system.md`, project/constitution, stack with `updated` frontmatter, ADRs, testing strategy, roadmap, README registry, changelog and hooks directory. Preserve roadmap/readme section markers, existing feature status and custom content. Theme files are optional; initialize the screen index from its template when needed.
- Integrate LiveSpec into `CLAUDE.md`/`AGENTS.md` using managed boundaries; preserve unrelated text. Keep local execution reports and `.specs/.livespec-path` ignored through exact entries, without deleting existing ignore rules.
- Preserve histories, hooks, runs, sources and accepted decisions. Before authorized overwrite, retain a unique local backup. Autonomous force recovery uses the backend's backed-up overlay; a different existing format is migrated rather than relabeled.

### Step 3.12 — Sync Agent Assets

1. Resolve the executing skill to its physical `.agent-sync/skills/spec-init/SKILL.md` and derive the LiveSpec root. If opaque, inspect the recorded project path, then the nearest source layout containing that skill and the sync script. Verify VERSION and required scripts before dependent writes.
2. Read the current project integration instructions; run `bash <source>/scripts/sync-agent-assets.sh <project> <source> --scope project --targets all` for the authorized installation. This affects project outputs only, never global skills.
3. Run `bash <source>/scripts/install-hooks.sh <project> <source>` only for the project integration requested; preserve custom hooks. Report the current installer's actual outcome, not an assumed legacy hook certificate.
4. Perform post-sync verification against the actual source inventory: every source `spec-*` skill and `source-command-cli` must resolve through target `.agent-sync.local/skills/`, `.claude/skills/` and `.agents/skills/` to its canonical `SKILL.md`. Verify `.specs/.livespec-path`, including `.agent-sync.local/skills/spec-feature/SKILL.md`, `.claude/skills/spec-feature/SKILL.md` and `.agents/skills/spec-feature/SKILL.md`. Verify each source `livespec-*` agent's local `agent.yaml`/`prompt.md` and generated `.claude/agents/<name>.md`/`.codex/agents/<name>.toml`, including `.codex/agents/livespec-verifier.toml`. Mutable local agents/provider outputs must stay project-local; reject escaping writes. The source `.agent-sync/` namespace is not a required target directory. Missing commands are a real incomplete-installation finding (`Unknown command: /spec-feature`); retain exact missing paths/errors, continue independent work/review and never announce those assets installed.
5. On a fresh project, record the source version. Copy the shipped recovery-policy template only when available and no policy exists. Never overwrite an existing policy or silently change an existing project's format/stops.
6. When executing an installed snapshot, use its explicit `<home>/bin/livespec`, `LIVESPEC_HOME=<home>` and `LIVESPEC_RUNTIME=<id>` consistently; a lock mismatch remains a refusal. Pin a fresh project with that launcher's `runtime pin --runtime <id>`; the autonomous backend pins itself. A mutable checkout is not presented as an installed snapshot.

## Non-Interactive Autonomous From-Code Mode

- Normalize aliases and autonomous intent to `--from-code --auto`; keep the selected target, explicit force/preview and timeout. Reject unsupported autonomous `--deep`, `--stack` and incompatible options before mutation.
- Read [the bounded backend entry point](../../../scripts/init-from-code-autonomous.sh). It selects the checkout interpreter or the installed launcher's interpreter and invokes `validator.init_from_code`; it neither launches a model nor executes Markdown hooks.
- Resolve `TARGET_DIR`, `LIVESPEC_ROOT` and the positive remaining timeout before calling the backend; preserve spaces with an argv array. Use the same finite deadline for requested external probes/setup, never a reset timeout per retry.

```bash
INIT_ARGS=("$TARGET_DIR" --timeout-seconds "$REMAINING_SECONDS")
if [[ "$INIT_FORCE" == "true" ]]; then INIT_ARGS+=(--force); fi
if [[ "$INIT_DRY_RUN" == "true" ]]; then INIT_ARGS+=(--dry-run); fi
bash "$LIVESPEC_ROOT/scripts/init-from-code-autonomous.sh" "${INIT_ARGS[@]}"
```

- The default backend timeout is 300 seconds unless explicitly overridden. Its actual probes, detected families, technical/product names, package manager, constitution, ADRs and Unknown business fields are observations; tooling availability is not application runtime proof.
- Nonzero exit/timeout is retained with stdout/stderr and affected files. Diagnose a real defect and continue independent work/review; do not substitute invented generation or claim missing essentials initialized. The backend marks an incomplete recap on failure.
- `--force` retains a unique backup before overlay, including generated specs/conventions, integration text and relevant hooks. Preserve original pre-images and source/shared-agent bytes. Do not follow escaping writable links or bypass an incompatible existing format.
- `--dry-run` performs the documented read-only scan/preview: no installer, sync, hooks, backups, goals, target mutation or success claim. A malformed source or unavailable prerequisite remains reported, not PASS.
- When useful, run `bash "$LIVESPEC_ROOT/scripts/init-from-code-autonomous.sh" "$TARGET_DIR" --verify-only --timeout-seconds "$REMAINING_SECONDS"` to check current content/profile identity. An old completed recap is insufficient; the current result is a review input, not a delivery certificate.
- Older backend recap text may mention proving or archiving a command goal; that historical message does not add a prerequisite to this review-led path.
- Inspect applicable after-init hooks; execute only authorized technical setup consistent with the shared policy and deadline. No inherited goal, semantic receipt, plan review or certification restart is applied. Preserve real outcomes and use affected checks after changes.
- For interactive from-code discovery, read [the scan/recap reference](../../../system/from-code.md) for technical details only. Its older certification instructions do not govern this ordinary path. No Git commit/branch/tag/push occurs without existing authorization.

## Preflight and conventions

- Generate the relevant preflight manifest from the observed stack and [its template](../../../system/templates/preflight-manifest-template.md). Keep `.specs/preflight-report.md` local and ignored; commit only authorized project documents.
- Inspect token references without exposing secrets. Run only authorized tool checks; do not start OAuth, providers, hosts or services automatically. Group actual missing authority/functional choices for the user; an unrelated unavailable tool is a finding, not a pipeline gate.
- Preserve valid convention routing whose referenced sources actually resolve. Back up invalid generated routing before a requested repair; never infer execution from the backend exit alone or silently overwrite user routing.
- Design/visual helper scaffolding is relevant only to an actual selected platform/tool. Preserve unavailable observations and do not invent UI execution or authenticated design ancestry.

## Step D.7 — Mission supervisor and prerequisites

- Continuity is not a certification gate, but an explicit user request or existing project configuration remains a functional need. Determine the project/root, selected runtime, existing process association, requested mode and actual host authority before dependent startup.
- When the authorized host supports a review-led continuity entry point, initialize or attach the process bound to this project through that current supported interface. Reuse an existing association; do not start duplicate missions, introduce a nested goal/certificate or imply authority for a global installer. Preserve project/runtime identity and report the actual process state.
- If continuity is not requested/configured, no host or socket observation is needed. If required continuity lacks a supported interface/authority or a previous explicit refusal applies, keep the unmet need visible and report the unexecuted action `NOT_RUN` with its reason. Continue independent feature work; do not erase the continuity requirement or invent startup success.
- Inspect only continuity commands actually exposed by the selected runtime. If no supported review-led interface exists, report the requested operation `NOT_RUN`; do not invent commands or import a supervisor dependency. Registration, when supported and authorized, is a write and does not itself start a process. No continuity command is a bootstrap prerequisite, and no legacy goal-bearing sequence is a fallback.
- Preserve exact state, budget, executor/model/effort, host qualification, durability and unmet prerequisites. Never turn `configured`, `stopped`, `absent` or non-durable into `ready`/durable. A failed or unexecuted command is not a successful observation.
- Existing socket, host, application or provider refusals remain binding; no permission/profile change or different surface is authorized by init.

## Report

Report created/preserved files, actual source/runtime/pin, backup path, integrations and useful checks with their real results and limits. An incomplete installation is not complete; a backend recap is not command certification. Send results to the parent owning final review, or follow the shared independent final review policy. Keep nonexecuted observations `NOT_RUN` and preserve historical evidence.
