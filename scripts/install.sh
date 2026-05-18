#!/usr/bin/env bash
set -euo pipefail

# LiveSpec bootstrap installer for portable Claude/Codex agent assets.
#
# Installs global bootstrap skills and rules through cc-hub. Project-local
# assets are synced later by spec-init via scripts/sync-agent-assets.sh.

LIVESPEC_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

BOOTSTRAP_COMMANDS=(spec-init spec-migrate)
DRY_RUN=false
UNINSTALL=false

print_help() {
  cat <<'EOF'
Usage: bash scripts/install.sh [OPTIONS]

Install the global LiveSpec bootstrap assets through cc-hub:
  spec-init and spec-migrate skills
  livespec routing and commands rules

Options:
  --force         Accepted for compatibility; cc-hub decides replacement safety
  --dry-run       Preview cc-hub calls without writing anything
  --uninstall     Remove bootstrap assets through cc-hub
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
  if [[ ! -f "$LIVESPEC_ROOT/.agent-sync/rules/livespec/routing.md" ]]; then
    log_warn "ERROR: missing source rule: $LIVESPEC_ROOT/.agent-sync/rules/livespec/routing.md"
    exit 1
  fi
  if [[ ! -f "$LIVESPEC_ROOT/.agent-sync/rules/livespec/commands.md" ]]; then
    log_warn "ERROR: missing source rule: $LIVESPEC_ROOT/.agent-sync/rules/livespec/commands.md"
    exit 1
  fi
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
    run_cc_hub skill link "$LIVESPEC_ROOT/.agent-sync/skills/$command_name" \
      --scope global --targets all
  done
}

uninstall_bootstrap_commands() {
  local command_name
  for command_name in "${BOOTSTRAP_COMMANDS[@]}"; do
    run_cc_hub skill unlink "$command_name" --scope global --targets all
  done
}

install_bootstrap_rules() {
  run_cc_hub rule link "$LIVESPEC_ROOT/.agent-sync/rules/livespec/routing.md" \
    --scope global --targets all --namespace livespec -n livespec-routing
  run_cc_hub rule link "$LIVESPEC_ROOT/.agent-sync/rules/livespec/commands.md" \
    --scope global --targets all --namespace livespec -n livespec-commands
  run_cc_hub rule build --scope global --targets all --namespace livespec
}

uninstall_bootstrap_rules() {
  run_cc_hub rule unlink livespec-routing --scope global --targets all
  run_cc_hub rule unlink livespec-commands --scope global --targets all
}

main() {
  parse_args "$@"
  ensure_source_files

  if [[ "$UNINSTALL" == true ]]; then
    printf 'Removing LiveSpec bootstrap skills and rules...\n'
    uninstall_bootstrap_commands
    uninstall_bootstrap_rules
    printf 'Done.\n'
    return
  fi

  printf 'Installing LiveSpec bootstrap skills...\n'
  install_bootstrap_commands
  printf '\nInstalling LiveSpec global routing rules...\n'
  install_bootstrap_rules
  printf '\nInstalled: spec-init, spec-migrate, livespec rules (global)\n'
  printf 'Next: run spec-init inside a project to sync LiveSpec locally.\n'
}

main "$@"
