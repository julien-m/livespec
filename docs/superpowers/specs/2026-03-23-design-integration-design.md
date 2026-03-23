# Design Spec: Design Tool Integration in LiveSpec

> **Date:** 2026-03-23
> **Status:** Draft
> **Scope:** Global design config, before-init hook, design protocol, command updates (init, specify, plan, implement, check)

---

## 1. Problem Statement

LiveSpec currently has no visual design validation in its pipeline. Features with UI go from spec (user stories) directly to plan (technical) then implementation — without any mockup generation, visual validation, or design-to-code comparison. This results in:

- No visual contract between spec and code
- No way to validate UI intent before implementation
- No visual regression against a design reference (only against previous code screenshots)
- No mechanism to leverage design tools (Pencil, Figma, Excalidraw) programmatically

Additionally, the `/spec.init` Phase B (stack decisions) operates without access to the user's curated stack reference database (`ai-ressources/stack-ref/`) or their personal preferences, leading to generic recommendations. **Note:** The stack-ref and user-memory loading in the `before-init.md` hook are bundled here for completeness but are independent improvements — they can be implemented or reverted separately from the design integration.

---

## 2. Design Decisions (Approved)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Design tool config location | `~/.claude/livespec/design.md` (global, personal) | LiveSpec is public and tool-agnostic; tool choice is personal preference |
| Design assets location | `.specs/design/` (centralized per project) | Single `.pen`/`.fig` file, one place to open, git tracks history |
| Naming convention | `ui.<ext>` + `screens/<name>.png` + `ui.pdf` | Universal prefix regardless of tool |
| Mockup generation timing | During `/spec.specify` (before plan) | User stories define screens; plan needs validated mockups |
| Versioning strategy | Latest only, git handles history | No `v1`/`v2` files; `git show` for past versions |
| No-config behavior | Gate with wizard on first UI feature | Explicit `tool: none` recorded if user opts out |
| Stack knowledge in init | `before-init.md` hook loads decision-matrix + user memory | Anchors recommendations in curated data, not LLM general knowledge |

---

## 3. Architecture

### 3.1 Global Design Config (`~/.claude/livespec/design.md`)

Personal config file — NOT part of the LiveSpec repo. Defines the user's preferred design tool.

```yaml
---
tool: pencil | figma | excalidraw | html | none
extension: .pen | .fig | .excalidraw | .html
mcp: true | false
exports: [png, pdf]
open_command: open
design_system: shadcn | material | custom
design_system_tokens: path/to/tokens.json  # optional — design system color/spacing tokens
configured: YYYY-MM-DD  # when this config was created/last updated
---

# Design Tool Configuration

Additional instructions for the AI when using this tool.
E.g., "Use shadcn/ui dark theme with zinc color palette" or
"Always export at 2x resolution".
```

**Resolution:** Commands check for this file at hook resolution time. If absent and feature has UI → gate triggers.

### 3.2 Design Gate (No Config Detected)

When `~/.claude/livespec/design.md` does not exist and the current feature involves UI:

**Trigger points:**
- `/spec.init` Phase B (after stack decisions, before installation)
- `/spec.specify` after Step 4 (Read Context Files) and before Step 5 (Generate spec.md)

**Behavior:**

```
⚠️  No design tool configured.

LiveSpec generates visual mockups for UI features.
Without a configured tool, interfaces won't be validated visually before implementation.

Supported tools:
  • Pencil    — browser-based design, MCP integration, export PNG/PDF (.pen)
  • Figma     — collaborative design, API available (.fig)
  • Excalidraw — sketch-style wireframes, CLI available (.excalidraw)
  • HTML      — AI-generated playground, zero dependency (.html)
  • Other     — any tool that exports PNG per screen

→ Configure now? (recommended)
→ Continue without design? (mockups will be skipped)
```

**If "configure now"** → interactive wizard:
1. Which tool? (choice from list)
2. MCP available? (determines if AI can generate directly)
3. Design system? (shadcn, Material, custom)
4. Write `~/.claude/livespec/design.md`

**If "continue without"** → write `design.md` with `tool: none`:

