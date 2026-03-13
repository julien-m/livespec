# Visual Baselines Protocol

> Universal workflow for screenshot-based visual regression testing — not tied to any specific tool.
> Applies only to features with UI components. Skip for non-UI features.

---

## Capture

On first successful run, capture screenshots of key states:
- Empty state
- Loaded state with data
- Interactive states (hover, open, etc.)
- Error states

## Storage

Baselines are stored in `.specs/features/NNN-feature-name/baselines/`.

## Comparison

On each subsequent run, capture new screenshots and compare against stored baselines.

## Threshold

Diff > 2% → test FAILS.

## Update

When a change is intentional, update the baselines and commit them.

## Archival

Old baselines are moved to `baselines/archived/YYYY-MM-DD/` before replacement.

## Systematic capture

Every passing visual test saves its screenshot as the new reference baseline, enabling regression detection on the next run.

## Prerequisite check

The visual tool availability is resolved **once** during discovery (see `discovery.md` step 3) and recorded in Resolved Test Commands.

- If status is `Verified` → proceed with visual tests
- If status is `Not available` → skip visual tests, no re-detection needed
- Log when skipped: "Visual baselines skipped — no visual testing tool resolved"

The exact capture/compare command comes from the **Resolved Test Commands** in `plan.md`.

---

*LiveSpec Test Protocol — Visual Baselines v1.1*
