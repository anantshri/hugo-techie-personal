#!/bin/bash
# process-slides.sh — Convert slide PDFs to multi-resolution images
#
# Dependencies: poppler-utils (pdftoppm), libwebp (cwebp), imagemagick (magick/convert)
# Usage: ./scripts/process-slides.sh [content_dir]
#
# Scans for slides.pdf in page bundles under content/slides/
# Generates three resolution tiers in WebP + JPEG fallback
# Creates metadata.json with slide count and dimensions
# Skips already-processed PDFs (checks source hash)

set -euo pipefail

# ---- Configuration ----
THUMB_WIDTH=400
MEDIUM_WIDTH=1024
FULL_WIDTH=1920
WEBP_QUALITY=85
JPEG_QUALITY=90
DPI=300

# ---- Color helpers ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[slides]${NC} $*"; }
warn() { echo -e "${YELLOW}[slides]${NC} $*"; }
err()  { echo -e "${RED}[slides]${NC} $*" >&2; }
ok()   { echo -e "${GREEN}[slides]${NC} $*"; }

# ---- Dependency check ----
check_deps() {
  local missing=0
  for cmd in pdftoppm cwebp shasum; do
    if ! command -v "$cmd" &>/dev/null; then
      err "Missing required command: $cmd"
      missing=1
    fi
  done

  # Check for imagemagick (magick or convert)
  if command -v magick &>/dev/null; then
    CONVERT="magick"
  elif command -v convert &>/dev/null; then
    CONVERT="convert"
  else
    err "Missing required command: imagemagick (magick or convert)"
    missing=1
  fi

  if [ "$missing" -eq 1 ]; then
    err ""
    err "Install missing dependencies:"
    err "  macOS:  brew install poppler webp imagemagick"
    err "  Debian: sudo apt-get install poppler-utils libwebp-dev imagemagick"
    exit 1
  fi
}

# ---- Compute SHA-256 of a file ----
file_hash() {
  shasum -a 256 "$1" | cut -d' ' -f1
}

# ---- Process a single PDF ----
process_pdf() {
  local bundle_dir="$1"
  local pdf_path="$bundle_dir/slides.pdf"
  local out_dir="$bundle_dir/slides"
  local metadata="$out_dir/metadata.json"

  if [ ! -f "$pdf_path" ]; then
    return
  fi

  log "Found: $pdf_path"

  # Check if already processed (compare hash)
  local current_hash
  current_hash="$(file_hash "$pdf_path")"

  if [ -f "$metadata" ]; then
    local stored_hash
    stored_hash="$(grep -o '"source_hash"[[:space:]]*:[[:space:]]*"sha256:[^"]*"' "$metadata" | sed 's/.*sha256://' | tr -d '"')"
    if [ "$stored_hash" = "$current_hash" ]; then
      log "  Skipping (unchanged, hash matches)"
      return
    fi
    log "  PDF changed, regenerating..."
  fi

  mkdir -p "$out_dir"

  # Step 1: Extract pages as high-res JPEG using pdftoppm
  local tmp_dir
  tmp_dir="$(mktemp -d)"
  log "  Extracting pages at ${DPI}dpi..."
  pdftoppm -jpeg -r "$DPI" "$pdf_path" "$tmp_dir/page"

  # Count extracted pages
  local page_files
  page_files=("$tmp_dir"/page-*.jpg)
  local page_count=${#page_files[@]}

  if [ "$page_count" -eq 0 ]; then
    err "  No pages extracted from $pdf_path"
    rm -rf "$tmp_dir"
    return
  fi

  log "  Processing $page_count slides..."

  # Get dimensions from first page
  local dimensions
  dimensions=$($CONVERT "${page_files[0]}" -format "%wx%h" info:)
  local orig_w orig_h
  orig_w=$(echo "$dimensions" | cut -dx -f1)
  orig_h=$(echo "$dimensions" | cut -dx -f2)

  # Step 2: Generate three tiers for each page
  local i=0
  for page_file in "${page_files[@]}"; do
    i=$((i + 1))
    local num
    num=$(printf "%03d" "$i")

    # Full resolution (cap at FULL_WIDTH)
    if [ "$orig_w" -gt "$FULL_WIDTH" ]; then
      $CONVERT "$page_file" -resize "${FULL_WIDTH}x" -quality "$JPEG_QUALITY" "$out_dir/slide-${num}-full.jpg"
    else
      $CONVERT "$page_file" -quality "$JPEG_QUALITY" "$out_dir/slide-${num}-full.jpg"
    fi

    # Medium
    $CONVERT "$page_file" -resize "${MEDIUM_WIDTH}x" -quality "$JPEG_QUALITY" "$out_dir/slide-${num}-medium.jpg"

    # Thumbnail
    $CONVERT "$page_file" -resize "${THUMB_WIDTH}x" -quality "$JPEG_QUALITY" "$out_dir/slide-${num}-thumb.jpg"

    # WebP versions
    cwebp -q "$WEBP_QUALITY" -quiet "$out_dir/slide-${num}-full.jpg" -o "$out_dir/slide-${num}-full.webp"
    cwebp -q "$WEBP_QUALITY" -quiet "$out_dir/slide-${num}-medium.jpg" -o "$out_dir/slide-${num}-medium.webp"
    cwebp -q "$WEBP_QUALITY" -quiet "$out_dir/slide-${num}-thumb.jpg" -o "$out_dir/slide-${num}-thumb.webp"

    # Progress
    if [ $((i % 10)) -eq 0 ] || [ "$i" -eq "$page_count" ]; then
      log "  $i / $page_count"
    fi
  done

  # Compute output dimensions (from the full-size first slide)
  local out_dimensions
  out_dimensions=$($CONVERT "$out_dir/slide-001-full.jpg" -format "%wx%h" info:)
  local out_w out_h
  out_w=$(echo "$out_dimensions" | cut -dx -f1)
  out_h=$(echo "$out_dimensions" | cut -dx -f2)

  # Step 3: Write metadata.json
  cat > "$metadata" <<EOF
{
  "page_count": $page_count,
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "source_pdf": "slides.pdf",
  "source_hash": "sha256:$current_hash",
  "dimensions": { "width": $out_w, "height": $out_h }
}
EOF

  # Step 4: Update page_count in index.md frontmatter if present
  local index_md="$bundle_dir/index.md"
  if [ -f "$index_md" ]; then
    if grep -q "page_count:" "$index_md"; then
      sed -i.bak "s/page_count:.*/page_count: $page_count/" "$index_md"
      rm -f "$index_md.bak"
      log "  Updated page_count in index.md"
    fi
  fi

  # Cleanup
  rm -rf "$tmp_dir"

  ok "  Done: $page_count slides (${out_w}x${out_h})"
}

# ---- Main ----
main() {
  check_deps

  local content_dir="${1:-content/slides}"

  if [ ! -d "$content_dir" ]; then
    err "Content directory not found: $content_dir"
    err "Usage: $0 [content_dir]"
    exit 2
  fi

  log "Scanning $content_dir for slide PDFs..."
  echo ""

  local found=0
  for bundle_dir in "$content_dir"/*/; do
    [ -d "$bundle_dir" ] || continue
    if [ -f "$bundle_dir/slides.pdf" ]; then
      found=$((found + 1))
      process_pdf "$bundle_dir"
      echo ""
    fi
  done

  if [ "$found" -eq 0 ]; then
    warn "No slides.pdf files found in $content_dir/*/"
  else
    ok "Processed $found presentation(s)"
  fi
}

main "$@"
