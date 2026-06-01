#!/usr/bin/env bash
set -euo pipefail

# migrate.sh — Parse and execute LiveSpec migration DSL
#
# Usage: migrate.sh <migration-file> <project-dir> <livespec-dir>
#
# DSL verbs: MKDIR, SYMLINK, COPY, DELETE, RUN, GITIGNORE, SET_VERSION
# Lines starting with # are comments. Empty lines are ignored.
# Frontmatter (--- blocks) is skipped.

MIGRATION_FILE="${1:?Usage: migrate.sh <migration-file> <project-dir> <livespec-dir>}"
PROJECT_DIR="${2:?Usage: migrate.sh <migration-file> <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${3:?Usage: migrate.sh <migration-file> <project-dir> <livespec-dir>}"

# Resolve to absolute paths
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
LIVESPEC_DIR="$(cd "$LIVESPEC_DIR" && pwd)"

if [[ ! -f "$MIGRATION_FILE" ]]; then
  echo "ERROR: Migration file not found: $MIGRATION_FILE" >&2
  exit 1
fi

in_frontmatter=false
frontmatter_count=0
line_num=0

while IFS= read -r line || [[ -n "$line" ]]; do
  line_num=$((line_num + 1))

  # Handle frontmatter
  if [[ "$line" == "---" ]]; then
    frontmatter_count=$((frontmatter_count + 1))
    if [[ $frontmatter_count -eq 1 ]]; then
      in_frontmatter=true
      continue
    elif [[ $frontmatter_count -eq 2 ]]; then
      in_frontmatter=false
      continue
    fi
  fi
  if [[ "$in_frontmatter" == true ]]; then
    continue
  fi

  # Skip empty lines and comments
  [[ -z "$line" ]] && continue
  [[ "$line" =~ ^[[:space:]]*# ]] && continue

  # Parse verb and arguments
  verb="${line%% *}"
  args="${line#* }"

  # Skip prose lines — only process known DSL verbs
  case "$verb" in
    MKDIR|SYMLINK|COPY|DELETE|RUN|GITIGNORE|SET_VERSION) ;;
    *) continue ;;
  esac

  case "$verb" in
    MKDIR)
      mkdir -p "$PROJECT_DIR/$args"
      echo "  ✓ MKDIR $args"
      ;;
    SYMLINK)
      src="${args%% *}"
      dest="${args#* }"
      mkdir -p "$(dirname "$PROJECT_DIR/$dest")"
      ln -sf "$LIVESPEC_DIR/$src" "$PROJECT_DIR/$dest"
      echo "  ✓ SYMLINK $src → $dest"
      ;;
    COPY)
      src="${args%% *}"
      dest="${args#* }"
      mkdir -p "$(dirname "$PROJECT_DIR/$dest")"
      cp -f "$LIVESPEC_DIR/$src" "$PROJECT_DIR/$dest"
      echo "  ✓ COPY $src → $dest"
      ;;
    DELETE)
      if [[ -e "$PROJECT_DIR/$args" ]]; then
        rm -rf "$PROJECT_DIR/$args"
        echo "  ✓ DELETE $args"
      else
        echo "  ✓ DELETE $args (already absent)"
      fi
      ;;
    RUN)
      script="${args%% *}"
      script_args="${args#* }"
      if [[ "$script_args" == "$script" ]]; then
        script_args=""
      fi
      echo "  ▸ RUN $script $script_args"
      if [[ "$script" == *.py ]]; then
        python3 "$LIVESPEC_DIR/scripts/$script" "$PROJECT_DIR" "$LIVESPEC_DIR" $script_args
      else
        "$LIVESPEC_DIR/scripts/$script" "$PROJECT_DIR" "$LIVESPEC_DIR" $script_args
      fi
      echo "  ✓ RUN $script complete"
      ;;
    GITIGNORE)
      pattern="$args"
      gitignore="$PROJECT_DIR/.gitignore"
      if [[ ! -f "$gitignore" ]]; then
        echo "$pattern" > "$gitignore"
        echo "  ✓ GITIGNORE $pattern (created .gitignore)"
      elif ! grep -qxF "$pattern" "$gitignore"; then
        echo "$pattern" >> "$gitignore"
        echo "  ✓ GITIGNORE $pattern"
      else
        echo "  ✓ GITIGNORE $pattern (already present)"
      fi
      ;;
    SET_VERSION)
      echo "$args" > "$PROJECT_DIR/.specs/livespec-version"
      echo "  ✓ SET_VERSION $args"
      ;;
    *)
      echo "ERROR: Unknown verb '$verb' at line $line_num: $line" >&2
      exit 1
      ;;
  esac
done < "$MIGRATION_FILE"

echo "Migration complete."
exit 0
