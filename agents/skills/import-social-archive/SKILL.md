---
name: hugo-techie-import-social-archive
description: Import X/Twitter, LinkedIn, Instagram, or Facebook data takeouts into a hugo-techie-personal site as mirrored page bundles under content/archive/. Handles the draft/publish/auto-publish flow, platform-specific URL-mapping sidecars, exclusion list, and SHA-based idempotent re-imports. Use when the user has a platform data export and wants to mirror or archive their posts on their own domain.
---

# import-social-archive

Import X / Twitter, LinkedIn, Instagram, or Facebook data takeouts into Hugo page bundles under `content/archive/`. Each archived post is published at a URL that mirrors the original (e.g. `/x.com/<user>/status/<id>/`), so pasting the original URL behind the user's domain resolves to the local copy.

## When to use

- *"Import my Twitter takeout."*
- *"Archive my LinkedIn posts on my site."*
- *"Here's my Instagram data export, host it on my domain."*
- *"Mirror my Facebook posts."*

## Prerequisites

- `uv` installed (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`). **Never use `pip` or `pip3`** — workspace rule.
- The takeout zip from each platform:
  - Twitter/X: Settings → Your account → Download an archive of your data.
  - LinkedIn: Settings → Data privacy → Get a copy of your data → "Want something in particular?" → choose Shares + Articles (Pulse) + InstantReposts, or just "Download larger data archive" for everything.
  - Instagram: Settings → Accounts Center → Your information and permissions → Download your information.
  - Facebook: Settings → Accounts Center → Your information and permissions → Download your information.
- Drop zips into `takeouts/` at the site root (gitignored by convention; add if missing).

## Importers

All live in `themes/hugo-techie-personal/scripts/`:

| Platform    | Command |
|-------------|---------|
| Twitter / X | `uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_twitter.py --takeout takeouts/twitter-<date>.zip --user <handle>` |
| LinkedIn    | `uv run --with pyyaml --with beautifulsoup4 --with lxml --with markdownify python3 themes/hugo-techie-personal/scripts/import_linkedin.py --takeout takeouts/linkedin-<date>.zip` |
| Instagram   | `uv run --with pyyaml --with beautifulsoup4 --with lxml python3 themes/hugo-techie-personal/scripts/import_instagram.py --takeout takeouts/instagram-<date>.zip --user <handle>` |
| Facebook    | `uv run --with pyyaml --with beautifulsoup4 --with lxml python3 themes/hugo-techie-personal/scripts/import_facebook.py --takeout takeouts/facebook-<date>.zip --user <handle>` |

## Shared flags

| Flag              | Effect |
|-------------------|--------|
| `--dry-run`       | Report what would change; no files written. |
| `--force`         | Rewrite bundles even if content hash hasn't changed. |
| `--publish`       | New imports default to `draft: false`. Existing bundles untouched. |
| `--auto-publish`  | New imports get `draft: false` only if they look like original impactful content (see policy below). Existing bundles untouched. Mutually exclusive with `--publish`. |
| `--limit N`       | Import only first N posts (useful for quick testing). |

Twitter-specific: `--include-replies`, `--include-retweets` (off by default).

## Recommended workflow

First time on a fresh takeout — use auto-publish with dry-run first to preview:

```sh
uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_twitter.py \
    --takeout takeouts/twitter-2026-04-10.zip --user <handle> \
    --auto-publish --dry-run
```

The output shows `[publish] <id>: <reason>` / `[draft ] <id>: <reason>` for each record. Adjust the policy in `takeouts/auto-publish.yml` (see below) if the split looks wrong, then re-run without `--dry-run`.

```sh
uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_twitter.py \
    --takeout takeouts/twitter-2026-04-10.zip --user <handle> \
    --auto-publish
```

For subsequent re-runs (e.g. to pick up a newer takeout), the SHA-256 manifest in each bundle makes re-imports idempotent — only changed posts are rewritten.

## Auto-publish policy

Summary: a new post auto-publishes if none of these **exclusions** apply and **at least one** signal does:

Exclusions:

- `sensitive: true`
- Twitter reply / retweet
- LinkedIn plain repost (`extra.kind == "repost"`)
- Quote-reshare with < `min_quote_reshare_chars` (default 140) of commentary
- Completely empty post with no media

Signals:

1. LinkedIn Pulse article (always published).
2. Long-form body ≥ `min_longform_chars` (default 280) characters of visible text.
3. Own media + caption ≥ `min_caption_chars` (default 40).
4. Links to the user's own domains (`own_domains`) or GitHub orgs (`own_github_orgs`).

Tune via `takeouts/auto-publish.yml`:

```yaml
min_longform_chars: 280
min_caption_chars: 40
min_quote_reshare_chars: 140
own_domains:
  - yourdomain.com
  - cyfinoid.com
own_github_orgs:
  - your-handle
  - your-org
```

## Excluding specific posts

If a post shouldn't be mirrored (sensitive, personal, unflattering), add its ID to `takeouts/exclude.yml`:

```yaml
twitter:
  - "1987495307735974094"
linkedin:
  - "7448950708240035841"
instagram:
  - "DUjOA_yDeae"
facebook:
  - "pfbid0abc123"
```

Re-run the importer; excluded posts are skipped.

## Platform-specific gotchas

### Instagram URL mirroring

Exports don't include `/p/<shortcode>/` per post. Without a mapping, bundles go to `/www.instagram.com/archive/ts-<timestamp>/` and can only be found via `/archive/`. To enable real URL mirroring, create `takeouts/instagram-shortcode-map.json`:

```json
{
  "posts/202410/abc_1.jpg": "DUjOA_yDeae",
  "1728750000": "DUjOA_yDeae"
}
```

Keys: media path inside the zip, media basename, or `creation_timestamp` as a string. Values: the shortcode.

### Facebook URL mirroring

Same issue. Create `takeouts/facebook-url-map.json`:

```json
{
  "posts/media/abc.jpg": "pfbid0abc123",
  "1728750000": "https://www.facebook.com/permalink.php?story_fbid=12345&id=9876"
}
```

Values: bare post ID or full URL. The importer normalises either.

### LinkedIn quote-reshares

LinkedIn's export omits the parent URN for reshares-with-commentary. To surface a parent post, maintain `takeouts/linkedin-reshare-map.json`:

```json
{
  "ugcPost-7411939790561890304": "https://www.linkedin.com/feed/update/urn:li:activity:7411359639843360768/"
}
```

Keys are `<urn_type_lowercase>-<urn_id>`; values are a feed URL or bare URN.

## Draft workflow

All bundles default to `draft: true`. To publish:

- **Per-post:** open `content/archive/<platform>/<id>/index.md` and flip `draft: false`. Importer preserves manual `draft` values on re-run.
- **Bulk new imports:** use `--publish` or `--auto-publish`.
- **Force an already-imported post back to draft:** edit the file (or delete the bundle and re-import).

## Procedure

1. Ask user which platform(s) they want to import and check the zip(s) are in `takeouts/`.
2. Dry-run with `--auto-publish --dry-run`.
3. Review counts, propose `takeouts/auto-publish.yml` if needed.
4. Real run without `--dry-run`.
5. `hugo server -D` and verify `/archive/` landing page.
6. Note to user: the smart 404 in `layouts/404.html` flattens `:` / `?` / `&` / `=` so users can paste original URLs and still land on the archived copy.

## Helper files

- [`tool-specific-tips.md`](tool-specific-tips.md)

## Common pitfalls

- **Using `pip install` instead of `uv`.** Workspace rule. Always `uv run --with <pkg> python3 …`.
- **Committing `takeouts/`.** It's sensitive data. Verify it's in `.gitignore`; add if missing.
- **Re-running with `--force` unnecessarily.** It rewrites every bundle — expensive and noisy in git diffs. Only use when you change the importer/layout code itself.
- **Running `--publish` and `--auto-publish` together.** Mutually exclusive. Pick one.
