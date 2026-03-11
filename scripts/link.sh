#!/usr/bin/env bash
# LiveSpec link script
# Installs AI tool adapters and copies command docs into .specs/commands/
#
# Usage:
#   bash link.sh                                     # Auto-detect tools, install all found
#   bash link.sh --tool copilot                      # Install only Copilot adapter
#   bash link.sh --tool claude-code                  # Install only Claude Code adapter
#   bash link.sh --tool cursor                       # Install only Cursor adapter
#   bash link.sh --tool all                          # Install all adapters
#   bash link.sh --tool all --force                  # Overwrite existing files
#   bash link.sh --tool claude-code --global         # Install Claude Code globally
#   bash link.sh --symlink                           # Use symlinks instead of copies
#   bash link.sh --livespec-dir /path/to/livespec    # Specify LiveSpec source directory

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
skipped() { echo -e "${YELLOW}–${RESET}  $* ${YELLOW}(skipped — use --force to overwrite)${RESET}"; }

# ─── Script location ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIVESPEC_ROOT_DEFAULT="$(dirname "$SCRIPT_DIR")"

# ─── Help ─────────────────────────────────────────────────────────────────────
show_help() {
  cat <<EOF
${BOLD}LiveSpec Link${RESET} — Install AI tool adapters and make commands discoverable

${BOLD}Usage:${RESET}
  bash link.sh [OPTIONS]

${BOLD}Options:${RESET}
  --tool <tool>           Tool to link: copilot | claude-code | cursor | all
                          (default: auto-detect from project files)
  --symlink               Use symlinks instead of file copies
  --global                For Claude Code: install to ~/.claude/skills/livespec.md
  --force                 Overwrite existing adapter files without prompting
  --dry-run               Show what would be created without writing files
  --livespec-dir <path>   Path to LiveSpec repository (default: auto-detected)
  --help                  Show this help message

${BOLD}Examples:${RESET}
  bash link.sh                            # Auto-detect and link all found tools
  bash link.sh --tool copilot             # Link only GitHub Copilot
  bash link.sh --tool all --force         # Link all tools, overwrite existing
  bash link.sh --tool claude-code --global  # Install Claude Code skill globally
  bash link.sh --symlink                  # Use symlinks (stays in sync)

${BOLD}What it creates:${RESET}
  .specs/commands/                  ← Command docs (readable by the AI tool)
  .github/copilot-instructions.md   ← Copilot adapter
  CLAUDE.md                         ← Claude Code adapter (project-level)
  ~/.claude/skills/livespec.md      ← Claude Code adapter (with --global)
  .cursorrules                      ← Cursor adapter
EOF
  exit 0
}

# ─── Parse arguments ──────────────────────────────────────────────────────────
TOOL=""
USE_SYMLINK=false
GLOBAL=false
FORCE=false
DRY_RUN=false
LIVESPEC_ROOT="$LIVESPEC_ROOT_DEFAULT"
PROJECT_DIR="."

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)        show_help ;;
    --tool)           TOOL="${2:-}"; shift 2 ;;
    --symlink)        USE_SYMLINK=true; shift ;;
    --global)         GLOBAL=true; shift ;;
    --force)          FORCE=true; shift ;;
    --dry-run)        DRY_RUN=true; shift ;;
    --livespec-dir)   LIVESPEC_ROOT="${2:-}"; shift 2 ;;
    -*) error "Unknown option: $1. Use --help for usage." ;;
    *)  PROJECT_DIR="$1"; shift ;;
  esac
done

# Resolve directories to absolute paths
PROJECT_DIR="$(cd "$PROJECT_DIR" 2>/dev/null && pwd)" || error "Directory not found: $PROJECT_DIR"
LIVESPEC_ROOT="$(cd "$LIVESPEC_ROOT" 2>/dev/null && pwd)" || error "LiveSpec directory not found: $LIVESPEC_ROOT"

# ─── Check prerequisites ──────────────────────────────────────────────────────
check_prerequisites() {
  if [[ ! -f "$LIVESPEC_ROOT/system/spec-system.md" ]]; then
    error "LiveSpec source files not found at: $LIVESPEC_ROOT
Please run this script from the livespec repository, or pass --livespec-dir /path/to/livespec"
  fi
  if [[ ! -d "$PROJECT_DIR/.specs" ]]; then
    warn ".specs/ directory not found in $PROJECT_DIR"
    info "Run 'bash init.sh' first to initialize LiveSpec, or run from your project directory."
  fi
}

