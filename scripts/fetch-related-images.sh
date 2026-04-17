#!/usr/bin/env bash
#
# fetch-related-images.sh
# Downloads OG images for related_links in timeline entries and saves them to
# <site>/assets/images/related-links/ with a deterministic slug name. The slug
# matches what the Hugo partial generates so images are found at build time.
#
# Shipped with the hugo-techie-personal theme.
#
# Usage:
#   ./themes/hugo-techie-personal/scripts/fetch-related-images.sh
#
# Site-root resolution (first match wins):
#   1. HUGO_SITE_ROOT env var, if set
#   2. <script>/../../..  (conventional theme layout)
#   3. $PWD fallback
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -n "${HUGO_SITE_ROOT:-}" ] && [ -d "$HUGO_SITE_ROOT" ]; then
  SITE_ROOT="$(cd "$HUGO_SITE_ROOT" && pwd)"
elif [ -d "$SCRIPT_DIR/../../../content" ] \
  || [ -f "$SCRIPT_DIR/../../../hugo.toml" ] \
  || [ -f "$SCRIPT_DIR/../../../config.toml" ]; then
  SITE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
else
  SITE_ROOT="$(pwd)"
fi

ASSETS_DIR="$SITE_ROOT/assets/images/related-links"
CONTENT_DIR="$SITE_ROOT/content/timeline"

mkdir -p "$ASSETS_DIR"

url_to_slug() {
  echo "$1" \
    | sed 's|https\{0,1\}://||' \
    | sed 's|?.*||; s|#.*||' \
    | sed 's|[^a-zA-Z0-9]|-|g' \
    | sed 's|-\{2,\}|-|g' \
    | sed 's|^-||; s|-$||'
}

detect_ext() {
  local url="$1"
  case "$url" in
    *.png|*.png\?*|*.png\#*) echo "png" ;;
    *.jpg|*.jpg\?*|*.jpg\#*|*.jpeg|*.jpeg\?*) echo "jpg" ;;
    *.webp|*.webp\?*) echo "webp" ;;
    *.gif|*.gif\?*) echo "gif" ;;
    *.svg|*.svg\?*) echo "svg" ;;
    *)
      local ct
      ct=$(curl -sI -L --max-time 15 "$url" 2>/dev/null | tr -d '\r' | grep -i '^content-type:' | tail -1 || true)
      case "$ct" in
        *png*)  echo "png" ;;
        *jpeg*|*jpg*) echo "jpg" ;;
        *webp*) echo "webp" ;;
        *gif*)  echo "gif" ;;
        *svg*)  echo "svg" ;;
        *)      echo "jpg" ;;
      esac
      ;;
  esac
}

process_url() {
  local url="$1"
  local slug
  slug=$(url_to_slug "$url")

  # Already downloaded?
  if compgen -G "$ASSETS_DIR/$slug."* > /dev/null 2>&1; then
    echo "  ✓ Cached: $slug"
    return
  fi

  echo "  Fetching page: $url"

  # Skip non-HTML URLs (PDFs, images, etc.)
  local ct_header
  ct_header=$(curl -sI -L --max-time 15 "$url" 2>/dev/null | tr -d '\r' | grep -i '^content-type:' | tail -1 || true)
  if [ -n "$ct_header" ] && ! echo "$ct_header" | grep -qi 'text/html'; then
    echo "  ⚠  Skipping non-HTML content (${ct_header#*: })"
    return
  fi

  local html
  html=$(curl -sL --max-time 30 "$url" 2>/dev/null) || { echo "  ✗ Failed to fetch page"; return; }

  local og_image
  og_image=$(echo "$html" | sed -n 's/.*<meta[^>]*property="og:image"[^>]*content="\([^"]*\)".*/\1/p' | head -1)

  if [ -z "$og_image" ]; then
    echo "  ⚠  No og:image found"
    return
  fi

  # Decode HTML entities
  og_image=$(echo "$og_image" | sed 's/&amp;/\&/g; s/&#038;/\&/g; s/&#0*38;/\&/g')

  local ext
  ext=$(detect_ext "$og_image")

  local target="$ASSETS_DIR/${slug}.${ext}"
  echo "  Downloading image..."
  curl -sL --max-time 30 -o "$target" "$og_image" 2>/dev/null

  if [ -f "$target" ] && [ -s "$target" ]; then
    # Verify the download is actually an image
    local actual_type
    actual_type=$(file -b --mime-type "$target" 2>/dev/null || true)
    if ! echo "$actual_type" | grep -q '^image/'; then
      rm -f "$target"
      echo "  ✗ Downloaded file is not an image ($actual_type), removed"
      return
    fi
    # Correct extension if actual format differs from guessed one
    local actual_ext=""
    case "$actual_type" in
      image/webp) actual_ext="webp" ;;
      image/png)  actual_ext="png" ;;
      image/jpeg) actual_ext="jpg" ;;
      image/gif)  actual_ext="gif" ;;
      image/svg*) actual_ext="svg" ;;
    esac
    if [ -n "$actual_ext" ] && [ "$actual_ext" != "$ext" ]; then
      local corrected="$ASSETS_DIR/${slug}.${actual_ext}"
      mv "$target" "$corrected"
      echo "  ⚠  Corrected extension: .${ext} → .${actual_ext}"
      target="$corrected"
    fi
    echo "  ✓ Saved: $target"
  else
    rm -f "$target"
    echo "  ✗ Failed to download image"
  fi
}

echo "Scanning $CONTENT_DIR for related_links..."
echo ""

for file in "$CONTENT_DIR"/*.md; do
  in_frontmatter=false
  in_related=false

  while IFS= read -r line; do
    if [ "$line" = "---" ]; then
      if $in_frontmatter; then
        break
      fi
      in_frontmatter=true
      continue
    fi

    $in_frontmatter || continue

    if echo "$line" | grep -q '^related_links:'; then
      in_related=true
      continue
    fi

    if $in_related; then
      local_url=""
      if echo "$line" | grep -qE '^\s+-\s+url:\s*'; then
        local_url=$(echo "$line" | sed 's/.*url: *"\{0,1\}//; s/"\{0,1\} *$//')
      elif ! echo "$line" | grep -qE '^\s'; then
        in_related=false
        continue
      else
        continue
      fi

      if [ -n "$local_url" ]; then
        echo "$(basename "$file"):"
        process_url "$local_url"
        echo ""
      fi
    fi
  done < "$file"
done

echo "Done. Images saved to $ASSETS_DIR/"