#!/usr/bin/env bash
# LiveSpec init script
# Installs the LiveSpec spec system in a project directory
#
# Usage:
#   bash init.sh              # Install in current directory
#   bash init.sh /path/to/project  # Install in specified directory
#   bash init.sh --help       # Show help

set -euo pipefail

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

# ─── Helpers ──────────────────────────────────────────────────────────────────
info()    { echo -e "${BLUE}ℹ${RESET}  $*"; }
success() { echo -e "${GREEN}✅${RESET} $*"; }
warn()    { echo -e "${YELLOW}⚠️${RESET}  $*"; }
error()   { echo -e "${RED}❌${RESET} $*" >&2; exit 1; }
header()  { echo -e "\n${BOLD}$*${RESET}"; }

# ─── Script location ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIVESPEC_ROOT="$(dirname "$SCRIPT_DIR")"

# ─── Help ─────────────────────────────────────────────────────────────────────
show_help() {
  cat <<EOF
${BOLD}LiveSpec Init${RESET} — Install the LiveSpec spec system in your project

${BOLD}Usage:${RESET}
  bash init.sh [PROJECT_DIR]

${BOLD}Arguments:${RESET}
  PROJECT_DIR   Directory to install LiveSpec into (default: current directory)

${BOLD}Options:${RESET}
  --help        Show this help message
  --dry-run     Show what would be created without creating files

${BOLD}Examples:${RESET}
  bash init.sh                    # Install in current directory
  bash init.sh /path/to/project   # Install in specified directory
  bash init.sh --dry-run          # Preview only

${BOLD}What it creates:${RESET}
  .specs/
  ├── spec-system.md          ← Universal spec rules (READ FIRST)
  ├── constitution.md         ← Architecture principles template
  ├── project.md              ← Project profile template
  ├── changelog.md            ← Global changelog
  ├── stacks/
  │   ├── _default.md         ← Stack placeholder (fill with /spec.init or manually)
  │   └── decisions/          ← Architecture Decision Records
  ├── testing/
  │   └── strategy.md         ← Testing strategy template
  └── features/               ← Empty, ready for /spec.specify
EOF
  exit 0
}

# ─── Parse arguments ──────────────────────────────────────────────────────────
DRY_RUN=false
PROJECT_DIR="."

for arg in "$@"; do
  case "$arg" in
    --help|-h) show_help ;;
    --dry-run) DRY_RUN=true ;;
    -*) error "Unknown option: $arg. Use --help for usage." ;;
    *)  PROJECT_DIR="$arg" ;;
  esac
done

# Resolve project directory to absolute path
PROJECT_DIR="$(cd "$PROJECT_DIR" 2>/dev/null && pwd)" || error "Directory not found: $PROJECT_DIR"

# ─── Check prerequisites ──────────────────────────────────────────────────────
check_prerequisites() {
  if [[ ! -f "$LIVESPEC_ROOT/system/spec-system.md" ]]; then
    error "LiveSpec source files not found at: $LIVESPEC_ROOT
Please run this script from the livespec repository, or pass the correct path."
  fi
}

# ─── Create file (respects --dry-run) ─────────────────────────────────────────
create_file() {
  local dest="$1"
  local source="$2"

  if [[ "$DRY_RUN" == true ]]; then
    echo -e "  ${YELLOW}[dry-run]${RESET} Would create: $dest"
    return
  fi

  local dir
  dir="$(dirname "$dest")"
  mkdir -p "$dir"

  if [[ -f "$source" ]]; then
    cp "$source" "$dest"
  else
    error "Source file not found: $source"
  fi

  success "Created: ${dest#"$PROJECT_DIR/"}"
}

# ─── Create directory (respects --dry-run) ────────────────────────────────────
create_dir() {
  local dir="$1"

  if [[ "$DRY_RUN" == true ]]; then
    echo -e "  ${YELLOW}[dry-run]${RESET} Would create dir: $dir"
    return
  fi

  mkdir -p "$dir"
  success "Created dir: ${dir#"$PROJECT_DIR/"}"
}

# ─── Write inline content to file (respects --dry-run) ────────────────────────
write_file() {
  local dest="$1"
  local content="$2"

  if [[ "$DRY_RUN" == true ]]; then
    echo -e "  ${YELLOW}[dry-run]${RESET} Would create: $dest"
    return
  fi

  local dir
  dir="$(dirname "$dest")"
  mkdir -p "$dir"
  printf '%s\n' "$content" > "$dest"
  success "Created: ${dest#"$PROJECT_DIR/"}"
}

