# Flag Aliases Reference

Short aliases for all `/spec.*` command flags. Each alias is unique within its command.

## Global aliases (shared across commands)

| Long | Short | Commands |
|------|-------|----------|
| `--auto` | `-a` | feature, implement, specify, propose, refine, init, plan |
| `--resume` | `-r` | feature, implement, ship |
| `--dry-run` | `-d` | init, stack, preflight, refine, refresh-conventions |
| `--force` | `-f` | stack, preflight, refresh-conventions |
| `--mono` | `-m` | feature, implement, ship |
| `--economy` | `-e` | feature, implement, ship |
| `--branch` | `-b` | feature, specify |
| `--no-branch` | `-B` | feature, specify |
| `--priority` | `-p` | feature, specify |
| `--step` | `-s` | feature, implement |
| `--count` | `-n` | ship, propose |
| `--no-visual` | `-V` | implement, check |

## Per-command aliases

### spec.feature

`-a` auto, `-r` resume, `-b` branch, `-B` no-branch, `-p` priority, `-m` mono, `-e` economy, `-s` step

### spec.implement

`-a` auto, `-N` no-save, `-m` mono, `-e` economy, `-r` resume, `-V` no-visual, `-s` step

### spec.specify

`-a` auto, `-b` branch, `-B` no-branch, `-p` priority

### spec.plan

`-a` auto, `-r` review, `-R` all-reviewers, `-C` no-contracts, `-D` diagram-only

### spec.check

`-u` update, `-V` no-visual, `-x` fix, `-R` report, `-t` tree-only, `-T` skip-tree, `-q` quality, `-A` all, `-S` summary

### spec.explain

`-D` diagrams-only, `-H` history, `-c` code, `-w` why, `-S` since

### spec.ship

`-t` tier, `-n` count, `-r` resume, `-m` mono, `-e` economy

### spec.propose

`-n` count, `-r` role, `-M` mvp, `-a` auto

### spec.status

`-R` roadmap, `-F` features, `-j` json

### spec.hooks

`-v` verbose, `-c` create, `-g` global, `-l` local, `-e` edit

### spec.init

`-a` auto, `-s` stack, `-D` dir, `-d` dry-run

### spec.stack

`-d` dry-run, `-A` no-adr, `-M` no-migration-specs, `-f` force

### spec.preflight

`-l` light, `-r` regenerate, `-f` force, `-d` dry-run

### spec.refine

`-a` auto, `-d` dry-run

### spec.refresh-conventions

`-f` force, `-d` dry-run
