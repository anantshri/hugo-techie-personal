#!/bin/bash
# migrate-slides.sh — One-time migration of slide PDFs from content bundles
#
# Moves slides.pdf from content/slides/<slug>/slides.pdf to:
#   1. assets/slides/pdf_files/<slug>.pdf  (inbox / source of truth)
#   2. static/slides/<slug>/slides.pdf     (download serving)
# Then removes the PDF from the content bundle.
#
# Safe to run multiple times — skips bundles where the PDF is already gone.
#
# Usage: ./themes/hugo-techie-personal/scripts/migrate-slides.sh

set -euo pipefail

# ---- Color helpers ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[migrate]${NC} $*"; }
warn() { echo -e "${YELLOW}[migrate]${NC} $*"; }
err()  { echo -e "${RED}[migrate]${NC} $*" >&2; }
ok()   { echo -e "${GREEN}[migrate]${NC} $*"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SITE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

CONTENT_DIR="$SITE_ROOT/content/slides"
INBOX="$SITE_ROOT/assets/slides/pdf_files"
STATIC_DIR="$SITE_ROOT/static/slides"

mkdir -p "$INBOX"

log "Site root: $SITE_ROOT"
log "Migrating PDFs from content bundles to inbox + static..."
echo ""

migrated=0
skipped=0
already_done=0

for bundle_dir in "$CONTENT_DIR"/*/; do
  [ -d "$bundle_dir" ] || continue
  slug="$(basename "$bundle_dir")"
  bundle_pdf="$bundle_dir/slides.pdf"
  inbox_pdf="$INBOX/$slug.pdf"
  static_pdf="$STATIC_DIR/$slug/slides.pdf"

  if [ ! -f "$bundle_pdf" ]; then
    if [ -f "$inbox_pdf" ]; then
      already_done=$((already_done + 1))
    fi
    continue
  fi

  log "Migrating: $slug"

  # Copy to inbox (source of truth)
  if [ -f "$inbox_pdf" ]; then
    log "  Inbox already has $slug.pdf — verifying match"
    bundle_hash="$(shasum -a 256 "$bundle_pdf" | cut -d' ' -f1)"
    inbox_hash="$(shasum -a 256 "$inbox_pdf" | cut -d' ' -f1)"
    if [ "$bundle_hash" != "$inbox_hash" ]; then
      warn "  Hash mismatch! Bundle PDF differs from inbox copy."
      warn "  Bundle: $bundle_hash"
      warn "  Inbox:  $inbox_hash"
      warn "  Skipping $slug — resolve manually."
      skipped=$((skipped + 1))
      continue
    fi
  else
    cp "$bundle_pdf" "$inbox_pdf"
    ok "  → assets/slides/pdf_files/$slug.pdf"
  fi

  # Copy to static (download serving)
  mkdir -p "$STATIC_DIR/$slug"
  cp "$bundle_pdf" "$static_pdf"
  ok "  → static/slides/$slug/slides.pdf"

  # Remove PDF from content bundle
  rm "$bundle_pdf"
  ok "  Removed content/slides/$slug/slides.pdf"

  migrated=$((migrated + 1))
  echo ""
done

echo ""
if [ "$migrated" -eq 0 ] && [ "$already_done" -eq 0 ]; then
  warn "No slide PDFs found in content bundles."
else
  [ "$migrated" -gt 0 ] && ok "Migrated $migrated presentation(s)."
  [ "$already_done" -gt 0 ] && log "$already_done presentation(s) already migrated."
  [ "$skipped" -gt 0 ] && warn "$skipped presentation(s) skipped due to conflicts."
  echo ""
  ok "Migration complete. You can now use:"
  ok "  1. Drop new PDFs in assets/slides/pdf_files/"
  ok "  2. ./themes/hugo-techie-personal/scripts/scaffold-slides.sh"
  ok "  3. ./themes/hugo-techie-personal/scripts/process-slides.sh"
fi
