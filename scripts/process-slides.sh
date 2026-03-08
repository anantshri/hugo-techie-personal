#!/bin/bash
# process-slides.sh — Convert slide PDFs to single high-res WebP per slide
#
# Outputs one WebP per slide to assets/slides/<slug>/ so the repo keeps a single
# copy per slide. Hugo's image processing (resources.Get + Resize) generates
# thumb/medium/full at build time with quality 100.
#
# Dependencies: poppler-utils (pdftoppm), libwebp (cwebp), imagemagick (magick/convert)
# Usage: ./scripts/process-slides.sh [content_dir]
#
# Scans for slides.pdf in page bundles under content/slides/
# Writes assets/slides/<slug>/slide-NNN.webp (one file per slide, highest resolution)
# Writes metadata.json in bundle's slides/ for hash check and page_count
# Skips already-processed PDFs (checks source hash)

set -euo pipefail

# ---- Configuration ----
FULL_WIDTH=1920
WEBP_QUALITY=100
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

# ---- Resolve site root (parent of directory containing content_dir) ----
site_root() {
  local content_dir="$1"
  local content_parent
  content_parent="$(cd "$(dirname "$content_dir")" && pwd)"
  (cd "$content_parent/.." && pwd)
}

# ---- Process a single PDF ----
process_pdf() {
  local bundle_dir="$1"
  local assets_slides_root="$2"
  local pdf_path="$bundle_dir/slides.pdf"
  local metadata_dir="$bundle_dir/slides"
  local metadata="$metadata_dir/metadata.json"
  local slug
  slug="$(basename "$bundle_dir")"
  local out_dir="$assets_slides_root/$slug"

  if [ ! -f "$pdf_path" ]; then
    return
  fi

  log "Found: $pdf_path"

  # Check if already processed (compare hash)
  local current_hash
  current_hash="$(file_hash "$pdf_path")"

  if [ -f "$metadata" ]; then
    local stored_hash
    stored_hash="$(grep -o '"source_hash"[[:space:]]*:[[:space:]]*"sha256:[^"]*"' "$metadata" 2>/dev/null | sed 's/.*sha256://' | tr -d '"')"
    if [ "$stored_hash" = "$current_hash" ]; then
      # Skip only if assets already exist with expected count
      local stored_count
      stored_count="$(grep -o '"page_count"[[:space:]]*:[[:space:]]*[0-9]*' "$metadata" 2>/dev/null | grep -o '[0-9]*$' | tr -d ' ')"
      local existing_slides=0
      [ -d "$out_dir" ] && existing_slides="$(find "$out_dir" -maxdepth 1 -name 'slide-*.webp' 2>/dev/null | wc -l | tr -d ' ')"
      if [ -n "$stored_count" ] && [ "$stored_count" -gt 0 ] && [ "$existing_slides" -eq "$stored_count" ] 2>/dev/null; then
        log "  Skipping (unchanged, hash matches, assets present)"
        return
      fi
      log "  Hash matches but assets missing or incomplete, regenerating..."
    else
      log "  PDF changed, regenerating..."
    fi
  fi

  mkdir -p "$metadata_dir"
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

  log "  Processing $page_count slides (single WebP per slide → $out_dir)..."

  # Get dimensions from first page
  local dimensions
  dimensions=$($CONVERT "${page_files[0]}" -format "%wx%h" info:)
  local orig_w orig_h
  orig_w=$(echo "$dimensions" | cut -dx -f1)
  orig_h=$(echo "$dimensions" | cut -dx -f2)

  # Step 2: One high-res WebP per page (cap width at FULL_WIDTH)
  local i=0
  for page_file in "${page_files[@]}"; do
    i=$((i + 1))
    local num
    num=$(printf "%03d" "$i")

    if [ "$orig_w" -gt "$FULL_WIDTH" ]; then
      $CONVERT "$page_file" -resize "${FULL_WIDTH}x" -quality 100 "$tmp_dir/slide.jpg"
    else
      cp "$page_file" "$tmp_dir/slide.jpg"
    fi
    cwebp -q "$WEBP_QUALITY" -quiet "$tmp_dir/slide.jpg" -o "$out_dir/slide-${num}.webp"

    if [ $((i % 10)) -eq 0 ] || [ "$i" -eq "$page_count" ]; then
      log "  $i / $page_count"
    fi
  done

  # Get output dimensions from first generated slide
  local first_webp="$out_dir/slide-001.webp"
  local out_dimensions
  out_dimensions=$($CONVERT "$first_webp" -format "%wx%h" info: 2>/dev/null || echo "0x0")
  local out_w out_h
  out_w=$(echo "$out_dimensions" | cut -dx -f1)
  out_h=$(echo "$out_dimensions" | cut -dx -f2)

  # Step 3: Write metadata.json (in bundle for hash check and page_count)
  cat > "$metadata" <<EOF
{
  "page_count": $page_count,
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "source_pdf": "slides.pdf",
  "source_hash": "sha256:$current_hash",
  "dimensions": { "width": $out_w, "height": $out_h },
  "assets_dir": "assets/slides/$slug"
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

  rm -rf "$tmp_dir"

  ok "  Done: $page_count slides → assets/slides/$slug/ (${out_w}x${out_h})"
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

  local root
  root="$(site_root "$content_dir")"
  local assets_slides_root="$root/assets/slides"
  log "Site root: $root → assets/slides: $assets_slides_root"
  log "Scanning $content_dir for slide PDFs..."
  echo ""

  local found=0
  for bundle_dir in "$content_dir"/*/; do
    [ -d "$bundle_dir" ] || continue
    if [ -f "$bundle_dir/slides.pdf" ]; then
      found=$((found + 1))
      process_pdf "$bundle_dir" "$assets_slides_root"
      echo ""
    fi
  done

  if [ "$found" -eq 0 ]; then
    warn "No slides.pdf files found in $content_dir/*/"
  else
    ok "Processed $found presentation(s). Hugo will resize from assets/slides/<slug>/ at build."
  fi
}

main "$@"
