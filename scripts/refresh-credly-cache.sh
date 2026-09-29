#!/usr/bin/env bash
#
# refresh-credly-cache.sh
# Fetches the public Credly badges feed and refreshes the on-disk fallback
# <site>/data/CredlyBadges.json used by the credly-badges partial when the
# Credly API is unreachable at Hugo build time. The partial reads this file
# via Hugo's Site.Data, so keeping it current means API outages during a
# deploy no longer resurrect months-old badge data.
#
# Shipped with the hugo-techie-personal theme.
#
# Usage:
#   ./themes/hugo-techie-personal/scripts/refresh-credly-cache.sh [username]
#
# The username defaults to the credly_username set in <site>/config.toml.
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

USERNAME="${1:-}"
if [ -z "$USERNAME" ]; then
  CONFIG="$SITE_ROOT/config.toml"
  if [ ! -f "$CONFIG" ]; then
    CONFIG="$SITE_ROOT/hugo.toml"
  fi
  if [ -f "$CONFIG" ]; then
    USERNAME="$(sed -n 's/^[[:space:]]*credly_username[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$CONFIG" | head -1)"
  fi
fi

if [ -z "$USERNAME" ]; then
  echo "error: no credly_username found in config and none given as argument" >&2
  echo "usage: $0 [credly-username]" >&2
  exit 1
fi

DATA_DIR="$SITE_ROOT/data"
TARGET="$DATA_DIR/CredlyBadges.json"
URL="https://www.credly.com/users/${USERNAME}/badges.json"

mkdir -p "$DATA_DIR"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

echo "Fetching $URL"
if ! curl -fsSL "$URL" -o "$TMP"; then
  echo "error: fetch failed - existing $TARGET left untouched" >&2
  exit 1
fi

if ! python3 - "$TMP" <<'EOF'
import json, sys
try:
    data = json.load(open(sys.argv[1]))
except Exception as exc:
    print(f"error: response is not valid JSON: {exc}", file=sys.stderr)
    sys.exit(1)
badges = data.get("data") if isinstance(data, dict) else data
if not badges:
    print("error: response contains no badges - refusing to overwrite", file=sys.stderr)
    sys.exit(1)
print(f"fetched {len(badges)} badge(s)")
EOF
then
  echo "error: validation failed - existing $TARGET left untouched" >&2
  exit 1
fi

mv "$TMP" "$TARGET"
trap - EXIT
echo "Refreshed $TARGET (Credly fallback cache for user '$USERNAME')"
