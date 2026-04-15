# Page Layouts

The theme provides several page layouts beyond the standard Hugo `single` and `list` templates.

## Bio Page

A structured biography page with copy-to-clipboard functionality, multiple format views (rendered HTML, Markdown source, plain text), and a downloadable photos section.

**Usage:** Set `layout: bio` in your page frontmatter.

```yaml
---
title: "Biography"
layout: bio
subtitle: "Your Professional Title"
short_bio: |
  A concise one-paragraph biography suitable for conference programs
  and speaker introductions. Supports **Markdown** formatting.
long_bio: |
  A detailed multi-paragraph biography covering your career history,
  expertise, and achievements. Supports **Markdown** formatting.

  Second paragraph with more detail.
photos:
  - file: "images/bio/headshot-formal.jpg"
    label: "Formal Headshot"
  - file: "images/bio/headshot-casual.jpg"
    label: "Casual Photo"
---

Optional additional content rendered below the biography sections.
```

### Features

- **Tab views**: Each bio section has Rendered / Markdown / Plain Text tabs
- **Copy button**: One-click copy of the currently visible format
- **Photos section**: Automatically generates Thumb, Medium, Large, and Original download links for each photo via Hugo image processing
- **Markdown body**: Any content in the page body renders below the bio sections

### Photo assets

Place photo files in your site's `assets/` directory (e.g., `assets/images/bio/headshot.jpg`). The template uses `resources.Get` to access them. Supported formats: JPG, PNG, WebP.

---

## Map Page

A standalone page showing all physical event locations on a Leaflet map. Combines locations from both the slides/presentations section and timeline entries.

**Usage:** Set `layout: map` in your page frontmatter.

```yaml
---
title: "Events Map"
layout: map
map_height: "60vh"
map_zoom: 3
---

Optional introductory text shown above the map.
```

### Frontmatter

| Field | Default | Description |
|-------|---------|-------------|
| `map_height` | `60vh` | CSS height for the map container |
| `map_zoom` | Site config default (usually `2`) | Initial zoom level |

### Requirements

- `params.slides.map.enabled` must be `true` in `config.toml`
- The home page must output `LocationsJSON` format (produces `locations.json`)
- Timeline and slide entries must have `location.latitude` and `location.longitude` set
- Entries with `online: true` are excluded from the map

### Menu entry

Add a menu item in `config.toml`:

```toml
[[menu.main]]
  name = "Map"
  url = "/map/"
  weight = 8
```

---

## Home Page

The home page uses a split layout with profile image and content.

### Configuration

```toml
[params]
  home_layout = "home-layout-50-50"  # CSS class for layout (default)
  profile_pic = "images/profile.png" # Path under assets/
```

### Dynamic content

The home page content supports a `YEARS_EXPERIENCE+` placeholder that is automatically replaced with the number of years since 2008 (calculated at build time).

### Social links

Social links are defined in the home page frontmatter (`content/_index.md`), not in `config.toml`:

```yaml
social_links:
  twitter: https://twitter.com/username
  github: https://github.com/username
  linkedin: https://linkedin.com/in/username
  mastodon: https://mastodon.social/@username
  email: mailto:you@example.com
  fediverse: https://infosec.exchange/@username
  verify_1: https://mastodon.social/@username    # rel="me" verification links
  verify_2: https://infosec.exchange/@username
```

Keys ending in `verify` become hidden `rel="me"` verification links. The platform name is extracted from the key before the first underscore (e.g., `twitter_url` → `twitter`).

---

## Alternate List Layouts

Several alternate list layouts are available for sections:

| Layout | Description |
|--------|-------------|
| `list` | Default chronological list with activity icons |
| `mosaic` | Grid-based card layout with excerpts and OEmbed |
| `category` | Groups entries by focus area |
| `priority` | Groups entries by priority focus areas |

Set via frontmatter in `_index.md`:

```yaml
layout: mosaic
```

Or in `config.toml` for section defaults.

---

## Banner

Display a site-wide banner below the header. Set in `config.toml`:

```toml
[params]
  Banner = "Your banner message with **Markdown** support"
```

> **Note:** The parameter name is `Banner` (capital B) in the template.
