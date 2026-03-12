#!/usr/bin/env bash
set -euo pipefail

# LiveSpec — Unified installer for Claude Code, GitHub Copilot, and Cursor
# Usage:
#   bash scripts/install.sh              # Interactive tool selector (TTY)
#   bash scripts/install.sh --tool all   # Install all tools (non-interactive)
#   bash scripts/install.sh --uninstall  # Remove symlinks (interactive)
#   bash scripts/install.sh --force      # Overwrite existing files
#   bash scripts/install.sh --dry-run    # Preview without changes

# --- Config ---

LIVESPEC_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_DIR="$HOME/.claude"
SKILL_DIR="$CLAUDE_DIR/skills/livespec"
COMMANDS_DIR="$CLAUDE_DIR/commands"

COMMANDS=(init specify plan implement check explain stack)

# --- Flags ---

FORCE=false
DRY_RUN=false
UNINSTALL=false
TOOLS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)     FORCE=true; shift ;;
    --dry-run)   DRY_RUN=true; shift ;;
    --uninstall) UNINSTALL=true; shift ;;
    --tool)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --tool requires a value (claude-code, copilot, cursor, all)" >&2
        exit 1
      fi
      TOOLS+=("$2"); shift 2
      ;;
    --help|-h)
      cat <<'EOF'
Usage: bash scripts/install.sh [OPTIONS]

Options:
  --tool <tool>   Tool to install: claude-code, copilot, cursor, all
                  Can be repeated: --tool claude-code --tool copilot
  --force         Overwrite existing files/symlinks
  --dry-run       Preview changes without writing anything
  --uninstall     Remove installed symlinks
  --help          Show this help message

Interactive mode (default when TTY):
  Displays a checkbox selector to choose which tools to install.

Non-interactive mode (CI, pipes):
  Requires --tool to specify which tools to install.

Examples:
  bash scripts/install.sh                                # Interactive selector
  bash scripts/install.sh --tool all                     # Install all tools
  bash scripts/install.sh --tool claude-code             # Claude Code only
  bash scripts/install.sh --tool copilot --tool cursor   # Copilot + Cursor
  bash scripts/install.sh --uninstall                    # Interactive uninstall
  bash scripts/install.sh --tool all --uninstall         # Uninstall all
  bash scripts/install.sh --dry-run                      # Preview with selector
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

log()  { echo "  $1"; }
ok()   { echo "  ✓ $1"; }
skip() { echo "  · $1 (skipped — already correct)"; }
warn() { echo "  ! $1" >&2; }
dry()  { echo "  → [dry-run] $1"; }

require_source() {
  local src="$1"
  if [[ ! -f "$src" ]]; then
    echo "ERROR: Missing source file: $src" >&2
    echo "Is this script running from the LiveSpec repository?" >&2
    exit 1
  fi
}

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

# --- Auto-detection ---

detect_claude_code() { [[ -d "$HOME/.claude" ]]; }
detect_copilot()     { [[ -d ".github" ]]; }
detect_cursor()      { [[ -f ".cursorrules" ]] || [[ -d "/Applications/Cursor.app" ]]; }

# --- Interactive TUI selector ---

