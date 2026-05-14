# Pipeline — 045-native-behavioral-specs

**Started:** 2026-05-14 10:07
**Flags:** `--auto`
**Feature Description:** Make `/spec.specify` autonomous on behavioral specs — produce flow + N screens (per F044 grammar v1.0) WITHOUT depending on brainstorm. Three modes auto-detected by priority: (a) reuse import F041 if `.specs/flows/<slug>.md` exists (already covered by F042, do not modify); (b) native interview if no flow + no mockups — structured section-by-section interview covering the 8 mandatory flow sections + 8 mandatory screen sections from F044 grammar, no LLM-generic prompts, "skip"/empty input → `(to fill later)` placeholder + WARNING from validator; (c) mockup-derived if no flow + `.specs/design/screens/*.png` (or `ui.pen`) exist — analyze mockups + short interview for the remaining canonical screen sections (`Acteur`, `Source d'entrée`, `Sortie principale`, `Validations`, `Erreurs`), draft marked `derivedFrom: native-mockups`. All natively-generated artefacts: `specStatus: manual` (protects against re-import overwrite per F041 contract); MUST pass `validate_behavioral()` from F044 with PASS or WARNING (never FAIL — STOP + BLOCKED otherwise). Format identical to F041 imports (interchangeable). No modification of F041/042/043/044 spec.md. Optional `--native` / `--from-mockups` flags on `/spec.specify` if convention warrants. Scope L, Priority P1.

| Phase | Status | Completed At |
|-------|--------|--------------|
| Specify | Done | 2026-05-14 10:16 |
| Spec Review | Done | 2026-05-14 10:16 |
| Plan | Done | 2026-05-14 10:23 |
| Plan Review | Done | 2026-05-14 10:23 |
| Preflight | Done | 2026-05-14 10:24 |
| Implement | Done | 2026-05-14 10:35 |
| Test | Done | 2026-05-14 10:39 |
