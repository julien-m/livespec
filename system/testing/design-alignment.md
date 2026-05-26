# Design Alignment Protocol

<!-- @spec FR-001: Global design alignment workflow — .specs/features/047-design-alignment-gate/spec.md#fr-001 -->

> Reusable LiveSpec workflow derived from the CloudSkill Playbook — Mockup-Code Alignment.
> It aligns the canonical Pencil mockup (`penflow/ui.pen`) with runtime UI contracts before approving a first or refreshed screenshot baseline.

## Purpose

Use this protocol whenever a visual feature starts from a new mockup, a changed `penflow/ui.pen` design source, or a redesigned screen/state. It prevents the first screenshot baseline from becoming an accidental snapshot of an incorrect implementation.

`Design Alignment Verdict: PASS | FAIL | BLOCKED`

| Verdict | Meaning | Exit code |
|---|---|---|
| `PASS` | Design support matches runtime support and all required nodes/properties align. | 0 |
| `FAIL` | Support matches, but runtime nodes/tokens/layout/states diverge from `penflow/ui.pen`. | 1 |
| `BLOCKED` | Inputs or support are not comparable: missing `penflow/ui.pen`, missing runtime capture, frame/safe-area/header/DPR/shape mismatch, or unreadable contract. | 2 |

## Invocation Point

`/spec-test --visual` runs this protocol before baseline capture when:

- the feature has a `## Screens` section, and
- `penflow/ui.pen` exists, and
- the screen has no approved baseline, or the stored design hash differs from the current design source.

For unchanged screens with approved baselines, use `system/testing/visual-baselines.md` instead.

## Worker: Pencil to Design Contract

The design extractor reads `penflow/ui.pen`, verifies support normalization first, then emits one design contract per screen:

```json
{
  "screen": "dashboard",
  "support": {
    "width": 393,
    "height": 852,
    "dpr": 3,
    "orientation": "portrait",
    "shape": "rectangular",
    "safe_area_top": 47,
    "header_height": 44,
    "decorative_shell": false
  },
  "nodes": [
    {
      "id": "dashboard.primary-action",
      "name": "PrimaryButton",
      "type": "button",
      "bounds": {"x": 24, "y": 120, "width": 180, "height": 44},
      "styles": {
        "fill": "#0066FF",
        "text_color": "#FFFFFF",
        "font_size": 14,
        "font_weight": 600,
        "padding": "12px 16px",
        "corner_radius": 6
      },
      "text": "Continue",
      "states": {"disabled": {"opacity": 0.5}}
    }
  ]
}
```

The extractor must output `SUPPORT_MATCH: yes/no` with details for frame, shape, safe-area, header/status bar, visible time if present, and decorative shell status.

## Validator: Runtime Contract to Design Contract

The runtime capture comes from the active UI runner:

- Web: DOM/accessibility tree + computed styles + Playwright viewport.
- iOS/watchOS: accessibility tree + frame data + simulator device metadata.
- Android: UI hierarchy + device metadata.
- Tauri: WebView accessibility/DOM contract where available.

The validator compares:

- component/node identity (`id`, `name`, `type`)
- hierarchy and presence
- bounds (`x`, `y`, `width`, `height`)
- visual tokens (colors, typography, radius, padding, gap)
- text labels and icons
- states (`hover`, `focus`, `disabled`, `selected`, `loading`, `error`)
- responsive/device variant declared for the screen

## Acceptance Rules

- Fuzzy matching is not passing.
- Color variable aliases are acceptable only when the resolved value equals the Pencil color.
- Spacing and bounds may use a documented ±1px tolerance.
- Missing states fail unless a platform-specific accessible alternative is documented.
- Support mismatches are `BLOCKED`, not warnings.
- Design/runtime divergence is `FAIL`, not a warning, when the command runs as a gate.

## Artifacts

Store artifacts under the feature:

```text
.specs/features/NNN-feature/design-alignment/
├── <screen>.design.json
├── <screen>.runtime.json
├── <screen>.diff.json
├── <screen>.report.md
└── design-alignment.manifest.json
```

`/spec-test --visual` includes the verdict and report path in `checks/YYYY-MM-DD-test.md`.
