#!/usr/bin/env bash
set -euo pipefail

# LiveSpec — Installer for Claude Code
# Usage:
#   bash scripts/install.sh              # Install commands
#   bash scripts/install.sh --uninstall  # Remove symlinks
#   bash scripts/install.sh --force      # Overwrite existing files
#   bash scripts/install.sh --dry-run    # Preview without changes

# --- Config ---

LIVESPEC_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMMANDS_DIR="$HOME/.claude/commands"
AGENTS_DIR="$HOME/.claude/agents"

COMMANDS=(init specify plan implement check explain stack feature)
AGENTS=(livespec-supervisor livespec-implementer livespec-verifier livespec-tester livespec-documenter)

# --- Flags ---

FORCE=false
DRY_RUN=false
UNINSTALL=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)     FORCE=true; shift ;;
    --dry-run)   DRY_RUN=true; shift ;;
    --uninstall) UNINSTALL=true; shift ;;
    --help|-h)
      cat <<'EOF'
Usage: bash scripts/install.sh [OPTIONS]

Installs LiveSpec /spec.* commands and agents into ~/.claude/.

Options:
  --force         Overwrite existing files/symlinks
  --dry-run       Preview changes without writing anything
  --uninstall     Remove installed symlinks
  --help          Show this help message

Examples:
  bash scripts/install.sh              # Install commands + agents
  bash scripts/install.sh --uninstall  # Remove commands + agents
  bash scripts/install.sh --dry-run    # Preview
  bash scripts/install.sh --force      # Overwrite existing
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Run with --help for usage." >&2
      exit 1
      ;;
  esac
done

# --- Helpers ---

ok()   { echo "  ✓ $1"; }
skip() { echo "  · $1 (skipped — already correct)"; }
warn() { echo "  ! $1" >&2; }
dry()  { echo "  → [dry-run] $1"; }

create_link() {
  local src="$1"
  local target="$2"
  local label="$3"

  if [[ "$DRY_RUN" == true ]]; then
    dry "$label → $src"
    return
  fi

  if [[ -L "$target" ]]; then
    local current
    current="$(readlink "$target")"
    if [[ "$current" == "$src" ]]; then
      skip "$label"
      return
    fi
    if [[ "$FORCE" == true ]]; then
      rm "$target"
    else
      warn "$label exists but points to $current (use --force to overwrite)"
      return
    fi
  elif [[ -e "$target" ]]; then
    if [[ "$FORCE" == true ]]; then
      rm "$target"
    else
      warn "$label exists as a regular file (use --force to overwrite)"
      return
    fi
  fi

  ln -sf "$src" "$target"
  ok "$label"
}

remove_link() {
  local target="$1"
  local label="$2"

  if [[ ! -L "$target" ]]; then
    if [[ -e "$target" ]]; then
      warn "$label is not a symlink — skipping (remove manually if needed)"
    fi
    return
  fi

  local current
  current="$(readlink "$target")"
  if [[ "$current" == "$LIVESPEC_ROOT"* ]]; then
    if [[ "$DRY_RUN" == true ]]; then
      dry "remove $label"
    else
      rm "$target"
      ok "removed $label"
    fi
  else
    warn "$label points to $current (not this repo) — skipping"
  fi
}

# --- Integrity check ---

for cmd in "${COMMANDS[@]}"; do
  local_src="$LIVESPEC_ROOT/commands/$cmd.md"
  if [[ ! -f "$local_src" ]]; then
    echo "ERROR: Missing source file: $local_src" >&2
    echo "Is this script running from the LiveSpec repository?" >&2
    exit 1
  fi
done

for agent in "${AGENTS[@]}"; do
  local_src="$LIVESPEC_ROOT/agents/$agent.md"
  if [[ ! -f "$local_src" ]]; then
    echo "ERROR: Missing source file: $local_src" >&2
    echo "Is this script running from the LiveSpec repository?" >&2
    exit 1
  fi
done

# --- Main ---

if [[ "$UNINSTALL" == true ]]; then
  echo ""
  echo "Uninstalling LiveSpec commands and agents..."
  echo ""
  for cmd in "${COMMANDS[@]}"; do
    remove_link "$COMMANDS_DIR/spec.$cmd.md" "commands/spec.$cmd.md"
  done
  for agent in "${AGENTS[@]}"; do
    remove_link "$AGENTS_DIR/$agent.md" "agents/$agent.md"
  done
  echo ""
  echo "Done."
  exit 0
fi

echo ""
echo "Installing LiveSpec commands and agents..."
echo ""

if [[ "$DRY_RUN" == false ]]; then
  mkdir -p "$COMMANDS_DIR"
  mkdir -p "$AGENTS_DIR"
fi

for cmd in "${COMMANDS[@]}"; do
  create_link "$LIVESPEC_ROOT/commands/$cmd.md" "$COMMANDS_DIR/spec.$cmd.md" "commands/spec.$cmd.md"
done

for agent in "${AGENTS[@]}"; do
  create_link "$LIVESPEC_ROOT/agents/$agent.md" "$AGENTS_DIR/$agent.md" "agents/$agent.md"
done

# --- Verify ---

if [[ "$DRY_RUN" == false ]]; then
  errors=0
  for cmd in "${COMMANDS[@]}"; do
    if [[ ! -L "$COMMANDS_DIR/spec.$cmd.md" ]]; then
      warn "Verification failed: commands/spec.$cmd.md is not a symlink"
      errors=$((errors + 1))
    fi
  done
  for agent in "${AGENTS[@]}"; do
    if [[ ! -L "$AGENTS_DIR/$agent.md" ]]; then
      warn "Verification failed: agents/$agent.md is not a symlink"
      errors=$((errors + 1))
    fi
  done

  if [[ "$errors" -gt 0 ]]; then
    echo "$errors symlink(s) failed verification." >&2
    exit 1
  fi
fi

echo ""
echo "Done! LiveSpec is ready."
echo ""
echo "Next: run /spec.init in your project to set up .specs/ and CLAUDE.md."
echo "Tip: /spec.implement uses multi-agent orchestration by default (--mono for single-agent)."
