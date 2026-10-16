# Minimal Spec Scope

<!-- @spec FR-001: Native minimal-spec-scope rule — .specs/features/090-minimal-plan-scope/spec.md#fr-001 -->

A native LiveSpec rule (`minimal-spec-scope`) for every `plan.md` and every plan review. A plan builds what the spec asks for, by the simplest means the constitution allows, and nothing else.

## Rule

- Every mechanism a plan introduces traces to a functional requirement, an acceptance criterion or a constitution rule. A mechanism is any component, layer or behavior that needs its own tests, review or evidence: a cache, a retry or backoff layer, telemetry or metrics, a queue, a feature flag, a background job, a new configuration surface, a fallback path, an abstraction kept "for later".
- A mechanism without that trace is extra scope. Remove it from the plan, or keep it only as a technical necessity of the chosen solution (an atomic write, a lock that a stated concurrency requires) with a one-sentence justification that names the requirement it serves.
- "Best practice", "robustness", "future needs" and "observability" are not justifications on their own.
- A plan never adds proof the spec did not ask for. Each step names the evidence it produces. Its class is `local` by default (produced on this machine during implementation; write nothing). Only a step whose proof needs release signing, a device fleet or production adds the line `**Evidence class:** release`. Read [execution rules](testing/execution-rules.md#plan-evidence-classes) for the deferral of release evidence.

## Plan review

The plan reviewer applies this rule. It reports each untraced mechanism in `extra_scope` with its citation: `kind: business` when nothing justifies it (it blocks readiness), `kind: technical` with the justification when it is a necessity of the chosen solution (it carries over). Read [complete review and progression](review-protocol.md) for readiness.

## Necessary validation

<!-- @spec FR-006: Proportional proof scope — .specs/features/095-test-time-budgets/spec.md#fr-006 -->
- Every proposed test proves a named observable behavior, changed branch, concrete risk or regression. Reuse adequate existing tests; never generate tests just to increase their count, duplicate covered cases or expand an exhaustive matrix without distinct proof value.
- For expensive validation, name the FR/AC requiring the scale, minimum representative dataset and configuration count, individual and aggregate estimates, and the budget for preparation, generation, execution and cleanup. Separate functional correctness from capacity measurement.
- A reviewer counterexample alone does not create a blocking capacity benchmark. Require an actual scale requirement; otherwise keep it optional.
- Stop after relevant checks pass. Broaden or repeat only for a new change, failure or concrete unresolved concern. Read [bounded execution and recovery](testing/execution-rules.md#validation-budgets).
