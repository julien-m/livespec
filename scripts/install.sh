#!/usr/bin/env bash
set -euo pipefail

# LiveSpec bootstrap installer for portable Claude/Codex bootstrap skills.
#
# Installs only the two global bootstrap skills through cc-hub. Project-local
# skills, agents, and rules are synced later by spec-init.

LIVESPEC_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

BOOTSTRAP_COMMANDS=(spec-init spec-migrate)
DRY_RUN=false
FORCE=false
UNINSTALL=false

print_help() {
  cat <<'EOF'
Usage: bash scripts/install.sh [OPTIONS]

Install the global LiveSpec bootstrap skills through cc-hub:
  spec-init and spec-migrate

Options:
  --force         Accepted for compatibility; cc-hub decides replacement safety
  --dry-run       Preview cc-hub calls without writing anything
  --uninstall     Remove bootstrap skills through cc-hub
  --help          Show this help message
EOF
}

log_warn() {
  printf '  %s\n' "$1" >&2
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

ensure_source_files() {
  local command_name
  for command_name in "${BOOTSTRAP_COMMANDS[@]}"; do
    if [[ ! -f "$LIVESPEC_ROOT/.agent-sync/skills/$command_name/SKILL.md" ]]; then
      log_warn "ERROR: missing source skill: $LIVESPEC_ROOT/.agent-sync/skills/$command_name/SKILL.md"
      exit 1
    fi
  done
  if [[ "$DRY_RUN" != true ]] && ! command -v cc-hub >/dev/null 2>&1; then
    log_warn "ERROR: cc-hub is required to install LiveSpec agent assets"
    exit 1
  fi
}

run_cc_hub() {
  if [[ "$DRY_RUN" == true ]]; then
    printf '  [dry-run] cc-hub'
    local arg
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
    return
  fi
  cc-hub "$@"
}

install_bootstrap_commands() {
  local command_name
  for command_name in "${BOOTSTRAP_COMMANDS[@]}"; do
    if [[ "$FORCE" == true ]]; then
      run_cc_hub skill link "$LIVESPEC_ROOT/.agent-sync/skills/$command_name" \
        --scope global --targets all --force
    else
      run_cc_hub skill link "$LIVESPEC_ROOT/.agent-sync/skills/$command_name" \
        --scope global --targets all
    fi
  done
}

uninstall_bootstrap_commands() {
  local command_name
  for command_name in "${BOOTSTRAP_COMMANDS[@]}"; do
    run_cc_hub skill unlink "$command_name" --scope global --targets all
  done
}

main() {
  parse_args "$@"
  ensure_source_files

  if [[ "$UNINSTALL" == true ]]; then
    printf 'Removing LiveSpec bootstrap skills...\n'
    uninstall_bootstrap_commands
    printf 'Done.\n'
    return
  fi

  printf 'Installing LiveSpec bootstrap skills...\n'
  install_bootstrap_commands
  printf '\nInstalled: spec-init and spec-migrate (global)\n'
  printf 'Next: run spec-init inside a project to sync LiveSpec locally.\n'
}

main "$@"
