#!/usr/bin/env bash
set -euo pipefail

# LiveSpec bootstrap installer for Claude Code.
#
# Installs the two global bootstrap commands that must exist before a project
# can link the rest of the LiveSpec commands locally via /spec.init.

LIVESPEC_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMMANDS_DIR="$HOME/.claude/commands"
RULES_DIR="$HOME/.claude/rules"

BOOTSTRAP_COMMANDS=(init migrate)
# Global rules — loaded by Claude on any project. The routing rule only
# triggers when `.specs/` is detected in the cwd, so it is safe globally.
# The commands reference is required alongside it (relative link target).
BOOTSTRAP_RULES=(livespec-routing livespec-commands)

FORCE=false
DRY_RUN=false
UNINSTALL=false

print_help() {
  cat <<'EOF'
Usage: bash scripts/install.sh [OPTIONS]

Install the global bootstrap commands and routing rule required by LiveSpec:
  /spec.init
  /spec.migrate
  .claude/rules/livespec-routing.md  (global rule, triggers on `.specs/`)
  .claude/rules/livespec-commands.md (referenced by routing rule)

All other /spec.* commands and agents are linked per project by /spec.init.

Options:
  --force         Overwrite existing symlinks
  --dry-run       Preview changes without writing anything
  --uninstall     Remove bootstrap symlinks
  --help          Show this help message
EOF
}

log_ok() {
  printf '  %s\n' "$1"
}

log_warn() {
  printf '  %s\n' "$1" >&2
}

log_dry_run() {
  printf '  [dry-run] %s\n' "$1"
}

ensure_source_files() {
  local command_name=""
  for command_name in "${BOOTSTRAP_COMMANDS[@]}"; do
    if [[ ! -f "$LIVESPEC_ROOT/commands/$command_name.md" ]]; then
      log_warn "ERROR: missing source file: $LIVESPEC_ROOT/commands/$command_name.md"
      exit 1
    fi
  done
  local rule_name=""
  for rule_name in "${BOOTSTRAP_RULES[@]}"; do
    if [[ ! -f "$LIVESPEC_ROOT/.claude/rules/$rule_name.md" ]]; then
      log_warn "ERROR: missing source file: $LIVESPEC_ROOT/.claude/rules/$rule_name.md"
      exit 1
    fi
  done
}

create_symlink() {
  local source_path="$1"
  local target_path="$2"
  local label="$3"

  if [[ "$DRY_RUN" == true ]]; then
    log_dry_run "$label -> $source_path"
    return
  fi

  if [[ -L "$target_path" ]]; then
    local current_target=""
    current_target="$(readlink "$target_path")"
    if [[ "$current_target" == "$source_path" ]]; then
      log_ok "$label already up to date"
      return
    fi
    if [[ "$FORCE" != true ]]; then
      log_warn "$label exists and points to $current_target (use --force to overwrite)"
      return
    fi
    rm -f "$target_path"
  elif [[ -e "$target_path" ]]; then
    if [[ "$FORCE" != true ]]; then
      log_warn "$label exists as a regular file (use --force to overwrite)"
      return
    fi
    rm -f "$target_path"
  fi

  ln -s "$source_path" "$target_path"
  log_ok "linked $label"
}

remove_symlink() {
  local target_path="$1"
  local label="$2"

  if [[ ! -L "$target_path" ]]; then
    if [[ -e "$target_path" ]]; then
      log_warn "$label is not a symlink; leaving it in place"
    fi
    return
  fi

  if [[ "$DRY_RUN" == true ]]; then
    log_dry_run "remove $label"
    return
  fi

  rm -f "$target_path"
  log_ok "removed $label"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --force)
        FORCE=true
        shift
        ;;
      --dry-run)
        DRY_RUN=true
        shift
        ;;
      --uninstall)
        UNINSTALL=true
        shift
        ;;
      --help|-h)
        print_help
        exit 0
        ;;
      *)
        log_warn "Unknown option: $1"
        log_warn "Run with --help for usage."
        exit 1
        ;;
    esac
  done
}

install_bootstrap_commands() {
  local command_name=""

  if [[ "$DRY_RUN" != true ]]; then
    mkdir -p "$COMMANDS_DIR"
  fi

  for command_name in "${BOOTSTRAP_COMMANDS[@]}"; do
    create_symlink \
      "$LIVESPEC_ROOT/commands/$command_name.md" \
      "$COMMANDS_DIR/spec.$command_name.md" \
      "commands/spec.$command_name.md"
  done
}

uninstall_bootstrap_commands() {
  local command_name=""
  for command_name in "${BOOTSTRAP_COMMANDS[@]}"; do
    remove_symlink "$COMMANDS_DIR/spec.$command_name.md" "commands/spec.$command_name.md"
  done
}

install_bootstrap_rules() {
  local rule_name=""

  if [[ "$DRY_RUN" != true ]]; then
    mkdir -p "$RULES_DIR"
  fi

  for rule_name in "${BOOTSTRAP_RULES[@]}"; do
    create_symlink \
      "$LIVESPEC_ROOT/.claude/rules/$rule_name.md" \
      "$RULES_DIR/$rule_name.md" \
      "rules/$rule_name.md"
  done
}

uninstall_bootstrap_rules() {
  local rule_name=""
  for rule_name in "${BOOTSTRAP_RULES[@]}"; do
    remove_symlink "$RULES_DIR/$rule_name.md" "rules/$rule_name.md"
  done
}

main() {
  parse_args "$@"
  ensure_source_files

  if [[ "$UNINSTALL" == true ]]; then
    printf 'Removing LiveSpec bootstrap commands and rules...\n'
    uninstall_bootstrap_commands
    uninstall_bootstrap_rules
    printf 'Done.\n'
    return
  fi

  printf 'Installing LiveSpec bootstrap commands...\n'
  install_bootstrap_commands
  printf '\n'
  printf 'Installing LiveSpec global routing rule...\n'
  install_bootstrap_rules
  printf '\n'
  printf 'Installed: /spec.init, /spec.migrate, livespec-routing rule (global)\n'
  printf 'Next: run /spec.init inside a project to link the rest of LiveSpec locally.\n'
}

main "$@"
