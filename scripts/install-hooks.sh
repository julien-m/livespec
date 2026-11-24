#!/usr/bin/env bash
# LiveSpec traceability anchors
# @spec(FR-009)

# Install the review-led advisory pre-commit hook.
#
# @spec FR-009: hook installer — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-009
#
# Usage:
#   scripts/install-hooks.sh                           # self-install in LiveSpec repo
#   scripts/install-hooks.sh <project-dir> <livespec>  # install in downstream project (migrate/init)
#
# Behavior:
#   - Installs the advisory template as <project>/.git/hooks/pre-commit.
#   - Preserves other checks in a custom or legacy composite hook.
#   - Appends `.specs/.runs/` and `.specs/.previews/` to .gitignore if absent.

set -euo pipefail

# Two-argument form (project-dir, livespec-dir) is the canonical signature used
# by the migrate.sh DSL. Zero-argument form falls back to a self-install where
# both roots collapse to the current git toplevel (used during LiveSpec dev).
if [[ $# -ge 2 ]]; then
  PROJECT_DIR="$(cd "$1" && pwd)"
  LIVESPEC_DIR="$(cd "$2" && pwd)"
elif [[ $# -eq 0 ]]; then
  PROJECT_DIR="$(git rev-parse --show-toplevel)"
  LIVESPEC_DIR="${PROJECT_DIR}"
else
  echo "Usage: install-hooks.sh [<project-dir> <livespec-dir>]" >&2
  exit 1
fi

HOOK_SRC="${LIVESPEC_DIR}/validator/hooks/pre-commit-hook"
HISTORICAL_HOOK="${LIVESPEC_DIR}/validator/hooks/pre-commit-certification-hook"
HOOK_DST="${PROJECT_DIR}/.git/hooks/pre-commit"
MARKER="# @spec FR-003: Advisory commit hook"

if [[ ! -f "${HOOK_SRC}" ]]; then
    echo "Error: ${HOOK_SRC} not found." >&2
    exit 1
fi

# A project without `.git/` is either a bare checkout or a sub-tree — skip
# silently so the migration DSL does not break unrelated layouts.
if [[ ! -d "${PROJECT_DIR}/.git" ]]; then
    echo "  (no .git/ in ${PROJECT_DIR} — skipping hook install)"
else
    mkdir -p "${PROJECT_DIR}/.git/hooks"

    if [[ -L "${HOOK_DST}" ]]; then
        echo "Error: refusing to write linked pre-commit hook at ${HOOK_DST}" >&2
        exit 1
    elif [[ -f "${HOOK_DST}" ]] && cmp -s "${HOOK_DST}" "${HISTORICAL_HOOK}"; then
        cp "${HOOK_SRC}" "${HOOK_DST}"
        chmod +x "${HOOK_DST}"
        echo "Replaced the original LiveSpec certification hook with the advisory hook"
    elif [[ -e "${HOOK_DST}" ]]; then
        if grep -Fq "${MARKER}" "${HOOK_DST}"; then
            echo "Hook already installed (${MARKER} marker found). Nothing to do."
        else
            echo "Existing pre-commit hook retained. Inspect its checks separately." >&2
            {
                printf '\n'
                cat "${HOOK_SRC}"
            } >> "${HOOK_DST}"
            chmod +x "${HOOK_DST}"
        fi
    else
        cp "${HOOK_SRC}" "${HOOK_DST}"
        chmod +x "${HOOK_DST}"
        echo "Installed LiveSpec pre-commit hook at ${HOOK_DST}"
    fi
fi

# .gitignore handling — append `.specs/.runs/` and `.specs/.previews/` if
# absent. Both are local artefacts produced by `livespec verify-output`
# (--save) and the run wrapper; neither is ever versioned.
GITIGNORE="${PROJECT_DIR}/.gitignore"
ensure_gitignore_line() {
    local pattern="$1"
    local comment="$2"
    if [[ -f "${GITIGNORE}" ]]; then
        if ! grep -qxF "${pattern}" "${GITIGNORE}"; then
            printf '\n# %s\n%s\n' "${comment}" "${pattern}" >> "${GITIGNORE}"
            echo "Appended ${pattern} to .gitignore"
        fi
    else
        printf '# %s\n%s\n' "${comment}" "${pattern}" > "${GITIGNORE}"
        echo "Created .gitignore with ${pattern}"
    fi
}

ensure_gitignore_line ".specs/.runs/" "LiveSpec local run artefacts (feature 039)"
ensure_gitignore_line ".specs/.previews/" "LiveSpec verify-output --preview/--save output (feature 040)"