```yaml
---
tool: none
confirmed: 2026-03-23
---
```

This silences the gate for all subsequent features. The user can reconfigure at any time by editing the file or re-running the wizard.

**Second feature and beyond:** If `design.md` exists with `tool: none` → skip silently, no warning. The opt-out decision is respected.

### 3.3 Project Design Directory (`.specs/design/`)

Created by `/spec.init` (Phase C) or on first `/spec.specify` with UI.

```
.specs/design/
├── ui.pen                  ← source file (saved manually by user)
├── ui.pdf                  ← full export (all screens, generated via MCP)
├── screens/
│   ├── login.png           ← per-screen export (generated via MCP)
│   ├── dashboard.png
│   ├── settings.png
│   └── ...
└── changelog.md            ← tracks which screens changed and why
```

**Rules:**
- `ui.<ext>` — one source file per project by default, extension from `design.md`. For large projects with many screens, the user can organize by feature (`design/features/NNN-feature.pen`) as a project-level convention. The pipeline only cares about `screens/*.png` — the source file organization is the user's choice.
- `screens/*.png` — one PNG per screen, always overwritten (latest version only)
- `ui.pdf` — complete PDF export, always overwritten
- `changelog.md` — cross-feature design change log. This exists separately from per-feature changelogs because a single screen can be modified by multiple features over time. The feature changelog records "feature X updated dashboard.png" but `design/changelog.md` records the full history of dashboard.png across all features — useful for designers tracking screen evolution.

**Git behavior:**
- All files tracked in git. PNGs in `screens/` are small reference screenshots (typically < 500KB each) — standard git tracking is appropriate.
- `.specs/design/ui.<ext>` may be large (especially `.pen` or `.fig` files) → add to `.gitattributes` with LFS if needed (user decision, not automated)

### 3.4 Before-Init Hook (`~/.claude/livespec/hooks/before-init.md`)

New global hook that enriches the init Phase B with curated knowledge.

```markdown
---
mode: extend
---

# Before Init — Load Stack Knowledge & User Preferences

## 1. Stack Reference (always load)

**Read** [`decision-matrix.md`](~/projects/ai-ressources/stack-ref/decision-matrix.md) — decision trees, cost comparisons, recommended combos.
**Read** [`index.yaml`](~/projects/ai-ressources/stack-ref/index.yaml) — catalog of all evaluated technologies by category.

Use these references to anchor stack recommendations in evaluated data rather than general knowledge.
When recommending a technology, cite the relevant entry from the stack-ref if available.

## 2. User Preferences (always load)

**Read** [`dev.md`](~/.claude-memory/dev.md) — user's preferred stack, runtime, package manager, testing approach.

Propose the user's preferred technologies first. Present alternatives second.
If a preferred technology is suboptimal for the project's constraints, explain why and suggest the alternative.

## 3. Design Tool Config

**Read** [`design.md`](~/.claude/livespec/design.md) — user's preferred design tool configuration.

If this file exists and `tool` is not `none`:
- Include the design tool in the stack summary during Phase B
- Note the design system for future reference in the constitution
- Add a "Design" row to the recommended stack table

If this file does not exist:
- Trigger the design gate during Phase B (after stack decisions, before Phase C)
```

### 3.5 Command Updates

#### 3.5.1 `/spec.init` — Phase B Addition

After existing stack decisions (framework, deploy, DB, auth, testing) and before the testing strategy:

**New step — Design Tool Check:**

1. Read `~/.claude/livespec/design.md`
2. If exists and `tool != none` → add "Design" row to stack table:
   ```
   | Design | Pencil (MCP) | shadcn/ui dark theme, PNG + PDF export |
   ```
3. If does not exist → trigger the design gate (Section 3.2)
4. Record the design tool choice in `.specs/stacks/_default.md` under a `## Design` section

#### 3.5.2 `/spec.init` — Phase C Addition

In the `.specs/` directory creation, add:

```
.specs/design/
├── screens/            ← empty, ready for mockups
└── changelog.md        ← initial entry
```

Add `.specs/design/` to the installation output message.

Update `.specs/README.md` template with a Design section:

