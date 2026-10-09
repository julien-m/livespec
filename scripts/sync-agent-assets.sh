#!/usr/bin/env bash
# LiveSpec traceability anchors
# @spec(FR-005)
# @spec FR-003: Isolate mutable agents — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-003

set -euo pipefail
shopt -s nullglob

# Sync LiveSpec agent-sync assets into a project and let cc-hub materialize
# provider-native Claude/Codex outputs.
#
# Usage: sync-agent-assets.sh <project-dir> <livespec-dir> [--scope project|global|all]
#        [--targets claude|codex|all] [--dry-run] [--force]
#        [--check-paths-only] (read-only installer preflight)

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
CHECK_PATHS_ONLY=false

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
    --check-paths-only)
      CHECK_PATHS_ONLY=true
      shift
      ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      exit 2
      ;;
  esac
done

case "$SCOPE" in project|global|all) ;; *) echo "ERROR: invalid scope: $SCOPE" >&2; exit 2 ;; esac
case "$TARGETS" in claude|codex|all) ;; *) echo "ERROR: invalid targets: $TARGETS" >&2; exit 2 ;; esac

if [[ ! -d "$SOURCE_ROOT" ]]; then
  echo "ERROR: missing LiveSpec agent-sync source: $SOURCE_ROOT" >&2
  exit 1
fi

# Validate provider ancestors and mutable destinations before projection or build.
# Legacy mutable-agent links are unlinked later; immutable skill/rule links are read-only.
check_local_paths() {
  python3 - "$PROJECT_DIR" "$SOURCE_ROOT" <<'PY'
import os
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
shared = Path(sys.argv[2])

def is_legacy_provider_link(path):
    relative = path.relative_to(root)
    if len(relative.parts) != 3 or relative.parts[1] != "agents" or not path.is_symlink():
        return False
    provider, _, filename = relative.parts
    extension, dist = {".claude": (".md", "claude.md"), ".codex": (".toml", "codex.toml")}.get(provider, ("", ""))
    if not extension or not filename.startswith("livespec-") or not filename.endswith(extension):
        return False
    name = filename[:-len(extension)]
    linked = Path(os.path.abspath(path.parent / os.readlink(path)))
    return linked in (
        root / ".agent-sync.local/agents" / name / "dist" / dist,
        root / ".agent-sync/agents" / name / "dist" / dist,
        shared / "agents" / name / "dist" / dist,
    )

def check(path):
    if not path.resolve().is_relative_to(root):
        raise SystemExit(f"ERROR: escaping writable path: {path}")
    # Internal redirects can target canonical sources just as external links can.
    # Only explicit legacy links detached before mutation bypass this check.
    if path.is_symlink():
        raise SystemExit(f"ERROR: writable path symlink is unsupported: {path}")

def check_ancestors(path):
    for parent in reversed((path, *path.parents)):
        if parent == root or root in parent.parents:
            check(parent)

def check_assets(path, mutable_root=False):
    if mutable_root and path.is_symlink():
        return  # Only unlink this legacy root, never traverse its shared target.
    if is_legacy_provider_link(path):
        return  # Exact old LiveSpec outputs are detached after copying agents.
    check(path)
    if not path.is_dir():
        return
    for child in path.iterdir():
        if mutable_root and child.name.startswith("livespec-") and child.is_symlink():
            continue  # A legacy agent link is detached before any build.
        check_assets(child)

for relative in (".agent-sync.local", ".agent-sync.local/skills", ".agent-sync.local/rules"):
    check_ancestors(root / relative)
check_assets(root / ".agent-sync.local/agents", mutable_root=True)
for provider in (".agents", ".claude", ".codex"):
    base = root / provider
    check(base)
    if base.is_dir():
        for child in base.iterdir():
            if child.name in ("skills", "rules", "commands"):
                check(child)  # Legacy commands and skill/rule files are read-only links.
            else:
                check_assets(child)
for relative in (
    "AGENTS.md", "CLAUDE.md", ".gitignore", ".conventions/index.md",
    ".conventions/manifest.yaml", ".specs/spec-system.md", ".specs/constitution.md",
    ".specs/project.md", ".specs/changelog.md", ".specs/stacks/_default.md",
    ".specs/stacks/decisions", ".specs/testing/strategy.md", ".specs/hooks",
    ".specs/features",
):
    check_ancestors(root / relative)
PY
}

check_local_paths
[[ "$CHECK_PATHS_ONLY" != true ]] || exit 0

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
  check_local_paths
  # Build/link receives explicit argv in the installer process group; its caller
  # owns the total deadline and cancels this group, including cc-hub descendants.
  (cd "$PROJECT_DIR" && cc-hub "$@")
}

project_mutable_agent() {
  local src="$1"
  local dest="$2"
  if [[ "$DRY_RUN" == true ]]; then
    printf 'copy mutable agent %s -> %s\n' "$src" "$dest"
    return
  fi
  # Unlink before mkdir/copy: writing through a legacy directory link changes
  # the shared checkout. Existing real local agents retain their custom content.
  [[ ! -L "$dest" ]] || rm -f "$dest"
  if [[ -e "$dest" ]]; then
    [[ -d "$dest" ]] || { echo "ERROR: agent destination is not a directory: $dest" >&2; exit 1; }
    return
  fi
  mkdir -p "$dest"
  # Dereference source links while copying so build cannot mutate a shared asset.
  cp -RL "$src/." "$dest/"
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
  for skill in "$SOURCE_ROOT"/skills/spec-* "$SOURCE_ROOT"/skills/source-command-cli; do
    [[ -d "$skill" ]] || continue
    project_source "$skill" "$LOCAL_ROOT/skills/$(basename "$skill")" "skill $(basename "$skill")"
  done

  local agent
  if [[ "$DRY_RUN" != true && -L "$LOCAL_ROOT/agents" ]]; then
    rm -f "$LOCAL_ROOT/agents"
  fi
  for agent in "$SOURCE_ROOT"/agents/livespec-*; do
    [[ -d "$agent" ]] || continue
    project_mutable_agent "$agent" "$LOCAL_ROOT/agents/$(basename "$agent")"
  done

  local rule
  for rule in "$SOURCE_ROOT"/rules/livespec/*.md; do
    [[ -f "$rule" ]] || continue
    project_source "$rule" "$LOCAL_ROOT/rules/$(basename "$rule")" "rule $(basename "$rule")"
  done

  if [[ "$DRY_RUN" != true ]]; then
    # Provider links can still resolve through the old shared agent directory.
    # Unlink only the known LiveSpec outputs; custom files remain untouched.
    for agent in "$SOURCE_ROOT"/agents/livespec-*; do
      [[ -d "$agent" ]] || continue
      local name
      name="$(basename "$agent")"
      local output
      for output in "$PROJECT_DIR/.claude/agents/$name.md" "$PROJECT_DIR/.codex/agents/$name.toml"; do
        [[ ! -L "$output" ]] || rm -f "$output"
      done
    done
  fi
}

sync_skills() {
  local root="$1"
  local skill
  for skill in "$root"/skills/spec-* "$root"/skills/source-command-cli; do
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
