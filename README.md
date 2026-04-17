# Hugo Techie Personal

A timeline-based personal site theme designed specifically for tech professionals who love to share their work, projects, and journey with the community.

[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](CHANGELOG.md)
[![Hugo](https://img.shields.io/badge/hugo-0.158.0+-blue.svg)](https://gohugo.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

✨ **Timeline-based content organization** - Perfect for showcasing your professional journey  
🎯 **Activity categorization** - Organize content by talks, tools, articles, training, and more  
🎬 **Self-hosted slides/presentations** - PDF slide viewer with keyboard/touch navigation, OEmbed, and embeddable iframes  
🗺️ **Events map** - Leaflet-based map showing physical event locations from talks and presentations  
🏆 **Professional badge integration** - Display Credly and Accredible certifications with API integration  
📱 **Responsive design** - Mobile-first approach with modern CSS Grid and Flexbox  
🔧 **Highly configurable** - Extensive customization options via config.toml  
🎨 **Notice system** - Beautiful callout boxes for important information  
🔗 **OEmbed support** - Embed YouTube, Vimeo, Twitter, and more  
💬 **Social chatter** - Embed social media posts (Twitter/X, Bluesky, Mastodon, LinkedIn) on timeline pages  
🗄️ **Social archive** - Import X/Twitter, LinkedIn, Instagram, and Facebook takeouts into local page bundles served at mirrored URLs  
🌐 **Social integration** - Built-in social media links with verification support  
📊 **Analytics ready** - Supports Plausible, Google Analytics, and custom solutions  
♿ **Accessible** - Semantic HTML5 with proper ARIA labels  
🚀 **Performance optimized** - Minimal CSS, lazy loading, and optimized assets

## Perfect For

- **Tech professionals** building their personal brand
- **Certified professionals** showcasing credentials and achievements
- **Open source contributors** showcasing their projects  
- **Developers and security researchers** sharing their journey
- **Conference speakers** documenting talks and presentations
- **Technology enthusiasts** reviewing gadgets and tools

## Quick Start

1. **Install Hugo** (version 0.158.0 or later)
2. **Create a new site**:
   ```bash
   hugo new site my-techie-site
   cd my-techie-site
   ```
3. **Add the theme**:
   ```bash
   git submodule add https://github.com/anantshri/hugo-techie-personal.git themes/hugo-techie-personal
   ```
4. **Copy example configuration**:
   ```bash
   cp themes/hugo-techie-personal/exampleSite/config.toml .
   ```
5. **Start the development server**:
   ```bash
   hugo server -D
   ```

## Demo

**Live Example:** See the theme in action at **[anantshri.info](https://anantshri.info)** - the author's personal site showcasing real-world usage with extensive timeline content, project portfolios, and gadget reviews.

**Demo Site:** A live demo is automatically deployed to GitHub Pages with each release, showcasing all theme features and the latest updates.

**Example Site:** Check out the [example site](exampleSite/) included with the theme to see all features and configuration options.

---

## Acknowledgments

This theme extends the excellent [Hugo Xmin](https://github.com/yihui/hugo-xmin) theme by [Yihui Xie](https://yihui.org), maintaining its minimal philosophy while adding powerful timeline functionality and modern features.

## Configuration

This theme provides comprehensive timeline functionality and additional features:

### Noti.st Integration

The theme supports embedding slides from Noti.st, including custom domain CNAMEs. Configure this in your `config.toml`:

```toml
[params]
  # Your Noti.st username
  notist_username = "your-username"
  
  # Array of custom domains that point to Noti.st
  # This allows the theme to recognize your custom domain as a Noti.st embed
  notist_custom_domains = ["slides.yourdomain.com", "presentations.example.org"]
```

**Example:**
- If you have `slides.anantshri.info` as a CNAME pointing to Noti.st
- Add it to the `notist_custom_domains` array
- The theme will automatically embed slides from that domain using your `notist_username`

### Slides / Presentations (Self-Hosted PDFs)

The theme supports hosting presentation slides as page bundles. PDFs are converted to **one high-resolution WebP per slide** stored in `assets/slides/<slug>/`. At build time, Hugo resizes these to thumb/medium/full (quality 100%) so the repo keeps a single copy per slide and the site still gets responsive images.

#### Content structure

```
assets/slides/
├── pdf_files/              # INBOX: drop source PDFs here
│   └── <slug>.pdf          # Filename (minus .pdf) = presentation slug
└── <slug>/                 # Processed WebP slide images (auto-generated)
    ├── slide-001.webp
    └── slide-NNN.webp

content/slides/
├── _index.md               # Section list page (see Output formats below)
└── <slug>/                 # One folder per presentation
    ├── index.md            # Frontmatter + abstract
    └── slides/
        └── metadata.json   # Auto-generated by process-slides.sh

static/slides/
└── <slug>/
    └── slides.pdf          # PDF copy for download (auto-copied by process-slides.sh)
```

Source PDFs go in `assets/slides/pdf_files/<slug>.pdf`. The processing scripts convert each page to a single high-res WebP at `assets/slides/<slug>/slide-NNN.webp` (1920px width cap) and copy the PDF to `static/slides/<slug>/slides.pdf` for download. Hugo’s image processing (`resources.Get` + `Resize`) generates thumb, medium, and full sizes at build time, so no pre-generated multi-tier files are needed. For backwards compatibility, if assets are missing the theme falls back to legacy bundle images at `content/slides/<slug>/slides/slide-NNN-{thumb,medium,full}.webp`.

#### Frontmatter (slides pages)

Use the slides archetype when creating new presentations:

```bash
hugo new slides/my-talk
```

Key frontmatter fields:

```yaml
title: "Presentation Title"
date: YYYY-MM-DD
draft: true

conference: "Conference Name"
conference_url: "https://..."
event_year: 2024

location:
  city: ""
  country: ""
  latitude: 0
  longitude: 0

slides:
  pdf: "slides.pdf"      # References the static download copy at static/slides/<slug>/slides.pdf
  page_count: 0          # Set by process-slides.sh or manually after processing
  external_url: ""       # Optional link to external slide deck
  download_enabled: true # Show PDF download button in viewer

videos: []               # Optional: list of { url, label }
resources: []            # Optional: list of { title, url }
timeline_entry: ""       # Path to related timeline entry, e.g. /timeline/event-slug/
related_presentations: [] # Paths to other /slides/... pages
tags: []
focus: []
activity: talk           # talk, training, tool, etc.

oembed:
  author_name: ""
  author_url: ""
  provider_name: ""
  provider_url: ""
```

#### Shortcodes

**Full viewer:**

```hugo
{{< slideviewer src="/slides/presentation-slug/" >}}
```

- `src` — path to the slides page (e.g. `/slides/blackhat-usa-2019-devsecops/`)
- Renders the full interactive viewer (toolbar, prev/next, grid, fullscreen, download).

**Card only (alternative shortcode):**

```hugo
{{< slide-embed src="/slides/presentation-slug/" >}}
```

Always renders a card linking to the presentation page.

#### Adding a new presentation

**Step 1: Drop the PDF in the inbox**

```bash
cp /path/to/presentation.pdf assets/slides/pdf_files/my-talk-event-2025.pdf
```

The filename (minus `.pdf`) becomes the slug. Uppercase and underscores are normalized to lowercase hyphens.

**Step 2: Scaffold the content page**

```bash
./themes/hugo-techie-personal/scripts/scaffold-slides.sh
```

Creates a draft `content/slides/<slug>/index.md` with template frontmatter. Edit this file to fill in title, conference, date, location, tags, etc.

**Step 3: Process the PDF into slide images**

```bash
./themes/hugo-techie-personal/scripts/process-slides.sh
```

The script:

1. Scans `assets/slides/pdf_files/` for `*.pdf` files
2. Requires a corresponding `content/slides/<slug>/index.md` (run scaffold first)
3. Skips PDFs where the source hash hasn’t changed (idempotent)
4. Converts each PDF page to WebP at 300 DPI, max 1920px width
5. Writes images to `assets/slides/<slug>/slide-NNN.webp`
6. Copies the PDF to `static/slides/<slug>/slides.pdf` for download serving
7. Generates `content/slides/<slug>/slides/metadata.json` with page count, PDF hash, and dimensions
8. Updates `slides.page_count` in `index.md` frontmatter automatically

Hugo then resizes each asset at build time to thumb (400px), medium (1024px), and full (1920px) with `Resize "…x webp q100"`, so the repository stores only one file per slide.

**Step 4: Build and verify**

```bash
hugo server
# Visit http://localhost:1313/slides/my-talk-event-2025/
# PDF download available at /slides/my-talk-event-2025/slides.pdf
```

**Dependencies:**

- `poppler-utils` (for `pdftoppm`)
- `libwebp` (for `cwebp`)
- ImageMagick (`magick` or `convert`)

Install on macOS: `brew install poppler webp imagemagick`  
Install on Debian/Ubuntu: `sudo apt-get install poppler-utils libwebp-dev imagemagick`

Already-processed PDFs are skipped by comparing the source file SHA-256 with the hash stored in `metadata.json`. Change the PDF and run the script again to regenerate.

#### Configuration

Add to your `config.toml`:

```toml
[params.slides]
  enabled = true
  default_author = "Your Name"
  default_author_url = "https://yoursite.com"
  pdf_download = true

  [params.slides.viewer]
    theme = "dark"           # Viewer theme
    show_grid_button = true  # Grid overview button
    show_fullscreen = true   # Fullscreen button
    show_counter = true      # "1 / N" counter
    show_download = true    # PDF download button
    keyboard_nav = true      # Arrow keys, Home/End, G (grid), F (fullscreen)
    swipe_nav = true         # Touch swipe
    preload_adjacent = 2     # Preload N slides on each side

  [params.slides.map]
    enabled = true
    tile_provider = "openstreetmap"
    default_zoom = 2
    cluster_markers = true
    show_on_listing = true
    show_on_home = false

  [params.slides.oembed]
    enabled = true
    embed_width = 640
    embed_height = 480
```

#### Output formats

For the slides section and OEmbed/Embed URLs to work, define these output formats and assign them to the slides section and home:

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

[outputs]
  home = ["HTML", "RSS", "SlidesJSON"]
```

In `content/slides/_index.md`, set the section cascade so each presentation gets HTML, OEmbed, and Embed:

```yaml
cascade:
  outputs:
    - HTML
    - OEmbed
    - Embed
```

Each presentation is then available as:

- `https://yoursite.com/slides/<slug>/` — full page with viewer
- `https://yoursite.com/slides/<slug>/oembed.json` — OEmbed metadata for external embeds
- `https://yoursite.com/slides/<slug>/embed.html` — embeddable iframe (self-contained with CSS custom properties for consistent toolbar styling)

#### Viewer features

- **Keyboard:** ←/→ previous/next, Home/End first/last, G toggle grid, F fullscreen, Escape exit fullscreen
- **URL hash:** `#slide-N` opens slide N
- **Touch:** Swipe left/right on touch devices
- **Preloading:** Adjacent slides (configurable) are preloaded for smooth navigation
- **Accessibility:** ARIA labels, live region for counter, focus management

#### Map integration

If `params.slides.map.enabled` is true and a presentation has `location.latitude` and `location.longitude` in frontmatter, it can appear on the Leaflet-based talks map. Set `online: true` for virtual/remote presentations to **exclude them from the map** even if coordinates are present. The home page can output `SlidesJSON` to supply slide locations for the map; the listing page can also show the map via the section's `map` config.

**Global events map:** If the home page also outputs `LocationsJSON`, the site can serve `locations.json` combining **slides** and **timeline** entries that have structured `location` (with `latitude` and `longitude`) and are **not** marked `online: true`. A standalone map page (e.g. `layout: map` and content at `/map/`) can then show all physical event locations. Timeline entries use the same `location` structure as slides (city, country, latitude, longitude) and the same `online` marker.

**Dedup between slides and timeline:** When a slide sets `timeline_entry` to link to a timeline page, the slide is **excluded** from the global events map; the linked timeline entry represents that event instead. This prevents duplicate markers for the same physical event. Ensure the linked timeline entry has its own `location` block — otherwise the event will not show on `/maps/`. The slide continues to appear on the slides-section map (`/slides/`) independent of this rule.

### Social Chatter (Timeline)

Timeline entry pages can display a **Social chatter** section with embedded social media posts. In timeline frontmatter, add a list of post URLs (strings only; platform is auto-detected):

```yaml
social_chatter:
  - "https://x.com/user/status/123456789"
  - "https://www.linkedin.com/posts/username_activity-123456789"
  - "https://infosec.exchange/@user/123456789"
  - "https://bsky.app/profile/user.bsky.social/post/abc123"
```

**Supported platforms:** Twitter/X, Bluesky, Mastodon (any instance with OEmbed discovery), LinkedIn, Facebook, Instagram.

Platform is detected from each URL. Twitter/X, Bluesky, and Mastodon use the site's OEmbed system (`data/oembed.json` and discovery); LinkedIn, Facebook, and Instagram use direct iframes. No JavaScript required. The section appears between the main content and Related Entities on the timeline single page.

### Analytics Configuration

The theme supports multiple analytics providers with flexible configuration:

```toml
[params.analytics]
  provider = "plausible"           # Options: "plausible", "plausible_cloud", "google", "custom"
  domain = "yourdomain.com"        # Your domain for analytics
  
  # For self-hosted Plausible with custom proxy (like nginx redirect):
  api_endpoint = "/api/event"      # Custom API endpoint
  script_src = "/js/script.js"     # Custom script source
  
  # For Plausible Cloud:
  # provider = "plausible_cloud"
  # domain = "yourdomain.com"
  
  # For Google Analytics:
  # provider = "google"
  # tracking_id = "G-XXXXXXXXXX"
  
  # For custom analytics code:
  # provider = "custom"
  # custom_code = '''<script>/* your custom analytics */</script>'''
```

**Self-hosted Plausible Setup:**
1. Set `provider = "plausible"`
2. Configure your nginx proxy to redirect `/api/event` and `/js/script.js` to your Plausible instance
3. Set your domain in the `domain` parameter
4. The theme will use your custom endpoints

**Note:** The nginx configuration for proxying is outside the theme scope but enables privacy-friendly analytics without exposing your analytics server directly.

### Work in Progress Notification System

The theme includes a flexible system for displaying work-in-progress notifications:

```toml
[params.work_in_progress]
  enabled = true                   # Enable/disable globally
  default_message = "This content is currently being updated..."
  default_title = "🚧 Work in Progress"
  exclude_statuses = ["discontinued", "archived", "completed", "finished"]  # Don't show WIP for these statuses
  
  # Predefined message types
  [params.work_in_progress.types]
    updating = { title = "🚧 Work in Progress", message = "Content being updated..." }
    incomplete = { title = "📝 Content Incomplete", message = "Partial information available..." }
    review = { title = "🔍 Under Review", message = "Content under review..." }
    placeholder = { title = "📋 Placeholder", message = "Content coming soon..." }
```

**Usage Options:**

1. **Section-level**: Add to section's `_index.md`:
   ```yaml
   work_in_progress: "updating"  # Use predefined type
   # OR
   work_in_progress: true        # Use default message
   # OR custom message:
   work_in_progress_title: "Custom Title"
   work_in_progress_message: "Custom message here"
   ```

2. **Page-level**: Add to individual page front matter (overrides section-level)
3. **Automatic display**: Shows on both list and single page views
4. **Smart exclusions**: WIP messages are automatically hidden for content with "final" statuses like `discontinued`, `archived`, `completed`, or `finished`

### Navigation System

The theme includes a modern, configurable navigation system:

```toml
[params.navigation]
  enable_breadcrumbs = true           # Enable breadcrumb navigation
  enable_prev_next = true             # Enable previous/next navigation
  breadcrumb_separator = "›"          # Breadcrumb separator character
  show_section_context = true         # Show current section in header
  
  # Configurable navigation labels (for internationalization)
  [params.navigation.labels]
    home = "Home"
    projects = "Projects"
    gadgets = "Gadgets"
    timeline = "Timeline"
    back_to = "Back to"
    previous = "Previous"
    next = "Next"
    currently_used = "Currently Used"
    upcoming = "Upcoming"
    discontinued = "Discontinued"
    discontinued_projects = "Discontinued Projects"
    archived_device = "⚠️ Archived Device"
    planned_device = "📋 Planned Device"
```

**Navigation Features:**
- **Breadcrumb navigation**: Shows `Home › Section › Current Page` path
- **Previous/Next navigation**: Navigate between adjacent pages in sections
- **Responsive design**: Adapts to mobile and desktop layouts
- **Configurable labels**: Customize all text for internationalization
- **Accessible**: Proper ARIA labels and semantic HTML

### Timeline Features

This theme is designed for timeline-based content with support for:
- Activity-based categorization
- Focus area taxonomies
- Embedded content (YouTube, Vimeo, SlideShare, Noti.st)
- Responsive timeline layout
- Configurable activity icons with intelligent fallbacks

#### Activity Icons Configuration

Configure timeline activity icons in your `config.toml`:

```toml
[params.timeline]
  show_activity_icons = true    # Enable/disable activity icons (default: true)
```

#### Icon System Architecture

The theme uses a **hierarchical icon system** that checks multiple locations:

**Theme Icons (Built-in):**
- Default icons included with theme in `themes/hugo-techie-personal/assets/images/`
- Includes all standard activity icons: `talk.svg`, `tool.svg`, `training.svg`, etc.
- Social media icons: `twitter.svg`, `linkedin.svg`, `mastodon.svg`, etc.
- Notice system icons: `info.svg`, `note.svg`, `tip.svg`, `warning.svg`

**Site-Specific Icons (Optional Override):**
- Place custom icons in your site's `assets/images/` directory
- Same naming format: `{activity-name}.svg` or `{platform}.svg`
- Site icons override theme icons when present

**Icon Requirements:**
- Format: SVG files for scalability
- Activity icons: 25x25px recommended
- Social icons: 50x50px recommended
- Notice icons: Included with theme

**Fallback Behavior:**
- **First**: Checks site `assets/images/` for custom icons
- **Second**: Falls back to theme's built-in icons
- **Third**: Shows styled text badges/links if no icons found
- **Configuration**: `show_activity_icons = false` disables all icons

## New Features Added (Extracted from hugo_booster)

### Notice/Admonition System
The theme now includes a comprehensive notice system for creating styled callout boxes:

**Usage:**
```hugo
{{< notice warning >}}
This is a warning message with custom styling!
{{< /notice >}}

{{< notice info "Custom Title" >}}
This is an info box with a custom title.
{{< /notice >}}
```

**Available Types:**
- `warning` - Red warning notices
- `info` - Orange informational notices  
- `tip` - Green tip notices
- `note` - Blue note notices (default)

**Features:**
- Custom titles supported
- Light/dark mode compatible
- Responsive design
- SVG icons for each type

### FontAwesome Shortcode
Easily embed FontAwesome icons as inline SVG:

**Usage:**
```hugo
{{< fontawesome "heart" >}} Love this feature!
```

**Requirements:**
- Place FontAwesome SVG files in `static/fontawesome/` directory
- SVG files should be named like `heart.svg`, `star.svg`, etc.

### Enhanced OEmbed System
The theme includes comprehensive OEmbed support with both hardcoded and data-driven providers:

**Hardcoded Platforms:**
- YouTube (with privacy-enhanced nocookie domains)
- Vimeo
- SlideShare
- Spreaker
- Noti.st (configurable custom domains)

**Data-Driven Platforms:**
The theme includes `data/oembed.json` with additional provider configurations for:
- Twitter
- Spotify
- SpeakerDeck
- CodeSandbox
- Apple Podcasts

**Features:**
- Consistent error handling with styled fallback messages
- Lazy loading iframes for performance
- Responsive wrapper containers
- Flexible configuration via JSON data file
- **OEmbed discovery**: Automatically discovers OEmbed endpoints by fetching the target page and reading `<link>` discovery tags — any site with OEmbed support (including self-hosted slides) works without explicit configuration
- Automatic fallback chain: data-driven → OEmbed discovery → Noti.st custom domains → error message

**Usage:**
```hugo
<!-- As shortcode -->
{{% oembed url="https://www.youtube.com/watch?v=example" %}}

<!-- Self-hosted slides (via OEmbed discovery) -->
{{% oembed url="https://yoursite.com/slides/presentation-slug/" %}}

<!-- As partial -->
{{ partial "oembed.html" "https://www.youtube.com/watch?v=example" }}
```

**Note on self-hosted slides**: The OEmbed shortcode can embed slides from your own site via OEmbed discovery (the slides section's OEmbed/Embed output formats are auto-discovered). For same-site slides, prefer the `slideviewer` shortcode which renders natively without an iframe. OEmbed with relative URLs or `localhost` will not work since Hugo's `resources.GetRemote` cannot fetch from itself during build.

### Professional Badge Integration

The theme provides comprehensive support for displaying professional certifications and badges from popular platforms:

#### Credly Integration

Display your Credly badges with automatic API fetching and intelligent caching:

```toml
[params]
  # Your Credly username
  credly_username = "your-username"
  
  # Optional: Custom image directory for cached badge images
  credly_image_dir = "images/CredlyBadges"  # Default
```

**Usage:**
```hugo
<!-- Display all Credly badges -->
{{< credly-badges >}}

<!-- Display with custom size -->
{{< credly-badges size="small" >}}

<!-- Hide expired badges -->
{{< credly-badges hide_expired="true" >}}

<!-- Show only expired badges -->
{{< credly-badges show_expired="true" >}}
```

#### Accredible Integration

Display your Accredible credentials with API integration:

```toml
[params]
  # Your Accredible username
  accredible_username = "your-username"
  
  # Optional: Custom image directory for cached badge images
  accredible_image_dir = "images/AccredibleBadges"  # Default
```

**Usage:**
```hugo
<!-- Display all Accredible badges -->
{{< accredible-badges >}}

<!-- Display with custom options -->
{{< accredible-badges size="small" hide_expired="true" >}}
```

#### Badgr Integration

Display your Badgr badges with API integration:

```toml
[params]
  # Your Badgr username
  badgr_username = "your-username"
  
  # API token (required for API access)
  badgr_api_token = "your-api-token"
  
  # Optional: Custom image directory for cached badge images
  badgr_image_dir = "images/BadgrBadges"  # Default
```

**Usage:**
```hugo
<!-- Display all Badgr badges -->
{{< badgr-badges >}}

<!-- Display with custom options -->
{{< badgr-badges size="small" hide_expired="true" >}}
```

#### Manual/Custom Badges

Add custom badges by creating `data/ManualBadges.json`:

```json
{
  "badges": [
    {
      "id": "custom-1",
      "name": "Custom Badge Name",
      "description": "Badge description",
      "image_url": "https://example.com/badge-image.png",
      "issued_at": "2024-01-15T00:00:00Z",
      "expires_at": "2025-01-15T00:00:00Z",
      "url": "https://example.com/badge-link"
    }
  ]
}
```

**Usage:**
```hugo
{{< manual-badges >}}
```

#### Open Badges Support

Add Open Badges (JSON-LD format) by creating `data/OpenBadges.json`:

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

**Usage:**
```hugo
{{< openbadges-badges >}}
```

#### Bugcrowd Integration

Display your Bugcrowd badges with API integration. By default, only awarded badges are displayed, but performance statistics and hall of fame data are automatically fetched and cached:

```toml
[params]
  # Your Bugcrowd username
  bugcrowd_username = "your-username"
  
  # Optional: Custom image directory for cached badge images
  bugcrowd_image_dir = "images/BugcrowdBadges"  # Default
```

**Usage:**
```hugo
<!-- Display all awarded Bugcrowd badges -->
{{< bugcrowd-badges >}}

<!-- Display with custom options -->
{{< bugcrowd-badges size="small" hide_expired="true" >}}

<!-- Display with statistics and hall of fame (if needed) -->
{{< bugcrowd-badges show_statistics="true" show_hall_of_fame="true" >}}
```

**Features:**
- **Automatic API fetching** from Bugcrowd profile endpoints
- **Awarded badges only** displayed by default
- **Performance statistics** fetched and cached (displayed only if requested)
- **Hall of Fame** data fetched and cached (displayed only if requested)
- **Intelligent caching** for all data types

#### HackerOne Integration

Display your HackerOne badges with API integration:

```toml
[params]
  # Your HackerOne username
  hackerone_username = "your-username"
  
  # Optional: Custom image directory for cached badge images
  hackerone_image_dir = "images/HackerOneBadges"  # Default
```

**Usage:**
```hugo
<!-- Display all HackerOne badges -->
{{< hackerone-badges >}}

<!-- Display with custom options -->
{{< hackerone-badges size="small" hide_expired="true" >}}
```

**API Endpoint:**
The integration uses the HackerOne public API endpoint: `https://hackerone.com/{username}/badges.json`

**Features:**
- **Automatic API fetching** from HackerOne profile badges endpoint
- **Relative image URL handling** - automatically converts relative URLs to absolute
- **Intelligent caching** for badge data and images
- **Unified display** - integrates seamlessly with other badge platforms

#### Unified Badge Display

Display badges from all platforms in a unified grid:

```hugo
<!-- Display badges from all platforms -->
{{< badges >}}

<!-- Display only specific platforms -->
{{< badges show_accredible="false" show_badgr="false" >}}

<!-- Display only Credly badges -->
{{< badges show_accredible="false" show_manual="false" show_openbadges="false" show_badgr="false" >}}

<!-- Custom sizing and filtering -->
{{< badges size="small" hide_expired="true" >}}
```

**Badge Features:**
- **Multiple platform support**: Credly, Accredible, Badgr, Bugcrowd, HackerOne, Open Badges, and Manual badges
- **Automatic API fetching** with intelligent caching for performance
- **Fallback system**: API → cached data → Site.Data → graceful degradation
- **Expiration handling**: Show/hide expired badges with visual indicators
- **Responsive design**: Adapts to different screen sizes
- **Local image caching**: Reduces API calls and improves load times
- **Error handling**: Graceful fallbacks when APIs are unavailable
- **Unified display**: Mix badges from multiple platforms seamlessly

### Bio Page

A structured biography page with copy-to-clipboard functionality, multiple format views (Rendered, Markdown, Plain Text), and a downloadable photos section.

Set `layout: bio` in your page frontmatter with `short_bio`, `long_bio`, and optional `photos` fields. See [docs/layouts.md](docs/layouts.md) for full details.

### Events Map Page

A standalone page showing all physical event locations on a Leaflet map. Set `layout: map` in your page frontmatter. Requires `params.slides.map.enabled = true` and `LocationsJSON` output format on the home page.

Timeline and slide entries with `location.latitude` and `location.longitude` (and not marked `online: true`) appear on the map. Slides that set `timeline_entry` are excluded from this map and represented by their linked timeline entry instead, so each physical event appears only once. See [docs/layouts.md](docs/layouts.md) for details.

### Related Links

Timeline entries can display card-style links to external content (blog posts, research pages, etc.) using the `related_links` frontmatter field:

```yaml
related_links:
  - url: "https://example.com/blog/post"
    title: "Blog Post Title"
    image: "https://example.com/og-image.jpg"
    description: "Short description"
```

Title, image, and description are auto-fetched from Open Graph meta tags when omitted.

### AI Summaries

AI-generated summaries are stored in `ai_summary/` subdirectories and automatically included by templates at build time. No shortcodes needed in content files. See your project's AGENTS.md or theme docs for the full workflow.

### Social Archive (Takeouts)

The theme ships a small set of Python importers that convert X/Twitter, LinkedIn, Instagram, and Facebook data exports into Hugo page bundles under `content/archive/<platform>/`. Each archived post is published at a URL that mirrors the original (e.g. `/x.com/<user>/status/<id>/`), so pasting the original URL behind your site's domain resolves to the local copy.

**Importers** (all live under `themes/hugo-techie-personal/scripts/`):

```bash
uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_twitter.py \
    --takeout takeouts/twitter-<date>.zip --user <handle>

uv run --with pyyaml --with beautifulsoup4 --with lxml --with markdownify python3 \
    themes/hugo-techie-personal/scripts/import_linkedin.py \
    --takeout takeouts/linkedin-<date>.zip
# Imports feed posts from Shares.csv and/or Pulse articles from
# Articles/Articles/*.html, whichever are present in the archive.

uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_instagram.py \
    --takeout takeouts/instagram-<date>.zip --user <handle>

uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_facebook.py \
    --takeout takeouts/facebook-<date>.zip --user <handle>
```

- The scripts auto-detect the site root from their location in the theme (or honour `HUGO_SITE_ROOT` if set).
- All posts default to `draft: true` — pass `--publish` to bulk-publish new imports, or flip `draft: false` manually.
- Re-running an importer is idempotent (SHA-256 manifest) and never clobbers a manually-curated `draft` value.
- Instagram and Facebook exports omit public permalinks; optional sidecars (`takeouts/instagram-shortcode-map.json`, `takeouts/facebook-url-map.json`) restore URL mirroring.
- A smart redirector in `layouts/404.html` flattens `:`, `?`, `&`, `=` → `/` so URLs with LinkedIn URNs or Facebook query-string permalinks still resolve.

**Content section**: create `content/archive/_index.md` (optionally per-platform `content/archive/<platform>/_index.md`) to enable the browse listing at `/archive/`.

## Documentation

Detailed documentation is available in the [`docs/`](docs/) directory:

- **[Configuration Reference](docs/configuration.md)** — All `config.toml` parameters
- **[Page Layouts](docs/layouts.md)** — Bio, Map, Home, alternate list layouts, Banner
- **[Shortcodes Reference](docs/shortcodes.md)** — All available shortcodes with examples

## Automated Deployment

The theme includes GitHub Actions for automated testing and demo site deployment:

- **Continuous Testing** - Automatic theme validation on every push and pull request
- **Demo Deployment** - Automatic GitHub Pages deployment on new releases
- **Multi-version Testing** - Tests against multiple Hugo versions for compatibility
- **HTML Validation** - Automated checks for generated content quality

The demo site is automatically updated whenever a new release is published, ensuring the latest features are always showcased.
