#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

# Sync LiveSpec agent-sync assets into a project and let cc-hub materialize
# provider-native Claude/Codex outputs.
#
# Usage: sync-agent-assets.sh <project-dir> <livespec-dir> [--scope project|global|all]
#        [--targets claude|codex|all] [--dry-run] [--force]

PROJECT_DIR="${1:?Usage: sync-agent-assets.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: sync-agent-assets.sh <project-dir> <livespec-dir>}"
shift 2

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd -P)"
LIVESPEC_DIR="$(cd "$LIVESPEC_DIR" && pwd -P)"
SOURCE_ROOT="$LIVESPEC_DIR/.agent-sync"
LOCAL_ROOT="$PROJECT_DIR/.agent-sync.local"

SCOPE="project"
TARGETS="all"
DRY_RUN=false
FORCE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scope)
      SCOPE="${2:?--scope requires a value}"
      shift 2
      ;;
    --targets)
      TARGETS="${2:?--targets requires a value}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      exit 2
      ;;
  esac
done

if [[ ! -d "$SOURCE_ROOT" ]]; then
  echo "ERROR: missing LiveSpec agent-sync source: $SOURCE_ROOT" >&2
  exit 1
fi

if [[ "$DRY_RUN" != true ]] && ! command -v cc-hub >/dev/null 2>&1; then
  echo "ERROR: cc-hub is required to sync LiveSpec agent assets" >&2
  exit 1
fi

run_cc_hub() {
  if [[ "$DRY_RUN" == true ]]; then
    printf 'cc-hub %q' "$1"
    shift
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
    return
  fi
  (cd "$PROJECT_DIR" && cc-hub "$@")
}

project_source() {
  local src="$1"
  local dest="$2"
  local label="$3"

  if [[ "$DRY_RUN" == true ]]; then
    printf 'project %s -> %s\n' "$label" "$src"
    return
  fi

  mkdir -p "$(dirname "$dest")"
  if [[ -L "$dest" ]]; then
    local current
    current="$(readlink "$dest")"
    if [[ "$current" == "$src" ]]; then
      return
    fi
    if [[ "$FORCE" != true ]]; then
      echo "WARN: $label already links to $current; use --force to replace" >&2
      return
    fi
    rm -f "$dest"
  elif [[ -e "$dest" ]]; then
    echo "WARN: $label exists as a regular file; leaving project-local asset in place" >&2
    return
  fi
  ln -s "$src" "$dest"
}

project_shared_sources() {
  local skill
  for skill in "$SOURCE_ROOT"/skills/spec-*; do
    [[ -d "$skill" ]] || continue
    project_source "$skill" "$LOCAL_ROOT/skills/$(basename "$skill")" "skill $(basename "$skill")"
  done

  local agent
  for agent in "$SOURCE_ROOT"/agents/livespec-*; do
    [[ -d "$agent" ]] || continue
    project_source "$agent" "$LOCAL_ROOT/agents/$(basename "$agent")" "agent $(basename "$agent")"
  done

  local rule
  for rule in "$SOURCE_ROOT"/rules/livespec/*.md; do
    [[ -f "$rule" ]] || continue
    project_source "$rule" "$LOCAL_ROOT/rules/$(basename "$rule")" "rule $(basename "$rule")"
  done
}

sync_skills() {
  local root="$1"
  local skill
  for skill in "$root"/skills/spec-*; do
    [[ -d "$skill" ]] || continue
    run_cc_hub skill link "$skill" --scope "$SCOPE" --targets "$TARGETS" --agent-sync-root .agent-sync.local
  done
}

sync_agents() {
  local root="$1"
  local agent
  for agent in "$root"/agents/livespec-*; do
    [[ -d "$agent" ]] || continue
    local name
    name="$(basename "$agent")"
    run_cc_hub agent build "$name" --scope "$SCOPE" --targets "$TARGETS" --agent-sync-root .agent-sync.local
    run_cc_hub agent link "$name" --scope "$SCOPE" --targets "$TARGETS" --agent-sync-root .agent-sync.local
  done
}

sync_rules() {
  local root="$1"
  local rule
  local has_rules=false
  for rule in "$root"/rules/*.md "$root"/rules/livespec/*.md; do
    [[ -f "$rule" ]] || continue
    has_rules=true
    break
  done
  if [[ "$has_rules" == true ]]; then
    run_cc_hub rule build --scope "$SCOPE" --targets "$TARGETS" --namespace livespec --agent-sync-root .agent-sync.local
  fi
}

project_shared_sources
sync_skills "$LOCAL_ROOT"
sync_agents "$LOCAL_ROOT"
sync_rules "$LOCAL_ROOT"

echo "LiveSpec agent-sync assets synced through cc-hub"
