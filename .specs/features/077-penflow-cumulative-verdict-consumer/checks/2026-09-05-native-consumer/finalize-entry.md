Feature: Integrate current Penflow cumulative verification into LiveSpec closure

- **Type:** Feature
- **Spec modified:** Yes, consumer stages and governed upstream authority.
- **Code modified:** Penflow transport, approval/import adapters, finalizer and pipeline gates, shared workflow callers and regression tests.
- **AC impacted:** AC-001 through AC-009.
- **Evidence:** Actual A+B runtime certification and closure; actual Brainstorm design handoff and governed union; negative cases restore exact source bytes. Final caller checks: 28 PASS; finalizer checks: 69 PASS.
- **Limit:** Consumer pilot operations are proved individually; no unexecuted native pipeline phase is claimed Done. Historical producer Feature archive remains DRIFT and is not rewritten by this finalization.
- **Author:** Codex