# ─── Main ─────────────────────────────────────────────────────────────────────
main() {
  header "🔥 LiveSpec Init"
  echo -e "  Installing LiveSpec in: ${BOLD}$PROJECT_DIR${RESET}"

  if [[ "$DRY_RUN" == true ]]; then
    warn "Dry run mode — no files will be created"
  fi

  check_prerequisites

  # Check if .specs already exists
  if [[ -d "$PROJECT_DIR/.specs" ]]; then
    warn ".specs/ directory already exists in $PROJECT_DIR"
    echo -n "  Continue and overwrite spec-system.md? (existing features will NOT be affected) [y/N]: "
    read -r confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
      echo "  Aborted."
      exit 0
    fi
  fi

  header "Creating .specs/ structure..."

  # Core files
  create_file "$PROJECT_DIR/.specs/spec-system.md" \
    "$LIVESPEC_ROOT/system/spec-system.md"

  create_file "$PROJECT_DIR/.specs/constitution.md" \
    "$LIVESPEC_ROOT/system/constitution-template.md"

  create_file "$PROJECT_DIR/.specs/project.md" \
    "$LIVESPEC_ROOT/system/templates/project-template.md"

  # Global changelog
  local project_name
  project_name="$(basename "$PROJECT_DIR")"
  write_file "$PROJECT_DIR/.specs/changelog.md" \
"# Global Changelog — ${project_name}

> Project-level changelog. Add a summary entry here when features are shipped.
> Per-feature changelogs are in \`.specs/features/NNN-feature-name/changelog.md\`.

---

## $(date +%Y-%m-%d) — LiveSpec initialized

- **Type:** Setup
- **Description:** LiveSpec spec system installed
- **Author:** init.sh
"

  # Stacks directory
  create_dir "$PROJECT_DIR/.specs/stacks/decisions"
  write_file "$PROJECT_DIR/.specs/stacks/_default.md" \
"# Default Stack — ${project_name}

> This file is generated by \`/spec.init\` Phase B (Stack Decisions).
> Run \`/spec.init\` in your AI tool to fill this in through a guided conversation.
> Or fill it in manually based on your chosen stack.

## Stack (to be filled in)

| Layer | Choice | Reason |
|---|---|---|
| Framework | [TBD] | [Run /spec.init to decide] |
| Deploy | [TBD] | |
| Database | [TBD] | |
| Auth | [TBD] | |
| Testing | [TBD] | |

## Stack Presets

See the available presets for guidance:
- \`livespec/stacks/presets/web-realtime.md\`
- \`livespec/stacks/presets/web-static.md\`
- \`livespec/stacks/presets/api-rest.md\`
"

  # Testing directory
  create_file "$PROJECT_DIR/.specs/testing/strategy.md" \
    "$LIVESPEC_ROOT/system/templates/testing-strategy-template.md"

  # Features directory (empty)
  create_dir "$PROJECT_DIR/.specs/features"

  # Summary
  header "✅ LiveSpec installed successfully!"
  echo ""
  echo -e "  ${BOLD}Project:${RESET} $project_name"
  echo -e "  ${BOLD}Location:${RESET} $PROJECT_DIR/.specs/"
  echo ""
  echo -e "  ${BOLD}Next steps:${RESET}"
  echo ""
  echo -e "  1. ${YELLOW}Fill in your stack:${RESET}"
  echo -e "     Run ${BOLD}/spec.init${RESET} in your AI tool for guided setup"
  echo -e "     OR edit ${BOLD}.specs/stacks/_default.md${RESET} manually"
  echo ""
  echo -e "  2. ${YELLOW}Edit your constitution:${RESET}"
  echo -e "     ${BOLD}.specs/constitution.md${RESET} — add your project's principles"
  echo ""
  echo -e "  3. ${YELLOW}Create your first feature spec:${RESET}"
  echo -e "     ${BOLD}/spec.specify \"User can [action]\"${RESET}"
  echo ""
  echo -e "  ${BLUE}Documentation:${RESET} https://github.com/julien-m/livespec"
}

main "$@"
