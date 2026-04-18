---
name: hugo-techie-set-up-badges
description: Configure professional badges (Credly, Accredible, Badgr, Bugcrowd, HackerOne, Open Badges, or manual) on a hugo-techie-personal site. Adds config.toml keys, creates a /badges/ page with the {{< badges >}} shortcode, and handles the Badgr API-token secret-management gotcha. Use when the user wants to display certifications, add a badges page, or hook up a credentialing platform.
---

# set-up-badges

Configure professional badges (Credly, Accredible, Bugcrowd, HackerOne, Badgr, Open Badges, manual) and add them to a `/badges/` page (or any page the user wants).

## When to use

- *"Set up my Credly badges."*
- *"Show my HackerOne / Bugcrowd badges."*
- *"Add a badges page."*
- *"I have an Open Badges JSON file, put it on my site."*

## Supported platforms

| Platform | Config keys | Data source |
|----------|-------------|-------------|
| Credly | `credly_username`, `credly_image_dir` | Public Credly API |
| Accredible | `accredible_username`, `accredible_image_dir` | Public Accredible API |
| Badgr | `badgr_username`, `badgr_api_token`, `badgr_image_dir` | Badgr API (token required) |
| Bugcrowd | `bugcrowd_username`, `bugcrowd_image_dir` | Public Bugcrowd profile |
| HackerOne | `hackerone_username`, `hackerone_image_dir` | Public HackerOne `/badges.json` |
| Open Badges | `data/OpenBadges.json` | user-provided JSON-LD |
| Manual | `data/ManualBadges.json` | user-provided JSON |

All platforms follow the same flow:

1. Add the config keys to `config.toml`.
2. Add the shortcode to a page.
3. Build — the theme fetches the API and caches images locally.

## Procedure per platform

### Credly

```toml
[params]
  credly_username = "your-handle"
  credly_image_dir = "images/CredlyBadges"   # default; leave as-is unless you want a different cache dir
```

Shortcode on the badges page: `{{< credly-badges >}}`. Filters: `size="small"`, `hide_expired="true"`, `show_expired="true"`.

### Accredible

```toml
[params]
  accredible_username = "your-handle"
  accredible_image_dir = "images/AccredibleBadges"
```

Shortcode: `{{< accredible-badges >}}`.

### Badgr

Requires an API token from Badgr.io:

```toml
[params]
  badgr_username = "your-handle"
  badgr_api_token = "xxxxxxxxxxxxxxxxxxx"
  badgr_image_dir = "images/BadgrBadges"
```

Shortcode: `{{< badgr-badges >}}`.

⚠️ The API token is a secret. Don't commit `config.toml` with a live token to a public repo. Options:

- Keep `badgr_api_token = ""` in the committed config and set it via environment variable on the build server.
- Use a `config.private.toml` (gitignored) that Hugo merges via `--configDir`.

Ask the user how they want to handle secrets before writing the token to disk.

### Bugcrowd

```toml
[params]
  bugcrowd_username = "your-handle"
  bugcrowd_image_dir = "images/BugcrowdBadges"
```

Shortcode: `{{< bugcrowd-badges >}}`. By default shows only awarded badges; statistics/hall-of-fame are fetched but hidden unless `show_statistics="true"` / `show_hall_of_fame="true"` is passed.

### HackerOne

```toml
[params]
  hackerone_username = "your-handle"
  hackerone_image_dir = "images/HackerOneBadges"
```

Shortcode: `{{< hackerone-badges >}}`.

### Open Badges (JSON-LD)

The user provides a JSON-LD file of Open Badges Assertions. Save to `data/OpenBadges.json`:

```json
{
  "badges": [
    {
      "@context": "https://w3id.org/openbadges/v2",
      "type": "Assertion",
      "id": "https://example.com/badges/badge-1",
      "badge": {
        "type": "BadgeClass",
        "name": "Badge Name",
        "description": "Badge description",
        "image": "https://example.com/badge-image.png"
      },
      "issuedOn": "2024-01-15T00:00:00Z",
      "url": "https://example.com/badge-link"
    }
  ]
}
```

Shortcode: `{{< openbadges-badges >}}`.

### Manual badges

For one-offs not covered by any platform, `data/ManualBadges.json`:

```json
{
  "badges": [
    {
      "id": "custom-1",
      "name": "Custom Badge Name",
      "description": "Description",
      "image_url": "https://example.com/badge.png",
      "issued_at": "2024-01-15T00:00:00Z",
      "expires_at": "2025-01-15T00:00:00Z",
      "url": "https://example.com/badge-link"
    }
  ]
}
```

Shortcode: `{{< manual-badges >}}`.

## Creating the `/badges/` page

Write `content/badges.md`:

```markdown
---
title: "Professional Badges"
---

{{< badges >}}
```

`{{< badges >}}` shows all configured platforms in one grid. To restrict:

```markdown
{{< badges show_accredible="false" show_badgr="false" >}}
```

Flags: `show_credly`, `show_accredible`, `show_badgr`, `show_bugcrowd`, `show_hackerone`, `show_openbadges`, `show_manual`, plus `size="small"` / `hide_expired="true"`.

Add a menu entry in `config.toml`:

```toml
[[menu.main]]
  name = "Badges"
  url = "/badges/"
  weight = 6
```

## Procedure

1. Ask which platforms the user is on (show the table above).
2. For each: add the config keys. Ask for the API token up front for Badgr.
3. Create `content/badges.md` with `{{< badges >}}` (or specific shortcodes if the user wants to split platforms across multiple pages).
4. Add the menu entry.
5. Run `hugo server -D`. On first build, the theme calls the platform APIs and caches images under `static/<*_image_dir>/`. Commit that directory if the user wants builds to work offline afterward.
6. Verify each platform's badges render; check for expired badges and offer `hide_expired="true"` if the user wants them gone.

## Helper files

- [`tool-specific-tips.md`](tool-specific-tips.md)

## Common pitfalls

- **Badgr token committed to a public repo.** Tell the user; offer the env-var / private-config path.
- **Empty username.** If a platform has an empty `*_username`, the shortcode renders nothing silently — not an error. Check before blaming the theme.
- **Rate limits.** On first build, each API is hit once per badge. If the user has many badges the first `hugo` run takes 5–30s; subsequent builds use the local cache.
- **Using `{{< badges >}}` without any configured platform.** Renders an empty grid. Not fatal, just useless.
