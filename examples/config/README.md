# LiveSpec — Config Examples

This directory ships copy-paste templates for user-level extensions
under `~/.config/livespec/`. Each `*.example` file is **OPT-IN**:
LiveSpec does NOT reference, load, or invoke any of these unless you
explicitly copy the file to `~/.config/livespec/<name>.md`.

## Available templates

| Template | Activate by |
|----------|-------------|
| `mockups.md.example` | `cp mockups.md.example ~/.config/livespec/mockups.md` |

## How it works

`*.md` files under `~/.config/livespec/` are **Level 0 user
integrations** in the LiveSpec hook resolution chain. Each integration
declares the commands it targets via YAML frontmatter
(`integration:` + `commands:`). LiveSpec injects the markdown body
into the LLM context BEFORE (or AFTER) the targeted command runs.

See [`../../system/integrations.md`](../../system/integrations.md) for
the full pattern: schema, ordering, override scope, template variables,
and the diagnostic CLI surfaces.

## Disabling

Remove or rename the file under `~/.config/livespec/` — LiveSpec
returns to default behavior with zero residual mention of the
integration.
