#!/bin/bash
# scaffold-slides.sh — Create draft index.md for new PDFs in the inbox
#
# Scans assets/slides/pdf_files/ for *.pdf files. For each PDF that does not
# yet have a corresponding content/slides/<slug>/index.md, generates a draft
# index.md with template frontmatter for the user to fill in.
#
# Usage: ./themes/hugo-techie-personal/scripts/scaffold-slides.sh

set -euo pipefail

# ---- Color helpers ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[scaffold]${NC} $*"; }
warn() { echo -e "${YELLOW}[scaffold]${NC} $*"; }
err()  { echo -e "${RED}[scaffold]${NC} $*" >&2; }
ok()   { echo -e "${GREEN}[scaffold]${NC} $*"; }

# ---- Resolve site root ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SITE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

INBOX="$SITE_ROOT/assets/slides/pdf_files"
CONTENT_DIR="$SITE_ROOT/content/slides"

if [ ! -d "$INBOX" ]; then
  err "Inbox directory not found: $INBOX"
  err "Create it with: mkdir -p assets/slides/pdf_files"
  exit 1
fi

log "Scanning inbox: $INBOX"
echo ""

created=0
skipped=0

for pdf_path in "$INBOX"/*.pdf; do
  [ -f "$pdf_path" ] || continue

  filename="$(basename "$pdf_path")"
  slug="${filename%.pdf}"

  # Sanitize slug: lowercase and replace spaces/underscores with hyphens
  clean_slug="$(echo "$slug" | tr '[:upper:]' '[:lower:]' | tr ' _' '--' | tr -s '-')"
  if [ "$clean_slug" != "$slug" ]; then
    new_pdf="$INBOX/$clean_slug.pdf"
    # On case-insensitive filesystems, check inode to allow case-only renames
    if [ -f "$new_pdf" ]; then
      src_inode="$(stat -f '%i' "$pdf_path" 2>/dev/null || stat -c '%i' "$pdf_path" 2>/dev/null)"
      dst_inode="$(stat -f '%i' "$new_pdf" 2>/dev/null || stat -c '%i' "$new_pdf" 2>/dev/null)"
      if [ "$src_inode" != "$dst_inode" ]; then
        err "  Cannot rename '$filename' → '$clean_slug.pdf': target already exists — skipping"
        continue
      fi
    fi
    mv "$pdf_path" "$new_pdf"
    warn "  Renamed PDF: $filename → $clean_slug.pdf"
    slug="$clean_slug"
  fi

  index_md="$CONTENT_DIR/$slug/index.md"

  if [ -f "$index_md" ]; then
    log "  Exists: content/slides/$slug/index.md — skipping"
    skipped=$((skipped + 1))
    continue
  fi

  mkdir -p "$CONTENT_DIR/$slug"

  # Extract a human-readable title from the slug
  title="$(echo "$slug" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1')"

  cat > "$index_md" <<FRONTMATTER
---
title: "$title"
date: $(date +%Y-%m-%d)
draft: true

conference: ""
conference_url: ""
event_year: $(date +%Y)

location:
  city: ""
  state: ""
  country: ""
  latitude: 0.0
  longitude: 0.0

online: false

slides:
  pdf: "slides.pdf"
  page_count: 0
  download_enabled: true

videos: []
resources: []
timeline_entry: ""
related_presentations: []
project_links: []

tags: []
focus: []
activity: talk

oembed:
  author_name: "Anant Shrivastava"
  author_url: "https://anantshri.info"
  provider_name: "Anant Shrivastava"
  provider_url: "https://anantshri.info"
---

TODO: Add a one-line abstract of the presentation.
FRONTMATTER

  ok "  Created: content/slides/$slug/index.md (draft)"
  created=$((created + 1))
done

echo ""
if [ "$created" -eq 0 ] && [ "$skipped" -eq 0 ]; then
  warn "No PDF files found in $INBOX"
elif [ "$created" -eq 0 ]; then
  log "All $skipped PDF(s) already have content pages. Nothing to scaffold."
else
  ok "Scaffolded $created new presentation(s). Edit their index.md files, then run process-slides.sh"
  [ "$skipped" -gt 0 ] && log "($skipped existing presentation(s) skipped)"
fi