```markdown
## Design

| Document | Description |
|---|---|
| [design/](design/) | UI mockups and screen references |
| [design/changelog.md](design/changelog.md) | Design change history |
```

#### 3.5.3 `/spec.specify` — Mockup Generation

After Step 5 (generate spec.md) and before Step 6 (quality validation), add:

**New Step 5.5 — Generate Mockups (UI features only):**

1. **Detect UI feature:** Scan the generated spec.md for user stories that mention screens, pages, forms, buttons, navigation, or visual elements. If no UI detected → skip.

2. **Check design config:** Read `~/.claude/livespec/design.md`.
   - If missing → trigger design gate (Section 3.2)
   - If `tool: none` → skip silently
   - If tool configured → proceed

3. **Identify screens:** From user stories and flowcharts, list all unique screens/views the feature requires (new screens) and modifies (existing screens).

4. **Generate mockups:**
   - If MCP available (`mcp: true`) → use the tool's MCP to generate mockups programmatically, applying the configured theme/design system
   - If MCP not available → instruct user to create mockups manually and provide the screen list as guidance

5. **Export assets:**
   - Via MCP: export each screen as PNG to `.specs/design/screens/<screen-name>.png`
   - Via MCP: export PDF to `.specs/design/ui.pdf`
   - The source file (`ui.pen`, etc.) must be saved manually by the user

6. **User validation gate:**
   ```
   🎨 Mockups generated for [feature name]:
     • login.png (new)
     • dashboard.png (modified — added notification widget)
     • notification-panel.png (new)

   Exported to .specs/design/screens/

   → Open the design tool to review and save the source file:
     open .specs/design/ui.pen

   → Approve mockups to continue, or describe changes needed.
   ```

7. **Add screen references to spec.md:** After validation, add a `## Screens` section to the feature's `spec.md`:

   ```markdown
   ## Screens

   | Screen | Status | Reference |
   |--------|--------|-----------|
   | login | New | [login.png](../../design/screens/login.png) |
   | dashboard | Modified | [dashboard.png](../../design/screens/dashboard.png) |
   | notification-panel | New | [notification-panel.png](../../design/screens/notification-panel.png) |
   ```

8. **Update design changelog:** Add entry to `.specs/design/changelog.md`:

   ```markdown
   ### YYYY-MM-DD — Feature NNN: [feature name]

   - **login.png** — new screen (login form with social auth buttons)
   - **dashboard.png** — modified (added notification widget top-right)
   - **notification-panel.png** — new screen (slide-out panel with notification list)
   ```

**New quality gate addition (Step 6):**

- [ ] If feature has UI: Screens section exists in spec.md with references to PNG files
- [ ] If feature has UI and design tool configured: PNG files exist in `.specs/design/screens/`

#### 3.5.4 `/spec.specify` — Re-modification Workflow

When `/spec.specify` is run on a feature that already has mockups (screens listed in existing spec.md):

1. Detect existing screens from the current spec's `## Screens` section
2. Determine which screens need updating based on spec changes
3. If MCP available → open the source file (`ui.pen`) via MCP, modify affected screens
4. Re-export updated PNGs, overwriting the previous versions
5. Present the user with the list of changes for validation
6. User saves the source file manually
7. Update design changelog

#### 3.5.5 `/spec.plan` — Mockup Reference

In the plan template, after "Technical Context" and before "Constitution Check":

**New section — Design Reference:**

```markdown
## Design Reference

| Screen | Component Breakdown | Reference |
|--------|-------------------|-----------|
| login | LoginForm, SocialAuthButtons, AuthLayout | [login.png](../../design/screens/login.png) |
| dashboard | DashboardLayout, NotificationWidget, StatsGrid | [dashboard.png](../../design/screens/dashboard.png) |
```

The plan uses the validated mockups to:
- Identify components to create
- Determine the component hierarchy
- Define the layout structure
- Plan responsive breakpoints

**Before-plan hook addition:** The existing `before-plan.md` hook should verify:
- If the feature's spec.md has a `## Screens` section → check that referenced PNGs exist
- If PNGs are missing → warn before proceeding (soft gate, not blocking)

#### 3.5.6 `/spec.implement` — Visual Comparison

