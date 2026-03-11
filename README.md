# 🔥 LiveSpec — Specs that live beyond implementation

> A universal, tool-agnostic specification framework with visual diagrams, living documentation, and spec-to-code traceability for AI-driven development.

---

## The Problem

Specs today are **throwaway documents**:

- Written once, never updated after implementation
- No visual diagrams — just walls of text
- No traceability between spec requirements and actual code
- No history of what changed and why
- Tools and AI assistants forget the context

Six months later, nobody knows **why** something was built the way it was.

---

## What LiveSpec Does Differently

| Problem | LiveSpec Solution |
|---|---|
| No visuals | **Mermaid diagrams mandatory** in every spec and plan |
| No traceability | **Implementation mapping** — every spec requirement links to `@spec` anchors in code |
| Specs rot after launch | **Living docs** — specs updated when behavior changes |
| No history | **Per-feature changelogs** — every change is recorded |
| No visual testing | **Playwright baselines** built into implementation + check |
| Stack decisions lost | **Stack presets with decision trees** — know WHY you chose each tool |
| One-time init | **Brainstorm-driven init** — AI interviews you before generating anything |
| Tool-specific | **Tool-agnostic** — works with Copilot, Claude Code, Cursor, or any AI |

---

## The 8 Commands

| Command | What it does |
|---|---|
| `/spec.init` | 3-phase conversational brainstorm → generates project profile, stack, and `.specs/` structure |
| `/spec.specify` | Create a new feature spec with user stories, Mermaid flows, AC, and FR |
| `/spec.plan` | Generate technical plan with sequence, state, and ER diagrams |
| `/spec.implement` | APEX-style auto-pipeline: implement → test → visual baselines → map to spec |
| `/spec.check` | Compare spec vs actual code — find gaps, verify AC, detect visual drift |
| `/spec.explain` | "How does X work?" — living documentation from spec + diagrams + history |
| `/spec.stack` | Evolve your stack and analyze impact on existing features |
| `/spec.link` | Install AI tool adapters and make commands discoverable in your project |

---

## Quick Start

```bash
# 1. Install LiveSpec in your project
# Tip: review the script before running: https://github.com/julien-m/livespec/blob/main/scripts/init.sh
curl -s https://raw.githubusercontent.com/julien-m/livespec/main/scripts/init.sh -o /tmp/livespec-init.sh
bash /tmp/livespec-init.sh

# 2. Link your AI tool (installs adapter + copies command docs)
/spec.link copilot    # or claude-code, cursor, all
# OR: bash /path/to/livespec/scripts/link.sh --tool copilot

# 3. Or initialize via your AI tool (includes linking prompt)
/spec.init

# 4. Create your first feature spec
/spec.specify "User can receive real-time notifications"

# 5. Generate technical plan
/spec.plan notifications

# 6. Implement with auto-pipeline
/spec.implement notifications

# 7. Verify spec vs code
/spec.check notifications

# 8. Explain the feature (living docs)
/spec.explain "how do notifications work?"
```

---

## Project Structure Created by `/spec.init`

```
.specs/
├── spec-system.md          ← The rules (READ FIRST — every tool reads this)
├── constitution.md         ← Project architecture principles
├── project.md              ← Vision, users, constraints (from brainstorm)
│
├── commands/               ← LiveSpec command docs (installed by /spec.link)
│   ├── init.md
│   ├── specify.md
│   ├── plan.md
│   ├── implement.md
│   ├── check.md
│   ├── explain.md
│   ├── stack.md
│   └── link.md
│
├── stacks/
│   ├── _default.md         ← Your chosen stack + reasoning
│   └── decisions/          ← Architecture Decision Records (ADRs)
│       └── ADR-001-*.md
│
├── testing/
│   └── strategy.md         ← What to test, how, with which tools
│
├── features/
│   └── 001-notifications/
│       ├── spec.md          ← WHAT and WHY (user stories, Mermaid flows, AC, FR)
│       ├── plan.md          ← HOW (sequence/state/ER diagrams, file-by-file plan)
│       ├── implementation.md ← WHERE in code (FR/AC → @spec mapping)
│       ├── changelog.md     ← WHEN (every change recorded)
│       ├── contracts/       ← API contracts (OpenAPI/GraphQL)
│       └── baselines/       ← Playwright visual screenshots
│
└── changelog.md            ← Global project changelog
```

