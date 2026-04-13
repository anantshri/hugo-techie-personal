#!/bin/bash
# process-slides.sh — Convert slide PDFs to single high-res WebP per slide
#
# Reads PDFs from the inbox at assets/slides/pdf_files/<slug>.pdf
# Outputs one WebP per slide to assets/slides/<slug>/
# Copies PDF to static/slides/<slug>/slides.pdf for download serving
# Writes metadata.json in content bundle's slides/ for hash check and page_count
#
# Hugo's image processing (resources.Get + Resize) generates
# thumb/medium/full at build time with quality 100.
#
# Dependencies: poppler-utils (pdftoppm), libwebp (cwebp), imagemagick (magick/convert)
# Usage: ./themes/hugo-techie-personal/scripts/process-slides.sh
#
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

# ---- Resolve site root ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---- Process a single PDF ----
process_pdf() {
  local pdf_path="$1"
  local site_root="$2"
  local slug="$3"

  local content_dir="$site_root/content/slides/$slug"
  local metadata_dir="$content_dir/slides"
  local metadata="$metadata_dir/metadata.json"
  local assets_out="$site_root/assets/slides/$slug"
  local static_out="$site_root/static/slides/$slug"

  # Require content page to exist (run scaffold-slides.sh first)
  if [ ! -f "$content_dir/index.md" ]; then
    warn "No content page for '$slug'. Run scaffold-slides.sh first."
    return
  fi

  log "Found: $pdf_path (slug: $slug)"

  local current_hash
  current_hash="$(file_hash "$pdf_path")"

  # Check if already processed (compare hash)
  if [ -f "$metadata" ]; then
    local stored_hash
    stored_hash="$(grep -o '"source_hash"[[:space:]]*:[[:space:]]*"sha256:[^"]*"' "$metadata" 2>/dev/null | sed 's/.*sha256://' | tr -d '"')"
    if [ "$stored_hash" = "$current_hash" ]; then
      local stored_count
      stored_count="$(grep -o '"page_count"[[:space:]]*:[[:space:]]*[0-9]*' "$metadata" 2>/dev/null | grep -o '[0-9]*$' | tr -d ' ')"
      local existing_slides=0
      [ -d "$assets_out" ] && existing_slides="$(find "$assets_out" -maxdepth 1 -name 'slide-*.webp' 2>/dev/null | wc -l | tr -d ' ')"
      local static_pdf_exists=0
      [ -f "$static_out/slides.pdf" ] && static_pdf_exists=1
      if [ -n "$stored_count" ] && [ "$stored_count" -gt 0 ] && [ "$existing_slides" -eq "$stored_count" ] && [ "$static_pdf_exists" -eq 1 ] 2>/dev/null; then
        log "  Skipping (unchanged, hash matches, assets + static PDF present)"
        return
      fi
      log "  Hash matches but assets/static PDF missing or incomplete, regenerating..."
    else
      log "  PDF changed, regenerating..."
    fi
  fi

  mkdir -p "$metadata_dir"
  mkdir -p "$assets_out"

  # Copy PDF to static/ for download serving
  mkdir -p "$static_out"
  cp "$pdf_path" "$static_out/slides.pdf"
  log "  Copied PDF → static/slides/$slug/slides.pdf"

  # Step 1: Extract pages as high-res JPEG using pdftoppm
  local tmp_dir
  tmp_dir="$(mktemp -d)"
  log "  Extracting pages at ${DPI}dpi..."
  pdftoppm -jpeg -r "$DPI" "$pdf_path" "$tmp_dir/page"

  local page_files
  page_files=("$tmp_dir"/page-*.jpg)
  local page_count=${#page_files[@]}

  if [ "$page_count" -eq 0 ]; then
    err "  No pages extracted from $pdf_path"
    rm -rf "$tmp_dir"
    return
  fi

  log "  Processing $page_count slides (single WebP per slide → assets/slides/$slug/)..."

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
    cwebp -q "$WEBP_QUALITY" -quiet "$tmp_dir/slide.jpg" -o "$assets_out/slide-${num}.webp"

    if [ $((i % 10)) -eq 0 ] || [ "$i" -eq "$page_count" ]; then
      log "  $i / $page_count"
    fi
  done

  local first_webp="$assets_out/slide-001.webp"
  local out_dimensions
  out_dimensions=$($CONVERT "$first_webp" -format "%wx%h" info: 2>/dev/null || echo "0x0")
  local out_w out_h
  out_w=$(echo "$out_dimensions" | cut -dx -f1)
  out_h=$(echo "$out_dimensions" | cut -dx -f2)

  # Step 3: Write metadata.json
  cat > "$metadata" <<EOF
{
  "page_count": $page_count,
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "source_pdf": "$slug.pdf",
  "source_hash": "sha256:$current_hash",
  "dimensions": { "width": $out_w, "height": $out_h },
  "assets_dir": "assets/slides/$slug",
  "static_pdf": "static/slides/$slug/slides.pdf"
}
EOF

  # Step 4: Update page_count in index.md frontmatter if present
  local index_md="$content_dir/index.md"
  if [ -f "$index_md" ]; then
    if grep -q "page_count:" "$index_md"; then
      sed -i.bak "s/page_count:.*/page_count: $page_count/" "$index_md"
      rm -f "$index_md.bak"
      log "  Updated page_count in index.md"
    fi
  fi

  rm -rf "$tmp_dir"

  ok "  Done: $page_count slides → assets/slides/$slug/ (${out_w}x${out_h})"
  ok "        PDF download → static/slides/$slug/slides.pdf"
}

# ---- Main ----
main() {
  check_deps

  local site_root
  site_root="$(cd "$SCRIPT_DIR/../../.." && pwd)"

  local inbox="$site_root/assets/slides/pdf_files"

  if [ ! -d "$inbox" ]; then
    err "PDF inbox not found: $inbox"
    err "Create it with: mkdir -p assets/slides/pdf_files"
    exit 2
  fi

  log "Site root: $site_root"
  log "Scanning inbox: assets/slides/pdf_files/"
  echo ""

  local found=0
  for pdf_path in "$inbox"/*.pdf; do
    [ -f "$pdf_path" ] || continue
    local filename
    filename="$(basename "$pdf_path")"
    local slug="${filename%.pdf}"
    found=$((found + 1))
    process_pdf "$pdf_path" "$site_root" "$slug"
    echo ""
  done

  if [ "$found" -eq 0 ]; then
    warn "No PDF files found in assets/slides/pdf_files/"
  else
    ok "Processed $found presentation(s)."
    ok "  Slide images: assets/slides/<slug>/"
    ok "  PDF downloads: static/slides/<slug>/slides.pdf"
    ok "  Hugo will resize from assets at build time."
  fi
}

main "$@"
