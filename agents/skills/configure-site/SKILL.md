---
name: hugo-techie-configure-site
description: Edit config.toml and content/_index.md to configure a hugo-techie-personal site — title, baseURL, subtitle, profile pic, social links, analytics, menus, taxonomies, output formats. Use when the user wants to change site-level settings, hook up analytics, add menu items, or fix the common "social links don't appear" gotcha (they live in content/_index.md frontmatter, not config.toml).
---

# configure-site

Edit `config.toml` and `content/_index.md` to configure the most common site-level settings: identity, menus, social links, analytics, taxonomies, output formats.

## When to use

- *"Change my site title."*
- *"Hook up Plausible / Google Analytics."*
- *"Add a menu item."*
- *"Set my profile pic / banner."*
- *"Where do the social icons on my home page come from?"*

## Where things live

**Important:** this theme splits configuration between `config.toml` and `content/_index.md`. Get this wrong and things render blank with no error.

| Thing                          | File                 | Key |
|--------------------------------|----------------------|-----|
| Site title, baseURL            | `config.toml`        | `title`, `baseURL` |
| Subtitle, description, footer  | `config.toml`        | `[params] subtitle`, `description`, `footer` |
| Profile pic                    | `config.toml`        | `[params] profile_pic` (relative to `assets/`) |
| Site-wide banner               | `config.toml`        | `[params] Banner` (capital B!) |
| Menu entries                   | `config.toml`        | `[[menu.main]]` blocks |
| Taxonomies                     | `config.toml`        | `[taxonomies]` |
| Output formats (OEmbed, Embed, SlidesJSON, LocationsJSON) | `config.toml` | `[outputFormats.*]` + `[outputs] home` |
| Analytics                      | `config.toml`        | `[params.analytics]` |
| Notist custom domains          | `config.toml`        | `[params] notist_username`, `notist_custom_domains` |
| Badge platform usernames       | `config.toml`        | `[params] credly_username`, etc. See `../set-up-badges/`. |
| **Home page social icons**     | **`content/_index.md`** | `social_links:` in **frontmatter**, not `config.toml` |

## Bootstrapping `config.toml`

Start from the example: `cp themes/hugo-techie-personal/exampleSite/config.toml .` (the `bootstrap-portfolio` skill does this). Then edit:

```toml
baseURL = "https://yourdomain.com"        # must be correct for oembed of self-hosted slides to work at build time
defaultContentLanguage = "en"
title = "Your Name"
theme = "hugo-techie-personal"
enableRobotsTXT = true

[taxonomies]
  types = "type"
  focus = "focus"
  activities = "activity"

[params]
  subtitle = "Your tagline"
  description = "Site-wide description for meta tags and SEO"
  footer = "&copy; [Your Name](https://yourdomain.com)"
  profile_pic = "images/profile.png"
  home_layout = "home-layout-50-50"
  # Banner = "<a href='#'>Optional site-wide banner message</a>"
```

The required output formats (so slides, OEmbed, and the map work) must be present; copy them verbatim from `exampleSite/config.toml`:

```toml
[mediaTypes."application/json+oembed"]
  suffixes = ["json"]

[outputFormats.OEmbed]
  mediaType = "application/json+oembed"
  baseName = "oembed"
  isPlainText = true
  notAlternative = true

[outputFormats.Embed]
  mediaType = "text/html"
  baseName = "embed"
  isPlainText = false
  notAlternative = true

[outputFormats.SlidesJSON]
  mediaType = "application/json"
  baseName = "slides"
  isPlainText = true
  notAlternative = true

[outputFormats.LocationsJSON]
  mediaType = "application/json"
  baseName = "locations"
  isPlainText = true
  notAlternative = true

[outputs]
  home = ["HTML", "RSS", "SlidesJSON", "LocationsJSON"]
```

## Social links (home page)

In `content/_index.md` frontmatter:

```yaml
---
title: "Your Name"
social_links:
  github: "https://github.com/handle"
  linkedin: "https://linkedin.com/in/handle"
  twitter: "https://x.com/handle"
  mastodon: "https://infosec.exchange/@handle"
  bluesky: "https://bsky.app/profile/handle.bsky.social"
  email: "mailto:you@example.com"
  # rel="me" verification (hidden links; platform picks them up for verification checkmarks)
  verify_1: "https://mastodon.social/@handle"
  verify_2: "https://infosec.exchange/@handle"
---
```

Keys are `<platform>` or `<platform>_url`. Keys ending in `verify` / `verify_N` produce hidden `rel="me"` links.

## Analytics

```toml
# Plausible (self-hosted behind nginx proxy)
[params.analytics]
  provider = "plausible"
  domain = "yourdomain.com"
  api_endpoint = "/api/event"
  script_src = "/js/script.js"

# OR Plausible Cloud
[params.analytics]
  provider = "plausible_cloud"
  domain = "yourdomain.com"

# OR Google Analytics
[params.analytics]
  provider = "google"
  tracking_id = "G-XXXXXXXXXX"

# OR custom
[params.analytics]
  provider = "custom"
  custom_code = '''<script>/* your snippet */</script>'''
```

## Menus

```toml
[[menu.main]]
  name = "Timeline"
  url = "/timeline/"
  weight = 2

[[menu.main]]
  name = "Projects"
  url = "/projects/"
  weight = 4
```

Set `weight` to control order (lower = earlier). See the `exampleSite/config.toml` for a complete menu.

## Full reference

See [`../../../docs/configuration.md`](../../../docs/configuration.md) for the complete list, and [`../../../docs/layouts.md`](../../../docs/layouts.md) for layout-specific config (bio, map, etc.).

## Helper files

- [`tool-specific-tips.md`](tool-specific-tips.md)

## Common pitfalls

- **Putting social links in `config.toml`.** They go in `content/_index.md` frontmatter. Putting them in `config.toml` silently does nothing.
- **Forgetting to update `baseURL`.** The self-hosted slide oembed uses this at build time. If `baseURL = "https://example.com"`, `{{% oembed url="https://example.com/slides/X/" %}}` will try to fetch the literal `example.com` at build time.
- **Removing one of the output formats.** If you drop `OEmbed` or `Embed`, slide pages stop generating their iframe/oembed variants. Don't prune.
- **Lowercase `banner`.** The param is `Banner` (capital B). Lowercase `banner` is ignored.