During implementation, when creating UI components:

1. **Reference mockups:** At each step that creates a UI component, reference the corresponding mockup PNG from `.specs/design/screens/`
2. **Fidelity check:** After generating a component, the AI compares its output mentally against the mockup. If the feature has visual testing configured, capture a Playwright screenshot and diff against the mockup PNG.
3. **Implementation.md update:** Add a "Visual Reference" column to the requirement mapping:

   ```markdown
   | FR | File(s) | @spec Anchor | Visual Ref | Status |
   |---|---|---|---|---|
   | FR-001 | `src/components/Login.tsx` | @spec FR-001 | [login.png](../../design/screens/login.png) | ✅ |
   ```

#### 3.5.7 `/spec.check` — Design Drift Detection

Extend Step 8 (Detect Visual Drift) to also compare against design mockups:

**New sub-step — Design Fidelity Check:**

1. Read the feature's `## Screens` section from spec.md
2. For each referenced screen:
   a. If Playwright baselines exist in `baselines/` → compare baseline vs mockup PNG
   b. Report fidelity status:
      - ✅ Faithful — implementation matches mockup (< 5% diff, higher threshold than code regression)
      - 🎨 Diverged — implementation differs from mockup (> 5% diff)
      - ❌ No baseline — cannot compare (no Playwright screenshot captured)

3. Add to gap report:

   ```markdown
   ### Design Fidelity

   | Screen | Mockup | Baseline | Diff | Status |
   |--------|--------|----------|------|--------|
   | login | [mockup](../../design/screens/login.png) | [baseline](baselines/login.png) | 2.1% | ✅ Faithful |
   | dashboard | [mockup](../../design/screens/dashboard.png) | [baseline](baselines/dashboard.png) | 8.4% | 🎨 Diverged |
   ```

**Threshold distinction:**
- **Visual regression** (code vs previous code): 2% threshold — catches unintended CSS changes
- **Design fidelity** (code vs mockup): 5% threshold — allows minor implementation differences while catching major layout drift

---

## 4. Spec Template Updates

### 4.1 `spec-template.md` — Add Screens Section

After "Key Entities" and before "Infrastructure Requirements":

```markdown
## Screens

> **Include this section only when the feature involves user-facing interfaces.** Omit entirely for API-only or backend features.
> Screens are generated during `/spec.specify` using the configured design tool (see `~/.claude/livespec/design.md`).

| Screen | Status | Reference |
|--------|--------|-----------|
| [screen-name] | New / Modified | [screen-name.png](../../design/screens/screen-name.png) |
```

### 4.2 `plan-template.md` — Add Design Reference Section

After "Technical Context" table:

```markdown
## Design Reference

> **Include this section only when the feature has screens defined in spec.md.** Omit for non-UI features.

| Screen | Component Breakdown | Reference |
|--------|-------------------|-----------|
| [screen-name] | [Component1, Component2, ...] | [screen-name.png](../../design/screens/screen-name.png) |
```

### 4.3 `implementation-template.md` — Add Visual Reference Column

Extend the Requirement Mapping table with an optional "Visual Ref" column when screens exist.

---

## 5. Hook Updates

### 5.1 New: `~/.claude/livespec/hooks/before-init.md`

Content as described in Section 3.4.

### 5.2 Update: `~/.claude/livespec/hooks/before-specify.md`

Add a new section after the current last section:

```markdown
## Design Tool Config

**Read** [`design.md`](~/.claude/livespec/design.md) — load the design tool configuration.

If tool is configured and not `none`:
- Prepare to generate mockups after spec generation
- Load the theme tokens if specified in design.md
```

### 5.3 Update: `~/.claude/livespec/hooks/before-plan.md`

Add a new section after the current last section:

```markdown
## Design Mockup Validation

If the feature spec.md contains a `## Screens` section:
- Verify that all referenced PNG files exist in `.specs/design/screens/`
- If any are missing, warn before proceeding: "Screen mockup [name].png referenced in spec but not found"
```

### 5.4 Update: `~/.claude/livespec/hooks/before-implement.md`

Add a new section after the current last section:

```markdown
## Design Reference