---

## Multi-Tool Support

LiveSpec is **tool-agnostic**. All commands are written as Markdown skills that any AI can follow.

| Tool | Adapter | Location | Installed to |
|---|---|---|---|
| GitHub Copilot | Agent config | `adapters/copilot/agent.md` | `.github/copilot-instructions.md` |
| Claude Code / APEX | Skill file | `adapters/claude-code/SKILL.md` | `CLAUDE.md` (or `~/.claude/skills/livespec.md`) |
| Cursor | Rules file | `adapters/cursor/.cursorrules` | `.cursorrules` |
| Any AI | Paste `system/spec-system.md` | Works universally | — |

### Linking adapters with `/spec.link`

After running `/spec.init`, link your AI tool so it knows where to find LiveSpec commands:

```bash
/spec.link copilot       # Creates .github/copilot-instructions.md
/spec.link claude-code   # Creates CLAUDE.md at project root
/spec.link cursor        # Copies/appends to .cursorrules
/spec.link all           # All of the above
```

This also copies all command documentation into `.specs/commands/` so your AI tool can read detailed instructions locally without accessing the LiveSpec repository.

To run as a shell script directly:

```bash
bash /path/to/livespec/scripts/link.sh --tool copilot
bash /path/to/livespec/scripts/link.sh --tool all --force
```

---

## Comparison

| Feature | LiveSpec | Spec Kit (GitHub) | APEX (aiblueprint) |
|---|---|---|---|
| Mermaid diagrams | ✅ Mandatory | ❌ None | ❌ None |
| Spec-to-code traceability | ✅ FR/AC → `@spec` anchors | ❌ None | ⚠️ Partial |
| Per-feature changelogs | ✅ Yes | ❌ No | ❌ No |
| Visual testing baselines | ✅ Playwright | ❌ None | ❌ None |
| Stack presets + decision trees | ✅ Yes | ❌ No | ⚠️ Minimal |
| Brainstorm-driven init | ✅ 3-phase conversation | ❌ No | ⚠️ Partial |
| Gap detection (spec vs code) | ✅ `/spec.check` | ❌ None | ❌ None |
| Living documentation | ✅ `/spec.explain` | ❌ None | ❌ None |
| Stack evolution + impact | ✅ `/spec.stack` | ❌ None | ❌ None |
| Tool-agnostic | ✅ Yes | ⚠️ GitHub only | ⚠️ Claude only |

---

## Repository Structure

```
livespec/
├── README.md
├── system/
│   ├── spec-system.md              ← Core rules (install in .specs/)
│   ├── constitution-template.md   ← Constitution template
│   └── templates/
│       ├── spec-template.md
│       ├── plan-template.md
│       ├── implementation-template.md
│       ├── changelog-template.md
│       ├── project-template.md
│       └── testing-strategy-template.md
├── stacks/
│   └── presets/
│       ├── web-realtime.md
│       ├── web-static.md
│       └── api-rest.md
├── commands/
│   ├── init.md
│   ├── specify.md
│   ├── plan.md
│   ├── implement.md
│   ├── check.md
│   ├── explain.md
│   ├── stack.md
│   └── link.md                    ← /spec.link command
├── scripts/
│   ├── init.sh                    ← Bootstrap .specs/ structure
│   └── link.sh                    ← Install adapters + command docs
└── adapters/
    ├── copilot/agent.md           ← → .github/copilot-instructions.md
    ├── claude-code/SKILL.md       ← → CLAUDE.md or ~/.claude/skills/livespec.md
    └── cursor/.cursorrules        ← → .cursorrules
```

---

## License

MIT — see [LICENSE](LICENSE)

