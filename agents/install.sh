#!/bin/sh
# install.sh — wire the hugo-techie-personal theme's AI guidance into a Hugo site.
#
# What it does:
#   1. Copies themes/hugo-techie-personal/AGENTS.md to <site_root>/AGENTS.md (if missing).
#   2. Creates .agents-skills  -> themes/hugo-techie-personal/agents/skills  (symlink).
#   3. For each skill, wires .cursor/skills/hugo-techie-<name>/ and
#      .claude/skills/hugo-techie-<name>/ to the skill bundle (if those
#      parent directories exist).
#   4. Picks symlink vs copy automatically: symlink when the theme is a git
#      submodule, copy otherwise (e.g. vendored directly, zip download).
#
# Usage:
#   ./themes/hugo-techie-personal/agents/install.sh            # install
#   ./themes/hugo-techie-personal/agents/install.sh --force    # overwrite existing AGENTS.md
#   ./themes/hugo-techie-personal/agents/install.sh --dry-run  # show what would happen
#
# Exits non-zero on error. Safe to re-run.

set -eu

FORCE=0
DRY=0
for arg in "$@"; do
    case "$arg" in
        -f|--force)   FORCE=1 ;;
        -n|--dry-run) DRY=1 ;;
        -h|--help)
            sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            printf 'install.sh: unknown argument: %s\n' "$arg" >&2
            exit 2
            ;;
    esac
done

# Locate the theme root (this script's parent's parent).
THEME_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
THEME_NAME=$(basename "$THEME_DIR")

# Locate the site root. Strategy:
#   - If invoked from somewhere inside a Hugo site, walk up from PWD looking
#     for a hugo config (config.toml / hugo.toml / hugo.yaml / config.yaml).
#   - Fallback: the parent of themes/<theme>/, which is the conventional layout.
find_site_root() {
    dir=$PWD
    while [ "$dir" != "/" ]; do
        for cfg in config.toml hugo.toml hugo.yaml config.yaml hugo.json config.json; do
            if [ -f "$dir/$cfg" ]; then
                printf '%s\n' "$dir"
                return 0
            fi
        done
        dir=$(dirname "$dir")
    done
    # Fallback: two levels up from the theme dir (themes/<name>/.. == site root).
    CDPATH='' cd -- "$THEME_DIR/../.." && pwd
}

SITE_ROOT=$(find_site_root)

printf 'Theme:       %s\n' "$THEME_DIR"
printf 'Site root:   %s\n' "$SITE_ROOT"

# Relative path from $SITE_ROOT to the given absolute path.
# Prefers `realpath --relative-to` (GNU coreutils), then python3, then
# falls back to emitting the absolute path unchanged.
rel_theme() {
    _abs=$1
    if realpath --relative-to="$SITE_ROOT" "$_abs" 2>/dev/null; then
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'import os,sys; print(os.path.relpath(sys.argv[2], sys.argv[1]))' "$SITE_ROOT" "$_abs"
        return $?
    fi
    printf '%s\n' "$_abs"
}

# Decide symlink vs copy. Symlink when the theme is a git submodule
# (i.e. tracked as a submodule of the containing repo, or its own .git is a
# file pointing to a superproject gitdir). Copy otherwise.
use_symlinks() {
    if [ -f "$THEME_DIR/.git" ] && grep -q '^gitdir:' "$THEME_DIR/.git" 2>/dev/null; then
        return 0
    fi
    if [ -f "$SITE_ROOT/.gitmodules" ] && \
       grep -q "path *= *themes/$THEME_NAME" "$SITE_ROOT/.gitmodules" 2>/dev/null; then
        return 0
    fi
    return 1
}

if use_symlinks; then
    MODE=symlink
else
    MODE=copy
fi
printf 'Link mode:   %s\n' "$MODE"

run() {
    if [ "$DRY" -eq 1 ]; then
        printf '  [dry-run] %s\n' "$*"
    else
        eval "$@"
    fi
}

link_or_copy() {
    src=$1
    dst=$2
    if [ -e "$dst" ] || [ -L "$dst" ]; then
        run "rm -rf -- '$dst'"
    fi
    run "mkdir -p -- '$(dirname -- "$dst")'"
    if [ "$MODE" = symlink ]; then
        rel=$(rel_theme "$src")
        run "ln -s -- '$rel' '$dst'"
    else
        run "cp -R -- '$src' '$dst'"
    fi
}

# --- 1. Copy AGENTS.md to the site root ----------------------------------
AGENTS_SRC="$THEME_DIR/AGENTS.md"
AGENTS_DST="$SITE_ROOT/AGENTS.md"

if [ ! -f "$AGENTS_SRC" ]; then
    printf 'ERROR: %s is missing.\n' "$AGENTS_SRC" >&2
    exit 1
fi

if [ -f "$AGENTS_DST" ] && [ "$FORCE" -ne 1 ]; then
    printf 'AGENTS.md:   exists at %s (use --force to overwrite)\n' "$AGENTS_DST"
else
    run "cp -- '$AGENTS_SRC' '$AGENTS_DST'"
    printf 'AGENTS.md:   %s -> %s\n' "$AGENTS_SRC" "$AGENTS_DST"
fi

# --- 2. Canonical skills folder pointer ----------------------------------
SKILLS_DIR="$THEME_DIR/agents/skills"
if [ ! -d "$SKILLS_DIR" ]; then
    printf 'ERROR: skills directory missing: %s\n' "$SKILLS_DIR" >&2
    exit 1
fi

POINTER="$SITE_ROOT/.agents-skills"
if [ -L "$POINTER" ] || [ -e "$POINTER" ]; then
    run "rm -f -- '$POINTER'"
fi
rel_skills=$(rel_theme "$SKILLS_DIR")
run "ln -s -- '$rel_skills' '$POINTER'"
printf '.agents-skills: -> %s\n' "$rel_skills"

# --- 3. Per-skill wiring into .cursor/skills and .claude/skills ----------
wire_skill() {
    parent=$1
    tool_label=$2

    if [ ! -d "$SITE_ROOT/$parent" ]; then
        printf '%-14s skip (no %s/)\n' "$tool_label:" "$parent"
        return 0
    fi

    wired=0
    for skill_path in "$SKILLS_DIR"/*/; do
        [ -d "$skill_path" ] || continue
        skill_name=$(basename "$skill_path")
        # Only wire skills that actually have a SKILL.md (skip empty stubs).
        if [ ! -f "$skill_path/SKILL.md" ]; then
            continue
        fi
        dst="$SITE_ROOT/$parent/hugo-techie-$skill_name"
        link_or_copy "$skill_path" "$dst"
        wired=$((wired + 1))
    done
    printf '%-14s wired %d skill(s) into %s/\n' "$tool_label:" "$wired" "$parent"
}

wire_skill ".cursor/skills"  "Cursor"
wire_skill ".claude/skills"  "Claude"

# --- 4. Next steps ------------------------------------------------------
rel_theme_dir=$(rel_theme "$THEME_DIR")
cat <<EOF

Done. Next steps:

  1. Open your AI assistant in this directory.
  2. Try one of these to get started:
       "Bootstrap a portfolio site for <your name>."
       "Add a talk I gave: <URL of the event>."
       "Import my LinkedIn takeout from takeouts/linkedin-*.zip."
  3. The assistant will find AGENTS.md at the site root and use the
     skills under $rel_skills/.

For details, see $rel_theme_dir/agents/README.md
EOF
