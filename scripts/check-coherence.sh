#!/usr/bin/env bash
# LiveSpec — Internal coherence checker
# Validates that docs, scripts, and commands are consistent.
#
# Usage: bash scripts/check-coherence.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

errors=0
warnings=0

pass() { echo -e "  ${GREEN}✓${RESET} $1"; }
fail() { echo -e "  ${RED}✗${RESET} $1"; errors=$((errors + 1)); }
warn() { echo -e "  ${YELLOW}!${RESET} $1"; warnings=$((warnings + 1)); }

# Extract the COMMANDS=(...) array content from install.sh
extract_commands() {
  sed -n 's/^COMMANDS=(\(.*\))/\1/p' "$ROOT/scripts/install.sh"
}

# Extract the AGENTS=(...) array content from install.sh
extract_agents() {
  sed -n 's/^AGENTS=(\(.*\))/\1/p' "$ROOT/scripts/install.sh"
}

echo -e "${BOLD}LiveSpec Coherence Check${RESET}"
echo ""

# --- 1. Command count consistency ---
echo -e "${BOLD}1. Commands${RESET}"

INSTALL_CMD_LIST=$(extract_commands)
INSTALL_COMMANDS=$(echo "$INSTALL_CMD_LIST" | wc -w | tr -d ' ')
COMMAND_FILES=$(find "$ROOT/commands" -name "*.md" -maxdepth 1 | wc -l | tr -d ' ')

if [[ "$INSTALL_COMMANDS" == "$COMMAND_FILES" ]]; then
  pass "install.sh declares $INSTALL_COMMANDS commands, $COMMAND_FILES .md files found"
else
  fail "install.sh declares $INSTALL_COMMANDS commands but $COMMAND_FILES .md files exist"
fi

# Check each declared command has a .md file
for cmd in $INSTALL_CMD_LIST; do
  if [[ ! -f "$ROOT/commands/$cmd.md" ]]; then
    fail "Declared command '$cmd' has no commands/$cmd.md"
  fi
done

# --- 2. CLAUDE.md block command count ---
echo -e "${BOLD}2. CLAUDE.md block in init.sh${RESET}"

CLAUDEMD_COMMANDS=$(sed -n '/<!-- livespec:start -->/,/<!-- livespec:end -->/p' "$ROOT/scripts/init.sh" | grep -o '/spec\.[a-z-]*' | sort -u | wc -l | tr -d ' ')
if [[ "$CLAUDEMD_COMMANDS" -ge "$INSTALL_COMMANDS" ]]; then
  pass "CLAUDE.md block lists $CLAUDEMD_COMMANDS commands (install.sh: $INSTALL_COMMANDS)"
else
  fail "CLAUDE.md block lists $CLAUDEMD_COMMANDS commands but install.sh installs $INSTALL_COMMANDS"
fi

# --- 3. Hooks valid commands list ---
echo -e "${BOLD}3. Hooks valid commands${RESET}"

if grep -q 'play-coverage' "$ROOT/system/hooks.md"; then
  pass "play-coverage is in hooks valid commands (system/hooks.md)"
else
  fail "play-coverage missing from hooks valid commands (system/hooks.md)"
fi
if grep -q 'play-coverage' "$ROOT/commands/hooks.md"; then
  pass "play-coverage is in hooks valid commands (commands/hooks.md)"
else
  fail "play-coverage missing from hooks valid commands (commands/hooks.md)"
fi

# --- 4. No phantom references ---
echo -e "${BOLD}4. Phantom references${RESET}"

if grep -q '\.specs/commands/' "$ROOT/system/spec-system.md"; then
  fail "spec-system.md still references .specs/commands/ (phantom directory)"
else
  pass "No .specs/commands/ phantom reference in spec-system.md"
fi

if grep -q 'link\.md' "$ROOT/system/spec-system.md"; then
  fail "spec-system.md still references link.md (phantom command)"
else
  pass "No link.md phantom reference in spec-system.md"
fi

# --- 5. Playwright consistency ---
echo -e "${BOLD}5. Playwright references${RESET}"

if grep -q 'playwright-cli' "$ROOT/system/testing/discovery.md"; then
  fail "discovery.md still references deprecated playwright-cli"
else
  pass "No playwright-cli in discovery.md"
fi

# --- 6. Agent files ---
echo -e "${BOLD}6. Agents${RESET}"

INSTALL_AGENT_LIST=$(extract_agents)
INSTALL_AGENTS=$(echo "$INSTALL_AGENT_LIST" | wc -w | tr -d ' ')
AGENT_FILES=$(find "$ROOT/agents" -name "*.md" -maxdepth 1 | wc -l | tr -d ' ')

if [[ "$INSTALL_AGENTS" == "$AGENT_FILES" ]]; then
  pass "install.sh declares $INSTALL_AGENTS agents, $AGENT_FILES .md files found"
else
  fail "install.sh declares $INSTALL_AGENTS agents but $AGENT_FILES .md files exist"
fi

# --- 7. README command count ---
echo -e "${BOLD}7. README${RESET}"

README_TABLE_COMMANDS=$(grep -c '| `/spec\.' "$ROOT/README.md" || true)
if [[ "$README_TABLE_COMMANDS" == "$INSTALL_COMMANDS" ]]; then
  pass "README command table has $README_TABLE_COMMANDS entries (matches install.sh)"
else
  warn "README command table has $README_TABLE_COMMANDS entries but install.sh installs $INSTALL_COMMANDS"
fi

# --- Summary ---
echo ""
echo -e "${BOLD}Summary${RESET}"
if [[ "$errors" -eq 0 && "$warnings" -eq 0 ]]; then
  echo -e "  ${GREEN}All checks passed.${RESET}"
elif [[ "$errors" -eq 0 ]]; then
  echo -e "  ${YELLOW}$warnings warning(s), 0 errors.${RESET}"
else
  echo -e "  ${RED}$errors error(s), $warnings warning(s).${RESET}"
  exit 1
fi