show_selector() {
  local -n _items=$1
  local -n _checked=$2
  local -n _descs=$3
  local cursor=0
  local count=${#_items[@]}

  # Hide cursor
  tput civis 2>/dev/null || true

  draw_menu() {
    for (( i=0; i<count; i++ )); do
      local check=" "
      [[ "${_checked[$i]}" == "1" ]] && check="x"

      if [[ $i -eq $cursor ]]; then
        printf "\r\033[K\033[7m  [%s] %-16s %s\033[0m\n" "$check" "${_items[$i]}" "${_descs[$i]}"
      else
        printf "\r\033[K  [%s] %-16s %s\n" "$check" "${_items[$i]}" "${_descs[$i]}"
      fi
    done
    printf "\r\033[K\n"
    printf "\r\033[K  ↑/↓ navigate · Space toggle · Enter confirm"
    # Move back up to top of menu + hint line
    for (( i=0; i<count+1; i++ )); do
      tput cuu1 2>/dev/null
    done
  }

  echo "LiveSpec — Select tools to install:"
  echo ""
  draw_menu

  while true; do
    IFS= read -rsn1 key

    case "$key" in
      $'\x1b')
        read -rsn2 -t 0.1 seq || true
        case "$seq" in
          '[A') (( cursor > 0 )) && (( cursor-- )) || true ;;
          '[B') (( cursor < count - 1 )) && (( cursor++ )) || true ;;
        esac
        ;;
      ' '|$'\t')
        if [[ "${_checked[$cursor]}" == "1" ]]; then
          _checked[$cursor]=0
        else
          _checked[$cursor]=1
        fi
        ;;
      '')
        # Enter — move to end of menu and clear hint
        for (( i=0; i<count; i++ )); do
          echo ""
        done
        # Reprint final state without highlight
        printf "\r\033[K\n"
        printf "\r\033[K"
        # Move back up past the blank + hint
        tput cuu1 2>/dev/null
        tput cuu1 2>/dev/null
        for (( i=0; i<count; i++ )); do
          tput cuu1 2>/dev/null
        done
        # Final clean draw
        for (( i=0; i<count; i++ )); do
          local check=" "
          [[ "${_checked[$i]}" == "1" ]] && check="x"
          printf "\r\033[K  [%s] %-16s %s\n" "$check" "${_items[$i]}" "${_descs[$i]}"
        done
        printf "\r\033[K\n"
        printf "\r\033[K"
        tput cnorm 2>/dev/null || true
        return
        ;;
    esac

    draw_menu
  done
}

# --- Resolve selected tools ---

