<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-006) -->
<!-- @spec(FR-012) -->

# Penflow Contract Gate

Penflow is the primary UI behavior contract when a project has root `penflow/`.
In reports, screenshots remain visual regression gates; they never replace Penflow flow correctness.

## Workspace

Root layout:

```text
penflow/
├── flow-ui-contract/
├── ui.pen
├── semantic-ui-tree.json
├── expected-ui-tree.json
├── code-ir.json
├── actual-ui-tree.json
├── run-report.json
├── compare-report.json
├── compare-report.md
├── review-report.md
└── fix-report.md
```

Required for readiness inspection (not certification):

- `penflow/ui.pen`
- `penflow/semantic-ui-tree.json`
- `penflow/expected-ui-tree.json`
- `penflow/code-ir.json`

`penflow/ui.pen is the only allowed `.pen` file` in a LiveSpec project.
Any duplicate `.pen` under `.specs/design/`, `.specs/features/*/design/`,
or another path blocks the contract.

Required for runtime comparison:

- `penflow/actual-ui-tree.json` emitted by an external adapter

## Global LiveSpec Design Registry

Penflow-backed UI features must also populate the project-level design registry.
PNG screenshots and baselines are visual evidence only; `penflow/ui.pen` remains
the only Penflow/Pencil source file.

Required registry layout:

```text
.specs/design/
├── screens/
│   ├── index.md
│   └── <feature_slug>/
│       └── <screen>.png
├── baselines/
│   └── <feature_slug>/
│       └── <runtime-screen>.png
└── changelog.md
```

If mockup PNGs under `.specs/design/screens/<feature_slug>/` are missing for a
Penflow-backed UI feature, the visual gate is `BLOCKED`. Do not auto-approve
runtime screenshots without mockups.

## Mockup Factory Validation

Penflow-backed UI features must run Mockup Factory after the Penflow forward
chain and design registry sync, before code starts. Required proof:

```text
.mockup-validation/
├── audit-report.md
├── <feature_slug>/
│   ├── checklist.md
│   ├── manifest.json
│   └── drift-report.json
└── visual-evidence/
    ├── manifest.json   (status: PASS)
    ├── visual-report.md
    └── *.png
```

The canonical visual evidence manifest path is
`.mockup-validation/visual-evidence/manifest.json`.

`PASSED_WITH_WARNINGS`, `ESCALATED`, `BLOCKED`, and `BLOCKED_VISUAL_NOT_RUN`
block `/spec-feature` and `/spec-test` for web desktop UI features. The mockup
must pass modern desktop, no-placeholder, no-overflow, and visual evidence gates
before implementation or runtime baseline approval.

## Verdict

Every run exposes a top-level `verdict` in JSON, or this text line:

```text
Penflow Contract Verdict: READY | PASS | FAIL | BLOCKED | ABSENT
```

| Verdict | Meaning | Caller behavior |
|---|---|---|
| READY | Preparation inputs ready; certified false. | Continue preparation, never certify closure. |
| PASS | Current C51 validation matches the requested profile; certified true. | Requested stage certified; complementary visual gates still apply. |
| FAIL | Penflow rejected current certification. | Block closure. |
| BLOCKED | Invalid inspection, missing required inputs or incompatible response. | Repair before continuing. |
| ABSENT | No workspace and no certification request. | Non-UI inspection only. |

READY, ABSENT and certified PASS exit 0. Every invalid inspection or unsuccessful
certification exits 1. Missing workspace blocks an explicit certification request.
Legacy compare-report.json and actual-ui-tree.json remain diagnostics, never certificates.

## Command Sequence

```bash
livespec penflow-contract status --project . --json
livespec penflow-contract status --project . --required-profile design --json
livespec penflow-contract status --project . --required-profile implementation \
  --build-manifest <runner-build-manifest> --require-design-registry \
  --require-mockup-validation --feature <feature_slug> --json
```

The workflow inspects preparation before generation, certifies design after Mockup
Factory, and certifies implementation after its runner produces current runtime evidence.
`--require-actual` aliases implementation and cannot downgrade an explicit requirement.
`--require-mockup-validation` checks partial mockup evidence without requesting C51. LiveSpec inspects phase 0.5 before Specify, then certifies design after source approval and before application code. Reuse valid mockup evidence; a second full MockupFactory pass is unnecessary.
For required implementation, `runtime_comparison: BLOCKED` prevents closure.