If the feature spec.md contains a `## Screens` section:
- **Read** each referenced PNG from `.specs/design/screens/` as the visual target
- When implementing UI components, match the layout, colors, and spacing from the mockup
- Use the design system tokens (shadcn, Material, etc.) specified in the project's constitution
```

---

## 6. `spec-system.md` Updates

### 6.1 Project Layout — Add Design Directory

In the `.specs/` tree diagram:

```
├── design/
│   ├── ui.<ext>            ← Design source file (tool-specific)
│   ├── ui.pdf              ← Full PDF export
│   ├── screens/            ← Per-screen PNG exports
│   │   └── *.png
│   └── changelog.md        ← Design change history
```

### 6.2 Quality Gates — Add Design Gate

In "Before a spec is considered complete":

```
- [ ] If feature has UI screens: `## Screens` section exists with PNG references
- [ ] If design tool configured: referenced PNGs exist in `.specs/design/screens/`
```

In "Before implementation is considered complete":

```
- [ ] For visual features with design mockups: design fidelity check performed
```

### 6.3 Rules for AI Tools — Add Design Convention

New subsection after "When REVIEWING a feature":

```markdown
### When working with DESIGN mockups

1. Design mockups are centralized in `.specs/design/` — one source file per project
2. PNGs in `screens/` are the reference for implementation — always the latest version
3. The design source file (`ui.pen`, `ui.fig`, etc.) is saved manually by the user
4. When a feature modifies existing screens, overwrite the PNG — git tracks history
5. The `## Screens` section in `spec.md` links features to their visual references
6. Design fidelity threshold is 5% (more permissive than visual regression at 2%)
```

---

## 7. Edge Cases

- **Feature with no UI:** The entire design workflow is skipped. No `## Screens` section in spec, no mockup generation, no design fidelity check.
- **Design tool without MCP:** The AI provides the screen list and descriptions but cannot generate mockups programmatically. The user creates them manually. Export and validation still work if the user places PNGs in the right location.
- **Multiple features modifying the same screen:** Both features reference the same PNG. The second feature to run specify will update the PNG, overwriting the first version. The design changelog tracks which feature caused each change.
- **Switching design tools mid-project:** The user updates `~/.claude/livespec/design.md`. The source file extension changes. Old source file remains in git history. New screens are generated with the new tool. PNGs are still PNGs — the rest of the pipeline doesn't care about the source format.
- **Large .pen/.fig files:** Not automated — the user decides whether to use Git LFS. LiveSpec does not enforce this.
- **Large projects with many screens:** A single source file may become impractical. The user can organize by feature (`design/features/NNN-feature.pen`) as a project-level convention. The pipeline only cares about `screens/*.png` — the source file organization is the user's choice.

---

## 8. Files to Create/Modify

### Create

| File | Description |
|------|-------------|
| `~/.claude/livespec/hooks/before-init.md` | New global hook — loads stack-ref + user memory + design config |

### Modify

| File | Change |
|------|--------|
| `system/spec-system.md` | Add `.specs/design/` to project layout, add design quality gates, add design convention rules |
| `system/templates/spec-template.md` | Add `## Screens` section template |
| `system/templates/plan-template.md` | Add `## Design Reference` section template |
| `system/templates/implementation-template.md` | Add "Visual Ref" column note |
| `commands/init.md` | Add design gate in Phase B, add `.specs/design/` creation in Phase C, update exit criteria |
| `commands/specify.md` | Add Step 5.5 (mockup generation), update quality gates, add re-modification workflow |
| `commands/plan.md` | Add Design Reference section generation after Technical Context |
| `commands/implement.md` | Add mockup reference during UI steps, visual fidelity check, Visual Ref column in implementation.md |
| `commands/check.md` | Add design fidelity sub-step in Step 8, add to gap report format |
| `~/.claude/livespec/hooks/before-specify.md` | Add design tool config loading |
| `~/.claude/livespec/hooks/before-plan.md` | Add mockup existence validation |
| `~/.claude/livespec/hooks/before-implement.md` | Add design reference loading |

---

*Design Spec — LiveSpec Design Integration v1.0*
