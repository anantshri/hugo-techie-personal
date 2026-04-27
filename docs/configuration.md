# Configuration Reference

Complete reference for all `config.toml` parameters supported by the theme.

## Site Parameters

```toml
[params]
  subtitle = "Your tagline"
  description = "Site-wide description for meta tags"
  footer = "&copy; [Your Name](https://yoursite.com)"
  profile_pic = "images/profile.png"     # Path under assets/
  home_layout = "home-layout-50-50"      # Home page CSS layout class
  Banner = "Banner message with **Markdown** support"  # Site-wide banner (capital B)
```

## Analytics

```toml
[params.analytics]
  provider = "plausible"           # "plausible", "plausible_cloud", "google", "custom"
  domain = "yourdomain.com"

  # Self-hosted Plausible
  api_endpoint = "/api/event"
  script_src = "/js/script.js"

  # Google Analytics
  # tracking_id = "G-XXXXXXXXXX"

  # Custom analytics
  # custom_code = '''<script>/* your code */</script>'''
```

## Navigation

```toml
[params.navigation]
  enable_breadcrumbs = true
  enable_prev_next = true
  breadcrumb_separator = "›"
  show_section_context = true

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

## Timeline

```toml
[params.timeline]
  show_activity_icons = true    # Show SVG icons for activity types
```

## Slides / Presentations

```toml
[params.slides]
  enabled = true
  default_author = "Your Name"
  default_author_url = "https://yoursite.com"
  pdf_download = true

  [params.slides.viewer]
    theme = "dark"
    show_grid_button = true
    show_fullscreen = true
    show_counter = true
    show_download = true
    keyboard_nav = true
    swipe_nav = true
    preload_adjacent = 2

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
    embed_chrome_height = 70   # Pixel height of viewer toolbar chrome
```

## Sponsor / Support Buttons

The theme ships a data-driven sponsor button row (FUNDING.yml-style schema) that
can appear in up to four places: on the homepage under the social icons, on the
projects listing page, embedded inline via the `support-buttons` shortcode, and
as a sticky banner just below the menu on every page. All four placements share
the same configuration and render nothing when no platforms are configured.

```toml
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

  # Display toggles
  show_on_projects = true             # show buttons above the projects listing (default true)
  show_as_banner = false              # sticky strip below the menu on every page (default false)
  banner_label = "Support my work"    # optional prefix label for the sticky banner
```

```toml
# Homepage display toggles. Page-level frontmatter (in content/_index.md) wins
# over these site-wide defaults.
[params.home]
  show_social = true   # show social icons on the homepage (default true)
  show_sponsor = true  # show sponsor buttons under the social icons (default true)
```

The sticky banner is wrapped together with the main menu in a single
`.site-top-bar` element so the two pin to the top of the viewport as one
unit. On screens narrower than 480px the banner label and button labels
collapse, leaving only the icons.

## Work in Progress

```toml
[params.work_in_progress]
  enabled = true
  default_message = "This content is currently being updated..."
  default_title = "🚧 Work in Progress"
  exclude_statuses = ["discontinued", "archived", "completed", "finished"]

  [params.work_in_progress.types]
    updating = { title = "🚧 Work in Progress", message = "Content being updated..." }
    incomplete = { title = "📝 Content Incomplete", message = "Partial information..." }
    review = { title = "🔍 Under Review", message = "Content under review..." }
    placeholder = { title = "📋 Placeholder", message = "Content coming soon..." }
```

## Noti.st Integration

```toml
[params]
  notist_username = "your-username"
  notist_custom_domains = ["slides.yourdomain.com"]
```

## Badge Platforms

```toml
[params]
  credly_username = "username"
  credly_image_dir = "images/CredlyBadges"

  accredible_username = "username"
  accredible_image_dir = "images/AccredibleBadges"

  badgr_username = "username"
  badgr_api_token = "token"
  badgr_image_dir = "images/BadgrBadges"

  bugcrowd_username = "username"
  bugcrowd_image_dir = "images/BugcrowdBadges"

  hackerone_username = "username"
  hackerone_image_dir = "images/HackerOneBadges"
```

## Output Formats

Required in `config.toml` for slides, OEmbed, and map features:

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

## Taxonomies

```toml
[taxonomies]
  types = "type"
  focus = "focus"
  activities = "activity"
```