LiveSpec delegates to the installed Penflow validate-report command with --schema,
--required-profile, --project and --json; it forwards --build-manifest for implementation.
Penflow owns current report schema, gate and binding validation. LiveSpec accepts only
exit 0 with known wrapper kind penflow-verification-validation, integer version 1,
matching profiles, PASS and an empty issues list. The wrapper also supplies
`scope.project_root/workspace` matching resolved caller paths,
`report_sha256` matching requested bytes, and `build_manifest` null for design or
the requested path/raw sha256 for implementation. Inputs must remain unchanged during
validation. The independent build manifest comes
from the build/capture runner; never infer the served build from HEAD or copy its identity
from the report. Imported reports are revalidated at their destination. Missing CLI or
legacy report never falls back to historical PASS. No new user checklist is introduced.

## Rules

- Do not treat Penflow flows under `.specs/features/` as the project registry; feature-local copies are audit evidence only.
- Do not create or require secondary `.pen` files. Sync only PNG/mockup registry artifacts to `.specs/design/screens/<feature_slug>/`, `.specs/design/baselines/<feature_slug>/`, `.specs/design/screens/index.md`, and `.specs/design/changelog.md`.
- Do not generate runtime adapters in LiveSpec core.
- Preserve `semantic_id`, `test_id`, `binding`, `entity`, `validations`, and `side_effects` in UI implementation.
- Run Penflow before visual baseline approval; screenshot gates remain complementary visual regression gates.

## Machine lifecycle closure

The final lifecycle commands call the same C51 consumer boundary; a prior status printout or stored PASS never replaces current revalidation.

| Transition | Visual requirement |
|---|---|
| `finalize apply --status Implemented` | Current implementation certificate and independent runner manifest |
| `finalize apply` with omitted status on an Implemented feature | Same current certification, including idempotent replay |
| `finalize verify` on an Implemented feature | Fresh revalidation |
| `pipeline update --phase test --status done` or `skipped` | Fresh revalidation before recording completion |
| Any update producing an entirely terminal pipeline, or terminal `pipeline next` | Fresh revalidation before terminal success |
| Preparation, coding progress, or explicit reopening into a nonfinal status | Noncertifying progress; no premature runtime requirement |

For visual closure the workflow forwards `--build-manifest <runner_build_manifest>` to these commands from the same successful runtime runner. Missing input blocks; nonvisual callers keep their existing commands. Registry receipt PASS during preparation or reopening describes registry consistency only. The feature cannot regain Implemented or terminal pipeline success until certification passes.

Classification uses current feature scope. Active visual artifacts contradicting `visual: false`, or unresolved visual signals, block closure and require correcting upstream authority. Historical run/check archives do not prevent an approved conversion to nonvisual work. The partial visual renderer gate retains its own inspection behavior.

## Reviewed requirement authority

C51 certification requires `--feature <feature_slug>` from the active workflow. The governed selection accumulates previously approved features plus this caller, in sorted order; Draft backlog is never scanned. Required `retired_features` records per-feature retirement. Actual FR/AC definitions of the complete active difference are extracted from reviewed Markdown AST sections; references and examples cannot silently change the denominator. Canonical `penflow/flow-ui-contract/contract.json` supplies requirements references and outcome mappings. Categories and expected predicates are approved with those mappings; categories are never guessed from prose.

The C20 producer first uses `penflow authority prepare <contract> --project . --json` automatically and persists its prepared copy. Penflow preserves explicit test identifiers and fills missing ones deterministically before approval. The snapshot command delegates the real read-only `validate-flow-contract --require-test-ids` guard; absent CLI, invalid C20 or missing selectors blocks publication. Approved inputs are never repaired by validation.

Before its real plan review, the workflow runs:

```bash
livespec penflow-contract review-snapshot --feature <feature_slug> --json
```

