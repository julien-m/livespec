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
| Tool-specific | **Tool-agnostic** — works with Claude Code or any AI that reads Markdown |

---

## The 7 Commands

| Command | What it does |
|---|---|
| `/spec.init` | 3-phase conversational brainstorm → generates project profile, stack, `.specs/` structure + CLAUDE.md |
| `/spec.specify` | Create a new feature spec with user stories, Mermaid flows, AC, and FR |
| `/spec.plan` | Generate technical plan with sequence, state, and ER diagrams |
| `/spec.implement` | APEX-style auto-pipeline: implement → test → visual baselines → map to spec. Multi-agent orchestration by default (`--mono` for single-agent) |
| `/spec.check` | Compare spec vs actual code — find gaps, verify AC, detect visual drift |
| `/spec.explain` | "How does X work?" — living documentation from spec + diagrams + history |
| `/spec.stack` | Evolve your stack and analyze impact on existing features |

---

## Quick Start

### Claude Code (recommended)

```bash
# 1. Clone LiveSpec
git clone https://github.com/julien-m/livespec.git ~/livespec

# 2. Install /spec.* commands globally
bash ~/livespec/scripts/install.sh

# 3. Initialize LiveSpec in your project (creates .specs/ + CLAUDE.md)
cd your-project
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

### Other AI tools

For any AI tool that reads Markdown, paste the content of `system/spec-system.md` into your tool's context. The spec system is tool-agnostic — any AI that can read `.specs/` will follow the rules.

---

## Project Structure Created by `/spec.init`

```
.specs/
├── README.md               ← Spec registry and artifact index (auto-maintained)
├── spec-system.md          ← The rules (READ FIRST — every tool reads this)
├── constitution.md         ← Project architecture principles
├── project.md              ← Vision, users, constraints (from brainstorm)
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

## Installation

```bash
bash scripts/install.sh              # Install /spec.* commands
bash scripts/install.sh --dry-run    # Preview without changes
bash scripts/install.sh --force      # Overwrite existing symlinks
bash scripts/install.sh --uninstall  # Remove all symlinks
```

Installs 7 commands (`~/.claude/commands/spec.*.md`) and 5 agents (`~/.claude/agents/livespec-*.md`) as symlinks. Changes to the LiveSpec repo are immediately reflected — no re-install needed.

For other AI tools, paste `system/spec-system.md` into your tool's context.

---

## Comparison

| Feature | LiveSpec | Spec Kit (GitHub) | APEX (aiblueprint) |
|---|---|---|---|
| Mermaid diagrams | ✅ Mandatory | ❌ None | ❌ None |
| Spec-to-code traceability | ✅ FR/AC → `@spec` anchors with deep-links | ❌ None | ⚠️ Partial |
| Per-feature changelogs | ✅ Yes | ❌ No | ❌ No |
| Visual testing baselines | ✅ Playwright | ❌ None | ❌ None |
| Stack presets + decision trees | ✅ Yes | ❌ No | ⚠️ Minimal |
| Brainstorm-driven init | ✅ 3-phase conversation | ❌ No | ⚠️ Partial |
| Gap detection (spec vs code) | ✅ `/spec.check` | ❌ None | ❌ None |
| Living documentation | ✅ `/spec.explain` | ❌ None | ❌ None |
| Stack evolution + impact | ✅ `/spec.stack` | ❌ None | ❌ None |
| Tool-agnostic | ✅ Yes (Markdown-based) | ⚠️ GitHub only | ⚠️ Claude only |

---

## Multi-Agent Mode (default)

`/spec.implement` uses multi-agent orchestration by default — a supervisor dispatches work to 4 specialized agents:

```
                  +-----------------+
                  |   SUPERVISOR    |
                  |  (orchestrator) |
                  +--------+--------+
                           |
         +---------+-------+-------+---------+
         |         |               |         |
   +-----+----+ +-+--------+ +----+-----+ +-+----------+
   | IMPLEMENT| |  VERIFY   | |   TEST   | |    DOC     |
   | (coder)  | | (devil's  | | (tester) | | (writer)   |
   |          | |  advocate) | |          | |            |
   +----------+ +----------+ +----------+ +------------+
```

```bash
# Multi-agent implementation (default)
/spec.implement notifications

# Single-agent mode (original APEX pipeline)
/spec.implement notifications --mono

# Resume an interrupted run
/spec.implement notifications --resume
```

**Per-step cycle:** Implement → Verify (adversarial) → Test → Document checkpoint. The verifier acts as a devil's advocate — no rubber-stamping. Blocking findings are re-dispatched to the implementer (max 3 iterations). Each agent can spawn sub-agents for intra-step parallelism (e.g., writing independent files simultaneously).

Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: 1` in settings.

---

## Repository Structure

```
livespec/
├── README.md
├── system/
│   ├── spec-system.md              ← Core rules (install in .specs/)
│   ├── constitution-template.md    ← Constitution template
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
├── agents/                         ← Agent definitions (symlinked by install.sh)
│   ├── livespec-supervisor.md      ← Orchestrator — decomposes plan, dispatches agents
│   ├── livespec-implementer.md     ← Writes production code
│   ├── livespec-verifier.md        ← Adversarial reviewer (read-only)
│   ├── livespec-tester.md          ← Runs/creates tests
│   └── livespec-documenter.md      ← Updates spec artifacts
├── commands/                       ← Command docs (symlinked by install.sh)
│   ├── init.md
│   ├── specify.md
│   ├── plan.md
│   ├── implement.md
│   ├── check.md
│   ├── explain.md
│   └── stack.md
└── scripts/
    ├── install.sh                  ← Install commands + agents into ~/.claude/
    └── init.sh                     ← Bootstrap .specs/ structure (shell)
```

---

## License

MIT — see [LICENSE](LICENSE)

