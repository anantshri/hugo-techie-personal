# Shortcodes Reference

Complete reference for all shortcodes provided by the theme.

## oembed

Embed external content (videos, slides, social posts) via OEmbed protocol.

```hugo
{{% oembed url="https://www.youtube.com/watch?v=VIDEO_ID" %}}
{{% oembed url="https://vimeo.com/VIDEO_ID" %}}
{{% oembed url="https://anantshri.info/slides/presentation-slug/" %}}
```

**Resolution order:**
1. Data-driven providers (`data/oembed.json`)
2. Same-site slides (renders iframe directly without remote fetch)
3. OEmbed discovery (fetches page, reads `<link>` discovery tag)
4. Noti.st custom domains (if configured)
5. Fallback: styled link to the URL

**Note:** Always use the full absolute URL (`https://...`) for OEmbed. Relative URLs and `localhost` will not work since Hugo's `resources.GetRemote` cannot fetch from itself during build.

---

## notice

Styled callout/admonition boxes.

```hugo
{{< notice info "Optional Title" >}}
Content supporting **Markdown** formatting.
{{< /notice >}}
```

**Types:** `warning` (red), `info` (orange), `tip` (green), `note` (blue, default)

---

## fontawesome

Inline SVG icon from FontAwesome.

```hugo
{{< fontawesome "heart" >}} Love this!
```

Requires SVG files in `static/fontawesome/` (e.g., `heart.svg`).

---

## slideviewer

Embed the full interactive slide viewer from a slides page. **Theme-internal use only** — in content files, use the `oembed` shortcode instead.

```hugo
{{< slideviewer src="/slides/presentation-slug/" >}}
```

---

## slide-embed

Render a card-style link to a slides page.

```hugo
{{< slide-embed src="/slides/presentation-slug/" >}}
```

---

## ai-summary-disclaimer

Display an AI-generated content disclaimer notice.

```hugo
{{< ai-summary-disclaimer >}}
```

> **Note:** AI summaries stored in `ai_summary/` are automatically included by templates with the disclaimer. This shortcode is only needed for manually placed disclaimers.

---

## support-buttons

Display sponsor / support buttons. Each platform is opt-in via `[params.sponsors]`
in `config.toml` (FUNDING.yml-style schema). The shortcode is a thin wrapper
around the `support-buttons.html` partial — both render nothing when no
platforms are configured.

```hugo
{{< support-buttons >}}
```

```toml
# config.toml
[params.sponsors]
  github = "your-username"            # https://github.com/sponsors/<user>
  buy_me_a_coffee = "your-username"   # https://www.buymeacoffee.com/<user>
  patreon = "your-username"           # https://www.patreon.com/<user>
  ko_fi = "your-username"             # https://ko-fi.com/<user>
  liberapay = "your-username"         # https://liberapay.com/<user>/
  open_collective = "your-collective" # https://opencollective.com/<slug>
  tidelift = "platform/package"       # https://tidelift.com/funding/github/<value>
  polar = "your-username"             # https://polar.sh/<user>
  thanks_dev = "your-username"        # https://thanks.dev/u/gh/<user>
  custom = ["https://example.com/donate"]  # arbitrary URLs
```

The same set of buttons can also be surfaced in three other places, controlled
by additional toggles:

| Toggle                                | Default | Effect                                                  |
|---------------------------------------|---------|---------------------------------------------------------|
| `params.home.show_social`             | `true`  | Show social icons on the homepage                       |
| `params.home.show_sponsor`            | `true`  | Show sponsor buttons under the social icons on the home |
| `params.sponsors.show_on_projects`    | `true`  | Show sponsor buttons above the projects listing         |
| `params.sponsors.show_as_banner`      | `false` | Render a sticky strip just below the menu on every page |
| `params.sponsors.banner_label`        | `"Support my work"` | Optional prefix label for the sticky banner |

The two homepage toggles can also be set per-page via frontmatter
(`show_social: false` / `show_sponsor: false` in `content/_index.md`),
which takes precedence over the site-wide values.

---

## talks-map

Embed a Leaflet map showing event locations inline.

```hugo
{{< talks-map >}}
```

The map reads data from `slides.json` by default.

---

## badges

Display professional badges from all configured platforms.

```hugo
{{< badges >}}
{{< badges show_accredible="false" size="small" hide_expired="true" >}}
```

### Platform-specific shortcodes

```hugo
{{< credly-badges >}}
{{< accredible-badges >}}
{{< bugcrowd-badges >}}
{{< hackerone-badges >}}
{{< badgr-badges >}}
{{< openbadges-badges >}}
{{< manual-badges >}}
```

---

## img

Basic image shortcode.

```hugo
{{< img src="image.jpg" alt="Description" >}}
```

## article-img

Image shortcode for article content with root-relative path fallback.

```hugo
{{< article-img src="images/photo.jpg" alt="Description" >}}
```
