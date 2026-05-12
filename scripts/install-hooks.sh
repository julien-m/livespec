#!/usr/bin/env bash
# Install the LiveSpec pre-commit `last_reviewed` hook.
#
# @spec FR-009: hook installer — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-009
#
# Usage:  scripts/install-hooks.sh
#
# Behavior:
#   - Installs hooks/livespec-last-reviewed.py as .git/hooks/pre-commit
#   - If a pre-commit hook already exists, appends a dispatcher block
#     keyed off the marker line `# livespec-expectations` (idempotent
#     re-install supported).
#   - Appends `.specs/.runs/` to .gitignore if absent.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_SRC="${REPO_ROOT}/hooks/livespec-last-reviewed.py"
HOOK_DST="${REPO_ROOT}/.git/hooks/pre-commit"
MARKER="# livespec-expectations"

if [[ ! -f "${HOOK_SRC}" ]]; then
    echo "Error: ${HOOK_SRC} not found." >&2
    exit 1
fi

mkdir -p "${REPO_ROOT}/.git/hooks"

if [[ -e "${HOOK_DST}" ]]; then
    if grep -q "${MARKER}" "${HOOK_DST}" 2>/dev/null; then
        echo "Hook already installed (${MARKER} marker found). Nothing to do."
    else
        echo "Existing pre-commit hook detected — appending LiveSpec dispatcher."
        {
            echo ""
            echo "${MARKER}"
            echo "python3 \"${HOOK_SRC}\" || exit 1"
        } >> "${HOOK_DST}"
        chmod +x "${HOOK_DST}"
    fi
else
    cat > "${HOOK_DST}" <<EOF
#!/usr/bin/env bash
${MARKER}
python3 "${HOOK_SRC}" || exit 1
EOF
    chmod +x "${HOOK_DST}"
    echo "Installed LiveSpec pre-commit hook at ${HOOK_DST}"
fi

GITIGNORE="${REPO_ROOT}/.gitignore"
if [[ -f "${GITIGNORE}" ]]; then
    if ! grep -qE '^\.specs/\.runs/?$' "${GITIGNORE}"; then
        printf '\n# LiveSpec local run artifacts (feature 039)\n.specs/.runs/\n' >> "${GITIGNORE}"
        echo "Appended .specs/.runs/ to .gitignore"
    fi
else
    printf '# LiveSpec local run artifacts (feature 039)\n.specs/.runs/\n' > "${GITIGNORE}"
    echo "Created .gitignore with .specs/.runs/"
fi