The standard workflow writes closed `penflow_verification_policy` YAML metadata in each actual producing plan. The existing review-snapshot command automatically archives all active plans and generates the union of their required procedures; missing metadata in one of these plans blocks. A later plan cannot disable another active plan's procedure. The selected mode (`livespec` or `brainstorm_handoff`) follows authenticated ancestry. Each mode declares version 1 and generated_docs/native_geometry/homologous_references/native_export as required or not_applicable. Duplicate keys, unknown modes and missing decisions block. Inherited required procedures remain required, and validation independently recomputes the union. C20 must agree; the generator never copies candidate decisions from C20. Governed retirement is the existing path to reduce the active union.

For an actual dedicated workflow covering the whole reviewed scope instead of plan-local declarations, its caller uses `livespec penflow-contract policy-source --workflow <actual-producing-workflow-path> --project . --json` automatically before review. This archives the real workflow and its explicit metadata. It is not a fallback for partially declared active plans or missing artifacts, and adds no user-maintained document to standard planning.

For Brainstorm origins, the existing bootstrap additionally takes `--source-project <brainstorm-project>` from its caller. It delegates source design validation to `penflow authority collect`, archives original files and a relative local import package, and preserves an existing root workspace. The next snapshot binds that immutable package through its policy source. Penflow projects the accepted product denominator through `authority project`; LiveSpec combines it with selected FR/AC and explicit current mappings. The original absolute source paths stay historical metadata, not live dependencies. Old copies without authenticated origin remain inspectable but cannot certify inheritance. Import/review retries preserve previously published immutable bytes.

The command archives every governed specification and plan (`inputs.sources` and `inputs.plans`), plus the complete active contract, and returns their immutable snapshot identity. Semantically unchanged source records reuse authenticated historical raw bytes across generated lifecycle updates. The reviewer consumes those bytes. Its actual structured JSON output contains `invocation_id`, `producer_id`, `input_sha256`, `verdict`, `blocking_count` and `findings`; `input_sha256` is the returned snapshot hash. The workflow automatically invokes `livespec penflow-contract review-result --snapshot <snapshot-path> --output <actual-reviewer-output-path> --json`. This internal assembler validates complete actual reviewer fields and current snapshot identities, archives the original bytes and returns the bound result path. It never fills missing verdicts, findings or identities. Its certified flag is false; packaging a blocking review cannot approve it. Findings may discuss IDs removed from the authenticated prior baseline without reactivating their obligations. A manually asserted PASS or a finalization receipt is insufficient.

The existing transition consumes the result:

```bash
livespec pipeline update --feature <feature_slug> --phase plan-review \
  --status done --review-result <review_result_path>
```

Under the existing project lock, it revalidates input identities and the actual review output, retains immutable approval history, publishes `.specs/penflow-requirements.json`, then records Done. Interruption before phase publication stays nonfinal; retrying the same result safely resumes. Missing selection, changed sources, weaker mappings or predicates, deleted baselines and broken history block certification. Source revisions and approved reductions use the same review path with explicit prior/new identities.

Lifecycle status, updated metadata and exact generated finalization markers do not change approved semantic identity. Raw reviewed bytes remain archived and authenticated. Business status, code, visual scope, requirements and predicates remain bound. Certification checks this source authority before and after the Penflow subprocess and rejects a baseline changed during validation.

Implemented finalization acquires the project write lock, validates current C51 certification, then synchronizes the existing parsed roadmap item and other registries. An idempotent return with no registry writes still validates current certification immediately before returning. Replaying a prior closure can repair that checkbox without another changelog entry. Nonfinal updates leave roadmap checkboxes unchanged; no neighboring feature is marked by this operation.

For an approved conversion to nonvisual work, the same review adds that feature to `retired_features`, preserving other active features and immutable prior history. The global disposition becomes `retired` only when every governed feature is retired; its active projection is then completely empty. Reactivation uses the same reviewed revision path. A caller checks its own membership/disposition; certification also requires Plan Review Done for every active feature. The reviewer may inspect artifacts awaiting cleanup; nonvisual closure requires their actual removal and the current approved nonvisual source. `active` baselines certify UI; `retired` baselines cannot satisfy design or implementation C51. Nonvisual work without Penflow history keeps its existing process.