resolve_tools() {
  if [[ ${#TOOLS[@]} -gt 0 ]]; then
    local resolved=()
    for tool in "${TOOLS[@]}"; do
      case "$tool" in
        all)
          resolved=(claude-code copilot cursor)
          break
          ;;
        claude-code|copilot|cursor)
          resolved+=("$tool")
          ;;
        *)
          echo "ERROR: Unknown tool: $tool (valid: claude-code, copilot, cursor, all)" >&2
          exit 1
          ;;
      esac
    done
    TOOLS=("${resolved[@]}")
    return
  fi

  if [[ ! -t 0 ]]; then
    echo "ERROR: No TTY detected and no --tool specified." >&2
    echo "In non-interactive mode, use: --tool claude-code|copilot|cursor|all" >&2
    exit 1
  fi

  # Auto-detect for pre-checking
  local items=("Claude Code" "GitHub Copilot" "Cursor")
  local tool_ids=(claude-code copilot cursor)
  local descs=(
    "~/.claude/skills/ + commands/"
    ".github/copilot-instructions.md"
    ".cursorrules"
  )
  local checked=(0 0 0)
  local any_detected=false

  if detect_claude_code; then checked[0]=1; any_detected=true; fi
  if detect_copilot;     then checked[1]=1; any_detected=true; fi
  if detect_cursor;      then checked[2]=1; any_detected=true; fi

  # Default: Claude Code if nothing detected
  if [[ "$any_detected" == false ]]; then
    checked[0]=1
  fi

  show_selector items checked descs

  TOOLS=()
  for (( i=0; i<${#tool_ids[@]}; i++ )); do
    if [[ "${checked[$i]}" == "1" ]]; then
      TOOLS+=("${tool_ids[$i]}")
    fi
  done

  if [[ ${#TOOLS[@]} -eq 0 ]]; then
    echo "No tools selected. Nothing to do."
    exit 0
  fi
}

# --- Integrity check ---

require_source "$LIVESPEC_ROOT/adapters/claude-code/SKILL.md"
for cmd in "${COMMANDS[@]}"; do
  require_source "$LIVESPEC_ROOT/commands/$cmd.md"
done
require_source "$LIVESPEC_ROOT/adapters/copilot/agent.md"
require_source "$LIVESPEC_ROOT/adapters/cursor/.cursorrules"

# --- Install functions ---

install_claude_code() {
  echo "Claude Code:"
  if [[ "$DRY_RUN" == false ]]; then
    mkdir -p "$SKILL_DIR"
    mkdir -p "$COMMANDS_DIR"
  fi
  create_link "$LIVESPEC_ROOT/adapters/claude-code/SKILL.md" "$SKILL_DIR/SKILL.md" "skills/livespec/SKILL.md"
  for cmd in "${COMMANDS[@]}"; do
    create_link "$LIVESPEC_ROOT/commands/$cmd.md" "$COMMANDS_DIR/spec.$cmd.md" "commands/spec.$cmd.md"
  done
}

install_copilot() {
  echo "GitHub Copilot:"
  local src="$LIVESPEC_ROOT/adapters/copilot/agent.md"
  local target=".github/copilot-instructions.md"
  if [[ "$DRY_RUN" == false ]]; then
    mkdir -p ".github"
  fi
  create_link "$src" "$target" ".github/copilot-instructions.md"
}

install_cursor() {
  echo "Cursor:"
  local src="$LIVESPEC_ROOT/adapters/cursor/.cursorrules"
  local target=".cursorrules"
  create_link "$src" "$target" ".cursorrules"
}

# --- Uninstall functions ---

uninstall_claude_code() {
  echo "Claude Code:"
  for cmd in "${COMMANDS[@]}"; do
    remove_link "$COMMANDS_DIR/spec.$cmd.md" "commands/spec.$cmd.md"
  done
  remove_link "$SKILL_DIR/SKILL.md" "skills/livespec/SKILL.md"

  if [[ -d "$SKILL_DIR" ]] && [[ -z "$(ls -A "$SKILL_DIR" 2>/dev/null)" ]]; then
    if [[ "$DRY_RUN" == true ]]; then
      dry "remove empty directory $SKILL_DIR"
    else
      rmdir "$SKILL_DIR"
      ok "removed empty skills/livespec/"
    fi
  fi
}

uninstall_copilot() {
  echo "GitHub Copilot:"
  remove_link ".github/copilot-instructions.md" ".github/copilot-instructions.md"
}

uninstall_cursor() {
  echo "Cursor:"
  remove_link ".cursorrules" ".cursorrules"
}

# --- Main ---

resolve_tools

if [[ "$UNINSTALL" == true ]]; then
  echo ""
  echo "Uninstalling LiveSpec..."
  echo ""
  for tool in "${TOOLS[@]}"; do
    case "$tool" in
      claude-code) uninstall_claude_code ;;
      copilot)     uninstall_copilot ;;
      cursor)      uninstall_cursor ;;
    esac
    echo ""
  done
  echo "Done."
  exit 0
fi

echo ""
echo "Installing LiveSpec..."
echo ""

for tool in "${TOOLS[@]}"; do
  case "$tool" in
    claude-code) install_claude_code ;;
    copilot)     install_copilot ;;
    cursor)      install_cursor ;;
  esac
  echo ""
done

# --- Verify ---

if [[ "$DRY_RUN" == false ]]; then
  errors=0
  for tool in "${TOOLS[@]}"; do
    case "$tool" in
      claude-code)
        if [[ ! -L "$SKILL_DIR/SKILL.md" ]]; then
          warn "Verification failed: skills/livespec/SKILL.md is not a symlink"
          errors=$((errors + 1))
        fi
        for cmd in "${COMMANDS[@]}"; do
          if [[ ! -L "$COMMANDS_DIR/spec.$cmd.md" ]]; then
            warn "Verification failed: commands/spec.$cmd.md is not a symlink"
            errors=$((errors + 1))
          fi
        done
        ;;
      copilot)
        if [[ ! -L ".github/copilot-instructions.md" ]]; then
          warn "Verification failed: .github/copilot-instructions.md is not a symlink"
          errors=$((errors + 1))
        fi
        ;;
      cursor)
        if [[ ! -L ".cursorrules" ]]; then
          warn "Verification failed: .cursorrules is not a symlink"
          errors=$((errors + 1))
        fi
        ;;
    esac
  done

  if [[ "$errors" -gt 0 ]]; then
    echo "$errors symlink(s) failed verification." >&2
    exit 1
  fi
fi

echo "Done! LiveSpec is ready."

for tool in "${TOOLS[@]}"; do
  if [[ "$tool" == "claude-code" ]]; then
    echo ""
    echo "Next: run /spec.init in your project to set up .specs/ and CLAUDE.md."
    break
  fi
done