# ─── Auto-detect tools ────────────────────────────────────────────────────────
detect_tools() {
  local detected=()

  [[ -d "$PROJECT_DIR/.github" ]] && detected+=("copilot")
  [[ -f "$PROJECT_DIR/CLAUDE.md" ]] && detected+=("claude-code")
  [[ -f "$PROJECT_DIR/.cursorrules" ]] && detected+=("cursor")

  if [[ ${#detected[@]} -eq 0 ]]; then
    warn "No AI tool config files detected (.github/, CLAUDE.md, .cursorrules)"
    info "Defaulting to 'all'. Use --tool <tool> to specify."
    echo "all"
  else
    echo "${detected[*]}"
  fi
}

# ─── Install a file (copy or symlink, respecting --dry-run and --force) ───────
install_file() {
  local src="$1"
  local dest="$2"
  local label="${3:-$dest}"

  if [[ ! -f "$src" ]]; then
    warn "Source not found, skipping: $src"
    return
  fi

  if [[ -e "$dest" ]] && [[ "$FORCE" == false ]]; then
    skipped "$label"
    return
  fi

  if [[ "$DRY_RUN" == true ]]; then
    echo -e "  ${YELLOW}[dry-run]${RESET} Would create: $label"
    return
  fi

  local dir
  dir="$(dirname "$dest")"
  mkdir -p "$dir"

  if [[ "$USE_SYMLINK" == true ]]; then
    ln -sf "$src" "$dest"
    success "$label → symlink to ${src#"$LIVESPEC_ROOT/"}"
  else
    cp "$src" "$dest"
    success "$label"
  fi
}

# ─── Create symlink (respecting --dry-run and --force) ────────────────────────
install_symlink() {
  local src="$1"
  local dest="$2"
  local label="${3:-$dest}"

  if [[ ! -f "$src" ]]; then
    warn "Source not found, skipping: $src"
    return
  fi

  if [[ -e "$dest" ]] && [[ "$FORCE" == false ]]; then
    skipped "$label"
    return
  fi

  if [[ "$DRY_RUN" == true ]]; then
    echo -e "  ${YELLOW}[dry-run]${RESET} Would create symlink: $label → $src"
    return
  fi

  local dir
  dir="$(dirname "$dest")"
  mkdir -p "$dir"
  ln -sf "$src" "$dest"
  success "$label → symlink to $src"
}

# ─── Write file with header (respecting --dry-run and --force) ────────────────
install_with_header() {
  local src="$1"
  local dest="$2"
  local header_text="$3"
  local label="${4:-$dest}"

  if [[ ! -f "$src" ]]; then
    warn "Source not found, skipping: $src"
    return
  fi

  if [[ -e "$dest" ]] && [[ "$FORCE" == false ]]; then
    skipped "$label"
    return
  fi

  if [[ "$DRY_RUN" == true ]]; then
    echo -e "  ${YELLOW}[dry-run]${RESET} Would create: $label"
    return
  fi

  local dir
  dir="$(dirname "$dest")"
  mkdir -p "$dir"

  {
    printf '%s\n\n' "$header_text"
    cat "$src"
  } > "$dest"
  success "$label"
}

# ─── Append to file with section marker (idempotent) ─────────────────────────
append_with_marker() {
  local src="$1"
  local dest="$2"
  local marker="$3"
  local label="${4:-$dest}"
  local section_start_marker="<!-- LiveSpec section start -->"
  local section_end_marker="# LiveSpec Rules — END"

  if [[ ! -f "$src" ]]; then
    warn "Source not found, skipping: $src"
    return
  fi

  if [[ "$DRY_RUN" == true ]]; then
    if [[ -f "$dest" ]]; then
      echo -e "  ${YELLOW}[dry-run]${RESET} Would append LiveSpec section to: $label"
    else
      echo -e "  ${YELLOW}[dry-run]${RESET} Would create: $label"
    fi
    return
  fi

  local dir
  dir="$(dirname "$dest")"
  mkdir -p "$dir"

  if [[ ! -f "$dest" ]]; then
    cp "$src" "$dest"
    success "$label (created)"
    return
  fi

  # Check if LiveSpec section already present
  if grep -qF "$section_start_marker" "$dest"; then
    if [[ "$FORCE" == true ]]; then
      # Strip everything from section_start_marker to section_end_marker (inclusive),
      # then re-append — using awk which is universally available on POSIX systems
      local tmp_file
      tmp_file="$(mktemp)"
      awk -v start="$section_start_marker" -v end="$section_end_marker" '
        BEGIN { in_section=0; found=0 }
        index($0, start) > 0 { in_section=1; found=1; next }
        in_section && index($0, end) > 0 { in_section=0; next }
        !in_section { print }
      ' "$dest" | sed -e 's/[[:space:]]*$//' > "$tmp_file"
      # Remove trailing blank lines before re-appending
      {
        cat "$tmp_file"
        printf '\n\n---\n%s\n' "$section_start_marker"
        cat "$src"
        printf '\n%s\n' "$section_end_marker"
      } > "$dest"
      rm -f "$tmp_file"
      success "$label (LiveSpec section updated)"
    else
      skipped "$label (LiveSpec section already present)"
    fi
  else
    # Append LiveSpec section for the first time
    {
      printf '\n\n---\n%s\n' "$section_start_marker"
      cat "$src"
      printf '\n%s\n' "$section_end_marker"
    } >> "$dest"
    warn "$label — LiveSpec section appended"
  fi
}

# ─── Copy command files ───────────────────────────────────────────────────────
copy_commands() {
  header "Copying command files to .specs/commands/..."

  local commands_src="$LIVESPEC_ROOT/commands"
  local commands_dest="$PROJECT_DIR/.specs/commands"

  if [[ "$DRY_RUN" == false ]]; then
    mkdir -p "$commands_dest"
  fi

  local cmd_files=(
    "init.md"
    "specify.md"
    "plan.md"
    "implement.md"
    "check.md"
    "explain.md"
    "stack.md"
    "link.md"
  )

  for cmd in "${cmd_files[@]}"; do
    install_file \
      "$commands_src/$cmd" \
      "$commands_dest/$cmd" \
      ".specs/commands/$cmd"
  done
}

# ─── Link Copilot ─────────────────────────────────────────────────────────────
link_copilot() {
  header "Linking GitHub Copilot adapter..."

  local src="$LIVESPEC_ROOT/adapters/copilot/agent.md"
  local dest="$PROJECT_DIR/.github/copilot-instructions.md"
  local header_text="<!-- Generated by LiveSpec /spec.link copilot -->
<!-- To update: run /spec.link copilot --force or bash scripts/link.sh --tool copilot --force -->
<!-- Source: adapters/copilot/agent.md -->"

  install_with_header "$src" "$dest" "$header_text" ".github/copilot-instructions.md"
}

# ─── Link Claude Code ─────────────────────────────────────────────────────────
link_claude_code() {
  header "Linking Claude Code adapter..."

  local src="$LIVESPEC_ROOT/adapters/claude-code/SKILL.md"

  if [[ "$GLOBAL" == true ]]; then
    local dest="$HOME/.claude/skills/livespec.md"
    install_symlink "$src" "$dest" "~/.claude/skills/livespec.md"
  else
    local dest="$PROJECT_DIR/CLAUDE.md"
    local header_text="<!-- Generated by LiveSpec /spec.link claude-code -->
<!-- To update: run /spec.link claude-code --force or bash scripts/link.sh --tool claude-code --force -->
<!-- Source: adapters/claude-code/SKILL.md -->"
    install_with_header "$src" "$dest" "$header_text" "CLAUDE.md"
  fi
}

# ─── Link Cursor ──────────────────────────────────────────────────────────────
link_cursor() {
  header "Linking Cursor adapter..."

  local src="$LIVESPEC_ROOT/adapters/cursor/.cursorrules"
  local dest="$PROJECT_DIR/.cursorrules"

  append_with_marker "$src" "$dest" "# LiveSpec Rules for Cursor" ".cursorrules"
}

# ─── Process tool list ────────────────────────────────────────────────────────
process_tools() {
  local tools_to_process=("$@")

  for tool in "${tools_to_process[@]}"; do
    case "$tool" in
      copilot)    link_copilot ;;
      claude-code) link_claude_code ;;
      cursor)     link_cursor ;;
      *)          warn "Unknown tool: $tool (valid: copilot, claude-code, cursor, all)" ;;
    esac
  done
}

