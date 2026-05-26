# Design Alignment Quality Contract

<!-- @spec FR-001: Global design alignment workflow — .specs/features/047-design-alignment-gate/spec.md#fr-001 -->

The Design Alignment Gate is only meaningful when Pencil and runtime captures share the same support. If support differs, LiveSpec must return `BLOCKED`.

## Mandatory Support Parity

- **same frame size**: mockup frame width and height equal the target simulator/browser export.
- **same DPR/scale**: Pencil export and runtime capture agree on pixel ratio.
- **same orientation**: portrait/landscape must match.
- **same safe-area**: top/bottom/left/right insets match the simulator/browser target.
- **same header/status bar**: header height, visible system time, status indicators, and top content Y align.
- **same shape**: rectangular viewport if the simulator exports a rectangle.
- **no decorative shell**: no device casing, extra rounded corner mask, shadow, or bezel unless the runtime export contains it.
- **same fonts**: required fonts installed or documented platform aliases resolved.
- **deterministic data**: timestamps, network data, avatars, animation frames, and random values are frozen or masked.
- **animations disabled**: transitions/keyframes are disabled except for explicit animation tests.

## Failure Semantics

| Problem | Verdict |
|---|---|
| Missing `penflow/ui.pen` for a new mockup-driven visual screen | `BLOCKED` |
| Missing runtime contract | `BLOCKED` |
| Frame/DPR/safe-area/header/shape mismatch | `BLOCKED` |
| Missing runtime component | `FAIL` |
| Token/layout/text/state mismatch | `FAIL` |
| All support and component checks aligned | `PASS` |

## Recovery Guidance

For `BLOCKED`, fix the capture setup before judging UI quality:

- export Pencil with the correct target frame
- remove decorative device shells
- use the same simulator/device profile
- align safe-area/header settings
- install fonts or configure documented aliases
- regenerate the runtime contract

For `FAIL`, fix implementation code to match the current approved `penflow/ui.pen`; do not update the baseline screenshot until the alignment gate passes.
