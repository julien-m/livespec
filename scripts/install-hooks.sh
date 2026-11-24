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
#   - Replaces exact historical hooks and preserves custom hooks byte-for-byte.
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

GITIGNORE="${PROJECT_DIR}/.gitignore"
if [[ -L "${GITIGNORE}" ]]; then
    echo "Error: refusing to write linked .gitignore at ${GITIGNORE}" >&2
    exit 1
fi

# Both supported entrances use the same ownership checks. Pass a linked .git
# path to the helper so it can refuse it rather than treating it as absent.
if [[ -d "${PROJECT_DIR}/.git" || -L "${PROJECT_DIR}/.git" ]]; then
    PYTHON_BIN=python3
    [[ ! -x "${LIVESPEC_DIR}/.venv/bin/python" ]] || PYTHON_BIN="${LIVESPEC_DIR}/.venv/bin/python"
    "${PYTHON_BIN}" -B "${LIVESPEC_DIR}/validator/hook_install.py" "${PROJECT_DIR}"
else
    echo "  (no .git/ in ${PROJECT_DIR} — skipping hook install)"
fi

# .gitignore handling — append `.specs/.runs/` and `.specs/.previews/` if
# absent. Both are local artefacts produced by `livespec verify-output`
# (--save) and the run wrapper; neither is ever versioned.
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