# ─── Main ─────────────────────────────────────────────────────────────────────
main() {
  header "🔗 LiveSpec Link"
  echo -e "  Linking adapters in: ${BOLD}$PROJECT_DIR${RESET}"

  if [[ "$DRY_RUN" == true ]]; then
    warn "Dry run mode — no files will be created"
  fi

  check_prerequisites

  # Step 1: Copy command files
  copy_commands

  # Step 2: Determine which tools to link
  local tools_input="$TOOL"

  if [[ -z "$tools_input" ]]; then
    tools_input="$(detect_tools)"
  fi

  if [[ "$tools_input" == "all" ]]; then
    process_tools "copilot" "claude-code" "cursor"
  else
    # Split space-separated tool list from auto-detect
    read -ra tools_array <<< "$tools_input"
    process_tools "${tools_array[@]}"
  fi

  # Summary
  header "✅ Done!"
  echo ""
  echo -e "  ${BOLD}Next steps:${RESET}"
  echo ""
  echo -e "  • AI tools can now find command docs at ${BOLD}.specs/commands/*.md${RESET}"
  echo -e "  • Re-run with ${BOLD}--force${RESET} to update adapters after a LiveSpec upgrade"
  echo ""
  if [[ "$DRY_RUN" == true ]]; then
    echo -e "  ${YELLOW}(dry run — no files were actually created)${RESET}"
    echo ""
  fi
}

main "$@"
